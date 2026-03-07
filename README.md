# ScratchBird-ai

`ScratchBird-ai` is the AI integration layer for ScratchBird.
This repository contains the MCP-oriented service layer, dialect-aware query orchestration, HTTP adapter and bridge runtime, and deterministic governance helpers used to connect AI workflows to ScratchBird parser/compiler and execution paths.

Current release track: **initial early beta** (`0.1.0`)
Status timestamp: **March 7, 2026**

## Support Policy

`ScratchBird-ai` supports **ScratchBird native engine workflows only**.

- Native-only AI support is in scope for this repository.
- Emulated external engines are out of scope for this repository's AI layer.
- Non-native dialect requests are rejected with explicit policy errors.
- ScratchBird engine execution boundary remains `ServerSession`; SQL must be compiled to SBLR before engine submission.

## Current Early-Beta Surface

Included in the current baseline:

- MCP-oriented service orchestration with canonical tool declarations.
- Safe-by-default policy path with read-only mode and approval-gated mutation mode.
- Compile/execute split orchestration with artifact identifiers, trace IDs, and audit bundles.
- Dialect capability matrix loader and native-only routing gates.
- HTTP adapter mode (`mock`, `http`, `hybrid`) for parser/executor integration.
- Local HTTP bridge implementation for adapter contract testing and live driver-backed access.
- Engine-free vector and hybrid retrieval helpers with deterministic ranking.
- Deterministic plan hashing, execution-mode evaluation, audit replay, and cluster-routing helpers.
- Release evidence generation and validation for the implemented early-beta surface.

Not included in this release:

- Production-grade authz depth, quota billing, and full multi-tenant hard isolation.
- AI support for non-native emulated engine modes.
- Durable approval-evidence workflow for production mutation governance.
- Full live-workload certification against production-like ScratchBird deployments.

## Quick Start

### 1. Prerequisites

- Python `3.11+`
- Access to a ScratchBird server and Python driver for live bridge mode

### 2. Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ".[mcp]"
```

### 3. Validate Locally

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONPATH=src python3 tools/validate_capability_matrix.py
PYTHONPATH=src python3 tools/smoke_http_contract.py --mode selftest
python3 tools/generate_ai_conformance_artifacts.py --repo-root .
python3 tools/validate_evidence_gates.py --repo-root . --spec docs/releases/EARLY_BETA_CONFORMANCE_GATES.md
```

### 4. Run Bridge

```bash
PYTHONPATH=src tools/run_local_bridge.sh
```

### 5. Run Bridge + MCP Stack

```bash
PYTHONPATH=src tools/run_local_stack.sh
```

## Runtime Configuration

### Adapter Environment Variables

- `SCRATCHBIRD_AI_ADAPTER_MODE`: `mock`, `http`, or `hybrid` (default `mock`)
- `SCRATCHBIRD_AI_HTTP_BASE_URL`: HTTP base URL for adapter calls
- `SCRATCHBIRD_AI_HTTP_TIMEOUT_SEC`: timeout for HTTP adapter requests
- `SCRATCHBIRD_AI_HTTP_API_TOKEN`: optional Bearer token
- `SCRATCHBIRD_AI_HTTP_DIALECTS`: dialect CSV used for `hybrid` mode (default `native`)

### Bridge Environment Variables

- `SCRATCHBIRD_AI_BRIDGE_HOST`: bridge bind host (default `127.0.0.1`)
- `SCRATCHBIRD_AI_BRIDGE_PORT`: bridge bind port (default `3095`)
- `SCRATCHBIRD_AI_BRIDGE_API_TOKEN`: optional Bearer token required by bridge
- `SCRATCHBIRD_AI_BRIDGE_DIALECTS`: enabled dialect CSV (default `native`)
- `SCRATCHBIRD_AI_BRIDGE_DEFAULT_DSN`: fallback DSN for enabled dialects
- `SCRATCHBIRD_AI_BRIDGE_DSN_<DIALECT>`: per-dialect DSN override
- `SCRATCHBIRD_AI_BRIDGE_SERVER_SETUP`: `listener-only`, `managed`, `ipc-only`, or `embedded` (default `listener-only`)
- `SCRATCHBIRD_AI_BRIDGE_TRANSPORT_MODE`: explicit transport override (`inet_listener`, `managed`, `local_ipc`, `embedded`)
- `SCRATCHBIRD_AI_BRIDGE_FRONT_DOOR_MODE`: explicit front-door override (`direct`, `manager_proxy`)
- `SCRATCHBIRD_AI_BRIDGE_IPC_METHOD`: IPC method override (`auto`, `unix`, `pipe`, `tcp`)
- `SCRATCHBIRD_AI_BRIDGE_IPC_PATH`: IPC socket/pipe path override for `ipc-only`
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_AUTH_TOKEN` / `SCRATCHBIRD_AI_BRIDGE_MCP_AUTH_TOKEN`: managed signon token
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_USERNAME` / `SCRATCHBIRD_AI_BRIDGE_MCP_USERNAME`: managed username override
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_DATABASE` / `SCRATCHBIRD_AI_BRIDGE_MCP_DATABASE`: managed database override
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_CONNECTION_PROFILE` / `SCRATCHBIRD_AI_BRIDGE_MCP_CONNECTION_PROFILE`: managed connection profile (default `native_v3`)
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_CLIENT_INTENT` / `SCRATCHBIRD_AI_BRIDGE_MCP_CLIENT_INTENT`: managed client intent (default `native_v3`)
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_CLIENT_FLAGS` / `SCRATCHBIRD_AI_BRIDGE_MCP_CLIENT_FLAGS`: managed client flags (`0..65535`)
- `SCRATCHBIRD_AI_BRIDGE_MANAGER_AUTH_FAST_PATH` / `SCRATCHBIRD_AI_BRIDGE_MCP_AUTH_FAST_PATH`: managed fast-path auth toggle (default `true`)
- `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC`: path to ScratchBird Python driver `src/`
- `SCRATCHBIRD_AI_BRIDGE_STRICT_COMPILE`: fail compile endpoint if compile probe fails

Connection-mode note:

- `ScratchBird-ai` forwards mode-aware transport and signon options to the driver.
- `ipc-only` and `embedded` require a Python driver/runtime that supports those transport modes.

Reference example:

- `examples/http-bridge.env.example`

## Repository Layout

- `docs/` - release, status, planning, specification, and reference documentation
- `artifacts/` - AI conformance proof artifacts used for release gating
- `src/` - package source (`scratchbird_ai`)
- `tests/` - unit and integration tests
- `examples/` - runtime configuration examples
- `tools/` - local scripts for validation, evidence generation, and stack startup

## Documentation Map

- Start here: `docs/README.md`
- Current status: `docs/status/EARLY_BETA_STATUS_2026-03-07.md`
- Known gaps: `docs/status/EARLY_BETA_KNOWN_GAPS_2026-03-07.md`
- Release gate contract: `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`
- Getting started guide: `docs/guides/GETTING_STARTED_EARLY_BETA.md`
- Delivery backlog: `docs/planning/PHASED_IMPLEMENTATION_BACKLOG.md`
- Draft/final specs: `docs/specifications/`
