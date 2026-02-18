# Technical Report: AI-to-Database Integration Methods (Direct + Indirect)

Date: February 18, 2026

## 1) Scope and Definitions

This report covers the main patterns used by modern AI systems to access database-backed knowledge:

- Direct access: the model (or model-driven tool loop) executes database queries/actions itself.
- Indirect access: the model calls a middleware layer (semantic layer, retrieval service, analytics API, graph pipeline) that then queries databases.

"Fully support features" in this report means implementing both:

- Core capability features (querying, retrieval, execution, tool orchestration)
- Production features (authz, safety, governance, observability, reliability, and evaluation)

## 2) Current Method Map

1. Function-calling SQL tools (direct)
2. MCP database servers (direct or indirect, standardized)
3. Text-to-SQL agent frameworks (direct SQL behind orchestration)
4. Semantic layer query tools (indirect, governed metric APIs)
5. Vector/hybrid retrieval tools (indirect RAG)
6. GraphRAG tools (indirect+direct graph query)
7. Managed NL analytics APIs (indirect, fully managed)

## 3) Method 1: Function-Calling SQL Tool (Direct)

### What it is

Use model tool/function calling to generate typed query requests, execute query code in your application, and return structured results to the model.

### Feature-complete requirements

- Tool schema with strict JSON typing
- Multi-turn tool loop (model -> tool call -> tool output -> model)
- Query allowlist or SQL AST validation
- Parameterized SQL only (no string concatenation)
- Read-only DB role by default
- Per-query timeout + row/result size caps
- Cost/budget guards (max scanned rows, max tokens, max tool calls)
- Audit log (who asked, SQL executed, latency, rows returned)
- Retry policy for transient DB errors

### Reference architecture

- LLM runtime: OpenAI Responses API tools/function calling
- Execution layer: SQLAlchemy (or native DB driver)
- Guardrails: SQL parser/allowlist + query budget middleware
- DB access: read replica or analytics warehouse role

### Python example (direct SQL tool loop)

```python
import json
from typing import Any
from openai import OpenAI
from sqlalchemy import create_engine, text

client = OpenAI()
engine = create_engine("postgresql+psycopg://ro_user:***@db.example/app")

TOOLS = [
    {
        "type": "function",
        "name": "run_readonly_sql",
        "description": "Execute read-only SQL with bound parameters",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "params": {"type": "object", "additionalProperties": True}
            },
            "required": ["sql"],
            "additionalProperties": False
        },
        "strict": True,
    }
]


def enforce_readonly(sql: str) -> None:
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke"]
    lowered = sql.lower()
    if any(tok in lowered for tok in forbidden):
        raise ValueError("Non-read-only SQL blocked")


def run_readonly_sql(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    enforce_readonly(sql)
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        rows = [dict(r._mapping) for r in result.fetchmany(200)]  # hard cap
    return {"rows": rows, "row_count": len(rows)}


user_question = "Top 5 customers by total revenue in 2025"
response = client.responses.create(
    model="gpt-5",
    input=user_question,
    tools=TOOLS,
)

while True:
    tool_calls = [item for item in response.output if item.type == "function_call"]
    if not tool_calls:
        print(response.output_text)
        break

    tool_outputs = []
    for call in tool_calls:
        args = json.loads(call.arguments)
        out = run_readonly_sql(args["sql"], args.get("params"))
        tool_outputs.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": json.dumps(out),
        })

    response = client.responses.create(
        model="gpt-5",
        previous_response_id=response.id,
        input=tool_outputs,
    )
```

## 4) Method 2: MCP Database Server (Standardized Tooling)

### What it is

Expose database capabilities via MCP so any MCP-capable client/agent can discover and call your tools/resources/prompts.

### Feature-complete requirements

- MCP primitives: tools + resources + prompts
- Transport support:
  - `stdio` for local workflows
  - Streamable HTTP for remote workflows
- OAuth for remote deployments
- Tool-level access controls (read vs write separation)
- Session-scoped tenant context propagation
- Structured output schemas for tool responses
- Rate limits + quota enforcement per user/workspace
- Server-side validation against prompt-injection-style tool misuse

### Minimal MCP database toolset

- `list_schemas`
- `list_tables`
- `describe_table`
- `run_sql_readonly`
- `explain_sql`
- Optional write tools behind explicit approval:
  - `run_sql_mutation`

