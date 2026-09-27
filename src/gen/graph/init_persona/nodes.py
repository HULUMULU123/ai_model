"""Узлы графа `init_persona`.

Каждый узел — чистая функция от `InitPersonaState` к частичному апдейту
состояния, с провайдерами и путями, зафиксированными через `NodeDeps`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from gen.context.persona_context import PersonaBible
from gen.graph.init_persona.state import InitPersonaState
from gen.providers.base import FaceEmbeddingProvider, ImageProvider, LLMProvider

PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"

# См. gen.graph.generate.nodes.QC_SIMILARITY_THRESHOLD — то же калибровочное
# обоснование (InsightFace buffalo_l, реальные генерации RouterAI 27.09.2026).
QC_SIMILARITY_THRESHOLD = 0.75


@dataclass
class NodeDeps:
    llm: LLMProvider
    image_provider: ImageProvider
    face_embedding_provider: FaceEmbeddingProvider
    persona_dir: Path
    prompts_dir: Path = PROMPTS_DIR


def write_character(state: InitPersonaState, deps: NodeDeps) -> dict:
    template = (deps.prompts_dir / "init_character.md").read_text(encoding="utf-8")
    prompt = template.format(name=state["name"], brief=state.get("brief", ""))
    bible = deps.llm.generate_structured(prompt, PersonaBible)
    return {"bible": bible, "wardrobe": bible.wardrobe}


def save_bible_files(state: InitPersonaState, deps: NodeDeps) -> dict:
    bible: PersonaBible = state["bible"]
    deps.persona_dir.mkdir(parents=True, exist_ok=True)

    bible_md = _render_bible_md(bible)
    (deps.persona_dir / "bible.md").write_text(bible_md, encoding="utf-8")

    persona_yaml = {
        "name": bible.name,
        "default_format": "photo",
        "default_aspect": "4:5",
    }
    (deps.persona_dir / "persona.yaml").write_text(
        yaml.safe_dump(persona_yaml, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    (deps.persona_dir / "wardrobe.yaml").write_text(
        yaml.safe_dump(bible.wardrobe, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {}


def _render_bible_md(bible: PersonaBible) -> str:
    lines = [
        f"# {bible.name}",
        "",
        "## Внешность",
        bible.appearance,
        "",
        "## Сигнатурные детали",
        *[f"- {d}" for d in bible.signature_details],
        "",
        "## Характер",
        bible.personality,
        "",
        "## Биография",
        bible.backstory,
        "",
        "## Голос",
        bible.voice,
        "",
        "## Палитра",
        ", ".join(bible.palette),
        "",
        "## Чего не делать",
        *[f"- {d}" for d in bible.forbidden],
        "",
    ]
    return "\n".join(lines)


def build_reference_prompt(state: InitPersonaState, deps: NodeDeps) -> dict:
    bible: PersonaBible = state["bible"]
    signature_details = "; ".join(bible.signature_details)
    forbidden = ", ".join(bible.forbidden)
    palette = ", ".join(bible.palette)
    wardrobe_items = "; ".join(
        f"{situation}: {', '.join(items)}" for situation, items in bible.wardrobe.items()
    )

    portrait_template = (deps.prompts_dir / "canon_portrait_sheet.md").read_text(encoding="utf-8")
    portrait_prompt = portrait_template.format(
        name=bible.name,
        appearance=bible.appearance,
        signature_details=signature_details,
        forbidden=forbidden,
    )

    wardrobe_template = (deps.prompts_dir / "canon_wardrobe_sheet.md").read_text(encoding="utf-8")
    wardrobe_prompt = wardrobe_template.format(
        name=bible.name,
        appearance=bible.appearance,
        signature_details=signature_details,
        wardrobe_items=wardrobe_items,
        palette=palette,
        forbidden=forbidden,
    )

    return {"portrait_prompt": portrait_prompt, "wardrobe_prompt": wardrobe_prompt}


def generate_canon_batch(state: InitPersonaState, deps: NodeDeps) -> dict:
    variants = state.get("variants", 1)

    portrait_sheets = deps.image_provider.generate(state["portrait_prompt"], n=variants)
    wardrobe_sheets = deps.image_provider.generate(state["wardrobe_prompt"], n=variants)

    return {"portrait_sheets": portrait_sheets, "wardrobe_sheets": wardrobe_sheets}


def qc_embedding(state: InitPersonaState, deps: NodeDeps) -> dict:
    images = [state["portrait_sheets"][0], state["wardrobe_sheets"][0]]
    embeddings = [deps.face_embedding_provider.embed(p) for p in images]

    qc_warning = None
    if len(embeddings) >= 2:
        score = deps.face_embedding_provider.similarity(embeddings[0], embeddings[1])
        if score < QC_SIMILARITY_THRESHOLD:
            qc_warning = (
                f"Сходство между портретом и гардеробным листом низкое ({score:.2f}). "
                "Рекомендуется перегенерировать `init-persona` вручную."
            )

    return {"canon_images": images, "qc_warning": qc_warning}


def save_canon(state: InitPersonaState, deps: NodeDeps) -> dict:
    canon_dir = deps.persona_dir / "canon"
    canon_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, src in enumerate(state["canon_images"]):
        dst = canon_dir / f"canon-{i:02d}{src.suffix}"
        dst.write_bytes(src.read_bytes())
        saved.append(dst)

    return {"canon_images": saved}
