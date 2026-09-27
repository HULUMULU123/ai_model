"""Реальный адаптер синтеза речи через RouterAI (OpenAI-совместимый).

Подтверждено вживую 27.09.2026: `POST /audio/speech` (через `openai` SDK,
`client.audio.speech.create(model=..., voice=..., input=...)`) принял запрос
как валидный — упёрся в ту же структурированную ошибку `402 Insufficient
balance`, что и image/video эндпоинты, а не в ошибку формата параметров.
Значит контракт зеркалит стандартный OpenAI TTS API
(https://platform.openai.com/docs/guides/text-to-speech). Реальный
сгенерированный файл не получен (баланс аккаунта отрицательный) — если
после пополнения баланса ответ разойдётся с ожиданием (не бинарные байты
аудио), `generate` кинет `ProviderError` с деталями, а не тихо запишет мусор.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from openai import OpenAI

from gen.core.errors import ProviderError
from gen.providers.base import AudioProvider


class RouterAIAudioProvider(AudioProvider):
    def __init__(
        self, *, api_key: str, base_url: str, model: str, output_dir: Path | None = None
    ) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._output_dir = output_dir or Path(tempfile.mkdtemp(prefix="content-gen-audio-"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, text: str, *, voice: str, response_format: str = "mp3") -> Path:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=voice,
            input=text,
            response_format=response_format,
        )
        content = response.read()
        if not content:
            raise ProviderError("RouterAI audio API вернул пустой ответ")

        path = self._output_dir / f"voice-{uuid.uuid4().hex}.{response_format}"
        path.write_bytes(content)
        return path
