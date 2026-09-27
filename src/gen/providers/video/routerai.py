"""Реальный адаптер image-to-video генерации (RouterAI/fal.ai).

TODO: не реализовано. Эндпоинт image-to-video и формат polling-ответа
(job id / status / result url) не подтверждены документацией. Перед
реализацией свериться с:
  - fal.ai image-to-video моделями: https://fal.ai/models?categories=image-to-video
  - RouterAI видео-эндпоинтами (если есть в текущем плане подписки).
"""

from __future__ import annotations

from pathlib import Path

from gen.providers.base import VideoProvider


class RouterAIVideoProvider(VideoProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    async def generate(
        self,
        prompt: str,
        *,
        source_image: Path,
        reference_images: list[Path] | None = None,
    ) -> Path:
        raise NotImplementedError(
            "RouterAIVideoProvider.generate: эндпоинт image-to-video не подтверждён "
            "документацией, см. TODO в шапке файла"
        )
