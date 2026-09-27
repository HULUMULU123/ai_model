"""Тесты `astream_generate` — стриминг промежуточных шагов графа `generate`.

Нужно, чтобы Telegram-бот и CLI могли показывать промпт/попытку/QC/модерацию
по мере выполнения, а не только финальный результат (по прямому запросу).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import gen.graph.generate.run as run_module
from gen.context.persona_context import PersonaContext
from gen.graph.generate.nodes import NodeDeps
from gen.graph.generate.run import astream_generate
from gen.providers.face_embedding.mock import MockFaceEmbeddingProvider
from gen.providers.image.mock import MockImageProvider
from gen.qc.compliance_mock import MockComplianceProvider

FIXTURE_PERSONA_DIR = Path(__file__).parent.parent / "fixtures" / "persona"


@pytest.fixture
def _mock_deps(tmp_path, monkeypatch):
    deps = NodeDeps(
        image_provider=MockImageProvider(tmp_path / "generated"),
        face_embedding_provider=MockFaceEmbeddingProvider(),
        compliance_provider=MockComplianceProvider(passed=True),
        output_root=tmp_path / "output",
    )
    persona_ctx = PersonaContext.load(FIXTURE_PERSONA_DIR)

    def fake_build_deps(*, quality, persona_dir, output_root):
        deps.output_root = output_root
        return deps, persona_ctx

    monkeypatch.setattr(run_module, "_build_deps", fake_build_deps)
    return deps


def test_astream_generate_yields_expected_node_sequence(_mock_deps):
    async def collect():
        events = []
        async for node_name, delta in astream_generate(scene_brief="сцена в кафе"):
            events.append((node_name, delta))
        return events

    events = asyncio.run(collect())
    node_names = [name for name, _ in events]

    assert "build_prompt" in node_names
    assert "generate_one" in node_names
    assert "qc_one" in node_names
    assert "compliance_check" in node_names
    assert "deliver" in node_names

    build_prompt_delta = next(delta for name, delta in events if name == "build_prompt")
    assert "prompt" in build_prompt_delta

    deliver_delta = next(delta for name, delta in events if name == "deliver")
    assert deliver_delta["delivered_path"].is_file()
