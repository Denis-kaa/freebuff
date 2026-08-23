# ADR-001: Parser boundary and source gates

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** PROJECT-LOCAL
**Project:** `projects_17/public_request_parser`
**Related:** [`MANIFEST.md`***REMOVED***(../MANIFEST.md), [`ROADMAP.md`***REMOVED***(../ROADMAP.md), [`public-request-parser-spec.md`***REMOVED***(../../../public-request-parser-spec.md), [`projects_17/lead_aggregator`***REMOVED***(../../lead_aggregator/)

## 1. Context

Пользователь хочет публичный продукт, который по персональным критериям находит открытые публикации с запросами на услуги. В Workspace уже есть `lead_aggregator`, но он решает более узкую задачу поиска клиентов/заказов для конкретного исполнителя и содержит competence/commercial lead logic.

Источник может быть технически доступен через URL, но это не доказывает, что автоматическая агрегация разрешена условиями площадки. Telegram web-preview особенно требует отдельной проверки: техническая возможность HTML parsing не является policy approval.

## 2. Decision

1. Создать отдельный sibling-проект `public_request_parser`, а не расширять или переписывать `lead_aggregator`.
2. Определить Public Request Parser как универсальный слой: source adapters → normalized publications → policy/rules → profiles → dedup/storage → delivery.
3. Оставить Lead Aggregator отдельным consumer/domain scenario, который позднее может использовать общие контракты после field-level comparison.
4. Сделать RSS/Atom первым operational source, потому что feed является явным механизмом синдикации, который можно исследовать и тестировать независимо от HTML-изменений.
5. Спроектировать Telegram adapter и тестировать его на fixtures, но оставить live-режим `disabled/conditional` до explicit policy/legal approval.
6. Не реализовывать обход капч, блокировок, paywall, rate limits или приватности; не выполнять outbound к авторам.
7. Хранить полный текст только с TTL и сохранять snapshot профиля/правил для объяснимости.

## 3. Alternatives

### A. Расширить `lead_aggregator`

**Rejected for now.** Это смешивает универсальный публичный продукт с прикладной логикой competence/commercial lead scoring и усложняет миграцию.

### B. Немедленно вынести общий core в платформу

**Rejected for this phase.** Общие абстракции ещё не подтверждены сравнением семантики моделей и live source requirements. Сначала нужен автономный vertical slice и evidence.

### C. Сразу подключить Telegram web-preview live

**Rejected.** Public URL не заменяет policy/legal basis; сначала fixtures и отдельный reversible gate.

### D. Начать с RSS/Atom

**Accepted.** Позволяет проверить domain contracts, matching, dedup, TTL, checkpoints и delivery на источнике, где формат и способ подписки формализованы.

## 4. Consequences

### Положительные

- Граница Parser/Lead Aggregator понятна и проверяема.
- Первый MVP не зависит от нестабильности Kwork SPA или live Telegram policy.
- Новые источники подключаются через adapter contract.
- Telegram parsing можно тестировать без сетевого доступа.
- Single-tenant запуск не блокирует будущую изоляцию профилей.

### Ограничения

- В начале доступно меньше источников.
- Нужен отдельный source/policy matrix перед live polling.
- Возможное переиспользование существующего кода откладывается.
- Telegram live capability может остаться blocked, если не будет допустимого основания.

## 5. Verification gates

- [x***REMOVED*** ADR добавлен в project-local index.
- [x***REMOVED*** RSS/Atom first отражён в MANIFEST/ROADMAP/SPEC.
- [x***REMOVED*** Telegram fixture-only отражён в MANIFEST/ROADMAP/CHECKLIST.
- [x***REMOVED*** Lead Aggregator не изменён.
- [ ***REMOVED*** Первый RSS/Atom source получил `allowed` policy decision.
- [ ***REMOVED*** Domain contracts прошли review.
