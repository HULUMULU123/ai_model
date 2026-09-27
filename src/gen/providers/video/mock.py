"""Детерминированный мок VideoProvider для тестов (без сети)."""

from __future__ import annotations

from pathlib import Path

from gen.providers.base import VideoProvider


class MockVideoProvider(VideoProvider):
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.calls: list[str] = []

    async def generate(
        self,
        prompt: str,
        *,
        source_image: Path,
        reference_images: list[Path] | None = None,
    ) -> Path:
        self.calls.append(prompt)
        path = self._output_dir / f"mock-video-{self.call_count}.mp4"
        path.write_bytes(b"mock-video")
        return path

    @property
    def call_count(self) -> int:
        return len(self.calls)
