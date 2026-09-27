"""Точка входа для запуска графа `init_persona` из CLI."""

from __future__ import annotations

import uuid
from pathlib import Path

from gen.core.config import load_settings
from gen.core.models_config import load_models_config, resolve_model
from gen.graph.init_persona.graph import build_init_persona_graph
from gen.graph.init_persona.nodes import NodeDeps
from gen.graph.init_persona.state import InitPersonaState
from gen.providers.face_embedding.insightface import InsightFaceEmbeddingProvider
from gen.providers.image.routerai import RouterAIImageProvider
from gen.providers.llm.routerai import RouterAILLMProvider


def run_init_persona(
    *,
    brief: str,
    name: str,
    persona_dir: Path,
    variants: int = 1,
    full_reference_set: bool = False,
) -> InitPersonaState:
    if full_reference_set:
        raise NotImplementedError(
            "--full-reference-set пока не реализован (не входит в дефолтный режим M2)"
        )

    settings = load_settings()
    models_config = load_models_config()

    deps = NodeDeps(
        llm=RouterAILLMProvider(
            api_key=settings.routerai_api_key,
            base_url=settings.routerai_base_url,
            model=resolve_model(models_config, "write_character"),
        ),
        image_provider=RouterAIImageProvider(
            api_key=settings.routerai_api_key,
            base_url=settings.routerai_base_url,
            model=resolve_model(models_config, "photo"),
        ),
        face_embedding_provider=InsightFaceEmbeddingProvider(),
        persona_dir=persona_dir,
    )

    graph = build_init_persona_graph(deps)
    initial_state: InitPersonaState = {
        "brief": brief,
        "name": name,
        "persona_dir": persona_dir,
        "variants": variants,
        "full_reference_set": full_reference_set,
    }
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return graph.invoke(initial_state, config=config)
