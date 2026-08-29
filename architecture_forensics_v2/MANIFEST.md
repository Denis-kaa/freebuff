# MANIFEST.md — Манифест evaluation package

> **Пакет:** architecture_forensics_v2
> **Дата:** 2026-08-21
> **Версия проекта:** v5.189.67
> **Промт-источник:** pompts_11/104_19_platform_architectural_forensics_v2.md (Platform Architectural Forensics)
> **Методология:** pompts_11/103_19_forensic_engineering_reporter.md

## Файлы пакета

| # | Файл | Описание |
|---|------|----------|
| 1 | PLATFORM_ARCHITECTURE_FORENSICS_V2.md | Главный forensic-документ (секции A-Z: Executive Summary, Reality Map, Architecture, User Flow, Intelligence, Agent, Workspace/Project, Scenario, Factory, Forge, Agent/Skill/Tool, Artifact, Memory/Knowledge, Event/Orchestration, Plugin/MCP, Feedback, Execution Paths, Hypothesis Validation, Missing/Partial, Blind Spots, Contradictions, Provenance Gaps, Recommended Architecture, Roadmap, Evidence Ledger, Final Verdict) |
| 2 | CURRENT_ARCHITECTURE.md | Фактическая архитектура: 6 слоёв (User→Orchestration→Decision→Factory→Forge→Persistence), параллельные подсистемы (CoWork/Knowledge/Plugin/Policy/Runtime/Observability/Bootstrap), ключевые инварианты (§7.3, B10/R-127, B15, Privacy, ANTI-6b, CAN-16) |
| 3 | TARGET_MODEL_MAPPING.md | Поэлементная проверка модели «автомобиль» (20 элементов): Exists/Partial/Missing + итоговая статистика (~60% соответствия; ~75% с учётом частичных) |
| 4 | EXECUTION_PATHS.md | 7 реальных execution paths: Factory vertical slice, Whim→Opportunity, Orchestrator, Forge CLI, Forge chain-runner, MCP, Telegram |
| 5 | AGENT_ARCHITECTURE.md | Агентная архитектура: 14 pipeline-ролей (Blueprint v3), Presence-агенты, Collaboration-участники, RoleEngine; нет Agent ABC, нет A2A, нет lifecycle |
| 6 | INTELLIGENCE_ANALYSIS.md | Intelligence как emergent property: 9 компонентов формируют "Intelligence"; нет единого слоя; ScenarioIntelligence reactive (не proactive) |
| 7 | FACTORY_FORGE_ANALYSIS.md | Factory: BaseFactory template + 3 concrete + auto-discovery; Forge: production pipeline + bridge/gate + state tracker; capability discovery chain |
| 8 | GAP_MAP.md | 10 MISSING gaps (Agent ABC, Intelligence Layer, Skill, Artifact Registry, Proactive Companion, Evolution, Intent Router, A2A, Project isolation, External gateway), 7 PARTIAL, 4 CONCEPT ONLY, 12 BLIND SPOTS, 4 CONTRADICTIONS, 5 TRACEABILITY GAPS |
| 9 | EVIDENCE_LEDGER.md | 34 claims с трассировкой CLAIM→FILE→SYMBOL→BEHAVIOR (Workspace/Project, Scenario, Forge, Factory, Intelligence, Memory/Knowledge, Infrastructure) |
| 10 | TRACEABILITY_MATRIX.md | 30 компонентов: DOCUMENTED→IMPLEMENTED→TESTED (все ✅, имена тестовых файлов верифицированы) |
| 11 | README.md | Описание пакета, структура, ключевые выводы |
| 12 | FORENSICS_CONSOLIDATED_REPORT.md | Сводный отчёт по всем 8 forensic-проходам (Phase 4–9 + 104_19_platform_architectural_forensics_v2): что установлено, открытые GAP-ы, фактическая архитектура, рекомендации |
| 13 | MANIFEST.md | Этот файл |

## Архив

Пакет архивируется в `architecture_forensics_v2_v5.189.67.tar.gz` для передачи другому архитектору на независимую оценку.

## Ключевые метрики

- **Версия проекта:** v5.189.67
- **Модулей в core_02/:** 33
- **Модулей в scripts_01/:** 88
- **Тестов:** 3342+
- **Проектов:** 18
- **Factory:** 3 (content, research, test)
- **Pipeline-ролей:** 14
- **LLM providers:** 6
- **Соответствие модели:** ~60% (75% с учётом частичных как половина)
