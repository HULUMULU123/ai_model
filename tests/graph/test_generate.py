import asyncio
import uuid
from pathlib import Path

import pytest

from gen.context.persona_context import PersonaContext
from gen.core.errors import ContentGenError
from gen.graph.generate import nodes as generate_nodes
from gen.graph.generate.graph import build_generate_graph
from gen.graph.generate.nodes import NodeDeps, build_prompt
from gen.graph.generate.state import GenerateState
from gen.providers.face_embedding.mock import MockFaceEmbeddingProvider
from gen.providers.image.mock import MockImageProvider
from gen.providers.video.mock import MockVideoProvider
from gen.qc.compliance_mock import MockComplianceProvider

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


def _deps(tmp_path, scores, *, compliance_passed=True, compliance_reason=None):
    return NodeDeps(
        image_provider=MockImageProvider(tmp_path / "generated"),
        face_embedding_provider=ScriptedFaceEmbeddingProvider(scores),
        compliance_provider=MockComplianceProvider(
            passed=compliance_passed, reason=compliance_reason
        ),
        output_root=tmp_path / "output",
    )


def _run(deps, persona_ctx, max_retries=1, aspect="4:5", format_="photo"):
    graph = build_generate_graph(deps, max_retries=max_retries)
    initial_state: GenerateState = {
        "scene_brief": "сцена в кафе, повседневный образ",
        "format": format_,
        "persona_ctx": persona_ctx,
        "max_retries": max_retries,
        "aspect": aspect,
    }
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return asyncio.run(graph.ainvoke(initial_state, config=config))


def test_generate_accepts_on_first_try_without_retry(tmp_path, persona_ctx):
    deps = _deps(tmp_path, [0.9])

    result = _run(deps, persona_ctx)

    assert deps.image_provider.call_count == 1
    assert result["low_confidence"] is False
    assert result["compliance_passed"] is True
    assert result["delivered_path"].is_file()


def test_generate_retries_exactly_once_by_default(tmp_path, persona_ctx):
    deps = _deps(tmp_path, [0.1, 0.9])

    result = _run(deps, persona_ctx)

    assert deps.image_provider.call_count == 2
    assert result["low_confidence"] is False


def test_generate_escalates_to_low_confidence_after_retry_limit(tmp_path, persona_ctx):
    deps = _deps(tmp_path, [0.1, 0.2])

    result = _run(deps, persona_ctx)

    assert deps.image_provider.call_count == 2
    assert result["low_confidence"] is True
    assert result["delivered_path"].is_file()


def test_generate_delivers_upscaled_and_cropped_image(tmp_path, persona_ctx):
    from PIL import Image

    deps = _deps(tmp_path, [0.9])

    result = _run(deps, persona_ctx, aspect="1:1")

    with Image.open(result["delivered_path"]) as img:
        assert img.width == img.height
        # Апскейл поднимает исходный мок (64x96) до >= 2048 по длинной стороне
        # до кропа; после кропа в 1:1 остаётся min(upscaled_w, upscaled_h).
        assert max(img.size) > 96


def test_generate_rejected_by_compliance_is_not_delivered(tmp_path, persona_ctx):
    deps = _deps(tmp_path, [0.9], compliance_passed=False, compliance_reason="nudity detected")

    result = _run(deps, persona_ctx)

    assert result["compliance_passed"] is False
    assert result["compliance_reason"] == "nudity detected"
    assert "delivered_path" not in result
    assert deps.image_provider.call_count == 1


def test_generate_video_uses_video_provider_and_two_qc_frames(tmp_path, persona_ctx, monkeypatch):
    """Граф-уровень: ветвление по format=video, без реального ffmpeg.

    extract_frames/normalize_video тестируются на реальном ffmpeg отдельно в
    tests/unit/test_postprocess_video.py (skip, если ffmpeg не установлен).
    Здесь важна только связность графа и то, что QC берёт ровно 2 кадра, не
    вызывая сам видео-файл напрямую как изображение.
    """
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    frame_calls = []

    def fake_extract_frames(video_path, *, n=2):
        frame_calls.append(n)
        frames = []
        for i in range(n):
            frame = video_dir / f"frame-{i}.png"
            frame.write_bytes(b"fake-frame")
            frames.append(frame)
        return frames

    monkeypatch.setattr(generate_nodes, "extract_frames", fake_extract_frames)
    monkeypatch.setattr(generate_nodes, "normalize_video", lambda path: path)

    image_provider = MockImageProvider(tmp_path / "first_frame")
    video_provider = MockVideoProvider(video_dir)
    deps = NodeDeps(
        image_provider=image_provider,
        video_provider=video_provider,
        face_embedding_provider=ScriptedFaceEmbeddingProvider([0.9, 0.9]),
        compliance_provider=MockComplianceProvider(passed=True),
        output_root=tmp_path / "output",
    )

    result = _run(deps, persona_ctx, format_="video")

    # Сначала генерируется фото сцены (первый кадр), потом видео из него.
    assert image_provider.call_count == 1
    assert video_provider.call_count == 1
    assert frame_calls == [2, 1]  # qc_one (n=2), compliance_check (n=1)
    assert result["compliance_passed"] is True
    assert result["delivered_path"].is_file()


def test_build_prompt_requires_persona_context():
    deps = NodeDeps(image_provider=None, face_embedding_provider=None, compliance_provider=None)

    with pytest.raises(ContentGenError):
        build_prompt({"scene_brief": "сцена"}, deps)


def test_build_prompt_contains_bible_and_wardrobe(persona_ctx):
    deps = NodeDeps(image_provider=None, face_embedding_provider=None, compliance_provider=None)

    result = build_prompt(
        {"scene_brief": "сцена в кафе", "persona_ctx": persona_ctx},
        deps,
    )

    assert "Mila Novak" in result["prompt"]
    assert "freckles" in result["prompt"]
    assert "серая толстовка" in result["prompt"]
    assert "сцена в кафе" in result["prompt"]
    # Промпт для генерации изображения не должен тащить всю биографию/голос —
    # только визуально релевантные разделы bible.md.
    assert "Short phrases" not in result["prompt"]
    assert "Grew up in Split" not in result["prompt"]
