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
| M4. Пост-обработка и доставка (фото) | ✅ готово — апскейл/кроп, compliance-развилка, доставка в `output/<timestamp>/` |
| M5. Видео-генерация | ✅ готово — граф `generate` переиспользован для video, ffmpeg-обработка |

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

### Правка после ТЗ v4.0 (§3.1): модели теперь только из конфига

ТЗ обновилось (v4.0, приложен лор персонажа + раздел 3.1 с конкретными ID
моделей RouterAI) и явно требует: выбор модели — только через
`persona.yaml`/`models.yaml`, никогда хардкодом в коде. До этой правки
`run.py` графов `init_persona`/`generate` хардкодили `model="gpt-4o-mini"` /
`model="default"` — это было ошибкой ещё в M1-M3, исправлено сейчас:

- `models.yaml` (корень репозитория) — какая модель на какую задачу
  (`write_character`, `photo`, `video`), с тиром `default`/`quality`. ID и
  цены — из таблицы ТЗ §3.1 на 27.09.2026, **не проверены** по актуальному
  каталогу `routerai.ru/models` (сеть на этот хост заблокирована политикой
  окружения) — использовать как отправную точку, не как гарантированно
  рабочие ID.
- `src/gen/core/models_config.py` — `load_models_config()`/`resolve_model()`,
  путь настраивается через `MODELS_CONFIG_PATH`.
- `run_init_persona`/`run_generate` теперь берут модель через
  `resolve_model(config, "write_character")` / `resolve_model(config, "photo", tier=...)`.
- `generate --quality` — явный флаг для тира `quality` (более дорогая модель),
  по умолчанию `default` — соответствует принципу "расширение расхода только
  по флагу".
- Тест: `tests/unit/test_models_config.py`.

### M4: пост-обработка и доставка (фото)

- Граф `generate` расширен: `finalize_accepted`/`finalize_low_confidence` →
  `post_process` (апскейл + кроп) → `compliance_check` → развилка
  `deliver`/`reject`.
- `src/gen/postprocess/image.py` — `upscale()` (Pillow LANCZOS-ресемплинг до
  минимальной длинной стороны, по умолчанию 2048px) и `crop_to_aspect()`
  (центр-кроп под `4:5`/`9:16`/`1:1`). **Ограничение:** это не нейросетевой
  супер-резолюшн — такого апскейлера нет в стеке и он не подтверждён
  документацией; честный ресемплинг вместо "выдуманного" API.
- `src/gen/qc/compliance.py` — `ComplianceProvider` интерфейс +
  `NotImplementedComplianceProvider` (реальной NSFW/age-модели с подтверждённой
  документацией нет, как и для других внешних адаптеров) + мок
  `MockComplianceProvider` для тестов. При отклонении — граф идёт в `reject`,
  файл не доставляется, доп. попытки не делается (одноразовая проверка, не ретрай).
- `src/gen/delivery/local.py` — `deliver_to_output()`: копирует финальный файл
  в `output/<timestamp>/`, рядом кладёт `meta.json` (промпт, QC score,
  low_confidence) — история как файлы, без БД (ТЗ §7).
- `src/gen/delivery/telegram.py` — заглушка `NotImplementedError`; отправка в
  личный Telegram (вариант B, ТЗ §6) отложена до реальной необходимости,
  Bot API `sendPhoto` достаточно задокументирован, но не реализован в этой версии.
- `uv run generate --brief "..." --aspect 1:1` — при успехе печатает путь к
  файлу в `output/<timestamp>/`; при отклонении модерацией — печатает причину
  и не пишет файл.
- Тесты: `tests/unit/test_postprocess_image.py`, `tests/unit/test_compliance.py`,
  `tests/unit/test_delivery_local.py`, плюс в `tests/graph/test_generate.py`:
  `test_generate_delivers_upscaled_and_cropped_image`,
  `test_generate_rejected_by_compliance_is_not_delivered` (файл не создаётся,
  генерация не повторяется).
- **Известные ограничения:** реальный `ComplianceProvider` — заглушка
  (NSFW/модерационный эндпоинт не подтверждён документацией); апскейл —
  ресемплинг, не ИИ-суперрезолюшн; для видео пост-обработка (ffmpeg) — M5.

Проверить руками (без сети, на моках): `uv run pytest tests/graph/test_generate.py tests/unit/test_postprocess_image.py tests/unit/test_compliance.py tests/unit/test_delivery_local.py -v`.

