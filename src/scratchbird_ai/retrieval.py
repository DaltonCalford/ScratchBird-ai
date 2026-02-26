"""Engine-free vector and hybrid retrieval scaffolding with deterministic output."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .deterministic import deterministic_id
from .tool_schema import ToolContractError, require_security_context


class RetrievalError(RuntimeError):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        policy_rule_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.policy_rule_id = policy_rule_id
        self.retryable = retryable


@dataclass(slots=True, frozen=True)
class VectorRecord:
    vector_id: str
    embedding: tuple[float, ...]
    metadata: dict[str, Any]


@dataclass(slots=True)
class VectorIndex:
    index_id: str
    dimension: int
    records: dict[str, VectorRecord]


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise RetrievalError(
            error_code="E_INVALID_ARGUMENT",
            message=f"non-numeric value: {value!r}",
        ) from None
    if not math.isfinite(out):
        raise RetrievalError(
            error_code="E_INVALID_ARGUMENT",
            message="non-finite float values are not allowed",
        )
    return out


def _normalize_embedding(raw: Any, *, dimension: int | None = None) -> tuple[float, ...]:
    if not isinstance(raw, list) or not raw:
        raise RetrievalError(
            error_code="E_INVALID_ARGUMENT",
            message="embedding must be a non-empty array",
        )
    values = tuple(_safe_float(value) for value in raw)
    if dimension is not None and len(values) != dimension:
        raise RetrievalError(
            error_code="E_DIMENSION_MISMATCH",
            message=(
                f"embedding dimension {len(values)} does not match "
                f"index dimension {dimension}"
            ),
        )
    return values


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    numerator = sum(left * right for left, right in zip(a, b))
    a_norm = math.sqrt(sum(val * val for val in a))
    b_norm = math.sqrt(sum(val * val for val in b))
    if a_norm == 0.0 or b_norm == 0.0:
        return 0.0
    return numerator / (a_norm * b_norm)


def _tokenize(text: str) -> set[str]:
    parts = re.split(r"[^a-z0-9_]+", text.lower())
    return {part for part in parts if part}


def _lexical_score(query_text: str, document_text: str) -> float:
    query_tokens = _tokenize(query_text)
    doc_tokens = _tokenize(document_text)
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = query_tokens.intersection(doc_tokens)
    return len(overlap) / float(len(query_tokens.union(doc_tokens)))


def _match_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if metadata.get(key) != expected:
            return False
    return True


class InMemoryRetrievalStore:
    def __init__(self) -> None:
        self._indexes: dict[str, VectorIndex] = {}

    def _require_index(self, index_id: str) -> VectorIndex:
        if index_id not in self._indexes:
            raise RetrievalError(
                error_code="E_INDEX_NOT_FOUND",
                message=f"vector index not found: {index_id}",
            )
        return self._indexes[index_id]

    def add_embeddings(
        self,
        *,
        index_id: str,
        dimension: int,
        records: list[dict[str, Any]],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        if not records:
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="records must be non-empty",
            )
        if dimension < 1:
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="dimension must be >= 1",
            )

        index = self._indexes.get(index_id)
        if index is None:
            index = VectorIndex(index_id=index_id, dimension=dimension, records={})
            self._indexes[index_id] = index
        elif index.dimension != dimension:
            raise RetrievalError(
                error_code="E_DIMENSION_MISMATCH",
                message=(
                    f"index {index_id} dimension {index.dimension} does not match "
                    f"request dimension {dimension}"
                ),
            )

        accepted = 0
        rejected = 0
        tenant_id = security["tenant_id"]
        for item in records:
            if not isinstance(item, dict):
                rejected += 1
                continue
            vector_id = str(item.get("vector_id", "")).strip()
            if not vector_id:
                rejected += 1
                continue
            embedding = _normalize_embedding(item.get("embedding"), dimension=index.dimension)
            metadata_raw = item.get("metadata", {})
            metadata = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
            record_tenant = str(metadata.get("tenant_id", tenant_id)).strip() or tenant_id
            if record_tenant != tenant_id:
                raise RetrievalError(
                    error_code="E_POLICY_DENY",
                    message="cross-tenant embedding insert denied",
                    policy_rule_id="RLS-TENANT-INSERT-001",
                )
            metadata["tenant_id"] = tenant_id
            index.records[vector_id] = VectorRecord(
                vector_id=vector_id,
                embedding=embedding,
                metadata=metadata,
            )
            accepted += 1

        ingest_id = deterministic_id(
            "ing",
            {
                "index_id": index_id,
                "tenant_id": tenant_id,
                "accepted": accepted,
                "dimension": dimension,
            },
        )
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "add_embeddings",
                "index_id": index_id,
                "tenant_id": tenant_id,
                "ingest_id": ingest_id,
            },
        )
        return {
            "index_id": index_id,
            "accepted": accepted,
            "rejected": rejected,
            "ingest_id": ingest_id,
            "trace_id": trace_id,
        }

    def delete_embeddings(
        self,
        *,
        index_id: str,
        vector_ids: list[str],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        if not isinstance(vector_ids, list):
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="vector_ids must be an array",
            )

        index = self._require_index(index_id)
        tenant_id = security["tenant_id"]
        deleted = 0
        not_found = 0
        for raw_id in vector_ids:
            vector_id = str(raw_id)
            record = index.records.get(vector_id)
            if record is None:
                not_found += 1
                continue
            if str(record.metadata.get("tenant_id", "")) != tenant_id:
                raise RetrievalError(
                    error_code="E_POLICY_DENY",
                    message="cross-tenant embedding delete denied",
                    policy_rule_id="RLS-TENANT-DELETE-001",
                )
            del index.records[vector_id]
            deleted += 1

        trace_id = deterministic_id(
            "tr",
            {
                "operation": "delete_embeddings",
                "index_id": index_id,
                "tenant_id": tenant_id,
                "deleted": deleted,
                "not_found": not_found,
            },
        )
        return {
            "index_id": index_id,
            "deleted": deleted,
            "not_found": not_found,
            "trace_id": trace_id,
        }

    def vector_search(
        self,
        *,
        index_id: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None,
        include_vectors: bool,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        index = self._require_index(index_id)
        embedding = _normalize_embedding(query_embedding, dimension=index.dimension)
        if top_k < 1 or top_k > 200:
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="top_k must be in range 1..200",
            )
        filter_map = dict(filters) if isinstance(filters, dict) else {}
        tenant_id = security["tenant_id"]

        rows: list[dict[str, Any]] = []
        for record in index.records.values():
            if str(record.metadata.get("tenant_id", "")) != tenant_id:
                continue
            if not _match_filters(record.metadata, filter_map):
                continue
            score = _cosine_similarity(embedding, record.embedding)
            row: dict[str, Any] = {
                "vector_id": record.vector_id,
                "score": round(score, 6),
                "metadata": dict(record.metadata),
            }
            if include_vectors:
                row["embedding"] = [round(value, 6) for value in record.embedding]
            rows.append(row)

        rows.sort(key=lambda row: (-float(row["score"]), str(row["vector_id"])))
        rows = rows[:top_k]
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "vector_search",
                "index_id": index_id,
                "tenant_id": tenant_id,
                "top_k": top_k,
                "filters": filter_map,
                "result_ids": [row["vector_id"] for row in rows],
            },
        )
        return {
            "index_id": index_id,
            "results": rows,
            "trace_id": trace_id,
            "rls_applied": True,
        }

    def hybrid_search(
        self,
        *,
        dialect: str,
        query_text: str,
        query_embedding: list[float],
        vector_index_id: str,
        sql_filter: dict[str, Any] | None,
        weights: dict[str, Any] | None,
        top_k: int,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        if dialect != "native":
            raise RetrievalError(
                error_code="E_DIALECT_UNAVAILABLE",
                message=f"unsupported dialect: {dialect}",
            )

        weight_map = {
            "vector": 0.6,
            "lexical": 0.3,
            "structured": 0.1,
        }
        if isinstance(weights, dict):
            for key in list(weight_map):
                if key in weights:
                    weight_map[key] = _safe_float(weights[key])
        if any(value < 0.0 or value > 1.0 for value in weight_map.values()):
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="weights must be in [0.0, 1.0]",
            )
        total = weight_map["vector"] + weight_map["lexical"] + weight_map["structured"]
        if abs(total - 1.0) > 1e-6:
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="weights must sum to 1.0",
            )

        structured_filters: dict[str, Any] = {}
        if isinstance(sql_filter, dict):
            if "metadata" in sql_filter and isinstance(sql_filter["metadata"], dict):
                structured_filters = dict(sql_filter["metadata"])
            elif str(sql_filter.get("where", "")).strip():
                raise RetrievalError(
                    error_code="E_FILTER_PUSHDOWN_UNAVAILABLE",
                    message=(
                        "where-based structured pushdown requires live engine planner; "
                        "offline mode only supports sql_filter.metadata"
                    ),
                )

        vector_result = self.vector_search(
            index_id=vector_index_id,
            query_embedding=query_embedding,
            top_k=max(top_k * 4, top_k),
            filters=structured_filters or None,
            include_vectors=False,
            security_context=security_context,
        )
        by_vector_id = {
            str(row["vector_id"]): row for row in vector_result["results"]
        }
        hybrid_rows: list[dict[str, Any]] = []
        for vector_id, row in by_vector_id.items():
            metadata = dict(row.get("metadata", {}))
            document_id = str(metadata.get("document_id", vector_id))
            lexical = _lexical_score(query_text, str(metadata.get("text", document_id)))
            structured = 1.0 if _match_filters(metadata, structured_filters) else 0.0
            vector_score = _safe_float(row.get("score", 0.0))
            final = (
                weight_map["vector"] * vector_score
                + weight_map["lexical"] * lexical
                + weight_map["structured"] * structured
            )
            hybrid_rows.append(
                {
                    "document_id": document_id,
                    "vector_id": vector_id,
                    "scores": {
                        "vector": round(vector_score, 6),
                        "lexical": round(lexical, 6),
                        "structured": round(structured, 6),
                        "final": round(final, 6),
                    },
                    "metadata": metadata,
                }
            )

        hybrid_rows.sort(
            key=lambda row: (
                -float(row["scores"]["final"]),
                str(row["document_id"]),
            )
        )
        hybrid_rows = hybrid_rows[:top_k]
        plan_ref = deterministic_id(
            "plan",
            {
                "dialect": dialect,
                "index_id": vector_index_id,
                "query_text": query_text,
                "weights": weight_map,
                "sql_filter": structured_filters,
            },
        )
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "hybrid_search",
                "plan_ref": plan_ref,
                "result_ids": [row["document_id"] for row in hybrid_rows],
            },
        )
        return {
            "results": hybrid_rows,
            "trace_id": trace_id,
            "rls_applied": True,
            "query_plan_ref": plan_ref,
        }
