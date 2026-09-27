"""Детерминированный мок FaceEmbeddingProvider для тестов (без сети, без реального CV).

Эмбеддинг строится из хэша байтов файла — детерминированно, но не является
настоящим анализом лица. Годится только для проверки конвейера QC.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from gen.providers.base import FaceEmbeddingProvider


class MockFaceEmbeddingProvider(FaceEmbeddingProvider):
    def __init__(self) -> None:
        self.embed_calls = 0
        self.similarity_calls = 0

    def embed(self, image: Path) -> list[float]:
        self.embed_calls += 1
        digest = hashlib.sha256(image.read_bytes()).digest()
        return [b / 255.0 for b in digest[:16]]

    def similarity(self, a: list[float], b: list[float]) -> float:
        self.similarity_calls += 1
        if len(a) != len(b) or not a:
            return 0.0
        diffs = sum(abs(x - y) for x, y in zip(a, b, strict=True))
        max_diff = len(a)
        return 1.0 - (diffs / max_diff)
