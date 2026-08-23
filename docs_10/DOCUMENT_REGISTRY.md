# DOCUMENT REGISTRY — Статусы документации

> **Этап 4 консолидации (promt32).** Этот реестр — единый источник истины о статусе
> каждого документа проекта. Статусы: **ACTIVE** (актуален) / **LEGACY** (заменён,
> хранится как история) / **ARCHIVED** (в архиве) / **DRAFT** (черновик) /
> **OBSOLETE** (устарел, подлежит удалению на более поздних этапах).
>
> Правило (из `docs_10/core/ARCHITECTURE_MANIFEST.md` §6): архивация = перенос
> в архив **без удаления**, история сохраняется.
>
> Канонические реестры (проверяются `scripts_01/consistency_check.py`) помечены
> **`[канон***REMOVED***`** — их нельзя удалять или переименовывать.
>
> **Ограничение Этапа 4:** физический перенос файлов с входящими markdown-ссылками
> сломал бы link-checker `scripts_01/drift_check.py` (CI). Поэтому устаревшие документы
> помечены статусами **в месте их расположения** (не удалены, история сохранена),
> а физически удалены только `.bak`-файлы. Реестр фиксирует статусы, а не переносы.

---

## Корень проекта

| Документ | Статус | Примечание |
|----------|--------|------------|
| `AGENTS.md` | ACTIVE | Сессионный чекпоинт. Этап 5 консолидирует с BUFFY/CLAUDE/CODY/.cursorrules |
| `BUFFY.md` | ACTIVE | Главный документ Buffy. Этап 5 — унификация с AGENTS.md |
| `BUFFY_PROJECT.md` | ACTIVE | Состояние проекта (drift_check сравнивает статус-таблицы) |
| `CHANGELOG.md` | ACTIVE | История версий (Keep a Changelog) |
| `CLAUDE.md` | ACTIVE | Инструкции для Claude Code. Этап 5 — унификация |
| `CODY.md` | ACTIVE | Инструкции для Cody. Этап 5 — унификация |
| `.cursorrules` | ACTIVE | Инструкции для Cursor. Этап 5 — унификация |
| `README.md` | ACTIVE | Входная точка репозитория |
| `PLATFORM.md` | ACTIVE | **v5.75.0 (2026-08-04)**: канонический positioning-документ платформы (~6 348 слов, plain language, проверяется через `ls/grep/LESSONS/CHANGELOG` — см. footer) |
| `HOW_TO_LAUNCH_BUFFY.md` | ACTIVE | Operator runbook — как найти и запустить Баффи (CLI/TG-бот/promt-конвейер/MCP); TL;DR + 3 entry points + verification + FAQ || `SPEC.md` | ACTIVE | Техническая спецификация |
| `public-request-parser-spec.md` | DRAFT | Canonical specification: Public Request Parser Bot; интервью, source/policy scope, Parser ↔ Lead Aggregator boundary |
| `TASK.md` | ACTIVE | Трекер задач |

---

## `docs_10/` (корень)

