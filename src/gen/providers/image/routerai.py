"""Реальный адаптер генерации изображений (RouterAI/fal.ai).

TODO: не реализовано. У RouterAI и fal.ai нет проверенной здесь документации
на конкретный эндпоинт медиа-генерации (image generation с референсами лица
для консистентности) — сигнатура запроса/ответа не подтверждена, поэтому
адаптер не выдумывается. Перед реализацией свериться с актуальной
документацией:
  - RouterAI: эндпоинт(ы) генерации изображений (если есть в текущем плане).
  - fal.ai: https://fal.ai/models (image generation модели, image-to-image
    с референсами).
"""

from __future__ import annotations

from pathlib import Path

from gen.providers.base import ImageProvider


class RouterAIImageProvider(ImageProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[Path] | None = None,
        n: int = 1,
    ) -> list[Path]:
        raise NotImplementedError(
            "RouterAIImageProvider.generate: эндпоинт медиа-генерации не подтверждён "
            "документацией, см. TODO в шапке файла"
        )
