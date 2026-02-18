# ScratchBird AI Phased Implementation Backlog (P0/P1/P2)

Status: Draft
Last Updated: 2026-02-18

## 1. Scope

This backlog operationalizes the current draft specification set into delivery phases.

Reference specs:

- `docs/specifications/drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/DIALECT_CAPABILITY_MATRIX_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/specifications/final/ADR-0001_REPOSITORY_BOUNDARY.md`
- `docs/specifications/final/ADR-0002_QUERY_ENTRYPOINT_AND_SBLR_POLICY.md`

## 2. P0 Foundation (Read-Only, Safe-by-Default)

Goal: end-to-end safe read-only AI query path with traceability.

### Tasks

- P0-001: Scaffold MCP server with required read-only metadata/query tools.
- P0-002: Implement query router (dialect selection + capability gate lookup).
- P0-003: Implement compile adapter contract (`dialect, query_text -> compile_artifact`).
- P0-004: Implement execute adapter contract (`compile_artifact -> bounded rows`).
- P0-005: Enforce read-only policy default and deny mutation operations.
- P0-006: Add structured logging, trace IDs, and audit tuple emission.
- P0-007: Add first capability matrix payload and runtime loader.
- P0-008: CI checks for matrix schema validation and contract tests.

### Initial Dialect Coverage Target

- `native`

### Acceptance Criteria

- AC-P0-1: Metadata tools and read-only `run_query` pass integration tests.
- AC-P0-2: Mutation attempts are rejected without approval context.
- AC-P0-3: Every request has a trace ID and audit event.
- AC-P0-4: Capability matrix schema validation enforced in CI.

## 3. P1 Expansion (Native Hardening + Retrieval)

Goal: harden native coverage and add indirect retrieval pathways.

### Tasks

- P1-001: Harden native capability profile and contract behavior under live workloads.
- P1-002: Add bounded compile-repair loop for recoverable compile failures.
- P1-003: Add retrieval augmentation modules (vector/hybrid retrieval via tools).
- P1-004: Add evaluation harness for execution accuracy and retrieval quality.
- P1-005: Add explain/trace tool endpoints for diagnostics.

### Acceptance Criteria

- AC-P1-1: Router behavior matches native-only matrix policy.
- AC-P1-2: Repair loop bounded and deterministic.
- AC-P1-3: Retrieval metrics (recall@k baseline) tracked per build.
- AC-P1-4: Explain/trace tools available and covered by tests.

## 4. P2 Governed Mutations + Operations Hardening

Goal: controlled write workflows and production readiness controls.

### Tasks

- P2-001: Implement approval-gated mutation tool path.
- P2-002: Add policy rule identifiers and approval evidence in audit trail.
- P2-003: Implement quota/rate limiting and cost attribution.
- P2-004: Add resilience controls (timeouts, retries, circuit breakers).
- P2-005: Build compatibility matrix between `ScratchBird-ai` and parser/compiler versions.

### Acceptance Criteria

- AC-P2-1: Mutation path requires valid approval evidence and passes negative tests.
- AC-P2-2: Policy/audit data are complete and queryable.
- AC-P2-3: SLO dashboards for latency/error/timeout rates are live.
- AC-P2-4: Version compatibility checks fail closed on mismatch.

## 5. Delivery Notes

- Default AI query entrypoint remains parser/compiler path.
- No free-form model-generated SBLR bytecode in baseline releases.
- Promote specs from draft to final as each phase closes open questions.
