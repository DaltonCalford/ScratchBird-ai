# Getting Started (Early Beta)

Status: Active
Last Updated: 2026-03-07

## 1. Goal

Bring up `ScratchBird-ai` locally for current early-beta validation:

- run tests
- validate the capability matrix
- generate and validate release evidence
- run the local HTTP bridge
- run the MCP stack
- run HTTP contract smoke tests

Support scope note:

- This repository currently supports **native** dialect workflows only.

## 2. Prerequisites

- Linux/macOS shell
- Python `3.11+`
- ScratchBird server reachable when using live bridge mode
- ScratchBird Python driver source or package when using live bridge mode

## 3. Install

```bash
cd ~/CliWork/ScratchBird-ai
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ".[mcp]"
```

## 4. Validate Baseline

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONPATH=src python3 tools/validate_capability_matrix.py
PYTHONPATH=src python3 tools/smoke_http_contract.py --mode selftest
python3 tools/generate_ai_conformance_artifacts.py --repo-root .
python3 tools/validate_evidence_gates.py --repo-root . --spec docs/releases/EARLY_BETA_CONFORMANCE_GATES.md
```

Expected outcome:

- discovered test suite passes
- capability matrix validator exits `0`
- smoke script prints `[smoke] PASS`
- conformance artifacts are regenerated for the current commit
- evidence validator prints `OK: evidence gates valid ...`

## 5. Configure Bridge (Live Mode)

Copy and edit:

```bash
cp examples/http-bridge.env.example .env.bridge
```

Minimum required variables:

- `SCRATCHBIRD_AI_BRIDGE_DEFAULT_DSN`
- `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC` if the driver is not pip-installed
- `SCRATCHBIRD_AI_BRIDGE_SERVER_SETUP` when not using `listener-only` (valid: `managed`, `ipc-only`, `embedded`)

Managed setup additional requirement:

- `SCRATCHBIRD_AI_BRIDGE_MANAGER_AUTH_TOKEN` (or `mcp` alias)

Optional security:

- `SCRATCHBIRD_AI_BRIDGE_API_TOKEN`

## 6. Run Bridge

```bash
set -a
source .env.bridge
set +a
PYTHONPATH=src tools/run_local_bridge.sh
```

## 7. Run Full Local Stack

In another shell:

```bash
set -a
source .env.bridge
set +a
export SCRATCHBIRD_AI_ADAPTER_MODE=http
export SCRATCHBIRD_AI_HTTP_BASE_URL="http://${SCRATCHBIRD_AI_BRIDGE_HOST:-127.0.0.1}:${SCRATCHBIRD_AI_BRIDGE_PORT:-3095}"
export SCRATCHBIRD_AI_HTTP_API_TOKEN="${SCRATCHBIRD_AI_BRIDGE_API_TOKEN:-}"
PYTHONPATH=src tools/run_local_stack.sh
```

## 8. Run Live Contract Smoke Test

```bash
set -a
source .env.bridge
set +a
export SCRATCHBIRD_AI_HTTP_BASE_URL="http://${SCRATCHBIRD_AI_BRIDGE_HOST:-127.0.0.1}:${SCRATCHBIRD_AI_BRIDGE_PORT:-3095}"
export SCRATCHBIRD_AI_HTTP_API_TOKEN="${SCRATCHBIRD_AI_BRIDGE_API_TOKEN:-}"
PYTHONPATH=src tools/smoke_http_contract.py --mode live --dialect native
```

## 9. Common Failures

- `ImportError: scratchbird`: set `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC` to the driver `src` path.
- `401 Unauthorized`: set matching `SCRATCHBIRD_AI_HTTP_API_TOKEN` and `SCRATCHBIRD_AI_BRIDGE_API_TOKEN`.
- `404 Dialect not enabled`: include `native` in `SCRATCHBIRD_AI_BRIDGE_DIALECTS`.
- `400 Managed setup requires manager_auth_token`: set `SCRATCHBIRD_AI_BRIDGE_MANAGER_AUTH_TOKEN` or include `manager_auth_token` in DSN.
- `503 Connection failed` in `ipc-only` or `embedded`: verify the Python driver build supports those transport modes.
- `503 Connection failed`: verify DSN and ScratchBird server reachability.
