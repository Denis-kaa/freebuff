# 10_REFACTORING_ROADMAP.md — Безопасная миграция (по шагам)

> **Задача (§13):** НЕ «переписать всё». CURRENT → TARGET с промежуточными этапами.
> **Приоритет (§13):** 1 boundaries → 2 source-of-truth → 3 dependency → 4 filesystem → 5 naming → 6 docs → 7 cleanup.

---

## Шаг 0 — ФИКСАЦИЯ (0 код-изменений, ~30 мин)

**Что:** зафиксировать выявленные расхождения в терминах, НЕ трогая код.

- Обновить `docs_10/core/GLOSSARY.md`: развести 4 смысла Forge (Passport/Facade/Pipeline/Registry),
  2 смысла Scenario (corpus/decision), добавить слой Opportunity в целевую модель.
- Отметить Skill как ABSENT (capability-токены — замена), Agent как PARTIAL.
- **Что нельзя трогать:** код, тесты, data_13.
- **Откат:** git revert glossary-правки (однострочные).
- **Тесты:** не требуется (документация).

## Шаг 1 — Развести термины Forge/Scenario в коде (низкий риск)

**Что:** переименовать символы так, чтобы имя отражало 4/2 смысла (без изменения поведения).

- `ForgePipeline` → оставить (это CI-пайплайн, имя ок).
- `ForgeFacade` → оставить (execution boundary, имя ок).
- `ForgeRegistry` → оставить (реестр статусов).
- `ForgePassport` → оставить (декларация).
- НЕ переименовывать — вместо этого **добавить docstring-алias** и зафиксировать в glossary.
- **Что переносится:** ничего (только docstrings + glossary).
- **Тесты:** `python -m pytest tests_09/test_forge_*.py -q`.
- **Откат:** revert docstrings.

## Шаг 2 — Единый source-of-truth для db (средний риск)

**Что:** устранить дубль `scripts_01/data/*.db` vs `data_13/*.db` (5 db).

- Определить `data_13/` каноническим (уже указан в `DEFAULT_MEMORY_DB`).
- `scripts_01/data/` — пометить deprecated; добавить README-указатель.
- **Что НЕ переносить:** сами db (production-состояние) — сначала проверка, кто читает `scripts_01/data/`.
- **Тесты:** `python -m pytest tests_09/ -q` (после grep всех потребителей).
- **Откат:** symlink назад.

## Шаг 3 — Зафиксировать границу Platform/Project (низкий риск)

**Что:** добавить `projects_17/`-границу в `consistency_check` (project→platform импорты = warning).

- **Что:** аддитивный check в `consistency_check.py` (не ломающий exit 0, только warning).
- **Тесты:** `python -m scripts_01.consistency_check --report` (exit 0 сохранить).

## Шаг 4 — Интегрировать Orchestrator с ForgeFacade ИЛИ явно развести (средний риск, решить)

**Что:** решить судьбу двух execution-парадигм (03, R7).

- Вариант A: Orchestrator MODEL/AGENT-шаги → маршрутизировать через ForgeFacade (унификация).
- Вариант B: оставить параллельными, задокументировать как «agentic vs pipeline».
- **Рекомендация:** B (сначала), т.к. A ломает §7.3 boundary и требует глубокого рефакторинга.
- **Тесты:** `python -m pytest tests_09/test_orchestrator.py -q`.

## Шаг 5 — Ввести Skill как capability-реестр (низкий риск, аддитивно)

**Что:** признать capability-токены = Skill, завести `core_02/skill_registry.py` (тонкий поверх KNOWN_CAPABILITIES).

- **Что:** новый модуль, НЕ переписывает blueprint_v3; `SkillRegistry` = read-only view над capability-каталогом.
- **Тесты:** `python -m pytest tests_09/test_factory_registry.py -q` (не затронут).
- **Откат:** удалить модуль.

## Шаг 6 — Filesystem-реорганизация (высокий риск, последний)

**Что:** перенос каталогов по целевой структуре (09), с `имя_NN`-конвенцией или
обновлением `consistency_check._EVALUATION_PACKAGE_DIRS`.

- `phase*_evaluation_*` + `*forensics_*` → `evaluations_33/` (архив).
- `screenshots_16/logs_14/books_out_23/trash_21/` → `archive_34/`.
- `freebuff_plugin/` → `archive_34/`.
- **Что НЕ переносить:** `core_02/`, `scripts_01/`, `data_13/`, `tests_09/`, `projects_17/` (активные).
- **Тесты:** полный `python -m pytest tests_09/ -q` + `consistency_check` exit 0.
- **Откат:** git mv обратно (или revert).

## Шаг 7 — Cleanup (документация, низкий риск)

**Что:** пометить legacy в `docs_10/DOCUMENT_REGISTRY.md`, обновить AGENTS.md cross-links.

---

## Итоговая таблица приоритетов

| Шаг | Приоритет | Риск | Эффект |
|-----|-----------|------|--------|
| 0 (glossary) | 1 | нулевой | устраняет терминологический drift |
| 1 (термины) | 1 | низкий | ясность Forge/Scenario |
| 2 (db source-of-truth) | 2 | средний | убирает дубль 5 db |
| 3 (boundary) | 2 | низкий | явная Project-изоляция |
| 4 (orchestrator) | 3 | средний | разрешает 2 парадигмы |
| 5 (skill) | 4 | низкий | закрывает gap Skill |
| 6 (filesystem) | 5 | высокий | структура = архитектура |
| 7 (cleanup) | 6 | низкий | навигация |
