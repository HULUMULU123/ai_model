"""Пост-обработка видео через ffmpeg (CLI, документированный, не выдуманный).

Требует установленный `ffmpeg`/`ffprobe` в PATH. Если их нет — функции кидают
`FfmpegNotFoundError`, а не тихо падают или подделывают результат.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from gen.core.errors import ContentGenError


class FfmpegNotFoundError(ContentGenError):
    """ffmpeg/ffprobe не найден в PATH."""


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise FfmpegNotFoundError(
            "ffmpeg/ffprobe не найдены в PATH. Установи ffmpeg, чтобы обрабатывать видео."
        )


def _probe_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_frames(video_path: Path, *, n: int = 2) -> list[Path]:
    """Извлекает `n` кадров, равномерно распределённых по длительности видео.

    Для QC достаточно 1-2 кадра (см. ТЗ §8) — не 3-5, это и есть экономия.
    """
    _require_ffmpeg()
    if n < 1:
        raise ValueError("n должно быть >= 1")

    duration = _probe_duration(video_path)
    frames_dir = video_path.parent / f"{video_path.stem}-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = []
    for i in range(n):
        timestamp = duration * (i + 1) / (n + 1)
        frame_path = frames_dir / f"frame-{i:02d}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(frame_path),
            ],
            capture_output=True,
            check=True,
        )
        frame_paths.append(frame_path)
    return frame_paths


def normalize_video(video_path: Path, *, resolution: str = "1080x1920") -> Path:
    """Нормализует контейнер/разрешение видео на месте (перекодирует)."""
    _require_ffmpeg()

    tmp_path = video_path.with_suffix(f".normalized{video_path.suffix}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"scale={resolution.replace('x', ':')}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(tmp_path),
        ],
        capture_output=True,
        check=True,
    )
    tmp_path.replace(video_path)
    return video_path
