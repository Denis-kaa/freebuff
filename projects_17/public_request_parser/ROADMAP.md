# ROADMAP-PRP-001 — Public Request Parser Bot

> **Версия roadmap:** 0.2.1
> **Статус:** DRAFT — P3–P9 реализованы (offline/fixture); P10–P19: gates в `POST_MVP_GATES.md`
> **Canonical spec:** [`../../public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)
> **Шаблон:** [`../../docs_10/templates/PIPELINE_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PIPELINE_TEMPLATE.md)
> **Дата обновления:** 2026-08-23

## 0. Целевое состояние

Финальная цель проекта — не просто scraper, а устойчивый публичный продукт для поиска открытых заявок на услуги:

```text
Разрешённые источники
  → policy-aware adapters
  → нормализованные публикации
  → персональные профили поиска
  → explainable matching
  → deduplication / retention
  → Telegram delivery + management
  → multi-tenant isolation
  → feedback quality loop
  → каталог источников и observability
  → production v1.0
```

Финальный продукт должен позволять пользователю:

1. зарегистрироваться и создать профиль услуги;
2. выбрать проверенные источники или добавить разрешённый RSS/Atom URL;
3. настроить ключевые слова, синонимы, исключения и пороги;
4. получать новые релевантные открытые публикации;
5. видеть источник, ссылку и объяснение совпадения;
6. управлять статусом публикации;
7. улучшать качество поиска через feedback;
8. работать в изолированном профиле без доступа к данным других пользователей.

Финальная стадия не включает автоотклики авторам, сбор базы авторов, обход ограничений или обязательное подключение Telegram web-preview. Источник может остаться `blocked`, если нет разрешённого основания.

---

## 1. Explain-first: порядок и логика

Порядок выбран от неизвестного с максимальным риском к масштабированию:

1. Сначала доказать допустимость и техническую доступность источников.
2. Затем закрепить доменные контракты и retention/privacy boundaries.
3. Затем реализовать минимальный RSS/Atom vertical slice.
4. Затем довести Telegram-бота до полного single-tenant пользовательского сценария.
5. После MVP проверить качество на размеченной выборке и стабилизировать эксплуатацию.
6. Затем добавлять новые источники по одному, через независимые адаптеры.
7. После подтверждения модели данных включить multi-tenant isolation.
8. После накопления feedback выполнить качественный ranking/персонализацию.
9. Только после field-level evidence оценить интеграцию с Lead Aggregator и платформенный shared layer.
10. Завершить public beta, security/privacy review, операционным runbook и production v1.0.

Причины:

- Публичный URL не означает разрешённую автоматическую агрегацию.
- MVP должен подтвердить полезность и качество, а не только факт загрузки страниц.
- Multi-tenant и новые источники до стабилизации доменной модели создают лишний blast radius.
- Lead Aggregator имеет другую доменную семантику и не должен поглощать универсальный parser без contract evidence.

---

## 2. Полная карта этапов

| ID | Стадия | Статус | Результат | Выходной gate |
|---|---|---|---|---|
| P0 | Interview + canonical spec | ✅ Done | Зафиксированы цель, ограничения и открытые вопросы | Пользовательские решения записаны |
| P1 | Project scaffold | ✅ Done | Каркас sibling-проекта и ADR | Документы и границы существуют |
| P2 | Source/policy research | ✅ Done (conditional) | Матрица создана; первый production `allowed` source выбран — HeadHunter API (SRC-011, ADR-011), evidence: developer agreement + OpenAPI | G2 закрыт условно (активация: приложение + API-ключ + canary) |
| P3 | Domain contracts | ✅ Done | Typed Publication/Profile/Decision/Policy/Retention + adapter/storage/delivery ports | Contract tests green; G3 closed |
| P4 | RSS/Atom engine | ✅ Done (offline fixture) | Парсинг, нормализация, dedup, checkpoint на fixtures | Fixture suite green; live transport отдельно |
| P5 | Matching and explainability | ✅ Done | Правила, синонимы, exclusions, thresholds, intent gate, pending | Decision contract green; 14 tests |
| P6 | Storage and retention | ✅ Done | SQLite/WAL, schema v1, TTL cleanup, idempotency | Retention tests green; 14 tests |
| P7 | Telegram delivery | ✅ Done (contract-only) | HTML-карточки, dry-run, идемпотентная доставка, retry после failed | Delivery contract green; 11 tests |
| P8 | Single-tenant bot MVP | ✅ Done (offline slice) | Pipeline + CLI: fixture→match→SQLite→dry-run | 76+ проектных тестов; G5 зависит от live source |
| P9 | Telegram technical adapter | ✅ Done (fixture-only) | `tgpreview` adapter; live allowed запрещён | No live access without gate |
| P10 | MVP pilot | 🟡 Ready (активация) | Первый allowed source выбран (HH API); нужен API-ключ + canary | Pilot metrics collected |
| P11 | MVP hardening | 🟡 Partial | backup/maintenance; scheduler/runbook после pilot | Operational readiness |
| P12 | Source expansion | 🟡 Partial | HttpFeedAdapter (двойной гейт allowed+can_poll) | Each source independently gated |
| P13 | Multi-tenant foundation | 🟡 Partial | Schema v2 owner-isolated profiles; auth/quotas pending | Isolation tests green |
| P14 | Quality feedback loop | ✅ Made-ready | Feedback store + stats + детерминированный calibrator (accuracy); apply вручную через новую версию профиля | Калибровка на pilot-данных (G10) |
| P15 | Lead Aggregator integration review | ✅ Done | ADR-008: remain separate (evidence-based) | ADR accepted |
| P16 | Platformization | 🔷 Recorded | ADR-009: deferred до live-use evidence; кандидаты зафиксированы | — |
| P17 | Public beta | 🔴 Blocked (G2/G9) | Требует approved sources и multi-user auth | Beta exit metrics met |
| P18 | Production v1.0 | 🔴 Blocked | Все закрытые gates G2/G6/G7/G9/G13/G14 | Production DoD complete |
| P19 | Continuous evolution | 🔲 Ongoing | New sources, policy updates, quality releases | Every change gated and reversible |

