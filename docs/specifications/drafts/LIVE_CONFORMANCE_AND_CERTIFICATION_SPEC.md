# Live Conformance and Certification Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define how `ScratchBird-ai` moves from repository-local selftest evidence to release-grade live certification across servers, transports, frameworks, and provider runtimes.

This specification governs:

- which interface profiles can be certified,
- what environments must be exercised,
- what artifacts must be captured,
- what failures block a certification or release claim.

## 2. Scope

- In scope:
- live validation against real ScratchBird server/runtime dependencies
- profile-specific conformance levels
- framework and provider parity evidence
- artifact freshness, provenance, and compatibility requirements
- certification promotion and blocker semantics

- Out of scope:
- business/commercial certification programs
- third-party provider SLA guarantees
- deployment topology design beyond what is needed to execute the certification suite

## 3. Dependencies

- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md`
- `docs/specifications/drafts/EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md`
- `docs/specifications/drafts/MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md`

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Every certification claim MUST bind to a declared `interface_profile_id`.
- FR-002: Every certification claim MUST bind to a specific git commit and compatibility manifest.
- FR-003: Live certification MUST include a real ScratchBird runtime, not only fake-backend or selftest execution.
- FR-004: Framework and provider profile claims MUST prove canonical operation equivalence, not only transport success.
- FR-005: Certification MUST fail closed if evidence is stale, incomplete, or generated from mismatched commits.
- FR-006: Unsupported or draft-only interface profiles MUST not be advertised as implemented based solely on specification existence.
- FR-007: Every live certification suite MUST exercise authentication, policy, error handling, and deterministic result expectations.
- FR-008: Mutation-capable profile certification MUST include approval and audit correlation evidence.
- FR-009: Retrieval-capable profile certification MUST include tenant isolation and deterministic ranking evidence.
- FR-010: Release claims MUST distinguish repository selftest readiness from live certified runtime parity.

### 4.2 Non-Functional Requirements

- NFR-001: Evidence generation MUST be automated; manual artifact editing is non-compliant.
- NFR-002: Certification artifacts MUST remain machine-readable and auditable in git or release storage.
- NFR-003: Certification environments MUST be reproducible from a recorded manifest.
- NFR-004: Staleness windows MUST be explicit and enforced automatically.

## 5. Certification Levels

The certification ladder is:

| Level | Meaning | Minimum environment |
| --- | --- | --- |
| `baseline_selftest` | repo-local contract validation for the current commit | local test runner and selftest harness |
| `simulated_integration` | adapter/profile exercised with deterministic stubs or fake backend | local harness plus simulated dependencies |
| `live_native` | real ScratchBird server and parser/compiler dependency exercised | live server/runtime on the target commit set |
| `framework_parity` | external framework integration proves canonical operation parity | live server plus framework client harness |
| `provider_parity` | direct provider tool-calling client proves normalized behavior | live server plus provider-facing adapter harness |
| `release_candidate` | all required levels for claimed profiles pass on one candidate build | pinned release environment with full artifact capture |

Current release baseline note:

- `EARLY_BETA_CONFORMANCE_GATES.md` currently proves `baseline_selftest` for the implemented surface.
- This specification defines the additional work required for `live_native` and higher levels.

## 6. Environment Contract

Every live certification run MUST record:

- `git_commit`
- `interface_profile_id`
- `scratchbird_server_version`
- `parser_compiler_version`
- `driver_runtime_version` when applicable
- `scratchbird_ai_version`
- `transport_profile`
- `auth_mode`
- `test_dataset_version`
- `seed_or_fixture_version`
- `started_at_utc`
- `finished_at_utc`

If any dependency version is unknown, certification MUST fail with `E_COMPATIBILITY_MISMATCH`.

## 7. Required Evidence Artifacts

Every certification suite MUST emit:

- summary JSON with pass/fail counts
- compatibility manifest JSON
- JUnit XML or equivalent testcase output
- structured logs or trace bundle reference
- environment descriptor

Additional artifacts by profile type:

- framework/provider profiles: request/response parity report
- retrieval profiles: ranking quality report and tenant-isolation report
- mutation profiles: approval/audit correlation report
- streaming profiles: event-sequence and cancellation report

Artifact rules:

- all machine-readable artifacts MUST share the same `git_commit`
- stale artifacts older than the configured release window MUST fail
- placeholder or template artifacts are invalid for certification

## 8. Profile Certification Matrix

| Profile ID | Minimum certification level | Required evidence focus |
| --- | --- | --- |
| `service_internal_v0` | `live_native` | compile/execute/policy parity against real server |
| `mcp_local_v0` | `live_native` | tool execution, auth, and capability parity |
| `mcp_remote_v0` | `live_native` | session/auth/streaming/cancel behavior |
| `langchain_v0` | `framework_parity` | canonical tool and result equivalence |
| `llamaindex_v0` | `framework_parity` | retriever/query parity and error normalization |
| `semantic_kernel_v0` | `framework_parity` | plugin/function parity and policy enforcement |
| `provider_tool_calling_v0` | `provider_parity` | tool-calling and structured-output normalization |
| `streaming_async_v0` | `live_native` | event ordering, continuation, and cancellation |
| `retrieval_ingest_v0` | `live_native` | live retrieval lifecycle, tenant isolation, and ranking determinism |
| `governance_certification_v0` | `release_candidate` | durable approval evidence, replay integrity, and release attestation |

## 9. Failure and Blocker Semantics

Certification MUST fail when:

- required artifacts are missing
- artifact commits do not match
- compatibility manifests disagree on profile support
- a claimed operation is unsupported in the active profile
- authentication, policy, or approval evidence checks fail
- determinism checks regress
- live server/runtime errors exceed declared failure thresholds

Release blockers MUST include:

- unsupported profile advertised as implemented
- stale or placeholder certification evidence
- provider/framework parity claims without live harness proof
- mutation certification without durable approval evidence

## 10. Acceptance Criteria and Promotion Rules

An interface profile MAY be promoted from `draft` to `implemented` only when:

1. the implementation exists in the repository,
2. the corresponding draft specification is still accurate,
3. required certification level artifacts pass on the target release commit,
4. compatibility negotiation and downgrade behavior are tested,
5. policy and error-model behavior are exercised in negative tests.

`release_candidate` status for a repository build requires:

1. all claimed profiles meet their minimum certification level,
2. no blocker conditions remain open,
3. artifact manifests are reproducible and machine-validated.

## 11. Relationship to Current Release Gates

`docs/releases/EARLY_BETA_CONFORMANCE_GATES.md` remains the active release contract for the currently implemented early-beta surface.

This specification extends that baseline for future releases that claim:

- live ScratchBird server parity,
- remote MCP transport support,
- framework adapter support,
- direct provider compatibility,
- durable mutation governance,
- release-grade retrieval lifecycle support.
