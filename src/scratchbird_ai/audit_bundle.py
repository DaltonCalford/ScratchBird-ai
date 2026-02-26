"""Deterministic audit bundle generation and replay checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .deterministic import canonical_json, sha256_hex

REPLAY_OUTCOMES = {
    "match": "REPLAY_MATCH",
    "mismatch_hash": "REPLAY_MISMATCH_HASH",
    "mismatch_policy": "REPLAY_MISMATCH_POLICY",
    "insufficient_data": "REPLAY_INSUFFICIENT_DATA",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def security_context_hash(security_context: dict[str, Any]) -> str:
    roles_raw = security_context.get("roles", [])
    roles = [str(item) for item in roles_raw] if isinstance(roles_raw, list) else []
    context_version_raw = security_context.get("context_version", 1)
    try:
        context_version = int(context_version_raw)
    except (TypeError, ValueError):
        context_version = 1

    canonical_input = {
        "tenant_id": str(security_context.get("tenant_id", "")),
        "actor_id": str(security_context.get("actor_id", "")),
        "roles": sorted(roles),
        "context_version": max(1, context_version),
    }
    canonical = canonical_json(canonical_input)
    return sha256_hex(canonical)


def approval_token_hash(approval_token: str | None) -> str | None:
    token = (approval_token or "").strip()
    if not token:
        return None
    return sha256_hex(token)


def _bundle_hash_input(bundle: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in bundle.items() if k != "bundle_hash"}


def bundle_hash(bundle: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(_bundle_hash_input(bundle)))


@dataclass(slots=True, frozen=True)
class AuditReplayResult:
    outcome: str
    reason: str


def create_audit_bundle(
    *,
    trace_id: str,
    request_id: str,
    tenant_id: str,
    actor_id: str,
    dialect: str,
    execution_mode: str,
    sql_text_normalized: str,
    compile_artifact_id: str,
    execution_artifact_id: str | None,
    plan_json: dict[str, Any] | None,
    plan_hash: str,
    policy_decision: str,
    policy_rule_id: str,
    security_context: dict[str, Any],
    cluster_epoch: int = 0,
    approval_id: str | None = None,
    approval_token: str | None = None,
    error_code: str | None = None,
    sqlstate: str | None = None,
    created_at_utc: str | None = None,
    bundle_version: str = "1.0",
    statement_kind: str | None = None,
    sblr_hash: str | None = None,
) -> dict[str, Any]:
    sec_hash = security_context_hash(security_context)
    timestamp = created_at_utc or now_utc_iso()
    plan_doc = dict(plan_json) if isinstance(plan_json, dict) else {}
    bundle: dict[str, Any] = {
        "bundle_version": bundle_version,
        "trace_id": trace_id,
        "request_id": request_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "dialect": dialect,
        "execution_mode": execution_mode,
        "sql_text_normalized": sql_text_normalized,
        "compile_artifact_id": compile_artifact_id,
        "execution_artifact_id": execution_artifact_id,
        "plan_json": plan_doc,
        "plan_hash": plan_hash,
        "security_context_hash": sec_hash,
        "policy_decision": policy_decision,
        "policy_rule_id": policy_rule_id,
        "cluster_epoch": int(cluster_epoch),
        "timestamp_utc": timestamp,
        "approval_id": approval_id,
        "approval_token_hash": approval_token_hash(approval_token),
        "error_code": error_code,
        "sqlstate": sqlstate,
    }
    # Legacy fields retained for transition compatibility.
    bundle["schema_version"] = bundle_version
    bundle["created_at_utc"] = timestamp
    if statement_kind is not None:
        bundle["statement_kind"] = statement_kind
    if sblr_hash is not None:
        bundle["sblr_hash"] = sblr_hash
    bundle["bundle_hash"] = bundle_hash(bundle)
    return bundle


def replay_validate_bundle(
    *,
    bundle: dict[str, Any],
    security_context: dict[str, Any] | None = None,
    expected_policy_decision: str | None = None,
    expected_policy_rule_id: str | None = None,
    expected_plan_hash: str | None = None,
) -> AuditReplayResult:
    required_fields = {
        "bundle_version",
        "request_id",
        "trace_id",
        "tenant_id",
        "actor_id",
        "dialect",
        "execution_mode",
        "sql_text_normalized",
        "compile_artifact_id",
        "plan_json",
        "plan_hash",
        "security_context_hash",
        "policy_decision",
        "policy_rule_id",
        "cluster_epoch",
        "timestamp_utc",
        "bundle_hash",
    }
    if any(field not in bundle for field in required_fields):
        return AuditReplayResult(
            outcome=REPLAY_OUTCOMES["insufficient_data"],
            reason="bundle missing required fields",
        )

    recomputed_bundle_hash = bundle_hash(bundle)
    if recomputed_bundle_hash != bundle.get("bundle_hash"):
        return AuditReplayResult(
            outcome=REPLAY_OUTCOMES["mismatch_hash"],
            reason="bundle hash mismatch",
        )

    if security_context is not None:
        recomputed_sec_hash = security_context_hash(security_context)
        if recomputed_sec_hash != bundle.get("security_context_hash"):
            return AuditReplayResult(
                outcome=REPLAY_OUTCOMES["mismatch_hash"],
                reason="security_context_hash mismatch",
            )

    if expected_policy_decision is not None:
        if expected_policy_decision != bundle.get("policy_decision"):
            return AuditReplayResult(
                outcome=REPLAY_OUTCOMES["mismatch_policy"],
                reason="policy decision mismatch",
            )
    if expected_policy_rule_id is not None:
        if expected_policy_rule_id != bundle.get("policy_rule_id"):
            return AuditReplayResult(
                outcome=REPLAY_OUTCOMES["mismatch_policy"],
                reason="policy rule mismatch",
            )

    if expected_plan_hash is not None:
        if expected_plan_hash != bundle.get("plan_hash"):
            return AuditReplayResult(
                outcome=REPLAY_OUTCOMES["mismatch_hash"],
                reason="plan hash mismatch",
            )

    return AuditReplayResult(
        outcome=REPLAY_OUTCOMES["match"],
        reason="bundle replay checks match",
    )
