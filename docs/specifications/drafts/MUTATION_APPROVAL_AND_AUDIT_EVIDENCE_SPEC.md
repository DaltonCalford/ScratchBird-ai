# Mutation Approval and Audit Evidence Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the canonical contract for approval-gated mutations and deterministic audit evidence in `ScratchBird-ai`.

This specification binds together:

- execution-mode normalization,
- approval-evidence validation,
- deterministic audit bundle generation,
- replay validation and future durable attestation requirements.

## 2. Scope

- In scope:
- canonical execution modes and state transitions
- approval token and approval record normalization
- mutation authorization rules
- deterministic audit bundle schema, hashing, and replay validation
- release evidence required for mutation-capable interface claims

- Out of scope:
- organization-specific human approval workflow UI
- external PKI or signature service implementation details
- ScratchBird engine internal authorization mechanics

## 3. Dependencies

- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`

Implementation-backed baseline references:

- `src/scratchbird_ai/execution_mode.py`
- `src/scratchbird_ai/audit_bundle.py`
- `tests/test_execution_mode.py`
- `tests/test_audit_bundle.py`
- `tests/test_service.py`

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Mutation-capable requests MUST normalize to one canonical execution mode.
- FR-002: Unknown statement kinds MUST be treated as mutation-capable for fail-closed safety.
- FR-003: `ai_analysis` mode MUST deny mutation execution.
- FR-004: `ai_mutation_pending_approval` mode MUST deny execution until valid approval evidence exists.
- FR-005: `ai_mutation_approved` mode MUST require valid approval evidence before execution.
- FR-006: Approval evidence MUST bind, directly or indirectly, to tenant identity, actor identity, and mutation intent.
- FR-007: Resource limits MUST be normalized before execution and MUST reject values above hard ceilings.
- FR-008: Every request that reaches compile or execute evaluation MUST emit a deterministic audit bundle or a deterministic denial bundle.
- FR-009: Audit bundles MUST preserve policy decision, policy rule, compile artifact, execution artifact, and security-context correlation.
- FR-010: Replay validation MUST detect bundle tampering and policy mismatches.
- FR-011: Releases MUST not claim durable approval workflows unless approval evidence is persisted beyond in-process execution.

### 4.2 Non-Functional Requirements

- NFR-001: Approval and audit identifiers MUST be stable and reproducible when derived from the same canonical input.
- NFR-002: Secrets MUST not be stored in cleartext inside audit bundles.
- NFR-003: Approval and audit schemas MUST remain versioned and compatibility-checked across releases.
- NFR-004: Mutation authorization MUST fail closed when approval parsing, expiry, or claim matching cannot be established.

## 5. Canonical Mode Model

### 5.1 Canonical Modes

The canonical execution modes are:

| Canonical mode | Meaning | Mutation allowed | Approval required |
| --- | --- | --- | --- |
| `ai_analysis` | read/query analysis only | no | no |
| `ai_mutation_pending_approval` | mutation intent recognized but approval incomplete | no | yes |
| `ai_mutation_approved` | mutation request has validated approval evidence | yes | yes |

Legacy aliases MAY be accepted during transition:

- `read_only` -> `ai_analysis`
- `mutation_with_approval` -> `ai_mutation_pending_approval`

If `mutation_with_approval` arrives with explicit approval evidence, it MAY normalize to `ai_mutation_approved`.

### 5.2 Allowed Mode Transitions

The canonical transition set is:

- `ai_analysis` -> `ai_mutation_pending_approval`
- `ai_mutation_pending_approval` -> `ai_mutation_approved`
- `ai_mutation_approved` -> `ai_analysis`

All other transitions MUST be denied.

Transition to `ai_mutation_approved` MUST fail unless approval validation succeeds.

## 6. Approval Evidence Contract

### 6.1 Canonical Approval Envelope

Approval evidence MUST be normalizable to:

- `approval_token`
- `approval_id`
- `approved_by`
- `approved_at`

### 6.2 Approval Token Rules

The baseline implementation accepts opaque tokens and JSON-object tokens.

When the token parses as a JSON object, the following claims are recognized:

- `exp`
- `tenant_id`
- `actor_id`
- `statement_hash`

Validation rules:

- empty tokens MUST fail with `E_APPROVAL_INVALID`
- expired tokens MUST fail with `E_APPROVAL_INVALID`
- mismatched `tenant_id`, `actor_id`, or `statement_hash` claims MUST fail with `E_APPROVAL_INVALID`

### 6.3 Derived Fields

If `approval_id` is absent, it SHOULD be deterministically derived from:

- approval token
- tenant identity
- actor identity

If `approved_at` is absent, it SHOULD be populated with current UTC time.

If `approved_by` is absent, it SHOULD default to the actor or to an explicit unknown marker.

### 6.4 Durable Approval Record

Future release-grade mutation support MUST persist an approval record containing at least:

- `approval_id`
- `approval_token_hash`
- `tenant_id`
- `actor_id`
- `statement_hash`
- `approved_by`
- `approved_at`
- `expires_at`
- `interface_profile_id`
- `policy_rule_id`
- `compatibility_version`
- `release_commit`

Current baseline note:

- The repository validates inline approval evidence.
- It does not yet persist durable approval records or revocation history.

## 7. Audit Bundle Contract

### 7.1 Canonical Bundle Fields

Every audit bundle MUST include:

- `bundle_version`
- `trace_id`
- `request_id`
- `tenant_id`
- `actor_id`
- `dialect`
- `execution_mode`
- `sql_text_normalized`
- `compile_artifact_id`
- `execution_artifact_id`
- `plan_json`
- `plan_hash`
- `security_context_hash`
- `policy_decision`
- `policy_rule_id`
- `cluster_epoch`
- `timestamp_utc`
- `approval_id`
- `approval_token_hash`
- `error_code`
- `sqlstate`
- `bundle_hash`

Transition compatibility fields MAY also be emitted:

- `schema_version`
- `created_at_utc`
- `statement_kind`
- `sblr_hash`

### 7.2 Security Context Hash

`security_context_hash` MUST be computed from a canonicalized input containing:

- `tenant_id`
- `actor_id`
- sorted `roles[]`
- `context_version`

### 7.3 Bundle Hash Rules

- `bundle_hash` MUST exclude the `bundle_hash` field itself from its input.
- the remaining bundle payload MUST be canonically serialized before hashing.
- mutation approval tokens MUST be represented by hash, not raw token value.

### 7.4 Replay Validation

Replay validation MUST support these outcomes:

- `REPLAY_MATCH`
- `REPLAY_MISMATCH_HASH`
- `REPLAY_MISMATCH_POLICY`
- `REPLAY_INSUFFICIENT_DATA`

Replay MUST fail when:

- required bundle fields are missing
- bundle hash does not match recomputed hash
- supplied security context does not reproduce the stored hash
- expected policy decision or rule does not match
- expected plan hash does not match

## 8. Error Model

Required error codes:

- `E_INVALID_MODE`
- `E_APPROVAL_INVALID`
- `E_POLICY_DENY`
- `E_LIMIT_EXCEEDED`
- `E_EXECUTION_FAILED`
- `E_COMPATIBILITY_MISMATCH`

Required rule identifiers in the current baseline include:

- `MODE-INVALID-001`
- `MODE-LIMIT-001`
- `MODE-APPROVAL-001`
- `MODE-APPROVAL-002`
- `MODE-APPROVAL-003`
- `MODE-APPROVAL-004`
- `MODE-DENY-MUTATION-ANALYSIS-001`
- `MODE-DENY-MUTATION-PENDING-001`
- `MODE-ALLOW-READ-001`
- `MODE-ALLOW-MUTATION-APPROVED-001`

## 9. Testing and Acceptance Criteria

Required baseline tests:

- alias-to-canonical mode normalization
- mutation denial in `ai_analysis`
- approval token requirement in `ai_mutation_approved`
- approval-based transition validation
- lower-bound option normalization and hard-limit rejection
- deterministic audit bundle hashing
- replay detection for hash tamper and policy mismatch
- allow and deny audit bundle emission from the service layer

Additional tests required before promotion beyond draft:

- durable approval record persistence and replay
- revocation and expiry handling across process restarts
- externally attested or signed audit bundle verification
- mutation workflow correlation across framework/provider interfaces

Exit criteria for live mutation-capable claims:

- durable approval storage exists
- replay validation is exercised against persisted approval evidence
- release artifacts prove deny/allow correlation end to end

## 10. Release Evidence Mapping

Current early-beta evidence bindings:

- `EVID-08` for execution mode and policy
- `EVID-09` for audit bundle determinism

Future release-grade mutation claims MUST additionally include:

- durable approval evidence artifacts
- replay/correlation reports against persisted records
- attestation or equivalent integrity evidence for emitted audit bundles
