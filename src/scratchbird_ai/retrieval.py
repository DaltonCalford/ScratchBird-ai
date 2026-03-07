"""Engine-free vector and hybrid retrieval scaffolding with deterministic output."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .deterministic import deterministic_id
from .tool_schema import require_security_context


RETRIEVAL_COMPATIBILITY_VERSION = "2026-03-07"
_VALID_INDEX_STATES = {
    "provisioning",
    "ready",
    "reindexing",
    "deleting",
    "deleted",
    "failed",
}
_SUPPORTED_RETRIEVAL_PROFILES = {
    "client_supplied_embeddings_v0",
    "provider_generated_embeddings_v0",
}


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "vector_id": self.vector_id,
            "embedding": list(self.embedding),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VectorRecord":
        metadata_raw = payload.get("metadata", {})
        metadata = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
        return cls(
            vector_id=str(payload.get("vector_id", "")),
            embedding=_normalize_embedding(payload.get("embedding")),
            metadata=metadata,
        )


@dataclass(slots=True)
class IndexDescriptor:
    index_id: str
    profile_id: str
    dimension: int
    distance_metric: str
    backend_kind: str
    state: str
    tenant_scope: str
    created_at_utc: str
    updated_at_utc: str
    owner_tenant_id: str
    compatibility_version: str = RETRIEVAL_COMPATIBILITY_VERSION
    record_count: int = 0
    last_ingest_profile_id: str | None = None
    provider_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index_id": self.index_id,
            "profile_id": self.profile_id,
            "dimension": self.dimension,
            "distance_metric": self.distance_metric,
            "backend_kind": self.backend_kind,
            "state": self.state,
            "tenant_scope": self.tenant_scope,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "compatibility_version": self.compatibility_version,
            "record_count": self.record_count,
        }
        if self.last_ingest_profile_id:
            payload["last_ingest_profile_id"] = self.last_ingest_profile_id
        if self.provider_ref:
            payload["provider_ref"] = self.provider_ref
        return payload

    def to_catalog_dict(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload["owner_tenant_id"] = self.owner_tenant_id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IndexDescriptor":
        return cls(
            index_id=str(payload.get("index_id", "")),
            profile_id=str(payload.get("profile_id", "client_supplied_embeddings_v0")),
            dimension=int(payload.get("dimension", 0)),
            distance_metric=str(payload.get("distance_metric", "cosine")),
            backend_kind=str(payload.get("backend_kind", "in_memory")),
            state=str(payload.get("state", "provisioning")),
            tenant_scope=str(payload.get("tenant_scope", "tenant_bound")),
            created_at_utc=str(payload.get("created_at_utc", "")),
            updated_at_utc=str(payload.get("updated_at_utc", "")),
            owner_tenant_id=str(payload.get("owner_tenant_id", "")),
            compatibility_version=str(
                payload.get("compatibility_version", RETRIEVAL_COMPATIBILITY_VERSION)
            ),
            record_count=int(payload.get("record_count", 0)),
            last_ingest_profile_id=(
                str(payload["last_ingest_profile_id"])
                if payload.get("last_ingest_profile_id") is not None
                else None
            ),
            provider_ref=(
                str(payload["provider_ref"]) if payload.get("provider_ref") is not None else None
            ),
        )


@dataclass(slots=True)
class VectorIndex:
    descriptor: IndexDescriptor
    records: dict[str, VectorRecord]

    @property
    def index_id(self) -> str:
        return self.descriptor.index_id

    @property
    def dimension(self) -> int:
        return self.descriptor.dimension


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _normalize_dimension(value: Any) -> int:
    try:
        dimension = int(value)
    except (TypeError, ValueError):
        raise RetrievalError(
            error_code="E_INVALID_ARGUMENT",
            message="dimension must be an integer",
        ) from None
    if dimension < 1:
        raise RetrievalError(
            error_code="E_INVALID_ARGUMENT",
            message="dimension must be >= 1",
        )
    return dimension


def _normalize_index_state(state: str) -> str:
    normalized = str(state).strip().lower()
    if normalized not in _VALID_INDEX_STATES:
        raise RetrievalError(
            error_code="E_INDEX_STATE_INVALID",
            message=f"unsupported index state: {state}",
        )
    return normalized


def _ensure_supported_profile(profile_id: str) -> str:
    normalized = str(profile_id).strip() or "client_supplied_embeddings_v0"
    if normalized not in _SUPPORTED_RETRIEVAL_PROFILES:
        raise RetrievalError(
            error_code="E_COMPATIBILITY_MISMATCH",
            message=f"unsupported retrieval profile: {profile_id}",
        )
    return normalized


def _generate_provider_embedding(
    *,
    text: str,
    dimension: int,
    provider_profile_id: str,
    model: str,
) -> tuple[float, ...]:
    values: list[float] = []
    counter = 0
    seed = f"{provider_profile_id}|{model}|{text}"
    while len(values) < dimension:
        digest = hashlib.sha256(f"{seed}|{counter}".encode("utf-8")).digest()
        counter += 1
        for offset in range(0, len(digest), 4):
            chunk = digest[offset : offset + 4]
            if len(chunk) < 4:
                continue
            raw = int.from_bytes(chunk, "big")
            values.append(round(((raw / 4_294_967_295.0) * 2.0) - 1.0, 6))
            if len(values) == dimension:
                break
    return tuple(values)


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
    def __init__(self, *, catalog_path: str | None = None) -> None:
        self._catalog_path = Path(catalog_path).expanduser() if catalog_path else None
        self._indexes: dict[str, VectorIndex] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        if self._catalog_path is None or not self._catalog_path.exists():
            return
        raw = self._catalog_path.read_text(encoding="utf-8").strip()
        if not raw:
            return
        payload = json.loads(raw)
        indexes_raw = payload.get("indexes", [])
        if not isinstance(indexes_raw, list):
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="retrieval catalog indexes must be an array",
            )
        for item in indexes_raw:
            if not isinstance(item, dict):
                continue
            descriptor = IndexDescriptor.from_dict(item.get("descriptor", {}))
            records_payload = item.get("records", [])
            records: dict[str, VectorRecord] = {}
            if isinstance(records_payload, list):
                for record_payload in records_payload:
                    if not isinstance(record_payload, dict):
                        continue
                    record = VectorRecord.from_dict(record_payload)
                    if record.vector_id:
                        records[record.vector_id] = record
            descriptor.record_count = len(records)
            self._indexes[descriptor.index_id] = VectorIndex(descriptor=descriptor, records=records)

    def _persist_catalog(self) -> None:
        if self._catalog_path is None:
            return
        payload = {
            "catalog_version": RETRIEVAL_COMPATIBILITY_VERSION,
            "indexes": [
                {
                    "descriptor": index.descriptor.to_catalog_dict(),
                    "records": [
                        record.to_dict()
                        for record in sorted(index.records.values(), key=lambda row: row.vector_id)
                    ],
                }
                for index in sorted(self._indexes.values(), key=lambda row: row.index_id)
            ],
        }
        self._catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self._catalog_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _require_index(
        self,
        index_id: str,
        *,
        tenant_id: str | None = None,
        allow_deleted: bool = False,
    ) -> VectorIndex:
        if index_id not in self._indexes:
            raise RetrievalError(
                error_code="E_INDEX_NOT_FOUND",
                message=f"vector index not found: {index_id}",
            )
        index = self._indexes[index_id]
        if tenant_id is not None and index.descriptor.owner_tenant_id != tenant_id:
            raise RetrievalError(
                error_code="E_POLICY_DENY",
                message="cross-tenant vector index access denied",
                policy_rule_id="RLS-TENANT-INDEX-001",
            )
        state = index.descriptor.state
        if state == "deleted" and not allow_deleted:
            raise RetrievalError(
                error_code="E_INDEX_NOT_FOUND",
                message=f"vector index not found: {index_id}",
            )
        if state == "deleting":
            raise RetrievalError(
                error_code="E_INDEX_STATE_INVALID",
                message=f"vector index {index_id} is being deleted",
            )
        return index

    def _build_descriptor(
        self,
        *,
        index_id: str,
        profile_id: str,
        dimension: int,
        tenant_id: str,
        state: str = "provisioning",
        provider_ref: str | None = None,
    ) -> IndexDescriptor:
        created_at = _utc_now()
        return IndexDescriptor(
            index_id=index_id,
            profile_id=profile_id,
            dimension=dimension,
            distance_metric="cosine",
            backend_kind="in_memory_json" if self._catalog_path else "in_memory",
            state=_normalize_index_state(state),
            tenant_scope="tenant_bound",
            created_at_utc=created_at,
            updated_at_utc=created_at,
            owner_tenant_id=tenant_id,
            record_count=0,
            last_ingest_profile_id=profile_id,
            provider_ref=provider_ref,
        )

    def _set_index_state(self, index: VectorIndex, state: str) -> None:
        index.descriptor.state = _normalize_index_state(state)
        index.descriptor.updated_at_utc = _utc_now()

    def _touch_descriptor(
        self,
        index: VectorIndex,
        *,
        state: str | None = None,
        last_ingest_profile_id: str | None = None,
        provider_ref: str | None = None,
    ) -> None:
        if state is not None:
            index.descriptor.state = _normalize_index_state(state)
        if last_ingest_profile_id is not None:
            index.descriptor.last_ingest_profile_id = last_ingest_profile_id
        if provider_ref is not None:
            index.descriptor.provider_ref = provider_ref
        index.descriptor.record_count = len(index.records)
        index.descriptor.updated_at_utc = _utc_now()

    def _ensure_index(
        self,
        *,
        index_id: str,
        dimension: int,
        tenant_id: str,
        profile_id: str,
        provider_ref: str | None = None,
    ) -> VectorIndex:
        normalized_profile = _ensure_supported_profile(profile_id)
        index = self._indexes.get(index_id)
        if index is None or index.descriptor.state == "deleted":
            descriptor = self._build_descriptor(
                index_id=index_id,
                profile_id=normalized_profile,
                dimension=dimension,
                tenant_id=tenant_id,
                provider_ref=provider_ref,
            )
            index = VectorIndex(descriptor=descriptor, records={})
            self._indexes[index_id] = index
            self._persist_catalog()
            return index
        if index.descriptor.owner_tenant_id != tenant_id:
            raise RetrievalError(
                error_code="E_POLICY_DENY",
                message="cross-tenant vector index access denied",
                policy_rule_id="RLS-TENANT-INDEX-001",
            )
        if index.dimension != dimension:
            raise RetrievalError(
                error_code="E_DIMENSION_MISMATCH",
                message=(
                    f"index {index_id} dimension {index.dimension} does not match "
                    f"request dimension {dimension}"
                ),
            )
        if index.descriptor.profile_id != normalized_profile:
            raise RetrievalError(
                error_code="E_COMPATIBILITY_MISMATCH",
                message=(
                    f"index {index_id} profile {index.descriptor.profile_id} does not match "
                    f"request profile {normalized_profile}"
                ),
            )
        if (
            provider_ref is not None
            and index.descriptor.provider_ref is not None
            and index.descriptor.provider_ref != provider_ref
        ):
            raise RetrievalError(
                error_code="E_COMPATIBILITY_MISMATCH",
                message=(
                    f"index {index_id} provider_ref {index.descriptor.provider_ref} does not match "
                    f"request provider_ref {provider_ref}"
                ),
            )
        if index.descriptor.state == "failed":
            raise RetrievalError(
                error_code="E_INDEX_STATE_INVALID",
                message=f"vector index {index_id} is in failed state",
            )
        return index

    def _resolve_provider_config(self, provider_config: dict[str, Any]) -> tuple[str, str, str]:
        provider_profile_id = str(
            provider_config.get("provider_profile_id")
            or provider_config.get("provider_id")
            or "embedding_provider"
        ).strip()
        model = str(provider_config.get("model") or "default").strip() or "default"
        env_var = str(provider_config.get("api_key_env_var", "")).strip()
        inline_secret = str(provider_config.get("api_key", "")).strip()
        if env_var:
            if not os.getenv(env_var, "").strip():
                raise RetrievalError(
                    error_code="E_PROVIDER_AUTH_MISSING",
                    message=f"provider credential env var is empty: {env_var}",
                )
            return provider_profile_id, model, f"env:{env_var}"
        if inline_secret:
            return provider_profile_id, model, "inline:redacted"
        raise RetrievalError(
            error_code="E_PROVIDER_AUTH_MISSING",
            message="provider_config must contain api_key_env_var or api_key",
        )

    def create_index(
        self,
        *,
        index_id: str,
        dimension: int,
        security_context: dict[str, Any],
        profile_id: str = "client_supplied_embeddings_v0",
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        normalized_dimension = _normalize_dimension(dimension)
        tenant_id = security["tenant_id"]
        if not str(index_id).strip():
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="index_id must be non-empty",
            )
        descriptor = self._build_descriptor(
            index_id=str(index_id),
            profile_id=_ensure_supported_profile(profile_id),
            dimension=normalized_dimension,
            tenant_id=tenant_id,
        )
        existing = self._indexes.get(descriptor.index_id)
        if existing is not None and existing.descriptor.state != "deleted":
            if existing.descriptor.owner_tenant_id != tenant_id:
                raise RetrievalError(
                    error_code="E_POLICY_DENY",
                    message="cross-tenant vector index access denied",
                    policy_rule_id="RLS-TENANT-INDEX-001",
                )
            raise RetrievalError(
                error_code="E_ALREADY_EXISTS",
                message=f"vector index already exists: {descriptor.index_id}",
            )
        self._indexes[descriptor.index_id] = VectorIndex(descriptor=descriptor, records={})
        self._persist_catalog()
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "create_index",
                "index_id": descriptor.index_id,
                "tenant_id": tenant_id,
                "profile_id": descriptor.profile_id,
            },
        )
        return {"index": descriptor.to_dict(), "trace_id": trace_id}

    def list_indexes(
        self,
        *,
        security_context: dict[str, Any],
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        tenant_id = security["tenant_id"]
        rows = [
            index.descriptor.to_dict()
            for index in sorted(self._indexes.values(), key=lambda item: item.index_id)
            if index.descriptor.owner_tenant_id == tenant_id
            and (include_deleted or index.descriptor.state != "deleted")
        ]
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "list_indexes",
                "tenant_id": tenant_id,
                "index_ids": [row["index_id"] for row in rows],
            },
        )
        return {"indexes": rows, "trace_id": trace_id}

    def describe_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        index = self._require_index(str(index_id), tenant_id=security["tenant_id"], allow_deleted=True)
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "describe_index",
                "index_id": index.index_id,
                "tenant_id": security["tenant_id"],
            },
        )
        return {"index": index.descriptor.to_dict(), "trace_id": trace_id}

    def reindex_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        index = self._require_index(str(index_id), tenant_id=security["tenant_id"])
        previous_state = index.descriptor.state
        self._set_index_state(index, "reindexing")
        self._persist_catalog()
        self._touch_descriptor(
            index,
            state="ready" if index.records else "provisioning",
            last_ingest_profile_id=index.descriptor.profile_id,
        )
        self._persist_catalog()
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "reindex_index",
                "index_id": index.index_id,
                "tenant_id": security["tenant_id"],
                "previous_state": previous_state,
            },
        )
        return {
            "index": index.descriptor.to_dict(),
            "previous_state": previous_state,
            "trace_id": trace_id,
        }

    def delete_index(
        self,
        *,
        index_id: str,
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        index = self._require_index(str(index_id), tenant_id=security["tenant_id"], allow_deleted=True)
        previous_state = index.descriptor.state
        self._set_index_state(index, "deleting")
        self._persist_catalog()
        index.records.clear()
        self._touch_descriptor(index, state="deleted")
        self._persist_catalog()
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "delete_index",
                "index_id": index.index_id,
                "tenant_id": security["tenant_id"],
                "previous_state": previous_state,
            },
        )
        return {
            "index": index.descriptor.to_dict(),
            "previous_state": previous_state,
            "trace_id": trace_id,
        }

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
        normalized_dimension = _normalize_dimension(dimension)
        accepted = 0
        rejected = 0
        tenant_id = security["tenant_id"]
        index = self._ensure_index(
            index_id=str(index_id),
            dimension=normalized_dimension,
            tenant_id=tenant_id,
            profile_id="client_supplied_embeddings_v0",
        )
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
        self._touch_descriptor(
            index,
            state="ready" if accepted else index.descriptor.state,
            last_ingest_profile_id="client_supplied_embeddings_v0",
        )
        self._persist_catalog()

        ingest_id = deterministic_id(
            "ing",
            {
                "index_id": index_id,
                "tenant_id": tenant_id,
                "accepted": accepted,
                "dimension": normalized_dimension,
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
            "profile_id": index.descriptor.profile_id,
            "index": index.descriptor.to_dict(),
        }

    def add_generated_embeddings(
        self,
        *,
        index_id: str,
        dimension: int,
        records: list[dict[str, Any]],
        provider_config: dict[str, Any],
        security_context: dict[str, Any],
    ) -> dict[str, Any]:
        security = require_security_context({"security_context": security_context})
        if not records:
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="records must be non-empty",
            )
        if not isinstance(provider_config, dict):
            raise RetrievalError(
                error_code="E_INVALID_ARGUMENT",
                message="provider_config must be an object",
            )
        normalized_dimension = _normalize_dimension(dimension)
        provider_profile_id, model, provider_ref = self._resolve_provider_config(provider_config)
        tenant_id = security["tenant_id"]
        index = self._ensure_index(
            index_id=str(index_id),
            dimension=normalized_dimension,
            tenant_id=tenant_id,
            profile_id="provider_generated_embeddings_v0",
            provider_ref=provider_ref,
        )

        accepted = 0
        rejected = 0
        for item in records:
            if not isinstance(item, dict):
                rejected += 1
                continue
            vector_id = str(item.get("vector_id", "")).strip()
            if not vector_id:
                rejected += 1
                continue
            metadata_raw = item.get("metadata", {})
            metadata = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
            text = str(item.get("text") or metadata.get("text", "")).strip()
            if not text:
                rejected += 1
                continue
            record_tenant = str(metadata.get("tenant_id", tenant_id)).strip() or tenant_id
            if record_tenant != tenant_id:
                raise RetrievalError(
                    error_code="E_POLICY_DENY",
                    message="cross-tenant embedding insert denied",
                    policy_rule_id="RLS-TENANT-INSERT-001",
                )
            metadata["tenant_id"] = tenant_id
            metadata.setdefault("text", text)
            index.records[vector_id] = VectorRecord(
                vector_id=vector_id,
                embedding=_generate_provider_embedding(
                    text=text,
                    dimension=index.dimension,
                    provider_profile_id=provider_profile_id,
                    model=model,
                ),
                metadata=metadata,
            )
            accepted += 1

        self._touch_descriptor(
            index,
            state="ready" if accepted else index.descriptor.state,
            last_ingest_profile_id="provider_generated_embeddings_v0",
            provider_ref=provider_ref,
        )
        self._persist_catalog()

        ingest_id = deterministic_id(
            "ing",
            {
                "index_id": index_id,
                "tenant_id": tenant_id,
                "accepted": accepted,
                "provider_profile_id": provider_profile_id,
                "model": model,
            },
        )
        trace_id = deterministic_id(
            "tr",
            {
                "operation": "add_generated_embeddings",
                "index_id": index_id,
                "tenant_id": tenant_id,
                "ingest_id": ingest_id,
                "provider_profile_id": provider_profile_id,
                "model": model,
            },
        )
        return {
            "index_id": str(index_id),
            "accepted": accepted,
            "rejected": rejected,
            "ingest_id": ingest_id,
            "trace_id": trace_id,
            "profile_id": index.descriptor.profile_id,
            "provider_profile_id": provider_profile_id,
            "provider_ref": provider_ref,
            "index": index.descriptor.to_dict(),
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

        index = self._require_index(index_id, tenant_id=security["tenant_id"])
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
        self._touch_descriptor(
            index,
            state="ready" if index.records else "provisioning",
            last_ingest_profile_id=index.descriptor.profile_id,
        )
        self._persist_catalog()

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
            "index": index.descriptor.to_dict(),
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
        index = self._require_index(index_id, tenant_id=security["tenant_id"])
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
            "index": index.descriptor.to_dict(),
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
