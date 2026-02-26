# ScratchBird LlamaIndex Adapter Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the required LlamaIndex integration surface for ScratchBird AI:
1. SQLQueryEngine adapter.
2. Vector index adapter.
3. Hybrid retrieval adapter.
4. Plan-introspection metadata exposure.

Out of scope:
1. Custom LlamaIndex orchestration plugins unrelated to query execution.
2. Non-native dialect support for v1.

## 2. Compatibility Contract

1. Supported runtime:
   - `llama-index-core >=0.11,<0.12`
2. Required exported classes:
   - `ScratchBirdSQLQueryEngine`
   - `ScratchBirdVectorStore`
   - `ScratchBirdHybridRetriever`
3. v1 dialect scope:
   - `native` only.

## 3. Required Interfaces

### 3.1 SQLQueryEngine Adapter

Required operations:
1. `query(query_text: str, execution_mode: str = "ai_analysis", approval_token: str | None = None, context: dict | None = None) -> QueryResponse`
2. `explain(query_text: str, context: dict | None = None) -> PlanIntrospectionResult`

Rules:
1. `query` MUST call compile then execute; direct execute is forbidden.
2. `execution_mode` semantics MUST match specification `08`.
3. Output MUST include `compile_artifact_id`, `execution_artifact_id`, and `trace_id`.

### 3.2 BaseVectorStore Implementation

`ScratchBirdVectorStore` MUST implement LlamaIndex `BaseVectorStore` contract.

Required methods:
1. `add(nodes: list[NodeWithEmbedding], **kwargs) -> list[str]`
2. `query(query: VectorStoreQuery, **kwargs) -> VectorStoreQueryResult`
3. `delete(ref_doc_id: str, **kwargs) -> None`

Rules:
1. Embedding dimensions MUST be validated per index.
2. Tenant and RLS context MUST be required for `add`, `query`, and `delete`.
3. Query path MUST deny operation when security context is absent.

### 3.3 Hybrid Retriever

Required method:
1. `retrieve(query_bundle: QueryBundle, **kwargs) -> list[NodeWithScore]`

Rules:
1. Retriever MUST combine vector and structured constraints using specification `05`.
2. Result ordering MUST be deterministic for equal scores using lexical `document_id` tiebreaker.

## 4. Structured Plan Metadata

1. `explain` MUST return:
   - `plan_hash`
   - `operator_tree`
   - `rls_visibility`
   - `estimated_cost`
2. `plan_hash` MUST follow specification `07`.
3. No row-level protected data may appear in plan output.

## 5. Security Requirements

1. RLS enforcement is mandatory for SQL, vector, and hybrid operations.
2. Mutation in `query` path MUST require approved mode + valid approval evidence.
3. Adapter MUST reject user/model attempts to inject security overrides in prompt text.

## 6. Failure Semantics

1. Compile errors MUST fail before execution and return `E_COMPILE_FAILED`.
2. Policy denials MUST return `E_POLICY_DENY` and include `policy_rule_id`.
3. Missing security context for vector/hybrid operations MUST return `E_RLS_ENFORCEMENT_FAILED`.
4. Timeouts MUST return `E_TIMEOUT`.

## 7. Telemetry Requirements

Each call MUST emit:
1. `trace_id`
2. `tenant_id`
3. `execution_mode`
4. `compile_ms` and/or retrieval stage latency
5. outcome (`success|denied|error`)

## 8. Required Tests

1. Interface conformance tests for `BaseVectorStore`.
2. Integration tests:
   - SQL read query success.
   - mutation denied without approval.
   - mutation success with approval.
3. RLS tests:
   - cross-tenant retrieval denied.
   - same-tenant retrieval allowed.
4. Determinism tests:
   - identical explain inputs produce identical `plan_hash`.
5. Serialization tests for structured plan metadata.

## 9. Acceptance Criteria

1. All required tests pass in CI.
2. Plan metadata is deterministic and secure.
3. No adapter path allows execution without compile stage.
4. No adapter path returns cross-tenant rows or embeddings.

## 10. Evidence Binding

1. This specification is bound to `EVID-03` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/03/adapter_parity.json`
   - `artifacts/ai_conformance/03/test_report.junit.xml`
3. Claims of framework parity are invalid unless `EVID-03` is `PASS`.
