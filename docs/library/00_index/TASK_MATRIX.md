# ScratchBird AI Research Task Matrix

## Objective
Collect authoritative specifications, whitepapers, and best-practice references required to implement and validate:
- `docs/specifications/ScratchBird_AI_Specifications/01_ScratchBird_AI_Integration_Roadmap.md`
- `docs/specifications/ScratchBird_AI_Specifications/02_LangChain_Adapter_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/03_LlamaIndex_Adapter_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/04_VectorStore_API_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/05_Hybrid_Retrieval_API_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/06_Tool_Calling_Schema_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/07_Plan_Introspection_API_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/08_AI_Execution_Mode_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/09_Deterministic_Audit_Bundle_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/10_Cluster_Aware_AI_Routing_Specification.md`
- `docs/specifications/ScratchBird_AI_Specifications/11_Cross_Spec_Conformance_Matrix.md`
- `docs/specifications/ScratchBird_AI_Specifications/12_External_Evidence_Traceability.md`

## Batch Plan

1. Core Standards and Interop
- Scope: RFC 2119, OpenAPI 3.1, JSON Schema 2020-12, JCS (RFC 8785), JWT (RFC 7519), MCP.
- Output folder: `docs/library/01_core_standards/`
- Primary specs covered: 01, 06, 08, 09, 10, 11.

2. Security and Governance
- Scope: NIST AI RMF, OWASP LLM/GenAI guidance, OpenTelemetry semantic conventions.
- Output folder: `docs/library/02_security_governance/`
- Primary specs covered: 06, 08, 09, 10, 11.

3. Framework and Protocol Adapters
- Scope: LangChain, LlamaIndex, model/tool invocation and structured output contracts.
- Output folder: `docs/library/03_frameworks_protocols/`
- Primary specs covered: 02, 03, 06, 08.

4. Vector and Hybrid Retrieval
- Scope: Vector DB and hybrid retrieval practices across Milvus, OpenSearch, Elasticsearch, Weaviate, Pinecone, Qdrant, Vespa.
- Output folder: `docs/library/04_vector_hybrid/`
- Comparative references output: `docs/library/06_comparative_tools/`
- Primary specs covered: 04, 05, 10, 11.

5. Planning, Introspection, and Auditability
- Scope: EXPLAIN plan formats, deterministic logging/auditing, telemetry traces/logs correlation.
- Output folder: `docs/library/05_planning_introspection/`
- Primary specs covered: 07, 08, 09, 11.

6. Consolidated Evidence Index
- Scope: Link all collected sources to spec requirements and parity/exceed criteria.
- Output folder: `docs/library/00_index/`
- Primary specs covered: all.

## Evidence Policy
- Download source artifacts locally when licensing/access permits.
- Store one metadata entry per source with:
  - Source URL
  - Retrieval date (UTC)
  - Topic tags
  - Target spec mapping
  - Notes on relevance and parity implications
- Keep source text in library; do not rely on context-only memory.
