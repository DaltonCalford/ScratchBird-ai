"""HTTP bridge service that exposes ScratchBird compile/execute/metadata routes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Protocol
from urllib import parse
from uuid import UUID


DEFAULT_DIALECTS = ("native",)
DEFAULT_REQUEST_MAX_BYTES = 2 * 1024 * 1024


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(part.strip().lower() for part in raw.split(",") if part.strip())


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _classify_statement_kind(query_text: str) -> str:
    lowered = query_text.strip().lower()
    if not lowered:
        return "unknown"

    match = re.match(r"[a-z]+", lowered)
    if not match:
        return "unknown"

    keyword = match.group(0)
    if keyword in {"select", "with", "show", "describe", "desc", "explain"}:
        return "read"
    if keyword in {
        "insert",
        "update",
        "delete",
        "merge",
        "create",
        "alter",
        "drop",
        "truncate",
        "grant",
        "revoke",
        "set",
        "call",
        "execute",
    }:
        return "mutation"
    return "unknown"


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return str(value)


@dataclass(slots=True)
class BridgeCompileResult:
    statement_kind: str
    sblr_hash: str
    diagnostics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BridgeExecuteResult:
    rows: list[dict[str, Any]]
    notices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BridgeBackend(Protocol):
    def compile_query(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any],
    ) -> BridgeCompileResult:
        ...

    def execute_query(
        self,
        *,
        dialect: str,
        query_text: str,
        options: dict[str, Any],
        compile_artifact_id: str,
    ) -> BridgeExecuteResult:
        ...

    def list_schemas(self, *, dialect: str, database: str | None = None) -> list[str]:
        ...

    def list_tables(self, *, dialect: str, schema: str) -> list[str]:
        ...

    def describe_table(self, *, dialect: str, schema: str, table: str) -> dict[str, Any]:
        ...


class BridgeError(RuntimeError):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(slots=True)
class BridgeSettings:
    host: str = "127.0.0.1"
    port: int = 3095
    api_token: str | None = None
    request_max_bytes: int = DEFAULT_REQUEST_MAX_BYTES
    strict_compile: bool = False
    default_dsn: str = ""
    enabled_dialects: tuple[str, ...] = DEFAULT_DIALECTS
    dialect_dsns: dict[str, str] = field(default_factory=dict)
    python_driver_src: str = ""

    @classmethod
    def from_env(cls) -> BridgeSettings:
        dialect_dsns: dict[str, str] = {}
        for key, value in os.environ.items():
            if not key.startswith("SCRATCHBIRD_AI_BRIDGE_DSN_"):
                continue
            suffix = key.removeprefix("SCRATCHBIRD_AI_BRIDGE_DSN_").strip()
            if not suffix:
                continue
            dialect = suffix.lower()
            dsn = value.strip()
            if dsn:
                dialect_dsns[dialect] = dsn

        default_dsn = os.getenv("SCRATCHBIRD_AI_BRIDGE_DEFAULT_DSN", "").strip()
        enabled = _parse_csv(
            os.getenv(
                "SCRATCHBIRD_AI_BRIDGE_DIALECTS",
                ",".join(DEFAULT_DIALECTS),
            )
        )
        if not enabled:
            enabled = DEFAULT_DIALECTS

        strict_raw = os.getenv("SCRATCHBIRD_AI_BRIDGE_STRICT_COMPILE", "0").strip().lower()
        strict_compile = strict_raw in {"1", "true", "yes", "on"}

        return cls(
            host=os.getenv("SCRATCHBIRD_AI_BRIDGE_HOST", "127.0.0.1").strip(),
            port=_env_int("SCRATCHBIRD_AI_BRIDGE_PORT", 3095),
            api_token=os.getenv("SCRATCHBIRD_AI_BRIDGE_API_TOKEN", "").strip() or None,
            request_max_bytes=_env_int(
                "SCRATCHBIRD_AI_BRIDGE_REQUEST_MAX_BYTES",
                DEFAULT_REQUEST_MAX_BYTES,
            ),
            strict_compile=strict_compile,
            default_dsn=default_dsn,
            enabled_dialects=enabled,
            dialect_dsns=dialect_dsns,
            python_driver_src=os.getenv("SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC", "").strip(),
        )

    def require_enabled_dialect(self, dialect: str) -> None:
        normalized = dialect.strip().lower()
        enabled_set = set(self.enabled_dialects)
        if normalized not in enabled_set:
            enabled_list = ", ".join(sorted(enabled_set)) if enabled_set else "<none>"
            raise BridgeError(
                status_code=404,
                message=(
                    f"Unsupported dialect '{dialect}'. "
                    f"Bridge is configured for enabled dialects: {enabled_list}"
                ),
            )

    def resolve_dsn(self, dialect: str) -> str:
        normalized = dialect.strip().lower()
        self.require_enabled_dialect(normalized)

        if normalized in self.dialect_dsns:
            return self.dialect_dsns[normalized]
        if self.default_dsn:
            return self.default_dsn
        raise BridgeError(
            status_code=404,
            message=f"No bridge DSN configured for dialect: {dialect}",
        )


class ScratchBirdDriverBackend:
    """Bridge backend that uses the ScratchBird Python driver for live queries.

    SQL text enters parser/wire adapter flow via driver APIs. Engine execution remains
    SBLR-based in ScratchBird core execution boundary.
    """

    def __init__(self, settings: BridgeSettings) -> None:
        self.settings = settings

        driver_src = settings.python_driver_src
        if driver_src and driver_src not in sys.path:
            sys.path.insert(0, driver_src)

        try:
            import scratchbird as scratchbird_module
        except ImportError as exc:
            raise RuntimeError(
                "Unable to import scratchbird Python driver. "
                "Set SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC or install the package."
            ) from exc

        self._scratchbird = scratchbird_module
        try:
            from scratchbird import protocol as protocol_module
        except ImportError:
            protocol_module = None
        self._protocol = protocol_module

    def compile_query(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any],
    ) -> BridgeCompileResult:
        self.settings.resolve_dsn(dialect)
        statement_kind = _classify_statement_kind(query_text)
        fallback_hash = hashlib.sha256(
            f"{dialect}\n{query_text}".encode("utf-8")
        ).hexdigest()

        warnings: list[str] = []
        diagnostics: list[str] = []
        sblr_hash = fallback_hash

        # Compile probe is performed only for read statements to avoid accidental side effects.
        if statement_kind == "read":
            try:
                server_hash = self._probe_compile_sblr_hash(
                    dialect=dialect,
                    query_text=query_text,
                    context=context,
                )
                if server_hash:
                    sblr_hash = server_hash
                else:
                    warnings.append("Compile probe returned no SBLR hash; using fallback hash.")
            except Exception as exc:
                if self.settings.strict_compile:
                    raise BridgeError(status_code=400, message=f"Compile probe failed: {exc}") from exc
                warnings.append(f"Compile probe unavailable: {exc}")
        else:
            warnings.append("Mutation/unknown compile path uses local statement classification only.")

        return BridgeCompileResult(
            statement_kind=statement_kind,
            sblr_hash=sblr_hash,
            diagnostics=diagnostics,
            warnings=warnings,
        )

    def execute_query(
        self,
        *,
        dialect: str,
        query_text: str,
        options: dict[str, Any],
        compile_artifact_id: str,
    ) -> BridgeExecuteResult:
        del compile_artifact_id
        params = options.get("params")
        max_rows_value = options.get("max_rows", 0)
        try:
            max_rows = int(max_rows_value)
        except (TypeError, ValueError):
            max_rows = 0

        columns, rows, rowcount = self._run_query(
            dialect=dialect,
            sql=query_text,
            params=params,
            max_rows=max_rows,
        )
        out_rows = [self._row_to_dict(columns, row) for row in rows]
        notices: list[str] = []
        if rowcount is not None and rowcount >= 0:
            notices.append(f"rowcount={rowcount}")
        if max_rows > 0 and len(out_rows) >= max_rows:
            notices.append(f"max_rows={max_rows} limit reached")
        return BridgeExecuteResult(rows=out_rows, notices=notices)

    def list_schemas(self, *, dialect: str, database: str | None = None) -> list[str]:
        del database
        attempts = [
            "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name",
            "SELECT DISTINCT table_schema AS schema_name FROM information_schema.tables "
            "ORDER BY schema_name",
            "SELECT TRIM(rdb$owner_name) AS schema_name FROM rdb$relations "
            "WHERE rdb$system_flag = 0 GROUP BY rdb$owner_name ORDER BY rdb$owner_name",
        ]
        return self._query_first_column_with_fallbacks(dialect=dialect, attempts=attempts)

    def list_tables(self, *, dialect: str, schema: str) -> list[str]:
        schema_lit = _sql_literal(schema)
        attempts = [
            "SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = {schema_lit} ORDER BY table_name",
            "SELECT TRIM(rdb$relation_name) AS table_name FROM rdb$relations "
            "WHERE rdb$system_flag = 0 ORDER BY rdb$relation_name",
        ]
        return self._query_first_column_with_fallbacks(dialect=dialect, attempts=attempts)

    def describe_table(self, *, dialect: str, schema: str, table: str) -> dict[str, Any]:
        schema_lit = _sql_literal(schema)
        table_lit = _sql_literal(table)
        attempts = [
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            f"WHERE table_schema = {schema_lit} AND table_name = {table_lit} "
            "ORDER BY ordinal_position",
            "SELECT TRIM(rf.rdb$field_name) AS column_name, "
            "TRIM(f.rdb$field_type) AS data_type, "
            "CASE WHEN rf.rdb$null_flag = 1 THEN 'NO' ELSE 'YES' END AS is_nullable "
            "FROM rdb$relation_fields rf "
            "JOIN rdb$fields f ON rf.rdb$field_source = f.rdb$field_name "
            f"WHERE TRIM(rf.rdb$relation_name) = UPPER({table_lit}) "
            "ORDER BY rf.rdb$field_position",
        ]

        last_error: Exception | None = None
        for sql in attempts:
            try:
                columns, rows, _ = self._run_query(dialect=dialect, sql=sql, params=None, max_rows=0)
            except Exception as exc:
                last_error = exc
                continue
            if not rows:
                continue
            col_index = {name.lower(): idx for idx, name in enumerate(columns)}
            result_columns: list[dict[str, Any]] = []
            for row in rows:
                name_idx = col_index.get("column_name", 0)
                type_idx = col_index.get("data_type", 1 if len(row) > 1 else 0)
                null_idx = col_index.get("is_nullable", 2 if len(row) > 2 else 0)

                name = str(row[name_idx]).strip()
                type_name = str(row[type_idx]).strip()
                nullable_text = str(row[null_idx]).strip().lower()
                nullable = nullable_text in {"yes", "true", "1", "nullable"}
                result_columns.append(
                    {
                        "name": name,
                        "type": type_name,
                        "nullable": nullable,
                    }
                )
            return {
                "dialect": dialect,
                "schema": schema,
                "table": table,
                "columns": result_columns,
            }

        if last_error is not None:
            raise BridgeError(status_code=501, message=f"Describe table unsupported: {last_error}") from last_error
        return {
            "dialect": dialect,
            "schema": schema,
            "table": table,
            "columns": [],
        }

    def _query_first_column_with_fallbacks(self, *, dialect: str, attempts: list[str]) -> list[str]:
        last_error: Exception | None = None
        for sql in attempts:
            try:
                _, rows, _ = self._run_query(dialect=dialect, sql=sql, params=None, max_rows=0)
            except Exception as exc:
                last_error = exc
                continue
            out: list[str] = []
            seen: set[str] = set()
            for row in rows:
                if not row:
                    continue
                value = str(row[0]).strip()
                if not value or value in seen:
                    continue
                seen.add(value)
                out.append(value)
            return out
        if last_error is not None:
            raise BridgeError(status_code=501, message=f"Metadata query unsupported: {last_error}") from last_error
        return []

    def _probe_compile_sblr_hash(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any],
    ) -> str | None:
        protocol = self._protocol
        if protocol is None:
            raise RuntimeError("scratchbird.protocol unavailable")

        timeout_ms_raw = context.get("timeout_ms", 0)
        try:
            timeout_ms = int(timeout_ms_raw)
        except (TypeError, ValueError):
            timeout_ms = 0

        flags = protocol.QUERY_FLAG_DESCRIBE_ONLY
        flags |= protocol.QUERY_FLAG_INCLUDE_PLAN
        flags |= protocol.QUERY_FLAG_RETURN_SBLR
        if bool(context.get("no_cache")):
            flags |= protocol.QUERY_FLAG_NO_CACHE

        conn = self._connect(dialect)
        try:
            payload = protocol.build_query_payload(query_text, flags, 0, timeout_ms)
            conn._send_message(protocol.MessageType.QUERY, payload)
            conn._send_message(protocol.MessageType.SYNC, b"")
            conn._drain_until_ready()
            sblr = conn.last_sblr()
            if isinstance(sblr, tuple) and sblr and isinstance(sblr[0], int):
                return f"{sblr[0]:016x}"
            return None
        finally:
            conn.close()

    def _run_query(
        self,
        *,
        dialect: str,
        sql: str,
        params: Any,
        max_rows: int,
    ) -> tuple[list[str], list[tuple[Any, ...]], int]:
        conn = self._connect(dialect)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            description = cursor.description or []
            columns = [str(col[0]) for col in description]
            rows: list[tuple[Any, ...]] = []

            while True:
                batch = cursor.fetchmany(256)
                if not batch:
                    break
                for row in batch:
                    rows.append(tuple(row))
                    if max_rows > 0 and len(rows) >= max_rows:
                        break
                if max_rows > 0 and len(rows) >= max_rows:
                    break

            rowcount = int(cursor.rowcount) if isinstance(cursor.rowcount, int) else -1
            return columns, rows, rowcount
        finally:
            conn.close()

    def _row_to_dict(self, columns: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
        if columns and len(columns) == len(row):
            return {columns[idx]: _json_safe(value) for idx, value in enumerate(row)}

        out: dict[str, Any] = {}
        for idx, value in enumerate(row):
            key = columns[idx] if idx < len(columns) and columns[idx] else f"col_{idx + 1}"
            out[key] = _json_safe(value)
        return out

    def _connect(self, dialect: str):
        dsn = self.settings.resolve_dsn(dialect)
        try:
            return self._scratchbird.connect(dsn=dsn)
        except Exception as exc:
            raise BridgeError(status_code=503, message=f"Connection failed for dialect {dialect}: {exc}") from exc


@dataclass(slots=True)
class ScratchBirdBridgeApp:
    settings: BridgeSettings
    backend: BridgeBackend


class _BridgeHandler(BaseHTTPRequestHandler):
    app: ScratchBirdBridgeApp

    server_version = "ScratchBirdAIHTTPBridge/0.1"

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, fmt: str, *args: Any) -> None:
        del fmt, args
        return

    def _dispatch(self, method: str) -> None:
        try:
            self._authorize()
            parsed = parse.urlparse(self.path)
            segments = [parse.unquote(part) for part in parsed.path.split("/") if part]
            query_params = parse.parse_qs(parsed.query)

            if method == "GET" and segments == ["healthz"]:
                self._send_json(200, {"status": "ok"})
                return

            if len(segments) < 3 or segments[0] != "v1" or segments[1] != "dialects":
                raise BridgeError(status_code=404, message=f"Route not found: {self.path}")

            dialect = segments[2].strip().lower()
            self.app.settings.require_enabled_dialect(dialect)
            tail = segments[3:]

            if method == "POST" and tail == ["compile"]:
                doc = self._read_json_body()
                query_text = doc.get("query_text")
                context = doc.get("context", {})
                if not isinstance(query_text, str) or not query_text.strip():
                    raise BridgeError(status_code=400, message="compile request requires query_text string")
                if not isinstance(context, dict):
                    raise BridgeError(status_code=400, message="compile request context must be object")
                compile_result = self.app.backend.compile_query(
                    dialect=dialect,
                    query_text=query_text,
                    context=context,
                )
                self._send_json(200, compile_result.to_dict())
                return

            if method == "POST" and tail == ["execute"]:
                doc = self._read_json_body()
                compile_artifact_id = doc.get("compile_artifact_id")
                query_text = doc.get("query_text")
                options = doc.get("options", {})
                if not isinstance(compile_artifact_id, str) or not compile_artifact_id:
                    raise BridgeError(
                        status_code=400,
                        message="execute request requires compile_artifact_id string",
                    )
                if not isinstance(query_text, str) or not query_text.strip():
                    raise BridgeError(status_code=400, message="execute request requires query_text string")
                if not isinstance(options, dict):
                    raise BridgeError(status_code=400, message="execute request options must be object")
                execute_result = self.app.backend.execute_query(
                    dialect=dialect,
                    compile_artifact_id=compile_artifact_id,
                    query_text=query_text,
                    options=options,
                )
                self._send_json(200, execute_result.to_dict())
                return

            if method == "GET" and tail == ["schemas"]:
                raw_database = query_params.get("database", [])
                database = raw_database[0] if raw_database else None
                schemas = self.app.backend.list_schemas(dialect=dialect, database=database)
                self._send_json(200, {"schemas": schemas})
                return

            if method == "GET" and len(tail) == 3 and tail[0] == "schemas" and tail[2] == "tables":
                schema = tail[1]
                tables = self.app.backend.list_tables(dialect=dialect, schema=schema)
                self._send_json(200, {"tables": tables})
                return

            if method == "GET" and len(tail) == 4 and tail[0] == "schemas" and tail[2] == "tables":
                schema = tail[1]
                table = tail[3]
                table_description = self.app.backend.describe_table(
                    dialect=dialect,
                    schema=schema,
                    table=table,
                )
                self._send_json(200, table_description)
                return

            raise BridgeError(status_code=404, message=f"Route not found: {self.path}")
        except BridgeError as exc:
            self._send_json(exc.status_code, {"error": {"message": exc.message}})
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._send_json(500, {"error": {"message": f"internal bridge error: {exc}"}})

    def _authorize(self) -> None:
        token = self.app.settings.api_token
        if not token:
            return
        header = self.headers.get("Authorization", "")
        if header != f"Bearer {token}":
            raise BridgeError(status_code=401, message="Unauthorized")

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise BridgeError(status_code=400, message="Invalid Content-Length") from exc

        if length < 0:
            raise BridgeError(status_code=400, message="Invalid Content-Length")
        if length > self.app.settings.request_max_bytes:
            raise BridgeError(status_code=413, message="Request body too large")

        payload = self.rfile.read(length) if length else b"{}"
        if not payload:
            return {}

        try:
            decoded = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise BridgeError(status_code=400, message=f"Invalid JSON payload: {exc}") from exc

        if not isinstance(decoded, dict):
            raise BridgeError(status_code=400, message="JSON payload must be an object")
        return decoded

    def _send_json(self, status_code: int, doc: dict[str, Any]) -> None:
        body = json.dumps(doc, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_http_server(
    *,
    app: ScratchBirdBridgeApp,
) -> ThreadingHTTPServer:
    handler_cls = type("ScratchBirdBridgeHandler", (_BridgeHandler,), {"app": app})
    return ThreadingHTTPServer((app.settings.host, app.settings.port), handler_cls)


def run_http_bridge(
    *,
    settings: BridgeSettings | None = None,
    backend: BridgeBackend | None = None,
) -> None:
    runtime_settings = settings or BridgeSettings.from_env()
    runtime_backend = backend or ScratchBirdDriverBackend(runtime_settings)
    app = ScratchBirdBridgeApp(settings=runtime_settings, backend=runtime_backend)
    server = build_http_server(app=app)
    server.serve_forever()


def main() -> None:
    run_http_bridge()
