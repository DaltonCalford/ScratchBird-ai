"""P0 service layer for MCP tool orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapters.base import DialectAdapter
from .adapters.http import HttpJsonClient, make_http_dialect_adapter
from .adapters.mock import make_mock_dialect_adapter
from .audit_bundle import create_audit_bundle, security_context_hash
from .capability_matrix import load_capability_matrix
from .contracts import CompileResult, ExecuteResult, QueryResponse
from .deterministic import deterministic_id
from .plan_introspection import build_plan_response
from .policy import PolicyDeniedError, PolicyDecision, PolicyEngine
from .retrieval import InMemoryRetrievalStore
from .router import DialectRouter
from .settings import RuntimeSettings, load_runtime_settings
from .tool_schema import ToolContractError, TOOL_SCHEMA_VERSION, require_security_context, validate_options


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
    ) -> None:
        self.router = router
        self.policy_engine = policy_engine
        self.adapters = adapters
        self.adapter_mode = adapter_mode
        self._compile_store: dict[str, CompileRecord] = {}
        self._execution_attempts: dict[str, int] = {}
        self._audit_store: list[dict[str, Any]] = []
        self._retrieval = retrieval_store or InMemoryRetrievalStore()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "service": "scratchbird-ai",
            "version": "0.1.0",
            "query_entrypoint_policy": "parser_compiler_first",
            "adapter_mode": self.adapter_mode,
            "tool_schema_version": TOOL_SCHEMA_VERSION,
            "supports": {
                "metadata": True,
                "compile_execute_split": True,
                "read_only_mode": True,
                "mutation_requires_approval": True,
                "vector_search": True,
                "hybrid_search": True,
                "canonical_tools": [
                    "get_capabilities",
                    "list_dialects",
                    "list_schemas",
                    "list_tables",
                    "describe_table",
                    "execute_readonly_query",
                    "execute_mutation",
                    "explain_query",
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

        compiled = self.compile_query(
            dialect=dialect,
            query_text=query_text,
            context=query_context,
        )
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
