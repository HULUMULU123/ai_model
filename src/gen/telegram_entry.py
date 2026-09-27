"""Личный Telegram-бот "для себя" (вариант B из ТЗ §6).

Пишешь боту бриф текстом → бот запускает граф `generate` → присылает готовый
файл тебе в личку. Без карточек одобрения, без ролей, без вебхуков и БД —
long polling через `getUpdates` (документированный Telegram Bot API:
https://core.telegram.org/bots/api#getupdates), процесс работает, пока ты
сам его не остановишь (это не фоновый воркер фермы — просто другая точка
входа в тот же граф `generate`, что и CLI).

Формат сообщения:
  - обычный текст → бриф на фото, `--aspect 9:16` (вертикаль под Reels/Stories)
  - `video: <бриф>` → бриф на видео (вертикаль 9:16 по умолчанию в адаптере)

Пока `TELEGRAM_CHAT_ID` не задан в `.env`, бот ничего не генерирует — только
печатает в консоль chat_id первого написавшего, чтобы владелец мог его
зафиксировать. Это защита "для себя": бот не должен исполнять команды от
случайных людей.
"""

from __future__ import annotations

import httpx

from gen.core.config import load_settings
from gen.core.logging import get_logger
from gen.delivery.telegram import send_message, send_photo, send_video
from gen.graph.generate.run import run_generate

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
POLL_TIMEOUT_SECONDS = 30
VIDEO_PREFIXES = ("video:", "видео:")


def parse_message(text: str) -> tuple[str, str]:
    """Возвращает (format_, scene_brief) из текста сообщения."""
    stripped = text.strip()
    for prefix in VIDEO_PREFIXES:
        if stripped.lower().startswith(prefix):
            return "video", stripped[len(prefix) :].strip()
    return "photo", stripped


def _handle_message(*, bot_token: str, chat_id: str, text: str) -> None:
    format_, scene_brief = parse_message(text)
    if not scene_brief:
        send_message("Пустой бриф — напиши сцену текстом.", bot_token=bot_token, chat_id=chat_id)
        return

    send_message(f"Генерирую {format_}: {scene_brief}", bot_token=bot_token, chat_id=chat_id)
    try:
        result = run_generate(scene_brief=scene_brief, format_=format_, aspect="9:16")
    except Exception as exc:  # noqa: BLE001 - показать причину владельцу, не падать молча
        send_message(f"Ошибка генерации: {exc}", bot_token=bot_token, chat_id=chat_id)
        return

    if not result.get("compliance_passed", False):
        send_message(
            f"Отклонено модерацией: {result.get('compliance_reason') or 'причина не указана'}",
            bot_token=bot_token,
            chat_id=chat_id,
        )
        return

    caption = f"{scene_brief} (QC {result['best_score']:.2f})"
    if format_ == "video":
        send_video(result["delivered_path"], bot_token=bot_token, chat_id=chat_id, caption=caption)
    else:
        send_photo(result["delivered_path"], bot_token=bot_token, chat_id=chat_id, caption=caption)


def run_bot() -> None:
    settings = load_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан в .env")

    bot_token = settings.telegram_bot_token
    owner_chat_id = settings.telegram_chat_id or None
    offset = 0

    logger.info("Telegram-бот запущен, long polling...")
    if not owner_chat_id:
        logger.warning(
            "TELEGRAM_CHAT_ID не задан — бот будет только логировать chat_id входящих "
            "сообщений, не отвечая. Напиши боту что-нибудь и укажи chat_id в .env."
        )

    while True:
        response = httpx.get(
            f"{TELEGRAM_API_BASE}/bot{bot_token}/getUpdates",
            params={"offset": offset, "timeout": POLL_TIMEOUT_SECONDS},
            timeout=POLL_TIMEOUT_SECONDS + 10,
        )
        payload = response.json()
        for update in payload.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text")
            if not chat_id or not text:
                continue

            if not owner_chat_id:
                logger.info("Сообщение от chat_id=%s (владелец ещё не задан): %r", chat_id, text)
                continue
            if chat_id != owner_chat_id:
                logger.info("Игнорирую сообщение от чужого chat_id=%s", chat_id)
                continue

            _handle_message(bot_token=bot_token, chat_id=chat_id, text=text)


def main() -> None:
    run_bot()


if __name__ == "__main__":
    main()
