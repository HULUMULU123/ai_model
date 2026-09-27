"""Настройки инструмента, читаются только из env (см. .env.example)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    routerai_api_key: str = ""
    routerai_base_url: str = "https://api.routerai.example/v1"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    fal_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def load_settings() -> Settings:
    return Settings()
