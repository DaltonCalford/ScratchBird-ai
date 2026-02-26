"""Canonical tool schema validation and error envelope helpers."""

from __future__ import annotations

from typing import Any

from .deterministic import deterministic_id

TOOL_SCHEMA_VERSION = "1.0"

OPTION_LIMITS = {
    "max_rows": (1, 10_000, 200),
    "timeout_ms": (100, 30_000, 5_000),
    "memory_mb": (64, 2_048, 256),
}


class ToolContractError(RuntimeError):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        policy_rule_id: str | None = None,
        sqlstate: str | None = None,
        retryable: bool = False,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.policy_rule_id = policy_rule_id
        self.sqlstate = sqlstate
        self.retryable = retryable
        self.trace_id = trace_id


def _to_int(value: Any, default: int) -> int:
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def require_security_context(payload: dict[str, Any] | None) -> dict[str, Any]:
    src = payload or {}
    raw = src.get("security_context", src)
    if not isinstance(raw, dict):
        raise ToolContractError(
            error_code="E_POLICY_DENY",
            message="security_context must be an object",
            policy_rule_id="SECURITY-CONTEXT-001",
        )

    tenant_id = str(raw.get("tenant_id", "")).strip()
    actor_id = str(raw.get("actor_id", "")).strip()
    roles_raw = raw.get("roles", [])
    session_id = str(raw.get("session_id", "")).strip()
    context_version = _to_int(raw.get("context_version"), 1)

    if not tenant_id or not actor_id:
        raise ToolContractError(
            error_code="E_POLICY_DENY",
            message="security_context requires tenant_id and actor_id",
            policy_rule_id="SECURITY-CONTEXT-002",
        )

    roles = [str(role) for role in roles_raw] if isinstance(roles_raw, list) else []
    normalized = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "roles": roles,
        "session_id": session_id,
        "context_version": max(1, context_version),
    }
    return normalized


def validate_options(options: dict[str, Any] | None) -> dict[str, int]:
    src = options or {}
    out: dict[str, int] = {}
    aliases = {
        "max_rows": "limit",
    }
    for field_name, (minimum, maximum, default) in OPTION_LIMITS.items():
        value_raw = src.get(field_name)
        if value_raw is None and field_name in aliases:
            value_raw = src.get(aliases[field_name])
        value = _to_int(value_raw, default)
        if value > maximum:
            raise ToolContractError(
                error_code="E_LIMIT_EXCEEDED",
                message=f"{field_name} exceeds hard limit ({maximum})",
                policy_rule_id="OPTIONS-LIMIT-001",
            )
        if value < minimum:
            value = minimum
        out[field_name] = value
    out["limit"] = out["max_rows"]
    return out


def make_trace_id(seed: dict[str, Any]) -> str:
    return deterministic_id("tr", seed)


def error_envelope(
    *,
    error_code: str,
    message: str,
    trace_id: str | None = None,
    policy_rule_id: str | None = None,
    sqlstate: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": message,
        "trace_id": trace_id or make_trace_id({"error_code": error_code, "message": message}),
        "policy_rule_id": policy_rule_id,
        "sqlstate": sqlstate,
        "retryable": bool(retryable),
    }


def map_exception_to_error(exc: Exception, *, trace_seed: dict[str, Any]) -> dict[str, Any]:
    try:
        from .execution_mode import ExecutionModeError
        from .policy import PolicyDeniedError
        from .retrieval import RetrievalError
        from .router import RoutingError
    except Exception:  # pragma: no cover - import cycle fallback
        ExecutionModeError = None  # type: ignore[assignment]
        PolicyDeniedError = None  # type: ignore[assignment]
        RetrievalError = None  # type: ignore[assignment]
        RoutingError = None  # type: ignore[assignment]

    trace_id = make_trace_id(trace_seed)
    if isinstance(exc, ToolContractError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=exc.trace_id or trace_id,
            policy_rule_id=exc.policy_rule_id,
            sqlstate=exc.sqlstate,
            retryable=exc.retryable,
        )
    if PolicyDeniedError is not None and isinstance(exc, PolicyDeniedError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.reason,
            trace_id=trace_id,
            policy_rule_id=exc.rule_id,
            retryable=False,
        )
    if RoutingError is not None and isinstance(exc, RoutingError):
        return error_envelope(
            error_code="E_DIALECT_UNAVAILABLE",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    if ExecutionModeError is not None and isinstance(exc, ExecutionModeError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=trace_id,
            policy_rule_id=exc.rule_id,
            retryable=False,
        )
    if RetrievalError is not None and isinstance(exc, RetrievalError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=trace_id,
            policy_rule_id=exc.policy_rule_id,
            retryable=exc.retryable,
        )
    if isinstance(exc, KeyError):
        return error_envelope(
            error_code="E_INVALID_ARGUMENT",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    if isinstance(exc, ValueError):
        return error_envelope(
            error_code="E_INVALID_ARGUMENT",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    return error_envelope(
        error_code="E_EXECUTION_FAILED",
        message=str(exc) or "execution failed",
        trace_id=trace_id,
        retryable=False,
    )
