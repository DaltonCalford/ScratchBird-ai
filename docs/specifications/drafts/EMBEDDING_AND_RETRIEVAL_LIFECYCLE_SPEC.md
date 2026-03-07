# Embedding and Retrieval Lifecycle Specification

Status: Draft
Owner: ScratchBird AI Team
Last Updated: 2026-03-07

## 1. Purpose

Define the canonical lifecycle contract for embeddings, vector indexes, and retrieval operations exposed by `ScratchBird-ai`.

This specification separates:

- the retrieval behavior already implemented in the repository,
- the future live-engine and provider-assisted retrieval contracts,
- the release evidence required before broader retrieval claims can be made.

## 2. Scope

- In scope:
- embedding ingestion, replacement, and deletion contracts
- vector search and hybrid retrieval request/response normalization
- index lifecycle states and ownership rules
- tenant isolation, policy enforcement, and deterministic result ordering
- compatibility expectations for offline helper mode versus live engine-backed mode

- Out of scope:
- embedding model training
- ANN algorithm implementation details
- non-native dialect retrieval enablement
- UI ranking customization beyond declared weights and filters

## 3. Dependencies

- `docs/planning/AI_INTERFACE_SPEC_EXPANSION_BACKLOG.md`
- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md`
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md`
- `docs/specifications/drafts/SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`

Implementation-backed baseline references:

- `src/scratchbird_ai/retrieval.py`
- `tests/test_retrieval.py`
- `tests/test_service.py`

## 4. Requirements

### 4.1 Functional Requirements

- FR-001: Every retrieval operation MUST require a valid `security_context`.
- FR-002: Every write or delete operation on embeddings MUST be tenant-bound and fail closed on cross-tenant access.
- FR-003: Every index MUST declare one canonical `dimension`.
- FR-004: The current baseline MUST support caller-supplied embeddings without requiring model-side embedding generation.
- FR-005: The lifecycle contract MUST cover `add_embeddings`, `delete_embeddings`, `vector_search`, and `hybrid_search`.
- FR-006: `vector_search` MUST order results by descending score and lexical ascending `vector_id` for ties.
- FR-007: `hybrid_search` MUST order results by descending final score and lexical ascending `document_id` for ties.
- FR-008: Hybrid retrieval MUST reject structured pushdown modes that cannot be proven safe for the active runtime profile.
- FR-009: Retrieval requests MUST preserve native-only scope unless a later release explicitly expands dialect coverage.
- FR-010: Retrieval APIs MUST preserve canonical traceability through deterministic `trace_id` or equivalent identifiers.
- FR-011: Every retrieval profile MUST declare whether embeddings are caller-supplied, provider-generated, or engine-managed.
- FR-012: Releases MUST not claim live corpus or engine-backed retrieval parity unless live conformance evidence exists.

### 4.2 Non-Functional Requirements

- NFR-001: Retrieval result ordering MUST be deterministic for a fixed data snapshot, request, and security context.
- NFR-002: Floating-point output values MUST be finite and normalized to a bounded decimal representation.
- NFR-003: Retrieval profiles MUST fail closed when policy, pushdown, or compatibility guarantees cannot be established.
- NFR-004: Index and retrieval profile descriptors MUST be versionable and auditable in git.

## 5. Retrieval Profiles and Lifecycle Model

### 5.1 Retrieval Profile Inventory

The canonical retrieval lifecycle supports these acquisition profiles:

| Profile ID | Description | Current state | Notes |
| --- | --- | --- | --- |
| `client_supplied_embeddings_v0` | Caller provides numeric embeddings directly with each ingest request | implemented | Current `InMemoryRetrievalStore` baseline |
| `provider_generated_embeddings_v0` | Service calls an external embedding provider before ingest | draft | Requires provider/runtime contract and secret handling |
| `engine_managed_retrieval_v0` | ScratchBird-backed vector/index lifecycle with live planner pushdown | draft | Requires live server/runtime integration and certification |

Only `client_supplied_embeddings_v0` is implementation-backed today.

### 5.2 Index Descriptor

Every retrieval backend SHOULD be representable as:

- `index_id`
- `profile_id`
- `dimension`
- `distance_metric`
- `backend_kind`
- `state`
- `tenant_scope`
- `created_at_utc`
- `updated_at_utc`
- `compatibility_version`

### 5.3 Index Lifecycle States

The canonical lifecycle states are:

- `provisioning`
- `ready`
- `reindexing`
- `deleting`
- `deleted`
- `failed`

Current baseline note:

- The in-repository helper store lazily creates an index on first `add_embeddings` request.
- Future engine-managed profiles MAY expose explicit create/reindex operations, but MUST still normalize to the lifecycle above.

## 6. Canonical Contracts

### 6.1 Security Context

All retrieval requests MUST carry:

- `tenant_id`
- `actor_id`
- `roles[]`
- `session_id`
- `context_version`

