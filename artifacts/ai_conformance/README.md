# AI Conformance Artifacts

This tree contains release-gating proof artifacts referenced by:

- `docs/specifications/ScratchBird_AI_Specifications/12_External_Evidence_Traceability.md`
- `docs/specifications/ScratchBird_AI_Specifications/11_Cross_Spec_Conformance_Matrix.md`

## Layout

- `01/summary.json`
- `02/adapter_parity.json`, `02/test_report.junit.xml`
- `03/adapter_parity.json`, `03/test_report.junit.xml`
- `04/vector_api_report.json`, `04/benchmark.csv`
- `05/hybrid_report.json`, `05/relevance_eval.json`
- `06/schema_report.json`, `06/compat_report.json`
- `07/plan_hash_report.json`, `07/diff_report.json`
- `08/mode_matrix.json`, `08/policy_simulation.json`
- `09/audit_replay_report.json`, `09/attestation_report.json`
- `10/routing_report.json`, `10/failover_report.json`
- `11/matrix_status.json`

## Template Note

Template JSON files are initialized with `status: FAIL` intentionally.
They are placeholders and MUST be replaced by real CI-produced evidence before release.

## Validation

Run:

```bash
python tools/validate_evidence_gates.py --repo-root .
```

This command enforces artifact shape, age, status rules, and cross-artifact `git_commit` consistency.
