# ScratchBird Plan Introspection API Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the plan-introspection contract that returns deterministic, security-safe, structured execution plans for AI tooling and governance workflows.

Out of scope:
1. execution of plans,
2. plan mutation from AI clients.

## 2. API Surface

Base path: `/v1/plans`

Required endpoint:
1. `POST /introspect`

Input modes:
1. by SQL text (`query_text`),
2. by compile artifact (`compile_artifact_id`).

Exactly one input mode MUST be provided.

## 3. Request Schema

```json
{
  "dialect": "native",
  "query_text": "SELECT ...",
  "compile_artifact_id": "optional-cmp-id",
  "security_context": {
    "tenant_id": "tenant-a",
    "actor_id": "user-123",
    "roles": ["analyst"],
    "session_id": "sess-001",
    "context_version": 1
  },
  "options": {
    "include_costs": true,
    "include_rls_policies": true
  }
}
```

Validation rules:
1. `dialect` MUST be `native` in v1.
2. exactly one of `query_text` or `compile_artifact_id` MUST be present.
3. `security_context` is REQUIRED.

## 4. Response Schema

```json
{
  "compile_artifact_id": "cmp_...",
  "plan_hash": "lowercase-hex-sha256",
  "plan_version": "1.0",
  "operator_tree": {
    "operator_id": "op-1",
    "operator_type": "IndexScan",
    "children": []
  },
  "rls_visibility": {
    "applied": true,
    "policy_ids": ["RLS-001", "RLS-101"],
    "predicate_hash": "lowercase-hex-sha256"
  },
  "estimated_cost": {
    "cpu": 12.3,
    "io": 4.7,
    "rows": 1500
  },
  "trace_id": "tr_..."
}
```

## 5. Operator Tree Contract

Each node MUST include:
1. `operator_id` (stable within plan),
2. `operator_type`,
3. `children` array.

Optional deterministic fields:
1. `relation`,
2. `index`,
3. `predicate_summary`,
4. `estimated_rows`,
5. `estimated_cost`.

`children` ordering MUST be deterministic and match execution/planning order.

## 6. Deterministic plan_hash Algorithm

`plan_hash` MUST be computed as:
1. build canonical hash input object:
   - `dialect`
   - `normalized_query`
   - `normalized_operator_tree`
   - `rls_policy_ids` sorted ascending
   - `predicate_hash`
   - `planner_version`
2. canonicalize JSON using RFC 8785 JSON Canonicalization Scheme (JCS),
3. hash with SHA-256,
4. encode as lowercase hex.

For identical canonical input, `plan_hash` MUST be identical across repeated runs.

## 7. Security Requirements

1. Plan output MUST NOT include protected row values.
2. Literals containing secrets MAY be redacted to placeholders.
3. RLS visibility MUST explicitly indicate whether policies were applied.
4. Missing security context MUST fail with `E_POLICY_DENY`.

## 8. Error Model

Required error codes:
1. `E_INVALID_ARGUMENT`
2. `E_DIALECT_UNAVAILABLE`
3. `E_COMPILE_FAILED`
4. `E_POLICY_DENY`
5. `E_TIMEOUT`

Error responses MUST use the standard envelope from specification `06`.

## 9. Required Tests

1. Schema validation tests for request and response.
2. Deterministic `plan_hash` repeatability test.
3. RLS visibility correctness test.
4. Security redaction test (no protected row data).
5. Negative tests for invalid dual-input requests.

## 10. Acceptance Criteria

1. API returns deterministic `plan_hash`.
2. Operator hierarchy is complete and deterministic.
3. Security constraints are enforced and validated by tests.

## 11. Evidence Binding

1. This specification is bound to `EVID-07` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/07/plan_hash_report.json`
   - `artifacts/ai_conformance/07/diff_report.json`
3. Planner behavior regressions that fail `EVID-07` MUST block release.