### 6.2 Add Embeddings

Canonical request fields:

- `index_id`
- `dimension`
- `records[]`
- `security_context`

Each record MUST contain:

- `vector_id`
- `embedding[]`
- `metadata`

Canonical response fields:

- `index_id`
- `accepted`
- `rejected`
- `ingest_id`
- `trace_id`

Validation rules:

- `records` MUST be non-empty.
- every embedding length MUST equal `dimension`.
- all numeric values MUST be finite.
- record metadata tenant identity MUST resolve to the caller tenant.

### 6.3 Delete Embeddings

Canonical request fields:

- `index_id`
- `vector_ids[]`
- `security_context`

Canonical response fields:

- `index_id`
- `deleted`
- `not_found`
- `trace_id`

Delete requests MUST fail closed if a targeted record belongs to a different tenant.

### 6.4 Vector Search

Canonical request fields:

- `index_id`
- `query_embedding[]`
- `top_k`
- `filters`
- `include_vectors`
- `security_context`

Canonical response fields:

- `index_id`
- `results[]`
- `trace_id`
- `rls_applied`

Each result row MUST contain:

- `vector_id`
- `score`
- `metadata`

Optional:

- `embedding[]` when `include_vectors=true`

### 6.5 Hybrid Search

Canonical request fields:

- `dialect`
- `query_text`
- `query_embedding[]`
- `vector_index_id`
- `sql_filter`
- `weights`
- `top_k`
- `security_context`

Canonical response fields:

- `results[]`
- `trace_id`
- `rls_applied`
- `query_plan_ref`

Each result row MUST contain:

- `document_id`
- `vector_id`
- `scores.vector`
- `scores.lexical`
- `scores.structured`
- `scores.final`
- `metadata`

### 6.6 Weight Normalization

Hybrid retrieval weights MUST satisfy:

- `vector in [0.0, 1.0]`
- `lexical in [0.0, 1.0]`
- `structured in [0.0, 1.0]`
- `vector + lexical + structured == 1.0` within tolerance `1e-6`

Default baseline weights are:

- `vector = 0.6`
- `lexical = 0.3`
- `structured = 0.1`

## 7. Execution Rules

### 7.1 Policy and Tenant Isolation

- RLS-equivalent tenant filtering MUST be applied before result emission.
- Cross-tenant insert and delete requests MUST fail with deterministic policy errors.
- Retrieval operations MUST ignore prompt- or model-supplied attempts to widen tenant scope.

### 7.2 Determinism Rules

- Vector results MUST sort by `score DESC`, then `vector_id ASC`.
- Hybrid results MUST sort by `scores.final DESC`, then `document_id ASC`.
- Output scores SHOULD be rounded to at most six fractional digits.

### 7.3 Structured Pushdown Rules

- Live engine-backed retrieval MAY support richer structured filter pushdown.
- Offline helper mode only supports metadata-based structured filters.
- `where`-style pushdown MUST fail with `E_FILTER_PUSHDOWN_UNAVAILABLE` unless the active runtime can prove safe translation and planning.

### 7.4 Dialect Rules

- `hybrid_search` MUST reject unsupported dialects with `E_DIALECT_UNAVAILABLE`.
- The baseline profile is native-only.

## 8. Error Model

Required error codes:

- `E_INVALID_ARGUMENT`
- `E_INDEX_NOT_FOUND`
- `E_DIMENSION_MISMATCH`
- `E_POLICY_DENY`
- `E_FILTER_PUSHDOWN_UNAVAILABLE`
- `E_DIALECT_UNAVAILABLE`
- `E_TIMEOUT`
- `E_EXECUTION_FAILED`
- `E_COMPATIBILITY_MISMATCH`

Every error response SHOULD be normalizable to:

- `error_code`
- `message`
- `policy_rule_id` when applicable
- `retryable`
- `trace_id`

## 9. Testing and Acceptance Criteria

Required baseline tests:

- schema and validation tests for ingest/delete/search contracts
- tenant-isolation negative tests for insert and delete operations
- deterministic vector ordering tests
- deterministic hybrid ordering tests
- structured-pushdown denial tests for unsupported offline filters

Additional tests required before live parity claims:

- live engine-backed index lifecycle tests
- planner-backed hybrid pushdown tests
- larger-corpus retrieval quality and latency evidence
- compatibility negotiation tests across retrieval profiles

Exit criteria for promotion beyond draft:

- at least one non-helper retrieval backend exists
- live retrieval evidence is generated on the same commit as the release
- profile-specific conformance checks pass under `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md`

## 10. Release Evidence Mapping

Current early-beta evidence bindings:

- `EVID-04` for vector retrieval
- `EVID-05` for hybrid retrieval

Future release-grade retrieval claims MUST additionally include:

- live corpus certification artifacts
- retrieval profile compatibility metadata
- environment descriptors proving the active backend and corpus seed
