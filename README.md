# ScratchBird-ai

`ScratchBird-ai` is the AI integration layer for ScratchBird.  
This repository contains the MCP tool server, dialect-aware query orchestration, and adapter infrastructure used to connect AI workflows to ScratchBird parser/compiler and execution paths.

Current release track: **initial early beta** (`0.1.0`)  
Status timestamp: **February 18, 2026**

## Support Policy

`ScratchBird-ai` supports **ScratchBird native engine workflows only**.

- Native-only AI support is in scope for this repository.
- Emulated external engines are out of scope for this repository's AI layer.
- External engine teams are expected to maintain their own engine-native AI integrations.
- Non-native dialect requests are rejected with explicit policy errors.
- ScratchBird engine execution boundary remains `ServerSession`; SQL must be compiled to SBLR before engine submission.

## Early Beta Scope

Included in this release:

- MCP server scaffold with database-oriented tools.
- Safe-by-default policy path with read-only mode and approval-gated mutation mode.
- Compile/execute split orchestration with artifact identifiers and trace IDs.
- Dialect capability matrix loader and runtime routing gates.
- HTTP adapter mode (`mock`, `http`, `hybrid`) for parser/executor integration.
- Local HTTP bridge implementation for adapter contract testing and integration.
- CI checks for lint/type/build, capability matrix validation, and tests.

Not included in this release:

- Production-grade authz, quota billing, and multi-tenant hard isolation.
- AI support for non-native emulated engine modes.
- Finalized write-governance workflow for production operations.

## Quick Start

### 1. Prerequisites

- Python `3.11+`
- Access to ScratchBird server and Python driver when using live bridge mode

### 2. Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ".[mcp]"
```

### 3. Validate Locally

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
PYTHONPATH=src tools/smoke_http_contract.py --mode selftest
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
- `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC`: path to ScratchBird Python driver `src/`
- `SCRATCHBIRD_AI_BRIDGE_STRICT_COMPILE`: fail compile endpoint if compile probe fails

Reference example:

- `examples/http-bridge.env.example`

## Repository Layout

- `docs/` - release, status, planning, specification, and reference documentation
- `src/` - package source (`scratchbird_ai`)
- `tests/` - unit and integration tests
- `examples/` - runtime configuration examples
- `tools/` - local scripts for validation, smoke testing, and stack startup

## Documentation Map

- Start here: `docs/README.md`
- Early beta release notes: `docs/releases/INITIAL_EARLY_BETA_RELEASE_2026-02-18.md`
- Current status: `docs/status/EARLY_BETA_STATUS_2026-02-18.md`
- Getting started guide: `docs/guides/GETTING_STARTED_EARLY_BETA.md`
- Draft/final specs: `docs/specifications/`
- Delivery backlog: `docs/planning/PHASED_IMPLEMENTATION_BACKLOG.md`
