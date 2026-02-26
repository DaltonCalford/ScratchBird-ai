# ScratchBird AI Comparative Parity Matrix

## Scope
Defines minimum parity and exceed targets relative to external tools and standards referenced in `SOURCES_INDEX.md`.

## Capability Targets

| Capability area | Comparative baseline | Minimum parity requirement | Exceed target |
| --- | --- | --- | --- |
| Adapter interoperability | LangChain, LlamaIndex, MCP SDKs, Semantic Kernel | Stable adapter contracts for tool invocation, message role mapping, and structured response normalization | Cross-framework deterministic behavior test suite with identical prompts/tools and byte-stable normalized outputs |
| Tool calling schema | MCP tools, LangChain/LlamaIndex tool models, Anthropic tool use patterns | JSON Schema 2020-12 validation, strict argument coercion policy, explicit error envelopes | Versioned tool schema registry with compatibility guarantees and automated downgrade/upgrade checks |
| Structured outputs | OpenAPI + JSON Schema + framework structured-output support | Fail-closed validation on every model output that claims structure | Contract test generation from schema (positive + negative corpus) and conformance score reporting |
| Hybrid retrieval | Milvus, Qdrant, Weaviate, OpenSearch, Elasticsearch, Pinecone, Vespa, pgvector | Dense + sparse retrieval, filter-aware retrieval, rank fusion (RRF or equivalent), deterministic tie-break rules | Policy-driven dynamic fusion strategy (query-class aware), plus quality telemetry loop tied to BEIR-style metrics |
| Ranking/reranking | Elastic RRF + academic RRF/HNSW/BEIR references | Configurable fusion algorithm with explicit parameters and reproducible ranking snapshots | A/B evaluators with offline and online metrics; automatic regression blocking on relevance drift |
| Plan introspection | PostgreSQL/MySQL/DuckDB/SQLite EXPLAIN, OpenSearch/Elastic profile APIs | Structured explain payload with node types, estimated/actual costs, and timing | Plan diff API with deterministic node IDs and regression diagnostics across runs/builds |
| Execution modes | Multi-mode orchestration patterns from LangGraph/workflow systems | Explicit mode state machine and approval boundaries, with mode-specific constraints | Mode simulation harness that proves transitions and safety invariants across failure cases |
| Deterministic audit bundle | RFC 8785, RFC 3161, RFC 6962, in-toto/SLSA, CloudTrail integrity patterns | Canonical serialization + SHA-256 digests + artifact manifest + trace correlation IDs | Cryptographic attestations for bundles and tamper-evidence verification CLI integrated into CI |
| Cluster-aware routing | MCP transport guidance, distributed system best practices, OpenTelemetry correlation | Health-aware endpoint selection, timeout/retry budgets, trace propagation across hops | Predictive routing with SLO-aware admission control and deterministic failover reason codes |
| Security/governance | NIST AI RMF + GenAI Profile + OWASP LLM guidance | Threat model coverage, policy controls, auditability, abuse resistance checks | Continuous control validation with security scorecards mapped to RMF functions and release gates |

## Implementation Gate Criteria

1. Every capability area must have one normative spec section with:
- Input/output contract
- Error taxonomy
- Security constraints
- Conformance tests

2. Every capability area must have at least one comparative validation test:
- Same scenario executed against ScratchBird AI path and baseline semantics
- Differences classified as intentional or defect

3. “Exceed target” claims are allowed only when measured evidence exists:
- Benchmark result, conformance report, or deterministic replay artifact
- Stored under `docs/library/` or project test artifacts
