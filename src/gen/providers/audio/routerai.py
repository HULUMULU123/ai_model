"""Реальный адаптер синтеза речи через RouterAI (OpenAI-совместимый).

Контракт (`POST /audio/speech` через `openai` SDK,
`client.audio.speech.create(model=..., voice=..., input=...)`) подтверждён
вживую 27.09.2026 для `google/gemini-3.8-flash-tts`/`minimax/speech-2.8-hd` —
запрос принят как валидный, упёрся в `402 Insufficient balance`, а не в
ошибку формата параметров.

**Модель `bytedance-seed/seed-audio-1-0` пробовалась и отклонена** после
реального прогона: `503 {"error":{"message":"Provider rejected the request:
speaker <текст>...","code":400}}` — поле у неё называется `speaker`, а не
`voice`, и оно НЕ принимает свободное текстовое описание голоса, только
конкретный Seed speaker ID (недоступный без документации ByteDance Seed).
Та же попытка также показала `response_format` **только `"mp3"`/`"pcm"`**,
не `"opus"` — отсюда дефолт `"mp3"` в `generate()` ниже; `gen.telegram_entry`
шлёт результат через `sendAudio`, не `sendVoice` (тому нужен ogg/opus).

Текущая модель по умолчанию — `google/gemini-3.8-flash-tts` (см.
`models.yaml`), она принимает короткие пресет-id голоса (`voice="Leda"` и
т.п.), что и передаётся сюда без изменений в адаптере.
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