### M5: видео-генерация

- Один и тот же граф `generate` обслуживает фото и видео (ТЗ §8) — ветвление
  по `state["format"]` внутри узлов, не отдельный граф:
  - `generate_one` — асинхронный узел; для `format=video` вызывает
    `VideoProvider.generate(...)` (image-to-video, polling внутри адаптера);
    поэтому граф теперь запускается через `.ainvoke()` (`run_generate`
    оборачивает это в `asyncio.run` — CLI остаётся синхронным).
  - `qc_one` — для видео вызывает `extract_frames(candidate, n=2)` (не 3–5,
    как и требует ТЗ §8) и берёт минимальное сходство среди кадров, вместо
    прямого сравнения видеофайла как изображения.
  - `post_process` — для видео вызывает `normalize_video` (ffmpeg) вместо
    апскейла/кропа.
  - `compliance_check` — для видео проверяет 1 извлечённый кадр (реальной
    видео-модерации нет и не подтверждена документацией, как и NSFW-фото).
- `src/gen/postprocess/video.py` — `extract_frames`/`normalize_video` через
  `subprocess` + `ffmpeg`/`ffprobe` (документированный CLI, не выдуманный
  HTTP API). Если ffmpeg не установлен — `FfmpegNotFoundError`, а не тихий
  no-op.
- **В этом окружении `ffmpeg` не установлен** — тесты на реальную видео-
  обработку (`tests/unit/test_postprocess_video.py`) помечены
  `skipif(not ffmpeg)` и корректно скипаются (2 skipped), а не притворяются
  зелёными. Граф-уровневый тест видео-ветки (`tests/graph/test_generate.py::test_generate_video_uses_video_provider_and_two_qc_frames`)
  использует моки/monkeypatch на уровне узлов, чтобы проверить связность
  графа и экономию (ровно 2 кадра на QC, 1 на compliance) без ffmpeg.
- Реальный `VideoProvider` (RouterAI/fal.ai image-to-video) — по-прежнему
  заглушка `NotImplementedError` из M1: эндпоинт не подтверждён документацией,
  и сеть на `routerai.ru` в этом окружении заблокирована политикой сети.
- `AsyncPostgresSaver` сознательно не подключён — ТЗ прямо говорит не
  усложнять с БД-чекпоинтами, пока нет реальной необходимости в надёжности
  длинных генераций; `InMemorySaver` остаётся дефолтом.

Проверить руками: `uv run pytest` (все тесты без сети; 2 теста на ffmpeg
скипаются в окружениях без ffmpeg — установи `ffmpeg`, чтобы прогнать их).

### Реальные адаптеры RouterAI (после открытия сети на `routerai.ru`)

Сеть на `routerai.ru` открыли — проверил реальные эндпоинты вживую и заменил
часть `NotImplementedError`-заглушек на рабочий код:

- **LLM (`write_character`)** — работает как и раньше (M1), реальный вызов
  `anthropic/claude-sonnet-5` через `write_character` подтверждён вживую.
- **Изображения (`RouterAIImageProvider`)** — реализован и подтверждён вживую:
  `POST /api/v1/images/generations` (OpenAI-совместимый, через `openai`
  Python SDK), референсы лица передаются через `input_references` —
  RouterAI-специфичное расширение формата `[{"type": "image_url",
  "image_url": {"url": "data:image/png;base64,..."}}]` (формат подтверждён
  ошибкой валидации API на неверном формате и успешным HTTP 200 на верном).
  Полный прогон `init-persona` до `generate_canon_batch` включительно —
  реальный вызов LLM + 2 реальных генерации изображений — отработал.
- **Видео (`RouterAIVideoProvider`)** — реализован через прямые HTTP-запросы
  (`httpx`, не `openai` SDK — его `videos.create` шлёт multipart в формате
  OpenAI Sora API, а RouterAI ждёt обычный JSON и отвечает `400 Invalid
  JSON format` на multipart). `POST /api/v1/videos` с
  `{model, prompt, image: data-uri, size, duration}` подтверждён
  структурированной ошибкой `402 Insufficient balance` с точной оценкой
  стоимости (значит поля валидны) — сам факт успешной генерации и точная
  форма ответа `GET /videos/{id}` при `status=completed` **не проверены**:
  на аккаунте не хватило баланса даже на самый дешёвый вариант (46→40 RUB
  доступно, нужно ≥65.79 RUB за 480p/5с). Реализация — лучшее предположение
  по общей конвенции (`status`, `video_url`/`url`), с явным `ProviderError`
  вместо тихого падения, если поля не совпадут. Поправить после первого
  реального успешного прогона (нужно пополнить баланс).
