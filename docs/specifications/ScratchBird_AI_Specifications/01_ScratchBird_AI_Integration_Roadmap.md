# ScratchBird AI Integration Roadmap (2026-2027)

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Purpose

Define the implementation program that upgrades `ScratchBird-ai` from early-beta scaffolding to a production-grade AI-governed data platform with deterministic behavior, explicit security boundaries, and measurable conformance.

This roadmap is normative for sequencing and gate criteria. Feature details are defined in specifications `02` through `10`.

## 2. Normative Language

The keywords MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL are interpreted as described in RFC 2119.

## 3. Non-Negotiable Invariants

1. Parser/compiler-first execution boundary:
   - SQL text MUST be compiled through parser/compiler adapters before execution.
   - Engine execution remains SBLR/internal-procedure only.
2. Fail-closed security posture:
   - Unknown capability, unknown mode, invalid approval evidence, and invalid security context MUST deny execution.
3. RLS integrity:
   - AI execution MUST NOT bypass row-level security under any mode.
4. Deterministic artifacts:
   - `compile_artifact_id`, `plan_hash`, and `security_context_hash` MUST be deterministic under identical canonical input.
5. Mutable operations are gated:
   - Mutation execution MUST require verified approval evidence and complete audit bundle emission.

## 4. Canonical Program Phases

### Phase 1: Ecosystem Entry

Scope:
- Stable tool contract for read-only query + metadata + explain.
- LangChain/LlamaIndex adapter foundations.
- Deterministic compile artifact generation and trace wiring.

Exit Gates (all REQUIRED):
1. Tool-calling schema conformance suite passes 100%.
2. Read-only query path passes negative tests for mutation denial.
3. Deterministic `compile_artifact_id` and `plan_hash` tests pass across 3 repeated runs.
4. p95 read query latency measurement pipeline is active.

### Phase 2: Governance and Introspection

Scope:
- AI execution state machine and approval-evidence validation.
- Plan introspection API with deterministic plan hashing.
- Deterministic audit bundle creation and replay validation.
- Vector and hybrid retrieval contracts with RLS guarantees.

Exit Gates (all REQUIRED):
1. Mutation execution is impossible without valid approval evidence.
2. Audit bundle replay validator reproduces pass/fail outcomes deterministically.
3. RLS conformance matrix passes for SQL, vector, and hybrid paths.
4. Policy denial logs include rule identifier and decision reason in 100% of denied requests.

### Phase 3: Cluster-Aware Runtime

Scope:
- Cluster topology introspection.
- Query/vector routing based on shard ownership and policy.
- Distributed vector search with deterministic merge ordering.

Exit Gates (all REQUIRED):
1. `get_cluster_topology`, `route_query`, and `distributed_vector_search` pass contract tests.
2. Shard isolation violations are blocked in all tested scenarios.
3. Routing fallback behavior is deterministic and auditable.
4. Cluster epoch mismatch handling is fail-closed.

### Phase 4: Enterprise Certification

Scope:
- SLO/SLA operational hardening.
- Security and governance certification evidence.
- Compatibility and version pinning across parser/compiler/driver/runtime.

Exit Gates (all REQUIRED):
1. Version compatibility checks are enforced at startup and deny mismatched deployments.
2. p95/p99 and error-budget objectives meet target for 30-day certification run.
3. Security test battery (authn/authz/RLS/approval replay/injection) passes.
4. Operational runbooks and recovery procedures are validated in game-day tests.

## 5. Release Gates and Promotion Policy

1. A phase cannot be marked complete unless all mandatory gates pass.
2. Any SHOULD-level requirement promoted to MUST by implementation SHALL be reflected in the corresponding spec in the same change set.
3. Open questions are prohibited at phase completion. Remaining unknowns MUST be converted to explicit assumptions with owner/date or deferred to future non-blocking phase scope.

## 6. Dependency and Sequencing Rules

1. Specifications must be implemented in this order:
   - `08` execution mode and `06` tool schema before mutation enablement.
   - `07` plan introspection before `09` deterministic audit bundle finalization.
   - `04` vector API before `05` hybrid retrieval API.
   - `10` cluster routing after `04` and `05` local-node behavior is certified.
2. Backward compatibility:
   - Legacy tool aliases MAY be kept during migration, but canonical names from `06` must remain source-of-truth.
3. Contract changes:
   - Breaking schema changes require explicit version increment and migration notes.

## 7. Governance Principles

1. AI MUST NOT bypass RLS.
2. Compile/execute separation is mandatory.
3. Deterministic artifact generation is mandatory for compile/plan/audit content.
4. Mutation requires verified approval evidence and immutable audit emission.
5. Unknown security context or unknown tenant identity MUST fail closed.

## 8. Conformance Ownership

1. Spec owners for each document are responsible for CI conformance checks.
2. A requirement without an automated conformance test is considered incomplete.
3. Any production exception to a MUST requirement requires documented waiver, expiry date, and owner.

## 9. No-Gap Clause

If an implementation decision is not explicitly specified in documents `02` through `10`, the default behavior MUST be:
1. deny the operation,
2. emit a deterministic policy error,
3. persist an audit event with decision context.

## 10. Evidence Binding

1. This roadmap is bound to evidence gate `EVID-01` in `12_External_Evidence_Traceability.md`.
2. Phase completion claims MUST provide `artifacts/ai_conformance/01/summary.json` with `status=PASS`.
3. A phase MAY NOT be marked complete if its `EVID-01` proof artifact is missing, stale, or failed.
