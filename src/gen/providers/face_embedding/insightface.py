"""Локальный адаптер сходства лиц через `insightface` (без внешнего API).

Подтверждено вживую 27.09.2026:
  - `insightface.app.FaceAnalysis(name="buffalo_l")` + `.prepare(ctx_id=0)` —
    при первом запуске скачивает модель `buffalo_l` (~280 МБ) с
    `github.com/deepinsight/insightface` (единственный сетевой вызов, дальше
    работает офлайн из `~/.insightface/models/`).
  - `.get(image_bgr)` возвращает список найденных лиц, `face.normed_embedding`
    — L2-нормированный вектор 512 float32 (норма 1.0), поэтому косинусное
    сходство — это просто скалярное произведение.
  - Выбран как единственная специализированная face-recognition модель,
    доступная без переплаты за общий (не для лиц) image-embedding через
    RouterAI — см. открытый вопрос ТЗ §11.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from gen.core.errors import ProviderError
from gen.providers.base import FaceEmbeddingProvider

DET_SIZE = (640, 640)


class InsightFaceEmbeddingProvider(FaceEmbeddingProvider):
    def __init__(self, *, model_name: str = "buffalo_l") -> None:
        import cv2
        from insightface.app import FaceAnalysis

        self._cv2 = cv2
        self._app = FaceAnalysis(name=model_name)
        self._app.prepare(ctx_id=0, det_size=DET_SIZE)

    def embed(self, image: Path) -> list[float]:
        img = self._cv2.imread(str(image))
        if img is None:
            raise ProviderError(f"Не удалось прочитать изображение: {image}")

        faces = self._app.get(img)
        if not faces:
            raise ProviderError(f"Лицо не найдено на изображении: {image}")

        def _bbox_area(face) -> float:
            x1, y1, x2, y2 = face.bbox
            return (x2 - x1) * (y2 - y1)

        largest_face = max(faces, key=_bbox_area)
        return largest_face.normed_embedding.tolist()

    def similarity(self, a: list[float], b: list[float]) -> float:
        va, vb = np.array(a), np.array(b)
        cosine = float(np.dot(va, vb))
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))
