"""P0 service layer for MCP tool orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapters.base import DialectAdapter
from .adapters.http import HttpJsonClient, make_http_dialect_adapter
from .adapters.mock import make_mock_dialect_adapter
from .audit_bundle import create_audit_bundle, security_context_hash
from .capability_matrix import load_capability_matrix
from .compatibility import build_compatibility_manifest, negotiate_compatibility
from .contracts import CompileResult, ExecuteResult, QueryResponse
from .deterministic import deterministic_id
from .interface_profiles import INTERFACE_COMPATIBILITY_VERSION, get_interface_profiles
from .operation_streams import LongRunningOperationManager
from .plan_introspection import build_plan_response
from .policy import PolicyDeniedError, PolicyDecision, PolicyEngine
from .provider_profiles import get_provider_profile_descriptor, get_provider_profiles
from .remote_sessions import RemoteSessionManager
from .retrieval import InMemoryRetrievalStore
from .router import DialectRouter
from .settings import RuntimeSettings, load_runtime_settings
from .tool_schema import (
    TOOL_DESCRIPTOR_VERSION,
    ToolContractError,
    TOOL_SCHEMA_VERSION,
    get_tool_descriptors,
    map_exception_to_error,
    normalize_tool_invocation,
    normalize_tool_response,
    require_security_context,
    validate_options,
)


@dataclass(slots=True)
class CompileRecord:
    dialect: str
    query_text: str
    statement_kind: str
    sblr_hash: str
    context: dict[str, Any]
    security_context: dict[str, Any]
    security_context_hash: str


class ScratchBirdAIService:
    """Core orchestration service used by MCP tool handlers."""

    def __init__(
        self,
        *,
        router: DialectRouter,
        policy_engine: PolicyEngine,
        adapters: dict[str, DialectAdapter],
        adapter_mode: str = "mock",
        retrieval_store: InMemoryRetrievalStore | None = None,
        remote_session_manager: RemoteSessionManager | None = None,
        long_running_manager: LongRunningOperationManager | None = None,
    ) -> None:
        self.router = router
        self.policy_engine = policy_engine
        self.adapters = adapters
        self.adapter_mode = adapter_mode
        self._compile_store: dict[str, CompileRecord] = {}
        self._execution_attempts: dict[str, int] = {}
        self._audit_store: list[dict[str, Any]] = []
        self._retrieval = retrieval_store or InMemoryRetrievalStore()
        self._remote_sessions = remote_session_manager or RemoteSessionManager(auth_token=None)
        self._long_running = long_running_manager or LongRunningOperationManager()

    def get_capabilities(self) -> dict[str, Any]:
        interface_profiles = get_interface_profiles()
        return {
            "service": "scratchbird-ai",
            "version": "0.1.0",
            "query_entrypoint_policy": "parser_compiler_first",
            "adapter_mode": self.adapter_mode,
            "tool_schema_version": TOOL_SCHEMA_VERSION,
            "tool_descriptor_version": TOOL_DESCRIPTOR_VERSION,
            "compatibility_version": INTERFACE_COMPATIBILITY_VERSION,
            "compatibility_manifest_version": INTERFACE_COMPATIBILITY_VERSION,
            "interface_profiles": interface_profiles,
            "provider_profiles": get_provider_profiles(),
            "supports": {
                "metadata": True,
                "compile_execute_split": True,
                "read_only_mode": True,
                "mutation_requires_approval": True,
                "compatibility_negotiation": True,
                "retrieval_catalog": True,
                "provider_generated_embeddings": True,
                "structured_output_modes": ["none", "json_object", "json_schema"],
                "vector_search": True,
                "hybrid_search": True,
                "canonical_tools": [
                    "get_capabilities",
                    "get_tool_descriptors",
                    "get_provider_profiles",
                    "get_compatibility_manifest",
                    "negotiate_compatibility",
                    "list_dialects",
                    "list_schemas",
                    "list_tables",
                    "describe_table",
                    "execute_readonly_query",
                    "execute_mutation",
                    "explain_query",
                    "create_vector_index",
                    "list_vector_indexes",
                    "describe_vector_index",
                    "add_embeddings",
                    "add_generated_embeddings",
                    "delete_embeddings",
                    "reindex_vector_index",
                    "delete_vector_index",
                    "vector_search",
                    "hybrid_search",
                ],
                "canonical_execution_modes": [
                    "ai_analysis",
                    "ai_mutation_pending_approval",
                    "ai_mutation_approved",
                ],
                "legacy_mode_aliases": {
                    "read_only": "ai_analysis",
                    "mutation_with_approval": "ai_mutation_pending_approval",
                },
            },
            "matrix_version": self.router.matrix.get("version", "unknown"),
        }

    def get_tool_descriptors(self) -> dict[str, Any]:
        return {"tools": get_tool_descriptors()}

    def get_provider_profiles(self) -> dict[str, Any]:
        return {"profiles": get_provider_profiles()}

    def get_compatibility_manifest(self) -> dict[str, Any]:
        return build_compatibility_manifest(
            adapter_mode=self.adapter_mode,
            matrix_version=str(self.router.matrix.get("version", "unknown")),
        )

    def create_vector_index(
        self,
        *,
        index_id: str,
        dimension: int,
        security_context: dict[str, Any],
        profile_id: str = "client_supplied_embeddings_v0",
    ) -> dict[str, Any]:
        return self._retrieval.create_index(
            index_id=index_id,
            dimension=dimension,
            security_context=security_context,
            profile_id=profile_id,
        )

    def list_vector_indexes(
        self,
        *,
        security_context: dict[str, Any],
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        return self._retrieval.list_indexes(
            security_context=security_context,
            include_deleted=include_deleted,
        )

    def describe_vector_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.describe_index(
            index_id=index_id,
            security_context=security_context,
        )

    def negotiate_compatibility(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return negotiate_compatibility(
            request,
            adapter_mode=self.adapter_mode,
            matrix_version=str(self.router.matrix.get("version", "unknown")),
        )

    def open_remote_session(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._remote_sessions.open_session(
            request,
            capability_advertisement=self._remote_capabilities(),
        )

    def invoke_remote_tool(
        self,
        *,
        session_id: str,
        request_id: str,
        method: str,
        params: dict[str, Any] | None = None,
        client_operation_timeout_ms: int | None = None,
        stream_requested: bool = False,
        allow_background_execution: bool = False,
        cancellation_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            session = self._remote_sessions.require_session(session_id)
            invocation_payload = self._build_remote_tool_payload(
                session=session,
                session_id=session_id,
                request_id=request_id,
                method=method,
                params=params,
                client_operation_timeout_ms=client_operation_timeout_ms,
            )
            if stream_requested:
                if session.negotiated_transport != "https_sse_server_stream":
                    raise ToolContractError(
                        error_code="E_STREAM_NOT_SUPPORTED",
                        message=(
                            "stream_requested requires negotiated transport "
                            "https_sse_server_stream"
                        ),
                        policy_rule_id="REMOTE-SESSION-STREAM-001",
                    )
                operation = self._long_running.create_operation(
                    session_id=session_id,
                    request_id=request_id,
                    method=method,
                    trace_id=deterministic_id(
                        "tr",
                        {
                            "session_id": session_id,
                            "request_id": request_id,
                            "method": method,
                            "stream_requested": True,
                        },
                    ),
                    security_context=session.security_context,
                    cancellation_token=cancellation_token,
                )
                self._long_running.mark_running(
                    operation.operation_id,
                    payload={
                        "method": method,
                        "allow_background_execution": bool(allow_background_execution),
                    },
                )
                envelope = self.invoke_tool(
                    payload=invocation_payload,
                    interface_profile_id="streaming_async_v0",
                )
                for notice in envelope["notices"]:
                    self._long_running.record_notice(
                        operation.operation_id,
                        notice=notice,
                    )
                if envelope["status"] == "success":
                    self._long_running.complete(
                        operation.operation_id,
                        payload={
                            "result": envelope["result"],
                            "structured_output": envelope["structured_output"],
                        },
                    )
                    operation_events = self._long_running.get_events(
                        operation_id=operation.operation_id,
                        requested_by=session.security_context,
                    )
                    return {
                        "session_id": session_id,
                        "request_id": request_id,
                        "status": "success",
                        "trace_id": operation.trace_id,
                        "result": None,
                        "error": None,
                        "operation_id": operation.operation_id,
                        "operation_state": operation_events["operation_state"],
                        "stream_channel": operation.stream_channel,
                        "resumable": operation.resumable,
                        "continuation_token": operation.continuation_token,
                        "notices": [],
                    }
                self._long_running.fail(
                    operation.operation_id,
                    payload={"error": envelope["error"]},
                )
                return {
                    "session_id": session_id,
                    "request_id": request_id,
                    "status": "error",
                    "trace_id": operation.trace_id,
                    "result": None,
                    "error": envelope["error"],
                    "operation_id": operation.operation_id,
                    "operation_state": "failed",
                    "stream_channel": operation.stream_channel,
                    "resumable": operation.resumable,
                    "continuation_token": operation.continuation_token,
                    "notices": [],
                }

            envelope = self.invoke_tool(
                payload=invocation_payload,
                interface_profile_id="mcp_remote_v0",
            )
            return {
                "session_id": session_id,
                "request_id": request_id,
                "status": envelope["status"],
                "trace_id": envelope["trace_id"],
                "result": envelope["result"],
                "error": envelope["error"],
                "operation_id": None,
                "operation_state": "completed" if envelope["status"] == "success" else "failed",
                "stream_channel": None,
                "resumable": False,
                "continuation_token": None,
                "notices": envelope["notices"],
            }
        except Exception as exc:
            error = map_exception_to_error(
                exc,
                trace_seed={
                    "session_id": session_id,
                    "request_id": request_id,
                    "method": method,
                    "remote_invocation_error": True,
                },
            )
            return {
                "session_id": session_id,
                "request_id": request_id,
                "status": "error",
                "trace_id": error["trace_id"],
                "result": None,
                "error": error,
                "operation_id": None,
                "operation_state": "failed",
                "stream_channel": None,
                "resumable": False,
                "continuation_token": None,
                "notices": [],
            }

    def close_remote_session(self, *, session_id: str, request_id: str | None = None) -> dict[str, Any]:
        return self._remote_sessions.close_session(session_id=session_id, request_id=request_id)

    def poll_remote_operation(
        self,
        *,
        session_id: str,
        operation_id: str,
        continuation_token: str | None = None,
    ) -> dict[str, Any]:
        try:
            session = self._remote_sessions.require_session(session_id)
            events = self._long_running.get_events(
                operation_id=operation_id,
                requested_by=session.security_context,
                continuation_token=continuation_token,
            )
            return {
                "session_id": session_id,
                "operation_id": operation_id,
                "request_id": events["request_id"],
                "trace_id": events["trace_id"],
                "operation_state": events["operation_state"],
                "stream_channel": events["stream_channel"],
                "resumable": events["resumable"],
                "continuation_token": events["continuation_token"],
                "terminal": events["terminal"],
                "events": events["events"],
                "error": None,
            }
        except Exception as exc:
            error = map_exception_to_error(
                exc,
                trace_seed={
                    "session_id": session_id,
                    "operation_id": operation_id,
                    "poll_remote_operation_error": True,
                },
            )
            return {
                "session_id": session_id,
                "operation_id": operation_id,
                "request_id": None,
                "trace_id": error["trace_id"],
                "operation_state": "failed",
                "stream_channel": None,
                "resumable": False,
                "continuation_token": continuation_token,
                "terminal": True,
                "events": [],
                "error": error,
            }

    def cancel_remote_operation(
        self,
        *,
        session_id: str,
        operation_id: str,
        request_id: str,
        reason: str,
    ) -> dict[str, Any]:
        try:
            session = self._remote_sessions.require_session(session_id)
        except Exception:
            return {
                "session_id": session_id,
                "operation_id": operation_id,
                "request_id": request_id,
                "status": "session_invalid",
                "operation_state": "unknown",
                "trace_id": deterministic_id(
                    "tr",
                    {
                        "session_id": session_id,
                        "operation_id": operation_id,
                        "request_id": request_id,
                        "cancel_session_invalid": True,
                    },
                ),
                "continuation_token": None,
            }
        cancellation = self._long_running.cancel(
            operation_id=operation_id,
            request_id=request_id,
            reason=reason,
            requested_by=session.security_context,
        )
        cancellation["session_id"] = session_id
        return cancellation

    def _build_remote_tool_payload(
        self,
        *,
        session: Any,
        session_id: str,
        request_id: str,
        method: str,
        params: dict[str, Any] | None,
        client_operation_timeout_ms: int | None,
    ) -> dict[str, Any]:
        tool_arguments = dict(params or {})
        for reserved_key in (
            "call_id",
            "client_capabilities",
            "interface_profile_id",
            "method",
            "request_id",
            "requested_transport",
            "session_id",
        ):
            tool_arguments.pop(reserved_key, None)
        session_security_context = dict(session.security_context)
        tool_arguments["security_context"] = session_security_context
        raw_context = tool_arguments.get("context", {})
        context = dict(raw_context) if isinstance(raw_context, dict) else {}
        context["security_context"] = dict(session_security_context)
        tool_arguments["context"] = context

        session_capabilities = dict(session.client_capabilities)
        session_capabilities.update(
            {
                "interface_profile_id": session.interface_profile_id,
                "requested_profile_version": session.negotiated_protocol_version,
                "requested_transport": session.negotiated_transport,
            }
        )
        if client_operation_timeout_ms is not None:
            options = tool_arguments.get("options", {})
            if not isinstance(options, dict):
                options = {}
            options.setdefault("timeout_ms", int(client_operation_timeout_ms))
            tool_arguments["options"] = options
        return {
            "request_id": request_id,
            "call_id": deterministic_id(
                "call",
                {"session_id": session_id, "request_id": request_id, "method": method},
            ),
            "tool_name": method,
            "arguments": tool_arguments,
            "client_capabilities": session_capabilities,
            "security_context": session_security_context,
        }

    def invoke_tool(
        self,
        *,
        payload: dict[str, Any],
        interface_profile_id: str = "service_internal_v0",
        provider_profile_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_tool_invocation(
            payload=payload,
            interface_profile_id=interface_profile_id,
            provider_profile_id=provider_profile_id,
        )
        return self._invoke_normalized_tool(normalized)

    def invoke_provider_tool(
        self,
        *,
        payload: dict[str, Any],
        provider_profile_id: str,
    ) -> dict[str, Any]:
        request_id = str(payload.get("request_id", "")).strip() or deterministic_id(
            "req",
            {
                "interface_profile_id": "provider_tool_calling_v0",
                "provider_profile_id": provider_profile_id,
                "payload": payload,
            },
        )
        try:
            descriptor = get_provider_profile_descriptor(provider_profile_id)
        except KeyError:
            error = map_exception_to_error(
                ToolContractError(
                    error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
                    message=f"unknown provider profile: {provider_profile_id}",
                    policy_rule_id="PROVIDER-PROFILE-001",
                ),
                trace_seed={
                    "request_id": request_id,
                    "provider_profile_id": provider_profile_id,
                    "provider_profile_error": True,
                },
            )
            return {
                "request_id": request_id,
                "interface_profile_id": "provider_tool_calling_v0",
                "provider_profile_id": provider_profile_id,
                "trace_id": error["trace_id"],
                "status": "error",
                "result": None,
                "structured_output": None,
                "error": error,
                "notices": [],
            }

        if descriptor.state != "implemented":
            error = map_exception_to_error(
                ToolContractError(
                    error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
                    message=f"provider profile is not implemented: {provider_profile_id}",
                    policy_rule_id="PROVIDER-PROFILE-002",
                ),
                trace_seed={
                    "request_id": request_id,
                    "provider_profile_id": provider_profile_id,
                    "provider_profile_error": True,
                },
            )
            return {
                "request_id": request_id,
                "interface_profile_id": "provider_tool_calling_v0",
                "provider_profile_id": provider_profile_id,
                "trace_id": error["trace_id"],
                "status": "error",
                "result": None,
                "structured_output": None,
                "error": error,
                "notices": [],
            }

        envelope = self.invoke_tool(
            payload=payload,
            interface_profile_id="provider_tool_calling_v0",
            provider_profile_id=provider_profile_id,
        )
        return {
            "request_id": envelope["request_id"],
            "interface_profile_id": envelope["interface_profile_id"],
            "provider_profile_id": provider_profile_id,
            "trace_id": envelope["trace_id"],
            "status": envelope["status"],
            "result": envelope["result"],
            "structured_output": envelope["structured_output"],
            "error": envelope["error"],
            "notices": envelope["notices"],
        }

    def list_audit_bundles(self, *, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(limit, 1000))
        return self._audit_store[-bounded:]

    def latest_audit_bundle(self) -> dict[str, Any] | None:
        if not self._audit_store:
            return None
        return self._audit_store[-1]

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
        query_context = context or {}
        _validate_compatibility_context(
            self,
            query_context,
            default_profile_id="service_internal_v0",
            default_transport="in_process",
        )
        security_context = _extract_security_context(query_context)
        sec_hash = security_context_hash(security_context)
        compiled = adapter.compiler.compile_query(query_text, query_context)

        normalized_query = " ".join(query_text.split())
        compile_artifact_id = deterministic_id(
            "cmp",
            {
                "dialect": dialect,
                "normalized_query_text": normalized_query,
                "security_context_hash": sec_hash,
                "context": query_context,
            },
        )

        statement_kind = compiled.statement_kind
        if statement_kind not in {"read", "mutation", "unknown"}:
            statement_kind = "unknown"

        self._compile_store[compile_artifact_id] = CompileRecord(
            dialect=dialect,
            query_text=query_text,
            statement_kind=statement_kind,
            sblr_hash=compiled.sblr_hash,
            context=query_context,
            security_context=security_context,
            security_context_hash=sec_hash,
        )

        return CompileResult(
            compile_artifact_id=compile_artifact_id,
            dialect=dialect,
            statement_kind=statement_kind,
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
        prevalidated_decision: PolicyDecision | None = None,
    ) -> ExecuteResult:
        record = self._compile_store.get(compile_artifact_id)
        if record is None:
            raise KeyError(f"Unknown compile artifact: {compile_artifact_id}")

        is_mutation = record.statement_kind != "read"
        opts = validate_options(options)

        decision = prevalidated_decision
        if decision is None:
            decision = self.policy_engine.enforce(
                mode=mode,
                is_mutation=is_mutation,
                approval_token=approval_token,
                options=opts,
                tenant_id=record.security_context.get("tenant_id"),
                actor_id=record.security_context.get("actor_id"),
                statement_hash=record.sblr_hash,
            )
        elif not decision.allowed:
            raise PolicyDeniedError(
                rule_id=decision.rule_id,
                reason=decision.reason,
                error_code=decision.error_code or "E_POLICY_DENY",
                canonical_mode=decision.canonical_mode,
            )

        if decision.normalized_options:
            opts = dict(decision.normalized_options)
        if "max_rows" in opts and "limit" not in opts:
            opts["limit"] = int(opts["max_rows"])

        required_cap = "write_dml" if is_mutation else "read_select"
        self.router.require_capability(record.dialect, required_cap)

        adapter = self.adapters[record.dialect]
        executed = adapter.executor.execute_compiled(
            compile_artifact_id=compile_artifact_id,
            query_text=record.query_text,
            options=opts,
        )

        attempt_index = self._execution_attempts.get(compile_artifact_id, 0) + 1
        self._execution_attempts[compile_artifact_id] = attempt_index
        execution_artifact_id = deterministic_id(
            "exe",
            {
                "compile_artifact_id": compile_artifact_id,
                "options": opts,
                "execution_mode": decision.canonical_mode,
                "attempt_index": attempt_index,
            },
        )
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
        approval_evidence: dict[str, Any] | None = None,
    ) -> QueryResponse:
        query_context = dict(context or {})
        try:
            security_context = require_security_context(query_context)
        except ToolContractError as exc:
            trace_id = deterministic_id(
                "tr",
                {
                    "request_id": request_id,
                    "error_code": exc.error_code,
                    "rule": exc.policy_rule_id,
                },
            )
            bundle = create_audit_bundle(
                trace_id=trace_id,
                request_id=request_id,
                tenant_id="unknown",
                actor_id="unknown",
                dialect=dialect,
                execution_mode="ai_analysis",
                sql_text_normalized=" ".join(query_text.split()),
                compile_artifact_id=deterministic_id("cmp", {"request_id": request_id, "invalid": True}),
                execution_artifact_id=None,
                plan_json={"operator_tree": {}, "rls_visibility": {"applied": False, "policy_ids": []}},
                plan_hash=deterministic_id("plan", {"request_id": request_id, "invalid": True}).removeprefix("plan_"),
                policy_decision="deny",
                policy_rule_id=exc.policy_rule_id or "SECURITY-CONTEXT-001",
                security_context={"tenant_id": "", "actor_id": "", "roles": [], "context_version": 1},
                approval_id=None,
                approval_token=approval_token,
                error_code=exc.error_code,
                statement_kind="unknown",
                sblr_hash="",
            )
            self._audit_store.append(bundle)
            raise PolicyDeniedError(
                rule_id=exc.policy_rule_id or "SECURITY-CONTEXT-001",
                reason=exc.message,
                error_code=exc.error_code,
                canonical_mode="ai_analysis",
            ) from None

        query_context["security_context"] = security_context
        validated_options = validate_options(options)
        resolved_approval_token = _resolve_approval_token(
            approval_token=approval_token,
            approval_evidence=approval_evidence,
        )

        try:
            compiled = self.compile_query(
                dialect=dialect,
                query_text=query_text,
                context=query_context,
            )
        except ToolContractError as exc:
            trace_id = deterministic_id(
                "tr",
                {
                    "request_id": request_id,
                    "error_code": exc.error_code,
                    "rule": exc.policy_rule_id,
                    "compatibility_denied": True,
                },
            )
            bundle = create_audit_bundle(
                trace_id=trace_id,
                request_id=request_id,
                tenant_id=security_context.get("tenant_id", "unknown"),
                actor_id=security_context.get("actor_id", "unknown"),
                dialect=dialect,
                execution_mode="ai_analysis",
                sql_text_normalized=" ".join(query_text.split()),
                compile_artifact_id=deterministic_id("cmp", {"request_id": request_id, "blocked": True}),
                execution_artifact_id=None,
                plan_json={"operator_tree": {}, "rls_visibility": {"applied": False, "policy_ids": []}},
                plan_hash=deterministic_id("plan", {"request_id": request_id, "blocked": True}).removeprefix("plan_"),
                policy_decision="deny",
                policy_rule_id=exc.policy_rule_id or "COMPATIBILITY-NEGOTIATION-001",
                security_context=security_context,
                approval_id=None,
                approval_token=resolved_approval_token,
                error_code=exc.error_code,
                statement_kind="unknown",
                sblr_hash="",
            )
            self._audit_store.append(bundle)
            raise
        record = self._compile_store[compiled.compile_artifact_id]
        is_mutation = compiled.statement_kind != "read"

        try:
            decision = self.policy_engine.enforce(
                mode=mode,
                is_mutation=is_mutation,
                approval_token=resolved_approval_token,
                options=validated_options,
                tenant_id=security_context.get("tenant_id"),
                actor_id=security_context.get("actor_id"),
                statement_hash=compiled.sblr_hash,
            )
            opts = dict(decision.normalized_options or validated_options)
            executed = self.execute_compiled(
                compile_artifact_id=compiled.compile_artifact_id,
                options=opts,
                mode=mode,
                approval_token=resolved_approval_token,
                prevalidated_decision=decision,
            )
            trace_id = deterministic_id(
                "tr",
                {
                    "request_id": request_id,
                    "compile_artifact_id": compiled.compile_artifact_id,
                    "execution_artifact_id": executed.execution_artifact_id,
                },
            )
            response = QueryResponse(
                request_id=request_id,
                compile_artifact_id=compiled.compile_artifact_id,
                execution_artifact_id=executed.execution_artifact_id,
                result_rows=executed.rows,
                row_count=executed.row_count,
                notices=executed.notices,
                trace_id=trace_id,
            )

            plan_info = self._build_plan_info(
                dialect=dialect,
                query_text=query_text,
                security_context=security_context,
                operator_type=("Mutation" if is_mutation else "Read"),
            )
            approval_id = _resolve_approval_id(
                approval_evidence=approval_evidence,
                approval_token=resolved_approval_token,
                compile_artifact_id=compiled.compile_artifact_id,
            )
            bundle = create_audit_bundle(
                trace_id=trace_id,
                request_id=request_id,
                tenant_id=security_context.get("tenant_id", "unknown"),
                actor_id=security_context.get("actor_id", "unknown"),
                dialect=dialect,
                execution_mode=decision.canonical_mode,
                sql_text_normalized=" ".join(query_text.split()),
                compile_artifact_id=compiled.compile_artifact_id,
                execution_artifact_id=executed.execution_artifact_id,
                plan_json=plan_info,
                plan_hash=plan_info["plan_hash"],
                policy_decision="allow",
                policy_rule_id=decision.rule_id,
                security_context=security_context,
                cluster_epoch=int(query_context.get("cluster_epoch", 0) or 0),
                approval_id=approval_id,
                approval_token=resolved_approval_token,
                error_code=None,
                statement_kind=compiled.statement_kind,
                sblr_hash=compiled.sblr_hash,
            )
            self._audit_store.append(bundle)
            return response
        except PolicyDeniedError as exc:
            trace_id = deterministic_id(
                "tr",
                {
                    "request_id": request_id,
                    "compile_artifact_id": compiled.compile_artifact_id,
                    "denied": True,
                    "rule": exc.rule_id,
                },
            )
            plan_info = self._build_plan_info(
                dialect=dialect,
                query_text=query_text,
                security_context=security_context,
                operator_type=("DeniedMutation" if is_mutation else "DeniedRead"),
            )
            bundle = create_audit_bundle(
                trace_id=trace_id,
                request_id=request_id,
                tenant_id=security_context.get("tenant_id", "unknown"),
                actor_id=security_context.get("actor_id", "unknown"),
                dialect=dialect,
                execution_mode=exc.canonical_mode,
                sql_text_normalized=" ".join(query_text.split()),
                compile_artifact_id=compiled.compile_artifact_id,
                execution_artifact_id=None,
                plan_json=plan_info,
                plan_hash=plan_info["plan_hash"],
                policy_decision="deny",
                policy_rule_id=exc.rule_id,
                security_context=security_context,
                cluster_epoch=int(query_context.get("cluster_epoch", 0) or 0),
                approval_id=(approval_evidence or {}).get("approval_id") if isinstance(approval_evidence, dict) else None,
                approval_token=resolved_approval_token,
                error_code=exc.error_code,
                statement_kind=compiled.statement_kind,
                sblr_hash=compiled.sblr_hash,
            )
            self._audit_store.append(bundle)
            raise

    def execute_readonly_query(
        self,
        *,
        request_id: str,
        dialect: str,
        query_text: str,
        security_context: dict[str, Any],
        options: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query_context = dict(context or {})
        query_context["security_context"] = require_security_context(
            {"security_context": security_context}
        )
        response = self.run_query(
            request_id=request_id,
            dialect=dialect,
            query_text=query_text,
            mode="ai_analysis",
            options=options,
            context=query_context,
            approval_token=None,
        )
        return {
            "compile_artifact_id": response.compile_artifact_id,
            "execution_artifact_id": response.execution_artifact_id,
            "result_rows": response.result_rows,
            "row_count": response.row_count,
            "notices": response.notices,
            "trace_id": response.trace_id,
        }

    def execute_mutation(
        self,
        *,
        request_id: str,
        dialect: str,
        query_text: str,
        security_context: dict[str, Any],
        approval_evidence: dict[str, Any],
        options: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(approval_evidence, dict):
            raise ToolContractError(
                error_code="E_APPROVAL_INVALID",
                message="approval_evidence must be an object",
                policy_rule_id="MODE-APPROVAL-001",
            )
        query_context = dict(context or {})
        query_context["security_context"] = require_security_context(
            {"security_context": security_context}
        )
        response = self.run_query(
            request_id=request_id,
            dialect=dialect,
            query_text=query_text,
            mode="ai_mutation_approved",
            options=options,
            context=query_context,
            approval_token=_resolve_approval_token(
                approval_token=None,
                approval_evidence=approval_evidence,
            ),
            approval_evidence=approval_evidence,
        )
        return {
            "compile_artifact_id": response.compile_artifact_id,
            "execution_artifact_id": response.execution_artifact_id,
            "affected_rows": response.row_count,
            "notices": response.notices,
            "trace_id": response.trace_id,
        }

    def introspect_plan(
        self,
        *,
        dialect: str,
        security_context: dict[str, Any],
        query_text: str | None = None,
        compile_artifact_id: str | None = None,
    ) -> dict[str, Any]:
        _ = require_security_context({"security_context": security_context})
        provided = [bool(query_text), bool(compile_artifact_id)]
        if sum(1 for flag in provided if flag) != 1:
            raise ToolContractError(
                error_code="E_INVALID_ARGUMENT",
                message="exactly one of query_text or compile_artifact_id is required",
            )

        if query_text is not None:
            compiled = self.compile_query(
                dialect=dialect,
                query_text=query_text,
                context={"security_context": security_context},
            )
            compile_id = compiled.compile_artifact_id
            statement_kind = compiled.statement_kind
            normalized_query = query_text
        else:
            assert compile_artifact_id is not None
            record = self._compile_store.get(compile_artifact_id)
            if record is None:
                raise KeyError(f"Unknown compile artifact: {compile_artifact_id}")
            compile_id = compile_artifact_id
            statement_kind = record.statement_kind
            normalized_query = record.query_text

        plan = self._build_plan_info(
            dialect=dialect,
            query_text=normalized_query,
            security_context=security_context,
            operator_type=("Mutation" if statement_kind != "read" else "Read"),
        )
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "introspect_plan",
                "compile_artifact_id": compile_id,
                "plan_hash": plan["plan_hash"],
            },
        )
        return {
            "compile_artifact_id": compile_id,
            "plan_hash": plan["plan_hash"],
            "plan_version": plan["plan_version"],
            "operator_tree": plan["operator_tree"],
            "rls_visibility": plan["rls_visibility"],
            "estimated_cost": plan["estimated_cost"],
            "trace_id": trace_id,
        }

    def explain_query(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        security_context = _extract_security_context(context or {})
        if not security_context.get("tenant_id") or not security_context.get("actor_id"):
            security_context = {
                "tenant_id": "system",
                "actor_id": "system",
                "roles": ["system"],
                "session_id": "system",
                "context_version": 1,
            }
        return self.introspect_plan(
            dialect=dialect,
            security_context=security_context,
            query_text=query_text,
        )

    def add_embeddings(
        self,
        *,
        index_id: str,
        dimension: int,
        records: list[dict[str, Any]],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.add_embeddings(
            index_id=index_id,
            dimension=dimension,
            records=records,
            security_context=security_context,
        )

    def add_generated_embeddings(
        self,
        *,
        index_id: str,
        dimension: int,
        records: list[dict[str, Any]],
        provider_config: dict[str, Any],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.add_generated_embeddings(
            index_id=index_id,
            dimension=dimension,
            records=records,
            provider_config=provider_config,
            security_context=security_context,
        )

    def delete_embeddings(
        self,
        *,
        index_id: str,
        vector_ids: list[str],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.delete_embeddings(
            index_id=index_id,
            vector_ids=vector_ids,
            security_context=security_context,
        )

    def reindex_vector_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.reindex_index(
            index_id=index_id,
            security_context=security_context,
        )

    def delete_vector_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._retrieval.delete_index(
            index_id=index_id,
            security_context=security_context,
        )

    def vector_search(
        self,
        *,
        index_id: str,
        query_embedding: list[float],
        top_k: int,
        security_context: dict[str, Any],
        filters: dict[str, Any] | None = None,
        include_vectors: bool = False,
    ) -> dict[str, Any]:
        return self._retrieval.vector_search(
            index_id=index_id,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
            include_vectors=include_vectors,
            security_context=security_context,
        )

    def hybrid_search(
        self,
        *,
        dialect: str,
        query_text: str,
        query_embedding: list[float],
        vector_index_id: str,
        top_k: int,
        security_context: dict[str, Any],
        sql_filter: dict[str, Any] | None = None,
        weights: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = validate_options(options)
        return self._retrieval.hybrid_search(
            dialect=dialect,
            query_text=query_text,
            query_embedding=query_embedding,
            vector_index_id=vector_index_id,
            sql_filter=sql_filter,
            weights=weights,
            top_k=top_k,
            security_context=security_context,
        )

    def _invoke_normalized_tool(self, normalized: dict[str, Any]) -> dict[str, Any]:
        tool_name = str(normalized["tool_name"])
        arguments = dict(normalized.get("arguments", {}))
        request_id = str(normalized["request_id"])
        call_id = str(normalized["call_id"])
        interface_profile_id = str(normalized["interface_profile_id"])
        try:
            result = self._dispatch_tool_call(
                tool_name=tool_name,
                request_id=request_id,
                arguments=arguments,
                normalized=normalized,
            )
            trace_id = _extract_trace_id(result) or deterministic_id(
                "tr",
                {"request_id": request_id, "call_id": call_id, "tool_name": tool_name},
            )
            return normalize_tool_response(
                tool_name=tool_name,
                request_id=request_id,
                call_id=call_id,
                interface_profile_id=interface_profile_id,
                trace_id=trace_id,
                result=result,
            )
        except Exception as exc:
            trace_id = deterministic_id(
                "tr",
                {"request_id": request_id, "call_id": call_id, "tool_name": tool_name, "error": True},
            )
            return normalize_tool_response(
                tool_name=tool_name,
                request_id=request_id,
                call_id=call_id,
                interface_profile_id=interface_profile_id,
                trace_id=trace_id,
                error=exc,
            )

    def _dispatch_tool_call(
        self,
        *,
        tool_name: str,
        request_id: str,
        arguments: dict[str, Any],
        normalized: dict[str, Any],
    ) -> Any:
        if tool_name == "get_capabilities":
            return self.get_capabilities()
        if tool_name == "get_tool_descriptors":
            return self.get_tool_descriptors()
        if tool_name == "get_provider_profiles":
            return self.get_provider_profiles()
        if tool_name == "get_compatibility_manifest":
            return self.get_compatibility_manifest()
        if tool_name == "negotiate_compatibility":
            return self.negotiate_compatibility(arguments.get("request"))
        if tool_name == "list_dialects":
            return {"dialects": self.list_dialects()}
        if tool_name == "list_schemas":
            return {
                "schemas": self.list_schemas(
                    dialect=str(arguments["dialect"]),
                    database=(str(arguments.get("database", "")).strip() or None),
                )
            }
        if tool_name == "list_tables":
            return {
                "tables": self.list_tables(
                    dialect=str(arguments["dialect"]),
                    schema=str(arguments["schema"]),
                )
            }
        if tool_name == "describe_table":
            return self.describe_table(
                dialect=str(arguments["dialect"]),
                schema=str(arguments["schema"]),
                table=str(arguments["table"]),
            )
        if tool_name == "compile_query":
            return self.compile_query(
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                context=arguments.get("context", {}),
            ).to_dict()
        if tool_name == "execute_compiled":
            return self.execute_compiled(
                compile_artifact_id=str(arguments["compile_artifact_id"]),
                options=arguments.get("options"),
                mode=str(arguments.get("mode", normalized.get("mode", "ai_analysis"))),
                approval_token=str(arguments.get("approval_token", "")).strip() or None,
            ).to_dict()
        if tool_name == "execute_readonly_query":
            return self.execute_readonly_query(
                request_id=request_id,
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                security_context=dict(arguments["security_context"]),
                options=arguments.get("options"),
                context=arguments.get("context"),
            )
        if tool_name == "execute_mutation":
            approval_evidence = normalized.get("approval_evidence") or arguments.get("approval_evidence")
            return self.execute_mutation(
                request_id=request_id,
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                security_context=dict(arguments["security_context"]),
                approval_evidence=dict(approval_evidence or {}),
                options=arguments.get("options"),
                context=arguments.get("context"),
            )
        if tool_name == "run_query":
            return self.run_query(
                request_id=request_id,
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                mode=str(arguments.get("mode", normalized.get("mode", "ai_analysis"))),
                options=arguments.get("options"),
                context=arguments.get("context"),
                approval_token=str(arguments.get("approval_token", "")).strip() or None,
            ).to_dict()
        if tool_name == "run_mutation":
            security_context = normalized.get("security_context", {})
            approval_evidence = normalized.get("approval_evidence") or {
                "approval_token": str(arguments.get("approval_token", "")).strip()
            }
            return self.execute_mutation(
                request_id=request_id,
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                security_context=dict(security_context),
                approval_evidence=dict(approval_evidence),
                options=arguments.get("options"),
                context=arguments.get("context"),
            )
        if tool_name == "explain_query":
            return self.explain_query(
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                context=arguments.get("context") or (
                    {"security_context": arguments["security_context"]}
                    if "security_context" in arguments
                    else {}
                ),
            )
        if tool_name == "create_vector_index":
            return self.create_vector_index(
                index_id=str(arguments["index_id"]),
                dimension=int(arguments["dimension"]),
                security_context=dict(arguments["security_context"]),
                profile_id=str(arguments.get("profile_id", "client_supplied_embeddings_v0")),
            )
        if tool_name == "list_vector_indexes":
            return self.list_vector_indexes(
                security_context=dict(arguments["security_context"]),
                include_deleted=bool(arguments.get("include_deleted", False)),
            )
        if tool_name == "describe_vector_index":
            return self.describe_vector_index(
                index_id=str(arguments["index_id"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "add_embeddings":
            return self.add_embeddings(
                index_id=str(arguments["index_id"]),
                dimension=int(arguments["dimension"]),
                records=list(arguments["records"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "add_generated_embeddings":
            return self.add_generated_embeddings(
                index_id=str(arguments["index_id"]),
                dimension=int(arguments["dimension"]),
                records=list(arguments["records"]),
                provider_config=dict(arguments["provider_config"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "delete_embeddings":
            return self.delete_embeddings(
                index_id=str(arguments["index_id"]),
                vector_ids=list(arguments["vector_ids"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "reindex_vector_index":
            return self.reindex_vector_index(
                index_id=str(arguments["index_id"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "delete_vector_index":
            return self.delete_vector_index(
                index_id=str(arguments["index_id"]),
                security_context=dict(arguments["security_context"]),
            )
        if tool_name == "vector_search":
            return self.vector_search(
                index_id=str(arguments["index_id"]),
                query_embedding=list(arguments["query_embedding"]),
                top_k=int(arguments["top_k"]),
                security_context=dict(arguments["security_context"]),
                filters=arguments.get("filters"),
                include_vectors=bool(arguments.get("include_vectors", False)),
            )
        if tool_name == "hybrid_search":
            return self.hybrid_search(
                dialect=str(arguments["dialect"]),
                query_text=str(arguments["query_text"]),
                query_embedding=list(arguments["query_embedding"]),
                vector_index_id=str(arguments["vector_index_id"]),
                top_k=int(arguments["top_k"]),
                security_context=dict(arguments["security_context"]),
                sql_filter=arguments.get("sql_filter"),
                weights=arguments.get("weights"),
                options=arguments.get("options"),
            )
        raise ToolContractError(
            error_code="E_TOOL_NOT_FOUND",
            message=f"unknown tool: {tool_name}",
            policy_rule_id="TOOL-DISPATCH-001",
        )

    def _build_plan_info(
        self,
        *,
        dialect: str,
        query_text: str,
        security_context: dict[str, Any],
        operator_type: str,
    ) -> dict[str, Any]:
        return build_plan_response(
            dialect=dialect,
            query_text=query_text,
            operator_tree={
                "operator_id": "root",
                "operator_type": operator_type,
                "children": [],
            },
            rls_policy_ids=[],
            predicate_hash=deterministic_id(
                "pred", {"security_context": security_context}
            ).removeprefix("pred_"),
            planner_version="v1",
            rls_applied=True,
        )

    def _remote_capabilities(self) -> dict[str, Any]:
        capabilities = self.get_capabilities()
        capabilities["interface_profiles"] = [
            profile
            for profile in capabilities["interface_profiles"]
            if profile.get("profile_id") == "mcp_remote_v0"
        ]
        capabilities["session_required"] = True
        capabilities["supports"]["streaming"] = True
        capabilities["supports"]["continuation_tokens"] = True
        capabilities["supports"]["cancellation"] = True
        capabilities["supports"]["remote_transports"] = [
            "https_json_request_response",
            "https_sse_server_stream",
        ]
        return capabilities


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
    remote_session_manager = RemoteSessionManager(
        auth_token=runtime_settings.remote_mcp_auth_token,
        session_ttl_sec=runtime_settings.remote_mcp_session_ttl_sec,
        heartbeat_interval_sec=runtime_settings.remote_mcp_heartbeat_interval_sec,
        supported_protocol_versions=runtime_settings.remote_mcp_protocol_versions,
        supported_transports=runtime_settings.remote_mcp_supported_transports,
    )
    retrieval_store = InMemoryRetrievalStore(
        catalog_path=runtime_settings.retrieval_catalog_path,
    )
    return ScratchBirdAIService(
        router=router,
        policy_engine=policy_engine,
        adapters=adapters,
        adapter_mode=mode,
        retrieval_store=retrieval_store,
        remote_session_manager=remote_session_manager,
    )


def _resolve_approval_token(
    *,
    approval_token: str | None,
    approval_evidence: dict[str, Any] | None,
) -> str | None:
    token = (approval_token or "").strip()
    if token:
        return token
    if isinstance(approval_evidence, dict):
        candidate = str(approval_evidence.get("approval_token", "")).strip()
        return candidate or None
    return None


def _extract_trace_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        candidate = payload.get("trace_id")
    else:
        candidate = getattr(payload, "trace_id", None)
    if candidate is None:
        return None
    normalized = str(candidate).strip()
    return normalized or None


def _resolve_approval_id(
    *,
    approval_evidence: dict[str, Any] | None,
    approval_token: str | None,
    compile_artifact_id: str,
) -> str | None:
    if isinstance(approval_evidence, dict):
        provided = str(approval_evidence.get("approval_id", "")).strip()
        if provided:
            return provided
    if approval_token:
        return deterministic_id(
            "appr",
            {
                "token": approval_token,
                "compile_artifact_id": compile_artifact_id,
            },
        )
    return None


def _extract_security_context(context: dict[str, Any]) -> dict[str, Any]:
    raw = context.get("security_context")
    if isinstance(raw, dict):
        tenant_id = str(raw.get("tenant_id", context.get("tenant_id", ""))).strip()
        actor_id = str(
            raw.get(
                "actor_id",
                context.get("actor_id", context.get("user_id", "")),
            )
        ).strip()
        roles_raw = raw.get("roles", context.get("roles", []))
        roles = [str(role) for role in roles_raw] if isinstance(roles_raw, list) else []
        session_id = str(raw.get("session_id", context.get("session_id", ""))).strip()
        context_version_raw = raw.get("context_version", context.get("context_version", 1))
        try:
            context_version = int(context_version_raw)
        except (TypeError, ValueError):
            context_version = 1
        return {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "roles": roles,
            "session_id": session_id,
            "context_version": max(1, context_version),
        }

    tenant_id = str(context.get("tenant_id", "")).strip()
    actor_id = str(context.get("actor_id", context.get("user_id", ""))).strip()
    roles_raw = context.get("roles", [])
    roles = [str(role) for role in roles_raw] if isinstance(roles_raw, list) else []
    session_id = str(context.get("session_id", "")).strip()
    context_version_raw = context.get("context_version", 1)
    try:
        context_version = int(context_version_raw)
    except (TypeError, ValueError):
        context_version = 1
    return {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "roles": roles,
        "session_id": session_id,
        "context_version": max(1, context_version),
    }


def _validate_compatibility_context(
    service: ScratchBirdAIService,
    context: dict[str, Any],
    *,
    default_profile_id: str,
    default_transport: str,
) -> None:
    request = _extract_compatibility_request(
        context,
        default_profile_id=default_profile_id,
        default_transport=default_transport,
    )
    if request is None:
        return
    response = service.negotiate_compatibility(request)
    error = response.get("error")
    if isinstance(error, dict):
        raise ToolContractError(
            error_code=str(error.get("error_code", "E_COMPATIBILITY_MISMATCH")),
            message=str(error.get("message", "compatibility negotiation failed")),
            policy_rule_id=str(error.get("reason_code", "COMPATIBILITY-NEGOTIATION-001")),
            trace_id=str(error.get("trace_id", "")) or None,
        )


def _extract_compatibility_request(
    context: dict[str, Any],
    *,
    default_profile_id: str,
    default_transport: str,
) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None

    raw = context.get("client_capabilities")
    if raw is None:
        raw = context.get("compatibility_request")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ToolContractError(
            error_code="E_COMPATIBILITY_MISMATCH",
            message="client_capabilities must be an object when provided",
            policy_rule_id="COMPATIBILITY-REQUEST-001",
        )

    request = dict(raw)
    request["interface_profile_id"] = (
        str(request.get("interface_profile_id", "")).strip() or default_profile_id
    )
    request["requested_profile_version"] = (
        str(request.get("requested_profile_version", "")).strip() or "v0"
    )
    request["requested_transport"] = (
        str(request.get("requested_transport", "")).strip() or default_transport
    )
    return request
