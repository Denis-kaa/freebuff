# STEPS — project log for ROADMAP-PRP-001

> Формат: `Step N: что сделано | почему | что дальше`.
> Этот файл фиксирует только фактически выполненные действия; будущие шаги не помечаются выполненными.

## Step 1: Interview and canonical specification (2026-08-22)

**Что сделано:**

- Собран контекст Freebuff и существующего `projects_17/lead_aggregator`.
- Проверены официальные документы Telegram API/Content Licensing, VK API, RFC 9309 и Atom.
- Проведено несколько раундов уточняющих вопросов через `ask_user`.
- Создан корневой canonical spec `public-request-parser-spec.md`.

**Почему:**

- Нужно было отделить универсальный parser от прикладного Lead Aggregator.
- Доступ к открытой странице нельзя автоматически трактовать как разрешение на агрегацию.

**Что дальше:**

- Создать project-local source/policy matrix.

## Step 2: Project scaffold (2026-08-22)

**Что сделано:**

- Создан отдельный sibling-проект `projects_17/public_request_parser/`.
- Созданы MANIFEST, README, SPEC pointer, ROADMAP, STEPS, LESSONS, RUNNABLE, CHECKLIST, requirements и project.yaml.
- Зафиксировано решение: RSS/Atom — первый operational source; Telegram — technical fixture-only до approval.
- Создан project-local ADR-001.

**Почему:**

- Пользователь выбрал отдельный проект, одновременно сохранив идею будущего платформенного инструмента.
- Канон PROJECT_RULES требует project-local контекст, решения, паспорт и runnable/checklist артефакты.

**Что дальше:**

- Не писать код до закрытия source/policy gate и domain contracts.

## Step 3: Source/policy research (2026-08-23)

**Что сделано:**

- Проверены реальные технические endpoints Stack Overflow Atom, DEV RSS и Reddit Atom.
- Проверены официальные Terms/licensing/API materials Stack Overflow/Stack Exchange, Telegram, VK и RFC 9309.
- Создан `SOURCE_POLICY_MATRIX.md` с source records, evidence, allowed fields, retention и gate vocabulary.
- Stack Overflow Python Atom feed выбран как `technical_candidate` для fixtures и локального parser canary.
- Stack Exchange API отмечен как `conditional` из-за attribution, scope, quota и storage review.
- DEV RSS и Reddit Atom отмечены `manual_review`.
- Telegram web-preview оставлен `policy_blocked` для live aggregation.

**Почему:**

- Нельзя приравнивать наличие RSS/Atom URL к разрешению на user-facing агрегацию.
- Технический pipeline можно разрабатывать на fixtures, не включая live polling и не создавая ложное утверждение о product approval.

**Результат:**

- P2 = partial: source matrix готова, но G2 production `allowed` source остаётся открытым.
- P3 domain contracts и fixture-based P4 могут начинаться без live network polling.

## Step 4: Domain contracts (2026-08-23)

**Что сделано:**

- Создан `app/domain/contracts.py` с frozen typed entities и Protocol-портами.
- Зафиксированы `Publication`, `SearchProfile`, `MatchDecision`, `SourcePolicy`, `RetentionPolicy`, `SourceAdapter`, `CheckpointStore` и `Delivery`.
- Добавлены `DOMAIN_CONTRACTS.md` и ADR-003 о границах ошибок и ownership.
- Добавлены 10 hermetic contract tests; прогон `PYTHONPATH=. python -m pytest tests/ -q` завершился успешно.

**Почему:**

- P4 должен иметь стабильную доменную границу до реализации parser/storage/delivery.
- Policy rejection, adapter failure, match reject и delivery failure имеют разную семантику.
- Проект остаётся автономным и не заимствует модели `lead_aggregator` напрямую.

**Результат:**

- P3 = done, G3 закрыт.
- Live polling, credentials и статус источников не изменялись.
- Следующий этап — P4 RSS/Atom engine на fixtures.

## Step 5: RSS/Atom fixture engine (2026-08-23)

**Что сделано:**

- Реализован `app/rss_atom/engine.py`: RSS 2.x и Atom 1.0 parsing на `xml.etree.ElementTree` без сетевых вызовов.
- Добавлены namespace-aware local-name, RFC 2822/ISO-8601 даты с UTC-нормализацией, `FeedWarning` для неполных item и `AdapterError` для повреждённых документов.
- Добавлены `normalize_source_item`, `deduplicate_publications`, `FixtureFeedAdapter` и `InMemoryCheckpointStore`.
- Добавлены synthetic fixtures `fixtures/rss/sample_rss.xml` и `fixtures/atom/sample_atom.xml` без персональных данных.
- Добавлены 8 hermetic tests: RSS/Atom нормализация, categories, missing URL, malformed XML, text cap, dedup, checkpoint resume, запрет fixture adapter как live allowed transport.
- Созданы `RSS_ATOM_ENGINE.md` и ADR-004 о границе fixture engine и live transport.

