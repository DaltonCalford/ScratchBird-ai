# ScratchBird AI Interface Coverage Program Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the authoritative interface-coverage program for `ScratchBird-ai`.

This specification answers a question the current repository does not yet answer explicitly:

- which AI-facing interface classes are supported,
- which are planned,
- how each interface binds to the same canonical policy and execution contract,
- how release evidence must prove interface availability without bypassing ScratchBird architecture rules.

This document is the top-level control spec for broader AI accessibility. Framework-specific and provider-specific interface specs MUST inherit from it.

## 2. Scope

- In scope:
- AI-facing interface classes exposed by `ScratchBird-ai`
- canonical interface-profile inventory and support states
- compatibility promises across transports, frameworks, and provider runtimes
- binding rules from every interface to the same policy, compile, execute, audit, and error model
- release-evidence expectations for interface availability claims

- Out of scope:
- ScratchBird engine internals
- parser implementation details inside `ScratchBird`
- direct SQL execution in engine code
- non-native dialect enablement policy
- framework-specific implementation details beyond the common contract

## 3. Dependencies

- Reference docs:
- `docs/planning/AI_INTERFACE_SPEC_EXPANSION_BACKLOG.md`
- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`

- Final architecture decisions:
- `docs/specifications/final/ADR-0001_REPOSITORY_BOUNDARY.md`
- `docs/specifications/final/ADR-0002_QUERY_ENTRYPOINT_AND_SBLR_POLICY.md`
- `docs/specifications/final/ADR-0003_SERVER_EXECUTION_BOUNDARY_AND_ADAPTER_ROLE.md`

- Draft implementation specs:
- `docs/specifications/drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md`
- `docs/specifications/drafts/DIALECT_CAPABILITY_MATRIX_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/specifications/drafts/SCRATCHBIRD_HTTP_ADAPTER_CONTRACT_SPEC.md`
- `docs/specifications/drafts/SCRATCHBIRD_HTTP_BRIDGE_RUNTIME_SPEC.md`

- Internal components:
- `ScratchBirdAIService`
- MCP server entrypoint
- HTTP bridge runtime
- capability-matrix loader
- policy engine
- plan/audit/routing/retrieval helper modules

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: `ScratchBird-ai` MUST define a canonical inventory of AI interface profiles.
- FR-002: Every interface profile MUST declare whether it is `implemented`, `draft`, `planned`, or `deferred`.
- FR-003: Every interface profile MUST bind to the same server-side policy and execution contract.
- FR-004: Every SQL-like request accepted through any interface profile MUST flow through parser/compiler entrypoints before execution.
- FR-005: No interface profile may introduce a second engine execution path or direct SQL execution path in engine code.
- FR-006: Every interface profile MUST declare its transport model, session model, authentication model, and operation set.
- FR-007: Framework-specific adapters MUST be thin compatibility layers over the canonical `ScratchBird-ai` service contract, not alternate execution stacks.
- FR-008: Provider-specific tool-calling integrations MUST normalize requests and errors into the canonical tool and policy model.
- FR-009: Unsupported or unavailable interface profiles MUST fail closed with deterministic policy or capability errors.
- FR-010: Every release claim about interface support MUST map to explicit conformance evidence.

### 4.2 Non-Functional Requirements

- NFR-001: Interface profile definitions MUST be versioned and auditable in git.
- NFR-002: Capability advertisement for interface profiles MUST be deterministic for a given release.
- NFR-003: Interface profile changes MUST preserve backward-compatibility rules or declare breaking changes explicitly.
- NFR-004: Security-context handling MUST be explicit and fail closed for every interface family.
- NFR-005: Observability across interface families MUST preserve trace correlation and interface identity.

## 5. Interface Families

### 5.1 Canonical Families

The interface program is organized into these families:

- `service_internal`: canonical in-process service contract used inside this repository
- `mcp_local`: local MCP server usage where the server is process-local or developer-hosted
- `mcp_remote`: remotely reachable MCP session and transport surfaces
- `framework_adapter`: framework compatibility layers such as LangChain, LlamaIndex, or Semantic Kernel
- `provider_tool_calling`: direct tool-calling compatibility profiles for model-provider runtimes
- `streaming_async`: streaming, partial-result, and long-running execution profiles
- `retrieval_ingest`: embedding, corpus-ingest, and retrieval lifecycle interfaces
- `governance_certification`: audit, approval, compatibility, and live certification interfaces

### 5.2 Current Coverage State

As of 2026-03-07, the intended profile inventory is:

| Profile ID | Family | Current state | Notes |
| --- | --- | --- | --- |
| `service_internal_v0` | `service_internal` | implemented | Backed by `ScratchBirdAIService` |
| `mcp_local_v0` | `mcp_local` | implemented | Backed by the current MCP server draft and implementation |
| `mcp_remote_v0` | `mcp_remote` | draft | Session/auth, streaming, continuation, and cancellation primitives exist; live-native and environment-manifest promotion evidence is still missing |
| `langchain_v0` | `framework_adapter` | draft | Thin adapter implementation and parity evidence exist; live-native certification is still missing |
| `llamaindex_v0` | `framework_adapter` | draft | Thin adapter implementation and parity evidence exist; live-native certification is still missing |
| `semantic_kernel_v0` | `framework_adapter` | draft | Thin adapter implementation and parity evidence exist; live-native certification is still missing |
| `provider_tool_calling_v0` | `provider_tool_calling` | implemented | OpenAI-style, Anthropic-style, and Gemini-style child profiles execute through the canonical provider entrypoint and parity evidence exists |
| `streaming_async_v0` | `streaming_async` | draft | Service-layer streaming, continuation, and deterministic cancellation exist; live-native certification is still missing |
| `retrieval_ingest_v0` | `retrieval_ingest` | draft | Lifecycle spec now exists; implementation remains helper-level and not yet live-certified |
| `governance_certification_v0` | `governance_certification` | draft | Approval/audit and live certification specs now exist; durable evidence is still missing |

Any profile not listed above MUST be treated as unsupported.

## 6. Interfaces and Contracts

### 6.1 Interface Profile Descriptor

Every interface profile MUST publish or be representable as a descriptor with at least:

- `profile_id` (string)
- `family` (enum)
- `version` (string)
- `state` (`implemented` | `draft` | `planned` | `deferred`)
- `transport` (string)
- `session_model` (string)
- `auth_model` (string)
- `operation_set[]` (array of operation identifiers)
- `streaming_mode` (`none` | `request_response` | `server_stream` | `bidirectional`)
- `compatibility_version` (string)
- `evidence_gate` (string or null)

### 6.2 Capability Advertisement Contract

The canonical capability advertisement for `ScratchBird-ai` SHOULD evolve to include:

- `service`
- `version`
- `tool_schema_version`
- `query_entrypoint_policy`
- `matrix_version`
- `interface_profiles[]`

The currently implemented capability response MAY expose a reduced subset during transition, but new interface work MUST target the expanded model above.

### 6.3 Canonical Operation Contract

Every interface profile that exposes database-affecting operations MUST map to the same canonical operation model:

- capability discovery
- dialect discovery
- metadata discovery
- compile query
- execute compiled
- read-only query execution
- approval-gated mutation
- explain or trace retrieval
- retrieval operations where supported

Framework or provider interfaces MAY rename these operations, but they MUST preserve equivalent semantics.

### 6.4 Canonical Request Shape

Every AI-facing operation MUST be normalizable to a request containing:

- `request_id`
- `interface_profile_id`
- `dialect`
- `operation`
- `mode`
- `query_text` or structured tool arguments
- `security_context`
- `options`
- `approval_evidence` when required
- `client_capabilities` when negotiation is relevant

### 6.5 Canonical Response Shape

Every AI-facing operation MUST be normalizable to a response containing:

- `request_id`
- `trace_id`
- `interface_profile_id`
- `status`
- `result` or `error`
- `compile_artifact_id` when compilation occurred
- `execution_artifact_id` when execution occurred
- `plan_hash` when explain/trace was requested
- `notices[]`

### 6.6 Error Model

Interface-profile work MUST support deterministic mapping for at least:

- `E_POLICY_DENY`
- `E_DIALECT_UNAVAILABLE`
- `E_INTERFACE_UNAVAILABLE`
- `E_INTERFACE_UNSUPPORTED_OPERATION`
- `E_COMPATIBILITY_MISMATCH`
- `E_SESSION_REQUIRED`
- `E_STREAM_NOT_SUPPORTED`
- `E_COMPILE_FAILED`
- `E_EXECUTION_FAILED`
- `E_TIMEOUT`

## 7. Security and Governance

- Authentication/authorization:
- Every interface profile MUST specify where caller identity is established.
- Security context MUST be normalized before policy evaluation.
- Provider/framework-local prompt state MUST never be treated as authoritative authorization state.

- Data handling and redaction:
- Interface adapters MUST not log raw secrets, provider tokens, or unredacted sensitive fields.
- Provider-native envelopes MAY be retained only if redaction rules are applied before persistence or export.

- Auditability:
- Interface profile ID MUST be recorded in audit output.
- Audit output for equivalent operations SHOULD remain comparable across interface families.
- Mutation-capable interfaces MUST define approval-evidence handling before they can claim support.

## 8. Observability

- Logs:
- Every request log SHOULD include `interface_profile_id`, `operation`, `dialect`, and `trace_id`.

- Metrics:
- Metrics SHOULD be sliceable by interface family and profile version.
- Release dashboards SHOULD distinguish implemented profiles from draft or planned profiles.

- Traces:
- Trace propagation MUST cross adapter, compile, execute, retrieval, and audit stages.

## 9. Testing and Acceptance Criteria

- Unit tests:
- interface-profile descriptor validation
- capability advertisement normalization
- error mapping consistency across interface profiles

- Integration tests:
- at least one implemented profile in each claimed family MUST execute end-to-end
- framework/provider adapters MUST prove canonical operation equivalence, not only transport success

- Regression tests:
- profile inventory drift detection
- compatibility negotiation downgrade or mismatch failures
- fail-closed behavior for unsupported profiles

- Exit criteria:
- no interface may be marked `implemented` without tests and evidence
- no release may claim support for a profile missing from the canonical inventory
- no adapter spec may bypass parser/compiler-first execution or server-side policy evaluation

## 10. Rollout Plan

- Phase 1:
- establish this interface-coverage program spec
- extend planning and release docs to reference interface-profile inventory
- keep only `service_internal_v0` and `mcp_local_v0` as implemented

- Phase 2:
- add remote MCP transport/session spec
- add provider-neutral tool-calling and compatibility/versioning specs
- update capability advertisement to expose interface-profile inventory

- Phase 3:
- rewrite LangChain and LlamaIndex specs against the current architecture
- add Semantic Kernel and direct provider compatibility profiles
- define streaming, retrieval-ingest, governance, and certification layers

## 11. Open Questions

- Q1: Should interface-profile inventory live only in documentation first, or also as a machine-readable artifact checked by CI?
- Q2: Should remote MCP and direct provider profiles share one session-negotiation model, or are separate negotiation contracts required?
