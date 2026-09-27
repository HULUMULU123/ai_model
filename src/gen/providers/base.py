"""Абстрактные интерфейсы провайдеров. Реальные адаптеры и моки — в подпакетах."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMProvider(ABC):
    """LLM-провайдер с structured-output вызовами (без streaming/чатов)."""

    @abstractmethod
    def generate_structured(
        self, prompt: str, schema: type[SchemaT], *, defaults: dict | None = None
    ) -> SchemaT:
        """Один вызов LLM, результат провалидирован по Pydantic-схеме `schema`.

        `defaults` — значения полей, уже известные вызывающей стороне (например,
        имя персонажа из CLI/брифа): подставляются, если LLM не вернула поле.
        """


class ImageProvider(ABC):
    """Провайдер генерации изображений (с референсами лица для консистентности)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[Path] | None = None,
        n: int = 1,
    ) -> list[Path]:
        """Генерирует `n` изображений, возвращает пути к файлам."""


class VideoProvider(ABC):
    """Провайдер image-to-video генерации (асинхронно, с polling)."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        source_image: Path,
        reference_images: list[Path] | None = None,
    ) -> Path:
        """Запускает генерацию видео и дожидается результата, возвращает путь к файлу."""


class AudioProvider(ABC):
    """Провайдер синтеза речи (озвучка текста голосом персонажа)."""

    @abstractmethod
    def generate(self, text: str, *, voice: str, response_format: str = "mp3") -> Path:
        """Озвучивает `text` выбранным пресетом `voice`, возвращает путь к файлу."""


class FaceEmbeddingProvider(ABC):
    """Провайдер эмбеддингов лица для QC сходства (без LLM)."""

    @abstractmethod
    def embed(self, image: Path) -> list[float]:
        """Возвращает embedding-вектор лица на изображении."""

    @abstractmethod
    def similarity(self, a: list[float], b: list[float]) -> float:
        """Возвращает сходство двух эмбеддингов в диапазоне [0, 1]."""
