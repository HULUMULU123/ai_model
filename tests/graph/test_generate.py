import uuid
from pathlib import Path

import pytest

from gen.context.persona_context import PersonaContext
from gen.core.errors import ContentGenError
from gen.graph.generate.graph import build_generate_graph
from gen.graph.generate.nodes import NodeDeps, build_prompt
from gen.graph.generate.state import GenerateState
from gen.providers.face_embedding.mock import MockFaceEmbeddingProvider
from gen.providers.image.mock import MockImageProvider

FIXTURE_PERSONA_DIR = Path(__file__).parent.parent / "fixtures" / "persona"


class ScriptedFaceEmbeddingProvider(MockFaceEmbeddingProvider):
    """Мок, отдающий заранее заданную последовательность сходств."""

    def __init__(self, scores: list[float]) -> None:
        super().__init__()
        self._scores = list(scores)

    def similarity(self, a, b) -> float:
        super().similarity(a, b)
        return self._scores.pop(0)


@pytest.fixture
def persona_ctx():
    return PersonaContext.load(FIXTURE_PERSONA_DIR)


def _run(deps, persona_ctx, max_retries=1):
    graph = build_generate_graph(deps, max_retries=max_retries)
    initial_state: GenerateState = {
        "scene_brief": "сцена в кафе, повседневный образ",
        "format": "photo",
        "persona_ctx": persona_ctx,
        "max_retries": max_retries,
    }
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return graph.invoke(initial_state, config=config)


def test_generate_accepts_on_first_try_without_retry(tmp_path, persona_ctx):
    image_provider = MockImageProvider(tmp_path)
    deps = NodeDeps(
        image_provider=image_provider,
        face_embedding_provider=ScriptedFaceEmbeddingProvider([0.9]),
    )

    result = _run(deps, persona_ctx)

    assert image_provider.call_count == 1
    assert result["low_confidence"] is False
    assert result["best_candidate"].is_file()


def test_generate_retries_exactly_once_by_default(tmp_path, persona_ctx):
    image_provider = MockImageProvider(tmp_path)
    deps = NodeDeps(
        image_provider=image_provider,
        face_embedding_provider=ScriptedFaceEmbeddingProvider([0.1, 0.9]),
    )

    result = _run(deps, persona_ctx)

    assert image_provider.call_count == 2
    assert result["low_confidence"] is False


def test_generate_escalates_to_low_confidence_after_retry_limit(tmp_path, persona_ctx):
    image_provider = MockImageProvider(tmp_path)
    deps = NodeDeps(
        image_provider=image_provider,
        face_embedding_provider=ScriptedFaceEmbeddingProvider([0.1, 0.2]),
    )

    result = _run(deps, persona_ctx)

    assert image_provider.call_count == 2
    assert result["low_confidence"] is True
    assert result["best_candidate"].is_file()


def test_build_prompt_requires_persona_context():
    deps = NodeDeps(image_provider=None, face_embedding_provider=None)

    with pytest.raises(ContentGenError):
        build_prompt({"scene_brief": "сцена"}, deps)


def test_build_prompt_contains_bible_and_wardrobe(persona_ctx):
    deps = NodeDeps(image_provider=None, face_embedding_provider=None)

    result = build_prompt(
        {"scene_brief": "сцена в кафе", "persona_ctx": persona_ctx},
        deps,
    )

    assert "Mila Novak" in result["prompt"]
    assert "серая толстовка" in result["prompt"]
    assert "сцена в кафе" in result["prompt"]
