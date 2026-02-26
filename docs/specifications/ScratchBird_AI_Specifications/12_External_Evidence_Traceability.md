# ScratchBird AI External Evidence Traceability Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define mandatory evidence binding between specifications `01` through `11` and the research library in `docs/library/`, including explicit pass/fail gates for parity and exceed claims.

## 2. Mandatory Evidence Rule

1. Every spec requirement group listed in Section 3 MUST map to an evidence ID (`EVID-*`).
2. A release candidate MUST provide machine-readable proof artifacts for every `EVID-*` row.
3. Missing, stale, or unparseable evidence artifacts MUST fail release gating.
4. All proof artifacts for a release candidate MUST reference the same `git_commit`.

## 3. Evidence IDs and Gates

| Evidence ID | Bound spec(s) | Required baseline references (local paths) | Minimum parity gate (all required) | Exceed gate candidates (at least one per release domain) | Required proof artifact(s) |
| --- | --- | --- | --- | --- | --- |
| `EVID-01` | `01` | `docs/library/00_index/TASK_MATRIX.md`, `docs/library/00_index/COVERAGE_REPORT.md` | Phase gates map to implemented CI jobs and owning lead | Cross-phase automation removes manual waiver path for at least one gate | `artifacts/ai_conformance/01/summary.json` |
| `EVID-02` | `02` | `docs/library/03_frameworks_protocols/langchain_*`, `docs/library/03_frameworks_protocols/langgraph_*` | LangChain adapter supports canonical tools, mode enforcement, deterministic IDs, standard errors | Deterministic normalized output parity across LangChain and at least one non-LangChain orchestrator | `artifacts/ai_conformance/02/adapter_parity.json`, `artifacts/ai_conformance/02/test_report.junit.xml` |
| `EVID-03` | `03` | `docs/library/03_frameworks_protocols/llamaindex_*` | LlamaIndex adapter enforces compile-then-execute, RLS, plan metadata determinism | Cross-framework replay harness reproduces identical plan hashes for equivalent queries | `artifacts/ai_conformance/03/adapter_parity.json`, `artifacts/ai_conformance/03/test_report.junit.xml` |
| `EVID-04` | `04` | `docs/library/04_vector_hybrid/*`, `docs/library/06_comparative_tools/hnsw_paper_1603_09320.pdf` | Vector API validates schema/dimensions, enforces RLS, deterministic ordering, and target latency gates | Index strategy auto-tuning improves quality-latency frontier versus fixed baseline run | `artifacts/ai_conformance/04/vector_api_report.json`, `artifacts/ai_conformance/04/benchmark.csv` |
| `EVID-05` | `05` | `docs/library/04_vector_hybrid/*`, `docs/library/06_comparative_tools/rrf_sigir_2009.pdf`, `docs/library/06_comparative_tools/beir_benchmark_2104_08663.pdf` | Hybrid retrieval enforces filter pushdown, deterministic ranking, weighted fusion validation | Query-class adaptive fusion outperforms fixed weights on defined offline corpus | `artifacts/ai_conformance/05/hybrid_report.json`, `artifacts/ai_conformance/05/relevance_eval.json` |
| `EVID-06` | `06` | `docs/library/01_core_standards/json_schema_2020-12_*`, `docs/library/01_core_standards/mcp_*`, `docs/library/03_frameworks_protocols/*tool*` | Tool schema validation, standard error envelope, alias compatibility, and governance checks pass | Backward-compatible schema evolution check prevents breaking drift automatically | `artifacts/ai_conformance/06/schema_report.json`, `artifacts/ai_conformance/06/compat_report.json` |
| `EVID-07` | `07` | `docs/library/05_planning_introspection/*explain*`, `docs/library/05_planning_introspection/*profile*` | Plan API returns deterministic hash, stable operator tree, and security-safe output | Plan diff diagnostics detect and classify planner regressions automatically | `artifacts/ai_conformance/07/plan_hash_report.json`, `artifacts/ai_conformance/07/diff_report.json` |
| `EVID-08` | `08` | `docs/library/02_security_governance/nist_ai_rmf_*`, `docs/library/02_security_governance/owasp_*` | Mode state machine, approval verification, and resource limits enforced before execution | Policy simulation covers all allowed transitions and denial states with zero unclassified outcomes | `artifacts/ai_conformance/08/mode_matrix.json`, `artifacts/ai_conformance/08/policy_simulation.json` |
| `EVID-09` | `09` | `docs/library/01_core_standards/rfc8785.txt`, `docs/library/05_planning_introspection/rfc3161.txt`, `docs/library/05_planning_introspection/rfc6962.txt`, `docs/library/05_planning_introspection/in_toto_*`, `docs/library/05_planning_introspection/slsa_*` | Audit bundle immutability, deterministic hashes, and replay outcomes validated | Signed attestations and tamper-evidence verification integrated into CI replay stage | `artifacts/ai_conformance/09/audit_replay_report.json`, `artifacts/ai_conformance/09/attestation_report.json` |
| `EVID-10` | `10` | `docs/library/01_core_standards/mcp_*transport*`, `docs/library/02_security_governance/otel_*`, `docs/library/04_vector_hybrid/opensearch_hybrid_*` | Cluster routing enforces epoch checks, shard isolation, deterministic merge ordering, fail-closed on ownership ambiguity | SLO-aware routing policy reduces timeout-induced degradation versus static routing baseline | `artifacts/ai_conformance/10/routing_report.json`, `artifacts/ai_conformance/10/failover_report.json` |
| `EVID-11` | `11` | `docs/library/00_index/COMPARATIVE_PARITY_MATRIX.md`, `docs/library/00_index/COVERAGE_REPORT.md` | Cross-spec matrix reflects current implementation/test status with no missing owner | Auto-generated cross-spec status dashboard with release-block reasons | `artifacts/ai_conformance/11/matrix_status.json` |

