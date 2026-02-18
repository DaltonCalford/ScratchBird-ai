"""Capability matrix loader utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_matrix_path() -> Path:
    """Return the default capability matrix JSON path in this repository."""
    return (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "specifications"
        / "drafts"
        / "capability-matrix"
        / "capability-matrix.v0.json"
    )


def load_capability_matrix(path: str | Path | None = None) -> dict[str, Any]:
    matrix_path = Path(path) if path is not None else default_matrix_path()
    data = json.loads(matrix_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "dialects" not in data:
        raise ValueError("Invalid capability matrix payload")
    return data


def list_dialects(matrix: dict[str, Any]) -> list[str]:
    dialects = matrix.get("dialects", {})
    if not isinstance(dialects, dict):
        raise ValueError("capability matrix dialects must be an object")
    return sorted(dialects.keys())


def get_dialect_capabilities(matrix: dict[str, Any], dialect: str) -> dict[str, Any]:
    dialects = matrix.get("dialects", {})
    if dialect not in dialects:
        raise KeyError(f"Unknown dialect: {dialect}")
    caps = dialects[dialect]
    if not isinstance(caps, dict):
        raise ValueError(f"Invalid capability payload for dialect: {dialect}")
    return caps
