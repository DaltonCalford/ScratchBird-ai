"""MCP server entrypoint and tool registration for ScratchBird AI."""

from __future__ import annotations

from uuid import uuid4

from .service import ScratchBirdAIService, build_default_service

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - runtime optional dependency
    FastMCP = None


def create_server(service: ScratchBirdAIService | None = None):
    if FastMCP is None:
        raise RuntimeError(
            "MCP runtime not installed. Install optional dependency: pip install .[mcp]"
        )

    svc = service or build_default_service()
    mcp = FastMCP("scratchbird-ai", json_response=True)

    @mcp.tool()
    def get_capabilities() -> dict:
        return svc.get_capabilities()

    @mcp.tool()
    def list_dialects() -> list[str]:
        return svc.list_dialects()

    @mcp.tool()
    def list_schemas(dialect: str, database: str = "") -> list[str]:
        return svc.list_schemas(dialect=dialect, database=database or None)

    @mcp.tool()
    def list_tables(dialect: str, schema: str) -> list[str]:
        return svc.list_tables(dialect=dialect, schema=schema)

    @mcp.tool()
    def describe_table(dialect: str, schema: str, table: str) -> dict:
        return svc.describe_table(dialect=dialect, schema=schema, table=table)

    @mcp.tool()
    def compile_query(dialect: str, query_text: str, context: dict | None = None) -> dict:
        return svc.compile_query(
            dialect=dialect,
            query_text=query_text,
            context=context or {},
        ).to_dict()

    @mcp.tool()
    def execute_compiled(
        compile_artifact_id: str,
        options: dict | None = None,
        mode: str = "read_only",
        approval_token: str = "",
    ) -> dict:
        return svc.execute_compiled(
            compile_artifact_id=compile_artifact_id,
            options=options or {},
            mode=mode,
            approval_token=approval_token or None,
        ).to_dict()

    @mcp.tool()
    def run_query(
        dialect: str,
        query_text: str,
        mode: str = "read_only",
        options: dict | None = None,
        context: dict | None = None,
        approval_token: str = "",
    ) -> dict:
        request_id = f"req_{uuid4().hex}"
        return svc.run_query(
            request_id=request_id,
            dialect=dialect,
            query_text=query_text,
            mode=mode,
            options=options or {},
            context=context or {},
            approval_token=approval_token or None,
        ).to_dict()

    @mcp.tool()
    def explain_query(dialect: str, query_text: str) -> dict:
        return svc.explain_query(dialect=dialect, query_text=query_text)

    @mcp.tool()
    def run_mutation(
        dialect: str,
        query_text: str,
        approval_token: str,
        options: dict | None = None,
        context: dict | None = None,
    ) -> dict:
        request_id = f"req_{uuid4().hex}"
        return svc.run_query(
            request_id=request_id,
            dialect=dialect,
            query_text=query_text,
            mode="mutation_with_approval",
            options=options or {},
            context=context or {},
            approval_token=approval_token,
        ).to_dict()

    return mcp


def main() -> None:
    server = create_server()
    server.run()
