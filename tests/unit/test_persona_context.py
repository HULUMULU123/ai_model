from pathlib import Path

import pytest

from gen.context.persona_context import PersonaContext, PersonaContextError

FIXTURE_PERSONA_DIR = Path(__file__).parent.parent / "fixtures" / "persona"


def test_persona_context_loads_from_fixture():
    ctx = PersonaContext.load(FIXTURE_PERSONA_DIR)

    assert ctx.name == "Mila Novak"
    assert "Mila Novak" in ctx.bible_text
    assert ctx.wardrobe["everyday"] == ["серая толстовка", "джинсы"]
    assert len(ctx.canon_images) == 2
    assert all(p.is_file() for p in ctx.canon_images)


def test_persona_context_missing_dir_raises(tmp_path):
    with pytest.raises(PersonaContextError):
        PersonaContext.load(tmp_path / "does-not-exist")


def test_persona_context_missing_canon_raises(tmp_path):
    persona_dir = tmp_path / "persona"
    persona_dir.mkdir()
    (persona_dir / "bible.md").write_text("# X")
    (persona_dir / "persona.yaml").write_text("name: X")
    (persona_dir / "wardrobe.yaml").write_text("everyday: []")
    (persona_dir / "canon").mkdir()

    with pytest.raises(PersonaContextError):
        PersonaContext.load(persona_dir)
