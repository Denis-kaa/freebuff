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