---

## 3. Scope и границы

### Входит в целевую систему

- RSS/Atom first adapter;
- official API/RSS adapters where documented and approved;
- conditional Telegram technical adapter with fixtures;
- source policy matrix and reversible enable/disable;
- normalized `Publication`;
- personal `SearchProfile`;
- exact/rules/synonyms/negative matching;
- accept/pending/reject thresholds;
- explainable `MatchDecision`;
- source-aware deduplication;
- SQLite/WAL, checkpoints and configurable text TTL;
- Telegram bot control plane and delivery;
- single-tenant MVP;
- later multi-tenant isolation;
- quality feedback and source health;
- future adapter/catalog integration with the platform.

### Явно не входит на всех стадиях

- автоотклики, массовые сообщения и комментарии авторам;
- база авторов, профили пользователей источников и контактные досье;
- обход captcha, blocks, paywall, robots, ToS или rate limits;
- приватные чаты и закрытые источники без отдельного approved contract;
- бессрочное хранение полного текста по умолчанию;
- обязательное использование LLM;
- обучение/валидация/benchmarking AI/ML-моделей на Telegram-контенте;
- автоматическое превращение каждой найденной публикации в коммерческий lead;
- переписывание `projects_17/lead_aggregator` без отдельного ADR;
- гарантия доступности конкретной площадки, если её policy не позволяет работу.

---

## 4. Capability-check

| Возможность | Статус среды | Решение |
|---|---|---|
| Python 3.11+ | ✅ | основной стек |
| SQLite/WAL | ✅ stdlib | storage v1 |
| httpx | ✅ workspace baseline | HTTP transport |
| BeautifulSoup4 | ✅ workspace baseline | HTML/fixture parsing |
| PyYAML | ✅ workspace baseline | declarative profiles/config |
| pytest/pytest-asyncio | ✅ | hermetic and async tests |
| Telegram Bot API library | ✅ workspace dependency | delivery layer |
| Telethon/public Telegram reading | ⚠️ technical precedent, policy conditional | fixture-only until approval |
| Official VK API | ⚠️ credentials and source decision needed | future adapter |
| PostgreSQL/Redis | not needed for MVP | post-MVP scale option |
| LLM scoring | not required | optional after feedback evidence |
| Web UI | not required for MVP | optional public beta surface |

---

## 5. Sequential gates

```text
P0 spec
  → G0: product decisions and exclusions recorded
P1 scaffold
  → G1: project container, ADR, runnable/checklist exist
P2 source/policy research
  → G2: at least one source = allowed → ✅ closed conditional 2026-08-23 (HH API, ADR-011); live polling disabled until key + canary
P3 domain contracts
  → G3: Publication/Profile/Decision/Retention ownership defined
P4-P7 engine slices
  → G4: parser, matcher, storage, delivery tests green
P8 single-tenant MVP
  → G5: end-to-end user journey green
P10 pilot
  → G6: real sample, quality baseline, no policy incidents
P11 hardening
  → G7: recovery, observability, security and retention ready
P12 source expansion
  → G8: every adapter independently approved and reversible
P13 multi-tenant
  → G9: isolation, auth, quotas and migration tested
P14 feedback loop
  → G10: measurable quality improvement without opaque decisions
P15 integration review
  → G11: Parser/Lead contracts compared and ADR decision recorded
P16 platformization
  → G12: external adapter/plugin boundary validated
P17 public beta
  → G13: beta reliability, privacy and support runbook ready
P18 production v1.0
  → G14: production DoD complete
P19 evolution
  → each release has policy, migration, tests and rollback evidence
```

---

## 6. Этапы до MVP

> P3–P9 завершены (offline/fixture). P10–P19 детализированы в `POST_MVP_GATES.md`; G2 (approved live source) закрыт условно (HeadHunter API, ADR-011) — осталась активация ключа и canary.

### P2 — Source/policy research

**Цель:** выбрать первый реально разрешённый и технически доступный источник.

