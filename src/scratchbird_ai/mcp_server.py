"""MCP server entrypoint and tool registration for ScratchBird AI."""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from .service import ScratchBirdAIService, build_default_service
from .tool_schema import map_exception_to_error

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - runtime optional dependency
    FastMCP = None


def _tool_call(
    *,
    tool_name: str,
    payload: dict[str, Any],
    fn: Callable[[], Any],
) -> Any:
    try:
        return fn()
    except Exception as exc:
        return map_exception_to_error(exc, trace_seed={"tool": tool_name, "payload": payload})


def create_server(service: ScratchBirdAIService | None = None):
    if FastMCP is None:
        raise RuntimeError(
            "MCP runtime not installed. Install optional dependency: pip install .[mcp]"
        )

    svc = service or build_default_service()
    mcp = FastMCP("scratchbird-ai", json_response=True)

    @mcp.tool()
    def get_capabilities() -> dict:
        return _tool_call(
            tool_name="get_capabilities",
            payload={},
            fn=lambda: svc.get_capabilities(),
        )

    @mcp.tool()
    def list_dialects() -> Any:
        return _tool_call(
            tool_name="list_dialects",
            payload={},
            fn=lambda: {"dialects": svc.list_dialects()},
        )

    @mcp.tool()
    def list_schemas(dialect: str, database: str = "") -> Any:
        return _tool_call(
            tool_name="list_schemas",
            payload={"dialect": dialect, "database": database},
            fn=lambda: {
                "schemas": svc.list_schemas(dialect=dialect, database=database or None),
            },
        )

    @mcp.tool()
    def list_tables(dialect: str, schema: str) -> Any:
        return _tool_call(
            tool_name="list_tables",
            payload={"dialect": dialect, "schema": schema},
            fn=lambda: {"tables": svc.list_tables(dialect=dialect, schema=schema)},
        )

    @mcp.tool()
    def describe_table(dialect: str, schema: str, table: str) -> Any:
        return _tool_call(
            tool_name="describe_table",
            payload={"dialect": dialect, "schema": schema, "table": table},
            fn=lambda: svc.describe_table(dialect=dialect, schema=schema, table=table),
        )

    @mcp.tool()
    def compile_query(dialect: str, query_text: str, context: dict | None = None) -> Any:
        payload = {
            "dialect": dialect,
            "query_text": query_text,
            "context": context or {},
        }
        return _tool_call(
            tool_name="compile_query",
            payload=payload,
            fn=lambda: svc.compile_query(
                dialect=dialect,
                query_text=query_text,
                context=context or {},
            ).to_dict(),
        )

    @mcp.tool()
    def execute_compiled(
        compile_artifact_id: str,
        options: dict | None = None,
        mode: str = "ai_analysis",
        approval_token: str = "",
    ) -> Any:
        payload = {
            "compile_artifact_id": compile_artifact_id,
            "options": options or {},
            "mode": mode,
            "approval_token_present": bool(approval_token),
        }
        return _tool_call(
            tool_name="execute_compiled",
            payload=payload,
            fn=lambda: svc.execute_compiled(
                compile_artifact_id=compile_artifact_id,
                options=options or {},
                mode=mode,
                approval_token=approval_token or None,
            ).to_dict(),
        )

    @mcp.tool()
    def execute_readonly_query(
        dialect: str,
        query_text: str,
        security_context: dict,
        options: dict | None = None,
        context: dict | None = None,
    ) -> Any:
        request_id = f"req_{uuid4().hex}"
        payload = {
            "request_id": request_id,
            "dialect": dialect,
            "query_text": query_text,
            "security_context": security_context,
            "options": options or {},
            "context": context or {},
        }
        return _tool_call(
            tool_name="execute_readonly_query",
            payload=payload,
            fn=lambda: svc.execute_readonly_query(
                request_id=request_id,
                dialect=dialect,
                query_text=query_text,
                security_context=security_context,
                options=options or {},
                context=context or {},
            ),
        )

    @mcp.tool()
    def execute_mutation(
        dialect: str,
        query_text: str,
        security_context: dict,
        approval_evidence: dict,
        options: dict | None = None,
        context: dict | None = None,
    ) -> Any:
        request_id = f"req_{uuid4().hex}"
        payload = {
            "request_id": request_id,
            "dialect": dialect,
            "query_text": query_text,
            "security_context": security_context,
            "approval_evidence": approval_evidence,
            "options": options or {},
            "context": context or {},
        }
        return _tool_call(
            tool_name="execute_mutation",
            payload=payload,
            fn=lambda: svc.execute_mutation(
                request_id=request_id,
                dialect=dialect,
                query_text=query_text,
                security_context=security_context,
                approval_evidence=approval_evidence,
                options=options or {},
                context=context or {},
            ),
        )

    @mcp.tool()
    def run_query(
        dialect: str,
        query_text: str,
        mode: str = "ai_analysis",
        options: dict | None = None,
        context: dict | None = None,
        approval_token: str = "",
    ) -> Any:
        request_id = f"req_{uuid4().hex}"
        payload = {
            "request_id": request_id,
            "dialect": dialect,
            "query_text": query_text,
            "mode": mode,
            "options": options or {},
            "context": context or {},
            "approval_token_present": bool(approval_token),
        }
        return _tool_call(
            tool_name="run_query",
            payload=payload,
            fn=lambda: svc.run_query(
                request_id=request_id,
                dialect=dialect,
                query_text=query_text,
                mode=mode,
                options=options or {},
                context=context or {},
                approval_token=approval_token or None,
            ).to_dict(),
        )

    @mcp.tool()
    def run_mutation(
        dialect: str,
        query_text: str,
        approval_token: str,
        options: dict | None = None,
        context: dict | None = None,
    ) -> Any:
        security_context = {}
        if isinstance(context, dict):
            raw = context.get("security_context", context)
            if isinstance(raw, dict):
                security_context = raw
        request_id = f"req_{uuid4().hex}"
        payload = {
            "request_id": request_id,
            "dialect": dialect,
            "query_text": query_text,
            "security_context": security_context,
            "options": options or {},
            "context": context or {},
            "approval_token_present": bool(approval_token),
        }
        return _tool_call(
            tool_name="run_mutation",
            payload=payload,
            fn=lambda: svc.execute_mutation(
                request_id=request_id,
                dialect=dialect,
                query_text=query_text,
                security_context=security_context,
                approval_evidence={"approval_token": approval_token},
                options=options or {},
                context=context or {},
            ),
        )

    @mcp.tool()
    def explain_query(
        dialect: str,
        query_text: str,
        security_context: dict | None = None,
        context: dict | None = None,
    ) -> Any:
        payload = {
            "dialect": dialect,
            "query_text": query_text,
            "security_context": security_context or {},
            "context": context or {},
        }
        return _tool_call(
            tool_name="explain_query",
            payload=payload,
            fn=lambda: svc.introspect_plan(
                dialect=dialect,
                query_text=query_text,
                security_context=security_context or {},
            ),
        )

    @mcp.tool()
    def vector_search(
        index_id: str,
        query_embedding: list[float],
        top_k: int,
        security_context: dict,
        filters: dict | None = None,
        include_vectors: bool = False,
    ) -> Any:
        payload = {
            "index_id": index_id,
            "top_k": top_k,
            "security_context": security_context,
            "filters": filters or {},
            "include_vectors": include_vectors,
        }
        return _tool_call(
            tool_name="vector_search",
            payload=payload,
            fn=lambda: svc.vector_search(
                index_id=index_id,
                query_embedding=query_embedding,
                top_k=top_k,
                security_context=security_context,
                filters=filters or {},
                include_vectors=include_vectors,
            ),
        )

    @mcp.tool()
    def hybrid_search(
        dialect: str,
        query_text: str,
        query_embedding: list[float],
        vector_index_id: str,
        top_k: int,
        security_context: dict,
        sql_filter: dict | None = None,
        weights: dict | None = None,
        options: dict | None = None,
    ) -> Any:
        payload = {
            "dialect": dialect,
            "query_text": query_text,
            "vector_index_id": vector_index_id,
            "top_k": top_k,
            "security_context": security_context,
            "sql_filter": sql_filter or {},
            "weights": weights or {},
            "options": options or {},
        }
        return _tool_call(
            tool_name="hybrid_search",
            payload=payload,
            fn=lambda: svc.hybrid_search(
                dialect=dialect,
                query_text=query_text,
                query_embedding=query_embedding,
                vector_index_id=vector_index_id,
                top_k=top_k,
                security_context=security_context,
                sql_filter=sql_filter or {},
                weights=weights or {},
                options=options or {},
            ),
        )

    return mcp


def main() -> None:
    server = create_server()
    server.run()
