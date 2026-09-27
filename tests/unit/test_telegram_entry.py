import json

import httpx
import respx

from gen.telegram_entry import (
    HELP_BUTTONS,
    _handle_callback_query,
    _send_help_keyboard,
    parse_message,
)


def test_parse_message_plain_text_is_photo():
    format_, brief = parse_message("сцена в кафе, повседневный образ")

    assert format_ == "photo"
    assert brief == "сцена в кафе, повседневный образ"


def test_parse_message_video_prefix_english():
    format_, brief = parse_message("video: idle at the gas station at night")

    assert format_ == "video"
    assert brief == "idle at the gas station at night"


def test_parse_message_video_prefix_russian():
    format_, brief = parse_message("видео: у гаража с Клипом")

    assert format_ == "video"
    assert brief == "у гаража с Клипом"


def test_parse_message_voice_prefix_english():
    format_, brief = parse_message("voice: Crvena update, day twelve")

    assert format_ == "voice"
    assert brief == "Crvena update, day twelve"


def test_parse_message_voice_prefix_russian():
    format_, brief = parse_message("озвучь: garage diaries, день 12")

    assert format_ == "voice"
    assert brief == "garage diaries, день 12"


def test_parse_message_strips_whitespace():
    format_, brief = parse_message("  сцена на пляже  ")

    assert format_ == "photo"
    assert brief == "сцена на пляже"


@respx.mock
def test_send_help_keyboard_includes_all_buttons():
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    _send_help_keyboard(bot_token="123:abc", chat_id="42")

    assert route.called
    body = route.calls[0].request.content
    for _, label, _ in HELP_BUTTONS:
        assert label.encode() in body


@respx.mock
def test_handle_callback_query_answers_and_sends_instruction():
    answer_route = respx.post(
        "https://api.telegram.org/bot123:abc/answerCallbackQuery"
    ).mock(return_value=httpx.Response(200, json={"ok": True, "result": True}))
    message_route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    _handle_callback_query(
        bot_token="123:abc", chat_id="42", callback_query_id="cbq1", data="help_photo"
    )

    assert answer_route.called
    assert message_route.called
    sent_body = json.loads(message_route.calls[0].request.content)
    expected_text = next(text for key, _, text in HELP_BUTTONS if key == "help_photo")
    assert sent_body["text"] == expected_text


@respx.mock
def test_handle_callback_query_unknown_data_only_answers():
    answer_route = respx.post(
        "https://api.telegram.org/bot123:abc/answerCallbackQuery"
    ).mock(return_value=httpx.Response(200, json={"ok": True, "result": True}))
    message_route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    _handle_callback_query(
        bot_token="123:abc", chat_id="42", callback_query_id="cbq1", data="unknown"
    )

    assert answer_route.called
    assert not message_route.called
