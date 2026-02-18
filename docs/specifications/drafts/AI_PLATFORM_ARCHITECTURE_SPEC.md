# ScratchBird AI Platform Architecture Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define the target architecture for `ScratchBird-ai`: a production AI integration layer that supports direct and indirect data access while preserving ScratchBird parser/SBLR/engine boundaries.

Initial implementation scope in this repository is native-only.

## 2. Scope

- In scope:
- MCP-compatible tool server
- NL-to-query orchestration
- Dialect-aware routing and capability gating
- Policy/governance controls for tool execution
- Retrieval pipelines (structured and unstructured)
- Audit, observability, and evaluation

- Out of scope:
- ScratchBird engine internals
- Dialect parser implementation details inside core repo
- Non-ScratchBird storage engine behavior

## 3. Dependencies

- Reference docs:
- `docs/reference/AI_DATABASE_TOOLING_REPORT_2026-02-18.md`

- External protocols/APIs:
- MCP tool interface model
- LLM function/tool calling runtime

- Internal components:
- ScratchBird parser/compiler services
- ScratchBird SBLR execution endpoints
- ScratchBird catalog/metadata surfaces

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Platform MUST support both direct structured query workflows and indirect retrieval workflows.
- FR-002: Platform MUST route AI query requests by dialect and capability profile.
- FR-003: SQL-like requests MUST compile through parser/compiler entrypoints before execution.
- FR-004: Platform MUST provide a standard tool contract consumable by MCP-capable clients.
- FR-005: Platform MUST support read-only and approved mutation modes with explicit policy controls.
- FR-006: Platform MUST expose schema and metadata introspection APIs for planning and grounding.
- FR-007: Platform MUST provide end-to-end traceability from user prompt to executed statement artifacts.
- FR-008: Platform integration MUST preserve single engine execution boundary (`ServerSession`) and treat protocol adapters as parser/wire translation layers.

### 4.2 Non-Functional Requirements

- NFR-001: p95 tool call latency for metadata and bounded read queries MUST be measured and published.
- NFR-002: All tool operations MUST emit structured logs with redaction policy.
- NFR-003: Access control MUST enforce tenant/user isolation at execution boundaries.
- NFR-004: System MUST fail closed for unknown dialect capability or policy decisions.

## 5. Interfaces and Contracts

- Input schemas:
- `QueryRequest`:
  - `request_id` (string)
  - `user_id` (string)
  - `tenant_id` (string)
  - `dialect` (enum)
  - `prompt_or_query` (string)
  - `mode` (`read_only` | `mutation_with_approval`)
  - `context` (object)

- Output schemas:
- `QueryResponse`:
  - `request_id`
  - `compile_artifact_id`
  - `execution_artifact_id`
  - `result_rows` (bounded)
  - `notices`
  - `trace_id`

- Error model:
- `E_POLICY_DENY`
- `E_DIALECT_UNAVAILABLE`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`

## 6. Security and Governance

- Authentication/authorization:
- Caller identity MUST be authenticated before tool execution.
- Authorization MUST be evaluated server-side, not by model instruction.

- Data handling and redaction:
- Logs MUST avoid raw secret material and sensitive field values.

- Auditability:
- Every request MUST persist a minimal audit tuple:
  - actor, action, target, policy decision, compile hash, execution hash, timestamp.

## 7. Observability

- Logs:
- Structured JSON logs for each stage (route, compile, execute, summarize).

- Metrics:
- Request volume, policy denials, compile failures, execution failures, timeout rate, token usage.

- Traces:
- End-to-end trace IDs across orchestration and database operations.

## 8. Testing and Acceptance Criteria

- Unit tests:
- Dialect router decisions
- Policy rule evaluation
- Contract schema validation

- Integration tests:
- MCP client -> AI tool server -> compile -> execute path
- Read-only and approval-gated mutation flows

- Regression tests:
- Dialect capability drift
- Prompt-injection resistance for tool misuse attempts

- Exit criteria:
- All mandatory FR/NFR checks pass in CI.
- Security controls validated with negative tests.

## 9. Rollout Plan

- Phase 1: Read-only direct query + schema introspection + trace logging.
- Phase 2: MCP standardization + retrieval augmentation + evaluation harness.
- Phase 3: Controlled mutation workflows + approval chain + native operations hardening.

## 10. Open Questions

- Q1: Should compile and execute be co-located in one service or split by internal RPC?
- Q2: What versioning policy will bind `ScratchBird-ai` releases to `ScratchBird` parser/compiler compatibility?
