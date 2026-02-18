# Text-to-SQL Router and Compiler Integration Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define how natural-language requests are translated into dialect-aware query text, compiled through parser pathways, and executed as validated SBLR workflows.

## 2. Scope

- In scope:
- NL intent handling
- Dialect detection/routing
- Compile contract
- Error recovery loop

- Out of scope:
- Model training/fine-tuning
- Direct SBLR synthesis from model output

## 3. Dependencies

- `docs/specifications/drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`
- `docs/specifications/drafts/DIALECT_CAPABILITY_MATRIX_SPEC.md`

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Router MUST resolve target dialect from session context or explicit input.
- FR-002: Router MUST validate dialect capability before compilation.
- FR-003: Query compilation MUST occur through parser/compiler adapters.
- FR-004: Execution MUST operate on compiled artifacts, not model-produced bytecode.
- FR-005: On compile error, orchestrator MAY run bounded repair attempts.
- FR-006: Repair loop MUST stop after configurable max attempts.
- FR-007: Engine execution boundary MUST remain `ServerSession`; no alternate SQL execution path may be introduced in server/executor.
- FR-008: Listener/parser configuration MUST enforce one dialect parser per configured port, with no protocol auto-detect fallback in parser logic.

### 4.2 Non-Functional Requirements

- NFR-001: Each stage MUST emit timing and status for traceability.
- NFR-002: Retry behavior MUST be deterministic and bounded.

## 5. Interfaces and Contracts

Compile adapter contract:

- Input:
  - `dialect`
  - `query_text`
  - `session_ctx`
- Output:
  - `compile_artifact_id`
  - `sblr_hash`
  - `diagnostics[]`
  - `warnings[]`

Execute adapter contract:

- Input:
  - `compile_artifact_id`
  - `execution_options`
- Output:
  - `execution_artifact_id`
  - `rows`
  - `row_count`
  - `sqlstate_or_error`

## 6. Security and Governance

- Enforce read-only mode unless explicit mutation policy is satisfied.
- Require parameterized statements for user-supplied values where supported.
- Reject requests that attempt cross-tenant data access.

## 7. Observability

- Stage spans: classify, route, compile, execute, synthesize.
- Log schema:
  - `trace_id`, `request_id`, `dialect`, `capability_version`, `compile_ms`, `execute_ms`.

## 8. Testing and Acceptance Criteria

- Unit:
- Dialect routing decisions
- Retry policy limit enforcement

- Integration:
- End-to-end NL -> compile -> execute for supported dialects

- Regression:
- Capability downgrade/upgrade handling
- Compile error repair loop behavior

- Exit criteria:
- Zero unbounded retry loops
- Deterministic fallback on unsupported dialect feature sets

## 9. Rollout Plan

- Phase 1: native pathway only.
- Phase 2: native hardening and governance maturation.

## 10. Open Questions

- Q1: Should repair strategy be model-only, rule-only, or hybrid?
- Q2: Should compile cache be shared across tenants with strict normalization constraints?
