# Security, Governance, and Observability Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define mandatory control-plane requirements for safe AI-to-database operation.

## 2. Scope

- In scope:
- AuthN/AuthZ controls
- Policy enforcement model
- Audit and evidence requirements
- Telemetry/alerting baselines

- Out of scope:
- Engine internal auth mechanics

## 3. Requirements

### 3.1 Security Requirements

- SR-001: Every tool request MUST be authenticated.
- SR-002: Authorization MUST be enforced server-side per action scope.
- SR-003: Read-only default mode MUST be applied unless elevated mode is explicitly approved.
- SR-004: Sensitive fields MUST be redacted in logs and traces.
- SR-005: Mutation requests MUST include approval evidence.

### 3.2 Governance Requirements

- GR-001: Each request MUST produce immutable audit records.
- GR-002: Policy decisions MUST include rule identifiers and evaluation outcomes.
- GR-003: Compile and execution artifacts MUST be trace-linked.

### 3.3 Observability Requirements

- OR-001: Platform MUST emit structured logs and metrics.
- OR-002: Trace IDs MUST propagate across all service boundaries.
- OR-003: Alert thresholds MUST exist for policy-denial spikes, error spikes, and timeout spikes.

## 4. Control Points

- Pre-route: identity and tenant validation.
- Pre-compile: policy and capability checks.
- Pre-execute: operation mode and resource budget checks.
- Post-execute: result-size enforcement and redaction checks.

## 5. Audit Event Schema (Minimum)

- `event_id`
- `timestamp`
- `actor_id`
- `tenant_id`
- `operation`
- `dialect`
- `policy_decision`
- `policy_rule_ids[]`
- `compile_artifact_id`
- `execution_artifact_id`
- `trace_id`
- `outcome`

## 6. Testing and Acceptance Criteria

- AuthZ negative tests (cross-tenant, unauthorized mutation, missing scope)
- Policy bypass resistance tests (prompt-injection-style misuse)
- Log redaction tests for configured sensitive patterns
- Audit completeness tests for all tool operations

## 7. Open Questions

- Q1: What retention window should apply to audit artifacts by default?
- Q2: Should policy runtime be embedded in `ScratchBird-ai` or delegated to external PDP?
