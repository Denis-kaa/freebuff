# MANIFEST.md — Манифест evaluation package

> **Пакет:** repository_organization_forensics_32
> **Дата:** 2026-08-21
> **Версия проекта:** v5.189.68
> **Промт-источник:** pompts_11/105_19_repository_organization_refactoring_forensics.md (Repository Organization & Refactoring Forensics)
> **Методология:** pompts_11/103_19_forensic_engineering_reporter.md (Forensic Engineering Reporter)
> **Статус:** FORENSIC ONLY — Refactoring Blueprint, код не изменялся, решения не принимались

## Назначение

Evaluation-пакет для независимой оценки **организации репозитория** платформы Freebuff / Workspace OS. Пакет восстанавливает фактическую структуру каталогов, определяет принадлежность компонентов (WHAT → RESPONSIBILITY → OWNER → DEPENDENCIES → LIFECYCLE → RUNTIME ROLE), строит границу Platform vs Project, карту Intelligence/Agents, проводит duplication/dependency анализ и предлагает **целевую каноническую структуру + безопасный план миграции** (Refactoring Blueprint).

## Файлы пакета

| # | Файл | Размер (LOC) | Описание |
|---|------|-------------|----------|
| 1 | REPOSITORY_ORGANIZATION_FORENSICS_V1.md | ~700 | Главный forensic-документ (секции A-Y: Executive Summary, Current Repository Map, Domain Map, Component Ownership Map, Code/Doc Analysis, Platform vs Project Boundary, Core/Service/Runtime Analysis, Intelligence Domain, Agent Ecosystem, Factory/Forge/Scenario Placement, Prompt Organization, Data/Storage, Experiments/Legacy, Duplication, Dependency, Architectural Smells, Proposed Canonical Structure, File Migration Matrix, Documentation Organization, Traceability, Metadata/Tagging, Migration Strategy, Risk Register, Validation, Final Recommendation) |
| 2 | MANIFEST.md | — | Этот файл |
| 3 | README.md | — | Описание пакета, ключевые выводы |

## Ключевые выводы

1. **Нумерация `NN` — исторический артефакт, не архитектура.** Каталоги 01–31 отражают порядок появления, а не слой системы.
2. **Архитектурные слои перемешаны с историческими контейнерами**: 10 архитектурных слоёв (core_02, scripts_01, runtime_05, freebuff_plugin_03, plugins_04, tests_09, docs_10, pompts_11, data_13, projects_17) vs 8 исторических (src_06, services_08, cli_07, frontend_18, infa_20, trash_21, books_out_23, screenshots_16).
3. **Platform vs Project граница** существует файлово (projects_17/), но **логическая изоляция отсутствует** (Knowledge/Memory глобальные, project→platform импорты).
4. **Intelligence (16 компонентов) и Agents (4 места) не имеют физического home** — размазаны по каталогам.
5. **Единственный реальный дубль** — SQLite-базы в `scripts_01/data/` и `data_13/` (5 db в обоих).
6. **Документация — лучшая часть** (8/10): 15 поддоменов, но нет машиночитаемой связи с кодом.
7. **Общая оценка организации: 5.1/10** — функционально, но навигация для новичка затруднена.

## Рекомендация (Refactoring Blueprint, НЕ миграция)

Аддитивная канонизация вместо рефакторинга:
1. Создать `archive/` + перенести evaluation-пакеты/tar.gz/trash (Phase 4, LOW risk)
2. README-алиасы `platform/` и `experiments/` (Phase 2)
3. Зафиксировать canonical home доменов в architecture.md (Phase 1)
4. Перенести infa_20 → docs_10/research/ (Phase 3)
5. Консолидировать ADR (decisions vs engineering-memory)
6. Начать тегирование 5 доменов (DO WITH LIMITS)

## Архив

Пакет архивируется в `repository_organization_forensics_32_v5.189.68.tar.gz` для передачи другому архитектору на независимую оценку.

## Ключевые метрики

- **Версия проекта:** v5.189.68
- **Каталогов top-level:** ~45 (включая 10 evaluation-пакетов)
- **Архитектурных слоёв:** 10
- **Исторических контейнеров:** 8
- **Модулей в core_02/:** 33
- **Модулей в scripts_01/:** 76+
- **Тестов:** 3345
- **Проектов:** 18+
- **Промтов:** 107 (конвенция NNN_TT_name.md)
- **Доменов:** 14 (3 с единым home, 11 размазаны)
- **Общая оценка организации:** 5.1/10
