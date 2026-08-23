# ADR-003 — Typed domain contracts and error boundaries

> **Статус:** Accepted
> **Дата:** 2026-08-23
> **Scope:** `projects_17/public_request_parser`

## Context

Проект должен поддерживать несколько источников, персональные профили,
временное хранение полного текста и Telegram-доставку, не смешивая эти
ответственности с доменной моделью `lead_aggregator`. До реализации RSS/Atom
нужна проверяемая граница, на которой можно строить fixture-based engine.

## Options

1. Использовать модели `lead_aggregator` напрямую.
2. Передавать между слоями свободные dictionaries.
3. Создать project-local frozen dataclasses и Protocol-порты.

## Decision

Выбран вариант 3:

- `SourceItem` и `Publication` отделяют source payload от нормализованной
  публикации;
- `SearchProfile` имеет `owner_scope`, версию и snapshot правил;
- `MatchDecision` всегда содержит provenance профиля и объяснение принятого
  решения;
- `SourcePolicy` блокирует polling и user-facing режимы для всех статусов,
  кроме evidence-backed `allowed`;
- `RetentionPolicy` не позволяет ослабить более строгий source TTL;
- `SourceAdapter`, `CheckpointStore` и `Delivery` оформлены как Protocol;
- ошибки валидации, adapter failures, domain rejection и delivery failures
  представлены разными типами/значениями.

Контрактный код живёт в `app/domain/contracts.py`, не импортирует платформу и
не выполняет сетевых операций.

## Consequences

### Положительные

- P4 может использовать стабильный API на fixtures без live source approval.
- Ошибка одного источника не обязана становиться отказом matching.
- Single-tenant scope не блокирует будущую изоляцию tenant-данных.
- Граница с `lead_aggregator` остаётся additive и обратимо расширяемой.
- TTL, explainability и policy gate проверяются до появления SQLite/Telegram.

### Ограничения

- Конкретные SQLite, RSS/Atom и Telegram реализации остаются задачами P4–P7.
- Формула scoring пока не закрыта; контракт фиксирует диапазон и provenance,
  но не алгоритм.
- P3 не утверждает live `allowed` source и не закрывает G2.

## Evidence

- `app/domain/contracts.py`
- `tests/test_domain_contracts.py`
- `DOMAIN_CONTRACTS.md`
- `SOURCE_POLICY_MATRIX.md`