**Почему:**

- Parser можно проверить на fixtures, не утверждая live source и не включая credentials.
- HTTP transport, conditional requests и polling добавляются отдельными gates (P6/P11), а не скрытой зависимостью P4.
- Найденные дефекты fixtures (отсутствие `<link>`) выявлены тестами и исправлены до документации.

**Результат:**

- P4 = done (offline fixture slice); 18 проектных тестов проходят (10 contracts + 8 RSS/Atom).
- `mypy --strict` для domain и engine без замечаний.
- G2 остаётся открытым; live polling, credentials и статус источников не изменялись.
- Следующий этап — P5 Matching and explainability.

## Step 6: Deterministic matcher (2026-08-23)

**Что сделано:**

- Реализован `app/matcher/engine.py`: `RuleMatcher(profile).match(publication)` → `MatchDecision`.
- Словесные правила + префиксный word-form доступ (>= 4 символа) + точные фразы скользящим окном.
- Жёсткие REJECT со score 0: excluded term, missing required, offer-wording без intent, пустой профиль.
- Intent gate: `OFFER_MARKERS` различают «ищет услугу» и «предлагает услугу».
- Score = mean(required/optional/synonyms ratios) × 0.9 + 0.1 за intent, cap 1.0; stopwords исключены из знаменателя optional.
- Explainable decision: profile snapshot, matched/rejected terms, reasons.
- Добавлены 14 hermetic tests; созданы `MATCHING_ENGINE.md` и ADR-005.

**Почему:**

- Первый проверил детерминированное правило на P3-контрактах: решение воспроизводимо и объяснимо без LLM.
- Граница спрос/предложение обязательна для продукта «ищу услугу»; консервативные маркеры не блокируют ambiguous текст.

**Результат:**

- P5 = done; G4 частично зелёный (parser + matcher; storage/delivery — P6/P7).
- 32 проектных теста проходят (10 contracts + 8 RSS/Atom + 14 matcher); `mypy --strict` без замечаний.
- G2 остаётся открытым; live polling, credentials и статус источников не изменялись.
- Следующий этап — P6 Storage and retention (SQLite/WAL).

## Step 7: P4→P5 integration slice (2026-08-23)

**Что сделано:**

- Добавлен `tests/test_integration_pipeline.py` (4 hermetic tests): RSS/Atom fixture → `SourceItem` → `Publication` → dedup → `RuleMatcher` → `MatchDecision`.
- Проверено: только релевантный item принимается (python+backend против designer); Atom entry без даты остаётся в pipeline (дата необязательна) и корректно отклоняется по required; async `FixtureFeedAdapter`-прогон идемпотентен; excluded-термин фильтрует шум даже при required-совпадении.

**Почему:**

- Подтверждён offline vertical slice P4→P5 до P6/P7: parser и matcher склеиваются без storage и delivery.
- Ошибочно выбранные английские intent-термины против русскоязычного профиля и умолчание `decided_at` в async-прогоне пойманы тестами и исправлены до фиксации.

**Результат:**

- 36 проектных тестов проходят (10 contracts + 8 RSS/Atom + 14 matcher + 4 integration); `mypy --strict` без замечаний (11 файлов).
- G2 остаётся открытым; следующий этап — P6 Storage and retention.

## Step 8: SQLite/WAL storage (2026-08-23)

**Что сделано:**

- Реализован `app/storage/sqlite.py`: `SqliteStorage` (WAL, FK, busy_timeout, миграции через `PRAGMA user_version`) и `SqliteCheckpointStore` (async-порт P3).
- Схема v1: `publications` (UNIQUE item_key + canonical_url, `text_expires_at`), `checkpoints`, `decisions` (UNIQUE pk+profile+version), `delivery_attempts` (FK каскад).
- Идемпотентные атомарные writes: INSERT OR IGNORE, checkpoint upsert.
- `expire_full_text()` обнуляет только истёкший content; строка/metadata/decisions остаются; идемпотентен.
- Cap текста и запрет текста применяются на уровне хранилища.
- Добавлены 14 hermetic tests и ADR-006.

**Почему:**

- SQLite/WAL даёт атомарность, индексы и идемпотентность без внешнего сервиса (MVP single-tenant).
- TTL должен удалять только временный текст, а не потерю metadata/decisions — иначе после cleanup нельзя отобразить карточку.
- `PRAGMA user_version` — единственная точка правды версии схемы; миграции forward-only.

**Результат:**

- P6 = done; часть G4 (storage) закрыта; 50 проектных тестов проходят (10+8+14+4+14).
- `mypy --strict` без замечаний (14 файлов); `git diff --check` чист.
- G2 остаётся открытым; следующий этап — P7 Telegram delivery (contract-only, без live).

