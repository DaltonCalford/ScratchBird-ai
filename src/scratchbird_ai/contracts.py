"""Typed contracts for ScratchBird AI query orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

QueryMode = Literal[
    "read_only",
    "mutation_with_approval",
    "ai_analysis",
    "ai_mutation_pending_approval",
    "ai_mutation_approved",
]


@dataclass(slots=True)
class QueryRequest:
    request_id: str
    user_id: str
    tenant_id: str
    dialect: str
    prompt_or_query: str
    mode: QueryMode = "read_only"
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CompileResult:
    compile_artifact_id: str
    dialect: str
    statement_kind: Literal["read", "mutation", "unknown"]
    sblr_hash: str
    diagnostics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecuteResult:
    execution_artifact_id: str
    compile_artifact_id: str
    rows: list[dict[str, Any]]
    row_count: int
    notices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QueryResponse:
    request_id: str
    compile_artifact_id: str
    execution_artifact_id: str
    result_rows: list[dict[str, Any]]
    row_count: int
    notices: list[str]
    trace_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
