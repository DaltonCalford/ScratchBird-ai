# ScratchBird Model Tool Calling and Structured Output Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the provider-neutral contract for tool calling and structured outputs in `ScratchBird-ai`.

This specification provides the normalization layer required to support:

- MCP tool usage
- direct model-provider tool-calling clients
- framework adapters that expose tools through their own runtime abstractions

The goal is to ensure every tool invocation and every structured result follows one canonical validation, policy, error, and audit path.

## 2. Scope

- In scope:
- canonical tool descriptor model
- tool invocation normalization
- strict argument validation
- structured output modes and validation rules
- provider or framework adaptation into the canonical contract
- deterministic error mapping for tool and schema failures

- Out of scope:
- provider-specific SDK wiring details
- remote transport negotiation
- framework-specific orchestration state machines
- model selection, prompting, or ranking policy

## 3. Dependencies

- Reference docs:
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`

- Internal components:
- tool schema validation helpers
- policy engine
- capability advertisement
- canonical service operations

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Every tool exposed by `ScratchBird-ai` MUST have a canonical descriptor independent of provider or framework format.
- FR-002: Every tool invocation MUST be normalized into one canonical request envelope before policy or execution logic runs.
- FR-003: Tool arguments MUST be validated against explicit schemas before execution.
- FR-004: Invalid tool arguments MUST fail closed before reaching compile, execute, or retrieval logic.
- FR-005: Structured output claims MUST be validated against the declared output mode and schema.
- FR-006: Provider-specific or framework-specific tool formats MUST be mapped into canonical tool descriptors and canonical error envelopes.
- FR-007: Mutation-capable tools MUST preserve mode and approval-evidence requirements after normalization.
- FR-008: Tool-call results MUST be normalizable into one canonical response shape even when the upstream provider or framework expects a different envelope.
- FR-009: The contract MUST support both unstructured textual responses and schema-validated structured outputs.
- FR-010: Unsupported tool or structured-output features MUST fail closed with deterministic compatibility errors.

### 4.2 Non-Functional Requirements

- NFR-001: Tool descriptor serialization MUST be deterministic for a given release.
- NFR-002: Schema validation behavior MUST be reproducible and testable.
- NFR-003: Backward-incompatible tool schema changes MUST be versioned explicitly.
- NFR-004: Structured output validation MUST not rely on best-effort heuristics by default.

## 5. Interfaces and Contracts

### 5.1 Canonical Tool Descriptor

Every tool MUST define at least:

- `tool_name`
- `tool_version`
- `description`
- `input_schema`
- `output_mode`
- `output_schema` or `null`
- `required_security_scopes[]`
- `mode_constraints[]`
- `operation_mapping`
- `retryable` (bool)

### 5.2 Canonical Invocation Envelope

Every tool invocation MUST be normalizable to:

- `request_id`
- `interface_profile_id`
- `call_id`
- `tool_name`
- `tool_version`
- `arguments`
- `security_context`
- `mode`
- `approval_evidence`
- `options`
- `client_capabilities`

### 5.3 Canonical Response Envelope

Every tool response MUST be normalizable to:

- `request_id`
- `call_id`
- `interface_profile_id`
- `trace_id`
- `status`
- `result`
- `structured_output` or `null`
- `error` or `null`
- `notices[]`

### 5.4 Structured Output Modes

The canonical structured-output modes are:

- `none`: no schema-bound output is promised
- `json_object`: the result MUST be valid JSON object but is not bound to a specific versioned schema
- `json_schema`: the result MUST validate against a declared schema ID and schema version

### 5.5 Structured Output Descriptor

When `output_mode = json_schema`, the response MUST bind:

- `schema_id`
- `schema_version`
- `validation_status`
- `payload`
- `validation_errors[]`

`validation_status` MUST be one of:

- `valid`
- `invalid`
- `not_requested`

### 5.6 Provider and Framework Mapping Rules

Provider-specific or framework-specific adapters MUST map their native representation into:

- canonical tool descriptors
- canonical invocation envelope
- canonical response envelope
- canonical error taxonomy

Adapters MAY preserve provider-specific metadata, but only as supplementary fields. They MUST NOT replace the canonical fields.

### 5.7 Error Model

The minimum canonical error set includes:

- `E_TOOL_NOT_FOUND`
- `E_TOOL_INPUT_INVALID`
- `E_STRUCTURED_OUTPUT_INVALID`
- `E_RESPONSE_SCHEMA_MISMATCH`
- `E_PROVIDER_CONTRACT_UNSUPPORTED`
- `E_INTERFACE_UNSUPPORTED_OPERATION`
- `E_POLICY_DENY`
- `E_APPROVAL_INVALID`
- `E_LIMIT_EXCEEDED`

## 6. Validation Rules

- Input validation:
- unknown required fields MUST fail closed unless the tool schema explicitly allows them
- type mismatch MUST fail closed
- missing required fields MUST fail closed

- Output validation:
- `json_object` responses MUST be parseable JSON objects
- `json_schema` responses MUST validate against the declared schema
- invalid structured responses MUST not be silently coerced into success

- Compatibility:
- tool schema version changes MUST preserve older versions or declare a breaking change path
- provider mappings MUST declare unsupported canonical features instead of silently degrading them

## 7. Security and Governance

- Authentication/authorization:
- tool descriptors MUST declare the scopes and mode constraints required for execution
- tool normalization MUST happen before authorization is treated as satisfied

- Data handling and redaction:
- raw provider transcripts, hidden prompts, and credentials MUST not be mixed into tool argument logs without redaction policy
- validation failures MAY log schema paths and error codes, but MUST not leak secrets

- Auditability:
- audit records SHOULD include `tool_name`, `tool_version`, `interface_profile_id`, `mode`, and validation outcome
- structured-output validation failures MUST be auditable as deterministic contract failures

## 8. Observability

- Logs:
- tool descriptor version used
- argument validation outcome
- structured-output validation outcome
- canonical error mapping result

- Metrics:
- tool invocation count
- validation failure rate
- structured-output mismatch rate
- unsupported-provider-feature rate

- Traces:
- trace IDs MUST survive provider or framework adaptation boundaries

## 9. Testing and Acceptance Criteria

- Unit tests:
- tool descriptor validation
- input schema validation
- structured-output mode validation
- canonical error envelope mapping

- Integration tests:
- one implemented interface profile MUST execute tools through the canonical descriptor model
- direct provider or framework adapters MUST prove normalized equivalence to canonical tool operations

- Regression tests:
- backward-compatible tool schema evolution
- fail-closed handling of unsupported provider features
- invalid structured output rejection

- Exit criteria:
- no tool interface may be marked implemented without canonical schema validation
- no structured-output claim may be marked supported without negative tests
- provider or framework adapters must prove canonical contract preservation

## 10. Rollout Plan

- Phase 1:
- define canonical tool descriptor and structured-output modes
- align existing tool-schema helpers and docs to the new contract

- Phase 2:
- add provider-neutral compatibility profiles
- bind direct provider and remote MCP work to this canonical contract

- Phase 3:
- require framework adapters to demonstrate canonical equivalence and schema/version compatibility

## 11. Open Questions

- Q1: Should unknown optional fields in structured outputs be rejected by default, or allowed when the declared schema supports extensibility?
- Q2: Should provider-native structured-output features be modeled as compatibility subsets of `json_schema`, or as separate output modes?
