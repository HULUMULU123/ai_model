"""Реальный адаптер генерации изображений через RouterAI (OpenAI-совместимый).

Подтверждено вживую 27.09.2026 запросом к `https://routerai.ru/api/v1/images/generations`
(через `openai` Python SDK, `client.images.generate`):
  - Эндпоинт зеркалит OpenAI Images API (`POST /v1/images/generations`),
    отвечает `{"data": [{"b64_json": "..."}]}`.
  - `input_references` — RouterAI-специфичное расширение (не входит в
    стандартную сигнатуру SDK, передаётся через `extra_body`), формат:
    `[{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]`.
    Именно этот формат подтверждён ошибкой валидации API при неверном формате
    и успешным (HTTP 200) ответом при верном.
"""

from __future__ import annotations

import base64
import tempfile
import uuid
from pathlib import Path

from openai import OpenAI

from gen.core.errors import ProviderError
from gen.providers.base import ImageProvider


def _image_to_data_uri(path: Path) -> str:
    suffix = path.suffix.lstrip(".").lower() or "png"
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{data}"


class RouterAIImageProvider(ImageProvider):
    def __init__(
        self, *, api_key: str, base_url: str, model: str, output_dir: Path | None = None
    ) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._output_dir = output_dir or Path(tempfile.mkdtemp(prefix="content-gen-images-"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[Path] | None = None,
        n: int = 1,
    ) -> list[Path]:
        extra_body = {}
        if reference_images:
            extra_body["input_references"] = [
                {"type": "image_url", "image_url": {"url": _image_to_data_uri(p)}}
                for p in reference_images
            ]

        response = self._client.images.generate(
            model=self._model,
            prompt=prompt,
            n=n,
            extra_body=extra_body or None,
        )

        if not response.data:
            raise ProviderError("RouterAI images API вернул пустой data[]")

        paths = []
        for i, item in enumerate(response.data):
            if not item.b64_json:
                raise ProviderError(f"RouterAI images API: элемент {i} без b64_json")
            image_bytes = base64.b64decode(item.b64_json)
            path = self._output_dir / f"routerai-image-{uuid.uuid4().hex}-{i}.png"
            path.write_bytes(image_bytes)
            paths.append(path)
        return paths