**Работы:**

- составить source catalog: RSS/Atom, Telegram, VK, форумы, сайты объявлений;
- для каждого источника записать owner, URL, access mode, official docs, ToS, robots, rate limits, credentials, allowed fields, retention constraints;
- классифицировать источник: `allowed`, `conditional`, `blocked`, `manual_review`;
- выбрать один RSS/Atom feed для first live canary;
- определить default/max TTL и минимальные metadata;
- зафиксировать безопасный User-Agent и polling floor.

**Артефакты:** `SOURCE_POLICY_MATRIX.md`, source fixture set, ADR при спорном решении.

**Acceptance:** первый источник имеет evidence и статус `allowed`; Telegram не включён автоматически.

### P3 — Domain contracts

**Цель:** формально отделить предметные сущности и ownership.

**Контракты:**

- `Publication`;
- `SearchProfile`;
- `MatchDecision`;
- `SourceAdapter`;
- `CheckpointStore`;
- `RetentionPolicy`;
- `Delivery`;
- `SourcePolicy`.

**Acceptance:**

- нет обязательной модели автора;
- owner scope формализован;
- `profile_version` и matched rules обязательны для decision;
- TTL не может быть ослаблен настройкой пользователя против более строгой source policy;
- ошибки нормализованы и не смешаны с domain rejection.

### P3 completion — Domain contracts

**Что сделано:**

- Создан project-local typed слой `app/domain/contracts.py` без сетевых вызовов.
- Добавлены `SourceItem`, `Publication`, `SearchProfile`, `MatchDecision`, `SourcePolicy`, `RetentionPolicy` и `DeliveryAttempt`.
- Добавлены Protocol-порты `SourceAdapter`, `CheckpointStore` и `Delivery`.
- Зафиксированы timezone-aware даты, source-scoped dedup key, profile snapshot,
  explainability, strict TTL и policy gate для polling/user-facing режима.
- Разделены `ContractValidationError`, `AdapterError`, domain rejection и delivery failure.

**Артефакты:** `DOMAIN_CONTRACTS.md`, `decisions/ADR-003_domain_contracts_and_error_boundaries.md`, `tests/test_domain_contracts.py`.

**Acceptance:** 10 hermetic contract tests passed; live polling и approved source status не изменены.

### P4 — RSS/Atom engine

**Работы:**

- RSS 2.x parsing;
- Atom parsing;
- `guid/id`, canonical URL, title, summary/content, dates;
- conditional requests, ETag/Last-Modified при поддержке;
- tolerant parsing и controlled warnings;
- source checkpoint/resume;
- bounded batches и graceful shutdown.

**Acceptance:** fixture tests для валидных, неполных и повреждённых feeds; повторный запуск не создаёт дубли.

### P4 completion — RSS/Atom fixture engine

**Что сделано:**

- Реализован `app/rss_atom/engine.py`: RSS 2.x и Atom 1.0 parsing на stdlib `xml.etree` без сети.
- Добавлены namespace-aware local-name обработка, RFC 2822/ISO-8601 даты с приведением к UTC и controlled `FeedWarning` для пропущенных URL/title и невалидных optional dates.
- Добавлены `normalize_source_item` (текст с cap), `deduplicate_publications` (source-scoped key + canonical URL).
- Добавлены `FixtureFeedAdapter` и `InMemoryCheckpointStore` с bounded batch и checkpoint resume.
- Фикстура adapter отвергает policy со статусом `allowed`, чтобы не превращаться в незаметный live transport.
- Добавлены synthetic fixtures `fixtures/rss/` и `fixtures/atom/`; 8 hermetic tests.

**Артефакты:** `RSS_ATOM_ENGINE.md`, `decisions/ADR-004_rss_atom_fixture_engine.md`, `tests/test_rss_atom.py`.

**Acceptance:** `pytest` 8 passed; `mypy --strict` для engine + tests без замечаний; live polling и credentials не менялись; ETag/Last-Modified, HTTP transport, SQLite persistence и scheduler остаются задачами P6/P11.

### P5 — Matching and explainability

**Работы:**

- exact phrases;
- required/optional terms;
- synonyms and word forms;
- stopwords and negative rules;
- intent rules «ищет услугу» против «предлагает услугу»;
- accept/pending/reject thresholds;
- decision explanation;
- profile versioning.

**Acceptance:** для каждой decision воспроизводимы profile snapshot, matched terms, rejected rules и reason.

### P5 completion — Deterministic matcher

**Что сделано:**

- Реализован `app/matcher/engine.py`: `RuleMatcher` поверх контрактов P3.
- Word-form доступ по префиксу (>= 4 символа), точные фразы скользящим окном.
- Жёсткие REJECT со score 0: excluded term, missing required, offer-wording без intent, пустой профиль.
- Intent gate: `OFFER_MARKERS` различают «ищет услугу» и «предлагает услугу».
- Score = mean(ratio required/optional/synonyms) × 0.9 + 0.1 за intent, cap 1.0; stopwords не загрязняют знаменатель.
- Каждый decision несёт profile snapshot, matched/rejected terms и reasons.
- Добавлены 14 hermetic tests (`tests/test_matcher.py`) и ADR-005.

