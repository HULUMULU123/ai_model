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
| M3. Фото-генерация | ✅ готово — граф `generate` на моках, 1 генерация + макс. 1 ретрай по умолчанию |
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

### M3: фото-генерация

- Граф `generate`: `build_prompt` → `generate_one` → `qc_one` → (retry ≤ 1 раз
  по умолчанию, флаг `--retries`) → `finalize_accepted` / `finalize_low_confidence`.
- `build_prompt` — код-гард из ТЗ §4: без `PersonaContext` кидает
  `MissingPersonaContextError`; промпт собирается из `prompts/generate_photo.md`
  + `bible.md` + `wardrobe.yaml` + брифа сцены, без LLM.
- `uv run generate --brief "сцена в кафе, повседневный образ"` — 1 генерация +
  максимум 1 повтор при провале QC (embedding-сходство с canon-референсом),
  `--n`/`--retries` только явно расширяют расход.
- `--n > 1` и `--format video` пока не реализованы — явный `NotImplementedError`,
  не тихая заглушка (веер кандидатов и видео не входят в дефолт M3 по ТЗ).
- Реальный `ImageProvider` (RouterAI) — всё ещё заглушка `NotImplementedError`
  из M1: сеть на `routerai.ru` в этом окружении сейчас заблокирована политикой
  сети (403 от прокси), поэтому формат ответа медиа-эндпоинта не подтверждён
  документацией и не проверен вживую. Как только сеть откроют — доделаю
  адаптер и проверю LLM- и image-вызовы по-настоящему.
- Тесты на экономию: `tests/graph/test_generate.py` —
  `test_generate_accepts_on_first_try_without_retry` (1 генерация),
  `test_generate_retries_exactly_once_by_default` (ровно 2 генерации при
  провале QC на первой попытке), `test_generate_escalates_to_low_confidence_after_retry_limit`
  (не больше 2 генераций, даже если QC не проходит снова).

Проверить руками (без сети, на моках): `uv run pytest tests/graph/test_generate.py -v`.
