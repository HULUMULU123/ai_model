"""Единый контекст персонажа: bible.md, persona.yaml, wardrobe.yaml, canon/.

Собирается один раз при старте и передаётся во все узлы графов. Ни один узел
сборки промпта не должен работать без него (см. ТЗ, раздел 4).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from gen.core.errors import ContentGenError


class PersonaContextError(ContentGenError):
    """Персонаж ещё не подготовлен (нет bible.md/persona.yaml/wardrobe.yaml)."""


class PersonaBible(BaseModel):
    """Схема результата write_character (заполняется на M2).

    Поля соответствуют разделам bible.md из ТЗ: внешность, сигнатурные детали,
    характер, биография-канон, голос в текстах, гардероб по ситуациям,
    палитра, "чего не делать".
    """

    name: str
    appearance: str
    signature_details: list[str] = Field(default_factory=list)
    personality: str
    backstory: str
    voice: str
    wardrobe: dict[str, list[str]] = Field(default_factory=dict)
    palette: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)


class PersonaContext(BaseModel):
    """Всё, что нужно узлам графа `generate` для консистентной генерации."""

    persona_dir: Path
    name: str
    bible_text: str
    persona_config: dict = Field(default_factory=dict)
    wardrobe: dict = Field(default_factory=dict)
    canon_images: list[Path] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def load(cls, persona_dir: Path | str) -> PersonaContext:
        persona_dir = Path(persona_dir)

        bible_path = persona_dir / "bible.md"
        persona_yaml_path = persona_dir / "persona.yaml"
        wardrobe_yaml_path = persona_dir / "wardrobe.yaml"
        canon_dir = persona_dir / "canon"

        missing = [
            p.name
            for p in (bible_path, persona_yaml_path, wardrobe_yaml_path)
            if not p.is_file()
        ]
        if missing or not canon_dir.is_dir():
            raise PersonaContextError(
                f"Персонаж не подготовлен в {persona_dir}: отсутствуют {missing or ['canon/']}. "
                "Сначала запусти `uv run init-persona`."
            )

        bible_text = bible_path.read_text(encoding="utf-8")
        persona_config = yaml.safe_load(persona_yaml_path.read_text(encoding="utf-8")) or {}
        wardrobe = yaml.safe_load(wardrobe_yaml_path.read_text(encoding="utf-8")) or {}
        canon_images = sorted(
            p for p in canon_dir.iterdir() if p.is_file() and not p.name.startswith(".")
        )
        if not canon_images:
            raise PersonaContextError(
                f"В {canon_dir} нет ни одного файла-референса. "
                "Сначала запусти `uv run init-persona`."
            )

        name = persona_config.get("name") or bible_path.stem

        return cls(
            persona_dir=persona_dir,
            name=name,
            bible_text=bible_text,
            persona_config=persona_config,
            wardrobe=wardrobe,
            canon_images=canon_images,
        )
