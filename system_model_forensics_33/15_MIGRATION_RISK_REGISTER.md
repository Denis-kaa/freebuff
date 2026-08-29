# 15_MIGRATION_RISK_REGISTER.md — Реестр рисков миграции

> **Задача (§13):** безопасная миграция; для каждого шага — что нельзя трогать + откат.

---

## Реестр рисков

| ID | Шаг | Риск | Вероятность | Влияние | Митигация | Откат |
|----|-----|------|-------------|---------|-----------|-------|
| R-001 | 1 (термины) | docstring-правки заденут grep-инварианты | LOW | LOW | только docstrings, не символы | git revert |
| R-002 | 2 (db) | production-данные в scripts_01/data потеряются | MEDIUM | HIGH | НЕ переносить db; сначала grep потребителей; README-указатель | symlink назад |
| R-003 | 3 (boundary) | consistency_check exit 0 сломается | LOW | MEDIUM | только warning (не error) | удалить check |
| R-004 | 4 (orchestrator) | унификация ломает §7.3 boundary | HIGH | HIGH | вариант B (задокументировать, не соединять) | — |
| R-005 | 5 (skill) | новый модуль ломает ANTI-6b closed vocab | LOW | MEDIUM | read-only view, не менять KNOWN_CAPABILITIES | удалить модуль |
| R-006 | 6 (filesystem) | перенос сломает import-пути + consistency_check naming | HIGH | HIGH | только archive/evaluations; обновить _EVALUATION_PACKAGE_DIRS | git mv обратно |
| R-007 | 6 (filesystem) | archive/ нарушит имя_NN | HIGH | MEDIUM | использовать имя_NN (archive_34) или исключение | — |
| R-008 | 7 (cleanup) | cross-links в AGENTS.md сломаются | LOW | LOW | перепроверить grep | git revert |
| R-009 | все | параллельные агенты перезапишут общий файл | LOW | MEDIUM | str_replace только (не write_file) для общих файлов | — |

---

## Что НЕЛЬЗЯ трогать (жёсткие инварианты)

1. `core_02/forge_registry.py` — single source of truth статусов, B10/R-127.
2. `core_02/forge_facade.py` — §7.3 boundary (direct Forge call из Scenario = НЕТ).
3. `data_13/*` — production-состояние (whims/opportunities/forge_registry/context.db).
4. Активные тесты `tests_09/` — зелёный набор.
5. `KNOWN_CAPABILITIES` (closed vocab, ANTI-6b) — без REGISTER-FIRST.

---

## Критерий готовности каждого шага (§19 finish condition)

- repository не изменён на forensic phase ✅ (этот пакет — только документация).
- Тесты: `python -m pytest tests_09/ -q` + `consistency_check --report` exit 0.
- Каждый шаг миграции — с тестом «до/после» и git-откатом.