## Step 9: Delivery contract (2026-08-23)

**Что сделано:**

- Реализован `app/delivery/`: `render_card()` (HTML-escape, без Markdown и полей автора), `MessageTransport` Protocol, `TelegramDelivery`.
- Идемпотентный ключ `owner:item_key:p{version***REMOVED***`: повторная доставка возвращает SENT без вызова transport.
- Dry-run по умолчанию; retry после FAILED через `replace_failed=True` в storage; `get_delivery_attempt` добавлен.
- Owner-гейт: scope обязан совпадать с владельцем decision; пустой scope запрещён.
- Добавлены 11 hermetic tests и ADR-007.

**Почему:**

- Live Telegram остаётся policy-gated (P9); доставка должна быть проверяемой без token и сети.
- Идемпотентность на уровне ключа + storage защищает от дублей и потери evidence попытки.
- HTML-escape — обязательный безопасный рендер для пользовательского контента.

**Результат:**

- P7 = done (contract-only); 61 проектный тест проходит (50 + 11 delivery).
- `mypy --strict` без замечаний (16 файлов); `git diff --check` чист.
- G2 остаётся открытым; следующий этап — P8 single-tenant MVP slice (offline pipeline glue).

## Step 10: P8–P14 implementation sprint (2026-08-23)

**Что сделано:**

- P8: `app/pipeline` (adapter→normalize→SQLite→matcher→delivery) + `app/cli` `--once`/`--maintenance`; checkpoint-resume идемпотентен (CLI smoke: 2→0 fetched, maintenance backup OK).
- P9: `app/tgpreview` — fixture web-preview адаптер; ALLOWED-policy жёстко запрещена.
- P11: `storage.backup_to()` (sqlite backup API).
- P12: `app/adapters/http_feed.py` — live только для `allowed` + `can_poll` (двойной гейт, hermetic-тесты с fake HTTP).
- P13/P14: schema v2 (`profiles` owner-scoped CRUD, `feedback` идемпотентно + stats); миграция v1→v2 сохраняет данные.

**Почему:**

- Все реализуемые офлайн-части конвейера должны быть готовы до G2, чтобы после approval осталось только подключить источник.
- Live-транспорт существует, но не может стрелять без `allowed` — инвариант проверяется тестами.

**Результат:**

- 81 проектных тестов проходят; `mypy --strict` без замечаний (25 файлов); CLI работает end-to-end.
- Коммит `e1b5c32` (P7–P14 code slice).
- P15/P16 и gates P10–P19 зафиксированы в ADR-008/009 и `POST_MVP_GATES.md`; главный блокер — G2.

## Step 11: Feedback calibration (2026-08-23)

**Что сделано:**

- Создан `app/calibration/`: `ThresholdCalibrator(storage).calibrate(profile)` → `CalibrationResult | None`.
- Выборка строится из `storage.list_feedback` + `get_decision` (score из сохранённых решений); ghost-записи без decision исключаются.
- Оптимальный порог — максимум accuracy по наблюдаемым score; pending = accept × 0.5.
- Применение не автоматическое: `changed=True` требует явного сохранения новой версии профиля.
- Добавлены 5 hermetic тестов и ADR-010.

**Почему:**

- P14 требует измеримого улучшения без opaque-решений; детерминированная рекомендация объяснима и откатываема.
- Авто-apply ломало бы объяснимость и историю версий профиля.

**Результат:**

- 86 проектных тестов проходят; `mypy --strict` без замечаний (28 файлов).
- P14 «calibration» готов как инструмент; калибровка на реальных pilot-данных — G10.

## Step 12: E2E-тест с TG-fixture (2026-08-23)

**Что сделано:**

- Добавлен `tests/test_e2e_tg_pipeline.py` (5 hermetic тестов): полный конвейер `tgpreview` → normalize → SQLite → matcher → delivery.
- Python-профиль: 3 сообщения → 1 accept («Ищу python…»), 2 reject; dry-run карточка содержит ссылку и не содержит author-полей.
- Идемпотентность повторного прогона (checkpoint → fetched=0).
- Copywriter-профиль принимает только «Нужен копирайтер».
- Design-профиль: required «дизайн» совпадает, но offer-marker без intent → REJECT через intent-gate (E2E-проверка гейта).

**Почему:**

- Сквозное (не unit) покрытие проверяет контракты между слоями: adapter→Publication→decision→card.
- Intent-gate проверяется в реальном потоке с HTTP-like сообщением, а не изолированно.

**Результат:**

- 91 проектных тестов проходят; `mypy --strict` без замечаний (29 файлов).
- E2E-покрытие конвейера завершено; следующий интеграционный шаг — CLI-режимы по профилям (после G2).
