from click.testing import CliRunner

from gen.cli import generate, init_persona


def test_init_persona_help():
    result = CliRunner().invoke(init_persona, ["--help"])
    assert result.exit_code == 0
    assert "brief" in result.output.lower()


def test_generate_help():
    result = CliRunner().invoke(generate, ["--help"])
    assert result.exit_code == 0
    assert "brief" in result.output.lower()


def test_init_persona_not_implemented_yet():
    result = CliRunner().invoke(init_persona, [])
    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)


def test_generate_not_implemented_yet():
    result = CliRunner().invoke(generate, ["--brief", "тестовая сцена"])
    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
