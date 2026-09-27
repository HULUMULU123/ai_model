"""Тесты пост-обработки видео — реальный ffmpeg, без сети.

Скипаются, если ffmpeg/ffprobe не установлены в окружении (см.
gen.postprocess.video.FfmpegNotFoundError) — не подделываем результат, честно
сообщаем, что тест не может проверить реальное поведение.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from gen.postprocess.video import extract_frames, normalize_video

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

pytestmark = pytest.mark.skipif(
    not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe не установлены в этом окружении"
)


@pytest.fixture
def sample_video(tmp_path):
    video_path = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=10",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


def test_extract_frames_returns_requested_count(sample_video):
    frames = extract_frames(sample_video, n=2)

    assert len(frames) == 2
    assert all(f.is_file() for f in frames)


def test_normalize_video_produces_playable_file(sample_video):
    normalize_video(sample_video, resolution="640x360")

    assert sample_video.is_file()
    frames = extract_frames(sample_video, n=1)
    assert frames[0].is_file()
