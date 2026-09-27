import httpx
import pytest
import respx

from gen.delivery.telegram import TelegramDeliveryError, send_message, send_photo, send_video


@pytest.fixture
def fake_photo(tmp_path):
    path = tmp_path / "photo.png"
    path.write_bytes(b"fake-photo-bytes")
    return path


@respx.mock
def test_send_photo_success(fake_photo):
    route = respx.post("https://api.telegram.org/bot123:abc/sendPhoto").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_photo(fake_photo, bot_token="123:abc", chat_id="42", caption="test")

    assert route.called


@respx.mock
def test_send_photo_raises_on_api_error(fake_photo):
    respx.post("https://api.telegram.org/bot123:abc/sendPhoto").mock(
        return_value=httpx.Response(400, json={"ok": False, "description": "chat not found"})
    )

    with pytest.raises(TelegramDeliveryError):
        send_photo(fake_photo, bot_token="123:abc", chat_id="42")


@respx.mock
def test_send_video_success(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake-video-bytes")
    route = respx.post("https://api.telegram.org/bot123:abc/sendVideo").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_video(video, bot_token="123:abc", chat_id="42")

    assert route.called


@respx.mock
def test_send_message_success():
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_message("hello", bot_token="123:abc", chat_id="42")

    assert route.called
