# ScratchBird AI Compatibility and Release Negotiation Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define how `ScratchBird-ai` declares compatibility, negotiates runtime support, and fails closed when version or capability mismatches exist between:

- `ScratchBird-ai`
- ScratchBird server
- parser/compiler components
- driver or runtime dependencies
- interface profiles exposed to AI clients

This specification closes a gap called out by `ADR-0001`: the repository needs an explicit compatibility contract rather than informal documentation-only coordination.

## 2. Scope

- In scope:
- release compatibility manifest requirements
- runtime negotiation of component versions and interface profiles
- fail-closed behavior for unsupported combinations
- version compatibility categories and support windows
- release-evidence expectations for compatibility claims

- Out of scope:
- semantic versioning policy for external third-party providers
- package-manager publishing workflows
- non-native dialect enablement policy
- provider-specific SDK compatibility details

## 3. Dependencies

- Reference docs:
- `docs/specifications/final/ADR-0001_REPOSITORY_BOUNDARY.md`
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/MCP_DATABASE_SERVER_SPEC.md`
- `docs/specifications/drafts/REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md`
- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`

- Internal components:
- capability advertisement
- interface profile inventory
- HTTP bridge runtime settings
- service layer and policy gates

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Every `ScratchBird-ai` release MUST declare a compatibility manifest.
- FR-002: The compatibility manifest MUST identify the supported versions or version ranges for ScratchBird server, parser/compiler, and required driver/runtime components.
- FR-003: Runtime entrypoints MUST negotiate or validate compatibility before claiming support for an operation or interface profile.
- FR-004: Unknown or unsupported version combinations MUST fail closed with deterministic compatibility errors.
- FR-005: Interface profile support MUST be versioned independently from repository release version when necessary.
- FR-006: Compatibility checks MUST distinguish between:
- repository release compatibility
- runtime transport compatibility
- interface profile compatibility
- driver/runtime dependency compatibility
- FR-007: Capability advertisement MUST expose enough compatibility information for a client to understand whether a requested profile or transport is supported.
- FR-008: Compatibility claims in docs or release notes MUST map to machine-readable evidence.
- FR-009: Bridge-backed and remote-interface-backed flows MUST not silently downgrade to unsupported compatibility modes.
- FR-010: The system MUST be able to report why compatibility failed, not only that it failed.

### 4.2 Non-Functional Requirements

- NFR-001: Compatibility manifests MUST be deterministic and auditable in git.
- NFR-002: Negotiation results MUST be stable for a given manifest and runtime environment.
- NFR-003: Compatibility failures MUST be observable in logs, metrics, and release evidence.
- NFR-004: Manifest changes that weaken support guarantees MUST be explicit and reviewable.

## 5. Compatibility Model

### 5.1 Compatibility Domains

Compatibility is defined across these domains:

- `repo_release`: the `ScratchBird-ai` repository release itself
- `server_runtime`: ScratchBird server/runtime version support
- `parser_compiler`: parser/compiler contract version support
- `driver_runtime`: driver/runtime or bridge dependency support
- `interface_profile`: interface-profile version support
- `transport_profile`: transport/session capability support

### 5.2 Support States

Each compatibility entry MUST declare one of:

- `supported`
- `conditionally_supported`
- `unsupported`
- `deprecated`

### 5.3 Failure Policy

Entries marked `unsupported` or unknown MUST fail closed.

Entries marked `conditionally_supported` MUST include a machine-readable reason and required condition list.

## 6. Interfaces and Contracts

### 6.1 Compatibility Manifest

Every release SHOULD publish a manifest containing:

- `release_version`
- `release_date`
- `interface_profiles[]`
- `server_runtime_support[]`
- `parser_compiler_support[]`
- `driver_runtime_support[]`
- `transport_support[]`
- `notes[]`

### 6.2 Compatibility Entry

Every compatibility entry MUST include:

