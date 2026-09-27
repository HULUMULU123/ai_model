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
  - `voice: <текст>` (или `озвучь:`) → озвучка текста голосом персонажа
    (не входит в исходное ТЗ — добавлено отдельно, см. `src/gen/voice.py`)
  - `/start` или `/help` → инлайн-клавиатура с краткими подсказками по каждой
    команде (нажатие кнопки не запускает генерацию — только показывает
    инструкцию, чтобы не путаться в форматах)

Пока `TELEGRAM_CHAT_ID` не задан в `.env`, бот ничего не генерирует — только
печатает в консоль chat_id первого написавшего, чтобы владелец мог его
зафиксировать. Это защита "для себя": бот не должен исполнять команды от
случайных людей.
"""

from __future__ import annotations

import httpx

from gen.core.config import load_settings
from gen.core.logging import get_logger
from gen.delivery.telegram import (
    answer_callback_query,
    send_message,
    send_photo,
    send_video,
    send_voice,
)
from gen.graph.generate.run import run_generate
from gen.voice import run_voice_line

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
POLL_TIMEOUT_SECONDS = 30
VIDEO_PREFIXES = ("video:", "видео:")
VOICE_PREFIXES = ("voice:", "озвучь:")

WELCOME_TEXT = (
    "Привет! Я генерирую фото и видео персонажа по твоему брифу. "
    "Нажми кнопку ниже, чтобы узнать формат команды."
)

# (callback_data, подпись кнопки, текст инструкции при нажатии)
HELP_BUTTONS: list[tuple[str, str, str]] = [
    (
        "help_photo",
        "📷 Фото",
        (
            "Просто напиши сцену текстом, например:\n«сцена в кафе, повседневный образ»\n"
            "Формат — вертикальный (9:16), под Reels/Stories/Threads."
        ),
    ),
    (
        "help_video",
        "🎬 Видео",
        (
            "Напиши с префиксом video: (или видео:), например:\n«video: у гаража с Клипом»\n"
            "Ролик 5 секунд, вертикальный (9:16)."
        ),
    ),
    (
        "help_voice",
        "🎙️ Голос",
        (
            "Напиши с префиксом voice: (или озвучь:), например:\n«voice: Crvena update, day "
            "twelve. Still not starting.»\nПрисылаю голосовым сообщением, не входит в "
            "исходное ТЗ — добавлено отдельно по запросу."
        ),
    ),
    (
        "help_general",
        "❓ Как это работает",
        (
            "1 сообщение = 1 генерация (без веера кандидатов, без ретраев сверх лимита).\n"
            "Если QC (сходство лица) не проходит — 1 автоповтор, потом присылаю "
            "лучшее с пометкой low-confidence.\n"
            "Нарушающий модерацию кадр не присылается — только причина отказа."
        ),
    ),
]


def parse_message(text: str) -> tuple[str, str]:
    """Возвращает (format_, scene_brief) из текста сообщения.

    `format_` — один из `photo`/`video`/`voice`.
    """
    stripped = text.strip()
    for prefix in VIDEO_PREFIXES:
        if stripped.lower().startswith(prefix):
            return "video", stripped[len(prefix) :].strip()
    for prefix in VOICE_PREFIXES:
        if stripped.lower().startswith(prefix):
            return "voice", stripped[len(prefix) :].strip()
    return "photo", stripped


def _send_help_keyboard(*, bot_token: str, chat_id: str) -> None:
    buttons = [(label, data) for data, label, _ in HELP_BUTTONS]
    send_message(WELCOME_TEXT, bot_token=bot_token, chat_id=chat_id, buttons=buttons)


def _handle_callback_query(*, bot_token: str, chat_id: str, callback_query_id: str, data: str) -> None:
    answer_callback_query(callback_query_id, bot_token=bot_token)
    instruction = next((text for key, _, text in HELP_BUTTONS if key == data), None)
    if instruction is None:
        return
    send_message(instruction, bot_token=bot_token, chat_id=chat_id)


def _handle_message(*, bot_token: str, chat_id: str, text: str) -> None:
    if text.strip().lower() in ("/start", "/help"):
        _send_help_keyboard(bot_token=bot_token, chat_id=chat_id)
        return

    format_, scene_brief = parse_message(text)
    if not scene_brief:
        send_message("Пустой бриф — напиши сцену текстом.", bot_token=bot_token, chat_id=chat_id)
        return

    send_message(f"Генерирую {format_}: {scene_brief}", bot_token=bot_token, chat_id=chat_id)

    if format_ == "voice":
        try:
            delivered_path = run_voice_line(scene_brief, response_format="opus")
        except Exception as exc:  # noqa: BLE001 - показать причину владельцу, не падать молча
            send_message(f"Ошибка озвучки: {exc}", bot_token=bot_token, chat_id=chat_id)
            return
        send_voice(delivered_path, bot_token=bot_token, chat_id=chat_id, caption=scene_brief)
        return

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

            callback_query = update.get("callback_query")
            message = update.get("message") or (callback_query or {}).get("message") or {}
            chat_id = str(message.get("chat", {}).get("id", ""))
            if not chat_id:
                continue

            if not owner_chat_id:
                logger.info("Сообщение от chat_id=%s (владелец ещё не задан)", chat_id)
                continue
            if chat_id != owner_chat_id:
                logger.info("Игнорирую сообщение от чужого chat_id=%s", chat_id)
                continue

            if callback_query:
                _handle_callback_query(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    callback_query_id=callback_query["id"],
                    data=callback_query.get("data", ""),
                )
                continue

            text = message.get("text")
            if not text:
                continue
            _handle_message(bot_token=bot_token, chat_id=chat_id, text=text)


def main() -> None:
    run_bot()


if __name__ == "__main__":
    main()
