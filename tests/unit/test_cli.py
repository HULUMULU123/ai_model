from click.testing import CliRunner

from gen.cli import generate, init_persona
from gen.context.persona_context import PersonaContextError


def test_init_persona_help():
    result = CliRunner().invoke(init_persona, ["--help"])
    assert result.exit_code == 0
    assert "brief" in result.output.lower()


def test_generate_help():
    result = CliRunner().invoke(generate, ["--help"])
    assert result.exit_code == 0
    assert "brief" in result.output.lower()


def test_init_persona_requires_name():
    result = CliRunner().invoke(init_persona, [])
    assert result.exit_code != 0
    assert "--name" in result.output


def test_generate_without_persona_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(generate, ["--brief", "тестовая сцена"])
    assert result.exit_code != 0
    assert isinstance(result.exception, PersonaContextError)
