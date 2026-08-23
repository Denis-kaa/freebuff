# MANIFEST.md — Паспорт проекта `public_request_parser`

> **Slug:** `public_request_parser`
> **Версия:** 0.1.0
> **Статус:** 🟡 DRAFT — P3–P9 реализованы (offline/fixture); P10+ гated в `POST_MVP_GATES.md`
> **Дата:** 2026-08-22
> **Стек:** Python 3.11+, SQLite/WAL, RSS/Atom; Telegram adapter fixture-only до policy approval
> **Режим:** сначала single-tenant, архитектурно готов к multi-tenant
> **Связанный canonical spec:** [`../../public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)

## Назначение

Универсальный read-only парсер-бот для поиска в разрешённых открытых источниках публикаций и сообщений, где пользователи ищут услуги. Результаты нормализуются, дедуплицируются, сопоставляются с персональными профилями поиска и доставляются через Telegram-бота.

Проект не создаёт базу авторов, не выполняет автоотклики и не обходит ограничения площадок.

## Первый vertical slice

```text
RSS/Atom feed
  → policy check
  → normalized Publication
  → deterministic profile matcher
  → deduplication
  → SQLite/WAL + configurable text TTL
  → Telegram delivery contract
```

Telegram web-preview описан и тестируется только на fixtures/contract уровне до отдельного разрешения. Live-доступ не включается автоматически.

## Граница с Lead Aggregator

`public_request_parser` — универсальный сборщик и маршрутизатор публикаций для разных услуг и профилей.

`projects_17/lead_aggregator` — прикладной Attract-сценарий для исполнителя: компетенции, коммерческий scoring и жизненный цикл лида. На этой фазе проекты не объединяются и не переписываются.

## Обязательные инварианты

- read-only доступ к источникам;
- только разрешённые API/RSS/публичные маршруты;
- никакого обхода капч, блокировок, paywall и rate limits;
- никакого outbound к авторам публикаций;
- авторские поля выключены по умолчанию;
- полный текст хранится только с TTL;
- результат содержит `profile_version` и snapshot применённых правил;
- ошибки одного источника не ломают остальные;
- secrets только через environment/secret storage;
- код проекта не импортирует `core_02`, `scripts_01` или `freebuff_plugin_03` напрямую.

## Индекс документов

| Файл | Назначение |
|---|---|
| `MANIFEST.md` | Паспорт и границы |
| `README.md` | Навигация и текущий статус |
| `SPEC.md` | Указатель на canonical specification |
| `ROADMAP.md` | Этапы и gates |
| `STEPS.md` | Журнал действий |
| `LESSONS.md` | Project-local уроки |
| `RUNNABLE.md` | Запуск и ограничения |
| `CHECKLIST.md` | Pre-flight и acceptance |
| `requirements.txt` | Минимальный dependency contract |
| `project.yaml` | Метаданные Workspace/Forge |
| `SOURCE_POLICY_MATRIX.md` | Матрица источников, evidence и policy gates |
| `DOMAIN_CONTRACTS.md` | P3 typed domain/API contracts and invariants |
| `RSS_ATOM_ENGINE.md` | P4 parser/normalization/dedup/checkpoint API and boundaries |
| `MATCHING_ENGINE.md` | P5 matcher API: rules, intent gate, score formula, explainability |
| `STORAGE.md` | P6 SQLite/WAL storage: schema, idempotency, TTL cleanup, checkpoints |
| `DELIVERY.md` | P7 delivery contract: HTML cards, dry-run, idempotency, retry |
| `POST_MVP_GATES.md` | P10–P19 статусы: done/partial/blocked + evidence |
| `CALIBRATION.md` | P14 feedback→threshold calibration: детерминизм, без авто-apply |
| `decisions/` | Project-local ADR |

## Текущий статус

- [x***REMOVED*** Интервью и canonical spec созданы.
- [x***REMOVED*** Project-local каркас создан.
- [x***REMOVED*** Граница с Lead Aggregator зафиксирована.
- [x***REMOVED*** Telegram fixture-only policy зафиксирована.
- [x***REMOVED*** Research matrix источников создана; production `allowed` source пока не утверждён.
- [x***REMOVED*** P3 domain contracts и error boundaries реализованы; G3 закрыт.
- [x***REMOVED*** P4 RSS/Atom fixture engine: parser RSS 2.x/Atom 1.0, normalization, dedup, checkpoint; 8 tests green; live HTTP не включён.
- [x***REMOVED*** P5 deterministic matcher: rules, synonyms, exclusions, intent gate, thresholds, explainable decisions; 14 tests green.
- [x***REMOVED*** P6 SQLite/WAL storage: schema v1, UNIQUE dedup, идемпотентный TTL cleanup; 14 tests green.
- [x***REMOVED*** P7 delivery contract: HTML renderer, dry-run, idempotent key, retry; 11 tests green (live transport не включён).
- [x***REMOVED*** P8 offline pipeline + CLI; P9 TG fixture adapter; P11 backup; P12 gated HTTP; P13/P14 schema v2; P14 calibration; P15/P16 ADR-008/009; P14 ADR-010.
- [ ***REMOVED*** G2: первый production `allowed` source (блокер pilot/P17/P18).
- [ ***REMOVED*** Telegram Bot delivery implementation.
- [ ***REMOVED*** Live source approval.
