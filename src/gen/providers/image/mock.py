"""Детерминированный мок ImageProvider для тестов (без сети).

Пишет настоящие маленькие PNG (через Pillow), а не байты-заглушки — это
позволяет тестировать пост-обработку (апскейл/кроп) на реальных изображениях
без сети.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from gen.providers.base import ImageProvider

MOCK_IMAGE_SIZE = (64, 96)


class MockImageProvider(ImageProvider):
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.calls: list[tuple[str, int]] = []

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[Path] | None = None,
        n: int = 1,
    ) -> list[Path]:
        self.calls.append((prompt, n))
        paths = []
        for i in range(n):
            path = self._output_dir / f"mock-image-{self.call_count}-{i}.png"
            Image.new("RGB", MOCK_IMAGE_SIZE, color=(120, 140, 160)).save(path)
            paths.append(path)
        return paths

    @property
    def call_count(self) -> int:
        return len(self.calls)
