"""Озвучка текста голосом персонажа — озвучка сцен/подписей контентом.

Не входит в исходное ТЗ (там только фото/видео) — добавлено по прямому
запросу. Сознательно не оформлено как LangGraph-граф: тут нет ни
face-QC (нет лица), ни аспект-кропа, ни compliance-развилки — просто один
вызов `AudioProvider` и доставка файла, экономия ради экономии здесь
означала бы городить граф с одним узлом.
"""

from __future__ import annotations

from pathlib import Path

from gen.core.config import load_settings
from gen.core.models_config import load_models_config, resolve_model, resolve_setting
from gen.delivery.local import deliver_to_output
from gen.providers.audio.routerai import RouterAIAudioProvider
from gen.providers.base import AudioProvider

DEFAULT_OUTPUT_ROOT = Path("output")


def generate_voice_line(
    text: str,
    *,
    audio_provider: AudioProvider,
    voice: str,
    response_format: str = "mp3",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Path:
    audio_path = audio_provider.generate(text, voice=voice, response_format=response_format)
    return deliver_to_output(
        audio_path,
        prompt=text,
        qc_score=1.0,
        low_confidence=False,
        output_root=output_root,
    )


def run_voice_line(
    text: str,
    *,
    quality: bool = False,
    voice: str | None = None,
    response_format: str = "mp3",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Path:
    """`voice` — переопределить пресет из `models.yaml` (для A/B на слух:
    `uv run voice-line --text "..." --voice Kore`), без правки конфига."""
    settings = load_settings()
    models_config = load_models_config()
    tier = "quality" if quality else "default"

    audio_provider = RouterAIAudioProvider(
        api_key=settings.routerai_api_key,
        base_url=settings.routerai_base_url,
        model=resolve_model(models_config, "voice", tier=tier),
    )
    resolved_voice = voice or resolve_setting(models_config, "voice", "voice_name")

    return generate_voice_line(
        text,
        audio_provider=audio_provider,
        voice=resolved_voice,
        response_format=response_format,
        output_root=output_root,
    )
