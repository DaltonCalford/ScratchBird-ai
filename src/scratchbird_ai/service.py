"""P0 service layer for MCP tool orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .adapters.base import DialectAdapter
from .adapters.http import HttpJsonClient, make_http_dialect_adapter
from .adapters.mock import make_mock_dialect_adapter
from .capability_matrix import load_capability_matrix
from .contracts import CompileResult, ExecuteResult, QueryResponse
from .policy import PolicyEngine
from .router import DialectRouter
from .settings import RuntimeSettings, load_runtime_settings


@dataclass(slots=True)
class CompileRecord:
    dialect: str
    query_text: str
    statement_kind: str
    sblr_hash: str


class ScratchBirdAIService:
    """Core orchestration service used by MCP tool handlers."""

    def __init__(
        self,
        *,
        router: DialectRouter,
        policy_engine: PolicyEngine,
        adapters: dict[str, DialectAdapter],
        adapter_mode: str = "mock",
    ) -> None:
        self.router = router
        self.policy_engine = policy_engine
        self.adapters = adapters
        self.adapter_mode = adapter_mode
        self._compile_store: dict[str, CompileRecord] = {}

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "service": "scratchbird-ai",
            "version": "0.1.0",
            "query_entrypoint_policy": "parser_compiler_first",
            "adapter_mode": self.adapter_mode,
            "supports": {
                "metadata": True,
                "compile_execute_split": True,
                "read_only_mode": True,
                "mutation_requires_approval": True,
            },
            "matrix_version": self.router.matrix.get("version", "unknown"),
        }

    def list_dialects(self) -> list[str]:
        return self.router.available_dialects()

    def list_schemas(self, dialect: str, database: str | None = None) -> list[str]:
        self.router.require_capability(dialect, "metadata_introspection")
        return self.adapters[dialect].metadata.list_schemas(database)

    def list_tables(self, dialect: str, schema: str) -> list[str]:
        self.router.require_capability(dialect, "metadata_introspection")
        return self.adapters[dialect].metadata.list_tables(schema)

    def describe_table(self, dialect: str, schema: str, table: str) -> dict[str, Any]:
        self.router.require_capability(dialect, "metadata_introspection")
        return self.adapters[dialect].metadata.describe_table(schema, table)

    def compile_query(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any] | None = None,
    ) -> CompileResult:
        self.router.require_capability(dialect, "read_select")

        adapter = self.adapters[dialect]
        compiled = adapter.compiler.compile_query(query_text, context or {})
        compile_artifact_id = f"cmp_{uuid4().hex}"

        self._compile_store[compile_artifact_id] = CompileRecord(
            dialect=dialect,
            query_text=query_text,
            statement_kind=compiled.statement_kind,
            sblr_hash=compiled.sblr_hash,
        )

        return CompileResult(
            compile_artifact_id=compile_artifact_id,
            dialect=dialect,
            statement_kind=(
                "mutation" if compiled.statement_kind == "mutation" else "read"
            ),
            sblr_hash=compiled.sblr_hash,
            diagnostics=compiled.diagnostics,
            warnings=compiled.warnings,
        )

    def execute_compiled(
        self,
        *,
        compile_artifact_id: str,
        options: dict[str, Any] | None = None,
        mode: str = "read_only",
        approval_token: str | None = None,
    ) -> ExecuteResult:
        record = self._compile_store.get(compile_artifact_id)
        if record is None:
            raise KeyError(f"Unknown compile artifact: {compile_artifact_id}")

        is_mutation = record.statement_kind == "mutation"
        self.policy_engine.enforce(
            mode=mode,
            is_mutation=is_mutation,
            approval_token=approval_token,
        )

        required_cap = "write_dml" if is_mutation else "read_select"
        self.router.require_capability(record.dialect, required_cap)

        adapter = self.adapters[record.dialect]
        executed = adapter.executor.execute_compiled(
            compile_artifact_id=compile_artifact_id,
            query_text=record.query_text,
            options=options or {},
        )

        execution_artifact_id = f"exe_{uuid4().hex}"
        return ExecuteResult(
            execution_artifact_id=execution_artifact_id,
            compile_artifact_id=compile_artifact_id,
            rows=executed.rows,
            row_count=len(executed.rows),
            notices=executed.notices,
        )

    def run_query(
        self,
        *,
        request_id: str,
        dialect: str,
        query_text: str,
        mode: str = "read_only",
        options: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        approval_token: str | None = None,
    ) -> QueryResponse:
        compiled = self.compile_query(
            dialect=dialect,
            query_text=query_text,
            context=context,
        )
        executed = self.execute_compiled(
            compile_artifact_id=compiled.compile_artifact_id,
            options=options,
            mode=mode,
            approval_token=approval_token,
        )

        trace_id = f"tr_{uuid4().hex}"
        return QueryResponse(
            request_id=request_id,
            compile_artifact_id=compiled.compile_artifact_id,
            execution_artifact_id=executed.execution_artifact_id,
            result_rows=executed.rows,
            notices=executed.notices,
            trace_id=trace_id,
        )

    def explain_query(self, *, dialect: str, query_text: str) -> dict[str, Any]:
        self.router.require_capability(dialect, "read_select")
        compiled = self.compile_query(dialect=dialect, query_text=query_text, context={})
        return {
            "dialect": dialect,
            "compile_artifact_id": compiled.compile_artifact_id,
            "statement_kind": compiled.statement_kind,
            "sblr_hash": compiled.sblr_hash,
            "warnings": compiled.warnings,
            "explain_note": "P0 scaffold explain output",
        }


def _build_adapters(
    *,
    router: DialectRouter,
    settings: RuntimeSettings,
) -> tuple[dict[str, DialectAdapter], str]:
    mode = settings.normalized_mode()
    adapters: dict[str, DialectAdapter] = {}
    http_client: HttpJsonClient | None = None

    if mode in {"http", "hybrid"}:
        http_client = HttpJsonClient(
            base_url=settings.http_base_url,
            timeout_sec=settings.http_timeout_sec,
            api_token=settings.http_api_token,
        )

    for dialect in router.available_dialects():
        if http_client is not None and settings.should_use_http_for_dialect(dialect):
            adapters[dialect] = make_http_dialect_adapter(dialect=dialect, client=http_client)
        else:
            adapters[dialect] = make_mock_dialect_adapter(dialect)

    return adapters, mode


def build_default_service(settings: RuntimeSettings | None = None) -> ScratchBirdAIService:
    runtime_settings = settings or load_runtime_settings()
    matrix = load_capability_matrix()
    router = DialectRouter(matrix=matrix)
    policy_engine = PolicyEngine()
    adapters, mode = _build_adapters(router=router, settings=runtime_settings)
    return ScratchBirdAIService(
        router=router,
        policy_engine=policy_engine,
        adapters=adapters,
        adapter_mode=mode,
    )
