"""Узлы графа `generate` (фото и видео — один граф, ветвление по `state["format"]`).

`generate_one` — асинхронный узел (video использует async `VideoProvider` с
polling), поэтому граф целиком запускается через `.ainvoke()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen.context.persona_context import PersonaContext
from gen.core.errors import ContentGenError
from gen.delivery.local import deliver_to_output
from gen.graph.generate.state import GenerateState
from gen.postprocess.image import crop_to_aspect, upscale
from gen.postprocess.video import extract_frames, normalize_video
from gen.providers.base import FaceEmbeddingProvider, ImageProvider, VideoProvider
from gen.qc.compliance import ComplianceProvider

PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"

QC_SIMILARITY_THRESHOLD = 0.5
DEFAULT_ASPECT = "4:5"
VIDEO_QC_FRAMES = 2


class MissingPersonaContextError(ContentGenError):
    """build_prompt не может собрать промпт без PersonaContext (см. ТЗ, раздел 4)."""


@dataclass
class NodeDeps:
    image_provider: ImageProvider
    face_embedding_provider: FaceEmbeddingProvider
    compliance_provider: ComplianceProvider
    video_provider: VideoProvider | None = None
    prompts_dir: Path = PROMPTS_DIR
    output_root: Path = Path("output")


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


async def generate_one(state: GenerateState, deps: NodeDeps) -> dict:
    persona_ctx: PersonaContext = state["persona_ctx"]

    if state["format"] == "video":
        if deps.video_provider is None:
            raise ValueError("format=video требует NodeDeps.video_provider")
        candidate = await deps.video_provider.generate(
            state["prompt"],
            source_image=persona_ctx.canon_images[0],
            reference_images=persona_ctx.canon_images,
        )
    else:
        candidates = deps.image_provider.generate(
            state["prompt"],
            reference_images=persona_ctx.canon_images,
            n=1,
        )
        candidate = candidates[0]

    return {"candidate": candidate, "attempts": state.get("attempts", 0) + 1}


def _qc_reference_images(state: GenerateState, deps: NodeDeps) -> list[Path]:
    if state["format"] == "video":
        return extract_frames(state["candidate"], n=VIDEO_QC_FRAMES)
    return [state["candidate"]]


def qc_one(state: GenerateState, deps: NodeDeps) -> dict:
    persona_ctx: PersonaContext = state["persona_ctx"]
    reference_embedding = deps.face_embedding_provider.embed(persona_ctx.canon_images[0])

    candidate_images = _qc_reference_images(state, deps)
    scores = [
        deps.face_embedding_provider.similarity(
            deps.face_embedding_provider.embed(img), reference_embedding
        )
        for img in candidate_images
    ]
    score = min(scores)

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


def post_process(state: GenerateState) -> dict:
    candidate = state["best_candidate"]
    if state["format"] == "video":
        normalize_video(candidate)
    else:
        aspect = state.get("aspect") or DEFAULT_ASPECT
        upscale(candidate)
        crop_to_aspect(candidate, aspect)
    return {}


def compliance_check(state: GenerateState, deps: NodeDeps) -> dict:
    if state["format"] == "video":
        check_target = extract_frames(state["best_candidate"], n=1)[0]
    else:
        check_target = state["best_candidate"]
    result = deps.compliance_provider.check(check_target)
    return {"compliance_passed": result.passed, "compliance_reason": result.reason}


def should_deliver(state: GenerateState) -> str:
    return "deliver" if state["compliance_passed"] else "reject"


def reject(state: GenerateState) -> dict:
    return {}


def deliver(state: GenerateState, deps: NodeDeps) -> dict:
    dest = deliver_to_output(
        state["best_candidate"],
        prompt=state["prompt"],
        qc_score=state["best_score"],
        low_confidence=state["low_confidence"],
        output_root=deps.output_root,
    )
    return {"delivered_path": dest}