**Артефакты:** `MATCHING_ENGINE.md`, `decisions/ADR-005_deterministic_matcher_and_intent_gate.md`, `tests/test_matcher.py`.

**Acceptance:** `pytest` 32 passed (10 contracts + 8 RSS/Atom + 14 matcher); `mypy --strict` без замечаний; G2 остаётся открытым; LLM-scoring отложен до P14.

### P6 — Storage and retention

**Работы:**

- SQLite schema и WAL;
- publications, source state, profiles, decisions, delivery attempts;
- atomic writes;
- text TTL cleanup;
- dedup indexes;
- migration/version table;
- recovery after interruption.

**Acceptance:** текст удаляется после TTL, metadata/decision остаются только в разрешённом объёме; cleanup идемпотентен.

### P6 completion — SQLite/WAL storage

**Что сделано:**

- Реализован `app/storage/sqlite.py`: `SqliteStorage` (WAL, FK, busy_timeout) + `SqliteCheckpointStore` (async порт P3).
- Схема v1 через `PRAGMA user_version`: `publications` (UNIQUE item_key + canonical_url, `text_expires_at`), `checkpoints`, `decisions` (UNIQUE pk+profile+version), `delivery_attempts` (FK, каскад).
- Атомарные идемпотентные writes: `INSERT OR IGNORE` для publications/decisions/delivery, checkpoint upsert.
- `expire_full_text()` обнуляет только истёкший `content`; строка/metadata/decisions остаются; повторный вызов возвращает 0.
- Cap текста и запрет текста (`allow_full_text=False`) применяются на уровне хранилища.
- Добавлены 14 hermetic tests: WAL/user_version, dedup по ключу и URL, roundtrip, TTL (истёк/не истёк/без TTL/запрет текста/cap), checkpoint upsert, decision idempotency и каскад, delivery idempotency, async-контракт, persistence между соединениями.

**Артефакты:** `STORAGE.md`, `decisions/ADR-006_sqlite_wal_storage_and_retention.md`, `tests/test_storage_sqlite.py`.

**Acceptance:** `pytest` 50 passed (10 contracts + 8 RSS/Atom + 14 matcher + 4 integration + 14 storage); `mypy --strict` без замечаний; G2 остаётся открытым; multi-tenant isolation и backup/restore остаются P13/P11.

### P7 — Telegram delivery

**Работы:**

- card renderer с HTML escaping;
- configurable card template;
- dry-run delivery;
- retry/backoff;
- idempotent delivery key;
- buttons: source, viewed, relevant, irrelevant, archive;
- delivery failure state.

**Acceptance:** ошибка доставки не теряет publication/decision; повтор доставки не создаёт лишние карточки.

### P7 completion — Delivery contract

**Что сделано:**

- Реализован `app/delivery/`: `render_card()` (HTML-escape, без Markdown, без полей автора), `MessageTransport` Protocol, `TelegramDelivery`.
- Идемпотентный ключ `owner:item_key:p{version***REMOVED***`; повторная доставка возвращает сохранённый SENT и не вызывает transport.
- Dry-run по умолчанию; `SKIPPED` без сети.
- Retry после `FAILED` через `save_delivery_attempt(... replace_failed=True)` (перезапись только failed); `get_delivery_attempt` добавлен.
- Owner-гейт: scope обязан совпадать с владельцем decision; пустой scope запрещён.
- Добавлены 11 hermetic tests и ADR-007.

**Артефакты:** `DELIVERY.md`, `decisions/ADR-007_delivery_contract_and_idempotency.md`, `tests/test_delivery.py`.

**Acceptance:** `pytest` 61 passed (50 + 11 delivery); `mypy --strict` без замечаний; live Telegram transport и кнопки остаются вне P7 (policy/UX gates); G2 остаётся открытым.

### P8 — Single-tenant bot MVP

**User journey:**

```text
/start
  → создать профиль
  → добавить услугу/ключевые слова
  → выбрать approved source
  → включить profile
  → получить matching card
  → открыть source
  → изменить status
  → открыть explanation/pending
```

**MVP Definition of Done:**

- один operator/user scope;
- минимум один approved RSS/Atom source;
- end-to-end collection → match → SQLite → Telegram;
- profiles and thresholds configurable;
- text TTL works;
- no outbound to publication authors;
- fixtures and integration tests green;
- dry-run and once modes available;
- runbook/checklist updated.

**MVP не означает:** public multi-user release, широкий source catalog, Telegram live approval или production SLA.

### P9 — Telegram technical adapter

**Работы:**

- fixture-only parser contract;
- source-specific normalization;
- policy-blocked behavior;
- official fallback contract;
- no live credentials or global indexing.

**Acceptance:** adapter tests pass offline; live source remains disabled unless G2/G8-style explicit approval exists.

---

## 7. Post-MVP: P10 — Ограниченный pilot

**Цель:** проверить, что MVP полезен на реальных, но ограниченных данных.

