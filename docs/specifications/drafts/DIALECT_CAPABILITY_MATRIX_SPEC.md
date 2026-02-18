# Dialect Capability Matrix Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-02-18

## 1. Purpose

Define a machine-readable capability matrix used by AI routing to decide whether a dialect can safely serve a request.

Current policy scope for this repository is native-only.

## 2. Scope

- In scope:
- Dialect inventory
- Capability flags
- Routing/fallback rules

- Out of scope:
- Parser implementation internals

## 3. Artifacts

- JSON Schema:
  - `capability-matrix/capability-matrix.schema.json`
- Matrix payload (initial):
  - `capability-matrix/capability-matrix.v0.json`
- Validator script:
  - `../../../tools/validate_capability_matrix.py`

## 4. Dialect Inventory

- native

## 5. Capability Model

Each dialect MUST declare:

- `status` (`unavailable` | `experimental` | `partial` | `baseline` | `full`)
- `read_select` (bool)
- `write_dml` (bool)
- `ddl` (bool)
- `transactions` (bool)
- `prepare_bind` (bool)
- `metadata_introspection` (bool)
- `vector_ops` (bool)
- `graph_ops` (bool)
- `last_verified_at` (date)
- `compat_version` (string)

## 6. Routing Rules

- Route only to dialects with required capability flags.
- If required capability is absent, fail closed or fallback per policy.
- Never auto-fallback from one tenant’s configured dialect to another without explicit policy.

## 7. Governance Rules

- Matrix updates MUST be versioned and auditable.
- Runtime MUST include matrix version in each trace event.
- CI MUST validate matrix schema on every change.

## 8. Testing and Acceptance Criteria

- Matrix schema validation tests.
- Router conformance tests against matrix fixtures.
- Fallback denial tests for unsupported operations.

## 9. Open Questions

- Q1: Should capability matrix be stored in git only, or also in runtime config service?
- Q2: What is minimum verification cadence per dialect?
