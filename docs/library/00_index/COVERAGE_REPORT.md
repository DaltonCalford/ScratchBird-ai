# ScratchBird AI Research Coverage Report

## Coverage Status

| Spec task | Evidence coverage | Notes |
| --- | --- | --- |
| `01_ScratchBird_AI_Integration_Roadmap.md` | High | Core standards, governance controls, comparative framework baselines captured |
| `02_LangChain_Adapter_Specification.md` | High | LangChain + LangGraph + MCP spec and SDK references captured |
| `03_LlamaIndex_Adapter_Specification.md` | High | LlamaIndex agent/workflow/tool references captured |
| `04_VectorStore_API_Specification.md` | High | Multi-engine vector store references (Milvus, Qdrant, Weaviate, OpenSearch, Elastic, Pinecone, Vespa, pgvector) captured |
| `05_Hybrid_Retrieval_API_Specification.md` | High | Hybrid retrieval docs plus RRF/HNSW/BEIR benchmark papers captured |
| `06_Tool_Calling_Schema_Specification.md` | High | MCP + JSON Schema + framework tool-calling references captured |
| `07_Plan_Introspection_API_Specification.md` | High | SQL/search EXPLAIN and PROFILE references across PostgreSQL/MySQL/DuckDB/SQLite/OpenSearch/Elastic/ClickHouse captured |
| `08_AI_Execution_Mode_Specification.md` | High | Governance + orchestration workflow references captured |
| `09_Deterministic_Audit_Bundle_Specification.md` | High | RFC 8785/3161/6962 + in-toto attestation + SLSA + CloudTrail integrity references captured |
| `10_Cluster_Aware_AI_Routing_Specification.md` | Medium-High | MCP transport/auth + OpenTelemetry + hybrid search cluster behavior references captured |
| `11_Cross_Spec_Conformance_Matrix.md` | High | Parity matrix and cross-spec evidence mappings captured |
| `12_External_Evidence_Traceability.md` | High | Explicit evidence IDs, required proof artifacts, and release-domain exceed gates defined |

## Comparative Tool Coverage

Captured comparative references include:
- Frameworks: LangChain, LangGraph, LlamaIndex, Semantic Kernel, Haystack
- Tooling/protocol: MCP SDKs, Anthropic tool use patterns
- Retrieval engines: Milvus, Qdrant, Weaviate, OpenSearch, Elasticsearch, Pinecone, Vespa, pgvector, Chroma
- Planning/introspection: PostgreSQL, MySQL, DuckDB, SQLite, OpenSearch, Elasticsearch, ClickHouse
- Auditability patterns: NIST logging guidance, in-toto attestation, SLSA provenance, CloudTrail integrity
- Benchmarks/whitepapers: HNSW, BEIR, RRF, ANN benchmarks, MTEB

## Blocked Source Notes (Mitigated)

- OpenAI docs pages returned HTTP 403 from CLI (`platform.openai.com/docs/...`).
- MySQL doc page on `dev.mysql.com` returned HTTP 403; Oracle-hosted MySQL 8.4 mirror was used.
- `in-toto.io/spec/` returned HTTP 404; canonical upstream attestation spec repository was used.
- `docs.milvus.io` DNS/HTTP issues from CLI; canonical Milvus docs repository content (`milvus-docs` v2.6.x) was used.

All mitigations are recorded in `SOURCES_INDEX.md`.
