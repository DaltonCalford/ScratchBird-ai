# ScratchBird Streaming and Long-Running Operation Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the canonical model for streaming, partial results, long-running operations, continuations, and cancellation in `ScratchBird-ai`.

This specification ensures that asynchronous or streaming behavior remains consistent across remote MCP, direct provider profiles, and future framework adapters.

## 2. Scope

- In scope:
- operation states for long-running work
- partial-result and progress event model
- continuation and resumability concepts
- cancellation model
- streaming compatibility rules

- Out of scope:
- provider-specific wire framing details
- remote session establishment
- engine-internal job execution design
- queueing or scheduling implementation details

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Research input:
- `docs/reference/AI_DATABASE_TOOLING_REPORT_2026-02-18.md`
- `docs/library/01_core_standards/mcp_2025-11-25_transports.html`

- Internal components:
- canonical request/response envelopes
- trace and audit helpers
- policy engine

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Long-running operations MUST use the `streaming_async_v0` profile from the interface-coverage program.
- FR-002: Every long-running operation MUST expose a deterministic operation identifier.
- FR-003: Every long-running operation MUST expose explicit operation state.
- FR-004: Streaming-capable interfaces MUST use the same canonical event types for progress, notices, partial results, completion, and failure.
- FR-005: Cancellation MUST be explicit and deterministic.
- FR-006: Interfaces that do not support streaming MUST reject streaming requests explicitly rather than silently downgrading.
- FR-007: Partial results MUST identify whether they are final, append-only, or replaceable snapshots.
- FR-008: Continuation or resume behavior MUST declare whether the operation is resumable and how clients reattach.
- FR-009: Long-running operations MUST preserve canonical policy and security context for their full lifetime.
- FR-010: Long-running operations MUST remain auditable and traceable through completion or cancellation.

### 4.2 Non-Functional Requirements

- NFR-001: Event ordering MUST be deterministic for a given transport and operation.
- NFR-002: Operation-state transitions MUST be testable and fail closed on invalid transitions.
- NFR-003: Streaming and long-running behavior MUST expose explicit backpressure or truncation semantics where applicable.

## 5. Operation Model

### 5.1 Canonical Operation States

The canonical operation states are:

- `accepted`
- `running`
- `partially_completed`
- `completed`
- `failed`
- `cancel_requested`
- `cancelled`
- `expired`

### 5.2 Canonical Event Types

Minimum event types:

- `accepted`
- `progress`
- `partial_result`
- `notice`
- `checkpoint`
- `completed`
- `failed`
- `cancelled`

### 5.3 Partial Result Modes

Partial results MUST declare one of:

- `append`: additively extends previous partial output
- `replace`: supersedes previous partial output
- `final`: terminal result payload

## 6. Interfaces and Contracts

### 6.1 Long-Running Invocation Request

The request MUST be normalizable to:

- `request_id`
- `interface_profile_id`
- `stream_requested`
- `allow_background_execution`
- `cancellation_token`
- `continuation_token` or `null`

### 6.2 Long-Running Invocation Response

The initial response MUST include:

- `request_id`
- `operation_id`
- `operation_state`
- `trace_id`
- `stream_channel` or `null`
- `resumable`
- `continuation_token` or `null`

### 6.3 Event Envelope

Every event emitted after acceptance MUST include:

- `operation_id`
- `request_id`
- `trace_id`
- `sequence_no`
- `event_type`
- `operation_state`
- `timestamp_utc`
- `payload`

### 6.4 Cancellation Contract

Cancellation requests MUST include:

- `operation_id`
- `request_id`
- `reason`
- `requested_by`

Cancellation responses MUST distinguish:

- accepted cancellation
- already terminal
- unknown operation
- unauthorized cancellation

### 6.5 Continuation Contract

If continuation is supported, the interface MUST define:

- whether continuation tokens are single-use or reusable
- expiry rules
- whether resumed streams replay historical events or only future events

## 7. Security and Governance

- Authentication/authorization:
- long-running operations MUST retain the original canonical security context
- cancellation and resume requests MUST be authorized against the same canonical identity or a stricter administrative identity

- Data handling and redaction:
- partial-result payloads and checkpoints MUST follow the same redaction policy as final results

- Auditability:
- operation accept, progress milestones, failure, cancellation, and completion SHOULD be auditable
- audit outputs SHOULD include `operation_id` and `interface_profile_id = streaming_async_v0`

## 8. Error Handling

The canonical long-running error set includes:

- `E_STREAM_NOT_SUPPORTED`
- `E_LONG_RUNNING_UNSUPPORTED`
- `E_INVALID_OPERATION_STATE`
- `E_CANCELLATION_REJECTED`
- `E_CONTINUATION_INVALID`
- `E_OPERATION_EXPIRED`
- `E_TIMEOUT`
- `E_POLICY_DENY`

## 9. Observability

- Logs:
- operation start and terminal state
- state transition failures
- cancellation requests and outcomes
- continuation attach or reject outcomes

- Metrics:
- active long-running operations
- cancellation rate
- failure rate
- average runtime per operation class
- expired operation count

- Traces:
- the full operation lifecycle MUST remain trace-linked from acceptance through terminal state

## 10. Testing and Acceptance Criteria

- Unit tests:
- state transition validation
- event ordering
- partial-result mode validation
- cancellation authorization and outcome mapping

- Integration tests:
- accepted -> running -> completed lifecycle
- accepted -> running -> cancelled lifecycle
- resumable operation continuation attach
- rejected streaming request on unsupported profile

- Regression tests:
- invalid state transitions
- stale continuation token rejection
- unauthorized cancellation rejection

- Exit criteria:
- no interface may claim streaming or long-running support without lifecycle tests
- unsupported streaming requests must fail closed
- operation-state transitions must be deterministic and auditable

## 11. Evidence Binding

This draft is not part of the active early-beta release gate.

When implemented, streaming and long-running support MUST be added to:

- interface-profile inventory updates
- compatibility evidence
- future live conformance and certification evidence

## 12. Open Questions

- Q1: Should continuation support be mandatory for long-running operations, or optional per profile?
- Q2: Should partial results be limited to read-only and retrieval operations initially, with mutation flows remaining strictly terminal?
