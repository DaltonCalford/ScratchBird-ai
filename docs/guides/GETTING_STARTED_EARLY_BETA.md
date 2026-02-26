# Getting Started (Early Beta)

Status: Active  
Last Updated: 2026-02-18

## 1. Goal

Bring up `ScratchBird-ai` locally for early beta validation:

- run tests
- run bridge
- run MCP stack
- run HTTP contract smoke tests

Support scope note:

- This repository currently supports **native** dialect workflows only.

## 2. Prerequisites

- Linux/macOS shell
- Python `3.11+`
- ScratchBird server reachable (for live bridge mode)
- ScratchBird Python driver source or package (for live bridge mode)

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
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
PYTHONPATH=src tools/validate_capability_matrix.py
PYTHONPATH=src tools/smoke_http_contract.py --mode selftest
```

Expected outcome:

- test suite passes
- capability matrix validator exits `0`
- smoke script prints `[smoke] PASS`

## 5. Configure Bridge (Live Mode)

Copy and edit:

```bash
cp examples/http-bridge.env.example .env.bridge
```

Minimum required variables:

- `SCRATCHBIRD_AI_BRIDGE_DEFAULT_DSN`
- `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC` if driver is not pip-installed
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
- `404 Dialect not enabled`: include dialect in `SCRATCHBIRD_AI_BRIDGE_DIALECTS`.
- `400 Managed setup requires manager_auth_token`: set `SCRATCHBIRD_AI_BRIDGE_MANAGER_AUTH_TOKEN` or include `manager_auth_token` in DSN.
- `503 Connection failed` in `ipc-only`/`embedded`: verify the Python driver build supports those transport modes.
- `503 Connection failed`: verify DSN and ScratchBird server reachability.
