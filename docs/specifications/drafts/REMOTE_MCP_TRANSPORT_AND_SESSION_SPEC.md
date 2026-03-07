# ScratchBird Remote MCP Transport and Session Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the remotely reachable MCP transport and session contract for `ScratchBird-ai`.

This specification exists because the current MCP draft focuses on tool semantics, but does not define how remote clients authenticate, negotiate compatibility, establish sessions, stream long-running results, cancel work, or close connections safely.

The goal is to make remote MCP access explicit without creating an alternate execution or authorization model.

## 2. Scope

- In scope:
- remote MCP session establishment
- transport negotiation
- authentication and session binding
- request lifecycle for tool calls over remote transports
- long-running operation events, cancellation, and session close behavior
- compatibility checks between client and server interface profiles

- Out of scope:
- local stdio MCP behavior
- non-MCP framework adapters
- provider-specific tool-calling contracts
- HTTP bridge internal compile or execute APIs
- engine-side execution behavior

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`

- Final architecture decisions:
- `docs/specifications/final/ADR-0002_QUERY_ENTRYPOINT_AND_SBLR_POLICY.md`
- `docs/specifications/final/ADR-0003_SERVER_EXECUTION_BOUNDARY_AND_ADAPTER_ROLE.md`

- Internal components:
- MCP server entrypoint
- policy engine
- capability advertisement surface
- trace and audit bundle helpers

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Remote MCP access MUST use the canonical `mcp_remote_v0` interface profile defined by the interface-coverage program.
- FR-002: The server MUST require explicit session establishment before handling remote tool execution.
- FR-003: Session establishment MUST negotiate protocol version, transport mode, and capability compatibility.
- FR-004: Remote tool calls MUST bind to the same canonical policy, mode, compile, execute, and audit semantics as local MCP usage.
- FR-005: The server MUST support deterministic session termination and cancellation semantics.
- FR-006: Long-running operations MUST expose progress or completion state through a defined event model when streaming is enabled.
- FR-007: Unsupported transport or streaming requests MUST fail closed with deterministic compatibility errors.
- FR-008: Remote MCP access MUST not expose internal bridge endpoints as client-facing substitutes for MCP session behavior.
- FR-009: Authentication state MUST be bound to the session server-side and MUST not be inferred from prompt content or client-supplied tool arguments.
- FR-010: Every remote MCP request MUST be attributable to a session, trace, and interface profile.

### 4.2 Non-Functional Requirements

- NFR-001: Session negotiation MUST be deterministic for a given client capability set and server release.
- NFR-002: Session expiration and invalidation behavior MUST be explicit and testable.
- NFR-003: Remote transport behavior MUST preserve trace propagation and audit correlation.
- NFR-004: Transport negotiation MUST be versioned so incompatible clients fail cleanly.

## 5. Transport Model

### 5.1 Supported Transport Classes

The remote MCP program defines these transport classes:

- `https_json_request_response`: baseline request/response transport for remote MCP calls
- `https_sse_server_stream`: request/response plus server-stream events for long-running operations
- `websocket_bidirectional`: deferred bidirectional mode for future expansion

Current support policy:

- baseline implementation target: `https_json_request_response`
- optional expansion target: `https_sse_server_stream`
- deferred target: `websocket_bidirectional`

### 5.2 Session Requirement

Remote MCP clients MUST establish a session before invoking tools over remote transport.

Session state MUST bind:

- authenticated caller identity
- negotiated protocol version
- negotiated transport class
- interface profile ID
- session expiry metadata
- server-generated trace correlation seed

## 6. Interfaces and Contracts

### 6.1 Session Open Request

The remote session-open request MUST be normalizable to:

- `request_id`
- `interface_profile_id`
- `protocol_version`
- `requested_transport`
- `client_id`
- `client_version`
- `client_capabilities`
- `auth_envelope`
- `security_context_hint` (optional)

### 6.2 Session Open Response

The session-open response MUST include:

- `request_id`
- `session_id`
- `interface_profile_id`
- `negotiated_protocol_version`
- `negotiated_transport`
- `session_expires_at`
- `heartbeat_interval_sec`
- `capability_advertisement`
- `trace_seed`
- `warnings[]`

### 6.3 Invocation Envelope

Every remote MCP invocation MUST be normalizable to:

- `session_id`
- `request_id`
- `method`
- `params`
- `client_operation_timeout_ms` (optional)
- `stream_requested` (bool)
- `cancellation_token` (optional)

### 6.4 Invocation Response

Every remote MCP invocation response MUST be normalizable to:

- `session_id`
- `request_id`
- `status`
- `trace_id`
- `result` or `error`
- `operation_state` (`completed` | `running` | `cancelled` | `failed`)
- `stream_channel` or `null`
- `notices[]`

### 6.5 Streaming Event Envelope

When streaming is enabled, the server MUST emit event payloads that include:

- `session_id`
- `request_id`
- `trace_id`
- `event_type`
- `sequence_no`
- `timestamp_utc`
- `payload`

Minimum event types:

- `ack`
- `progress`
- `partial_result`
- `notice`
- `completed`
- `failed`
- `cancelled`

### 6.6 Cancellation Contract

Cancellation requests MUST include:

- `session_id`
- `request_id`
- `target_request_id`
- `reason`

The server MUST respond deterministically with:

- `accepted`
- `already_completed`
- `unknown_request`
- `session_invalid`

### 6.7 Session Close Contract

Session close MUST invalidate further tool execution under that session ID.

The close response MUST be idempotent for already-closed sessions.

## 7. Compatibility and Negotiation Rules

- The client MUST declare `interface_profile_id = mcp_remote_v0` during remote negotiation.
- The server MUST reject unknown interface profile IDs.
- The server MUST reject unsupported transport classes even if the MCP method set is otherwise valid.
- Version negotiation MUST fail closed when client and server protocol versions are incompatible.
- Capability advertisement after session open MUST reflect the negotiated profile and transport, not only the server's full internal capability set.

## 8. Security and Governance

- Authentication/authorization:
- Remote sessions MUST authenticate before they are considered active.
- Authenticated identity MUST be bound to the session and re-used for subsequent requests.
- Session-auth context MAY be refreshed only through explicit server-defined re-auth flows.

- Data handling and redaction:
- Access tokens, OAuth assertions, API keys, and provider secrets MUST never be returned in capability or session payloads.
- Session logs MUST record auth outcome and interface profile, but MUST not persist raw bearer material.

- Auditability:
- Session open, tool invocation, cancellation, expiry, and close events MUST be auditable.
- Audit records for remote MCP traffic MUST include `interface_profile_id = mcp_remote_v0`.

## 9. Observability

- Logs:
- session open and close
- negotiation outcome
- transport downgrade or rejection
- per-invocation status and cancellation outcome

- Metrics:
- active sessions
- session open failures
- transport negotiation failures
- cancellation requests
- stream start and completion counts

- Traces:
- one root trace per remote invocation
- session ID linked to trace metadata

## 10. Testing and Acceptance Criteria

- Unit tests:
- session negotiation normalization
- transport compatibility checks
- cancellation state transitions
- session expiry handling

- Integration tests:
- remote session open -> tool invocation -> close
- failed auth -> deterministic denial
- long-running operation event flow where streaming is enabled
- cancellation before completion and after completion

- Regression tests:
- unsupported transport rejection
- interface profile mismatch rejection
- stale or expired session rejection

- Exit criteria:
- remote MCP cannot be marked implemented until remote session lifecycle tests pass
- capability advertisement must reflect negotiated transport/profile state
- unsupported remote features must fail closed with deterministic errors

## 11. Rollout Plan

- Phase 1:
- define remote session and transport contract
- keep `mcp_remote_v0` in draft status

- Phase 2:
- implement baseline `https_json_request_response`
- add auth and compatibility negotiation tests

- Phase 3:
- add `https_sse_server_stream`
- add cancellation and long-running event certification

## 12. Open Questions

- Q1: Should the first remote MCP implementation use bearer-token auth only, or require OAuth-compatible flows from the start?
- Q2: Should streaming be introduced only after baseline request/response remote MCP is stable, or must it be part of the initial remote profile?
