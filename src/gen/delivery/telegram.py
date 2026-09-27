"""Отправка результата в личный Telegram (вариант B из ТЗ §6).

Telegram Bot API — официально документированный, публичный контракт
(https://core.telegram.org/bots/api#sendphoto,
https://core.telegram.org/bots/api#sendvideo): `POST
https://api.telegram.org/bot<token>/sendPhoto` / `/sendVideo`, файл —
multipart-полем `photo`/`video`, получатель — `chat_id`.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from gen.core.errors import ProviderError

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 60.0


class TelegramDeliveryError(ProviderError):
    pass


def _send_file(
    *, bot_token: str, chat_id: str, method: str, field_name: str, path: Path, caption: str = ""
) -> dict:
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"
    with path.open("rb") as f:
        response = httpx.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={field_name: (path.name, f)},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramDeliveryError(f"Telegram Bot API {method} отклонил запрос: {payload}")
    return payload


def send_photo(path: Path, *, bot_token: str, chat_id: str, caption: str = "") -> None:
    _send_file(
        bot_token=bot_token,
        chat_id=chat_id,
        method="sendPhoto",
        field_name="photo",
        path=path,
        caption=caption,
    )


def send_video(path: Path, *, bot_token: str, chat_id: str, caption: str = "") -> None:
    _send_file(
        bot_token=bot_token,
        chat_id=chat_id,
        method="sendVideo",
        field_name="video",
        path=path,
        caption=caption,
    )


def send_message(text: str, *, bot_token: str, chat_id: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    response = httpx.post(
        url, json={"chat_id": chat_id, "text": text}, timeout=REQUEST_TIMEOUT_SECONDS
    )
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramDeliveryError(f"Telegram Bot API sendMessage отклонил запрос: {payload}")
