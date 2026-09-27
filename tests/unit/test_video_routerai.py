"""Тесты RouterAIVideoProvider на реальном (наблюдённом) ответе API, respx-моки.

Регрессионный тест на баг, найденный вживую 27.09.2026: ответ POST /videos
приходит со status="pending" и отдельным polling_url, не просто {"id": ...}
с status="queued" как предполагалось раньше.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

import gen.providers.video.routerai as routerai_module
from gen.core.errors import ProviderError
from gen.providers.video.routerai import RouterAIVideoProvider


@pytest.fixture
def source_image(tmp_path):
    path = tmp_path / "source.png"
    path.write_bytes(b"fake-image-bytes")
    return path


@pytest.fixture(autouse=True)
def _fast_polling(monkeypatch):
    monkeypatch.setattr(routerai_module, "POLL_INTERVAL_SECONDS", 0.0)


@respx.mock
def test_generate_handles_pending_status_and_polling_url(tmp_path, source_image):
    respx.post("https://routerai.ru/api/v1/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "generation_id": "rai-vid-1",
                "id": "gen-vid-1",
                "polling_url": "https://routerai.ru/api/v1/videos/gen-vid-1",
                "status": "pending",
            },
        )
    )
    poll_route = respx.get("https://routerai.ru/api/v1/videos/gen-vid-1")
    poll_route.side_effect = [
        httpx.Response(200, json={"id": "gen-vid-1", "status": "pending"}),
        httpx.Response(
            200, json={"id": "gen-vid-1", "status": "completed", "video_url": "https://cdn/x.mp4"}
        ),
    ]
    respx.get("https://cdn/x.mp4").mock(return_value=httpx.Response(200, content=b"video-bytes"))

    provider = RouterAIVideoProvider(
        api_key="key",
        base_url="https://routerai.ru/api/v1",
        model="alibaba/wan-2.6",
        output_dir=tmp_path,
    )

    result_path = asyncio.run(provider.generate("prompt", source_image=source_image))

    assert result_path.is_file()
    assert result_path.read_bytes() == b"video-bytes"
    assert poll_route.call_count == 2


@respx.mock
def test_generate_uses_polling_url_not_constructed_path(tmp_path, source_image):
    """polling_url может отличаться от /videos/{id} — используем его как есть."""
    respx.post("https://routerai.ru/api/v1/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "gen-vid-2",
                "polling_url": "https://routerai.ru/api/v1/jobs/gen-vid-2/status",
                "status": "queued",
            },
        )
    )
    poll_route = respx.get("https://routerai.ru/api/v1/jobs/gen-vid-2/status").mock(
        return_value=httpx.Response(
            200, json={"id": "gen-vid-2", "status": "completed", "video_url": "https://cdn/y.mp4"}
        )
    )
    respx.get("https://cdn/y.mp4").mock(return_value=httpx.Response(200, content=b"video-bytes-2"))

    provider = RouterAIVideoProvider(
        api_key="key",
        base_url="https://routerai.ru/api/v1",
        model="alibaba/wan-2.6",
        output_dir=tmp_path,
    )

    result_path = asyncio.run(provider.generate("prompt", source_image=source_image))

    assert poll_route.called
    assert result_path.read_bytes() == b"video-bytes-2"


@respx.mock
def test_generate_raises_on_unknown_status(tmp_path, source_image):
    respx.post("https://routerai.ru/api/v1/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "gen-vid-3",
                "polling_url": "https://routerai.ru/api/v1/videos/gen-vid-3",
                "status": "pending",
            },
        )
    )
    respx.get("https://routerai.ru/api/v1/videos/gen-vid-3").mock(
        return_value=httpx.Response(200, json={"id": "gen-vid-3", "status": "weird"})
    )

    provider = RouterAIVideoProvider(
        api_key="key",
        base_url="https://routerai.ru/api/v1",
        model="alibaba/wan-2.6",
        output_dir=tmp_path,
    )

    with pytest.raises(ProviderError):
        asyncio.run(provider.generate("prompt", source_image=source_image))
