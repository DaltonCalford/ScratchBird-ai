# ScratchBird AI Cross-Spec Conformance Matrix

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Purpose

Provide a single checklist that proves every mandatory requirement in specifications `01` through `10` has:
1. a defined implementation contract,
2. an explicit test obligation,
3. an evidence-bound parity gate,
4. a release gate owner.

## 2. Matrix

| Spec | Requirement Domain | Evidence ID | Required Automated Test Family | Required Proof Artifacts | Gate Owner |
|---|---|---|---|---|---|
| `01` | Phase gates and sequencing | `EVID-01` | phase gate CI checks | `artifacts/ai_conformance/01/summary.json` | AI Platform Lead |
| `02` | LangChain adapters | `EVID-02` | adapter contract + policy + determinism tests | `artifacts/ai_conformance/02/adapter_parity.json`, `artifacts/ai_conformance/02/test_report.junit.xml` | Adapter Lead |
| `03` | LlamaIndex adapters | `EVID-03` | interface + RLS + explain determinism tests | `artifacts/ai_conformance/03/adapter_parity.json`, `artifacts/ai_conformance/03/test_report.junit.xml` | Adapter Lead |
| `04` | Vector API | `EVID-04` | schema + RLS + benchmark + determinism tests | `artifacts/ai_conformance/04/vector_api_report.json`, `artifacts/ai_conformance/04/benchmark.csv` | Retrieval Lead |
| `05` | Hybrid retrieval | `EVID-05` | pushdown + ranking determinism + RLS tests | `artifacts/ai_conformance/05/hybrid_report.json`, `artifacts/ai_conformance/05/relevance_eval.json` | Retrieval Lead |
| `06` | Tool schemas | `EVID-06` | schema validation + alias compatibility tests | `artifacts/ai_conformance/06/schema_report.json`, `artifacts/ai_conformance/06/compat_report.json` | MCP Lead |
| `07` | Plan introspection | `EVID-07` | plan hash determinism + redaction + plan-diff tests | `artifacts/ai_conformance/07/plan_hash_report.json`, `artifacts/ai_conformance/07/diff_report.json` | Query Introspection Lead |
| `08` | Execution mode | `EVID-08` | state-machine + approval + limits tests | `artifacts/ai_conformance/08/mode_matrix.json`, `artifacts/ai_conformance/08/policy_simulation.json` | Policy Lead |
| `09` | Audit bundle | `EVID-09` | replay validation + hash determinism + attestation tests | `artifacts/ai_conformance/09/audit_replay_report.json`, `artifacts/ai_conformance/09/attestation_report.json` | Governance Lead |
| `10` | Cluster routing | `EVID-10` | topology + routing + failover + isolation tests | `artifacts/ai_conformance/10/routing_report.json`, `artifacts/ai_conformance/10/failover_report.json` | Cluster Lead |
| `11` | Cross-spec integrity | `EVID-11` | matrix consistency and ownership checks | `artifacts/ai_conformance/11/matrix_status.json` | Release Governance Lead |

## 3. Release-Domain Exceed Requirement

For production promotion, at least one exceed gate MUST pass in each domain defined by `12_External_Evidence_Traceability.md`:
1. adapter/tool domain,
2. retrieval domain,
3. governance/audit domain,
4. runtime/introspection domain.

A release with all parity gates passing but missing any domain-level exceed evidence MUST remain pre-production.

## 4. Mandatory Completion Rule

A requirement is incomplete unless:
1. contract language exists in its spec,
2. automated conformance tests exist,
3. CI job includes those tests,
4. required proof artifacts exist and are parseable,
5. owning lead is assigned.

## 5. Fail-Closed Policy

If any conformance item above is missing at runtime:
1. corresponding feature MUST remain disabled,
2. API/tool MUST return deterministic policy denial,
3. denial MUST be audit logged.

## 6. Traceability Binding

1. This matrix is normatively bound to `12_External_Evidence_Traceability.md`.
2. A change to any `EVID-*` gate requires same-change-set updates to:
   - this matrix,
   - spec `12`,
   - `docs/library/00_index/COMPARATIVE_PARITY_MATRIX.md`.
