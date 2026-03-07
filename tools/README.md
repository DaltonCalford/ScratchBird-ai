# Tools

Local helper scripts for validation, evidence generation, and stack startup.

- `tools/validate_capability_matrix.py` validates `docs/specifications/drafts/capability-matrix/capability-matrix.v0.json`.
- `tools/generate_ai_conformance_artifacts.py` regenerates `artifacts/ai_conformance/` for the current commit.
- `tools/validate_evidence_gates.py` validates release evidence artifacts against `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`.
- `tools/run_local_bridge.sh` starts the HTTP bridge (`python -m scratchbird_ai.http_bridge`).
- `tools/run_local_stack.sh` starts bridge + MCP server in one command for local adapter testing.
- `tools/smoke_http_contract.py` runs HTTP contract smoke tests (`--mode selftest` or `--mode live`).
