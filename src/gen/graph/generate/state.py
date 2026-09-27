"""Состояние графа `generate`."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict

from gen.context.persona_context import PersonaContext


class GenerateState(TypedDict, total=False):
    scene_brief: str
    format: Literal["photo", "video"]
    persona_ctx: PersonaContext
    max_retries: int

    aspect: str

    prompt: str
    attempts: int
    candidate: Path
    qc_score: float
    best_candidate: Path
    best_score: float
    low_confidence: bool

    compliance_passed: bool
    compliance_reason: str | None
    delivered_path: Path
