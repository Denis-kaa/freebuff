# MANIFEST.md — Evaluation Package `platform_architectural_inventory_34`

> **Промт-источник:** `pompts_11/107_19_platform_architectural_inventory.md`
> **Задача:** FULL PLATFORM ARCHITECTURAL INVENTORY & SYSTEM BOUNDARY ANALYSIS (read-only)
> **Версия проекта на момент анализа:** v5.189.72
> **Дата:** 2026-08-22
> **Режим:** FORENSIC ONLY — код НЕ изменялся, решения НЕ принимались.

## Принцип доверия (promt107 §0)

```
CODE > TESTS > CONFIG > RUNTIME BEHAVIOUR > DOCUMENTATION > HYPOTHESIS > ASSUMPTIONS
```

Каждое утверждение в пакете подкреплено `path + symbol + call path` (evidence ledger).

## Файлы пакета

| # | Файл | Назначение |
|---|------|-----------|
| 1 | `PLATFORM_ARCHITECTURAL_INVENTORY_V1.md` | Главный forensic-отчёт (секции A–X) |
| 2 | `RESPONSIBILITY_MATRIX.md` | Матрица ответственности компонентов |
| 3 | `CONTRACT_GRAPH.md` | Граф контрактов (REAL/PARTIAL/IMPLICIT/NO) |
| 4 | `SECURITY_TRUST_BOUNDARY_MAP.md` | Карта доверия и внешние мосты |
| 5 | `EVIDENCE_LEDGER.md` | Журнал доказательств (claim → file → symbol) |
| 6 | `TRACEABILITY_MAP.md` | Документация ↔ код ↔ тесты |
| 7 | `COMPETING_ABSTRACTIONS.md` | Дублирующие/конкурирующие абстракции |
| 8 | `REPOSITORY_TREE.md` | Текущая структура репозитория (снимок) |
| 9 | `TARGET_ARCHITECTURE.md` | Целевая модель + миграционный мост |
| 10 | `README.md` | Описание содержимого (entry point для архитектора) |

## Самодостаточность

Пакет самодостаточен: содержит фактические excerpt'ы кода (evidence), карты,
матрицы и README. НЕ содержит весь исходный репозиторий (per promt107 §29).
