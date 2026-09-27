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
| M2. Команда init | ✅ готово — граф `init_persona` на моках, 1 LLM + 2 image-вызова по умолчанию |
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

### M2: команда init

- `uv run init-persona --brief persona/brief.md --name "Mila Novak"` — 1 вызов
  LLM (`write_character`, structured output `PersonaBible`) и ровно 2 вызова
  `ImageProvider.generate` (портрет-лист, гардероб-лист) в дефолтном режиме
  (`--variants 1`, без `--full-reference-set`). Результат: `persona/bible.md`,
  `persona/persona.yaml`, `persona/wardrobe.yaml`, `persona/canon/canon-00.*`,
  `persona/canon/canon-01.*`.
- `persona/brief.md` — заполнен лором персонажа «Mila Novak» (Сплит, гараж
  дедушки, BMW E30 «Црвена»), полученным от владельца проекта.
- Промпты вынесены в `prompts/init_character.md` (write_character),
  `prompts/canon_portrait_sheet.md`, `prompts/canon_wardrobe_sheet.md`
  (собираются без LLM из результата `write_character`).
- `qc_embedding` сравнивает портрет-лист и гардероб-лист между собой
  (embedding, без LLM); при низком сходстве не блокирует и не ретраит
  автоматически — только предупреждение в выводе CLI.
- **Известные ограничения:**
  - `--full-reference-set` пока не реализован (не входит в дефолт M2 по ТЗ) —
    флаг принимается и явно даёт `NotImplementedError`, не тихо игнорируется.
  - Реальный вызов `ImageProvider`/`FaceEmbeddingProvider` всё ещё заглушка
    (`NotImplementedError`) из M1 — без ключа RouterAI и не подтверждённого
    документацией эндпоинта команда без сети запустить нельзя; это ожидаемо
    и падает с понятной `ProviderError`, не трейсбеком.
- Тест на счётчик вызовов: `tests/graph/test_init_persona.py::test_init_persona_default_call_counts`.

Проверить руками (без сети, на моках): `uv run pytest tests/graph/test_init_persona.py -v`.
