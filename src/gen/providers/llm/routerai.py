"""RouterAI LLM-адаптер (OpenAI-совместимый), через langchain-openai.

RouterAI предоставляет OpenAI-совместимый chat completions эндпоинт, поэтому
`ChatOpenAI(base_url=...)` подходит напрямую — см. `langchain-openai` docs
(https://python.langchain.com/docs/integrations/chat/openai/) и обычный
OpenAI-совместимый контракт `POST /chat/completions`. Точная модель и её
поддержка structured output/tool-calling должны быть проверены под конкретный
RouterAI-план перед продакшн-использованием — если модель не поддерживает
tool-calling, `with_structured_output` даст ошибку на реальном вызове, не при
импорте.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from gen.core.errors import ProviderError
from gen.providers.base import LLMProvider, SchemaT


class RouterAILLMProvider(LLMProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._client = ChatOpenAI(base_url=base_url, api_key=api_key, model=model)

    def generate_structured(
        self, prompt: str, schema: type[SchemaT], *, defaults: dict | None = None
    ) -> SchemaT:
        """Один вызов LLM.

        Подтверждено вживую 27.09.2026: даже с `method="json_schema"` (дефолт
        `with_structured_output`) модель через RouterAI может не заполнить
        обязательное поле (реальная ошибка: `PersonaBible.name` отсутствовало
        в ответе) — строгий JSON-schema режим OpenAI, судя по всему, не
        гарантируется прокси-моделью. Поэтому используем `include_raw=True` и
        сами подставляем уже известные вызывающей стороне значения (`defaults`,
        например имя персонажа) перед валидацией, вместо того чтобы тратить
        второй LLM-вызов на ретрай (это нарушило бы правило "1 LLM-вызов").
        """
        structured_client = self._client.with_structured_output(schema, include_raw=True)
        raw_result = structured_client.invoke(prompt)
        parsed = raw_result.get("parsed")
        if isinstance(parsed, schema):
            return parsed

        tool_calls = getattr(raw_result.get("raw"), "tool_calls", None) or []
        if not tool_calls:
            raise ProviderError(f"LLM не вернула структурированный результат: {raw_result!r}")
        args = dict(tool_calls[0].get("args") or {})
        for key, value in (defaults or {}).items():
            args.setdefault(key, value)
        try:
            return schema.model_validate(args)
        except ValidationError as exc:
            raise ProviderError(f"LLM вернула невалидную структуру ({exc}): {args!r}") from exc
