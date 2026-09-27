"""Пост-обработка фото: апскейл ресемплингом и кроп под нужный аспект.

Ограничение: настоящей ИИ-апскейл-модели в стеке нет и она не подтверждена
документацией (см. CLAUDE.md, "не выдумывать API") — апскейл здесь честно
реализован через Pillow LANCZOS-ресемплинг, а не через нейросетевой
супер-резолюшн. Если позже появится проверенный апскейлер-провайдер, эта
функция заменяется на вызов к нему без изменения интерфейса узла.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "4:5": (4, 5),
    "9:16": (9, 16),
    "1:1": (1, 1),
}

DEFAULT_MIN_LONG_SIDE = 2048


def upscale(path: Path, *, min_long_side: int = DEFAULT_MIN_LONG_SIDE) -> Path:
    with Image.open(path) as img:
        long_side = max(img.size)
        if long_side >= min_long_side:
            return path

        scale = min_long_side / long_side
        new_size = (round(img.width * scale), round(img.height * scale))
        upscaled = img.resize(new_size, Image.LANCZOS)
        upscaled.save(path)
    return path


def crop_to_aspect(path: Path, aspect: str) -> Path:
    if aspect not in ASPECT_RATIOS:
        raise ValueError(f"Неизвестный аспект: {aspect!r}. Доступны: {list(ASPECT_RATIOS)}")

    target_w, target_h = ASPECT_RATIOS[aspect]
    target_ratio = target_w / target_h

    with Image.open(path) as img:
        width, height = img.size
        current_ratio = width / height

        if current_ratio > target_ratio:
            new_width = round(height * target_ratio)
            left = (width - new_width) // 2
            box = (left, 0, left + new_width, height)
        else:
            new_height = round(width / target_ratio)
            top = (height - new_height) // 2
            box = (0, top, width, top + new_height)

        cropped = img.crop(box)
        cropped.save(path)
    return path
