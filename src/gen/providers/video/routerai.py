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

**Обновлено после реального прогона (баланс пополнен, запрос дошёл до
создания job):** ответ `POST /videos` — не `{"id": ...}` напрямую, а
`{"generation_id": "rai-vid-...", "id": "gen-vid-...", "polling_url":
"https://routerai.ru/api/v1/videos/gen-vid-...", "status": "pending"}`.
Значит: (1) статус `pending` — тоже "ещё не готово", не ошибка; (2) есть
готовый `polling_url`, которым и нужно опрашивать вместо самостоятельной
сборки `/videos/{id}` (используем его, если он есть в ответе). Финальная
форма ответа при `status: "completed"` (имя поля с URL результата) всё ещё
не подтверждена — до этого статуса реальный прогон пока не дошёл.

**Модель по умолчанию сменена на `alibaba/wan-3.0` (было `wan-2.6`, по
прямому запросу). НЕ ПОДТВЕРЖДЕНО реальным запросом** (в отличие от
`size` для `wan-2.6`, который дошёл до 402 Insufficient balance). У
`wan-3.0` в каталоге `supported_sizes: null`, а `supported_resolutions:
["480p","720p","1080p"]` + `supported_aspect_ratios` (включая `9:16`) — то
есть, в отличие от `wan-2.6`, готовых строк `WxH` нет, поэтому вместо
единого поля `size` отправляются отдельные `resolution`+`aspect_ratio`.
Если API этой модели на самом деле ждёт другие имена полей — вернётся
ошибка API, а не тихая генерация с неверным разрешением.
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

DEFAULT_DURATION_SECONDS = 5
# 720p/9:16 по умолчанию (вертикаль под Reels/Stories, разрешение — по
# прямому запросу "пока 720"). См. models.yaml `video.resolution`/`aspect_ratio`.
DEFAULT_RESOLUTION = "720p"
DEFAULT_ASPECT_RATIO = "9:16"


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
        resolution: str = DEFAULT_RESOLUTION,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        duration_seconds: int = DEFAULT_DURATION_SECONDS,
        output_dir: Path | None = None,
    ) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._resolution = resolution
        self._aspect_ratio = aspect_ratio
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
                    "resolution": self._resolution,
                    "aspect_ratio": self._aspect_ratio,
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
            polling_url = job.get("polling_url") or f"{self._base_url}/videos/{job_id}"

            deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
            while True:
                status_response = await client.get(polling_url, timeout=30.0)
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
                if status not in ("queued", "pending", "in_progress", "processing", None):
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
