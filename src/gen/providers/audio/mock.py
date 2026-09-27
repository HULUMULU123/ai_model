"""Детерминированный мок AudioProvider для тестов (без сети)."""

from __future__ import annotations

from pathlib import Path

from gen.providers.base import AudioProvider


class MockAudioProvider(AudioProvider):
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.calls: list[tuple[str, str]] = []

    def generate(self, text: str, *, voice: str, response_format: str = "mp3") -> Path:
        self.calls.append((text, voice))
        path = self._output_dir / f"mock-voice-{self.call_count}.{response_format}"
        path.write_bytes(b"mock-audio")
        return path

    @property
    def call_count(self) -> int:
        return len(self.calls)
