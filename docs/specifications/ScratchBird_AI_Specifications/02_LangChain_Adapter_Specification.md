# ScratchBird LangChain Adapter Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the required LangChain integration surface for ScratchBird AI:
1. SQL query adapter.
2. Vector store adapter.
3. Hybrid retriever adapter.
4. Policy-aware execution mode enforcement.

Out of scope:
1. LangChain internal scheduler behavior.
2. Non-native ScratchBird dialect adapters for v1.

## 2. Compatibility Contract

1. The adapter MUST support:
   - `langchain-core >=0.3,<0.4`
   - `langchain-community >=0.3,<0.4`
2. The adapter MUST expose stable entrypoints:
   - `ScratchBirdLangChainSQLAdapter`
   - `ScratchBirdLangChainVectorStore`
   - `ScratchBirdLangChainHybridRetriever`
3. v1 dialect support is `native` only.

## 3. Canonical Interfaces

### 3.1 SQL Adapter

Required methods:
1. `compile_query(dialect: str, query_text: str, context: dict) -> CompileResult`
2. `execute_compiled(compile_artifact_id: str, options: dict, execution_mode: str, approval_token: str | None) -> ExecuteResult`
3. `run_query(dialect: str, query_text: str, options: dict, execution_mode: str, approval_token: str | None) -> QueryResponse`
4. `explain_query(dialect: str, query_text: str, options: dict) -> PlanIntrospectionResult`

Validation rules:
1. `dialect` MUST equal `native` in v1.
2. `query_text` MUST be non-empty UTF-8 text.
3. `execution_mode` MUST be one of:
   - `ai_analysis`
   - `ai_mutation_pending_approval`
   - `ai_mutation_approved`
4. Legacy aliases MAY be accepted:
   - `read_only` => `ai_analysis`
   - `mutation_with_approval` => `ai_mutation_pending_approval`

### 3.2 Vector Adapter

Required methods:
1. `add_embeddings(index_id: str, records: list[VectorRecord], security_context: SecurityContext) -> AddEmbeddingsResult`
2. `similarity_search(index_id: str, query_embedding: list[float], top_k: int, filters: dict, security_context: SecurityContext) -> VectorSearchResult`

### 3.3 Hybrid Adapter

Required method:
1. `hybrid_search(request: HybridSearchRequest, security_context: SecurityContext) -> HybridSearchResult`

## 4. Execution Semantics

1. Compile/execute separation is mandatory:
   - SQL execution MUST NOT occur without a compile artifact.
2. Read-only default:
   - If mode is absent, adapter MUST enforce `ai_analysis`.
3. Mutation:
   - MUST be denied unless mode is `ai_mutation_approved` and approval evidence validates.
4. Vector/hybrid retrieval:
   - MUST enforce RLS and tenant isolation before result emission.

## 5. Error Handling

1. SQLSTATE propagation:
   - If underlying service returns SQLSTATE, adapter MUST surface it in `sqlstate`.
2. Canonical adapter error payload:

```json
{
  "error_code": "E_COMPILE_FAILED",
  "message": "compile error details",
  "sqlstate": "42000",
  "retryable": false,
  "trace_id": "tr_..."
}
```

3. Required error codes:
   - `E_POLICY_DENY`
   - `E_DIALECT_UNAVAILABLE`
   - `E_COMPILE_FAILED`
   - `E_EXECUTION_FAILED`
   - `E_TIMEOUT`
   - `E_RLS_ENFORCEMENT_FAILED`
4. Unknown runtime errors MUST map to `E_EXECUTION_FAILED` and be fail-closed.

## 6. Security Controls

1. Every call MUST include authenticated security context:
   - `tenant_id`
   - `actor_id`
   - `roles`
2. Adapter MUST reject prompt-provided attempts to override policy, mode, or RLS clauses.
3. Mutation requires explicit override:
   - Valid approval token with unexpired signature.
   - Token claims MUST match `tenant_id`, `actor_id`, and `statement_hash`.

## 7. Performance and Reliability

1. Adapter MUST support request timeout configuration.
2. Adapter MUST enforce bounded row limits on SQL responses.
3. Adapter MUST expose structured telemetry fields:
   - `trace_id`, `compile_ms`, `execute_ms`, `rows_returned`, `policy_rule_id`.

## 8. Required Tests

1. Contract tests:
   - Method signature and payload conformance.
2. Security tests:
   - Mutation denied without approval.
   - RLS bypass attempts denied.
3. Determinism tests:
   - Same compile input => same `compile_artifact_id`.
4. Error mapping tests:
   - SQLSTATE and adapter error codes preserved.
5. Integration tests:
   - End-to-end LangChain call path for read-only, mutation denied, mutation approved.

## 9. Acceptance Criteria

1. All required tests pass in CI.
2. `native` read path produces deterministic compile artifacts.
3. Policy denials include explicit rule ID and reason.
4. No operation path bypasses compile step or RLS enforcement.

## 10. Evidence Binding

1. This specification is bound to `EVID-02` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/02/adapter_parity.json`
   - `artifacts/ai_conformance/02/test_report.junit.xml`
3. `EVID-02` is `PASS` only when all minimum parity gates succeed and artifact metadata fields are complete.