| Документ | Статус | Примечание |
|----------|--------|------------|
| `DOCUMENT_REGISTRY.md` | ACTIVE | Настоящий реестр (самодокументирование) |
| `INDEX.md` | ACTIVE | Навигация по документации |
| `PLAN_NEXT_OPERATIONS.md` | ACTIVE | **v5.101.0**: Развёрнутый план следующих операций (7 этапов, промты) |
| `ROADMAP_FORGE_RECONCILIATION.md` | ACTIVE | **ROADMAP-FR-001 (v1.4 CLOSED 2026-08-06)**: Reconciliation-plan между RFC_BUFFY_FORGE_V1.md v1.1 §2a и реализацией; 3 sequential Шага closed (Hypothesis C verified, LEVIATHAN inventory ready); bump-history: v1.1 → v1.2 → v1.3 → v1.4 CLOSED; pre-condition: capability-check через SmartRouter.route(). **Per-bump cross-refs** (CAN-17 audit-trail): v1.1 → LESSONS PB-16; v1.2 → RFC_BUFFY_FORGE_V1.md v1.2 §2a.1-2a.3 (lines 178/195/213); v1.3 → LEVIATHAN_INVENTORY_V1.md v1.1 + LESSONS CON-52; v1.4 → ROADMAP-FR-001 itself (Final Closure Bulletin) |
| ROADMAP_PHASE2_CONTINUATION_v1.md | NEW 2026-08-09 - Autonomous Execution roadmap (068_07_autonomous_project_executor directive) | active | CROSS-LINK: WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md |
| `ROADMAP_VKUSVILL_DEMO_062.md` | ACTIVE | **ROADMAP-VV-001 v5.105.0 (2026-08-06)**: Промт 62 demo для отклика ВкусВилл — xlsx-skill + модельный .xlsx + Teamwork-разбор 3 роли (analyst/developer/reviewer); артефакты в `projects_17/vkusvill_demo/{build_model_xlsx.py,model_forecast.xlsx,forecast.py,parity_check.py,business_logic.md,README.md,short_report.md***REMOVED***` + scenario `runtime_05/scenarios/vkusvill_demo.yaml`; parity variant (b) NO LibreOffice; 3 категории (молочка/крупа/напиток); 2 неочевидных (SERVICE_LEVEL_Z=1.65 + INCIDENT_2024_CORRECTION cell-content). **Per-bump cross-refs**: → CHANGELOG v5.105.0 (Task 0/1/2/3); → core_02/LESSONS.md CON-54 (Teamwork decomposition insight) |
| `ROADMAP_VV_002_RESEARCH.md` | ACTIVE | **ROADMAP-VV-002 (Stage 0 scaffold 2026-08-06)**: Промт 63 deep-research план по ВкусВилл × AI-Автоматизация (33 секции per pomt63); Tier 1/2/3 source-mining стратегия + anti-hallucination tag protocol per [CON-55***REMOVED***(core_02/LESSONS.md); 8 файлов-артефактов в `projects_17/vkusvill_research/{01_business_scale.md,02_supply_chain_economics.md,03_legacy_and_forecasting.md,04_ai_role_and_stack.md,05_cases_and_competitors.md,06_candidate_profile.md,07_interview_strategy.md,08_final_synthesis.md,SOURCES.md,README.md,STEPS.md,LESSONS.md***REMOVED***`; sibling к ROADMAP-VV-001 (research-слой над artifact-слоем). **Per-bump cross-refs**: → `pompts_11/064_04_vkusvill_ai_avtomatizaciya.md` (source brief); → core_02/LESSONS.md CON-55 (research-methodology, inline tag protocol) |
| `DRIFT_REPORT.md` | ARCHIVED | Генерируемый артефакт `drift_check.py` (в `.gitignore`) |

---

## `docs_10/visual/` — Mermaid диаграммы (git-renderable)

| Документ | Статус | Примечание |
|----------|--------|------------|
| `visual/diagrams/vv_001_to_vv_002.mmd` | ACTIVE | **2026-08-06**: Mermaid flowchart TB — линия ROADMAP-VV-001 → ROADMAP-VV-002 (артефактный слой projects_17/vkusvill_demo/ ↔ исследовательский слой projects_17/vkusvill_research/, общий OUTCOME-отклик). ClassDef по статусу (closed green / inprogress yellow / artifact blue / pending grey). cross-ref: [CON-54***REMOVED***(../core_02/LESSONS.md) (Teamwork-decomposition), [CON-55***REMOVED***(../core_02/LESSONS.md) (inline tag protocol). Render: mermaid.ink, GitLab/GitHub markdown, mermaid-cli, Obsidian — открыть как `.mmd` asset. |
| `visual/diagrams/forge_line.mmd` | ACTIVE | **2026-08-06**: Mermaid flowchart LR — Forge meta-system line (VISION_3.0 → RFC_BUFFY_FORGE_V1 v1.1 → ARB review → ROADMAP-FR-001 3 stages → v1.4 CLOSED → impl `core_02/{forge_pipeline,forge_registry,workspace***REMOVED***.py` + `scripts_01/forge.py` v5.103.0 + LEVIATHAN_INVENTORY_V1 v1.1 cat-A rows #26-#28). cross-ref: [CON-38..52***REMOVED***(../core_02/LESSONS.md). |

## `docs_10/history/` — история решений и сессий

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ADR-001_positioning.md` | ACTIVE | Почему агрегатор, не конкурент (источник: SESSION_UNDERSTANDING раздел 1) |
| `ADR-002_contracts.md` | ACTIVE | Почему JSON-контракты (источник: SESSION_UNDERSTANDING раздел 4) |
| `SESSION_UNDERSTANDING_2026-08-02.md` | ACTIVE | Полная фиксация сессии (canonical history entry, drift-anchor) |
| `DAY_SUMMARY_2026-08-02.md` | ACTIVE | Дневная сводка: стратегия + код + проекты |
| `SESSION_SUMMARY_2026-08-03.md` | ACTIVE | Полная фиксация сессии 2026-08-03 (v5.59.0→v5.63.0, 8 releases, CON-19…34, Phase 5 progress, ledger) |
| `DAY_SUMMARY_2026-08-03.md` | ACTIVE | Дневная сводка 2026-08-03: TL;DR стратегия + релизы + окружение + итог |
| `DAY_SUMMARY_2026-08-05.md` | ACTIVE | Дневная сводка 2026-08-05: v5.89.0→v5.91.0 — CON-33/34/35/36, queue cleanup, watcher, interior_planner restore + роль interior_consultant |
| DAY_SUMMARY_2026-08-06.md | ACTIVE | Дневная сводка 2026-08-06: v5.102.0 Memory Engine MVP + v5.103.0 Buffy Forge v1 — CON-50/51, интерьер v5-фичи, полный прогон tests_09/ |
| TEST_REPORT_2026-08-06.md | ACTIVE | Сводный отчёт прогона tests_09/: 2341 собрано, 2327 passed, 0 регрессий сессии; 3 фейла + 8 errors преэкзистующие (telegram_bot, mcp_server) |

---

## `docs_10/core/` — ядро документации

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ARCHITECTURAL_DEBT.md` | ACTIVE | Реестр долгов (base для Этапа 9) |
| `ARCHITECTURE_3.0.md` | LEGACY | Заменён на `ARCHITECTURE_CANONICAL.md` + `ARCHITECTURE_MANIFEST.md` |
| `ARCHITECTURE_CANONICAL.md` | ACTIVE **[канон***REMOVED***** | Каноническая архитектура (Этап 2) |
| `ARCHITECTURE_MANIFEST.md` | ACTIVE **[канон***REMOVED***** | Архитектурный закон (Этап 3) |
| `ARCHITECTURE_PRINCIPLES.md` | ACTIVE | Принципы; источник синтеза MANIFEST (ниже его в приоритете) |
| `ARCHITECTURE_REVIEW.md` | LEGACY | Экосистемный обзор 2026-07-27; заменён каноном |
| `BOOTSTRAP_SPECIFICATION.md` | ACTIVE | Спецификация Bootstrap Engine |
| `CAPABILITY_SPECIFICATION.md` | ACTIVE | Спецификация Capability Registry |
| `CODE_QUALITY_STANDARD.md` | ACTIVE | Стандарт качества (обязательный регламент) |
| `PROJECT_REQUIREMENTS.md` | ACTIVE | **v5.98.0**: Стандарт готовности проектов (RUNNABLE.md, CHECKLIST.md, web-фолбэк, Environment Doctor) |
| `PLAN_NEXT_OPERATIONS.md` | ACTIVE | **v5.101.0**: Развёрнутый план следующих операций (7 этапов, 6 проектов, промты) |
| `COMPATIBILITY_MATRIX.md` | ACTIVE | Матрица совместимости Runtime |
| `CORE_PROMPT.md` | ACTIVE | Единый Core Prompt (цель Этапа 5) |
| `DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` | ACTIVE | Спецификация Session Mesh v2.0 |
| `EVENT_PLATFORM_SPECIFICATION.md` | ACTIVE | Спецификация Event Platform |
| `FINAL_STRUCTURE.md` | ACTIVE | Итоговый синтез Этапа 10 (схема, каталоги, реестр, ADR, задачи) |
| `GLOSSARY.md` | ACTIVE **[канон***REMOVED***** | Единая терминология (Этап 7) |
| `LIFECYCLE.md` | ACTIVE **[канон***REMOVED***** | Жизненные циклы компонентов (Этап 8) |
| `MODULE_CONSOLIDATION.md` | ACTIVE **[канон***REMOVED***** | Аудит модулей (Этап 6) |
| `POLICY_ENGINE_SPECIFICATION.md` | ACTIVE | Спецификация Policy Engine; MCP-инструмент `policy_override` (правило 11, ADR-009) в §8 |
| `PROJECT_RULES.md` | ACTIVE | **2026-08-12**: Канон ведения проектов (проект = контейнер контекста): обязательный каркас (MANIFEST/LESSONS/decisions/ROADMAP/README/RUNNABLE/CHECKLIST) · контекст в проекте (уроки, шаги, «почему», ADR) · тиражируемое → общая база (одна сторона) · задача идёт через проект · работа по платформе = проект «сама платформа» · EM-шаблоны · чек-лист нового проекта. Расширяет RULES.md (чек-лист старта проекта обновлён со ссылкой на §8), cross-link AGENTS.md §6 |
| `PROJECT_REGISTRY.md` | ACTIVE | Реестр проектов |
| `PROMPT_IMPLEMENTATION_v1.0.md` | ARCHIVED | Стаб-копия `pompts_11/017_02_struktura_requirements_testy.md`; перенесён → `trash_21/` (2026-08-01, дубль решён, канон — промт) |
| `RULES.md` | ACTIVE | Правила (drift_check сравнивает дерево каталогов) |
| `RUNTIME_ABSTRACTION_SPECIFICATION.md` | ACTIVE | Спецификация Runtime Abstraction Layer |
| `RUNTIME_VALIDATION_FRAMEWORK.md` | ACTIVE | Фреймворк валидации Runtime |
| `SYSTEM_INVENTORY.md` | ACTIVE | Инвентаризация системы |

---

## `docs_10/audits/` — аудиты

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md` | ACTIVE | Аудит promt31 (цитируется ROADMAP_PROMT32) |
| `ARCHITECTURE_WORKSPACE_OS_2026-07-31.md` | ACTIVE | Доменный аудит Workspace OS |
| `AUDIT_2026-07-27.md` | ARCHIVED | Исторический аудит |
| `AUDIT_2026-07-28.md` | ARCHIVED | Исторический аудит |
| `AUDIT_2026-07-28_FULL_CODE_REVIEW.md` | ARCHIVED | Исторический аудит |
| `AUDIT_2026-07-29.md` | ARCHIVED | Исторический аудит |
| `AUDIT_2026-07-29_v5.0.0.md` | ARCHIVED | Исторический аудит |
| `AUDIT_BOOTSTRAP.md` | ARCHIVED | Исторический аудит |
| `AUDIT_CODE_QUALITY_2026-07-29.md` | ARCHIVED | Исторический аудит |
| `AUDIT_FULL_2026-07-29.md` | ARCHIVED | Исторический аудит |
| `AUDIT_STEP0_2026-07-31.md` | ACTIVE | Шаг 0 security-аудита (TASK_SECURE_MCP_ACCESS) |
| `AUDIT_TEMPLATE.md` | DRAFT | Шаблон для новых аудитов |
| `CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md` | ACTIVE | Аудит Этапа 1 консолидации (цитируется ROADMAP) |
| `PROJECT_INVENTORY_REPORT_2026-08-01.md` | ACTIVE | Полная инвентаризация проекта (promt41/041_03): документация + код + маппинг + SoT + план |
| `DOMAIN_MODEL_VERIFICATION_2026-07-31.md` | ACTIVE | Верификация доменной модели |
| `DOMAIN_MODEL_WORKSPACE_OS_2026-07-31.md` | ACTIVE | Доменная модель Workspace OS |
| `DRIFT_REPORT.md` | ARCHIVED | Генерируемый отчёт (история прогонов) |
| `RECOVERY_REPORT_2026-07-31.md` | ARCHIVED | Инцидент `metrics.py` (история) |
| `RECOVERY_REPORT_7_MODULES_2026-07-31.md` | ARCHIVED | Инцидент 7 модулей (история) |

---

## `docs_10/decisions/` — решения

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ADR_001_Vision_3.0_AI_Infrastructure_Layer.md` | LEGACY | Полный текст ADR; канонический указатель — `engineering-memory/decisions/ADR_001` (ADR-007) |
| `DECISIONS.md` | ACTIVE | Индекс ADR (обязателен для drift_check `_ADR_INDEX`) |
| `IDEAS.md` | ACTIVE | Реестр архитектурных идей (не удаляется) |

---

## `docs_10/engineering-memory/` — память проекта

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ARCHITECTURE.md` | ACTIVE | Архитектурная память |
| `PROJECT_BOOK.md` | ACTIVE **[канон***REMOVED***** | Книга проекта (проверяется consistency_check) |
| `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` | ACTIVE | **v5.92.0**: RFC — архитектура Organizational Memory Engine |
| `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md` | ACTIVE | **v5.93.0**: Архитектурная эволюция RFC (promt52): 8-уровневый анализ + 12 ADDITIVE improvements |
| `RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md` | ACTIVE | **v5.94.0 (2026-08-05)**: RFC Decision Intelligence System (promt53): подсистема анализа качества архитектурных решений (ARE + CAE + TDA + Policy Checker + Evolution Planner) |
| `RFC_BUFFY_FORGE_V1.md` | ACTIVE | **v5.95.0 (2026-08-05)**: RFC Buffy Forge v1 (promt56): метасистема архитектурной экосистемы — 6 форджей (Idea, Knowledge, Architecture, Implementation, Validation, Evolution) |
| `ARB_REVIEW_FACTORY_FORGE_MANIFEST_V1.md` | ACTIVE | **v5.96.0 (2026-08-05)**: ARB Review: Factory/Forge Manifest (promt57): 10-шаговый ARB-анализ документа 68, вердикт CHANGES REQUIRED |
| `ARB_REVIEW_PLATFORM_FORENSICS_PROMPT_V1.md` | ACTIVE | **2026-08-12 (ARB-REV-004)**: ARB Review: Platform Forensics & CI Integration Discovery v1.0 (промт 1 content_factory): 10-шаговый анализ 054_17, вердикт APPROVED WITH RECOMMENDATIONS — терминология канонична (Factory/Forge/Scenario = карта v1.1), read-only, evidence-правило; RA: AFC-seed + маппинг G0–G4 → MissingRegistry/DEBT + close-vocabulary guard + регистрация выхода |
| `FORENSICS_CI_GAP_MAP_V1.md` | ACTIVE | **2026-08-12**: Forensics gap map (промт 1 RA2 ARB-REV-004): целевая модель CI (10 шагов §8) ↔ фактические реестры платформы (ForgeRegistry/ScenarioRegistry/ForgeFacade/MissingRegistry/data_13), статусы G0–G4 + evidence CLAIM/EVIDENCE/CONFIDENCE; итог: 7×G0 + SELECT G0/G1 + FactoryRegistry G2 + 2×G3 (Opportunity Engine, Whim-capture), G4=0; вердикт READY WITH ADAPTER; кандидаты на register-first: opportunity_engine/whim_capture |
| `FORENSICS_CI_REPORT_V1.md` | ACTIVE | **2026-08-12**: Полный отчёт A–K Repository Forensics (промт 1 §19): A exec finding (~70% ready) · B repo map (entrypoints/core/services/runtime_05/data_13/projects_17) · C 4 real execution paths (forge chain / prompt dispatch / MCP / scenario discovery) · D примитивы (AGENT/RUNTIME/SCENARIO/FACTORY/FORGE/MEMORY/EVENT… CONFIRMED/PARTIAL/ABSENT) · E Factory/Forge/Scenario анализ (терминология канонична) · F CI compatibility · G gaps 10×G0+1×G1+1×G2+2×G3+0×G4 · H конфликтов 0 · I minimal integration (3 новые сущности: Whim/Opportunity/FactoryRegistry) · J первый vertical slice (Whim→Opportunity→Scenario→ForgeFacade→Validate→Memory) · K READY WITH ADAPTER. Финал: REPOSITORY FORENSICS COMPLETE — IMPLEMENTATION NOT STARTED (read-only) |
| `FORENSICS_CI_FOLLOWUP_V1.md` | ACTIVE | **2026-08-12**: План реализации Minimal CI Layer (§I FORENSICS_CI_REPORT_V1.md) в порядке register-first (RA2 ARB-REV-004): Фаза 1 — First Vertical Slice §J (opportunity_engine — промт 079_19 prompt_written; whim_capture — промт 080_19; e2e-прогон) · Фаза 2 — FactoryRegistry (Missing #1: mark-prompt-written по 078_19 + реализация) · Фаза 3 — scenario_engine (Missing #2, design_ready, оркестратор — не блокирует срез) · критерии приёмки по фазам · зависимости от Missing #1/#2 (не блокируют §J) · валидация (missing_registry check + build_report TOTAL 0) |
| `factory_forge_manifest.md` | ACTIVE | **v5.96.0 (2026-08-05)**: Factory/Forge Manifest (документ 68): визионерский документ — иерархия Workspace OS → Factory → Forge → Engine → Module → Tool → Skill → Prompt |
| `LEVIATHAN_INVENTORY_V1.md` | ACTIVE | **v5.97.0 (v1.1 bump 2026-08-06)**: LEVIATHAN Inventory: категоризация A/B/C 25 компонентов + ребрендинг терминологии под Buffy; v1.1 +Cat-A rows #26-#28 (forge_pipeline/forge_registry/workspace) + ROADMAP-FR-001 cross-ref (Шаг 3 prep). **Per-bump cross-ref**: v1.1 → ROADMAP-FR-001 Шаг 3 (cat-A preparation for downstream Forge extensions) + LESSONS CON-52 (Workspace/Project vs Forge levels anti-collision rule) |
| `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` | ACTIVE | **v1.2 (2026-08-09, 066_09_workspace_os_kus_vkusvill)**: Workspace OS stress-test research (39 секций; 43 артефакта §2 inventory; A/B/C доктрина §3). Phase 2: §4 Career + §5 Business + §6 Demo + §7 Scenario CLOSED (SHIP-verified; Hypothesis C orthogonal-STATE); §8-§39 Phase 2-4 deferred. **Cross-refs**: → AUDIT_WS_OS_P65_§4/§5/§6_V1.md; → projects_17/vkusvill_research/ |
| `AUDIT_WS_OS_P65_§4_V1.md` | ACTIVE | **2026-08-09**: независимый claim-by-claim audit §4 (Career pipeline): 12 primary + 11 secondary + 3 gaps; real command+output cross-refs; TRUST 8.5-9.0/10; verdict SHIP. Pattern: projects_17/vkusvill_research/09_audit_promt64.md |
| `AUDIT_WS_OS_P65_§5_V1.md` | ACTIVE | **2026-08-09**: независимый claim-by-claim audit §5 (Business pipeline): 11 primary C-Biz + 7 secondary + 5 gaps; real bash blocks embedded; TRUST 8.5-9.0/10; verdict SHIP |
| `AUDIT_WS_OS_P65_§6_V1.md` | ACTIVE | **2026-08-09**: независимый claim-by-claim audit §6 (Demo pipeline): 12 primary C-Demo + 6 secondary + Q-A..Q-E mapping + 4 gaps; real command outputs + per-stage 11-axis sampling; TRUST 8.5-9.0/10; verdict SHIP |
| `AUDIT_WS_OS_P65_§9_V1.md` | ACTIVE | **2026-08-09**: независимый claim-by-claim audit §9 (Forge pipeline): 13 primary C-Forge-01…13 + 9 secondary C-D1…9 + 4 gaps (G-1…G-4); line-level fact-check против forge_pipeline.py (run=203/hooks=85/on_report=175/_run_cmd=62 без shell=True), forge_registry.py (STATUSES=38/cap=161), forge_registry.yaml (7×UNFORGED), RFC_BUFFY_FORGE §4 (L0-L5), FR-001 §2a.1/§2a.3; TRUST 8.5-9.0/10; verdict SHIP |
| `AUDIT_WS_OS_P65_§10_V1.md` | ACTIVE | **2026-08-09**: независимый claim-by-claim audit §10 (Modes A-G, Human+AI spectrum): 18 primary C-Mode-01…18 (10 [ФАКТ***REMOVED*** + 7 [АРХ***REMOVED*** + 1 [ГИП***REMOVED*** → 11 VERIFIED + 7 CONSISTENT) + 7 secondary C-MS-1…7 + 4 gaps G-1…G-4 (Mode G absent / Mode D partial / Mode E partial / §3.x drift); line-level fact-check против router.py:239/271/302 (SmartRouter CON-40 best_score fallback), wizard_lib:27/41/70/127/284, blueprint_v3:114-148 + 347-357 (CAPABILITIES validation), distributed_agents:45-46 + 77-111 (AgentMesh), presence.py:157-237 (PresenceEngine), collaboration.py:113-172 (Participant), LESSONS ANTI-6:192-220; §3.3 forward-correct (G overstate + D/E/F understate); TRUST 8.5-9.0/10; verdict SHIPPABLE |
| `AUDIT_WS_OS_P65_RECAP.md` | ACTIVE | **v1.2 (2026-08-09)**: сводка 5 аудитов Phase 2 (§4/§5/§6/§9/§10): 66 primary + 40 secondary + 20 gaps, TRUST avg ≈ 8.9/10, все SHIP/SHIPPABLE; R-1…R-18 для §33 Minimal v0.1 + §23 (Mode D) + §33 prep |

| `P3_FORGE_FACADE_DESIGN.md` | ACTIVE | **v5.156.0 (2026-08-10)**: ForgeFacade design (ADR-013): add M1 CHAIN-runner + M2 memory integration + M3 registry hook + M4 project config + M5 validation; PIPELINE_CHAIN constants + ChainRun/ChainStage dataclasses + RoleArtifactValidator (v5.163.0 addendum). Cross-refs: → P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md (IDEA EXPLORER run); → WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §34 (Candidate 3 winner) |
| `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` | ACTIVE | **v5.156.0+v5.158.0+v5.161.0+v5.165.0+v5.166.0 (2026-08-10)**: IDEA EXPLORER v2.0 прогон на идее ForgeFacade-фабрики: 7 веток → score → prune → depth-2 → cross-pollination → reframe → 3 кандидата; H1 REFUTED → RoleArtifactValidator путь; H4 REFUTED (v5.158.0/v5.161.0) → existing last_pipeline['chain'***REMOVED*** достаточен (resume семантика); FWD-1 closed v5.166.0 через vkusvill_research проект. Cross-refs: → P3_FORGE_FACADE_DESIGN.md §6.5 H4 REBUTTAL |
| `RFC_BUFFY_FORGE_V1.md` | ACTIVE | **v5.95.0 (2026-08-05, v1.3 2026-08-10)**: RFC Buffy Forge v1 (промт 56) — метасистема архитектурной экосистемы: 6 форджей (Idea/Knowledge/Architecture/Implementation/Validation/Evolution); v1.3 уточняет RUNNABLE/CHECKLIST триггеры на v5.97.0. Cross-refs: → ROADMAP_FORGE_RECONCILIATION.md; → LEVIATHAN_INVENTORY_V1.md |
| `INDEX.md` | ACTIVE | **v5.168.0 (2026-08-10)**: sharded index connector — ADDITIVE new § Forge/Validator & chain cross-link секция + R-153..R-157 в RECAP_V2 (TOTAL: 152 → 157). Cross-refs: → core_02/forge_facade.py + tests_09/test_role_artifact_validator.py + tests_09/test_forge_chain_{cli,real_integration***REMOVED***.py |
| `decisions/ADR_001…ADR_007` | ACTIVE | Каноническое расположение ADR (drift_check `_ADR_CANONICAL_DIR`) |
| `templates/*.md` | ACTIVE | Шаблоны Engineering Memory |

---

## `docs_10/ops/`, `docs_10/plugin/`, `docs_10/projects_meta/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
| `docs_10/ops/` (10 файлов) | ACTIVE | Операционные гайды, шаблоны. Дубль `ops/AGENTS.md` → `trash_21/AGENTS_ops_duplicate.md` (2026-08-01); канон — корневой `AGENTS.md` |
| `docs_10/plugin/` (4 файла) | ACTIVE | Документация freebuff_plugin; `PLUGIN_CONTRACT_SPECIFICATION.md` §8 — MCP-инструменты ядра (incl. `policy_override`) |
| `docs_10/projects_meta/` (6 файлов) | ACTIVE | Интеграции: Lightpanda, Overlay, Workers; `PROJECTS_OVERVIEW.md` — **v5.101.0 → v1.1 (2026-08-17, +1 проект `kwork_site`)**: сводный аудит **7 проектов** платформы |

---

## `docs_10/vision/`

| Документ | Статус | Примечание |
|----------|--------|------------|
| `PRODUCT_MANIFESTO.md` | ACTIVE | Манифест продукта |
| `decision_index.md` | ACTIVE **[канон***REMOVED***** | **v5.62.0 (2026-08-03)**: phase-grouped ADR navigation view; ADR-010 (Remote Sync) detailed entry; canonical index at `decisions/DECISIONS.md`. Anti-duplication: this is a navigation view, не a second authoritative ADR registry. |
| `ROADMAP.md` | LEGACY | Заменён на `ROADMAP_PROMT31_WORKSPACE_OS.md` + `ROADMAP_PROMT32_CONSOLIDATION.md` |
| **ADR file (canonical)** | **ACTIVE** | `ADR_010_Remote_Sync_Telegram_Relay.md` (engineering-memory/decisions) — detailed Phase 5.3 Remote Sync decision; canonical switchboard for ADR cross-references |
| `ROADMAP_PROMT31_WORKSPACE_OS.md` | LEGACY | Заменён на ROADMAP_PROMT32 (фичи заморожены Mission Lock) |
| `ROADMAP_PROMT32_CONSOLIDATION.md` | ACTIVE **[канон***REMOVED***** | Текущая миссия консолидации |
| `VISION_3.0.md` | ACTIVE | Стратегическое видение |
| `VISION_3.0_MAP.md` | ACTIVE | Карта компонентов Vision 3.0 |
| `archive/ARCHITECTURE.md` | ARCHIVED | В архиве |
| `archive/VISION_2.0.md` | ARCHIVED | В архиве |

---

## `docs_10/session_dumps/`, `docs_10/task_archive/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
| `docs_10/session_dumps/` (3 файла) | ARCHIVED | Исторические дампы сессий |
| `docs_10/task_archive/` (2 файла) | ARCHIVED | Архив завершённых задач |

---

## `pompts_11/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
Ревизия Этапа 5 (полная, 38 файлов; 5 артефактов → `trash_21/`; 2026-08-01 добавлены `041_03`, `042_06`, `043_08`):

| Файл | Статус | Примечание |
|------|--------|------------|
| `032_09_workspace_os_konsolidaciya.md` | ACTIVE | Миссия консолидации (источник ROADMAP_PROMT32) |
| `036_09_full_consolidation_pipeline.md` | ACTIVE | 10 канонических правил Workspace OS (встроены в GLOSSARY §11) |
| `037_11_user_choice_override.md` | ACTIVE | Правило 11 User-Choice Override (встроено, ADR-009) |
| `014_02_leviathan_arhitektura.md` | ACTIVE | Основание спецификаций (VISION_3.0, POLICY, EVENT, RUNTIME, BRIDGE, CAPABILITY, BOOTSTRAP) |
| `016_02_arhitektura_reorganizaciya.md` | ACTIVE | Основание принципов/валидации/совместимости (ARCHITECTURE_PRINCIPLES, RUNTIME_VALIDATION_FRAMEWORK, COMPATIBILITY_MATRIX, DOCTOR_GUIDE, CODE_QUALITY_STANDARD) |
| `017_02_struktura_requirements_testy.md` | ACTIVE | Канонический промт Session Mesh v2.0 (стаб-копия `PROMPT_IMPLEMENTATION_v1.0.md` → trash_21, 2026-08-01) |
| `001_07_pravila_dokumentirovaniya.md` | ACTIVE | Источник docs_10/core/RULES.md (правила документирования) |
| `012_01_evolution_cowork_platform.md`, `013_01_vision_2_0_universal_companion.md` | ACTIVE | Основание VISION_3.0 / IDEAS |
| `022_02_architecture_reality_check.md`, `023_02_kanonicheskaya_model_workspace_os.md`, `024_02_domain_model_workspace_os.md` | ACTIVE | Источники аудитов (Architecture Reality Check, Workspace OS, Domain Model) |
| `025_02_principy_agenta.md`, `026_05_engineering_memory.md` | ACTIVE | Источники принципов Reuse First / Engineering Memory (PROJECT_BOOK) |
| `027_05_projectbook_storybook.md` | ACTIVE | Источник ROADMAP_PROMT31 (Project Book evolution) |
| `031_03_arhitekturnyy_audit.md` | ACTIVE | Источник аудита ARCHITECTURAL_AUDIT_PROMT31 |
| `038_03_audit_prompt.md` | ACTIVE | Активный аудит-промт (полный архитектурный аудит) |
| `047_06_e2e_platform_test.md` | ACTIVE | **v5.61.0 (2026-08-03)**: переименован с `promt47.md` → NNN_TT_имя формат, §5.13 RESOLVED; канонический источник Stage 1 E2E Platform Test (TG round-trip через `core_02/telegram_contract.py`) |
| `041_03_inventarizaciya_proekta.md` | ACTIVE | Миссия полной инвентаризации (переименован из `promt41.md`; отчёт: `docs_10/audits/PROJECT_INVENTORY_REPORT_2026-08-01.md`) |
| `042_06_dokumentaciya_meeting_tasks.md` | ACTIVE | Документация/meeting-задачи (переименован из `promt42.md`; rename-fallout фикс 2026-08-01) |
| `043_08_frontend_workspace_os_ui.md` | ACTIVE | Фронтенд Workspace OS (glassmorphism UI для FastAPI; переименован из `promt43.md`) |
| `CODE_QUALITY_STANDARD.md` | ACTIVE | Стаб-перенаправление на `docs_10/core/CODE_QUALITY_STANDARD.md` (переименован из STANDART, опечатка исправлена в Этапе 5) |
| `002_14_planirovshchik_arhitekt.md` | LEGACY | Планирование (выполнено) |
| `003_01_buffy_2_agentic_platform.md` | LEGACY | ТЗ Buffy 2.0 (заменено VISION_3.0) |
| `004_01_distributed_agents_platform.md` | LEGACY | DAP (история) |
| `005_04_interoperability_layer.md` | LEGACY | Interoperability Layer (история) |
| `006_08_prototype_lab.md` | LEGACY | Инструмент разработки (история) |
| `007_04_lightpanda_integration.md` | LEGACY | Lightpanda интеграция (реализовано) |
| `008_06_fix_docs_kontur.md` | LEGACY | Security-фиксы (выполнено) |
| `009_06_fix_knowledge_structure.md` | LEGACY | Документ-структура (история) |
| `010_07_self_check_triggery.md` | LEGACY | Self-check триггеры (история) |
| `011_07_session_snapshot.md` | LEGACY | Слепок сессии (реализовано: buffy_stream_logger) |
| `015_02_ultimate_architect_termux.md` | LEGACY | Системный промт v2.0 (заменён CORE_PROMPT) |
| `028_04_notification_framework.md` | LEGACY | Notification framework (реализовано) |
| `029_04_integration_registry.md` | LEGACY | Интеграционный реестр (план) |
| `030_05_knowledge_management_system.md` | LEGACY | KMS дизайн (реализовано: KnowledgeEngine) |
| `033_10_dpe_audit.md` | LEGACY | DPE аудит (выполнено, GLOSSARY/MANIFEST) |
| `034_10_dpe_realizaciya.md` | LEGACY | DPE реализация (отложена, ADR-008/ADR-009) |
| `039_12_terminal_ai_studio_mobile.md` | LEGACY | Контекст мобильного агента (история) |
| `091_19_phase8_universal_scenario_intelligence.md` | ACTIVE | **v5.189.25 (2026-08-17)**: PHASE 8 — UNIVERSAL SCENARIO INTELLIGENCE (переименован из `promt91.md` по NNN_19 конвенции; следующий номер 092 — Phase 9 Universal Factory Vertical Slice). Domain-neutral decision layer: discovery → evaluation → ranking → selection → capability → Factory → Forge; реализация `scripts_01/scenario_intelligence.py` + `opportunity_engine.py::propose()` BC-fallback; 18 тестов (§18) + регрессия 70; register-first `scenario_intelligence` = implemented; §20 карта row #21; evaluation-пакет `phase8_evaluation_29/` + архив `PHASE8_EVALUATION_5.189.25.tar.gz` |


---

## `trash_21/` (артефакты, перенесены из pompts_11/ в Этапе 5)

| Файл | Статус | Примечание |
|------|--------|------------|
| `error.md` | ARCHIVED | Лог ошибок npm (артефакт, перенесён из pompts_11/) |
| `new.md` | ARCHIVED | Транскрипт сессии Codebuff (артефакт, перенесён из pompts_11/) |
| `structure.md` | ARCHIVED | Устаревшая схема структуры docs_10/ (перенесён из pompts_11/) |
| `freb.md` | ARCHIVED | Пустой файл (0 байт, перенесён из pompts_11/) |
| `promt18.md` | ARCHIVED | Пустой файл (0 байт; LEVIATHAN-история, перенесён из pompts_11/) |
| `PROMPT_IMPLEMENTATION_v1.0.md` | ARCHIVED | Стаб-дубль промта 017_02 (перенесён из docs_10/core, 2026-08-01) |
| `AGENTS_ops_duplicate.md` | ARCHIVED | Устаревший онбординг внешних агентов (перенесён из docs_10/ops, 2026-08-01; канон — корневой AGENTS.md) |

> В `trash_21/` также исторические файлы вне таблицы: `freebuff_project_dump.md`, `retrospective.md`,
> `project_dump_20260801_222022.md` + `.tar.gz` и каталог `dump_20260801_222022/` (слепок документации;
> перенесены 2026-08-01 в рамках rename-fallout фикса [5.34.0***REMOVED***).

---

## MCP-инструменты ядра (реестр)

> Единый реестр MCP-инструментов, регистрируемых в `scripts_01/mcp_server.py`
> (источник истины — `self._tools[...***REMOVED*** = McpTool(...)`, проверяется `tools/list`).
> Статусы: ✅ **реализован** (зарегистрирован в MCP Server) / 🔶 **planned**
> (специфицирован, но не зарегистрирован — см. соответствующие спецификации).

### Реализованы (52)

| Категория | Инструменты | Кол-во |
|-----------|-------------|--------|
| `event` | `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse` | 11 |
| `policy` | `policy_override` (правило 11, ADR-009) | 1 |
| `runtime` | `runtime_list`, `runtime_connect`, `runtime_disconnect`, `runtime_select`, `runtime_generate` | 5 |
| `bootstrap` | `bootstrap_check`, `bootstrap_run`, `bootstrap_status` | 3 |
| `knowledge` | `knowledge_search` | 1 |
| `memory` | `memory_store`, `memory_retrieve`, `memory_list` | 3 |
| `session` | `session_status` | 1 |
| `context` | `context_resume` | 1 |
| `plugins` | `plugins_list` | 1 |
| `bridge` | `bridge_connect`, `bridge_list`, `bridge_disconnect`, `bridge_rpc` | 4 |
| `roles` | `roles_list`, `roles_get`, `roles_assign`, `roles_unassign`, `roles_stats` | 5 |
| `presence` | `presence_list`, `presence_get`, `presence_history` | 3 |
| `collaboration` | `collab_create`, `collab_list`, `collab_get`, `collab_join`, `collab_leave`, `collab_send`, `collab_history`, `collab_status` | 8 |
| `distributed` | `distributed_list`, `distributed_spawn`, `distributed_run`, `distributed_status`, `distributed_broadcast` | 5 |
| `rag` | `rag_search`, `rag_hybrid`, `rag_rerank` | 3 |
| `pulse` | `pulse_list`, `pulse_stats`, `pulse_scan` | 3 |

### Planned (специфицированы, не зарегистрированы)

| Категория | Инструменты | Источник |
|-----------|-------------|----------|
| `policy` | `policy_apply`, `policy_list`, `policy_status`, `pack_install`, `capability_list` | [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(core/POLICY_ENGINE_SPECIFICATION.md) §8 |

> **Ключевые спецификации:** [RUNTIME_ABSTRACTION_SPECIFICATION.md***REMOVED***(core/RUNTIME_ABSTRACTION_SPECIFICATION.md),
> [BOOTSTRAP_SPECIFICATION.md***REMOVED***(core/BOOTSTRAP_SPECIFICATION.md),
> [EVENT_PLATFORM_SPECIFICATION.md***REMOVED***(core/EVENT_PLATFORM_SPECIFICATION.md),
> [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(core/POLICY_ENGINE_SPECIFICATION.md),
> [PLUGIN_CONTRACT_SPECIFICATION.md***REMOVED***(plugin/PLUGIN_CONTRACT_SPECIFICATION.md) §8.

---


### ACTIVE entries added 2026-08-09 (v5.144.0)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §33.11-§33.17 | Addendum | ACTIVE | ADDITIVE per CAN-16 (after §33.10, before §34); 5 RECAP_V2 audit-themes → 5 build-milestones synthesis |
| `docs_10/engineering-memory/ROADMAP_MIN_V0_1.md` | Roadmap | ACTIVE | Companion to §33.11-§33.17; 11-section build roadmap for v0.1; 35-day calendar; 7 acceptance criteria |

### ACTIVE entries added 2026-08-10 (v5.171.0)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/runbook/FORGE_CHAIN_RUNBOOK.md` | Runbook | ACTIVE | Операционный manual для `forge chain --json`: real-cost matrix (vkusvill 7.49s / interior 14.83s / research 7.87s, drained из 3-run subprocess benchmarks 2026-08-10) + 9-key schema reference + status/overall decision tree + resume/serialization semantics + troubleshooting matrix (exit codes, status pathology, known operational issues G-7.1..3 + per-version resolution с CHANGELOG v5.156-v5.170) |

Bump: ACTIVE 88 → 89.

### ACTIVE entries added 2026-08-11

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/runbook/MISSING_REGISTRY_RUNBOOK.md` | Runbook | ACTIVE | Операционный manual для `python -m core_02.missing_registry` (register-first lifecycle): CLI-справочник (list/seed/register/mark-prompt-written/mark-implemented/check, --path) + lifecycle registered → design_ready → prompt_written → implemented (forward-only) + exit codes + пошаговый гайд регистрации нового элемента + troubleshooting (B10/R-127 инварианты, дрейф §20 ↔ YAML). Связан с AGENTS.md §5 REGISTER-FIRST (CLI-блок добавлен) и FACTORY_FORGE_ARCHITECTURE_V1.md §20 |

### ACTIVE entries added 2026-08-12

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/core/PROJECT_RULES.md` | Canon | ACTIVE | Канон ведения проектов (проект = контейнер контекста): обязательный каркас (MANIFEST/LESSONS/decisions/ROADMAP/README/RUNNABLE/CHECKLIST) · контекст в проекте · тиражируемое → общая база · задача идёт через проект · работа по платформе = проект «сама платформа» · EM-шаблоны · чек-лист §8. Расширяет RULES.md (чек-лист старта проекта обновлён со ссылкой на §8), cross-link AGENTS.md §6 |
| `docs_10/engineering-memory/FORENSICS_CI_FOLLOWUP_V1.md` | Plan | ACTIVE | План реализации Minimal CI Layer (§I FORENSICS_CI_REPORT_V1.md) в порядке register-first (RA2 ARB-REV-004): 3 фазы (opportunity_engine + whim_capture → factory_registry → scenario_engine), критерии приёмки, зависимости от Missing #1/#2, валидация |
| `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` | Contract | ACTIVE | Минимальный архитектурный контракт Intelligence ↔ Factory ↔ Scenario ↔ Forge (промт 2 content_factory, repository-first): выход A–P (repo reality 15 модулей с evidence path+symbol · reusable components · Intelligence boundary · contract map Boundary|API|Input|Output|Owner|Gap · Opportunity/Scenario/Factory/Execution/Project State/Event/Provenance contracts · min new components whim_capture/opportunity_engine/factory_registry · vertical slice plan · risks · final architecture). Read-only: Repository verified. Implementation not started. Cross-refs: FORENSICS_CI_REPORT/GAP_MAP/FOLLOWUP, промт 079_19/078_19 |
| `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_RECONCILIATION_V1.md` | Contract | ACTIVE | Сверка контракта A–P с FORENSICS_CI_REPORT/FORENSICS_CI_FOLLOWUP: единый согласованный план Фаз 1–3 (opportunity_engine+whim_capture → factory_registry → scenario_engine), сверочная матрица 10 измерений (8 согласованы, 2 расхождения D1/D2 разрешены), открытые пункты O1–O3, факт-чек реестра 9 записей |
| `docs_10/engineering-memory/PLATFORM_AUDIT_RECOMMENDATIONS_V1.md` | Audit | ACTIVE | Полный аудит платформы (read-only, 2026-08-12): 25 рекомендаций по 7 областям (версии/счётчики, реестры документов, ссылки/naming, код, структура каталогов, register-first бэклог, процессы/git) с evidence (путь+факт). Ключевые факты: 2694 теста, CHANGELOG v5.187.3 vs TASK v5.110.0, реестр 18/181 md, 7/9 записей missing_registry не implemented |

Bump: ACTIVE 89 → 94 (5 новых: PROJECT_RULES.md + FORENSICS_CI_FOLLOWUP_V1.md + INTELLIGENCE_FACTORY_CONTRACT_V1.md + INTELLIGENCE_FACTORY_CONTRACT_RECONCILIATION_V1.md + PLATFORM_AUDIT_RECOMMENDATIONS_V1.md, 2026-08-12).

### ACTIVE entries added 2026-08-12 — Vertical Slice ARB

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/engineering-memory/ARB_REVIEW_VERTICAL_SLICE_V1.md` | ARB Review | ACTIVE | ARB-REV-005: Implementation Gate + First Content Vertical Slice (promts/3.md). VERDICT **READY WITH ADAPTERS** — proceed per §27 implementation sequence (register-first, CREATE 3 files: scripts_01/opportunity_engine.py, scripts_01/whim_capture.py, data_13/opportunities.yaml; 0 production modifications, 7 inline adapters, 0 STOP conditions). Cross-refs: INTELLIGENCE_FACTORY_CONTRACT_V1, FACTORY_FORGE_ARCHITECTURE_V1 §17.1+§20, RECONCILIATION_V1 §3 Phase 1, missing_registry 15 entries (opportunity_engine=prompt_written). Reviewer: Buffy + thinker-with-files-gemini 10-step conformance, 2026-08-12. |

Bump: ACTIVE 94 → 95 (1 новый: ARB_REVIEW_VERTICAL_SLICE_V1.md, 2026-08-12).

### ACTIVE entries added 2026-08-12 — Phase 1.1 closed

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `scripts_01/opportunity_engine.py` | Implementation | ACTIVE | Phase 1.1 vertical slice — Missing Capability #8 (`opportunity_engine`), mark-implemented v5.187.7. Lifecycle ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED/FAILED, additive (CAN-16) — 0 production changes к 8 DO NOT TOUCH файлам, lazy G0 imports, JSON-stdout discipline, 29 passed pytests, ARB-REV-005 READY WITH ADAPTERS verdict honoured. Cross-refs: ARB_REVIEW_VERTICAL_SLICE_V1.md + INTELLIGENCE_FACTORY_CONTRACT_V1 §E persistence decision (lifecycle in YAML, content in KO). |
| `tests_09/test_opportunity_engine.py` | Tests | ACTIVE | Phase 1.1 vertical slice — 29 pytests passed (state-graph coverage + DEFERRED preservation + FAILED retry + dry-run safety + vocab safety + JSON discipline + atomic write). |
| `data_13/opportunities.yaml` | Schema | ACTIVE | Phase 1.1 lifecycle persistence — schema header (16 полей per CONTRACT §E), empty store seed before first discover. |

Bump: ACTIVE 95 → 96 (1 implementation + 1 test + 1 schema, 2026-08-12).

### ACTIVE entries added 2026-08-12 — Phase 1.2 closed

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `pompts_11/080_19_whim_capture_capability.md` | Prompt | ACTIVE | Register-first prompt for Missing Capability #9 (`whim_capture`); FSM design + Russian morphology stem-fix rationale + ANTI-6b vocab safety contract. |
| `scripts_01/whim_capture.py` | Implementation | ACTIVE | Phase 1.2 vertical slice — Missing Capability #9 (`whim_capture`), mark-implemented v5.187.8. Lifecycle NEW/TRIAGED/PROMOTED_TO_OPPORTUNITY/DISCARDED/DEFERRED/FAILED, lazy hook to `opportunity_engine` (CAN-16 additive — 0 production changes), atomic `.tmp`+`os.replace` YAML persistence, Russian-stem keyword whitelist (`книг`/`стать`/`стратег`/`сери`/`обуч`/`план`), 7 CLI subcommands (`capture`/`list`/`status`/`triage`/`promote`/`defer`/`get`), `--json` discipline + exit codes 0/1/2, 39 pytests green. Cross-refs: ARB_REVIEW_VERTICAL_SLICE_V1.md + INTELLIGENCE_FACTORY_CONTRACT_V1 §G + FORENSICS_CI_REPORT_V1.md §I + FORENSICS_CI_FOLLOWUP_V1.md Phase 1.2. |
| `tests_09/test_whim_capture.py` | Tests | ACTIVE | Phase 1.2 vertical slice — 39 pytests passed (~8.4s): state-graph coverage (NEW→TRIAGED→PROMOTED, blocking NEW→PROMOTED, terminal-block PROMOTE/DISCARDED, FAILED→NEW retry, DEFERRED preservation through retriage) + Russian-stem-inflection coverage + lazy-hook integration (monkeypatched `OpportunityStore.DEFAULT_DATA_PATH`) + CLI JSON parseability + exit codes + ANTI-6b vocab safety (`whim_capture ∉ KNOWN_CAPABILITIES`) + atomic-write no `.tmp` leak + corrupt-YAML graceful recovery. |
| `data_13/whims.yaml` | Schema | ACTIVE | Phase 1.2 lifecycle persistence — `_schema` header (per `promt 080_19` §3.4), empty store seed before first capture. |

Bump: ACTIVE 96 → 97 (1 prompt + 1 implementation + 1 test + 1 schema, 2026-08-12, v5.187.8).

### ACTIVE entries added 2026-08-12 — Prompt 4 Architecture–Code Sync Layer (v5.189.2)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md` | Artifact A | ACTIVE | Промт 4 §19-A (CODE MAP / Phase A Inventory): машиночитаемая карта кода — 25 `@entity` records (entity_id/type/file/symbol/public API/callers/dependencies/events/storage/tests/docs), секции §A.1–A.6. Cross-refs: Artifact B/D/E/I/L, SEMANTIC_ANCHOR_SPEC §I.3. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/DOCUMENTATION_CODE_MAP_V1.md` | Artifact B | ACTIVE | Промт 4 §19-B (DOC MAP / Phase B Inventory): 19 doc records (document_id/title/claims/entities/contracts/references/status), `doc.*` anchors. Cross-refs: Artifact A/E/I. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | Artifact C | ACTIVE | Промт 4 §19-C/§10 (CONTRACT REGISTRY): 14 контрактов (contract_id/name/purpose/producer/consumer/input/output/errors/events/storage/implementation/tests/documentation/status), канонический шаблон §C.3. Cross-refs: Artifact A/E/G/L. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/ARCHITECTURE_DECISION_REGISTRY_V1.md` | Artifact D | ACTIVE | Промт 4 §19-D/§11 (DECISION REGISTRY): 14 формальных ADR (statement/reason/source/affected_entities/status/supersedes/implementation_status), 27 `@decision` anchors, решения отделены от фактов. Cross-refs: Artifact A/E/I. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/TRACEABILITY_GRAPH_V1.md` | Artifact E | ACTIVE | Промт 4 §19-E/§8 (TRACEABILITY GRAPH): ~60 nodes + 85 edges + 19 relation types (DOCUMENTS/IMPLEMENTS/CALLS/EMITS/STORES/VALIDATED_BY/CONTRADICTS…), golden path scenario execution §E.4. Cross-refs: Artifact A/B/C/D/I. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/AGENT_NAVIGATION_MAP_V1.md` | Artifact F | ACTIVE | Промт 4 §19-F/§12–§13 (AGENT NAVIGATION MAP): 10 anchored capabilities, chain capability→entrypoint→script→contract→docs→tests, AGENT-RETURNS блок §13, cardinality invariants §F.2.3. Cross-refs: Artifact A/C/K/L. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/ARCHITECTURE_GAP_MAP_V1.md` | Artifact G | ACTIVE | Промт 4 `projects_17/content_factory/promts/4.md` §19-G (GAP MAP): платформенный gap map — 24/25 `@entity` CURRENT, 1 DESIGN_ONLY (`scenario.engine`); контракты все реализованы; gaps §G.6 приоритизированы. Cross-refs: Artifact A (§A.6), Artifact C, §20 FACTORY_FORGE_ARCHITECTURE_V1.md, missing_registry. |
| `docs_10/engineering-memory/DOCUMENTATION_CONSISTENCY_REPORT_V1.md` | Artifact H | ACTIVE | Промт 4 §19-H (CONSISTENCY REPORT): 5 реальных находок consistency_check (H-1 naming `prompts_11`, H-2 naming `promt81.md`, H-3 CHANGELOG 2742→2823, H-4 CQS 2742→2823, H-5 `doc_code_verify` не в §20) + классификация §9 промта. 5 находок закрыты (v5.189.2: H-3/H-4/H-5; v5.189.3: H-1/H-2). |
| `docs_10/engineering-memory/SEMANTIC_ANCHOR_SPEC_V1.md` | Artifact I | ACTIVE | Промт 4 §19-I/§5–§7 (SEMANTIC ANCHOR SPEC): 19 namespaces (15 base + 4 `@lesson`), format rules §I.2, AnchorResolver lookup §I.3, usage rules §I.4. Реализация: `core_02/anchors_resolver.py` + check #11 (v5.189.4). Cross-refs: Artifact A/C/F/L. Зарегистрирован финальным аудитом v5.189.5 (существовал, но отсутствовал в реестре). |
| `docs_10/engineering-memory/CODE_DOCUMENTATION_SYNC_SPEC_V1.md` | Artifact J | ACTIVE | Промт 4 §19-J (SYNC SPEC): нормативная спека на работающий `core_02/doc_code_verify.py` (register-first `doc_code_verify`, промт `pompts_11/082_19_doc_code_sync.md` — канон v5.189.3, 30 тестов): пайплайн 5 шагов, classification CONFIRMED/STALE/DOC_ONLY/UNKNOWN, CLI contract, CI-интеграция WARN/--strict. |
| `docs_10/engineering-memory/AI_REPOSITORY_NAVIGATION_SPEC_V1.md` | Artifact K | ACTIVE | Промт 4 §19-K (NAVIGATION SPEC): 3-layer retrieval (structured index / vector knowledge_engine / graph_index), capability→entrypoint таблица (14 записей, все с code evidence), query→answer шаблон §K.4, anti-hallucination §K.5. |
| `docs_10/engineering-memory/IMPLEMENTATION_PLAN_V1.md` | Artifact L | ACTIVE | Промт 4 §19-L/§20 (IMPLEMENTATION PLAN): фазы A–H (goal/files/reuse/new-code/complexity/risks/tests/acceptance) — фактический отчёт о закрытом слое; register-first `doc_code_verify`; next steps (H-1/H-2 ✅ CLOSED v5.189.3; mark-implemented, AnchorResolver). |

Bump: ACTIVE 97 → 102 (5 новых артефактов промта 4 — G/H/J/K/L, 2026-08-12, v5.189.2); финальный аудит v5.189.5 добавил 7 существовавших артефактов A/B/C/D/E/F/I (реестровый gap закрыт) → ACTIVE 102 → 109.

### ACTIVE entries added 2026-08-22 — Public Request Parser scaffold

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `public-request-parser-spec.md` | Specification | DRAFT | Canonical product/architecture specification created after multi-round user interview and source research; code not started |
| `projects_17/public_request_parser/MANIFEST.md` | Manifest | DRAFT | Project-local passport; universal parser boundary, RSS/Atom first, Telegram fixture-only |
| `projects_17/public_request_parser/README.md` | README | DRAFT | Project navigation and scope |
| `projects_17/public_request_parser/SPEC.md` | Specification pointer | DRAFT | Project-local entry point to canonical root specification |
| `projects_17/public_request_parser/ROADMAP.md` | Roadmap | DRAFT | Full lifecycle P0–P19: source matrix → MVP → pilot → hardening → multi-tenant → beta → production v1.0 → evolution |
| `projects_17/public_request_parser/SOURCE_POLICY_MATRIX.md` | Research/Policy | ACTIVE | P2 source matrix: technical candidates, conditional/manual-review/blocked statuses, evidence; G2 closed conditional — SRC-011 HeadHunter API allowed (ADR-011) |
| `projects_17/public_request_parser/STEPS.md` | Steps | ACTIVE | Actual scaffold creation log |
| `projects_17/public_request_parser/LESSONS.md` | Lessons | ACTIVE | Project-local boundary, policy and retention findings |
| `projects_17/public_request_parser/RUNNABLE.md` | Runnable | DRAFT | Documentation-only current launch status and planned CLI contract |
| `projects_17/public_request_parser/CHECKLIST.md` | Checklist | DRAFT | Scaffold, pre-flight and future acceptance gates |
| `projects_17/public_request_parser/project.yaml` | Project metadata | DRAFT | Workspace/Forge metadata for `public_request_parser` |
| `projects_17/public_request_parser/decisions/DECISIONS.md` | Decisions-index | ACTIVE | Project-local ADR index |
| `projects_17/public_request_parser/decisions/ADR-001_parser_boundary_and_source_gates.md` | ADR | ACTIVE | Separate universal parser; RSS/Atom first; Telegram fixture-only until approval |
| `projects_17/public_request_parser/decisions/ADR-002_source_status_and_first_candidate.md` | ADR | ACTIVE | Separate technical candidate from production `allowed`; Stack Overflow Atom fixture candidate; Telegram live blocked |
| `projects_17/public_request_parser/DOMAIN_CONTRACTS.md` | Contract | ACTIVE | P3 typed domain entities, policy/retention invariants and infrastructure ports |
| `projects_17/public_request_parser/app/domain/contracts.py` | Implementation | ACTIVE | P3 project-local typed contracts; no network access or platform imports |
| `projects_17/public_request_parser/tests/test_domain_contracts.py` | Tests | ACTIVE | P3 hermetic contract tests; 10 passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-003_domain_contracts_and_error_boundaries.md` | ADR | ACTIVE | Typed domain boundary and separate policy/adapter/match/delivery error semantics |
| `projects_17/public_request_parser/RSS_ATOM_ENGINE.md` | Implementation | ACTIVE | P4 parser/normalization/dedup/checkpoint API and boundaries |
| `projects_17/public_request_parser/app/rss_atom/engine.py` | Implementation | ACTIVE | P4 fixture-based RSS/Atom engine; no network or live polling |
| `projects_17/public_request_parser/tests/test_rss_atom.py` | Tests | ACTIVE | P4 hermetic fixture tests; 8 passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-004_rss_atom_fixture_engine.md` | ADR | ACTIVE | RSS/Atom fixture engine boundary; transport/live polling left to later gates |
| `projects_17/public_request_parser/MATCHING_ENGINE.md` | Implementation | ACTIVE | P5 matcher API: rules, intent gate, score formula, explainability and open limits |
| `projects_17/public_request_parser/app/matcher/engine.py` | Implementation | ACTIVE | P5 deterministic RuleMatcher; word forms, phrases, synonyms, exclusions, intent gate; no network or LLM |
| `projects_17/public_request_parser/tests/test_matcher.py` | Tests | ACTIVE | P5 hermetic matcher tests; 14 passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-005_deterministic_matcher_and_intent_gate.md` | ADR | ACTIVE | Deterministic rule matcher, hard rejects with score 0, intent gate; LLM scoring deferred to P14 |
| `projects_17/public_request_parser/STORAGE.md` | Implementation | ACTIVE | P6 SQLite/WAL storage: schema v1, idempotency, TTL cleanup, checkpoints |
| `projects_17/public_request_parser/app/storage/sqlite.py` | Implementation | ACTIVE | P6 SqliteStorage + SqliteCheckpointStore; WAL, user_version migrations, TTL cleanup; no network |
| `projects_17/public_request_parser/tests/test_storage_sqlite.py` | Tests | ACTIVE | P6 hermetic storage tests; 14 passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-006_sqlite_wal_storage_and_retention.md` | ADR | ACTIVE | SQLite/WAL storage, UNIQUE dedup, TTL cleanup only content; multi-tenant isolation deferred to P13 |
| `projects_17/public_request_parser/DELIVERY.md` | Implementation | ACTIVE | P7 delivery contract: HTML cards, dry-run, idempotency, retry, owner gate |
| `projects_17/public_request_parser/app/delivery/__init__.py` | Implementation | ACTIVE | P7 render_card, MessageTransport protocol, TelegramDelivery; no network, no credentials |
| `projects_17/public_request_parser/tests/test_delivery.py` | Tests | ACTIVE | 11 hermetic delivery tests; passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-007_delivery_contract_and_idempotency.md` | ADR | ACTIVE | Delivery contract: escape renderer, dry-run, idempotent key, retry only failed, owner gate |
| `projects_17/public_request_parser/POST_MVP_GATES.md` | Roadmap | ACTIVE | P10–P19 honest statuses: done/partial/blocked with evidence; G2 closed conditional (HH API), P10 Ready — activation pending |
| `projects_17/public_request_parser/app/pipeline/__init__.py` | Implementation | ACTIVE | P8 offline pipeline: adapter → normalize → store → match → deliver, checkpoint resume |
| `projects_17/public_request_parser/app/cli.py` | Implementation | ACTIVE | P8 CLI: `--once` (fixture run) and `--maintenance` (TTL+backup) |
| `projects_17/public_request_parser/app/tgpreview/__init__.py` | Implementation | ACTIVE | P9 Telegram web-preview fixture adapter; ALLOWED policy forbidden |
| `projects_17/public_request_parser/app/adapters/http_feed.py` | Implementation | ACTIVE | P12 gated HTTP feed transport: live only for ALLOWED + can_poll |
| `projects_17/public_request_parser/tests/test_pipeline.py` | Tests | ACTIVE | P8 pipeline tests (idempotency, TTL card retention, backup) |
| `projects_17/public_request_parser/tests/test_tgpreview.py` | Tests | ACTIVE | P9 fixture adapter tests |
| `projects_17/public_request_parser/tests/test_http_feed.py` | Tests | ACTIVE | P12 gated transport tests |
| `projects_17/public_request_parser/tests/test_multi_tenant.py` | Tests | ACTIVE | P13/P14 owner isolation + feedback + v1→v2 migration tests |
| `projects_17/public_request_parser/decisions/ADR-008_lead_aggregator_review_remain_separate.md` | ADR | ACTIVE | P15: remain separate (evidence-based field comparison) |
| `projects_17/public_request_parser/decisions/ADR-009_platformization_boundary_deferred.md` | ADR | ACTIVE | P16: platformization deferred until live-use evidence; candidates recorded |
| `projects_17/public_request_parser/CALIBRATION.md` | Implementation | ACTIVE | P14 feedback→threshold calibration: deterministic, no auto-apply |
| `projects_17/public_request_parser/app/calibration/engine.py` | Implementation | ACTIVE | P14 ThresholdCalibrator + optimal_accept_threshold (accuracy over observed scores) |
| `projects_17/public_request_parser/tests/test_calibration.py` | Tests | ACTIVE | 5 hermetic calibration tests; passed on 2026-08-23 |
| `projects_17/public_request_parser/decisions/ADR-010_feedback_calibration_determinism.md` | ADR | ACTIVE | Calibration determinism, no auto-apply; apply via new profile version |
| `projects_17/public_request_parser/tests/test_e2e_tg_pipeline.py` | Tests | ACTIVE | E2E full pipeline with TG fixture: accept/reject, idempotency, offer gate, card без author; 5 tests |
| `projects_17/public_request_parser/decisions/ADR-011_g2_first_allowed_source_headhunter_api.md` | ADR | ACTIVE | G2 closed conditional: HeadHunter API = first allowed source (developer agreement + OpenAPI evidence); activation = app+key+canary; Telegram stays blocked |

### ACTIVE entries added 2026-08-10 (v5.147.0)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md` | Template | ACTIVE | Протокол миграции проекта из платформы с сохранением решений; конвенция project-local ADR; закрывает PLATFORM.md:493 |
| `projects_17/lead_aggregator/decisions/DECISIONS.md` | Decisions-index | ACTIVE | Индекс project-local ADR lead_aggregator (ADR-001…003: pull-модель, юр. гейт, контракты-адаптеры) |
| `projects_17/lead_aggregator/decisions/ADR-001_pull_model_and_source_order.md` | ADR | ACTIVE | Project-local: pull-модель + порядок источников (provenance: ADR_014 platform) |
| `projects_17/lead_aggregator/decisions/ADR-002_legal_gate_readonly.md` | ADR | ACTIVE | Project-local: юр. гейт read-only (W-7) |
| `projects_17/lead_aggregator/decisions/ADR-003_adapter_contracts_embedding.md` | ADR | ACTIVE | Project-local: контракты-адаптеры вместо платформенных импортов |

Bump: ACTIVE 86 → 88 (реестровые записи: шаблон + индекс; ADR-001…003 — внутри каталога проекта).

### ACTIVE entries added 2026-08-10 (v5.145.0–v5.146.0)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `docs_10/engineering-memory/decisions/ADR_013_Forge_Facade_Blueprint_v3_Bridge.md` | ADR | ACTIVE | ForgeFacade (071_02_prompt_architect_1_7 Миссия 2, §7.6 gap 2 closed); 14 pipeline-ролей; §7.3 boundary сохранён |
| `docs_10/engineering-memory/decisions/ADR_014_Lead_Aggregator_Attract_Module.md` | ADR | ACTIVE | Attract-модуль (070_07_lead_aggregator_scraper × 70); IDEA EXPLORER Candidate A; pull-модель; юр. гейт W-7 |
| `docs_10/engineering-memory/decisions/ADR_017_Unified_Workspace_Model.md` | ADR | ACTIVE | Единая Workspace модель (promt107 §N P0-блокер): SQLite registry = source-of-truth для path→workspace mapping/privacy; YAML = декларативный конфиг (steps_policy и пр.); аддитивный sync-контракт YAML→SQLite (one-way, idempotent, additive). **Реализован (v5.189.83):** `WorkspaceRegistry.sync_from_config()` + `SyncReport` dataclass + 13 hermetic тестов |
| `docs_10/engineering-memory/decisions/ADR_018_Factory_Forge_Execution_Bridge.md` | ADR | DRAFT | Factory→Forge execution bridge (P1 контракт): фиксирует УЖЕ существующий мост (Path B REAL: opportunity_engine.py:941, factory_base.py:361, forge.py:490); forge_id адвизорный, исполнение по role_ids; + 6 hermetic тестов маппинга (отдельный заход). Cross-refs: ARCHITECTURAL_BASELINE_V1.md §1/§4, ADR-013 |
| `docs_10/engineering-memory/decisions/ADR_019_Agent_Base_Class.md` | ADR | ACTIVE | Agent base class + lifecycle (P1 контракт, baseline §3): единая сущность «Агент» — композиция ролей, capability→SmartRouter роутинг, ForgeFacade единственный мост, forward-only lifecycle CREATED→ACTIVE→PAUSED→DONE/FAILED. **Реализован (v5.189.80):** `core_02/agent_base.py` + `tests_09/test_agent_base.py` (29 тестов) |
| `docs_10/engineering-memory/decisions/ADR_020_Integration_Adapter_Boundary.md` | ADR | ACTIVE | Integration adapter boundary (P1 контракт, baseline §3): единая граница для TG/MCP/phone — AuthSpec (none/bearer/vault/chat_id_scope) + intent→capability роутинг (закрытый словарь) + нормализация входов; аддитивно, мосты не переписываются. **Реализован (v5.189.81):** `core_02/integration_base.py` + `tests_09/test_integration_base.py` (33 теста) |
| `core_02/integration_base.py` | Core Code | ACTIVE | IntegrationAdapter (ABC) — единый контракт для внешних мостов (ADR-020): AuthSpec, AdapterRequest/Response, INTENT_CAPABILITY_MAP, call_platform через SmartRouter (§7.3) |
| `docs_10/engineering-memory/decisions/ADR_021_Artifact_Contract.md` | ADR | ACTIVE | Unified Artifact contract (P2): canonical frozen dataclass + adapters для файл ↔ dict ↔ ChainRun; `factory_base.normalize_output` подключён без изменения сигнатуры; 13 hermetic-тестов |
| `docs_10/engineering-memory/ARCHITECTURAL_BASELINE_V1.md` | Canon | ACTIVE | Канонический архитектурный baseline (сводный вывод FORENSICS_104_105_106_107 v5.189.75, code-verified): «что система (Forge-слой + Path A/B REAL) / набор механизмов (memory ×4, role ×2, task ×2, tool ×2, registry ×6) / DOCUMENTED ONLY (Agent, Integration, sandbox) / чего не хватает (P0-P4 с ADR-маппингом)». Единая точка отсчёта для ADR-017…020 и будущих решений |
| `docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md` | Design | ACTIVE | Facade design (Задача 1) + impl notes (Задача 2); таблица соблюдения границ промт 70 п.1-3 |
| `docs_10/engineering-memory/P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md` | Research | ACTIVE | Задача 0: role-by-role аудит 17 ролей registry.yaml; 15/17 производственные стадии; auto-discovery прецедент |
| `projects_17/lead_aggregator/MANIFEST.md` | Manifest | ACTIVE | Паспорт проекта lead_aggregator (конвенция платформы, как diet_platform/realtor_os) |
| `projects_17/lead_aggregator/IDEA_EXPLORER_RUN.md` | Research | ACTIVE | Прогон IDEA EXPLORER v2.0 (промт 70 встроенный): 7 веток → 3 кандидата → A |
| `projects_17/lead_aggregator/PROMT_ARCHITECT_RUN.md` | Prompt | ACTIVE | Прогон ПРОМТ АРХИТЕКТОР 1.7 (промт 70 встроенный): исполнимый base prompt для Фазы 3 |

Bump: ACTIVE 79 → 86 (7 новых; ADR-013/014 — 13-14-й ADR платформы). Примечание: bump выполнен в v5.146.0 (v5.145.0 реестр не бумпался); P3-дизайн/исследование — v5.145.0, ADR/MANIFEST/прогоны — v5.146.0.

## Сводка (подсчёт по таблицам выше)

| Статус | Кол-во файлов | Состав |
|--------|---------------|--------|
| ACTIVE | 109 + каталоги | **Актуальный счётчик — bump-trail (v5.144.0: 77→79; v5.146.0: 79→86; v5.147.0: 86→88; v5.145.0 реестр не бумпался; v5.189.2: 97→102; v5.189.5: 102→109 — промт 4 A–L полный набор).** Legacy-состав ниже: (+1: ROADMAP_VV_002_RESEARCH.md — промт 63) +2: visual/diagrams/{vv_001_to_vv_002.mmd, forge_line.mmd***REMOVED*** (Mermaid git-renderable, 2026-08-06); +8: engineering-memory (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V2.md v1.3 + AUDIT_WS_OS_P65_§4_V1.md + AUDIT_WS_OS_P65_§5_V1.md + AUDIT_WS_OS_P65_§6_V1.md + AUDIT_WS_OS_P65_§9_V1.md + AUDIT_WS_OS_P65_§10_V1.md + AUDIT_WS_OS_P65_§11_V1.md| NEW 2026-08-09 — §11 Multi-Agent System audit pass | active |
| AUDIT_WS_OS_P65_§13_V1.md | NEW 2026-08-09 — §13 Different AI Providers audit pass | active | + AUDIT_WS_OS_P65_RECAP.md v1.3, 2026-08-09); корень 11 + docs_10/ 4 (+2 Mermaid diagrams) + history 5 + core 21 + audits 9 (+1 §10 audit) + decisions 2 + vision 4 + pompts 19 + engineering-memory 14 (RFC ×4 + ARB Review ×1 + Manifest ×1 + Inventory ×1 + Research ×1 + Audit ×9 + Recap ×1); каталоги целиком: engineering-memory, ops, plugin, projects_meta |
| AUDIT_WS_OS_P65_§14_V1.md | NEW 2026-08-09 — §14 Agent as a Worker audit pass | active | (new audit, same v5.112.0 base) |
| AUDIT_WS_OS_P65_§15_V1.md | NEW 2026-08-09 - section 15 Long-Lived Project audit pass | active | 16 primary + 8 secondary + 5 gaps |
| LEGACY | 28 | core 2 (ARCHITECTURE_3.0, ARCHITECTURE_REVIEW) + decisions 1 (ADR_001 full) + vision 2 (ROADMAP, ROADMAP_PROMT31) + pompts 17 |
| ARCHIVED | 21 + каталоги | docs_10/DRIFT_REPORT 1 + audits 11 + vision/archive 2 + trash 7; каталоги: session_dumps, task_archive |
| DRAFT | 1 | audits 1 (AUDIT_TEMPLATE) |
| OBSOLETE | 0 | Артефакты pompts_11/ перенесены в trash_21/ (Этап 5) |

---

_Связанные документы: [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(vision/ROADMAP_PROMT32_CONSOLIDATION.md) (Этап 4), [INDEX.md***REMOVED***(INDEX.md), [ARCHITECTURE_MANIFEST.md***REMOVED***(core/ARCHITECTURE_MANIFEST.md) (§6 Архивация), [LIFECYCLE.md***REMOVED***(core/LIFECYCLE.md) (стадия Архивация)_

| [AUDIT_WS_OS_P65_§16_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§16_V1.md) | v1.0 (2026-08-09) | ACTIVE | §16 Memory claim-by-claim audit per 09_audit_promt64 pattern (15-20 claims, TRUST 7.5-9.0/10) |

| [AUDIT_WS_OS_P65_§17_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§17_V1.md) | v1.0 (2026-08-09) | ACTIVE | §17 Learning Loop claim-by-claim audit per 09_audit_promt64 pattern (18-22 claims, TRUST 7.5-9.0/10) |

| [AUDIT_WS_OS_P65_§18_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§18_V1.md) | v1.0 (2026-08-09) | ACTIVE | §18 Artifact claim-by-claim audit per 09_audit_promt64 pattern (20-25 claims, TRUST 7.5-9.0/10) |

| [AUDIT_WS_OS_P65_§19_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§19_V1.md) | v1.0 (2026-08-09) | ACTIVE | §19 E&P claim-by-claim audit (20-25 claims, TRUST 7.5-9.0/10) |

| [AUDIT_WS_OS_P65_§20_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§20_V1.md) | v1.0 (2026-08-09) | ACTIVE | §20 Decision System claim-by-claim audit (25-30 claims, TRUST 6.5-8.5/10) |

| [AUDIT_WS_OS_P65_§21_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§21_V1.md) | v1.0 (2026-08-09) | ACTIVE | §21 Feedback claim-by-claim audit (20-25 claims, TRUST 7.5-9.0/10) |
| 81 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §22 Operating Environment (Workspace as OS) | Phase 2 COMPR v2.4 · 5 gaps G-OP-1..5 · RECAP R-68..R-72 |

| AUDIT_WS_OS_P65_§22_V1 | engineering-memory | claim-by-claim audit §22, TRUST 7.3/10, R-68..R-72 + cross-link §15/§16/§17/§18/§19/§20/§21 | 2026-08-09 |
| 82 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §23 Cross-Factory Orchestration | Phase 2 COMPR v2.5 · 5 gaps G-CFO-1..5 · RECAP R-78..R-82 |

| AUDIT_WS_OS_P65_§23_V1 | engineering-memory | claim-by-claim audit §23, TRUST 8.2/10, R-78..R-82 + cross-link §15/§16/§17/§18/§19/§20/§21/§22 | 2026-08-09 |
| 83 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §24 Reusability ♻️ | Phase 2 COMPR v2.6 · 5 levels · 5 gaps G-REU-1..5 · RECAP R-83..R-87 |

| AUDIT_WS_OS_P65_§24_V1 | engineering-memory | claim-by-claim audit §24, TRUST 7.9/10, R-83..R-87 + cross-link §15/§16/§17/§18/§19/§20/§21/§22/§23 | 2026-08-09 |
| 84 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §25 Security & Governance 🔐 | Phase 2 COMPR v2.7 · 4-Layer Sec · 5 gaps (2 Critical) · RECAP R-88..R-92 |

| AUDIT_WS_OS_P65_§25_V1 | engineering-memory | claim-by-claim audit §25, TRUST 9.1/10, R-88..R-92 + 2 Critical G-SEC-3/5 + cross-link §15-§24 | 2026-08-09 |
| 85 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §26 Failure Modes 💥 | Phase 2 COMPR v2.8 · 12 layers · 30 FMs F001-F030 · RECAP R-93..R-97 |

| AUDIT_WS_OS_P65_§26_V1 | engineering-memory | claim-by-claim audit §26, TRUST 8.0/10, R-93..R-97 + 30 F001-F030 cataloged + cross-link §15-§25 | 2026-08-09 |
| 86 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §27 Overengineering Audit 🪞 | Phase 2 COMPR v2.9 · 17 levels audited · 7 CORE/5 USEFUL/3 OPT/2 PRE · RECAP R-98..R-102 |

| AUDIT_WS_OS_P65_§27_V1 | engineering-memory | claim-by-claim audit §27, TRUST 8.0/10, R-98..R-102 + 17 levels verdicts + 2 PREMATURE identified + cross-link §15-§26 | 2026-08-09 |
| 87 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §28 Real-World Stress Test 🏋️ | Phase 2 COMPR v2.10 · 5 work-types · 20%/40%/40% ready · RECAP R-103..R-107 |

| AUDIT_WS_OS_P65_§28_V1 | engineering-memory | claim-by-claim audit §28, TRUST 8.5/10, R-103..R-107 + WT2+WT5 Critical gaps + stress-test protocol + cross-link §15-§27 | 2026-08-09 |
| 88 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §29 Architectural Vertical Revision 🏗️ | Phase 2 COMPR v2.11 · Model A canonical · 8 aspects · 5 gaps G-29-1..5 · RECAP R-108..R-112 |

| AUDIT_WS_OS_P65_§29_V1 | engineering-memory | claim-by-claim audit §29, TRUST 8.0/10, R-108..R-112 + Model A canonical decision + cross-link §15-§28 | 2026-08-09 |
| 89 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §30 Full VkusVill Pipeline 📦 | Phase 2 COMPR v2.12 · 28 stages · 89% done · 50+ files · RECAP R-113..R-117 |

| AUDIT_WS_OS_P65_§30_V1 | engineering-memory | claim-by-claim audit §30, TRUST 8.2/10, R-113..R-117 + 28 stages aggregation + cross-link §4/§5/§21/§28/§29 | 2026-08-09 |
| 90 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §31 Definition of Workspace OS 📐 | Phase 2 COMPR v2.13 · final def locked · 5 candidates · 8 aspects · RECAP R-118..R-122 |

| AUDIT_WS_OS_P65_§31_V1 | engineering-memory | claim-by-claim audit §31, TRUST 8.0/10, R-118..R-122 + Final Definition + cross-link §15-§30 | 2026-08-09 |
| 91 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §32 Architectural Boundaries 🧱 | Phase 2 COMPR v2.14 · 14 boundaries · 5 B-Rules · doctrine locked · RECAP R-123..R-127 |

| AUDIT_WS_OS_P65_§32_V1 | engineering-memory | claim-by-claim audit §32, TRUST 8.0/10, R-123..R-127 + 14 boundaries + 5 B-Rules + cross-link §15-§31 | 2026-08-09 |

| AUDIT_WS_OS_P65_§33_V1 | engineering-memory | claim-by-claim audit §33, TRUST 8.5/10, R-128..R-132 + 23 quality gates + 5 critical gaps + v3.0 APEX + cross-link §15-§32 | 2026-08-09 |
| 93 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §34 First Vertical Slice 🪜 | Phase 4 OPEN · Candidate 3 winner · ~200 LOC · 5 G-34-N · RECAP R-138..R-142 |

| AUDIT_WS_OS_P65_§34_V1 | engineering-memory | claim-by-claim audit §34, TRUST 8.0/10, R-138..R-142 + Candidate 3 + 8-aspect scoring + cross-link §15-§33 | 2026-08-09 |
| 94 | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md | engineering-memory | §35 ТОП-10 рисков ⚠️ | Phase 4 §35 done · 10 risks · 117 score · 4 Critical pending · RECAP R-143..R-147 |

| AUDIT_WS_OS_P65_§35_V1 | engineering-memory | claim-by-claim audit §35, TRUST 8.0/10, R-143..R-147 + 10 risks ranked + 4 Critical Phase 4 closure | 2026-08-09 |

| `AUDIT_WS_OS_P65_§36_V1.md` (planned in §37 work) | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | §36 — 4 YES/NO/PARTIALLY verdicts (Q1-Q4) on Workspace OS = Operating Environment | NEW (audit pending) |
| `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §36 | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | Финальный вердикт (4 главных вопроса) | FILLED Phase 4 ~40 мин |
| `AUDIT_WS_OS_P65_§37_V1.md` (planned in §38 work) | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | §37 — 17-layer corrected architecture + 18 boundary compliance | NEW (audit pending) |
| `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §37 | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | Финальная архитектура (исправленная карта) | FILLED Phase 4 ~90 мин |
| `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §38+§39 | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | §38 (14-Q gate) + §39 (Mission final eval) — Phase 4 CLOSED | FILLED Phase 4 final ~90 мин |
| `MISSION_CLOSE_20260809.md` | 2026-08-09 | WORKSPACE-OS-RSRCH-001 | Phase 4 FINAL CLOSE summary handoff | NEW |
| `core_02/dis_engine.py` | 2026-08-09 | core_02 | DIS v0.2 governance scaffolding (DIRSReviewer + ConflictAnalyzer + TechnicalDebtAnalyzer + PolicyChecker) - 7-criterion ARE scoring per RFC_DECISION_INTELLIGENCE_SYSTEM_V1 §4.1 | NEW |
| `tests_09/test_dis_engine_v1.py` | 2026-08-09 | core_02 | 7-test DIS audit (ReviewScore weighted-sum + ConflictAnalyzer dedup + TDA hardcode + PC blocking rule + PC compliance + idempotency + known-rfc-score-8) | NEW |
| `tests_09/test_graph_index_v2.py` | 2026-08-09 | core_02 | 6-test graph_index v0.2 audit (link + idempotency + interlink vkusvill_research + non-existent path + extension filter + version chain) | NEW |

### ACTIVE entries added 2026-08-22 (v5.189.72) — phone_control_mcp BaseTool.input_schema (НЕ pydantic)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `scripts_01/phone_control_mcp.py::BaseTool.input_schema()` | Method | ACTIVE | Кастомный метод (НЕ pydantic API): класс `BaseTool` не наследует `pydantic.BaseModel`; метод возвращает plain `dict` для ключа `inputSchema` MCP `tools/list`. Переименован из `schema()` в v5.189.72, чтобы снять name-collision с pydantic v1 `BaseModel.schema()` (deprecated в pydantic 2.x). Cross-refs: CHANGELOG v5.189.72; `tests_09/test_phone_control_mcp.py` |

### ACTIVE entries added 2026-08-22 (v5.189.75) — сводный forensic-архив v5.189.75 (Path B REAL + AUDIT_DELTA)

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `FORENSICS_104_105_106_107_v5.189.82.tar.gz` | Archive | ACTIVE | Финальная пересборка v5.189.75 с P1-закрытием Agent (ADR-019) + Integration (ADR-020). Состав: `FORENSICS_104_105_106_107/` (README v5.189.82 + `_consolidated/INDEX.md` / `UNIFIED_CONCLUSIONS.md` / `EVIDENCE_LEDGER_MERGED.md` / `AUDIT_DELTA.md` / **`AUDIT_DELTA_v5.189.82.md`** — перечень изменений P1-закрытия) + исходные пакеты `architecture_forensics_v2/` (104), `repository_organization_forensics_32/` (105), `system_model_forensics_33/` (106), `platform_architectural_inventory_34/` (107). Итого 56 файлов. SHA256 `cc90004b81de6f4d7baac6f992080e70380d4d8290f60d00475237e0890c45ba`. Изменено vs v5.189.75: UNIFIED_CONCLUSIONS §3/§4/§5/§6 (Agent + Integration из DOCUMENTED ONLY → IMPLEMENTED, все P1 закрыты), EVIDENCE_LEDGER_MERGED (+2 строки), INDEX.md (+ADR-019/020 в временной линии), README.md + новый AUDIT_DELTA_v5.189.82.md (детали — внутри файла). Cross-refs: CHANGELOG v5.189.82; ADR-019; ADR-020 |
| `FORENSICS_104_105_106_107_v5.189.75.tar.gz` | Archive | LEGACY | Пересборка v5.189.73 с forensic-коррекцией Path B (PARTIAL→REAL) и явной пометкой изменённых файлов для внешнего аудита. Состав: `FORENSICS_104_105_106_107/` (README v5.189.75 + `_consolidated/INDEX.md` + `_consolidated/UNIFIED_CONCLUSIONS.md` + `_consolidated/EVIDENCE_LEDGER_MERGED.md` + **`_consolidated/AUDIT_DELTA.md`** — перечень изменённых файлов) + исходные пакеты `architecture_forensics_v2/`, `repository_organization_forensics_32/`, `system_model_forensics_33/`, `platform_architectural_inventory_34/`. Итого 49 файлов. SHA256 `409d8cd6ec6b07ae75ef9cf3201c2b5b025c6b36d2d132e6286aff4dd8af35b6`. Predecessor: `FORENSICS_104_105_106_107_v5.189.73.tar.gz`. Cross-refs: CHANGELOG v5.189.75; ADR-017 |
| `FORENSICS_104_105_106_107_v5.189.73.tar.gz` | Archive | LEGACY | Объединённый forensic-пакет 4 проходов (промты 104/105/106/107): `FORENSICS_104_105_106_107/` (README + `_consolidated/INDEX.md` кросс-ссылки + `_consolidated/UNIFIED_CONCLUSIONS.md` единый Executive Summary + `_consolidated/EVIDENCE_LEDGER_MERGED.md` слитый журнал доказательств) + исходные пакеты `architecture_forensics_v2/`, `repository_organization_forensics_32/`, `system_model_forensics_33/`, `platform_architectural_inventory_34/`. Итого 48 файлов. SHA256 `12ae654cc580e7fdc6cc92af39947da9bf147095a78d9e2932a4458dcda6ca77`. Cross-refs: CHANGELOG v5.189.73; `pompts_11/104_19_platform_architectural_forensics_v2.md`; `pompts_11/105_19_repository_organization_refactoring_forensics.md`; `pompts_11/106_19_repository_forensics_system_modeling.md`; `pompts_11/107_19_platform_architectural_inventory.md` |

### ACTIVE entries added 2026-08-22 (v5.189.70) — объединённый forensic-архив

| File | Type | Status | Provenance |
|------|------|--------|------------|
| `FORENSICS_104_105_106_COMBINED_v5.189.69.tar.gz` | Archive | ACTIVE | Объединённый deliverable-архив трёх forensic-исследований (промты 104→105→106): `architecture_forensics_v2/` (13 файлов, promt104 Platform Architectural Forensics V2) + `repository_organization_forensics_32/` (3 файла, promt105 Repository Organization Forensics) + `system_model_forensics_33/` (17 файлов, promt106 Repository Forensics System Modeling). Итого 33 файла. SHA256 `6c9cef98249e0537133e7a0469773c2ae89a7e07a5b945ad60c5ddd6e9f0c305`. Cross-refs: CHANGELOG v5.189.70; `pompts_11/104_19_platform_architectural_forensics_v2.md`; `pompts_11/105_19_repository_organization_refactoring_forensics.md`; `pompts_11/106_19_repository_forensics_system_modeling.md` |
