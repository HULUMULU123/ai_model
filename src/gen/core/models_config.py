"""Загрузка выбора моделей RouterAI из `models.yaml` (см. ТЗ §3.1).

Модель для каждой задачи не хардкодится в коде — только читается отсюда.
Путь к файлу настраивается через `MODELS_CONFIG_PATH` (по умолчанию
`models.yaml` в корне репозитория).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from gen.core.errors import ContentGenError

DEFAULT_MODELS_CONFIG_PATH = Path("models.yaml")


class ModelsConfigError(ContentGenError):
    """models.yaml отсутствует или не содержит нужной задачи/тира."""


def load_models_config(path: Path | None = None) -> dict:
    config_path = path or Path(os.environ.get("MODELS_CONFIG_PATH", DEFAULT_MODELS_CONFIG_PATH))
    if not config_path.is_file():
        raise ModelsConfigError(
            f"Не найден {config_path}. Ожидается файл с выбором моделей по задачам (см. ТЗ §3.1)."
        )
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def resolve_model(config: dict, task: str, *, tier: str = "default") -> str:
    task_config = config.get(task)
    if not task_config or tier not in task_config:
        raise ModelsConfigError(f"В models.yaml нет '{task}.{tier}'.")
    return task_config[tier]


def resolve_setting(config: dict, task: str, key: str) -> str:
    """Читает произвольную настройку задачи (не тир модели), например `voice_name`."""
    task_config = config.get(task)
    if not task_config or key not in task_config:
        raise ModelsConfigError(f"В models.yaml нет '{task}.{key}'.")
    return task_config[key]
