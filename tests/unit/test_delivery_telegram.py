import httpx
import pytest
import respx

from gen.delivery.telegram import (
    TelegramDeliveryError,
    answer_callback_query,
    send_audio,
    send_message,
    send_photo,
    send_video,
    send_voice,
)


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
def test_send_voice_success(tmp_path):
    voice = tmp_path / "line.opus"
    voice.write_bytes(b"fake-voice-bytes")
    route = respx.post("https://api.telegram.org/bot123:abc/sendVoice").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_voice(voice, bot_token="123:abc", chat_id="42")

    assert route.called


@respx.mock
def test_send_audio_success(tmp_path):
    audio = tmp_path / "line.mp3"
    audio.write_bytes(b"fake-audio-bytes")
    route = respx.post("https://api.telegram.org/bot123:abc/sendAudio").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_audio(audio, bot_token="123:abc", chat_id="42")

    assert route.called


@respx.mock
def test_send_message_success():
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_message("hello", bot_token="123:abc", chat_id="42")

    assert route.called


@respx.mock
def test_send_message_with_buttons_includes_inline_keyboard():
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    send_message(
        "choose",
        bot_token="123:abc",
        chat_id="42",
        buttons=[("Photo", "help_photo"), ("Video", "help_video")],
    )

    assert route.called
    body = route.calls[0].request.content
    assert b"help_photo" in body
    assert b"help_video" in body


@respx.mock
def test_answer_callback_query_success():
    route = respx.post("https://api.telegram.org/bot123:abc/answerCallbackQuery").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": True})
    )

    answer_callback_query("cbq1", bot_token="123:abc")

    assert route.called


@respx.mock
def test_answer_callback_query_raises_on_api_error():
    respx.post("https://api.telegram.org/bot123:abc/answerCallbackQuery").mock(
        return_value=httpx.Response(400, json={"ok": False, "description": "query is too old"})
    )

    with pytest.raises(TelegramDeliveryError):
        answer_callback_query("cbq1", bot_token="123:abc")