- `models.yaml` — ID моделей из ТЗ §3.1 подтверждены существующими в
  каталоге на 27.09.2026 (`anthropic/claude-sonnet-5`,
  `bytedance-seed/seedream-4.5`, `black-forest-labs/flux.2-pro`,
  `alibaba/wan-2.6`, `bytedance/seedance-2.0`, `deepseek/deepseek-v4-pro-0813`).
- Добавлены явные зависимости `openai`, `httpx` в `pyproject.toml` (ранее
  использовались только транзитивно через `langchain-openai`).

### Сходство лица: локальный InsightFace (закрыт открытый вопрос ТЗ §11)

В каталоге `routerai.ru/models` нет специализированной face-recognition
модели — только общие мультимодальные text/image-эмбеддинги, которые эмбеддят
всё изображение целиком, а не лицо. Решение: локальный пакет `insightface`
(модель `buffalo_l`, ArcFace-эмбеддинги 512-d), без внешнего API — только
разовая загрузка весов (~280 МБ) с `github.com/deepinsight/insightface` при
первом запуске, дальше офлайн из `~/.insightface/models/`.

- `src/gen/providers/face_embedding/insightface.py` — реальный адаптер:
  `FaceAnalysis(name="buffalo_l").get(image)` → `face.normed_embedding`
  (L2-нормированный вектор, косинусное сходство = скалярное произведение,
  ремаппится в `[0, 1]`). Если лицо не найдено на кадре — `ProviderError`,
  а не тихий возврат нулевого вектора.
- **Порог `QC_SIMILARITY_THRESHOLD` откалиброван вживую** на реальных
  генерациях RouterAI: идентичное изображение → 1.0, одно и то же лицо на
  разных позах (генерация по референсу) → 0.88, разные люди → 0.66. Прежний
  порог 0.5 (унаследован от моков в M2/M3, до появления реального адаптера)
  пропускал бы разных людей — поднят до **0.75** в обоих графах
  (`init_persona` и `generate`).
- Тест `tests/unit/test_insightface_provider.py` — на реальном пакете,
  скипается, если `insightface` недоступен в окружении.

### Итог первого прогона и смена модели изображений (мультяшность/артефакты)

Первый полный прогон `init-persona` (1 LLM-вызов + 2 генерации на
`bytedance-seed/seedream-4.5`) отработал до конца, но результат оказался
непригоден: мультяшный, "пластиковый" вид, артефакты — не то, что нужно для
фотореалистичного персонажа. По итогам разбора заменил дефолтную фотомодель
в `models.yaml` на **`openai/gpt-image-2`** — тот же контракт эндпоинта
(`POST /images/generations`, `input_references`), правки адаптера не
понадобились. Сравнение вживую 27.09.2026: `gpt-image-2` даёт фотореалистичный
результат без мультяшности, консистентность лица через `input_references`
подтверждена на двух последовательных генерациях. Заодно рассмотрел `nano-
banana`/Gemini-image — она отвечает через chat-completions с мультимодальным
выводом, а не через `images/generations`, так что переход на неё потребовал
бы отдельного адаптера; отложено, `gpt-image-2` уже решает проблему без
переделки контракта.

Заодно поправил `build_prompt`/промпты изображений: раньше в промпт кадра
уходил **весь** `bible.md` целиком (включая биографию и голос — нерелевантный
для картинки текст, который разбавлял описание внешности). Добавил
`PersonaContext.bible_section(heading)` — вырезает конкретный `## ` раздел
(`Внешность`, `Сигнатурные детали`, `Чего не делать`), промпт теперь собирает
только визуально релевантные части + анти-мультяшный негатив
(`illustration, cartoon, anime, 3d render, cgi, doll-like face, airbrushed/
plastic/waxy skin`) во всех трёх шаблонах (`generate_photo.md`,
`canon_portrait_sheet.md`, `canon_wardrobe_sheet.md`).

**Повторный прогон `init-persona` не завершён** — баланс аккаунта RouterAI
ушёл в минус (-7.17 ₽) на второй из двух генераций (портрет-лист прошёл,
гардеробный — нет). `persona/bible.md` и предыдущие (некачественные)
canon-файлы удалены из репозитория, `persona/` сейчас в состоянии "ещё не
инициализирован" — пополните баланс и попросите повторить `init-persona`,
чтобы получить финальный набор на `gpt-image-2`.

