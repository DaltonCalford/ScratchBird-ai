# ScratchBird Deterministic Audit Bundle Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the immutable audit bundle format that records AI query/mutation decisions and supports deterministic replay validation.

## 2. Required Bundle Contents

Each bundle MUST include:
1. `bundle_version`
2. `request_id`
3. `trace_id`
4. `tenant_id`
5. `actor_id`
6. `dialect`
7. `execution_mode`
8. `sql_text_normalized`
9. `compile_artifact_id`
10. `execution_artifact_id` (if execution occurred)
11. `plan_json`
12. `plan_hash`
13. `security_context_hash`
14. `policy_decision`
15. `policy_rule_id`
16. `cluster_epoch`
17. `timestamp_utc`
18. `bundle_hash`

Optional fields:
1. `approval_id`
2. `approval_token_hash`
3. `error_code`
4. `sqlstate`

## 3. Canonical Bundle Schema

```json
{
  "bundle_version": "1.0",
  "request_id": "req_...",
  "trace_id": "tr_...",
  "tenant_id": "tenant-a",
  "actor_id": "user-123",
  "dialect": "native",
  "execution_mode": "ai_analysis",
  "sql_text_normalized": "SELECT ...",
  "compile_artifact_id": "cmp_...",
  "execution_artifact_id": "exe_...",
  "plan_json": {},
  "plan_hash": "hex-sha256",
  "security_context_hash": "hex-sha256",
  "policy_decision": "allow",
  "policy_rule_id": "POLICY-ALLOW-000",
  "cluster_epoch": 42,
  "timestamp_utc": "2026-02-24T13:00:00Z",
  "bundle_hash": "hex-sha256"
}
```

## 4. Deterministic Hashing Rules

### 4.1 security_context_hash

Compute over canonical object:
1. `tenant_id`
2. `actor_id`
3. sorted `roles`
4. `context_version`

Algorithm:
1. Canonicalize JSON with RFC 8785 JCS.
2. Hash with SHA-256.
3. Encode lowercase hex.

### 4.2 bundle_hash

Compute over full bundle content excluding `bundle_hash` field itself:
1. Canonicalize JSON with RFC 8785 JCS.
2. Hash with SHA-256.
3. Encode lowercase hex.

## 5. Storage and Immutability

1. Bundle storage key format:
   - `audit/{tenant_id}/{yyyy}/{mm}/{dd}/{trace_id}.json`
2. Bundles are immutable:
   - updates are prohibited.
   - corrections require a new bundle referencing superseded trace.
3. Bundle persistence MUST occur for both allow and deny outcomes.

## 6. Replay Validation Procedure

Replay validator MUST:
1. load bundle by `trace_id`,
2. recompute `security_context_hash` and `bundle_hash`,
3. re-run plan hash computation using recorded normalized inputs,
4. confirm policy decision by re-evaluating rule inputs,
5. verify deterministic match:
   - `plan_hash`,
   - `policy_decision`,
   - `policy_rule_id`.

Validation outcomes:
1. `REPLAY_MATCH`
2. `REPLAY_MISMATCH_HASH`
3. `REPLAY_MISMATCH_POLICY`
4. `REPLAY_INSUFFICIENT_DATA`

## 7. Security Requirements

1. Raw secrets MUST NOT be stored in bundle.
2. Approval token MUST be stored as hash only (`approval_token_hash`) unless explicit compliance policy requires encrypted token retention.
3. Sensitive literals in SQL MAY be redacted in `sql_text_normalized` if redaction is deterministic.

## 8. Error Handling

Required error codes:
1. `E_AUDIT_PERSISTENCE_FAILED`
2. `E_AUDIT_REPLAY_MISMATCH`
3. `E_AUDIT_SCHEMA_INVALID`

If bundle persistence fails for mutation operations, execution MUST fail closed.

## 9. Required Tests

1. Schema conformance tests.
2. Hash determinism tests across repeated serialization runs.
3. Replay match and mismatch scenario tests.
4. Deny-path audit emission tests.
5. Secret redaction tests.

## 10. Acceptance Criteria

1. Every request emits exactly one immutable audit bundle.
2. Replay validator deterministically reproduces hash and policy outcomes.
3. Bundle format is stable and versioned.

## 11. Evidence Binding

1. This specification is bound to `EVID-09` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/09/audit_replay_report.json`
   - `artifacts/ai_conformance/09/attestation_report.json`
3. Audit integrity claims MUST NOT be accepted unless `EVID-09` proof artifacts report `status=PASS`.
