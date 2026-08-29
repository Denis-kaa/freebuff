# repository_organization_forensics_32 — Repository Organization Forensics V1

> **Промт:** pompts_11/105_19_repository_organization_refactoring_forensics.md (Repository Organization & Refactoring Forensics)
> **Дата:** 2026-08-21 · **Версия проекта:** v5.189.68
> **Статус:** FORENSIC ONLY — Refactoring Blueprint, код не изменялся, решения не принимались

## Что это

Evaluation-пакет, восстанавливающий **фактическую организацию репозитория** Freebuff / Workspace OS: карта компонентов, граница Platform vs Project, домены Intelligence/Agents, duplication/dependency анализ и целевая каноническая структура с безопасным планом миграции.

## Ключевые выводы

- **Нумерация `NN` ≠ архитектура** — каталоги 01–31 отражают порядок появления, не слой
- **10 архитектурных слоёв vs 8 исторических контейнеров** (src_06/services_08/cli_07 почти пусты)
- **Intelligence (16 компонентов) и Agents (4 места) без физического home**
- **Единственный реальный дубль** — SQLite: scripts_01/data/ vs data_13/
- **Общая оценка: 5.1/10** — функционально, но навигация для новичка затруднена

## Рекомендация

**Аддитивная канонизация, НЕ рефакторинг** (первый шаг ~30 мин, нулевой риск):
1. `archive/` + перенос evaluation-пакетов/tar.gz/trash
2. README-алиасы `platform/`, `experiments/`
3. Canonical home доменов в architecture.md
4. infa_20 → docs_10/research/
5. Консолидация ADR
6. Тегирование 5 доменов (DO WITH LIMITS)

## Файлы

| Файл | Описание |
|------|----------|
| REPOSITORY_ORGANIZATION_FORENSICS_V1.md | Главный документ (секции A-Y) |
| MANIFEST.md | Манифест пакета |

## Архив

`repository_organization_forensics_32_v5.189.68.tar.gz`
