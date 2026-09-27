"""Точка входа для запуска графа `generate` из CLI."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from gen.context.persona_context import PersonaContext
from gen.core.config import load_settings
from gen.core.models_config import load_models_config, resolve_model
from gen.graph.generate.graph import build_generate_graph
from gen.graph.generate.nodes import NodeDeps
from gen.graph.generate.state import GenerateState
from gen.providers.face_embedding.insightface import InsightFaceEmbeddingProvider
from gen.providers.image.routerai import RouterAIImageProvider
from gen.providers.video.routerai import RouterAIVideoProvider
from gen.qc.compliance import NotImplementedComplianceProvider

DEFAULT_PERSONA_DIR = Path("persona")
DEFAULT_OUTPUT_ROOT = Path("output")


async def _run_generate_async(
    *,
    scene_brief: str,
    format_: str,
    n: int,
    retries: int,
    quality: bool,
    aspect: str,
    persona_dir: Path,
    output_root: Path,
) -> GenerateState:
    if n != 1:
        raise NotImplementedError("--n > 1 (веер кандидатов) не входит в дефолтный режим M3")

    persona_ctx = PersonaContext.load(persona_dir)
    settings = load_settings()
    models_config = load_models_config()
    tier = "quality" if quality else "default"

    deps = NodeDeps(
        image_provider=RouterAIImageProvider(
            api_key=settings.routerai_api_key,
            base_url=settings.routerai_base_url,
            model=resolve_model(models_config, "photo", tier=tier),
        ),
        video_provider=RouterAIVideoProvider(
            api_key=settings.routerai_api_key,
            base_url=settings.routerai_base_url,
            model=resolve_model(models_config, "video", tier=tier),
        ),
        face_embedding_provider=InsightFaceEmbeddingProvider(),
        compliance_provider=NotImplementedComplianceProvider(),
        output_root=output_root,
    )

    graph = build_generate_graph(deps, max_retries=retries)
    initial_state: GenerateState = {
        "scene_brief": scene_brief,
        "format": format_,
        "persona_ctx": persona_ctx,
        "max_retries": retries,
        "aspect": aspect,
    }
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return await graph.ainvoke(initial_state, config=config)


def run_generate(
    *,
    scene_brief: str,
    format_: str = "photo",
    n: int = 1,
    retries: int = 1,
    quality: bool = False,
    aspect: str = "4:5",
    persona_dir: Path = DEFAULT_PERSONA_DIR,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> GenerateState:
    return asyncio.run(
        _run_generate_async(
            scene_brief=scene_brief,
            format_=format_,
            n=n,
            retries=retries,
            quality=quality,
            aspect=aspect,
            persona_dir=persona_dir,
            output_root=output_root,
        )
    )