**Scope pilot:**

- 1–3 approved RSS/Atom sources;
- 1–5 controlled profiles;
- ограниченный poll frequency;
- ручное наблюдение оператором;
- Telegram delivery only;
- без обещания public SLA.

**Работы:**

- собрать первичную размеченную выборку: relevant / irrelevant / pending;
- измерить discovered, accepted, pending, rejected, duplicates, delivery failures;
- измерить time-to-detection и time-to-delivery;
- записать реальные parser failures и policy warnings;
- собрать feedback по карточке и настройке профиля;
- проверить, какие поля публикации действительно нужны.

**Выходные артефакты:** pilot report, labelled dataset policy, issue log, updated source matrix.

**Gate G6:**

- нет policy incidents;
- нет outbound к авторам;
- нет утечек secrets или запрещённых полей;
- пользователь получает полезные карточки;
- baseline quality metrics зафиксированы;
- открытые блокеры не скрыты.

---

## 8. Post-MVP: P11 — Production hardening

**Цель:** сделать single-tenant систему устойчивой к ежедневной эксплуатации.

**Работы:**

- structured logging и event counters;
- source health dashboard/CLI;
- retry/backoff/circuit breaker tuning;
- restart recovery and checkpoint validation;
- bounded memory for large feeds;
- SQLite backup and restore;
- schema migration procedure;
- secret handling audit;
- path/config validation;
- rate-limit and policy alerting;
- dry-run, once, forever and graceful shutdown modes;
- operational runbook and incident procedure.

**Acceptance:**

- controlled interruption не теряет подтверждённый checkpoint;
- source failure не останавливает другие источники;
- duplicate delivery invariant verified;
- TTL cleanup and backup restore tested;
- health state distinguishes empty source from failed source;
- logs do not contain tokens or full text by default.

**Gate G7:** single-tenant pilot can run unattended for a defined observation window without critical incidents.

---

## 9. Post-MVP: P12 — Расширение каталога источников

Добавлять источники строго по одному. Каждый проходит тот же source/policy gate.

### P12-A — Official API/RSS sources

- подключить источник с официальным API;
- credentials scope и secret storage;
- documented rate limits;
- API error mapping;
- source-specific retention.

### P12-B — VK API, если будет approved use case

- использовать только официальный HTTPS API;
- поддержать Bearer key через secret storage;
- учитывать API version и documented limits;
- не извлекать лишние user/profile fields;
- сначала fixture + sandbox, затем canary.

### P12-C — Форумы и Q&A

- подключать только открытые страницы с разрешённым read-only режимом;
- учитывать robots/ToS;
- ограничить crawl scope известными разделами;
- не строить профиль автора вопроса;
- normalizer должен отличать вопрос/обсуждение от предложения услуги.

### P12-D — Сайты объявлений

- только public pages или official feed/API;
- проверка изменений HTML/SPA;
- per-source crawl budget;
- explicit policy status;
- reversible disable.

**Acceptance для каждого адаптера:** contract tests, fixture corpus, policy record, rate-limit test, dedup mapping, failure matrix, canary report и rollback switch.

**Telegram live status:** отдельный conditional track; он не блокирует развитие RSS/API источников и не должен автоматически становиться production dependency.

---

## 10. Post-MVP: P13 — Multi-tenant foundation

**Цель:** перейти от single-tenant к изолированным пользовательским профилям.

**Работы:**

- user identity и authentication через разрешённый Telegram bot flow;
- `owner_scope` во всех пользовательских таблицах;
- row-level isolation;
- profiles, subscriptions, results и statuses per user;
- source catalog global, source selections per user;
- per-user quotas and polling budget;
- per-user TTL within source maximum;
- per-user delivery target;
- admin/operator scope;
- data export and deletion;
- migration from single-tenant records.

**Security invariants:**

- пользователь не может читать чужой profile/result/status;
- callback/button payload не доверяется без server-side owner check;
- admin operations audited;
- tenant id не берётся только из client-controlled text;
- secrets и source credentials не видны пользователям.

**Acceptance:** isolation tests, authorization boundary tests, migration rehearsal, deletion/export tests, quota tests.

**Gate G9:** multi-tenant contracts and storage are proven; production load is not claimed until P11/P14 metrics are sufficient.

---

## 11. Post-MVP: P14 — Feedback и качество поиска

**Цель:** повысить precision и полезность выдачи, сохраняя объяснимость.

**Работы:**

- collect user actions: relevant, irrelevant, archived, pending resolved;
- separate operational status from training/analytics data;
- per-profile calibration of thresholds;
- detect noisy keywords and overbroad synonyms;
- source-specific false-positive analysis;
- duplicate cluster review;
- ranking within accepted results;
- user-controlled mute rules;
- regression dataset from approved/retained metadata;
- quality report per profile/source.

**LLM policy:**

- LLM не добавляется автоматически;
- сначала deterministic calibration;
- если LLM нужен, он подключается как optional processor;
- запрещено передавать Telegram content в модель без отдельного допустимого основания;
- каждый LLM decision имеет provenance, fallback и opt-out.