### Python MCP server skeleton

```python
from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text

mcp = FastMCP("db-tools", json_response=True)
engine = create_engine("postgresql+psycopg://ro_user:***@db.example/app")

@mcp.tool()
def list_tables(schema: str = "public") -> list[str]:
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = :schema
    ORDER BY table_name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"schema": schema}).fetchall()
    return [r[0] for r in rows]

@mcp.tool()
def run_sql_readonly(sql: str, limit: int = 200) -> dict:
    lowered = sql.lower()
    if any(x in lowered for x in ["insert", "update", "delete", "drop", "alter", "truncate"]):
        raise ValueError("Non-read-only SQL blocked")

    wrapped = f"SELECT * FROM ({sql}) q LIMIT :limit"
    with engine.connect() as conn:
        rows = conn.execute(text(wrapped), {"limit": min(limit, 200)}).fetchmany(200)
    return {"rows": [dict(r._mapping) for r in rows]}

if __name__ == "__main__":
    mcp.run()  # stdio transport by default in many SDK examples
```

### OpenAI Responses API calling a remote MCP server

```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5",
    "input": "List the top 10 products by gross margin last quarter",
    "tools": [
      {
        "type": "mcp",
        "server_label": "finance_db",
        "server_url": "https://mcp.example.com/mcp",
        "allowed_tools": ["list_tables", "run_sql_readonly"],
        "require_approval": "never"
      }
    ]
  }'
```

## 5) Method 3: Text-to-SQL Agent Frameworks

### What it is

A framework-driven orchestration pipeline that converts NL -> SQL with iterative checking and execution.

### Representative ecosystems

- LangChain `SQLDatabaseToolkit`
- LlamaIndex Text-to-SQL query engines/retrievers
- Vanna (agentic RAG memory for SQL generation)

### Feature-complete requirements

- Schema introspection and schema retrieval (table/column pruning)
- Query synthesis prompt with dialect awareness
- SQL checker/rewrite step before execution
- Error-recovery loop (DB error -> repair prompt -> retry)
- Business logic memory/examples (few-shot retrieval)
- Optional charting + natural-language result explanation
- User-aware permissions and row filters

### Example orchestration pseudocode

```python
# Simplified framework-agnostic text-to-SQL loop
schema_ctx = schema_retriever.get_relevant_schema(user_question)
sql = sql_generator.generate(question=user_question, schema=schema_ctx, dialect="postgres")

review = sql_checker.validate(sql)
if not review.ok:
    sql = sql_rewriter.rewrite(sql, review.feedback)

rows = db_executor.run_readonly(sql)
answer = synthesizer.summarize(question=user_question, rows=rows, sql=sql)
return {"sql": sql, "rows": rows, "answer": answer}
```

## 6) Method 4: Semantic Layer Tool (Governed Indirect Access)

### What it is

The model queries metrics/entities through a semantic API instead of generating raw warehouse SQL each time.

### Representative systems

- dbt Semantic Layer APIs (GraphQL/JDBC/Python SDK)
- Cube semantic-layer APIs (SQL/REST/GraphQL, governance controls)
- Snowflake Cortex Analyst (NL -> SQL against semantic model/view)
- Databricks AI/BI Genie spaces

### Feature-complete requirements

- Metric catalog discovery (metrics, dimensions, entities, granularities)
- Query creation API + async status polling
- Role-aware governance and consistent metric definitions
- Saved query reuse
- Compiled SQL traceability for audit/debug
- Time grain and filter validation

### dbt Semantic Layer GraphQL example

```python
import os
import time
import requests

BASE = "https://semantic-layer.cloud.getdbt.com/api/graphql"
TOKEN = os.environ["DBT_TOKEN"]
ENV_ID = int(os.environ["DBT_ENVIRONMENT_ID"])

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

create_query = {
  "query": """
    mutation CreateQ($env: BigInt!) {
      createQuery(
        environmentId: $env,
        metrics: [{name: \"revenue\", alias: \"revenue\"}],
        groupBy: [{name: \"metric_time\", grain: MONTH}]
      ) { queryId }
    }
  """,
  "variables": {"env": ENV_ID}
}

qid = requests.post(BASE, json=create_query, headers=headers, timeout=30).json()["data"]["createQuery"]["queryId"]

poll_query = {
  "query": """
    query Poll($env: BigInt!, $qid: String!) {
      query(environmentId: $env, queryId: $qid) {
        status
        error
        sql
        jsonResult
      }
    }
  """
}

while True:
    resp = requests.post(BASE, json={**poll_query, "variables": {"env": ENV_ID, "qid": qid}}, headers=headers, timeout=30).json()
    q = resp["data"]["query"]
    if q["status"] in ("SUCCESSFUL", "FAILED"):
        print(q)
        break
    time.sleep(1.0)
```

