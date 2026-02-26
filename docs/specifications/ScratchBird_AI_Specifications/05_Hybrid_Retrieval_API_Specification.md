# ScratchBird Hybrid Retrieval API Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the canonical hybrid retrieval contract that combines:
1. vector similarity retrieval,
2. structured SQL filter constraints,
3. deterministic ranking and bounded result emission.

Out of scope:
1. end-user UI ranking preferences,
2. embedding model generation internals.

## 2. API Surface

Base path: `/v1/retrieval`

Required endpoint:
1. `POST /hybrid/search`

## 3. Request and Response Schemas

### 3.1 Request

```json
{
  "dialect": "native",
  "security_context": {
    "tenant_id": "tenant-a",
    "actor_id": "user-123",
    "roles": ["analyst"],
    "session_id": "sess-001",
    "context_version": 1
  },
  "query_text": "latest overdue invoices for north region",
  "query_embedding": [0.101, 0.202, 0.303],
  "vector_index_id": "idx_invoice_docs",
  "sql_filter": {
    "relation": "invoice_summary",
    "where": "status = 'OVERDUE' AND region = 'NORTH'"
  },
  "top_k": 20,
  "weights": {
    "vector": 0.60,
    "lexical": 0.30,
    "structured": 0.10
  },
  "options": {
    "timeout_ms": 1500,
    "max_rows": 200
  }
}
```

Validation rules:
1. `dialect` MUST be `native` for v1.
2. `top_k` MUST be `1..200`.
3. all weights MUST be in `[0.0, 1.0]`.
4. weight sum MUST equal `1.0` within tolerance `1e-6`.
5. `timeout_ms` MUST be `100..30000`.

### 3.2 Response

```json
{
  "results": [
    {
      "document_id": "inv-2026-0042",
      "vector_id": "inv-2026-0042#chunk-01",
      "scores": {
        "vector": 0.91,
        "lexical": 0.73,
        "structured": 1.00,
        "final": 0.866
      },
      "metadata": {
        "region": "NORTH",
        "status": "OVERDUE"
      }
    }
  ],
  "trace_id": "tr_...",
  "rls_applied": true,
  "query_plan_ref": "plan_..."
}
```

## 4. Execution Algorithm

The server MUST execute this sequence:
1. Validate request and security context.
2. Resolve RLS predicates from `security_context`.
3. Compile structured SQL filter with RLS predicate injection.
4. Execute vector candidate retrieval with tenant prefilter.
5. Execute structured filter candidate retrieval with pushdown preserved.
6. Join candidates by logical document identity.
7. Normalize scores:
   - `vector_norm in [0,1]`
   - `lexical_norm in [0,1]`
   - `structured_norm in [0,1]`
8. Compute final score:
   - `final = w_vector*vector_norm + w_lexical*lexical_norm + w_structured*structured_norm`
9. Sort by:
   1. `final DESC`
   2. `document_id ASC` (deterministic tie-break)
10. Emit top `top_k`.

## 5. Filter Pushdown Rules

1. Structured predicates MUST be pushed to SQL execution layer before result materialization.
2. RLS predicates MUST be logically `AND`-combined with caller filters.
3. If pushdown cannot be proven, request MUST fail with `E_FILTER_PUSHDOWN_UNAVAILABLE`.

## 6. Security Requirements

1. RLS MUST be applied before result emission.
2. Cross-tenant joins are forbidden.
3. If `security_context` is missing or invalid, request MUST fail with `E_POLICY_DENY`.
4. Any model-supplied instruction attempting to bypass filters MUST be ignored and audited.

## 7. Determinism Requirements

1. Identical request, security context, and data snapshot MUST produce identical ordered result IDs and final scores.
2. Floating-point values in output MUST be rounded to 6 decimal places.
3. Tie ordering MUST be lexical by `document_id`.

## 8. Error Model

Required error codes:
1. `E_INVALID_ARGUMENT`
2. `E_POLICY_DENY`
3. `E_RLS_ENFORCEMENT_FAILED`
4. `E_FILTER_PUSHDOWN_UNAVAILABLE`
5. `E_EXECUTION_FAILED`
6. `E_TIMEOUT`

## 9. Required Tests

1. End-to-end hybrid retrieval success path.
2. RLS denial path for cross-tenant request.
3. Filter pushdown verification test.
4. Deterministic ranking repeatability test.
5. Timeout and bounded-result tests.

## 10. Acceptance Criteria

1. All required tests pass.
2. RLS is applied before any response rows are emitted.
3. Deterministic ordering and scoring constraints hold across repeated runs.

## 11. Evidence Binding

1. This specification is bound to `EVID-05` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/05/hybrid_report.json`
   - `artifacts/ai_conformance/05/relevance_eval.json`
3. Hybrid quality claims are non-compliant unless grounded in repeatable evaluation artifacts captured by `EVID-05`.
