# ScratchBird MCP Database Server Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define the MCP-facing tool contract for exposing ScratchBird AI/data access capabilities to external AI clients and agent runtimes.

## 2. Scope

- In scope:
- Tool schema definitions
- Access policy enforcement at tool boundary
- Read-only baseline and mutation gating
- Contract versioning rules

- Out of scope:
- Non-MCP transports
- Engine-side execution internals

## 3. Dependencies

- `docs/specifications/drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`
- ScratchBird parser/compiler and execution services

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Server MUST publish a discoverable MCP tool catalog.
- FR-002: Each tool MUST validate arguments against strict schemas.
- FR-003: `run_query` MUST route through compile->execute pipeline.
- FR-004: Server MUST provide metadata tools for schema/table/column discovery.
- FR-005: Mutation tools MUST be disabled by default and require explicit approval mode.

### 4.2 Non-Functional Requirements

- NFR-001: Tool responses MUST be structured JSON.
- NFR-002: Server MUST enforce timeout and result-size ceilings.

## 5. Tool Contract

Required tools (v0):

- `get_capabilities()`
- `list_dialects()`
- `list_schemas(dialect, database)`
- `list_tables(dialect, schema)`
- `describe_table(dialect, schema, table)`
- `compile_query(dialect, query_text, context)`
- `execute_compiled(compile_artifact_id, options)`
- `run_query(dialect, query_text, options)`
- `explain_query(dialect, query_text, options)`

Dialect scope note (v0):

- `list_dialects()` currently returns `native` only.

Optional tools (approval-gated):

- `run_mutation(dialect, query_text, approval_token)`

## 6. Security and Governance

- All tools MUST run with authenticated caller identity.
- Tool-level RBAC MUST distinguish introspection/read/mutation scopes.
- Server MUST reject attempts to override policy via prompt text.

## 7. Observability

- Metrics per tool: request count, success/failure, latency p50/p95/p99.
- Audit event per tool call with policy decision and artifact references.

## 8. Testing and Acceptance Criteria

- Contract tests for each tool input/output schema.
- Negative tests for invalid argument payloads.
- Policy tests proving mutation rejection without approval.
- Interop tests with at least one MCP-compatible client runtime.

## 9. Rollout Plan

- Phase 1: metadata + `run_query` read-only.
- Phase 2: compile/explain tools + capability metadata.
- Phase 3: approval-gated mutation tools.

## 10. Open Questions

- Q1: Will remote MCP transport require OAuth in initial release or phase 2?
- Q2: Should `run_query` return raw rows only or rows + model-ready summary payload?