**Acceptance:**

- quality improves against P10 baseline;
- false-positive trends visible;
- no opaque automatic rejection without reason;
- feedback does not expose author database;
- profile changes remain versioned and reversible.

---

## 12. Post-MVP: P15 — Lead Aggregator integration review

**Цель:** понять, какие части parser могут стать общим ingestion layer для `lead_aggregator`.

**Работы:**

- field-level mapping `Publication → Request → Lead`;
- compare source semantics and lifecycle;
- compare dedup rules;
- compare profile vs competence profile;
- compare generic match score vs commercial score;
- compare storage ownership and retention;
- identify reusable contracts without moving code;
- run consumer compatibility fixtures;
- prepare ADR: reuse, adapter, or remain separate.

**Запрещено на этом этапе:**

- переписывать существующий `lead_aggregator`;
- удалять его адаптеры;
- смешивать commercial scoring с generic matcher;
- считать совпадение названий доказательством совместимости.

**Acceptance:** decision is evidence-backed and one of:

1. remain separate;
2. share contracts only;
3. share additive adapter/runtime;
4. migrate a bounded component with rollback.

---

## 13. Post-MVP: P16 — Platformization

**Цель:** при доказанной повторной ценности превратить устойчивые части в Workspace OS integration, не ломая автономный проект.

**Candidate reusable capabilities:**

- SourceAdapter contract;
- SourcePolicy/allowlist contract;
- Publication normalization;
- checkpoint/retention primitives;
- delivery adapter contract;
- source catalog metadata;
- health and event schema.

**Порядок:**

1. project-local implementation remains source of truth;
2. evidence report identifies genuinely reusable boundary;
3. platform capability is registered first per MissingRegistry rules if it is missing;
4. additive adapter/bridge is designed;
5. project is tested without platform import;
6. platform consumer is tested independently;
7. duplication is removed only after compatibility proof and ADR.

**Platform boundaries:**

- parser runtime remains optional to Workspace OS;
- core does not call external source directly;
- integration goes through explicit adapter/bridge contract;
- events are observable;
- no direct Scenario → Forge call is introduced;
- removing the plugin/consumer does not break the standalone project.

**Acceptance:** plugin/bridge contract validation, standalone regression, platform consumer tests, event observability and migration/rollback plan.

---

## 14. Post-MVP: P17 — Public beta

**Цель:** ограниченный multi-tenant запуск для приглашённых пользователей.

**Scope:**

- approved source catalog only;
- self-service profile setup;
- Telegram bot as primary interface;
- documented quotas;
- support channel and incident response;
- no user-added arbitrary sources unless they pass automated and manual policy checks.

**Работы:**

- onboarding and consent/notice screens;
- privacy/data retention notice;
- account deletion and export;
- source status UX;
- abuse/rate-limit protection;
- operator moderation of source catalog;
- beta telemetry with minimised content;
- migration and rollback drills;
- load test with synthetic fixtures.

**Beta exit criteria:**

- tenant isolation has zero known critical findings;
- no secret exposure;
- no unbounded text retention;
- source disable switch tested;
- delivery reliability and latency within defined targets;
- feedback loop produces actionable quality changes;
- support runbook and incident escalation tested;
- no source is enabled without policy record.

---

## 15. Final stage: P18 — Production v1.0

Production v1.0 means a stable, supportable public service, not merely a working script.

### 15.1. Product completeness

- user registration and isolated profile;
- source catalog with statuses;
- profile editor;
- keyword/synonym/negative rules;
- thresholds and pending queue;
- explainable cards;
- statuses and archive;
- source health;
- retention controls;
- export/delete flow;
- admin controls;
- documented limitations.

### 15.2. Source readiness

- at least one stable approved source in production;
- every additional source independently gated;
- source-level rate limits and disable switch;
- fixture corpus and canary verification;
- no dependency on a source whose policy status is unknown;
- Telegram remains optional/conditional unless separately approved.

### 15.3. Reliability

- graceful restart and checkpoint recovery;
- idempotent storage and delivery;
- backup/restore procedure;
- schema migration procedure;
- bounded resource usage;
- alerts for source failures, rate limits, delivery failures and retention cleanup failures;
- defined operational targets for detection latency and delivery latency.

### 15.4. Security/privacy

- tenant isolation test suite;
- secret management audit;
- minimal metadata policy;
- TTL enforcement evidence;
- no author database;
- no outbound author contact;
- no prohibited source access;
- audit trail for policy and admin actions;
- documented data deletion behavior.

### 15.5. Quality

- labelled evaluation set per source/profile family;
- target precision/recall approved from pilot evidence;
- regression suite for false positives and duplicates;
- feedback calibration procedure;
- explainability check for accepted, pending and rejected decisions;
- quality degradation alert or review trigger.

### 15.6. Documentation and operations

- README and user guide;
- source onboarding policy;
- RUNNABLE and CHECKLIST current;
- operator runbook;
- incident response;
- privacy/retention notice;
- ADR index current;
- changelog current;
- rollback and disable procedures documented.