### Snowflake Cortex Analyst REST example

```bash
curl -X POST "https://<account>.snowflakecomputing.com/api/v2/cortex/analyst/message" \
  -H "Authorization: Bearer $SNOWFLAKE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role":"user","content":[{"type":"text","text":"Which region had highest margin last quarter?"}]}],
    "semantic_model_file": "@MY_DB.MY_SCHEMA.MY_STAGE/semantic_model.yaml"
  }'
```

## 7) Method 5: Vector + Hybrid Retrieval Tool (Indirect)

### What it is

Use embeddings + vector indexes (optionally lexical/BM25 fusion) to retrieve relevant chunks, then generate an answer.

### Representative stacks

- Postgres + pgvector
- OpenSearch `knn_vector`
- Weaviate hybrid search
- Pinecone hybrid (dense+sparse)
- Milvus/Qdrant hybrid + reranking
- MongoDB Atlas Vector Search

### Feature-complete requirements

- Dense indexing and search
- Sparse/keyword retrieval (or BM25) for exact-term recall
- Hybrid rank fusion and reranking
- Metadata filters and tenant isolation
- Incremental indexing pipeline + re-embedding strategy
- Eval harness (recall@k, ndcg@k, answer faithfulness)

### Postgres hybrid retrieval example (pgvector + FTS)

```sql
-- 1) vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) corpus table
CREATE TABLE docs (
  id bigserial PRIMARY KEY,
  tenant_id text NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- 3) indexes
CREATE INDEX docs_embedding_hnsw ON docs USING hnsw (embedding vector_cosine_ops);
CREATE INDEX docs_tsv_idx ON docs USING GIN (tsv);
```

```python
# Hybrid rank fusion in application code
import math
from sqlalchemy import text

def reciprocal_rank_fusion(rank_lists, k=60):
    scores = {}
    for lst in rank_lists:
        for rank, doc_id in enumerate(lst, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

# dense_rank_ids: ids from vector similarity
# lexical_rank_ids: ids from BM25/FTS
final = reciprocal_rank_fusion([dense_rank_ids, lexical_rank_ids])
```

## 8) Method 6: GraphRAG Tool (Graph + Vector + Path Reasoning)

### What it is

Retrieve context from graph structure (entities/relations/path constraints) and vector similarity, then synthesize answers.

### Representative stack

- Neo4j vector indexes + Cypher
- Neo4j GraphRAG Python package

### Feature-complete requirements

- Entity extraction and graph ingestion pipeline
- Vector indexing on node/relationship properties
- Graph pattern retrieval (Cypher templates)
- Path explanation output (why this answer)
- Hybrid retriever (vector prefilter + graph traversal)
- Graph update strategy for evolving knowledge

### Neo4j example

```cypher
CREATE VECTOR INDEX doc_embedding_idx
FOR (d:Document)
ON (d.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};
```

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j+s://<id>.databases.neo4j.io", auth=("neo4j", "***"))

QUERY = """
CALL db.index.vector.queryNodes('doc_embedding_idx', 10, $embedding)
YIELD node, score
MATCH (node)-[:MENTIONS]->(e:Entity)
RETURN node.id AS doc_id, score, collect(DISTINCT e.name) AS entities
ORDER BY score DESC
"""

with driver.session() as s:
    rows = s.run(QUERY, embedding=query_embedding).data()
