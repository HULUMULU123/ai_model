from gen.core.config import Settings


def test_settings_defaults_without_env(monkeypatch):
    for key in [
        "ROUTERAI_API_KEY",
        "OPENROUTER_API_KEY",
        "FAL_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.routerai_api_key == ""
    assert settings.routerai_base_url.startswith("https://")


def test_settings_reads_from_env(monkeypatch):
    monkeypatch.setenv("ROUTERAI_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.routerai_api_key == "test-key"