**Final Gate G14:** production v1.0 may be declared only when product, source policy, reliability, security/privacy, quality, tests and operations all have evidence. Missing evidence remains `DRAFT`, not an implicit assumption.

---

## 16. P19 — Continuous evolution after v1.0

После production v1.0 продукт развивается отдельными релизами:

### Track A — Source lifecycle

- monitor ToS/API/robots changes;
- revalidate source policy periodically;
- pause source on uncertainty;
- update fixtures after format changes;
- maintain source compatibility matrix.

### Track B — Search quality

- analyse feedback by profile/source;
- calibrate thresholds;
- add synonyms only with evidence;
- maintain regression corpus;
- evaluate optional ranking/LLM separately.

### Track C — Product UX

- profile templates;
- import/export profiles;
- digest mode alongside real-time;
- notification quiet hours;
- saved views and filters;
- optional web dashboard only when Telegram UX is insufficient.

### Track D — Scale

- move from SQLite to a compatible external storage adapter only when measured limits require it;
- separate poll workers from bot process;
- queue-based delivery;
- rate-limit budgets per source and tenant;
- disaster recovery and multi-device sync.

### Track E — Platform integration

- version shared contracts;
- preserve standalone runtime;
- add Workspace OS plugin/bridge only when reuse is proven;
- publish events and metrics through platform contracts;
- maintain backward compatibility.

Every evolution item requires scope, policy review, tests, migration/rollback plan and updated documentation.

---

## 17. Artifact placement by stage

| Стадия | Артефакты |
|---|---|
| P2 Research | `SOURCE_POLICY_MATRIX.md`, source evidence, fixture provenance |
| P3 Contracts | `app/domain/`, contract docs, schema/ADR |
| P4-P7 MVP core | `app/adapters/`, `app/matcher/`, `app/storage/`, `app/delivery/`, tests |
| P8 MVP | `RUNNABLE.md`, `CHECKLIST.md`, MVP report, changelog |
| P10 Pilot | pilot report, labelled sample policy, issue log |
| P11 Hardening | ops runbook, backup/restore report, health report |
| P12 Sources | per-source adapter, fixtures, policy record, canary report |
| P13 Multi-tenant | auth/isolation ADR, migrations, security tests |
| P14 Quality | evaluation dataset policy, calibration report, regression fixtures |
| P15 Integration | field mapping, compatibility report, ADR |
| P16 Platformization | plugin/bridge contract, platform ADR, standalone regression |
| P17 Beta | beta runbook, privacy notice, support/incident docs |
| P18 Production | release checklist, production runbook, v1.0 changelog |
| P19 Evolution | per-release ADR/CHANGELOG/metrics/migration artifacts |

---

## 18. Risk register

| Risk | Стадия | Mitigation |
|---|---|---|
| Источник запрещает aggregation | P2+ | `blocked` state, source disable, official fallback |
| Telegram policy не допускает выбранный режим | P2/P9/P12 | fixtures only, no live dependency, separate approval |
| RSS/HTML format changes | P4/P12 | tolerant parser, fixtures, canary, health |
| False positives | P5/P10/P14 | labelled data, thresholds, pending, explainability |
| Duplicate sources | P4/P10 | source id, canonical URL, text hash, bounded clustering |
| TTL leak | P6/P11/P13 | expiry field, cleanup, test, alert |
| Tenant data leak | P13/P17 | owner scope, row-level checks, callback auth tests |
| OOM/restart | P4/P11 | bounded batches, SQLite checkpoints, graceful shutdown |
| Lead/parser semantic collision | P15 | field mapping, ADR, no blind reuse |
| Platform coupling | P16 | standalone project, explicit bridge, additive integration |
| Source catalog abuse | P13/P17 | admin approval, allowlist, quotas, policy review |
| Operational overload | P10/P11/P17 | per-source/per-tenant budgets, backoff, queueing |

---

## 19. Acceptance matrix

| Область | MVP P8 | Pilot P10 | Beta P17 | Production P18 |
|---|---:|---:|---:|---:|
| Approved sources | 1 | 1–3 | catalog | catalog with revalidation |
| Profiles | 1 operator | 1–5 controlled | isolated users | isolated users + admin |
| Delivery | Telegram | Telegram | Telegram | Telegram + documented extensions |
| Matching | deterministic | calibrated baseline | feedback-assisted | quality-controlled |
| Storage | SQLite/WAL | backup tested | migration tested | recovery and retention evidence |
| TTL | works | monitored | per source/profile | audited |
| Observability | basic logs | counters/health | alerts/runbook | operational targets |
| Security | basic secret hygiene | incident review | isolation/security review | full production review |
| Source policy | documented | rechecked | catalog governance | continuous revalidation |
| Lead Aggregator | separate | comparison optional | ADR decision | stable contract if integrated |
| Telegram web-preview | fixture-only | conditional | separately approved or blocked | optional, never implicit |

---

## 20. Definition of Done for final release

Production v1.0 is complete only when:

