# ScratchBird LlamaIndex Adapter Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the LlamaIndex adapter contract for `ScratchBird-ai` under the current architecture.

This rewrite replaces the older expansion-oriented LlamaIndex material as the active draft direction for framework integration. The adapter defined here is a compatibility layer over canonical `ScratchBird-ai` operations and interface profiles.

## 2. Scope

- In scope:
- LlamaIndex-compatible query, tool, vector, and retriever surfaces
- normalization of LlamaIndex requests into canonical `ScratchBird-ai` operations
- native-only, parser-first query execution
- secure plan/explain and retrieval integration
- canonical error, mode, and audit semantics for LlamaIndex usage

- Out of scope:
- LlamaIndex internal orchestration behavior
- non-native dialect support
- model selection or embedding-provider policy
- alternate execution or retrieval paths outside the canonical service contract

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Historical input:
- `docs/specifications/ScratchBird_AI_Specifications/03_LlamaIndex_Adapter_Specification.md`

- Internal components:
- `ScratchBirdAIService`
- canonical explain and retrieval operations
- policy engine
- plan and audit helpers

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: The LlamaIndex adapter profile MUST correspond to `llamaindex_v0` from the interface-coverage program.
- FR-002: The adapter MUST expose LlamaIndex-compatible query, tool, vector, or retriever surfaces that normalize to canonical `ScratchBird-ai` operations.
- FR-003: Query flows MUST compile before execution and MUST not introduce direct execution shortcuts.
- FR-004: The adapter MUST preserve native-only dialect policy for the initial profile.
- FR-005: Explain or plan-introspection results MUST preserve canonical `plan_hash`, normalized operator tree, and RLS-safe visibility metadata.
- FR-006: Vector and hybrid retrieval wrappers MUST preserve tenant isolation and canonical retrieval semantics.
- FR-007: Mutation requests through the adapter MUST preserve canonical mode and approval-evidence rules.
- FR-008: LlamaIndex-facing exceptions MUST map into the canonical error contract before being surfaced externally.
- FR-009: Structured outputs returned to LlamaIndex consumers MUST follow the provider-neutral structured-output contract.
- FR-010: Unsupported LlamaIndex patterns MUST fail closed and report deterministic compatibility or capability errors.

### 4.2 Non-Functional Requirements

- NFR-001: Equivalent explain calls SHOULD produce deterministic `plan_hash` values for a given release.
- NFR-002: Adapter compatibility targets MUST be declared explicitly and not inferred from transitive dependencies.
- NFR-003: Retrieval ordering and explain normalization MUST be reproducible and testable.

## 5. Compatibility Contract

Initial target compatibility window:

- `llama-index-core >=0.11,<0.12`

No active support claim exists until:

- the adapter is implemented,
- the interface profile is marked `implemented`,
- compatibility and conformance evidence is published.

## 6. Adapter Surfaces

### 6.1 Canonical LlamaIndex Integration Modes

The adapter should support these integration modes:

- `query_engine_mode`: query and explain compatibility layer
- `tool_mode`: tool-calling integration over canonical operations
- `vector_store_mode`: vector retrieval compatibility layer
- `retriever_mode`: hybrid retrieval compatibility layer

### 6.2 Canonical Operation Mapping

The adapter MUST normalize LlamaIndex-visible behavior into canonical operations:

- metadata discovery
- read-only query execution
- approval-gated mutation execution
- explain query
- vector search
- hybrid search

Where LlamaIndex expects different abstraction names, the mapping MUST still preserve canonical semantics and error handling.

### 6.3 Query and Explain Contract

Required query and explain behavior:

- query requests normalize to canonical query execution inputs
- explain requests normalize to canonical explain inputs
- query responses SHOULD preserve:
  - `trace_id`
  - `compile_artifact_id`
  - `execution_artifact_id`
- explain responses SHOULD preserve:
  - `trace_id`
  - `plan_hash`
  - `operator_tree`
  - `rls_visibility`

### 6.4 Retrieval Contract

Vector and retriever wrappers MUST preserve:

- required `security_context`
- same-tenant access only
- canonical dimension validation
- canonical filter semantics
- deterministic ordering for equivalent result sets

## 7. Security and Governance

- Authentication/authorization:
- the adapter MUST require explicit security context for query and retrieval operations
- framework-local state MUST not override server-side policy

- Mode handling:
- read-only remains the default behavior
- mutation remains approval-gated

- Auditability:
- adapter flows SHOULD record `interface_profile_id = llamaindex_v0`
- explain and retrieval flows SHOULD remain traceable to canonical audit outputs

## 8. Error Handling

The adapter MUST preserve or map failures into canonical errors including:

- `E_POLICY_DENY`
- `E_DIALECT_UNAVAILABLE`
- `E_TOOL_INPUT_INVALID`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`
- `E_COMPATIBILITY_MISMATCH`
- `E_STRUCTURED_OUTPUT_INVALID`

Framework-local exceptions MUST not become the primary contract surface.

## 9. Observability

- Logs:
- interface profile ID
- operation class
- trace ID
- policy outcome
- explain or retrieval outcome

- Metrics:
- query success and denial counts
- explain latency
- retrieval latency
- compatibility rejection count

- Traces:
- canonical trace propagation MUST survive LlamaIndex integration boundaries

## 10. Testing and Acceptance Criteria

- Unit tests:
- query and explain normalization
- retrieval normalization
- required security-context enforcement
- canonical error mapping

- Integration tests:
- read-only query success
- approved and denied mutation flows
- explain flow with deterministic `plan_hash`
- vector and hybrid retrieval success and same-tenant enforcement

- Regression tests:
- cross-tenant retrieval denial
- unsupported dialect rejection
- compatibility-window mismatch rejection

- Exit criteria:
- `llamaindex_v0` may not be marked implemented without tests and evidence
- no adapter path may bypass canonical compile, policy, retrieval, or audit rules

## 11. Evidence Binding

This draft is not part of the active early-beta release gate.

When implemented, LlamaIndex support MUST be bound to:

- interface-profile inventory updates
- compatibility evidence
- future live conformance and certification evidence

## 12. Open Questions

- Q1: Should the first LlamaIndex implementation prioritize query-engine compatibility, tool-calling compatibility, or both together?
- Q2: Should vector store and hybrid retriever layers ship in the first LlamaIndex profile, or after query/explain support is stable?
