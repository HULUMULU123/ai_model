from gen.telegram_entry import parse_message


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


def test_parse_message_strips_whitespace():
    format_, brief = parse_message("  сцена на пляже  ")

    assert format_ == "photo"
    assert brief == "сцена на пляже"
