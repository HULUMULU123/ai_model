# content-gen

Генератор фото/видео контента одного ИИ-персонажа. Отдаёт результат файлами —
без публикации в соцсети, без Telegram-бота с одобрениями, без движка ответов
на комментарии.

## Установка

```
uv sync --extra dev
cp .env.example .env  # заполнить ключи провайдеров
```

## Команды

```
uv run init-persona --help
uv run generate --help
```

## Тесты

```
uv run pytest
```

## Статус этапов

| Этап | Статус |
| --- | --- |
| M0. Каркас | ✅ готово — CLI-заглушки (`--help`), конфиг, логирование, ошибки |
| M1. Провайдеры и PersonaContext | ✅ готово — интерфейсы + моки + `PersonaContext.load` |
| M2. Команда init | не начато |
| M3. Фото-генерация | не начато |
| M4. Пост-обработка и доставка (фото) | не начато |
| M5. Видео-генерация | не начато |

На M0 команды `init-persona` и `generate` только парсят аргументы и печатают
`--help`; вызов без `--help` завершается `NotImplementedError` — реальная
логика графов появится на последующих этапах.

### M1: провайдеры и PersonaContext

- Интерфейсы `LLMProvider`/`ImageProvider`/`VideoProvider`/`FaceEmbeddingProvider`
  в `src/gen/providers/base.py`.
- Моки (`*/mock.py`) — детерминированные, без сети, считают число вызовов;
  пригодятся в M2/M3 для тестов на экономию.
- Реальный LLM-адаптер RouterAI (`providers/llm/routerai.py`) — через
  `langchain-openai` `ChatOpenAI`, structured output.
- Image/Video/FaceEmbedding реальные адаптеры — заглушки `NotImplementedError`
  с TODO: точные эндпоинты RouterAI/fal.ai и модель face-embedding не
  подтверждены документацией, будут уточнены и реализованы позже.
- `PersonaContext.load(persona_dir)` читает `bible.md`/`persona.yaml`/
  `wardrobe.yaml`/`canon/`; до запуска `init-persona` кидает понятную
  `PersonaContextError`, а не трейсбек.

Проверить руками: `uv run pytest` (сеть не используется).
