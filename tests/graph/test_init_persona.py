import uuid

import pytest

from gen.context.persona_context import PersonaBible
from gen.graph.init_persona.graph import build_init_persona_graph
from gen.graph.init_persona.nodes import NodeDeps
from gen.graph.init_persona.state import InitPersonaState
from gen.providers.face_embedding.mock import MockFaceEmbeddingProvider
from gen.providers.image.mock import MockImageProvider
from gen.providers.llm.mock import MockLLMProvider

FIXTURE_BIBLE = PersonaBible(
    name="Mila Novak",
    appearance="oval face, grey-green eyes, freckles",
    body="athletic slim build, 170cm, toned arms",
    signature_details=["gold chain with a key pendant", "scar on left eyebrow"],
    personality="confident, dry humor",
    backstory="grew up in Split, inherited a garage from her grandfather",
    voice="short phrases, croatian words like ajme",
    wardrobe={"garage": ["navy coverall", "white tank top"]},
    palette=["navy", "rust-red", "cream"],
    world={
        "pet": "sand-coloured Balkan mixed-breed dog, one ear up one ear down",
        "vehicle": "faded red two-door 1987 BMW E30, chrome bumpers",
    },
    forbidden=["plastic skin", "platinum hair"],
)


def _llm_factory(prompt, schema):
    assert "Mila Novak" in prompt
    return FIXTURE_BIBLE


@pytest.fixture
def deps(tmp_path):
    return NodeDeps(
        llm=MockLLMProvider(factory=_llm_factory),
        image_provider=MockImageProvider(tmp_path / "generated"),
        face_embedding_provider=MockFaceEmbeddingProvider(),
        persona_dir=tmp_path / "persona",
    )


def _run(deps):
    graph = build_init_persona_graph(deps)
    initial_state: InitPersonaState = {
        "brief": "24 года, Сплит, гараж дедушки, BMW E30",
        "name": "Mila Novak",
        "persona_dir": deps.persona_dir,
        "variants": 1,
        "full_reference_set": False,
    }
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return graph.invoke(initial_state, config=config)


def test_init_persona_produces_bible_and_canon_files(deps):
    result = _run(deps)

    persona_dir = deps.persona_dir
    assert (persona_dir / "bible.md").is_file()
    assert (persona_dir / "persona.yaml").is_file()
    assert (persona_dir / "wardrobe.yaml").is_file()

    bible_text = (persona_dir / "bible.md").read_text(encoding="utf-8")
    assert "Mila Novak" in bible_text
    assert "gold chain with a key pendant" in bible_text
    assert "athletic slim build" in bible_text
    assert "Balkan mixed-breed dog" in bible_text
    assert "1987 BMW E30" in bible_text

    canon_dir = persona_dir / "canon"
    canon_files = sorted(canon_dir.iterdir())
    assert len(canon_files) == 2
    assert result["canon_images"] == canon_files


def test_init_persona_default_call_counts(deps):
    _run(deps)

    assert deps.llm.call_count == 1
    assert deps.image_provider.call_count == 2


def test_init_persona_prompt_contains_wardrobe_and_signature_details(deps):
    result = _run(deps)

    assert "navy coverall" in result["wardrobe_prompt"]
    assert "gold chain with a key pendant" in result["portrait_prompt"]
    assert "gold chain with a key pendant" in result["wardrobe_prompt"]
    # body подмешивается в appearance для канон-листов (единый физический
    # образ на портрете и на гардеробе, не только лицо).
    assert "athletic slim build" in result["portrait_prompt"]
    assert "athletic slim build" in result["wardrobe_prompt"]
