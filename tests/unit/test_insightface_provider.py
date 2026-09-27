"""Тест реального InsightFace-адаптера — на настоящих файлах, без сети.

Требует локально закэшированную модель `buffalo_l` (`~/.insightface/models/`)
— при первом использовании она скачивается адаптером сам (см.
gen.providers.face_embedding.insightface). Если модели нет и её негде взять
в CI-окружении — тест скипается, а не притворяется зелёным.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("insightface")

from gen.core.errors import ProviderError
from gen.providers.face_embedding.insightface import InsightFaceEmbeddingProvider

FIXTURE_CANON_DIR = Path(__file__).parent.parent / "fixtures" / "persona" / "canon"


@pytest.fixture(scope="module")
def provider():
    try:
        return InsightFaceEmbeddingProvider()
    except (OSError, RuntimeError) as exc:  # окружение без доступа к модели
        pytest.skip(f"InsightFace недоступен в этом окружении: {exc}")


def test_embed_raises_on_image_without_a_face(provider, tmp_path):
    from PIL import Image

    no_face = tmp_path / "no-face.png"
    Image.new("RGB", (128, 128), color=(30, 30, 30)).save(no_face)

    with pytest.raises(ProviderError):
        provider.embed(no_face)


def test_similarity_of_identical_embedding_is_one(provider):
    vector = [0.1] * 512
    # нормируем как это делает insightface (L2-норма 1)
    import numpy as np

    v = np.array(vector)
    v = (v / np.linalg.norm(v)).tolist()

    assert provider.similarity(v, v) == pytest.approx(1.0, abs=1e-6)
