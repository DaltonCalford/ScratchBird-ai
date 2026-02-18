# Source

Implementation code for ScratchBird AI integration.

## Package Layout

- `scratchbird_ai/contracts.py` - request/response contracts
- `scratchbird_ai/capability_matrix.py` - matrix loading utilities
- `scratchbird_ai/router.py` - dialect routing + capability gating
- `scratchbird_ai/policy.py` - read-only and approval policy enforcement
- `scratchbird_ai/service.py` - compile/execute orchestration service
- `scratchbird_ai/mcp_server.py` - MCP tool server registration and entrypoint
- `scratchbird_ai/adapters/` - backend adapter interfaces and scaffolding adapters

## Local Usage

- Validate matrix: `./tools/validate_capability_matrix.py`
- Run tests: `python3 -m unittest discover -s tests -p "test_*.py"`
- Run MCP server (after installing optional deps):
  - `pip install .[mcp]`
  - `scratchbird-ai-mcp`

## Adapter Configuration

Environment variables:

- `SCRATCHBIRD_AI_ADAPTER_MODE` - `mock`, `http`, or `hybrid` (default: `mock`)
- `SCRATCHBIRD_AI_HTTP_BASE_URL` - HTTP service base URL for real adapters
- `SCRATCHBIRD_AI_HTTP_TIMEOUT_SEC` - adapter HTTP timeout in seconds
- `SCRATCHBIRD_AI_HTTP_API_TOKEN` - optional Bearer token
- `SCRATCHBIRD_AI_HTTP_DIALECTS` - comma-separated dialects for HTTP mode in `hybrid` (default `native`)

Support scope:

- AI runtime support in this repository is native-only.

See `docs/specifications/drafts/SCRATCHBIRD_HTTP_ADAPTER_CONTRACT_SPEC.md` for endpoint contracts.