- `component`
- `component_version` or `version_range`
- `support_state`
- `required_conditions[]`
- `failure_reason_code` or `null`
- `evidence_gate`

### 6.3 Runtime Negotiation Request

A runtime negotiation request SHOULD be normalizable to:

- `request_id`
- `interface_profile_id`
- `requested_profile_version`
- `requested_transport`
- `client_component_versions`
- `server_component_versions` if locally known
- `driver_runtime_versions` if relevant

### 6.4 Runtime Negotiation Response

The negotiation response SHOULD include:

- `request_id`
- `negotiation_status`
- `resolved_interface_profile_version`
- `resolved_transport`
- `compatibility_decisions[]`
- `warnings[]`
- `error` or `null`

### 6.5 Error Model

Compatibility work MUST support deterministic mapping for at least:

- `E_COMPATIBILITY_MISMATCH`
- `E_COMPONENT_VERSION_UNSUPPORTED`
- `E_INTERFACE_PROFILE_UNSUPPORTED`
- `E_TRANSPORT_PROFILE_UNSUPPORTED`
- `E_DRIVER_RUNTIME_UNSUPPORTED`
- `E_SERVER_RUNTIME_UNSUPPORTED`
- `E_CONDITIONAL_SUPPORT_BLOCKED`

## 7. Negotiation Rules

- Clients MUST declare the interface profile and requested profile version when negotiation is required.
- The server MUST compare the request against the active compatibility manifest.
- Unknown component versions MUST not be treated as supported.
- Remote interface negotiation MUST occur before session activation.
- Local or in-process compatibility checks MAY be reduced to manifest validation, but they MUST still fail closed on known-unsupported combinations.
- Bridge-backed flows MUST surface dependency mismatches explicitly instead of masking them as generic connection failures when the cause is compatibility.

## 8. Security and Governance

- Authentication/authorization:
- Compatibility negotiation MUST not be used as a substitute for authentication or authorization.
- Client-supplied version claims MAY inform negotiation, but server-side policy and environment inspection remain authoritative where possible.

- Data handling and redaction:
- Compatibility logs MAY include component names and versions, but MUST not leak secrets from DSNs, tokens, or hidden runtime config.

- Auditability:
- Compatibility failures SHOULD be auditable for release and operations review.
- Release approvals SHOULD not claim support outside the published manifest.

## 9. Observability

- Logs:
- manifest version used
- compatibility domain checked
- mismatch reason code
- downgraded or blocked interface profile

- Metrics:
- compatibility failures by domain
- blocked session opens
- blocked bridge connects
- deprecated-version usage

- Traces:
- negotiation outcome SHOULD be linked to the request trace when compatibility is checked at request time

## 10. Testing and Acceptance Criteria

- Unit tests:
- manifest schema validation
- version-range evaluation
- fail-closed handling of unknown support states

- Integration tests:
- supported runtime combinations pass
- unsupported runtime combinations fail with deterministic errors
- interface-profile version mismatches are rejected before operation execution

- Regression tests:
- accidental support widening is detected
- deprecated-version handling remains explicit
- bridge/runtime mismatch classification does not regress into generic failures

- Exit criteria:
- no interface profile may be claimed supported without a compatibility entry
- no release may claim compatibility without machine-readable manifest evidence
- runtime negotiation failures must report domain and reason code

## 11. Rollout Plan

- Phase 1:
- define manifest structure and negotiation semantics
- keep compatibility checks documentation-first where runtime inspection is not implemented yet

- Phase 2:
- bind remote MCP and bridge-backed runtime paths to manifest-based negotiation
- add release evidence proving compatibility coverage

- Phase 3:
- require framework and provider adapters to publish compatibility profiles
- add live certification for supported version matrices

## 12. Open Questions

- Q1: Should compatibility manifests be stored only in docs first, or also as machine-readable artifacts under version control for CI enforcement?
- Q2: How strict should version-range matching be for bridge/runtime dependencies that are partially environment-driven?
