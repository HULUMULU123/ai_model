from pathlib import Path

import pytest

from gen.core.models_config import ModelsConfigError, load_models_config, resolve_model


def test_load_models_config_from_repo_root():
    config = load_models_config(Path("models.yaml"))

    assert "write_character" in config
    assert "photo" in config


def test_resolve_model_default_and_quality_tier():
    config = load_models_config(Path("models.yaml"))

    assert resolve_model(config, "photo") == config["photo"]["default"]
    assert resolve_model(config, "photo", tier="quality") == config["photo"]["quality"]


def test_resolve_model_missing_task_raises():
    with pytest.raises(ModelsConfigError):
        resolve_model({}, "unknown-task")


def test_load_models_config_missing_file_raises(tmp_path):
    with pytest.raises(ModelsConfigError):
        load_models_config(tmp_path / "does-not-exist.yaml")
