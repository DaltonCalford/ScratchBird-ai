# Early Beta Status Snapshot

Snapshot Date: 2026-03-07
Scope: `ScratchBird-ai` early beta (`0.1.0`)
Overall Status: **Yellow** (functional beta surface with credible release evidence and known hardening gaps)

## 1. Executive Summary

`ScratchBird-ai` is materially ahead of the original February 18, 2026 snapshot.

Current verified baseline:

- repository tree is clean
- tracked generated artifacts were removed and are now ignored
- unit and integration suite passes on the current checkout (`74` tests)
- HTTP contract selftest passes
- capability matrix validation passes
- release evidence is now generated from the current commit and validates against the active early-beta release gate

The codebase currently provides a coherent native-only AI stack around:

- MCP-oriented service orchestration
- compile/execute split with trace and audit bundle generation
- HTTP adapter and local bridge runtime
- deterministic retrieval, plan, execution-mode, audit, and cluster-routing helpers

## 2. Readiness by Area

| Area | Status | Notes |
| --- | --- | --- |
| Core service orchestration | Green | `ScratchBirdAIService` covers compile, execute, read-only query flow, mutation gating, explain, and retrieval surfaces |
| Native-only routing and capability matrix | Green | Router and matrix loader are enforced fail-closed for non-native dialects |
| HTTP adapter and bridge runtime | Green | Adapter, bridge endpoints, auth checks, and service round-trip tests pass |
| Tool schema and policy guardrails | Green | Strict payload validation, error envelopes, mode normalization, and hard limits are implemented |
| Retrieval helpers | Green | Engine-free vector and hybrid retrieval paths exist with deterministic ranking and tenant isolation checks |
| Deterministic plan/audit/routing helpers | Green | Plan hashing, audit replay, and cluster-routing/failover behavior are covered by tests and release evidence |
| Native live-workload hardening | Yellow | Selftest and in-process flows are solid; broader live ScratchBird workload validation is still limited |
| Mutation governance maturity | Yellow | Approval-gated mutation path exists, but durable approval evidence and production policy workflow are not complete |
| Operations hardening | Yellow | Development/runtime controls exist, but quotas, SLO packaging, rate limits, and full resilience policy are not complete |

## 3. Verification Snapshot

Validated on 2026-03-07 with Python 3.12.3:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'` passed (`74` tests)
- `PYTHONPATH=src python3 tools/validate_capability_matrix.py` passed
- `PYTHONPATH=src python3 tools/smoke_http_contract.py --mode selftest` passed
- `python3 tools/generate_ai_conformance_artifacts.py --repo-root .` passed
- `python3 tools/validate_evidence_gates.py --repo-root . --spec docs/releases/EARLY_BETA_CONFORMANCE_GATES.md` passed

## 4. Implemented Surface Since The Initial Snapshot

The implemented code surface now includes verified modules for:

- retrieval: vector search and hybrid search with deterministic ordering
- plan introspection: deterministic plan hashing and stable payload normalization
- execution-mode governance: canonical modes, approvals, and hard resource ceilings
- deterministic audit bundles: replay and tamper detection helpers
- cluster-aware routing: shard selection, replica failover, and deterministic merge ordering
- bridge connectivity depth: managed, listener-only, `ipc-only`, and `embedded` option mapping through the Python driver interface

## 5. Key Risks

- Live native workload coverage is still thinner than the in-process and fake-backend coverage.
- Compile-repair behavior described in backlog/spec drafts is not implemented yet.
- Durable approval evidence, quotas, and rate limiting remain backlog work.
- Structured operational packaging exists as code-level controls and evidence, not as a full production runbook/SLO bundle.

## 6. Current Release Gate Position

Release-gate status is now based on the implemented early-beta surface in [EARLY_BETA_CONFORMANCE_GATES.md](/home/dcalford/CliWork/ScratchBird-ai/docs/releases/EARLY_BETA_CONFORMANCE_GATES.md), not on the older research-oriented adapter matrix.

That means the repository can produce truthful current evidence for what is actually shipped today.

## 7. Recommended Next Actions

1. Implement the bounded compile-repair loop and add negative/repair evidence for it.
2. Add live native integration evidence against a real ScratchBird server, not only selftest and fake backends.
3. Finish durable approval evidence, quotas, and resilience controls so P2 can move from scaffold to production-hardening.
