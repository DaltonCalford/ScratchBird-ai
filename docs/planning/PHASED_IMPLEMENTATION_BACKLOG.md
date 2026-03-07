# ScratchBird AI Phased Implementation Backlog (P0/P1/P2)

Status: Active
Last Updated: 2026-03-07

## 1. Scope

This backlog tracks the implemented early-beta surface and the remaining work required to harden it.

For broader post-early-beta AI interface expansion work, see:

- `docs/planning/AI_INTERFACE_IMPLEMENTATION_BACKLOG.md`

Reference drafts:

- `docs/specifications/drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/DIALECT_CAPABILITY_MATRIX_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/specifications/drafts/SCRATCHBIRD_HTTP_ADAPTER_CONTRACT_SPEC.md`
- `docs/specifications/drafts/SCRATCHBIRD_HTTP_BRIDGE_RUNTIME_SPEC.md`
- `docs/specifications/final/ADR-0001_REPOSITORY_BOUNDARY.md`
- `docs/specifications/final/ADR-0002_QUERY_ENTRYPOINT_AND_SBLR_POLICY.md`
- `docs/specifications/final/ADR-0003_SERVER_EXECUTION_BOUNDARY_AND_ADAPTER_ROLE.md`

## 2. Current Baseline Summary

Delivered baseline as of 2026-03-07:

- native-only routing and capability gating
- MCP-oriented service orchestration and canonical tool surface
- HTTP adapter plus local bridge runtime
- deterministic retrieval, plan, audit, execution-mode, and cluster-routing helpers
- release evidence generation and validation for the implemented feature set

## 3. P0 Foundation (Read-Only, Safe-by-Default)

Goal: end-to-end safe read-only AI query path with traceability.

| Task | Status | Notes |
| --- | --- | --- |
| P0-001: Scaffold MCP server with required read-only metadata/query tools | Completed | `mcp_server.py` exposes capability, metadata, query, explain, retrieval, and mutation-gated tools |
| P0-002: Implement query router (dialect selection + capability gate lookup) | Completed | Native-only router and capability checks are implemented and tested |
| P0-003: Implement compile adapter contract (`dialect, query_text -> compile_artifact`) | Completed | Compile artifact IDs are deterministic and bridge/http contracts are covered |
| P0-004: Implement execute adapter contract (`compile_artifact -> bounded rows`) | Completed | Execute path is bounded and exercised through service and HTTP tests |
| P0-005: Enforce read-only policy default and deny mutation operations | Completed | Read-only default and approval-gated mutation path are covered by tests |
| P0-006: Add structured logging, trace IDs, and audit tuple emission | Partial | Trace IDs and deterministic audit bundles are present; full structured logging/runbook packaging is still incomplete |
| P0-007: Add first capability matrix payload and runtime loader | Completed | Matrix schema, payload, loader, and validator are present |
| P0-008: CI checks for matrix schema validation and contract tests | Completed | Validation tooling exists and release evidence is now generated from the current checkout |

## 4. P1 Expansion (Native Hardening + Retrieval)

Goal: harden native coverage and add richer planning/retrieval support.

| Task | Status | Notes |
| --- | --- | --- |
| P1-001: Harden native capability profile and contract behavior under live workloads | Partial | In-process and fake-backend coverage is good; live native validation is still limited |
| P1-002: Add bounded compile-repair loop for recoverable compile failures | Pending | Not implemented |
| P1-003: Add retrieval augmentation modules (vector/hybrid retrieval via tools) | Completed | Engine-free vector/hybrid retrieval plus service/MCP exposure exist |
| P1-004: Add evaluation harness for execution accuracy and retrieval quality | Partial | Offline release evidence exists; larger live workload evaluation remains pending |
| P1-005: Add explain/trace tool endpoints for diagnostics | Partial | Explain/trace helpers and service endpoints exist; live bridge-backed validation remains thin |

## 5. P2 Governed Mutations + Operations Hardening

Goal: controlled write workflows and production readiness controls.

| Task | Status | Notes |
| --- | --- | --- |
| P2-001: Implement approval-gated mutation tool path | Partial | Mutation path is present, but approval evidence is not durable yet |
| P2-002: Add policy rule identifiers and approval evidence in audit trail | Partial | Rule identifiers and audit bundles exist; durable approval evidence is still missing |
| P2-003: Implement quota/rate limiting and cost attribution | Pending | Not implemented |
| P2-004: Add resilience controls (timeouts, retries, circuit breakers) | Partial | Hard limits exist; standardized retry/circuit-breaker policy does not |
| P2-005: Build compatibility matrix between `ScratchBird-ai` and parser/compiler versions | Pending | Not implemented |

## 6. Priority Order From Here

1. P1-002 compile-repair loop
2. P1-001 live native workload validation
3. P2-001 and P2-002 durable approval evidence
4. P2-003 quotas/rate limits and P2-004 resilience policy
5. P2-005 parser/compiler compatibility enforcement

Post-early-beta interface expansion sequencing is tracked separately in `docs/planning/AI_INTERFACE_IMPLEMENTATION_BACKLOG.md`.
