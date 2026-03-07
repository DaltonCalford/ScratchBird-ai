# AI Conformance Artifacts

This tree contains release-gating proof artifacts for the active early-beta release contract:

- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`

## Layout

- `01/summary.json`
- `02/adapter_parity.json`, `02/test_report.junit.xml`
- `03/service_surface.json`, `03/test_report.junit.xml`
- `04/vector_api_report.json`, `04/benchmark.csv`
- `05/hybrid_report.json`, `05/relevance_eval.json`
- `06/schema_report.json`, `06/compat_report.json`
- `07/plan_hash_report.json`, `07/diff_report.json`
- `08/mode_matrix.json`, `08/policy_simulation.json`
- `09/audit_replay_report.json`, `09/attestation_report.json`
- `10/routing_report.json`, `10/failover_report.json`
- `11/matrix_status.json`
- `12/framework_parity.json`, `12/test_report.junit.xml`
- `13/provider_parity.json`, `13/test_report.junit.xml`

## Regeneration

Artifacts are generated from the current checkout and are not meant to remain static forever.

Run:

```bash
python3 tools/generate_ai_conformance_artifacts.py --repo-root .
python3 tools/validate_evidence_gates.py --repo-root . --spec docs/releases/EARLY_BETA_CONFORMANCE_GATES.md
```

## Validation Rules

The validator enforces:

- required JSON fields
- `PASS` vs `FAIL` consistency
- stale-artifact age limits
- cross-artifact `git_commit` consistency
- CSV/JUnit structure checks
