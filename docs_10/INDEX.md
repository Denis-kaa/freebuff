
## v5.144.0 — Phase 3 → Phase 4 BRIDGE (2026-08-09)

- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §33.11-§33.17 (Phase 3 addendum): 5 audit-themes → 5 build-milestones synthesis
- `docs_10/engineering-memory/ROADMAP_MIN_V0_1.md`: 11-section build roadmap (35-day calendar, 7 acceptance criteria)

# Индекс документации Workspace OS

**Обновлено:** 2026-09-04

---

## Структура документации

### Positioning / Vision docs — входная точка для новых читателей
- [PLATFORM.md***REMOVED***(../PLATFORM.md) — что это и зачем (v5.75.0, 2026-08-04; ~6 350 слов, plain language). Канонический positioning-документ платформы.
- [PRODUCT_MANIFESTO.md***REMOVED***(vision/PRODUCT_MANIFESTO.md) — манифест продукта (vision/)

### Реестры / операционные каноны
- RECOMMENDATIONS.md (docs_10/RECOMMENDATIONS.md) — единый append-only реестр рекомендаций платформы (REC-NNN): аудит-фиксы, архитектурные улучшения, ops-гигиена. Источник: AUDIT_TEENFREELANCE_2026-09-04.md (docs_10/audits/, REC-001..020, 2026-09-04). Правило «AUDIT + RECOMMENDATIONS пара» — CON-68 (core_02/LESSONS.md).

### canonical/ — Текущее состояние системы (канон)
- [INDEX.md***REMOVED***(canonical/INDEX.md) — индекс канонических документов
- [architecture.md***REMOVED***(canonical/architecture.md) — иерархия, контракты, позиционирование

### history/ — История решений (ADR)
- [ADR-001_positioning.md***REMOVED***(history/ADR-001_positioning.md) — почему агрегатор, не конкурент
- [ADR-002_contracts.md***REMOVED***(history/ADR-002_contracts.md) — почему JSON-контракты
- [SESSION_UNDERSTANDING_2026-08-02.md***REMOVED***(history/SESSION_UNDERSTANDING_2026-08-02.md) — полная фиксация сессии
- [DAY_SUMMARY_2026-08-02.md***REMOVED***(history/DAY_SUMMARY_2026-08-02.md) — дневная сводка: стратегия + код + проекты
- [SESSION_SUMMARY_2026-08-03.md***REMOVED***(history/SESSION_SUMMARY_2026-08-03.md) — полная фиксация сессии 2026-08-03 (v5.59.0→v5.63.0)
- [DAY_SUMMARY_2026-08-03.md***REMOVED***(history/DAY_SUMMARY_2026-08-03.md) — дневная сводка 2026-08-03
- [DAY_SUMMARY_2026-08-05.md***REMOVED***(history/DAY_SUMMARY_2026-08-05.md) — дневная сводка 2026-08-05 (v5.89.0→v5.91.0: CON-33/35/36, queue cleanup, watcher, interior_planner restore + role registration)

### vision/ — Стратегическое видение
- [VISION_3.0.md***REMOVED***(vision/VISION_3.0.md) — стратегия и цели
- [ROADMAP.md***REMOVED***(vision/ROADMAP.md) — дорожная карта

### projects_meta/ — Сводки по проектам
- [PROJECTS_OVERVIEW.md***REMOVED***(projects_meta/PROJECTS_OVERVIEW.md) — **v5.101.0**: аудит 6 проектов (interior_planner, diet_platform, realtor_os, realtor_automation, freebuff_flutter_app, tg_terminal_messenger)

### core/ — Архитектурные манифесты
- [ARCHITECTURE_MANIFEST.md***REMOVED***(core/ARCHITECTURE_MANIFEST.md) — главный архитектурный закон
- [GLOSSARY.md***REMOVED***(core/GLOSSARY.md) — единый глоссарий терминов
- [ARCHITECTURE_PRINCIPLES.md***REMOVED***(core/ARCHITECTURE_PRINCIPLES.md) — принципы
- [PROJECT_REQUIREMENTS.md***REMOVED***(core/PROJECT_REQUIREMENTS.md) — **v5.98.0**: Стандарт готовности проектов: RUNNABLE.md, CHECKLIST.md, web-фолбэк, Environment Doctor
- [PLAN_NEXT_OPERATIONS.md***REMOVED***(PLAN_NEXT_OPERATIONS.md) — **v5.103.0**: Развёрнутый план следующих операций (7 этапов, 6 проектов, промты)
- [ROADMAP_FORGE_RECONCILIATION.md***REMOVED***(ROADMAP_FORGE_RECONCILIATION.md)
- [ROADMAP_VKUSVILL_DEMO_062.md***REMOVED***(ROADMAP_VKUSVILL_DEMO_062.md) — **ROADMAP-VV-001 v5.105.0 (2026-08-06)**: Промт 62 demo для отклика ВкусВилл — xlsx-skill + модельный .xlsx + Teamwork-разбор 3 роли (analyst/developer/reviewer); parity variant (b) NO LibreOffice; 3 категории (молочка/крупа/напиток); 2 неочевидных (SERVICE_LEVEL_Z=1.65 + INCIDENT_2024_CORRECTION cell-content proxy H22=0.92). Артефакты в `projects_17/vkusvill_demo/` + scenario `runtime_05/scenarios/vkusvill_demo.yaml` |
- [ROADMAP_VV_002_RESEARCH.md***REMOVED***(ROADMAP_VV_002_RESEARCH.md) — **ROADMAP-VV-002 (Stage 0 scaffold 2026-08-06)**: Промт 63 deep-research план по ВкусВилл × AI-Автоматизация (33 секции per pomt63); Tier 1/2/3 source-mining стратегия + anti-hallucination tag protocol per [CON-55***REMOVED***(../core_02/LESSONS.md); 8 файлов-артефактов в `projects_17/vkusvill_research/` (01_business_scale → 08_final_synthesis + SOURCES.md). **Sibling к ROADMAP-VV-001**: артефактный слой (model_forecast.xlsx) → исследовательский слой (research-ready markdown, готовый под web-research Stages 1-4) — **ROADMAP-FR-001 (v1.4 CLOSED, 2026-08-06)**: Reconciliation-plan между RFC_BUFFY_FORGE_V1.md v1.1 §2a и реализацией (3 sequential Шага closed; bump-history: v1.1 Шаг 1 → v1.2 Шаг 2 → v1.3 Шаг 3 → v1.4 CLOSED; capability-check pre-условие CON-40). **Per-bump cross-refs** (CAN-17 audit-trail): v1.1 → [PB-16***REMOVED***(../core_02/LESSONS.md); v1.2 → [RFC_BUFFY_FORGE_V1.md v1.2 §2a.1-2a.3***REMOVED***(engineering-memory/RFC_BUFFY_FORGE_V1.md); v1.3 → [LEVIATHAN_INVENTORY_V1.md v1.1***REMOVED***(engineering-memory/LEVIATHAN_INVENTORY_V1.md) + [CON-52***REMOVED***(../core_02/LESSONS.md); v1.4 → ROADMAP itself (Final Closure Bulletin). **Per-bump cross-refs** (CAN-17 audit-trail): v1.1 → [PB-16***REMOVED***(core_02/LESSONS.md); v1.2 → [RFC_BUFFY_FORGE_V1.md v1.2 §2a.1-§2a.3***REMOVED***(engineering-memory/RFC_BUFFY_FORGE_V1.md); v1.3 → [LEVIATHAN_INVENTORY_V1.md v1.1 + CON-52***REMOVED***(engineering-memory/LEVIATHAN_INVENTORY_V1.md) + [CON-52***REMOVED***(core_02/LESSONS.md); v1.4 → ROADMAP-FR-001 itself (Final Closure Bulletin)
- [RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md***REMOVED***(engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md) — **v5.92.0**: RFC Organizational Memory Engine (единая память платформы: Knowledge Objects, Graph, Semantic Layer, Learning Loop, Analytics)
- [RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md***REMOVED***(engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md) — **v5.93.0**: Архитектурная эволюция RFC (promt52): 8 уровней анализа + 12 ADDITIVE improvements
- [RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md***REMOVED***(engineering-memory/RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md) — **v5.94.0**: RFC Decision Intelligence System (promt53): подсистема качества архитектурных решений
- [RFC_BUFFY_FORGE_V1.md***REMOVED***(engineering-memory/RFC_BUFFY_FORGE_V1.md) — **v5.97.0** (v1.1): RFC Buffy Forge: метасистема архитектурной экосистемы + Workspace/Project контейнеры (Альтернатива A из ARB-REV-001)
- [ARB_REVIEW_FACTORY_FORGE_MANIFEST_V1.md***REMOVED***(engineering-memory/ARB_REVIEW_FACTORY_FORGE_MANIFEST_V1.md) — **v5.96.0**: ARB Review: Factory/Forge Manifest (promt57): 10-шаговый ARB-анализ, вердикт CHANGES REQUIRED, конфликт имён «Forge»
- [factory_forge_manifest.md***REMOVED***(engineering-memory/factory_forge_manifest.md) — **v5.96.0**: Factory/Forge Manifest (документ 68): визионерский документ Workspace OS
- [LEVIATHAN_INVENTORY_V1.md***REMOVED***(engineering-memory/LEVIATHAN_INVENTORY_V1.md) — **v5.97.0 (v1.1 bump 2026-08-06)**: LEVIATHAN Inventory: категоризация A/B/C 25 компонентов + ребрендинг под Buffy; во версии v1.1 добавлены Cat-A rows #26-#28 (фордж-*) + ROADMAP-FR-001 cross-ref block (Шаг 3 ROADMAP-FR-001 prep). **Per-bump cross-ref**: v1.1 → [Шаг 3 ROADMAP-FR-001***REMOVED***(ROADMAP_FORGE_RECONCILIATION.md) (cat-A preparation for downstream Forge extensions) + [CON-52***REMOVED***(../core_02/LESSONS.md) (Workspace/Project vs Forge levels anti-collision rule). **Per-bump cross-ref**: v1.1 → [Шаг 3 ROADMAP-FR-001***REMOVED***(ROADMAP_FORGE_RECONCILIATION.md) (cat-A preparation for downstream Forge extensions) + [CON-52***REMOVED***(core_02/LESSONS.md) (Workspace/Project vs Forge levels anti-collision rule)
- [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md) — **v1.2 (2026-08-09, 066_09_workspace_os_kus_vkusvill)**: Workspace OS stress-test research (39 секций) — не исследование Scenario, а всей Workspace OS через реальный кейс ВкусВилл. Phase 2: §4 Career + §5 Business + §6 Demo + §7 Scenario CLOSED (SHIP-verified); 43 артефакта в §2 inventory; A/B/C доктрина §3; Hypothesis C (orthogonal-STATE) verified в §7. **Cross-refs**: → [AUDIT_WS_OS_P65_§4_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§4_V1.md) + [AUDIT_WS_OS_P65_§5_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§5_V1.md) + [AUDIT_WS_OS_P65_§6_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§6_V1.md); → `projects_17/vkusvill_research/` (real-world instance)

- [ROADMAP_PHASE2_CONTINUATION_v1.md***REMOVED***(engineering-memory/ROADMAP_PHASE2_CONTINUATION_v1.md) - **v1.0 (2026-08-09)**: Autonomous Execution roadmap for section 15-39 per pompts_11/068_07_autonomous_project_executor.md (25 sections, 24+1 DEFERRED, ~10-15h).
- [AUDIT_WS_OS_P65_§4_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§4_V1.md) — **2026-08-09**: независимый claim-by-claim audit §4 (Career pipeline): 12 primary C-Stage-01…12 + 11 secondary C-D1…11 + 3 gaps (G-1/G-2/G-3); real command+output cross-refs; TRUST **8.5-9.0/10**; verdict SHIP. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §4***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§5_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§5_V1.md) — **2026-08-09**: независимый claim-by-claim audit §5 (Business pipeline): 11 primary C-Biz-01…11 + 7 secondary C-D1…7 + 5 gaps (G-1…G-5); real bash blocks embedded from start (урок §4 review-цикла); TRUST **8.5-9.0/10**; verdict SHIP. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §5***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§6_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§6_V1.md) — **2026-08-09**: независимый claim-by-claim audit §6 (Demo/Prototype pipeline): 12 primary C-Demo-01…12 + 6 secondary C-D1…6 + Q-A..Q-E verdict mapping + 4 gaps (G-1…G-4); real command outputs + per-stage 11-axis sampling; TRUST **8.5-9.0/10**; verdict SHIP. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §6***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§9_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§9_V1.md) — **2026-08-09**: независимый claim-by-claim audit §9 (Forge pipeline): 13 primary C-Forge-01…13 + 9 secondary C-D1…9 + 4 gaps (G-1…G-4); real command outputs (line-level fact-check против forge_pipeline.py run=203/hooks=85/on_report=175/_run_cmd=62, forge_registry.py STATUSES=38/cap=161, forge_registry.yaml 7×UNFORGED, RFC_BUFFY_FORGE §4 L0-L5, FR-001 §2a.1/§2a.3); TRUST **8.5-9.0/10**; verdict SHIP. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §9***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§10_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§10_V1.md) — **2026-08-09**:
- [AUDIT_WS_OS_P65_§11_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§11_V1.md) — **2026-08-09**: claim-by-claim audit §11 (Multi-Agent System): 18 primary C-MA-01…18 + 7 secondary + 4 gaps; real grep-verifications против distributed_agents.py:100/249/483 + wizard_lib.py:70/208 + workspace_registry + router.py:268-302; TRUST **8.5-9.0/10**; verdict SHIPPABLE. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §11***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§13_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§13_V1.md) — **2026-08-09**: claim-by-claim audit §13 (Different AI Providers): 16 primary C-AP-01…16 + 8 secondary C-AS-1…8 + 5 gaps G-AP-1…5; real grep-verifications против router.py:159-208/234/268-302 + model_gateway.py:168 + LESSONS.md CON-40/ANTI-6/ANTI-6b; TRUST **8.5-9.0/10**; verdict SHIPPABLE. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §13***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md) независимый claim-by-claim audit §10 (Modes A-G): 18 primary C-Mode-01…18 (10 [ФАКТ***REMOVED*** + 7 [АРХ***REMOVED*** + 1 [ГИП***REMOVED*** → 11 VERIFIED + 7 CONSISTENT) + 7 secondary C-MS-1…7 + 4 gaps (G-1…G-4); real grep-verifications против router.py:239/271/302 (SmartRouter CON-40 best_score fallback), wizard_lib:27/41/70/127/284, blueprint_v3:114-148/347-357 (CAPABILITIES validation), distributed_agents:45-46/77-111, presence.py:157-237, collaboration.py:113-172, LESSONS ANTI-6:192-220; §3.3 forward-correct (G overstate + D/E/F understate); TRUST **8.5-9.0/10**; verdict SHIPPABLE. **Cross-refs**: → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §10***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md); pattern: [09_audit_promt64.md***REMOVED***(../../projects_17/vkusvill_research/09_audit_promt64.md)
- [AUDIT_WS_OS_P65_§14_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§14_V1.md) — **v1.0 (2026-08-09)**: §14 Agent as a Worker audit pass (16 primary C-AW-01..16 + 8 secondary C-AS-1..8 + 5 gaps G-AW-1..5, TRUST 8.9/10, SHIPPABLE)

- [AUDIT_WS_OS_P65_§15_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§15_V1.md)
- [AUDIT_WS_OS_P65_§16_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§16_V1.md)
- [AUDIT_WS_OS_P65_§17_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§17_V1.md)
- [AUDIT_WS_OS_P65_§18_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§18_V1.md)
- [AUDIT_WS_OS_P65_§19_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§19_V1.md)
- [AUDIT_WS_OS_P65_§20_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§20_V1.md)
- [AUDIT_WS_OS_P65_§21_V1.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_§21_V1.md) - **v1.0 (2026-08-09)**: §21 Feedback claim-by-claim audit (20-25 claims, TRUST 7.5-9.0/10, 5 gaps G-FBK-1..5 fully cross-referenced — 4438 events prove architecture works at scale despite gaps).
 - **v1.0 (2026-08-09)**: §20 Decision System claim-by-claim audit (25-30 claims, TRUST 6.5-8.5/10, 5 gaps G-DEC-1..5 fully cross-referenced — gaps openly admit NOT-yet-implemented RFCs).
 - **v1.0 (2026-08-09)**: §19 Evidence & Provenance claim-by-claim audit (20-25 claims, TRUST 7.5-9.0/10, 5 gaps G-EVP-1..5 fully cross-referenced).
 - **v1.0 (2026-08-09)**: §18 Artifact claim-by-claim audit (20-25 claims, TRUST 7.5-9.0/10, 5 gaps G-ART-1..5 fully cross-referenced to §33 Minimal v0.1 MUST commitments: versioning convention + markdown→KO ingester + lineage auto-tracking).
 - **v1.0 (2026-08-09)**: §17 Learning Loop claim-by-claim audit (18-22 claims, TRUST 7.5-9.0/10, 5 gaps G-LL-1..5 fully cross-referenced to §33 Minimal v0.1).
 - **v1.0 (2026-08-09)**: §16 Memory claim-by-claim audit (15-20 claims, TRUST 7.5-9.0/10, 5 gaps G-MEM-1..5 fully cross-referenced to §33 Minimal v0.1 commitment).
 - **v1.0 (2026-08-09)**: section 15 Long-Lived Project audit pass (16 primary C-LLP + 8 secondary C-LS + 5 gaps G-LLP, TRUST 8.9/10)
- [AUDIT_WS_OS_P65_RECAP.md***REMOVED***(engineering-memory/AUDIT_WS_OS_P65_RECAP.md) — **v1.4 (2026-08-09)**: сводка 7 аудитов Phase 2 (§4 Career / §5 Business / §6 Demo / §9 Forge / §10 Modes A-G / §11 Multi-Agent / §13 AI Providers): 100 primary + 55 secondary + 29 gaps, TRUST avg ≈ 8.8/10, все SHIP/SHIPPABLE; R-1…R-27 рекомендации для §33 (Minimal v0.1) + §23 (Mode D) + §24 (Mode E) + §33 prep (drift sync). **Cross-refs**: → все 5 AUDIT_WS_OS_P65_§N_V1.md; → [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §33***REMOVED***(engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md)

### decisions/ — Реестр решений
- [DECISIONS.md***REMOVED***(decisions/DECISIONS.md) — индекс ADR
- [IDEAS.md***REMOVED***(decisions/IDEAS.md) — реестр идей

### visual/ — Mermaid диаграммы (git-renderable)
- [visual/diagrams/vv_001_to_vv_002.mmd***REMOVED***(visual/diagrams/vv_001_to_vv_002.mmd) — **2026-08-06**: Flowchart TB — линия VV-001 → VV-002 (BRIEF → ROADMAP-VV-001 → artifact layer (vkusvill_demo) + ROADMAP-VV-002 → research layer (vkusvill_research) → общий OUTCOME отклик). ClassDef по статусу (closed green / inprogress yellow / artifact blue / pending grey). Render: mermaid.ink, GitLab/GitHub markdown, mermaid-cli, Obsidian.
- [visual/diagrams/forge_line.mmd***REMOVED***(visual/diagrams/forge_line.mmd) — **2026-08-06**: Flowchart LR — Forge meta-system line (VISION_3.0 → RFC_BUFFY_FORGE v1.1 → ARB review → FR-001 3 stages → CLOSED → impl в core_02/forge_* + scripts_01/forge.py v5.103.0). Render: same. Cross-ref CON-38..52.

### Forge/Validator & chain cross-link (v5.163.0-v5.167.0)

**v5.168.0 сonneктор sharded index**: validator + chain артефакты v5.163.0-v5.167.0 привязаны к INDEX.md/DOCUMENT_REGISTRY.md/RECAP_V2.md.

**CON-60 (routing canon, 2026-08-18):** задачи вида «начать проект / составить план / задокументировать шаги» маршрутизируются через **Blueprint v3 role pipeline** (LIGHT-роли планирования `explainer → lisa → risk → decomposer → architect` → артефакты `brief.md` → `lisa_report.md` → `risk_matrix.md` → `decomposition.md` → `architecture.md` + ADR; затем HEAVY-роли `developer → tester → fixer → acceptance` через `ForgeFacade`), а не выполняются ad-hoc. Канон цепочки: `core_02/forge_facade.py::PIPELINE_CHAIN`; входные точки: `scripts_01/forge.py cmd_chain`, `ForgeFacade.run_chain`, `scripts_01/wizard.py`. См. [core_02/LESSONS.md CON-60***REMOVED***(../core_02/LESSONS.md).

**CON-61 (auto-execution design, 2026-08-18):** проход по ролям Blueprint v3 должен быть **автоматическим сценарием** (`forge.py chain --generate`), а не ручным пошаговым. Разрыв: `run_chain` для LIGHT-ролей = `check_only` (валидация существования артефактов, генерации нет). Дизайн: `core_02/role_executor.py::RoleExecutorRegistry` (role_id → генератор; детерминированные tool + LLM-роли по blueprint-промпту) + режим `light_mode` на `run_chain`. См. [core_02/LESSONS.md CON-61***REMOVED***(../core_02/LESSONS.md) + [ADR-016***REMOVED***(engineering-memory/decisions/ADR_016_Role_Executor_Auto_Chain_Generation.md).

**CON-62 (LISA calibration store, 2026-08-18):** каноничное хранилище весов калибровки LISA-3 — `data_13/lisa_calibration.yaml` (глобальные `weights` + `domains:`, напр. `xlsx.ai_suitability: 7.0`). Переиспользование `lisa_estimator --domain <name>`; сохранение `--save-calibration <name>`; обновление — роль retrospective (Evolution Forge). Доменные веса строго opt-in. См. [core_02/LESSONS.md CON-62***REMOVED***(../core_02/LESSONS.md).

**Implementation modules** (core_02/):
- [core_02/forge_facade.py***REMOVED***(../core_02/forge_facade.py) — ForgeFacade (run_chain facade) + `PIPELINE_CHAIN` (14 ролей) + `ChainRun`/`ChainStage` dataclasses (добавлены v5.158.0/v5.157.0).
- [core_02/forge_registry.py***REMOVED***(../core_02/forge_registry.py) — ForgeRegistry (status persistence + last_pipeline accumulator).
- [scripts_01/forge.py***REMOVED***(../scripts_01/forge.py) — CLI c v5.167.0 soft-failure wrapping.

**Tests** (tests_09/):
- [test_role_artifact_validator.py***REMOVED***(../tests_09/test_role_artifact_validator.py) — validator existence-validator edge cases.
- [test_forge_chain_cli.py***REMOVED***(../tests_09/test_forge_chain_cli.py) — CLI subcommand + --resume + v5.167.0 TestSoftFailure.
- [test_forge_chain_real_integration.py***REMOVED***(../tests_09/test_forge_chain_real_integration.py) — реальный прогон на vkusvill_research + vkusvill_demo + interior_planner (v5.164.0 + v5.166.0).
- [test_run_chain.py***REMOVED***(../tests_09/test_run_chain.py) — run_chain unit tests.

**Design docs** (docs_10/engineering-memory/):
- [P3_FORGE_FACADE_DESIGN.md***REMOVED***(engineering-memory/P3_FORGE_FACADE_DESIGN.md) — Facade design (v5.156.0, ADR-013).
- [P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md***REMOVED***(engineering-memory/P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md) — IDEA EXPLORER прогон (v5.156.0/v5.158.0/v5.161.0/v5.165.0/v5.166.0).


- [runbook/FORGE_CHAIN_RUNBOOK.md***REMOVED***(runbook/FORGE_CHAIN_RUNBOOK.md) — **v5.171.0 (2026-08-10)**: Operational manual для `forge chain --json`: real-cost matrix (vkusvill 7.49s / interior 14.83s / research 7.87s / --dry-run 14.42s) + 9-key schema reference + status/overall decision tree + resume/serialization semantics + troubleshooting matrix (exit codes, status pathology, known operational issues per CHANGELOG v5.156-v5.170) + G-7.1..3 open questions.
- [runbook/MISSING_REGISTRY_RUNBOOK.md***REMOVED***(runbook/MISSING_REGISTRY_RUNBOOK.md) — **v1.0 (2026-08-11)**: Operational manual для `python -m core_02.missing_registry` (register-first lifecycle): CLI-справочник (list/seed/register/mark-prompt-written/mark-implemented/check, --path) + lifecycle registered → design_ready → prompt_written → implemented (forward-only) + exit codes + пошаговый гайд регистрации нового элемента + troubleshooting (B10/R-127 инварианты, дрейф §20 ↔ YAML). Связан с AGENTS.md §5 REGISTER-FIRST и FACTORY_FORGE_ARCHITECTURE_V1.md §20.
### visual/ — Mermaid диаграммы (git-renderable)

---

## Правила ведения документации

1. **Canonical** — только факты, без истории споров
2. **History** — почему так получилось (ADR)
3. При изменении канона — обновить canonical/, создать ADR в history/
4. Не дублировать информацию между документами


### Operator guide
- [HOW_TO_LAUNCH_BUFFY.md***REMOVED***(HOW_TO_LAUNCH_BUFFY.md) — operator runbook: запустить Баффи (3 entry points + verification + FAQ)

- §22 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~2669-3120) — Operating Environment (Workspace as OS · OS-metaphor + 5 gaps G-OP-1..5 + RECAP R-68..R-72, Phase 2 COMPR v2.4)

- §23 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3147-3700) — Cross-Factory Orchestration (4 factories + 5 gaps G-CFO-1..5 + RECAP R-78..R-82, Phase 2 COMPR v2.5)

- §24 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3226-3800) — Reusability ♻️ (5 levels L1-L5 + 5 gaps G-REU-1..5 + RECAP R-83..R-87, Phase 2 COMPR v2.6)

- §25 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3320-3850) — Security & Governance 🔐 (4-Layer Security + 5 gaps incl. 2 Critical G-SEC-1..5 + RECAP R-88..R-92, Phase 2 COMPR v2.7)

- §26 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3412-3950) — Failure Modes 💥 (12 layers × 30 F001-F030 + heatmap + G-FM-1..5 + RECAP R-93..R-97, Phase 2 COMPR v2.8)

- §27 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3538-3950) — Overengineering Audit 🪞 (17 levels × 4-status verdict + Parking Lot + 4 rules + G-OE-1..5 + RECAP R-98..R-102, Phase 2 COMPR v2.9)

- §28 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3637-4050) — Real-World Stress Test 🏋️ (5 work-types × readiness map 20%/40%/40% + G-RT-1..5 + RECAP R-103..R-107, Phase 2 COMPR v2.10)

- §29 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3756-4100) — Архитектурная вертикаль 🏗️ (Model A canonical L0-L5 vs Model B 14-level future-ref + 8 aspects + G-29-1..5 + RECAP R-108..R-112, Phase 2 COMPR v2.11)

- §30 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3854-4200) — Full VkusVill Pipeline 📦 (28 stages unified real-instance, 89% complete + G-30-1..5 + RECAP R-113..R-117, Phase 2 COMPR v2.12)

- §31 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~3969-4350) — Definition of Workspace OS 📐 (5 candidates + 8 aspects + Final Definition project-centric/local-first/multi-mode/stateful + G-31-1..5 + RECAP R-118..R-122, Phase 2 COMPR v2.13)

- §32 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~4085-4500) — Architectural Boundaries 🧱 (14 boundaries + 5 B-Rules + cross-reference matrix + boundary doctrine + G-32-1..5 + RECAP R-123..R-127, Phase 2 COMPR v2.14)

- §33 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~4320-4800) — Minimal v0.1 🏛️ (Phase 3 APEX · v3.0 SYMBOLIC MILESTONE · MUST/SHOULD/LATER + 5 boundaries + Definition + Anti-Patterns + 23 quality gates + G-33-1..5 + R-128..R-132 + Release-Critic design)

- §34 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~4509-4900) — First Vertical Slice 🪜 (Phase 4 · Candidate 3 winner · 8-aspect sweep · 5-phase roadmap ~200 LOC · G-34-1..5 · RECAP R-138..R-142)

- §35 (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1, p. ~4632-5000) — ТОП-10 архитектурных рисков ⚠️ (10 risks × score × mitigation + 4 Critical in Phase 4 + 5 G-35-N + RECAP R-143..R-147)


- §36 — Финальный вердикт (4 главных вопроса) — *2026-08-09* — see `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` section §36 (v3.3)

- §37 — Финальная архитектура (исправленная карта) — *2026-08-09* — see `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` section §37 (v3.4)

- §38 — Критерий успешного исследования (14 вопросов) — *2026-08-09* — see `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` section §38 (v3.5)

- §39 — Mission final eval 🎯 — *2026-08-09* — see `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` section §39 (v3.5)

- **MISSION_CLOSE_20260809.md** — summary handoff report (Phase 4 CLOSE) — *2026-08-09*
