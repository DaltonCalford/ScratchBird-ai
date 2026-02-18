# ScratchBird HTTP Bridge Runtime Specification

Status: Draft  
Owner: ScratchBird AI Team  
Last Updated: 2026-02-18

## 1. Purpose

Define the runtime behavior of the local HTTP bridge used by `ScratchBird-ai` HTTP adapters.

## 2. Scope

- In scope:
- Local bridge service and request contracts
- Runtime configuration and auth controls
- Compile/execute/metadata behavior for driver-backed mode

- Out of scope:
- Production API gateway concerns
- ScratchBird engine internals
- Non-HTTP transports

## 3. Runtime Module

Reference implementation:

- `src/scratchbird_ai/http_bridge.py`
- CLI entrypoint: `scratchbird-ai-http-bridge`

## 4. Supported Endpoints

- `GET /healthz`
- `POST /v1/dialects/{dialect}/compile`
- `POST /v1/dialects/{dialect}/execute`
- `GET /v1/dialects/{dialect}/schemas`
- `GET /v1/dialects/{dialect}/schemas/{schema}/tables`
- `GET /v1/dialects/{dialect}/schemas/{schema}/tables/{table}`

Payload contracts match `SCRATCHBIRD_HTTP_ADAPTER_CONTRACT_SPEC.md`.

## 5. Runtime Configuration

- `SCRATCHBIRD_AI_BRIDGE_HOST` (default `127.0.0.1`)
- `SCRATCHBIRD_AI_BRIDGE_PORT` (default `3095`)
- `SCRATCHBIRD_AI_BRIDGE_API_TOKEN` (optional bearer token)
- `SCRATCHBIRD_AI_BRIDGE_REQUEST_MAX_BYTES` (default `2097152`)
- `SCRATCHBIRD_AI_BRIDGE_DIALECTS` (default `native`)
- `SCRATCHBIRD_AI_BRIDGE_DEFAULT_DSN` (fallback DSN for enabled dialects)
- `SCRATCHBIRD_AI_BRIDGE_DSN_<DIALECT>` (dialect-specific DSN)
- `SCRATCHBIRD_AI_BRIDGE_PYTHON_DRIVER_SRC` (ScratchBird Python driver source path)
- `SCRATCHBIRD_AI_BRIDGE_STRICT_COMPILE` (if true, compile probe failures return errors)

## 6. Backend Mode (Current)

Current backend mode uses the ScratchBird Python driver:

- Driver module: `scratchbird` from `ScratchBird-driver`
- Compile path:
- Read statements attempt describe-only compile probe to collect SBLR hash when available
- Mutation/unknown statements return classified type and fallback hash without probe execution
- Execute path:
- Submits SQL text to parser/wire adapter flow (driver path), where SQL is compiled to SBLR before engine execution
- Returns row objects plus notices from the executed statement

Execution-boundary invariant:

- This bridge does not define a second engine execution path.
- Engine execution boundary remains `ServerSession` in ScratchBird core.

## 7. Auth and Security

- If `SCRATCHBIRD_AI_BRIDGE_API_TOKEN` is set, requests must send:
- `Authorization: Bearer <token>`
- Request body size is capped via `SCRATCHBIRD_AI_BRIDGE_REQUEST_MAX_BYTES`.

## 8. Error Handling

- 400: invalid payload shape / bad request
- 401: token required or invalid
- 404: route missing or dialect not enabled
- 413: request body too large
- 501: metadata or describe operation not available for configured target
- 503: upstream connection failure

## 9. Open Follow-Ups

- Add a non-driver backend that calls parser/engine microservices directly.
- Standardize metadata SQL behavior for native runtime edge cases.
- Add compile artifact persistence in bridge layer (optional optimization).
