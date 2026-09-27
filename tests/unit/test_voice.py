from gen.providers.audio.mock import MockAudioProvider
from gen.voice import generate_voice_line


def test_generate_voice_line_calls_provider_once_and_delivers(tmp_path):
    provider = MockAudioProvider(tmp_path / "generated")

    delivered = generate_voice_line(
        "Crvena update, day twelve.",
        audio_provider=provider,
        voice="Leda",
        output_root=tmp_path / "output",
    )

    assert provider.call_count == 1
    assert provider.calls[0] == ("Crvena update, day twelve.", "Leda")
    assert delivered.is_file()
    assert (delivered.parent / "meta.json").is_file()


def test_generate_voice_line_uses_requested_response_format(tmp_path):
    provider = MockAudioProvider(tmp_path / "generated")

    delivered = generate_voice_line(
        "test",
        audio_provider=provider,
        voice="Leda",
        response_format="opus",
        output_root=tmp_path / "output",
    )

    assert delivered.suffix == ".opus"


def test_mock_audio_provider_writes_distinct_files(tmp_path):
    provider = MockAudioProvider(tmp_path)

    p1 = provider.generate("a", voice="Leda")
    p2 = provider.generate("b", voice="Leda")

    assert p1 != p2
    assert p1.is_file()
    assert p2.is_file()
