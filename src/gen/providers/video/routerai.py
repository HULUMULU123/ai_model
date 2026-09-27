"""Реальный адаптер image-to-video генерации через RouterAI.

Подтверждено вживую 27.09.2026 (`https://routerai.ru/api/v1/videos`) через
прямые HTTP-запросы (не через `openai` SDK — его `client.videos.create`
отправляет multipart в формате OpenAI Sora API, RouterAI отвечает `400
Invalid JSON format`, то есть эндпоинт ждёт обычный JSON, не multipart):

  - `POST /api/v1/videos` с JSON `{"model", "prompt", "image": "data:...",
    "size": ..., "duration": <секунды>}` — подтверждено структурированной
    ошибкой `402 Insufficient balance` с точной оценкой стоимости (значит
    модель/поля приняты как валидные) при недостатке средств на аккаунте.
    `size` — точный `WxH`, не тир качества: для `alibaba/wan-2.6` каталог
    (`routerai.ru/models`) даёт `supported_sizes: ["1280x720", "1080x1920",
    "720x1280", "1920x1080"]` и `supported_aspect_ratios: ["16:9", "9:16"]` —
    вертикаль для Reels/Stories это `720x1280` (или `1080x1920` подороже).
  - `GET /api/v1/videos/{id}` — подтверждено только на несуществующем id
    (`404 {"error": "Video job not found"}`), реальный успешный job
    получить не удалось (не хватило баланса даже на самый дешёвый вариант:
    46.57 ₽ при использовании 65.79 ₽ за 480p/5с).

**Не полностью подтверждено:** точная форма успешного ответа `GET
/videos/{id}` (имя поля статуса, имя поля с URL/данными результата) — не
проверена вживую из-за нехватки баланса. Реализация ниже — лучшее
предположение по обычным конвенциям (`status`, `video_url`/`url`), но
`_parse_status`/`_extract_video_url` кидают `ProviderError` с сырым JSON,
если ожидаемых полей нет, вместо того чтобы тихо упасть на непонятном
исключении. Поправить после первого реального успешного прогона (нужно
пополнить баланс аккаунта).
"""

from __future__ import annotations

import asyncio
import base64
import tempfile
import time
from pathlib import Path

import httpx

from gen.core.errors import ProviderError
from gen.providers.base import VideoProvider

POLL_INTERVAL_SECONDS = 5.0
POLL_TIMEOUT_SECONDS = 600.0

# Модель по умолчанию (alibaba/wan-2.6, см. models.yaml) поддерживает
# длительности 5 и 10 секунд — подтверждено ошибкой валидации API.
DEFAULT_DURATION_SECONDS = 5
# Вертикаль 9:16 по умолчанию — под Reels/Stories/TikTok-формат (720p, дешевле
# 1080x1920); см. supported_sizes в docstring выше.
DEFAULT_SIZE = "720x1280"


def _image_to_data_uri(path: Path) -> str:
    suffix = path.suffix.lstrip(".").lower() or "png"
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{data}"


class RouterAIVideoProvider(VideoProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        size: str = DEFAULT_SIZE,
        duration_seconds: int = DEFAULT_DURATION_SECONDS,
        output_dir: Path | None = None,
    ) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._size = size
        self._duration_seconds = duration_seconds
        self._output_dir = output_dir or Path(tempfile.mkdtemp(prefix="content-gen-videos-"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        prompt: str,
        *,
        source_image: Path,
        reference_images: list[Path] | None = None,
    ) -> Path:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            create_response = await client.post(
                "/videos",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "image": _image_to_data_uri(source_image),
                    "size": self._size,
                    "duration": self._duration_seconds,
                },
                timeout=60.0,
            )
            if create_response.status_code >= 400:
                raise ProviderError(
                    f"RouterAI videos API отклонил запрос ({create_response.status_code}): "
                    f"{create_response.text}"
                )
            job = create_response.json()
            job_id = job.get("id")
            if not job_id:
                raise ProviderError(f"RouterAI videos API: ответ без id: {job!r}")

            deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
            while True:
                status_response = await client.get(f"/videos/{job_id}", timeout=30.0)
                if status_response.status_code >= 400:
                    raise ProviderError(
                        f"RouterAI videos API: ошибка при опросе статуса "
                        f"({status_response.status_code}): {status_response.text}"
                    )
                job = status_response.json()
                status = job.get("status")

                if status == "completed":
                    break
                if status == "failed":
                    raise ProviderError(f"Видео {job_id} завершилось с ошибкой: {job!r}")
                if status not in ("queued", "in_progress", "processing", None):
                    raise ProviderError(
                        f"RouterAI videos API: неизвестный статус {status!r} в ответе {job!r}"
                    )
                if time.monotonic() >= deadline:
                    raise ProviderError(
                        f"Видео {job_id} не завершилось за {POLL_TIMEOUT_SECONDS:.0f}с "
                        f"(последний ответ: {job!r})"
                    )
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            video_url = job.get("video_url") or job.get("url") or job.get("output", {}).get("url")
            if not video_url:
                raise ProviderError(
                    f"RouterAI videos API: не найдено поле с URL результата в {job!r}"
                )

            download_response = await client.get(video_url, timeout=120.0)
            download_response.raise_for_status()

        output_path = self._output_dir / f"{job_id}.mp4"
        output_path.write_bytes(download_response.content)
        return output_path
