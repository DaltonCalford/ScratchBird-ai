# ScratchBird Semantic Kernel Adapter Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the Semantic Kernel adapter contract for `ScratchBird-ai` under the current architecture.

This specification covers Semantic Kernel plugin and function-invocation compatibility while preserving the same canonical policy, compile, execute, retrieval, and audit rules used elsewhere in `ScratchBird-ai`.

## 2. Scope

- In scope:
- Semantic Kernel plugin and function exposure for canonical `ScratchBird-ai` operations
- plugin/function mapping to canonical tool descriptors
- native-only, parser-first query execution
- policy-aware query, explain, vector, and hybrid operations
- structured output and canonical error mapping for Semantic Kernel usage

- Out of scope:
- Semantic Kernel internal planner behavior
- non-native dialect support
- provider-specific SDK concerns outside Semantic Kernel integration
- alternate execution paths outside canonical `ScratchBird-ai` operations

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Research input:
- `docs/library/03_frameworks_protocols/semantic_kernel_plugins.html`
- `docs/library/03_frameworks_protocols/semantic_kernel_function_calling.html`

- Internal components:
- `ScratchBirdAIService`
- canonical tool operations
- policy engine
- plan, audit, and retrieval helpers

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: The Semantic Kernel adapter profile MUST correspond to `semantic_kernel_v0` from the interface-coverage program.
- FR-002: The adapter MUST expose canonical `ScratchBird-ai` operations as Semantic Kernel-compatible functions or plugins.
- FR-003: Semantic Kernel invocation MUST normalize into canonical tool descriptors and canonical invocation envelopes before execution.
- FR-004: SQL-like operations MUST remain parser-first and MUST not bypass compile/execute separation.
- FR-005: Read-only default mode and approval-gated mutation behavior MUST be preserved after Semantic Kernel normalization.
- FR-006: The adapter MUST support metadata, query, explain, vector, and hybrid operations through plugin/function mapping.
- FR-007: Semantic Kernel-facing structured outputs MUST bind to the canonical structured-output model.
- FR-008: Plugin or function names MUST remain namespace-safe and deterministic for a given release.
- FR-009: Unsupported Semantic Kernel capabilities MUST fail closed with deterministic compatibility or capability errors.
- FR-010: Semantic Kernel integration MUST not depend on prompt text to carry authorization or approval state.

### 4.2 Non-Functional Requirements

- NFR-001: Function exposure and plugin naming MUST be deterministic for a given adapter version.
- NFR-002: Compatibility targets MUST be declared explicitly before support is claimed.
- NFR-003: Canonical trace IDs and audit identifiers MUST survive Semantic Kernel integration boundaries.

## 5. Adapter Surfaces

### 5.1 Canonical Semantic Kernel Integration Modes

The adapter should support:

- `plugin_mode`: expose canonical operations as Semantic Kernel plugins/functions
- `function_invocation_mode`: normalize function calls into canonical tool invocations
- `retrieval_plugin_mode`: expose vector and hybrid search as retrieval-oriented plugin functions

### 5.2 Canonical Operation Mapping

The adapter MUST map Semantic Kernel-visible behavior to:

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

### 5.3 Namespace and Function Rules

The adapter MUST define deterministic plugin and function naming rules:

- names SHOULD remain stable for a given release
- names MUST not leak secrets, tenant identifiers, or runtime environment state
- name transformation rules required by Semantic Kernel or underlying providers MUST not change canonical operation meaning

## 6. Compatibility Contract

The adapter MUST declare runtime compatibility targets before support is claimed.

Initial implementation guidance:

- prioritize one officially supported Semantic Kernel runtime profile first
- add additional runtime profiles only when evidence exists per profile

No active support claim exists until:

- the adapter is implemented,
- the interface profile is marked `implemented`,
- compatibility and conformance evidence is published

## 7. Security and Governance

- Authentication/authorization:
- Semantic Kernel functions MUST require canonical security context or an explicitly negotiated equivalent session binding
- framework-local planner state MUST not be treated as authoritative policy input

- Mode handling:
- read-only is the default
- mutation remains approval-gated

- Auditability:
- adapter flows SHOULD record `interface_profile_id = semantic_kernel_v0`
- plugin and function invocation identifiers SHOULD be auditable alongside canonical operation names

## 8. Error Handling

The adapter MUST preserve or map failures into canonical errors including:

- `E_POLICY_DENY`
- `E_TOOL_INPUT_INVALID`
- `E_STRUCTURED_OUTPUT_INVALID`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`
- `E_COMPATIBILITY_MISMATCH`

Semantic Kernel-local exceptions MUST not become the primary public contract.

## 9. Observability

- Logs:
- plugin name
- function name
- interface profile ID
- trace ID
- policy outcome

- Metrics:
- function invocation count
- validation failure count
- mutation denial count
- query and retrieval latency

- Traces:
- canonical trace propagation MUST survive Semantic Kernel adaptation and function invocation boundaries

## 10. Testing and Acceptance Criteria

- Unit tests:
- plugin/function descriptor normalization
- deterministic naming behavior
- canonical error mapping
- security-context requirement enforcement

- Integration tests:
- read-only query success
- denied and approved mutation flows
- explain flow with canonical `plan_hash`
- vector and hybrid retrieval success

- Regression tests:
- unsupported profile or capability rejection
- incompatible runtime profile rejection
- function name transformation preserving canonical operation identity

- Exit criteria:
- `semantic_kernel_v0` may not be marked implemented without tests and evidence
- no Semantic Kernel adapter path may bypass canonical compile, policy, retrieval, or audit rules

## 11. Evidence Binding

This draft is not part of the active early-beta release gate.

When implemented, Semantic Kernel support MUST be added to:

- interface-profile inventory updates
- compatibility evidence
- future live conformance and certification evidence

## 12. Open Questions

- Q1: Should the first Semantic Kernel profile prioritize plugin/function invocation only, or include planner-oriented helpers in the initial release?
- Q2: Should the first supported Semantic Kernel runtime profile be limited to one language/runtime at a time for clearer evidence and compatibility control?