```

## 9) Method 7: Managed NL Analytics APIs (Indirect, Platform Native)

### What it is

Use vendor-managed NL query services that convert natural language to SQL under governance and semantic context.

### Examples

- Snowflake Cortex Analyst
- Databricks AI/BI Genie

### Feature-complete requirements when building equivalent in-house

- Semantic modeling layer with high-quality metadata
- Conversation memory and follow-up question grounding
- Clarification question support
- SQL + result + explanation output modes
- Quality feedback loop (analyst corrections -> improved behavior)
- Trusted assets or approved logic overlays

## 10) Cross-Cutting Features Required for "Full" Tool Support

### Security and governance

- Least-privilege DB roles (separate read and mutation roles)
- Parameterized SQL everywhere
- Row-level security / tenant filters in DB and/or middleware
- Approval gates for write actions
- Tool argument validation and strict schemas
- Prompt-injection mitigations for tool use

### Reliability and scale

- Async/background execution for long-running jobs
- Streaming partial results where possible
- Idempotency keys for retries
- Circuit breakers for overloaded warehouses
- Query cancellation support

### Observability and operations

- Trace every tool call (input, SQL, latency, result size)
- Redaction for sensitive data in logs
- Cost attribution by tenant/user
- SLOs: p95 latency, failure rate, timeout rate

### Quality and evaluation

- Benchmarks per method:
  - Text-to-SQL execution accuracy
  - Retrieval recall@k / ndcg@k
  - Answer faithfulness/grounding
  - Metric consistency vs BI gold queries
- Regression suites for schema drift and model changes

## 11) Suggested Implementation Roadmap

1. Build Method 1 (direct function-calling SQL) with strict read-only controls
2. Add Method 5 (vector/hybrid retrieval) for unstructured context
3. Add Method 4 (semantic layer integration) for governed metrics
4. Standardize via Method 2 (MCP server) to make capabilities reusable by any MCP client
5. Add Method 6 (GraphRAG) for relationship-heavy domains
6. Add managed API connectors (Method 7) where platform-native acceleration is desired
7. Roll out write-capable tools only after approval workflow + policy tests are in place

## 12) Build-vs-Buy Guidance

- Build first when you need custom policy logic, on-prem constraints, or deep product embedding.
- Buy/managed first when speed-to-value and operational offload are higher priority.
- Common hybrid approach: managed semantic/text-to-SQL API + custom MCP gateway + internal policy engine.

## 13) Notes on Inference vs Explicit Documentation

The protocol/feature facts in this report come from vendor docs below. The taxonomy, reference architectures, and phased roadmap are engineering inferences synthesized across those sources.

## 14) Sources

- OpenAI Responses tools/function-calling/background/MCP:
  - https://platform.openai.com/docs/guides/background
  - https://platform.openai.com/docs/guides/tools/tool-choice
  - https://platform.openai.com/docs/mcp/
  - https://openai.com/index/new-tools-and-features-in-the-responses-api/
  - https://help.openai.com/en/articles/8555517-function-calling-updates
- MCP specification and security:
  - https://modelcontextprotocol.io/specification/2025-11-25/basic
  - https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
  - https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices
  - https://modelcontextprotocol.io/docs/sdk
- LangChain / LlamaIndex / Vanna:
  - https://docs.langchain.com/oss/python/integrations/tools/sql_database/
  - https://docs.llamaindex.ai/en/stable/examples/index_structs/struct_indices/SQLIndexDemo/
  - https://vanna.ai/docs/
- Semantic layer and managed NL analytics:
  - https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl
  - https://docs.getdbt.com/docs/dbt-cloud-apis/sl-api-overview
  - https://docs.getdbt.com/docs/dbt-cloud-apis/sl-graphql
  - https://docs.getdbt.com/docs/dbt-ai/about-mcp
  - https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
  - https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api
  - https://docs.databricks.com/aws/en/genie
- Vector/hybrid retrieval databases:
  - https://github.com/pgvector/pgvector
  - https://docs.opensearch.org/latest/vector-search/vector-search-techniques/index/
  - https://docs.weaviate.io/weaviate/search/hybrid
  - https://docs.pinecone.io/docs/hybrid-search
  - https://blog.milvus.io/docs/milvus_hybrid_search_retriever.md
  - https://www.mongodb.com/docs/atlas/atlas-vector-search/transform-documents-collections/
- GraphRAG / graph vector search:
  - https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
  - https://neo4j.com/docs/neo4j-graphrag-python/current/index.html
- Security practices for SQL execution:
  - https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
  - https://www.postgresql.org/docs/current/sql-createpolicy.html
