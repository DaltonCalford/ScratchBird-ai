# ScratchBird Direct Provider Compatibility Profiles Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define direct provider compatibility profiles for model runtimes that support tool calling or structured outputs without an intervening framework adapter.

This specification covers the compatibility layer for provider-native clients, such as OpenAI-style, Anthropic-style, or Gemini-style tool-calling runtimes, while preserving canonical `ScratchBird-ai` semantics.

## 2. Scope

- In scope:
- provider-native tool-calling compatibility profiles
- provider-native structured-output compatibility profiles
- normalization from provider request/response models into canonical tool and output contracts
- fail-closed handling of unsupported provider features

- Out of scope:
- provider SDK implementation details
- model selection policy
- remote MCP session transport
- framework-specific adapter behavior

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Research input:
- `docs/reference/AI_DATABASE_TOOLING_REPORT_2026-02-18.md`

- Internal components:
- canonical tool descriptors
- canonical invocation and response envelopes
- policy engine
- service operations

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Direct provider support MUST bind to `provider_tool_calling_v0` from the interface-coverage program.
- FR-002: Provider-native tool calls MUST normalize into canonical tool descriptors and invocation envelopes before execution.
- FR-003: Provider-native structured outputs MUST normalize into canonical structured-output modes and validation results.
- FR-004: Provider-specific naming, argument encoding, or tool-selection behavior MUST not change canonical operation semantics.
- FR-005: Provider-native query, mutation, explain, vector, and hybrid operations MUST preserve canonical policy and security-context rules.
- FR-006: Provider-specific unsupported features MUST fail closed with deterministic compatibility or capability errors.
- FR-007: Provider integrations MUST not treat model-produced or prompt-produced authorization data as authoritative policy input.
- FR-008: SQL-like requests routed through direct provider profiles MUST remain parser-first.
- FR-009: Provider profiles MUST declare their tool-calling and structured-output capability subsets explicitly.
- FR-010: Each provider profile MUST define how canonical errors are mapped into the provider-visible result model.

### 4.2 Non-Functional Requirements

- NFR-001: Provider compatibility profiles MUST be versioned and auditable.
- NFR-002: Equivalent canonical requests SHOULD normalize consistently across provider profiles.
- NFR-003: Provider-specific degradation behavior MUST be explicit, not silent.

## 5. Provider Profile Model

### 5.1 Canonical Provider Family

Direct provider compatibility is modeled as a family with provider-specific child profiles.

Initial planned child profiles:

- `openai_tool_calling_v0`
- `anthropic_tool_use_v0`
- `gemini_function_calling_v0`

These child profiles remain planned until individually implemented and evidenced.

### 5.2 Provider Profile Descriptor

Each provider profile MUST declare:

- `profile_id`
- `provider_name`
- `provider_runtime_family`
- `tool_calling_mode`
- `structured_output_modes[]`
- `streaming_support`
- `compatibility_version`
- `unsupported_features[]`

## 6. Interfaces and Contracts

### 6.1 Provider Request Normalization

Every provider-native request MUST normalize to:

- `request_id`
- `interface_profile_id`
- `provider_profile_id`
- `tool_name`
- `arguments`
- `security_context`
- `mode`
- `approval_evidence`
- `client_capabilities`

### 6.2 Provider Response Normalization

Every provider-native result MUST normalize to:

- `request_id`
- `interface_profile_id`
- `provider_profile_id`
- `trace_id`
- `status`
- `result`
- `structured_output`
- `error`
- `notices[]`

### 6.3 Capability Subset Rules

Each provider profile MUST explicitly state whether it supports:

- tool calling
- multi-tool calls in one turn
- structured JSON object output
- schema-bound structured output
- partial-result streaming
- cancellation or background execution correlation

Unsupported items MUST be enumerated rather than inferred.

## 7. Security and Governance

- Authentication/authorization:
- provider API credentials and provider session metadata MUST never substitute for canonical security context
- policy checks remain server-side

- Data handling and redaction:
- provider transcripts, tool payloads, and raw responses MUST follow canonical redaction rules before persistence or audit export

- Auditability:
- audit records SHOULD include `provider_profile_id`
- provider profile and canonical tool mapping SHOULD remain traceable for equivalent requests

## 8. Error Handling

Each provider profile MUST map at least:

- `E_TOOL_NOT_FOUND`
- `E_TOOL_INPUT_INVALID`
- `E_STRUCTURED_OUTPUT_INVALID`
- `E_PROVIDER_CONTRACT_UNSUPPORTED`
- `E_POLICY_DENY`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`
- `E_COMPATIBILITY_MISMATCH`

Provider-native errors MAY be preserved as supplemental metadata, but canonical error identity remains primary.

## 9. Observability

- Logs:
- provider profile ID
- canonical tool name
- normalization outcome
- validation outcome
- policy and execution outcome

- Metrics:
- calls by provider profile
- schema mismatch count
- unsupported-feature rejection count
- mutation denial count

- Traces:
- canonical trace IDs MUST survive provider adaptation boundaries

## 10. Testing and Acceptance Criteria

- Unit tests:
- provider-profile descriptor validation
- request normalization
- response normalization
- structured-output compatibility validation

- Integration tests:
- one implemented provider profile MUST execute canonical operations end-to-end
- multi-provider equivalence tests SHOULD compare normalized outputs for equivalent canonical requests

- Regression tests:
- unsupported provider feature rejection
- provider profile drift detection
- canonical error mapping stability

- Exit criteria:
- no provider profile may be marked implemented without tests and evidence
- no direct provider support claim may exist without explicit profile-level compatibility declaration

## 11. Evidence Binding

This draft is not part of the active early-beta release gate.

When implemented, direct provider profiles MUST be added to:

- interface-profile inventory updates
- compatibility evidence
- future live conformance and certification evidence

## 12. Open Questions

- Q1: Which provider profile should be implemented first: OpenAI-style tool calling, Anthropic-style tool use, or Gemini-style function calling?
- Q2: Should background or asynchronous provider execution be modeled inside this spec, or only through the streaming/long-running operation spec?
