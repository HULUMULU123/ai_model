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


def send_message(
    text: str,
    *,
    bot_token: str,
    chat_id: str,
    buttons: list[tuple[str, str]] | None = None,
) -> None:
    """Отправляет текст, опционально с инлайн-клавиатурой.

    `buttons` — список (подпись, callback_data) для `InlineKeyboardMarkup`
    (https://core.telegram.org/bots/api#inlinekeyboardmarkup), одна кнопка на
    строку — удобно листать с телефона.
    """
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload_body: dict = {"chat_id": chat_id, "text": text}
    if buttons:
        payload_body["reply_markup"] = {
            "inline_keyboard": [[{"text": label, "callback_data": data}] for label, data in buttons]
        }
    response = httpx.post(url, json=payload_body, timeout=REQUEST_TIMEOUT_SECONDS)
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramDeliveryError(f"Telegram Bot API sendMessage отклонил запрос: {payload}")


def answer_callback_query(callback_query_id: str, *, bot_token: str, text: str = "") -> None:
    """Подтверждает нажатие инлайн-кнопки (https://core.telegram.org/bots/api#answercallbackquery).

    Обязательно вызывать на каждый `callback_query` — иначе Telegram
    показывает у кнопки бесконечный "часики" в клиенте пользователя.
    """
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/answerCallbackQuery"
    response = httpx.post(
        url,
        json={"callback_query_id": callback_query_id, "text": text},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramDeliveryError(
            f"Telegram Bot API answerCallbackQuery отклонил запрос: {payload}"
        )
