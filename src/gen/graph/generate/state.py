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

    prompt: str
    attempts: int
    candidate: Path
    qc_score: float
    best_candidate: Path
    best_score: float
    low_confidence: bool
