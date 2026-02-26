# ScratchBird VectorStore API Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the canonical VectorStore API for:
1. embedding ingestion,
2. embedding deletion,
3. similarity search,
4. security-filtered retrieval under RLS and tenant isolation.

Out of scope:
1. embedding model generation itself,
2. non-native engine adapters in v1.

## 2. API Surface

Base path: `/v1/vector`

Required endpoints:
1. `POST /indexes/{index_id}/embeddings:add`
2. `POST /indexes/{index_id}/embeddings:delete`
3. `POST /indexes/{index_id}/search`

All endpoints MUST:
1. require authenticated identity,
2. require tenant security context,
3. return JSON object payloads only.

## 3. Canonical Schemas

### 3.1 Security Context (required)

```json
{
  "tenant_id": "string",
  "actor_id": "string",
  "roles": ["string"],
  "session_id": "string",
  "context_version": 1
}
```

### 3.2 Add Embeddings Request

```json
{
  "security_context": { "...": "see Security Context" },
  "dimension": 1536,
  "records": [
    {
      "vector_id": "doc-001#chunk-01",
      "embedding": [0.123, -0.456, 0.789],
      "metadata": {
        "document_id": "doc-001",
        "source": "kb",
        "tags": ["finance", "policy"]
      }
    }
  ]
}
```

Validation rules:
1. `records` MUST be non-empty.
2. every `embedding` length MUST equal `dimension`.
3. `dimension` MUST match index configuration.
4. all numbers MUST be finite IEEE-754 values (no NaN/inf).

Response:

```json
{
  "index_id": "idx_docs",
  "accepted": 100,
  "rejected": 0,
  "ingest_id": "ing_...",
  "trace_id": "tr_..."
}
```

### 3.3 Delete Embeddings Request

```json
{
  "security_context": { "...": "see Security Context" },
  "vector_ids": ["doc-001#chunk-01", "doc-001#chunk-02"]
}
```

Response:

```json
{
  "index_id": "idx_docs",
  "deleted": 2,
  "not_found": 0,
  "trace_id": "tr_..."
}
```

### 3.4 Similarity Search Request

```json
{
  "security_context": { "...": "see Security Context" },
  "query_embedding": [0.111, 0.222, 0.333],
  "top_k": 20,
  "filters": {
    "document_type": "policy",
    "region": "us"
  },
  "include_vectors": false
}
```

Response:

```json
{
  "index_id": "idx_docs",
  "results": [
    {
      "vector_id": "doc-001#chunk-01",
      "score": 0.9421,
      "metadata": {
        "document_id": "doc-001"
      }
    }
  ],
  "trace_id": "tr_...",
  "rls_applied": true
}
```

## 4. RLS and Tenant Enforcement

1. RLS MUST be applied before result emission.
2. Tenant isolation MUST be applied before similarity scoring output is produced.
3. Search execution order MUST be:
   1. resolve security predicates from `security_context`,
   2. apply tenant + RLS predicate prefilter,
   3. compute nearest-neighbor scores on eligible candidates,
   4. apply metadata filters,
   5. truncate to `top_k`,
   6. emit results.
4. If policy predicates cannot be resolved, request MUST fail with `E_RLS_ENFORCEMENT_FAILED`.

## 5. Transport and Encoding

1. API transport is HTTP/JSON for control payloads.
2. Internal driver/wire path to ScratchBird MUST use native protocol mode.
3. Optional binary payload mode MAY be added for bulk embeddings; if enabled, server MUST publish explicit `content-type` and checksum contract.

## 6. Determinism Rules

1. For identical input, security context, and index snapshot:
   - returned `vector_id` ordering MUST be deterministic.
2. Ties in score MUST be ordered by lexical ascending `vector_id`.
3. Score precision in response MUST be decimal string with max 6 fractional digits.

## 7. Error Model

Required error codes:
1. `E_INVALID_ARGUMENT`
2. `E_INDEX_NOT_FOUND`
3. `E_DIMENSION_MISMATCH`
4. `E_POLICY_DENY`
5. `E_RLS_ENFORCEMENT_FAILED`
6. `E_TIMEOUT`

Error envelope:

```json
{
  "error_code": "E_DIMENSION_MISMATCH",
  "message": "embedding dimension 1024 does not match index dimension 1536",
  "trace_id": "tr_..."
}
```

## 8. Performance Targets

Single-node baseline target (reference workload):
1. 1,000,000 vectors,
2. dimension 1536,
3. `top_k <= 20`,
4. warmed cache.

Targets:
1. p95 search latency MUST be <= 20 ms.
2. p99 search latency MUST be <= 40 ms.
3. ingest throughput MUST be >= 10,000 vectors/sec for batch size >= 1,000.

## 9. Required Tests

1. Schema validation tests for all request/response payloads.
2. RLS/tenant isolation tests (positive and negative).
3. Deterministic ordering tests for equal-score ties.
4. Dimension mismatch negative tests.
5. Latency benchmark tests against baseline workload.

## 10. Acceptance Criteria

1. All required tests pass.
2. Security and determinism guarantees are validated.
3. Performance targets are met or explicit waiver is approved.

## 11. Evidence Binding

1. This specification is bound to `EVID-04` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/04/vector_api_report.json`
   - `artifacts/ai_conformance/04/benchmark.csv`
3. Any parity claim against comparative vector tools MUST cite `EVID-04` outputs and cannot rely on narrative-only statements.
