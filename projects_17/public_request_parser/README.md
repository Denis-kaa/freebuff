# Public Request Parser Bot

Универсальный парсер открытых публикаций, где пользователи ищут услуги.

> **Состояние:** P3–P9 реализованы (offline/fixture, 91 тест); P10+ гated — см. `POST_MVP_GATES.md`; G2 закрыт: безусловно — Open Data API «Работа в России» (SRC-012, ADR-012), условно — HeadHunter API (SRC-011, ADR-011); осталось: адаптер + canary.
> **Canonical specification:** [`../../public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)

## Что решает проект

Пользователь задаёт профиль услуги: ключевые слова, фразы, синонимы, исключения, intent-правила и пороги. Система читает только разрешённые открытые источники, находит подходящие публикации, сохраняет ссылку и технические метаданные, временно хранит текст по TTL и отправляет карточку через Telegram-бота.

## Первый источник

RSS/Atom — первый operational candidate. Он должен пройти source/policy matrix и быть подключённым только после проверки URL, условий публикации, частоты запросов и формата данных.

**G2 закрыт (2026-08-23):**

- **SRC-012 — Open Data API «Работа в России» (trudvsem)** — официальные открытые данные («использование без ограничений»), без ключей, live-проверен (HTTP 200, ~514k вакансий) — **безусловный `allowed`** (ADR-012).
- **SRC-011 — HeadHunter API** — официальный developer agreement + OpenAPI — `allowed` при условной активации (приложение + ключ) (ADR-011).

Telegram web-preview имеет технический adapter contract и fixtures, но **не live-режим**. Его включение требует отдельного policy/legal decision. Публичная доступность страницы сама по себе не считается разрешением на агрегацию.

## Быстрый маршрут по документам

1. [`MANIFEST.md`***REMOVED***(MANIFEST.md) — паспорт и инварианты.
2. [`SPEC.md`***REMOVED***(SPEC.md) — указатель на полную спецификацию.
3. [`ROADMAP.md`***REMOVED***(ROADMAP.md) — последовательность этапов и gates.
4. [`STEPS.md`***REMOVED***(STEPS.md) — фактический журнал работы.
5. [`decisions/DECISIONS.md`***REMOVED***(decisions/DECISIONS.md) — индекс решений.
6. [`DOMAIN_CONTRACTS.md`***REMOVED***(DOMAIN_CONTRACTS.md) — P3 API и инварианты.
7. [`RSS_ATOM_ENGINE.md`***REMOVED***(RSS_ATOM_ENGINE.md) — P4 parser/normalization/dedup/checkpoint API.
8. [`MATCHING_ENGINE.md`***REMOVED***(MATCHING_ENGINE.md) — P5 matcher API: rules, intent gate, score formula.
9. [`STORAGE.md`***REMOVED***(STORAGE.md) — P6 SQLite/WAL storage: schema, idempotency, TTL cleanup.
10. [`DELIVERY.md`***REMOVED***(DELIVERY.md) — P7 delivery contract: HTML cards, dry-run, idempotency.
11. [`POST_MVP_GATES.md`***REMOVED***(POST_MVP_GATES.md) — статусы P10–P19 и блокеры.
12. [`RUNNABLE.md`***REMOVED***(RUNNABLE.md) и [`CHECKLIST.md`***REMOVED***(CHECKLIST.md) — запуск и acceptance gates.

## Граница с `lead_aggregator`

Этот проект не является переименованием или переписыванием `projects_17/lead_aggregator`.

- Parser: универсальные публикации, профили пользователей, policy, TTL и доставка.
- Lead Aggregator: доменный сценарий исполнителя, competence matching и коммерческий lead scoring.

Будущая интеграция возможна через формальные контракты, но только после сравнения семантики `Publication`, `Request` и `Lead`.

## Запрещено

- автоотклики, рассылки и комментарии авторам;
- сбор отдельной базы пользователей/авторов;
- обход капч, блокировок, paywall и лимитов;
- приватные источники без отдельного разрешённого контракта;
- отправка собранного Telegram-контента в LLM/ML pipeline без отдельного допустимого основания;
- хранение секретов в коде, YAML, карточках и логах.
