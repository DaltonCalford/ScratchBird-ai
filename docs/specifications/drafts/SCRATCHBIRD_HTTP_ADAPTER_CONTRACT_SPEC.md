# ScratchBird HTTP Adapter Contract Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define the HTTP contracts used by `ScratchBird-ai` adapters to call parser/compiler and execution services.

## 2. Scope

- In scope:
- Compile endpoint contract
- Execute endpoint contract
- Metadata endpoint contracts

- Out of scope:
- Transport security deployment specifics
- Internal engine/parser implementation details

## 3. Base URL and Auth

Configuration variables:

- `SCRATCHBIRD_AI_HTTP_BASE_URL`
- `SCRATCHBIRD_AI_HTTP_TIMEOUT_SEC`
- `SCRATCHBIRD_AI_HTTP_API_TOKEN` (optional Bearer token)

## 4. Endpoint Contracts

### 4.1 Compile

- Method: `POST`
- Path: `/v1/dialects/{dialect}/compile`
- Request JSON:
  - `query_text` (string)
  - `context` (object)
- Response JSON:
  - `statement_kind` (`read|mutation|unknown`)
  - `sblr_hash` (string)
  - `diagnostics` (string[])
  - `warnings` (string[])

### 4.2 Execute

- Method: `POST`
- Path: `/v1/dialects/{dialect}/execute`
- Request JSON:
  - `compile_artifact_id` (string)
  - `query_text` (string)
  - `options` (object)
- Response JSON:
  - `rows` (object[])
  - `notices` (string[])

### 4.3 List Schemas

- Method: `GET`
- Path: `/v1/dialects/{dialect}/schemas`
- Query params:
  - `database` (optional)
- Response JSON:
  - either string[] directly
  - or `{ "schemas": string[] }`

### 4.4 List Tables

- Method: `GET`
- Path: `/v1/dialects/{dialect}/schemas/{schema}/tables`
- Response JSON:
  - either string[] directly
  - or `{ "tables": string[] }`

### 4.5 Describe Table

- Method: `GET`
- Path: `/v1/dialects/{dialect}/schemas/{schema}/tables/{table}`
- Response JSON:
  - object containing table metadata (including column list)

## 5. Error Handling

- Non-JSON responses are invalid.
- Invalid payload shape is treated as adapter error.
- Runtime must fail closed for unsupported operations.

## 6. Open Questions

- Q1: Should compile return a stable `compile_artifact_id` from upstream service?
- Q2: Should metadata responses be standardized to object shape only (remove list shorthand)?
