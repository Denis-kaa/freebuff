# system_model_forensics_33 — Repository Forensics: System Modeling (promt106)

> **Дата:** 2026-08-21
> **Версия проекта:** v5.189.69
> **Промт-источник:** `pompts_11/106_19_repository_forensics_system_modeling.md`
> **Статус:** FORENSIC ONLY — код НЕ изменялся, рефакторинг НЕ выполнялся.

## Назначение

Восстановить **реальную** модель платформы по КОДУ (не по документации) и сопоставить
её с целевой концептуальной моделью:

```
WHIM → WORKSPACE → PROJECT → AGENT/COLLABORATION → SCENARIO → FACTORY → FORGE
     → SKILLS/TOOLS/RUNTIME → ARTIFACT → MEMORY/KNOWLEDGE
```

Главный принцип (§18 промта): **НЕ доказывать, что модель правильна — пытаться её ОПРОВЕРГНУТЬ.**

## Ключевые выводы (коротко)

1. **Цепочка реальная** — `WHIM → Opportunity → Scenario → Factory → Forge → Artifact → Memory`,
   но содержит **дополнительный слой `Opportunity`**, которого нет в целевой модели.
2. **Workspace/Project** — тонкие YAML-контейнеры (L-1/L-2), а не «рабочая тетрадь с обсуждениями».
3. **Scenario перегружен** — статический «корпус ролей» (`core_02/scenario.py`) vs
   динамический decision-слой (`scripts_01/scenario_intelligence.py`).
4. **Forge перегружен** — 4 смысла: ForgePassport (декларация), ForgeFacade (chain-runner),
   ForgePipeline (CI-пайплайн), ForgeRegistry (реестр статусов).
5. **Skill — ABSENT** как модуль (только capability-токены); **Agent — PARTIAL** (размазан);
   **Runtime — PARTIAL** (`freebuff_plugin_03/runtime/`).
6. **Две конкурирующие execution-парадигмы**: `ForgeFacade.run_chain` (14-ролевой конвейер)
   vs `Orchestrator` (FSM/DAG Goal→Plan→Execute→Validate).

## Файлы пакета

| # | Файл | Содержание |
|---|------|-----------|
| 01 | 01_EXECUTIVE_FINDING.md | Главный вывод + 28 обязательных ответов |
| 02 | 02_REPOSITORY_MAP.md | Карта компонентов (каталоги → слои) |
| 03 | 03_ACTUAL_SYSTEM_MODEL.md | Фактическая модель по коду (node→status→evidence) |
| 04 | 04_TARGET_SYSTEM_MODEL.md | Целевая модель (концепт → ответственность) |
| 05 | 05_CONCEPT_TRACEABILITY.md | Таблица concept → target → actual → status → gap |
| 06 | 06_FACTORY_FORGE_SCENARIO_ANALYSIS.md | Границы Factory/Forge/Scenario |
| 07 | 07_AGENT_RUNTIME_SKILL_TOOL_ANALYSIS.md | Слой агентов/рантаймов/скиллов/тулов |
| 08 | 08_REPOSITORY_STRUCTURE_AUDIT.md | Аудит «каши» (platform vs project vs legacy) |
| 09 | 09_TARGET_REPOSITORY_STRUCTURE.md | Целевая структура + правила зависимостей |
| 10 | 10_REFACTORING_ROADMAP.md | Безопасная миграция по шагам |
| 11 | 11_TRACEABILITY_AND_TAGGING.md | Механизм traceability + оценка semantic-тегов |
| 12 | 12_EVIDENCE_LEDGER.md | Журнал доказательств (EV-ID → claim → symbol → status) |
| 13 | 13_DEPENDENCY_GRAPH.md | Граф зависимостей (доп.) |
| 14 | 14_ARCHITECTURAL_GAPS.md | Gap-реестр (доп.) |
| 15 | 15_MIGRATION_RISK_REGISTER.md | Реестр рисков миграции (доп.) |

## Позиционирование относительно prior-проходов

- `promt103` → `architecture_forensics_v2/` — восстановление архитектуры по слоям.
- `promt104` → `architecture_forensics_v2/` — platform architectural forensics v2.
- `promt105` → `repository_organization_forensics_32/` — организация репозитория + граница Platform/Project.
- **`promt106` → этот пакет** — системная модель: сверяет целевую концептуальную
  цепочку (WHIM→…→MEMORY) с фактической реализацией по коду.
