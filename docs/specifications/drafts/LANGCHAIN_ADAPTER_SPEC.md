# ScratchBird LangChain Adapter Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the LangChain adapter contract for `ScratchBird-ai` under the current architecture.

This rewrite replaces the older expansion-oriented LangChain material as the active draft direction for framework integration. The adapter defined here is a compatibility layer over canonical `ScratchBird-ai` operations, not an alternate execution stack.

## 2. Scope

- In scope:
- LangChain-compatible tool and runnable surfaces
- mapping LangChain calls to canonical `ScratchBird-ai` operations
- native-only, parser-first query execution
- retrieval integration using the canonical vector and hybrid search model
- canonical error and policy mapping into LangChain-facing envelopes

- Out of scope:
- LangChain internal scheduler behavior
- non-native dialect support
- direct provider SDK behavior outside LangChain
- alternate execution paths that bypass parser/compiler-first rules

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Historical input:
- `docs/specifications/ScratchBird_AI_Specifications/02_LangChain_Adapter_Specification.md`

- Internal components:
- `ScratchBirdAIService`
- canonical tool operations
- retrieval helpers
- policy engine
- plan/audit helpers

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: The LangChain adapter profile MUST correspond to `langchain_v0` from the interface-coverage program.
- FR-002: The adapter MUST expose LangChain-compatible tools or runnables that normalize into canonical `ScratchBird-ai` tool operations.
- FR-003: SQL-like operations MUST compile before execution and MUST never bypass parser/compiler-first flow.
- FR-004: The adapter MUST preserve native-only dialect policy unless future specs explicitly expand it.
- FR-005: Read-only default mode and approval-gated mutation mode MUST be preserved after LangChain normalization.
- FR-006: The adapter MUST support canonical metadata, query, explain, vector, and hybrid operations.
- FR-007: Retrieval-oriented LangChain wrappers MUST enforce tenant isolation and canonical security-context requirements.
- FR-008: LangChain-facing exceptions and tool failures MUST map into the canonical error model before being surfaced.
- FR-009: The adapter MUST support structured tool outputs through the provider-neutral structured-output contract.
- FR-010: Unsupported LangChain features MUST fail closed rather than silently degrade semantics.

### 4.2 Non-Functional Requirements

- NFR-001: Adapter output for equivalent canonical calls SHOULD be deterministic for a given release.
- NFR-002: Tool descriptor and schema exposure for LangChain usage MUST be versioned.
- NFR-003: Adapter compatibility targets MUST be declared explicitly and validated by release evidence before support is claimed.

## 5. Compatibility Contract

Initial target compatibility window:

- `langchain-core >=0.3,<0.4`
- `langchain-community >=0.3,<0.4`

No compatibility claim is active until:

- the adapter is implemented,
- the compatibility profile is listed as `implemented`,
- conformance evidence exists for the claimed version window.

## 6. Adapter Surfaces

### 6.1 Canonical LangChain Integration Modes

The adapter should support these integration modes:

- `toolkit_mode`: expose canonical operations as LangChain tools
- `runnable_mode`: expose query and explain flows as runnable-style wrappers
- `retriever_mode`: expose vector and hybrid retrieval as retriever-compatible wrappers

### 6.2 Canonical Operation Mapping

The adapter MUST map LangChain-visible operations to the canonical `ScratchBird-ai` surface:

- `get_capabilities`
- `list_dialects`
- `list_schemas`
- `list_tables`
- `describe_table`
- `execute_readonly_query`
- `execute_mutation`
- `explain_query`
- `vector_search`
- `hybrid_search`

LangChain-specific naming MAY differ, but the semantic mapping MUST remain explicit.

### 6.3 Query and Explain Contract

Required query and explain behavior:

- query requests MUST normalize to:
  - `dialect`
  - `query_text`
  - `mode`
  - `security_context`
  - `options`
  - `approval_evidence` when required
- explain requests MUST normalize to the canonical explain/plan contract
- outputs MUST retain:
  - `trace_id`
  - `compile_artifact_id` when compilation occurred
  - `execution_artifact_id` when execution occurred
  - `plan_hash` for explain flows

### 6.4 Retrieval Contract

Vector and hybrid retrieval wrappers MUST normalize to the canonical retrieval contract:

- embeddings and query vectors are validated before execution
- same-tenant retrieval is required
- where-based structured pushdown limitations in offline mode MUST remain explicit
- deterministic ordering for equal scores MUST be preserved

## 7. Security and Governance

- Authentication/authorization:
- the adapter MUST require explicit `security_context`
- prompt or chain state MUST not be treated as authoritative policy input

- Mode handling:
- absent mode defaults to read-only analysis behavior
- mutation requests require approved mode plus valid approval evidence

- Auditability:
- LangChain adapter flows SHOULD record `interface_profile_id = langchain_v0`
- audit outputs MUST remain comparable to equivalent canonical service operations

## 8. Error Handling

The adapter MUST preserve or map failures into canonical errors including:

- `E_POLICY_DENY`
- `E_DIALECT_UNAVAILABLE`
- `E_TOOL_INPUT_INVALID`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`
- `E_COMPATIBILITY_MISMATCH`

Unknown runtime or framework-local exceptions MUST fail closed and be mapped to canonical execution or compatibility errors rather than leaking framework-specific internals as the primary contract.

## 9. Observability

- Logs:
- tool name or runnable name
- interface profile ID
- trace ID
- policy outcome
- retrieval or execution outcome

- Metrics:
- invocations by operation
- mutation denial count
- validation failure count
- retrieval latency and query latency

- Traces:
- the adapter MUST preserve canonical trace IDs across LangChain integration boundaries

## 10. Testing and Acceptance Criteria

- Unit tests:
- tool or runnable normalization
- security-context requirement enforcement
- canonical error mapping
- deterministic output normalization

- Integration tests:
- read-only query success
- mutation denial without approval
- approved mutation flow
- explain flow with stable `plan_hash`
- vector and hybrid retrieval success with same-tenant context

- Regression tests:
- unsupported dialect rejection
- unsupported LangChain feature rejection
- compatibility-window mismatch rejection

- Exit criteria:
- `langchain_v0` may not be marked implemented until tests and evidence exist
- no LangChain adapter path may bypass canonical policy, compile, or audit logic

## 11. Evidence Binding

This draft is not part of the active early-beta release gate.

When implemented, LangChain support MUST be added to:

- the interface-profile inventory as `implemented`
- compatibility evidence in the release-negotiation contract
- future live conformance and certification evidence

## 12. Open Questions

- Q1: Should the first LangChain implementation target toolkit-style usage only, or toolkit plus runnable abstractions together?
- Q2: Should retrieval wrappers ship in the initial LangChain profile, or after the query/tool surface is stable?
