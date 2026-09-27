"""Состояние графа `init_persona`."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from gen.context.persona_context import PersonaBible


class InitPersonaState(TypedDict, total=False):
    brief: str
    name: str
    persona_dir: Path
    variants: int
    full_reference_set: bool

    bible: PersonaBible
    wardrobe: dict

    portrait_prompt: str
    wardrobe_prompt: str

    portrait_sheets: list[Path]
    wardrobe_sheets: list[Path]

    canon_images: list[Path]
    qc_warning: str | None
