# ScratchBird Cluster-Aware AI Routing Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define cluster-aware AI routing contracts for:
1. topology inspection,
2. SQL query routing,
3. distributed vector search.

Out of scope:
1. cluster membership protocols,
2. low-level replication mechanics.

## 2. Required APIs

Base path: `/v1/cluster`

Required operations:
1. `GET /topology` (`get_cluster_topology`)
2. `POST /route/query` (`route_query`)
3. `POST /route/vector-search` (`distributed_vector_search`)

## 3. Topology Model

`get_cluster_topology` response MUST include:

```json
{
  "cluster_id": "cluster-a",
  "cluster_epoch": 42,
  "generated_at": "2026-02-24T13:00:00Z",
  "shards": [
    {
      "shard_id": "s01",
      "tenant_range": ["tenant-a", "tenant-f"],
      "primary_node": "node-1",
      "replicas": ["node-2", "node-3"],
      "status": "healthy"
    }
  ],
  "trace_id": "tr_..."
}
```

Rules:
1. `cluster_epoch` MUST be monotonically increasing for topology changes.
2. `status` MUST be one of:
   - `healthy`
   - `degraded`
   - `offline`

## 4. route_query Contract

Request:

```json
{
  "dialect": "native",
  "query_text": "SELECT ...",
  "security_context": {
    "tenant_id": "tenant-a",
    "actor_id": "user-123",
    "roles": ["analyst"],
    "session_id": "sess-001",
    "context_version": 1
  },
  "options": {
    "timeout_ms": 5000,
    "max_rows": 200
  }
}
```

Response:

```json
{
  "cluster_epoch": 42,
  "route_plan_id": "rp_...",
  "target_shards": ["s01", "s02"],
  "execution_mode": "single_shard",
  "trace_id": "tr_..."
}
```

Execution modes:
1. `single_shard`
2. `multi_shard`
3. `broadcast_read` (read-only metadata-safe paths only)

## 5. distributed_vector_search Contract

Request:

```json
{
  "index_id": "idx_docs",
  "query_embedding": [0.11, 0.22, 0.33],
  "top_k": 20,
  "security_context": {
    "tenant_id": "tenant-a",
    "actor_id": "user-123",
    "roles": ["analyst"],
    "session_id": "sess-001",
    "context_version": 1
  },
  "options": {
    "timeout_ms": 1500
  }
}
```

Response:

```json
{
  "cluster_epoch": 42,
  "participating_shards": ["s01", "s02"],
  "results": [],
  "trace_id": "tr_...",
  "rls_applied": true
}
```

## 6. Routing Algorithm

For both query and vector routing:
1. validate security context and tenant ownership,
2. fetch latest topology snapshot,
3. if caller-supplied `cluster_epoch` exists and mismatches current epoch, fail with `E_CLUSTER_EPOCH_MISMATCH`,
4. determine candidate shards from tenant-to-shard mapping,
5. remove unhealthy shards unless explicitly allowed by failover policy,
6. route to primary; fallback to replica if primary unavailable,
7. execute per-shard requests with bounded timeout,
8. merge results deterministically:
   - score DESC
   - shard_id ASC
   - document_id ASC

## 7. Security and Isolation

1. Shard isolation and RLS MUST both be enforced.
2. Cross-tenant shard access is forbidden.
3. `broadcast_read` is not permitted for mutation operations.
4. Unknown shard ownership MUST fail closed.

## 8. Failure Handling

Required error codes:
1. `E_CLUSTER_EPOCH_MISMATCH`
2. `E_ROUTE_UNAVAILABLE`
3. `E_SHARD_UNAUTHORIZED`
4. `E_TIMEOUT`
5. `E_EXECUTION_FAILED`

Timeout behavior:
1. partial shard timeouts in read paths MAY return partial results only if `allow_partial=true` is explicitly set.
2. mutation paths MUST NOT allow partial success.

## 9. Observability

Each routed request MUST emit:
1. `trace_id`
2. `cluster_epoch`
3. participating shard IDs
4. route decision reason
5. failover events

## 10. Required Tests

1. Topology schema and epoch monotonicity tests.
2. Shard authorization and cross-tenant denial tests.
3. Failover tests (primary down -> replica).
4. Deterministic merge ordering tests.
5. Epoch mismatch negative tests.

## 11. Acceptance Criteria

1. Required APIs are implemented and schema-conformant.
2. Routing is deterministic and secure.
3. Partial-failure semantics match this specification.

## 12. Evidence Binding

1. This specification is bound to `EVID-10` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/10/routing_report.json`
   - `artifacts/ai_conformance/10/failover_report.json`
3. Cluster routing readiness MUST be denied if `EVID-10` parity gates or runtime exceed-domain criteria fail.
