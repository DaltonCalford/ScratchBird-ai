# ScratchBird AI Execution Mode Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define canonical execution modes, transition rules, policy checks, and resource controls for AI-initiated database operations.

## 2. Canonical Modes

1. `ai_analysis`
   - Read-only mode.
   - Mutation statements are denied.
2. `ai_mutation_pending_approval`
   - Mutation intent acknowledged.
   - Execution blocked until valid approval evidence is supplied.
3. `ai_mutation_approved`
   - Mutation allowed only when approval evidence validates and policy checks pass.

Legacy compatibility aliases:
1. `read_only` => `ai_analysis`
2. `mutation_with_approval` => `ai_mutation_pending_approval` unless explicit approval evidence is provided.

## 3. Mode State Machine

Allowed transitions:
1. `ai_analysis` -> `ai_mutation_pending_approval`
2. `ai_mutation_pending_approval` -> `ai_mutation_approved`
3. `ai_mutation_approved` -> `ai_analysis`

Disallowed transitions:
1. direct `ai_analysis` -> `ai_mutation_approved` without approval verification.
2. any transition with expired/invalid security context.

## 4. Enforcement Order

For every execute attempt, enforcement MUST run in this order:
1. resolve mode and normalize aliases,
2. validate security context,
3. classify statement kind (`read|mutation|unknown`),
4. validate approval evidence when mutation path is requested,
5. enforce mode-policy matrix,
6. enforce resource limits,
7. execute if and only if all checks pass.

## 5. Mode-Policy Matrix

1. Statement kind `read`:
   - allowed in all modes.
2. Statement kind `mutation`:
   - denied in `ai_analysis`.
   - denied in `ai_mutation_pending_approval`.
   - allowed in `ai_mutation_approved` with valid approval evidence.
3. Statement kind `unknown`:
   - treated as mutation for safety and requires `ai_mutation_approved`.

## 6. Approval Evidence Requirements

For `ai_mutation_approved`, approval evidence MUST include:
1. `approval_token`,
2. `approval_id`,
3. `approved_by`,
4. `approved_at`.

`approval_token` validation requirements:
1. cryptographically verifiable signature,
2. unexpired (`exp` > now),
3. claim `tenant_id` equals request tenant,
4. claim `actor_id` equals request actor,
5. claim `statement_hash` equals compiled statement hash.

If any check fails, return `E_POLICY_DENY`.

## 7. Resource Controls

Default limits:
1. `max_rows = 200`
2. `timeout_ms = 5000`
3. `memory_mb = 256`

Hard limits:
1. `max_rows <= 10000`
2. `timeout_ms <= 30000`
3. `memory_mb <= 2048`

Requests exceeding hard limits MUST fail with `E_LIMIT_EXCEEDED`.

## 8. Audit and Trace Requirements

Every mode evaluation MUST emit:
1. `trace_id`,
2. resolved mode,
3. statement kind,
4. policy decision,
5. policy rule ID,
6. approval ID (if present).

Denied decisions MUST be auditable and deterministic.

## 9. Error Codes

Required mode-related errors:
1. `E_INVALID_MODE`
2. `E_POLICY_DENY`
3. `E_APPROVAL_INVALID`
4. `E_LIMIT_EXCEEDED`

## 10. Required Tests

1. State transition tests.
2. Mutation denial tests for `ai_analysis` and `ai_mutation_pending_approval`.
3. Approval validation tests (valid/expired/mismatched claims).
4. Resource limit enforcement tests.
5. Alias normalization tests.

## 11. Acceptance Criteria

1. Mode behavior is deterministic and fully covered by tests.
2. Mutation cannot execute without valid approval evidence.
3. Resource limits are enforced before execution.

## 12. Evidence Binding

1. This specification is bound to `EVID-08` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/08/mode_matrix.json`
   - `artifacts/ai_conformance/08/policy_simulation.json`
3. Any unclassified transition or denial outcome in `EVID-08` evidence MUST fail release gating.
