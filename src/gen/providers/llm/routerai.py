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

from gen.core.errors import ProviderError
from gen.providers.base import LLMProvider, SchemaT


class RouterAILLMProvider(LLMProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        if not api_key:
            raise ProviderError("ROUTERAI_API_KEY не задан")
        self._client = ChatOpenAI(base_url=base_url, api_key=api_key, model=model)

    def generate_structured(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        structured_client = self._client.with_structured_output(schema)
        result = structured_client.invoke(prompt)
        if not isinstance(result, schema):
            raise ProviderError(f"LLM вернул неожиданный тип результата: {type(result)!r}")
        return result
