"""Реальный адаптер сходства лиц через embedding-модель.

TODO: не реализовано. ТЗ (раздел 11, открытые вопросы) явно оставляет выбор
face-embedding модели/провайдера на M1 — нужно свериться с документацией,
какая модель доступна через RouterAI/fal.ai (или локально, например
InsightFace/ArcFace), прежде чем писать реальный вызов. Не выдумывать API.
Кандидаты для проверки:
  - fal.ai (если есть face-embedding/face-similarity модель в каталоге)
  - локальный `insightface` пакет (ArcFace embeddings), без внешнего API
"""

from __future__ import annotations

from pathlib import Path

from gen.providers.base import FaceEmbeddingProvider


class InsightFaceEmbeddingProvider(FaceEmbeddingProvider):
    def __init__(self) -> None:
        pass

    def embed(self, image: Path) -> list[float]:
        raise NotImplementedError(
            "InsightFaceEmbeddingProvider.embed: модель эмбеддингов лица не подтверждена "
            "документацией, см. TODO в шапке файла"
        )

    def similarity(self, a: list[float], b: list[float]) -> float:
        raise NotImplementedError(
            "InsightFaceEmbeddingProvider.similarity: см. TODO в шапке файла"
        )
