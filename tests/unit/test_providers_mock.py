import asyncio
from pathlib import Path

from pydantic import BaseModel

from gen.providers.face_embedding.mock import MockFaceEmbeddingProvider
from gen.providers.image.mock import MockImageProvider
from gen.providers.llm.mock import MockLLMProvider
from gen.providers.video.mock import MockVideoProvider


class DummySchema(BaseModel):
    text: str = "ok"


def test_mock_llm_provider_counts_calls():
    provider = MockLLMProvider(factory=lambda prompt, schema: schema(text="hi"))

    result = provider.generate_structured("бриф", DummySchema)

    assert result.text == "hi"
    assert provider.call_count == 1


def test_mock_image_provider_counts_calls_and_writes_files(tmp_path):
    provider = MockImageProvider(tmp_path)

    paths = provider.generate("сцена в кафе", n=2)

    assert len(paths) == 2
    assert all(p.is_file() for p in paths)
    assert provider.call_count == 1


def test_mock_video_provider_counts_calls_and_writes_file(tmp_path):
    provider = MockVideoProvider(tmp_path)

    path = asyncio.run(provider.generate("сцена", source_image=Path("source.png")))

    assert path.is_file()
    assert provider.call_count == 1


def test_mock_face_embedding_provider_is_deterministic(tmp_path):
    image = tmp_path / "face.png"
    image.write_bytes(b"same-bytes")
    provider = MockFaceEmbeddingProvider()

    v1 = provider.embed(image)
    v2 = provider.embed(image)

    assert v1 == v2
    assert provider.similarity(v1, v2) == 1.0
    assert provider.embed_calls == 2
    assert provider.similarity_calls == 1