- [ ***REMOVED*** all P0–P18 required gates are closed;
- [ ***REMOVED*** at least one source is approved, stable and monitored;
- [ ***REMOVED*** no blocked source is silently polled;
- [ ***REMOVED*** single-tenant migration path to multi-tenant is tested;
- [ ***REMOVED*** every user result is isolated and explainable;
- [ ***REMOVED*** TTL and deletion behavior are evidenced;
- [ ***REMOVED*** duplicate delivery and restart recovery are tested;
- [ ***REMOVED*** quality targets are based on real pilot data;
- [ ***REMOVED*** security/privacy review is complete;
- [ ***REMOVED*** operator and incident runbooks are usable;
- [ ***REMOVED*** rollback/disable procedures are tested;
- [ ***REMOVED*** documentation, ADRs and changelog are synchronized;
- [ ***REMOVED*** no outbound author contact or prohibited scraping behavior exists;
- [ ***REMOVED*** final release is versioned and reproducible.

---

## 21. Current status and next action

### Completed

- [x***REMOVED*** Interview and canonical specification.
- [x***REMOVED*** Separate project scaffold.
- [x***REMOVED*** Parser vs Lead Aggregator boundary.
- [x***REMOVED*** RSS/Atom first decision.
- [x***REMOVED*** Telegram fixture-only decision.
- [x***REMOVED*** Initial ADR and policy invariants.
- [x***REMOVED*** P3 typed domain contracts and error boundaries.

### Current outcome

- [x***REMOVED*** `SOURCE_POLICY_MATRIX.md` создан.
- [x***REMOVED*** Stack Overflow Atom выбран как technical fixture candidate.
- [x***REMOVED*** DEV RSS и Reddit Atom зафиксированы как manual-review candidates.
- [x***REMOVED*** Stack Exchange API зафиксирован как conditional candidate с attribution gate.
- [x***REMOVED*** Telegram web-preview оставлен `policy_blocked`.
- [x***REMOVED*** **Production/user-facing `allowed` source утверждён условно: HeadHunter API (SRC-011) — ADR-011, evidence = developer agreement (dev.hh.ru) + OpenAPI**; live polling выключен до регистрации приложения + API-ключа + canary.
- [ ***REMOVED*** Default/max TTL не закрыты.
- [x***REMOVED*** P3 contracts review-ready; G3 закрыт.
- [x***REMOVED*** P4 RSS/Atom fixture engine реализован; 8 tests green; live polling отсутствует.
- [x***REMOVED*** P5 deterministic matcher реализован; 14 tests green; live polling отсутствует.
- [x***REMOVED*** P6 SQLite/WAL storage реализован; 14 tests green; TTL cleanup идемпотентен; live polling отсутствует.
- [x***REMOVED*** P7 delivery contract реализован; 11 tests green; live transport отсутствует.
- [x***REMOVED*** P8 offline pipeline + CLI (`--once`/`--maintenance`) реализован; идемпотентен, checkpoint-resume.
- [x***REMOVED*** P9 TG web-preview fixture adapter реализован; live allowed запрещён.
- [x***REMOVED*** P11 backup/maintenance; P12 gated HttpFeedAdapter; P13/P14 schema v2 (profiles/feedback); P15 ADR-008; P16 ADR-009.

### Next action

**G2 закрыт условно (2026-08-23, ADR-011):** первый production `allowed` источник — HeadHunter API (поиск вакансий, SRC-011). Активация: регистрация приложения на `dev.hh.ru`, API-ключ в secret storage, canary-прогон `HttpFeedAdapter`, затем P10 pilot. Live polling остаётся выключен до активации (двойной гейт `allowed` + `can_poll`).

---

## 22. Open decisions

1. ~~Первый live/user-facing источник~~ → **решён (ADR-011): HeadHunter API (SRC-011)**, условная активация; Telegram web-preview по-прежнему `policy_blocked`.
2. Default/max TTL.
3. Формула thresholds.
4. Транспорт Telegram delivery.
5. Допустимый режим Telegram web-preview.
6. Максимальный размер/частота пользовательских источников.
7. Целевые precision/recall по результатам pilot.
8. Нужен ли Web UI для public beta.
9. Решение P15: separate, shared contracts или additive shared layer.

---

## 23. Cross-links

- [`../../public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)
- [`MANIFEST.md`***REMOVED***(MANIFEST.md)
- [`README.md`***REMOVED***(README.md)
- [`STEPS.md`***REMOVED***(STEPS.md)
- [`LESSONS.md`***REMOVED***(LESSONS.md)
- [`CHECKLIST.md`***REMOVED***(CHECKLIST.md)
- [`decisions/DECISIONS.md`***REMOVED***(decisions/DECISIONS.md)
- [`decisions/ADR-001_parser_boundary_and_source_gates.md`***REMOVED***(decisions/ADR-001_parser_boundary_and_source_gates.md)
- [`../lead_aggregator/MANIFEST.md`***REMOVED***(../lead_aggregator/MANIFEST.md)
- [`../../docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md)
- [`../../docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md)
