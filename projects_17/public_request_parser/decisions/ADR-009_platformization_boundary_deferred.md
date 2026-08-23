# ADR-009 — Platformization boundary deferred (P16)

> **Статус:** Accepted — deferred until live use-case evidence
> **Дата:** 2026-08-23
> **Связано:** `ROADMAP.md` P16, `AGENTS.md` (MissingRegistry), Workspace OS boundaries

## Контекст

P16 спрашивает, какие части parser превращаются в Workspace OS bridges/plugins.
Сейчас нет ни одного production `allowed` источника и ни одного реального
потребителя, поэтому платформализация была бы преждевременной.

## Решение

1. **Standalone-проект остаётся источником истины** для своих контрактов;
   никаких импортов платформы в любую сторону.
2. **Кандидаты на повторное использование зафиксированы**, но НЕ зарегистрированы
   в MissingRegistry: `SourceAdapter`-порт, `SourcePolicy` allowlist,
   `Publication`-нормализация, checkpoint/retention примитивы,
   delivery adapter contract, source catalog metadata.
3. **Порядок активации** (когда появится live-use evidence):
   employee-отчёт → register-first в `missing_registry` → additive bridge →
   независимые тесты обоих потребителей → удаление дубля только после
   compatibility proof.
4. Без нарушения границ Workspace OS: никакого direct Scenario → Forge call,
   runtime parser остаётся optional.

## Последствия

- Пока нет регистраций в MissingRegistry по этому проекту (ничего не «строилось на лету»);
- при появлении первого approved-источника (G2) этот ADR пересматривается;
- standalone-режим — обязательное условие любого будущего bridge.