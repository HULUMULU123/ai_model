"""Детерминированный мок LLM-провайдера для тестов (без сети)."""

from __future__ import annotations

from collections.abc import Callable

from gen.providers.base import LLMProvider, SchemaT


class MockLLMProvider(LLMProvider):
    def __init__(self, factory: Callable[[str, type], object] | None = None) -> None:
        self._factory = factory
        self.calls: list[tuple[str, type]] = []

    def generate_structured(
        self, prompt: str, schema: type[SchemaT], *, defaults: dict | None = None
    ) -> SchemaT:
        self.calls.append((prompt, schema))
        if self._factory is not None:
            result = self._factory(prompt, schema)
            assert isinstance(result, schema)
            return result
        return schema.model_construct(**(defaults or {}))

    @property
    def call_count(self) -> int:
        return len(self.calls)
