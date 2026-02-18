"""HTTP adapters that call ScratchBird parser/compiler/execution endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import parse, request

from .base import (
    AdapterCompileResult,
    AdapterExecuteResult,
    CompilerAdapter,
    DialectAdapter,
    ExecutorAdapter,
    MetadataAdapter,
)


class HttpAdapterError(RuntimeError):
    """Raised when an adapter HTTP request fails or returns invalid payload."""


class JsonHttpClient(Protocol):
    def request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> Any:
        ...


class HttpJsonClient:
    """Small stdlib JSON-over-HTTP client used by adapters."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_sec: float,
        api_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.api_token = api_token

    def request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> Any:
        query_string = ""
        if query:
            query_string = f"?{parse.urlencode(query)}"

        url = f"{self.base_url}{path}{query_string}"
        data = None
        headers: dict[str, str] = {"Accept": "application/json"}

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        req = request.Request(url=url, method=method.upper(), data=data, headers=headers)

        try:
            with request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network failures are environment-specific
            raise HttpAdapterError(f"HTTP request failed for {method} {path}: {exc}") from exc

        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise HttpAdapterError(f"Invalid JSON response for {method} {path}: {exc}") from exc



def _as_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HttpAdapterError(f"Expected object for {field_name}, got {type(value).__name__}")
    return value



def _as_list_of_strings(value: Any, *, field_name: str) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise HttpAdapterError(f"Expected string list for {field_name}")


class ScratchBirdHttpCompilerAdapter(CompilerAdapter):
    def __init__(self, *, dialect: str, client: JsonHttpClient) -> None:
        self.dialect = dialect
        self.client = client

    def compile_query(self, query_text: str, context: dict[str, Any]) -> AdapterCompileResult:
        resp = self.client.request(
            method="POST",
            path=f"/v1/dialects/{self.dialect}/compile",
            payload={"query_text": query_text, "context": context},
        )
        doc = _as_mapping(resp, field_name="compile response")

        statement_kind = doc.get("statement_kind", "unknown")
        sblr_hash = str(doc.get("sblr_hash", ""))
        diagnostics = doc.get("diagnostics", [])
        warnings = doc.get("warnings", [])

        if statement_kind not in {"read", "mutation", "unknown"}:
            statement_kind = "unknown"

        if not isinstance(diagnostics, list):
            diagnostics = [str(diagnostics)]
        diagnostics = [str(item) for item in diagnostics]

        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        warnings = [str(item) for item in warnings]

        if not sblr_hash:
            raise HttpAdapterError("compile response missing sblr_hash")

        return AdapterCompileResult(
            statement_kind=statement_kind,
            sblr_hash=sblr_hash,
            diagnostics=diagnostics,
            warnings=warnings,
        )


class ScratchBirdHttpExecutorAdapter(ExecutorAdapter):
    def __init__(self, *, dialect: str, client: JsonHttpClient) -> None:
        self.dialect = dialect
        self.client = client

    def execute_compiled(
        self,
        *,
        compile_artifact_id: str,
        query_text: str,
        options: dict[str, Any],
    ) -> AdapterExecuteResult:
        resp = self.client.request(
            method="POST",
            path=f"/v1/dialects/{self.dialect}/execute",
            payload={
                "compile_artifact_id": compile_artifact_id,
                "query_text": query_text,
                "options": options,
            },
        )
        doc = _as_mapping(resp, field_name="execute response")

        rows_raw = doc.get("rows", [])
        notices_raw = doc.get("notices", [])

        if not isinstance(rows_raw, list):
            raise HttpAdapterError("execute response field 'rows' must be a list")

        rows: list[dict[str, Any]] = []
        for idx, item in enumerate(rows_raw):
            if not isinstance(item, dict):
                raise HttpAdapterError(f"row {idx} is not an object")
            rows.append(item)

        if not isinstance(notices_raw, list):
            notices_raw = [str(notices_raw)]
        notices = [str(item) for item in notices_raw]

        return AdapterExecuteResult(rows=rows, notices=notices)


class ScratchBirdHttpMetadataAdapter(MetadataAdapter):
    def __init__(self, *, dialect: str, client: JsonHttpClient) -> None:
        self.dialect = dialect
        self.client = client

    def list_schemas(self, database: str | None = None) -> list[str]:
        query: dict[str, str] | None = None
        if database:
            query = {"database": database}

        resp = self.client.request(
            method="GET",
            path=f"/v1/dialects/{self.dialect}/schemas",
            query=query,
        )

        if isinstance(resp, list):
            return _as_list_of_strings(resp, field_name="schemas")

        doc = _as_mapping(resp, field_name="schemas response")
        return _as_list_of_strings(doc.get("schemas", []), field_name="schemas")

    def list_tables(self, schema: str) -> list[str]:
        encoded = parse.quote(schema, safe="")
        resp = self.client.request(
            method="GET",
            path=f"/v1/dialects/{self.dialect}/schemas/{encoded}/tables",
        )

        if isinstance(resp, list):
            return _as_list_of_strings(resp, field_name="tables")

        doc = _as_mapping(resp, field_name="tables response")
        return _as_list_of_strings(doc.get("tables", []), field_name="tables")

    def describe_table(self, schema: str, table: str) -> dict[str, Any]:
        encoded_schema = parse.quote(schema, safe="")
        encoded_table = parse.quote(table, safe="")
        resp = self.client.request(
            method="GET",
            path=(
                f"/v1/dialects/{self.dialect}/schemas/{encoded_schema}/tables/{encoded_table}"
            ),
        )
        return _as_mapping(resp, field_name="table description")


@dataclass(slots=True)
class ScratchBirdHttpDialectAdapter(DialectAdapter):
    dialect: str
    compiler: CompilerAdapter
    executor: ExecutorAdapter
    metadata: MetadataAdapter



def make_http_dialect_adapter(
    *,
    dialect: str,
    client: JsonHttpClient,
) -> ScratchBirdHttpDialectAdapter:
    return ScratchBirdHttpDialectAdapter(
        dialect=dialect,
        compiler=ScratchBirdHttpCompilerAdapter(dialect=dialect, client=client),
        executor=ScratchBirdHttpExecutorAdapter(dialect=dialect, client=client),
        metadata=ScratchBirdHttpMetadataAdapter(dialect=dialect, client=client),
    )