## Telegram-бот (вариант B, ТЗ §6) и проверка готовности к вертикальному контенту

### Telegram-бот

`uv run telegram-bot` — личный бот, тот же граф `generate`, что и CLI, без
карточек одобрения и без ролей:

- Long polling через `getUpdates` (документированный Telegram Bot API,
  https://core.telegram.org/bots/api) — не вебхук, не отдельный сервер.
- Обычный текст → бриф на фото (`--aspect 9:16`, вертикаль под
  Reels/Stories/Threads по умолчанию); префикс `video:`/`видео:` → бриф на
  видео.
- `TELEGRAM_CHAT_ID` не задан → бот только логирует `chat_id` первого
  написавшего в консоль и не отвечает (защита "для себя" — не выполняет
  команды от случайных людей). Задан → отвечает только этому `chat_id`.
- `/start` или `/help` → инлайн-клавиатура (`InlineKeyboardMarkup`) с тремя
  кнопками («📷 Фото», «🎬 Видео», «❓ Как это работает») — нажатие не
  запускает генерацию, только присылает короткую инструкцию по формату
  команды (`answerCallbackQuery` + `sendMessage`, без незакрытых "часиков" у
  кнопки в клиенте).
- `src/gen/delivery/telegram.py` — `send_photo`/`send_video`/`send_message`
  (с опциональной инлайн-клавиатурой)/`answer_callback_query` через прямой
  HTTP к Bot API, без сторонних SDK.
- **Проверено вживую 27.09.2026:** реальный бот (`@dream_team_ai_models_bot`)
  запущен, получил `/start` и текстовое сообщение по long polling, `chat_id`
  владельца определён и записан в `.env`; `send_message` доставил и обычное
  сообщение, и сообщение с инлайн-клавиатурой в реальный чат. Реальное
  нажатие кнопки (`callback_query`) не поймано в рамках сессии — путь
  `_handle_callback_query` покрыт тестами на `respx`-моках
  (`test_handle_callback_query_answers_and_sends_instruction`). Полный раунд
  с генерацией фото/видео через бота не проверялся вживую (баланс RouterAI в
  минусе) — но `_handle_message` вызывает тот же `run_generate`, что уже
  проверен в M3-M5 и в CLI.
- Тесты: `tests/unit/test_delivery_telegram.py` (моки `respx`, без сети),
  `tests/unit/test_telegram_entry.py` (парсинг `photo`/`video:` брифов).
- Процесс — обычный `uv run`, который вы запускаете и останавливаете сами;
  не фоновый воркер фермы (ТЗ §1.1 — "никаких фоновых процессов").

### Готовность пайплайна к вертикальному контенту (Instagram/Threads)

| Что | Статус | Как |
| --- | --- | --- |
| Вертикальные фото (Reels/Stories, 9:16) | ✅ готово | `generate --aspect 9:16` (или бот по умолчанию) — кроп в `post_process` (M4), апскейл до 2048px по длинной стороне |
| Фото под фид (4:5) | ✅ готово | `generate --aspect 4:5` (дефолт CLI) |
| Квадрат (1:1, Threads/карусели) | ✅ готово | `generate --aspect 1:1` |
| Вертикальное видео (Reels, 9:16) | ✅ адаптер готов, генерация не проверена вживую | `RouterAIVideoProvider` шлёт `size="720x1280"` по умолчанию (подтверждено в каталоге `alibaba/wan-2.6`: `supported_sizes` включает `720x1280`/`1080x1920`, `supported_aspect_ratios: ["16:9","9:16"]`); реальный прогон блокирован балансом |
| Промпты по кастомному брифу | ✅ готово | `build_prompt` собирает промпт из брифа + внешности/деталей персонажа (не всей библии) — см. правку выше |
| Доставка в Telegram лично себе | ✅ готово, проверено вживую (кроме самой генерации) | `uv run telegram-bot` |

**Не готово / требует действий:** пополнить баланс RouterAI, чтобы (1)
завершить `init-persona` (гардеробный лист), (2) прогнать хотя бы одно
реальное видео целиком и подтвердить точный формат успешного ответа
`GET /videos/{id}` (сейчас — лучшее предположение с явным `ProviderError`
при расхождении, см. раздел выше).
