"""Отправка результата в личный Telegram (опционально, вариант B из ТЗ §6).

TODO: не реализовано в этой версии. Telegram Bot API `sendPhoto`/`sendDocument`
достаточно хорошо задокументирован (https://core.telegram.org/bots/api#sendphoto),
но реализация отложена до момента, когда появится реальная потребность в
доставке в Telegram (сейчас файловая доставка в `output/` покрывает M4).
Оставляю интерфейс и заглушку, чтобы не блокировать граф `generate`.
"""

from __future__ import annotations

from pathlib import Path


class TelegramDeliveryError(RuntimeError):
    pass


def send_photo_to_telegram(path: Path, *, bot_token: str, chat_id: str) -> None:
    raise NotImplementedError(
        "send_photo_to_telegram: не реализовано в этой версии, см. TODO в шапке файла"
    )
