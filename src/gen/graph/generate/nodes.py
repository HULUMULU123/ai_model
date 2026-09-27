"""Узлы графа `generate` (фото; видео переиспользует те же узлы на M5)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen.context.persona_context import PersonaContext
from gen.core.errors import ContentGenError
from gen.graph.generate.state import GenerateState
from gen.providers.base import FaceEmbeddingProvider, ImageProvider

PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"

QC_SIMILARITY_THRESHOLD = 0.5


class MissingPersonaContextError(ContentGenError):
    """build_prompt не может собрать промпт без PersonaContext (см. ТЗ, раздел 4)."""


@dataclass
class NodeDeps:
    image_provider: ImageProvider
    face_embedding_provider: FaceEmbeddingProvider
    prompts_dir: Path = PROMPTS_DIR


def build_prompt(state: GenerateState, deps: NodeDeps) -> dict:
    persona_ctx = state.get("persona_ctx")
    if persona_ctx is None or not isinstance(persona_ctx, PersonaContext):
        raise MissingPersonaContextError(
            "build_prompt требует PersonaContext — сначала запусти `uv run init-persona`."
        )

    template = (deps.prompts_dir / "generate_photo.md").read_text(encoding="utf-8")
    wardrobe_text = "; ".join(
        f"{situation}: {', '.join(items)}" for situation, items in persona_ctx.wardrobe.items()
    )
    prompt = template.format(
        bible_text=persona_ctx.bible_text,
        wardrobe_text=wardrobe_text,
        scene_brief=state["scene_brief"],
    )
    return {"prompt": prompt, "attempts": 0}


def generate_one(state: GenerateState, deps: NodeDeps) -> dict:
    persona_ctx: PersonaContext = state["persona_ctx"]
    candidates = deps.image_provider.generate(
        state["prompt"],
        reference_images=persona_ctx.canon_images,
        n=1,
    )
    return {"candidate": candidates[0], "attempts": state.get("attempts", 0) + 1}


def qc_one(state: GenerateState, deps: NodeDeps) -> dict:
    persona_ctx: PersonaContext = state["persona_ctx"]
    candidate_embedding = deps.face_embedding_provider.embed(state["candidate"])
    reference_embedding = deps.face_embedding_provider.embed(persona_ctx.canon_images[0])
    score = deps.face_embedding_provider.similarity(candidate_embedding, reference_embedding)

    update: dict = {"qc_score": score}
    if score > state.get("best_score", -1.0):
        update["best_score"] = score
        update["best_candidate"] = state["candidate"]
    return update


def should_retry(state: GenerateState, max_retries: int) -> str:
    if state["qc_score"] >= QC_SIMILARITY_THRESHOLD:
        return "accept"
    if state["attempts"] <= max_retries:
        return "retry"
    return "escalate"


def finalize_low_confidence(state: GenerateState) -> dict:
    return {"low_confidence": True}


def finalize_accepted(state: GenerateState) -> dict:
    return {"low_confidence": False}