## 4. Release-Domain Exceed Requirement

In addition to all minimum parity gates, release candidates MUST show at least one accepted exceed gate in each domain:
1. Adapter/tool domain: one of `EVID-02`, `EVID-03`, `EVID-06`
2. Retrieval domain: one of `EVID-04`, `EVID-05`
3. Governance/audit domain: one of `EVID-08`, `EVID-09`
4. Runtime/introspection domain: one of `EVID-07`, `EVID-10`

## 5. Proof Artifact Rules

1. Every required proof artifact path in Section 3 MUST exist.
2. Every JSON proof artifact MUST include:
   - `generated_at_utc`
   - `git_commit`
   - `status` (`PASS|FAIL`)
   - `check_count`
   - `passed_checks`
   - `failed_checks` (array)
3. JSON artifacts with `status=PASS` MUST satisfy:
   - `failed_checks` length equals `0`
   - `passed_checks` equals `check_count`
4. JSON artifacts with `status=FAIL` MUST have non-empty `failed_checks`.
5. `generated_at_utc` older than 14 days from release candidate build time MUST fail unless waived by governance owner.
6. Non-JSON proof artifacts MUST satisfy:
   - `*.csv` contains a header row and at least one data row
   - `*.junit.xml` is well-formed XML with at least one test case
7. Any missing field or failed validation listed above MUST be treated as `status=FAIL`.

Reference validator command:

```bash
python tools/validate_evidence_gates.py --repo-root .
```

## 6. Failure Policy

If any `EVID-*` gate fails:
1. corresponding feature MUST be marked non-production-ready,
2. public interfaces for that feature MUST return deterministic denial where applicable,
3. failure details MUST be recorded in release notes and governance audit output.

## 7. Change Control

1. Changes to Section 3 gate definitions require updates to:
   - `11_Cross_Spec_Conformance_Matrix.md`
   - `docs/library/00_index/COMPARATIVE_PARITY_MATRIX.md`
2. Gate weakening (removing checks or lowering thresholds) requires explicit owner approval and dated rationale.
