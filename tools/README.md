# Tools

Local helper scripts for linting, validation, and generation tasks.

- `tools/validate_capability_matrix.py` validates `docs/specifications/drafts/capability-matrix/capability-matrix.v0.json`.
- `tools/run_local_bridge.sh` starts the HTTP bridge (`python -m scratchbird_ai.http_bridge`).
- `tools/run_local_stack.sh` starts bridge + MCP server in one command for local adapter testing.
- `tools/smoke_http_contract.py` runs HTTP contract smoke tests (`--mode selftest` or `--mode live`).
