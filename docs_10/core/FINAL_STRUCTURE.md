# FINAL STRUCTURE — Финальная структура Workspace OS

> **Версия:** 1.0.0
> **Дата:** 2026-08-01
> **Статус:** 🟢 ACTIVE — итоговый синтез консолидации (Этап 10)
> **Миссия:** Этап 10 консолидации (`pompts_11/032_09_workspace_os_konsolidaciya.md`) — финальная структура
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md)
> **Связанные:** [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md) (каталог компонентов), [GLOSSARY.md***REMOVED***(GLOSSARY.md) (термины), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md) (жизненные циклы), [MODULE_CONSOLIDATION.md***REMOVED***(MODULE_CONSOLIDATION.md) (модули), [DOCUMENT_REGISTRY.md***REMOVED***(../DOCUMENT_REGISTRY.md) (статусы документов), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md) (долги), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)

---

## 1. Архитектурная схема (сводная)

Workspace OS (Buffy) — **AI Infrastructure Layer**: инфраструктурный слой под, над и между
любыми AI-агентами (Claude Code, Cursor, Codebuff, OpenClaw). Канонические границы слоёв —
в [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) §2 и [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md) §3.1.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        WORKSPACE OS (Buffy)                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  CORE (ядро — обязательно)                                           │  │
│  │  ContextManager · MemoryEngine · KnowledgeEngine · GraphIndex ·      │  │
│  │  EventBus · Orchestrator · EMEngine · Bootstrap Engine · Policy      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXTENSIONS (опционально, по профилю)                                │  │
│  │  MCP Server · Bridge Layer · Runtime Abstraction · Scenario Engine ·  │  │
│  │  ToolRuntime · Plugin API · Notification · Provider/Key Pools         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  STATE & KNOWLEDGE SERVICES                                          │  │
│  │  RAGEngine · CollaborationEngine · PresenceEngine · RoleEngine ·     │  │
│  │  MetricsEngine · ProjectPulse · DriftCheck · ConsistencyCheck        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  LABS (экспериментальные)                                            │  │
│  │  Session Mesh · Node Mesh · Agent Mesh · Distributed Agents           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

**Режимы масштабирования** (канон): Single → Cowork → Teamwork → Organization → Community.
Single ✅ готов · Cowork 🟡 (connectivity готово, orchestration нет) · Teamwork 🟡 (ACP/Bridge готовы)
· Organization/Community 🔵 концепт.

**Каноническая модель (11 правил, promt36+promt37):** Workstation → Workspace (сфера) →
Project (цель); Work Area — **View**, не сущность; DPE рекомендует исполнителя, но
User-Choice Override оставляет выбор за пользователем (правило 11).

---

## 2. Структура каталогов (каноническая, проверено 2026-08-01)

```
freebuff/  (Workspace OS)
├── AGENTS.md · BUFFY.md · BUFFY_PROJECT.md · CHANGELOG.md · CLAUDE.md · CODY.md
│   README.md · SPEC.md · TASK.md · freebuff_cli.py · mypy.ini · requirements.txt
├── scripts_01/                    # 46 движков и инструментов
│   ├── memory_engine.py · knowledge_engine.py · graph_index.py · engineering_memory.py
│   ├── rag_engine.py · collaboration.py · presence.py · roles.py · metrics.py · project_pulse.py
│   ├── event_bus.py · orchestrator.py · context_manager.py · tool_runtime.py · plugin_api.py
│   ├── mcp_server.py · mcp_fastapi.py · model_gateway.py · stream_session.py · stream_bridge.py
│   ├── drift_check.py · consistency_check.py · doctor.py · verifier.py · auto_conspect.py
│   └── ... (полный каталог — SYSTEM_INVENTORY.md)
├── core_02/                       # Контракты и роутер
│   ├── interfaces.py · router.py (SmartRouter) · __init__.py
├── freebuff_plugin_03/            # Плагинный контур
│   ├── bridge.py · bridge_layer.py · scenario_engine.py · acp_protocol.py · mcp_client.py
│   ├── runtime/ (adapters, registry) · policy/ · bootstrap/ · event/ · mesh/
├── plugins_04/                    # Устанавливаемые плагины
│   ├── hello_world/ · system_monitor/ · knowledge_sync/ · tg_messenger/
├── runtime_05/                    # Marketplace провайдеров
│   ├── providers/ (yaml) · plugins/ · recipes/ · policies.json
├── src_06/workers/                # lightpanda_worker.py
├── cli_07/ · services_08/ · frontend_18/ (BuffyDashboard.tsx) · infa_20/
├── docs_10/                       # Документация (статусы — DOCUMENT_REGISTRY.md)
│   ├── core/ (канон, 22+ файла) · audits/ · decisions/ · engineering-memory/(decisions/, templates/)
│   ├── ops/ · plugin/ · projects_meta/ · session_dumps/ · task_archive/ · vision/(archive/)
├── pompts_11/                     # 35 промтов (классифицированы в Этапе 5)
├── tests_09/                      # тест-файлы (51+ suite)
├── data_13/                       # SQLite: context.db · metrics.db · presence.db · roles.db · ...
├── context_12/                    # knowledge/ · memory/ · streams/ · summaries/ · checkpoints/ · events.db
├── sessions_15/                   # (пусто — DEBT-003)
├── projects_17/                   # пользовательские проекты (diet_platform)
├── logs_14/ · screenshots_16/ · trash_21/   # служебные
└── .freebuff/                  # config.json · AGENTS.md · mcp.json
```

### 2.1 Схема именования (Naming Convention, канон)

> **Статус:** 🟢 КАНОНИЧЕСКОЕ правило (введено 2026-08-01 при переименовании каталогов и промтов).
> Нарушение схемы — документационный долг; новые сущности обязаны ей следовать.

**Два разных правила — осознанно, под разные требования:**

| Сущность | Схема | Пример | Почему так |
|----------|-------|--------|-----------|
| **Каталог** (Python-пакет) | `имя_NN` — **суффикс-ID** | `scripts_01/`, `core_02/`, `docs_10/` | Python-импорты **запрещают цифру в начале** имени пакета (`import 02_scripts` → SyntaxError); семантика имени первична для человека, `_NN` — стабильный уникальный ID от коллизий общих имён; `ls` группирует по смыслу; `_` совместим с кодом и shell |
| **Промт** (md-документ) | `NNN_TT_имя` — **префикс-порядок** | `032_09_workspace_os_konsolidaciya.md` | Промты — эволюционная лента: сортировка по номеру = история (1…40); не импортируются — цифра спереди безопасна |

**Важно:** суффикс `_NN` получают **только top-level каталоги**. Вложенные подкаталоги
имя НЕ меняют: `freebuff_plugin_03/runtime/` (adapters), `runtime_05/plugins/`,
`docs_10/core/` — без суффиксов (артефакт `freebuff_plugin_03/runtime_05/` был
исправлен при миграции).

**Каталоги: `NN` = порядковый номер каталога в исходном дереве Workspace** (стабильный ID, не меняется при реорганизации):

| Старое имя | Новое имя (канон) | № |
|-----------|-------------------|---|
| `scripts` | `scripts_01` | 01 |
| `core` | `core_02` | 02 |
| `freebuff_plugin` | `freebuff_plugin_03` | 03 |
| `plugins` | `plugins_04` | 04 |
| `runtime` | `runtime_05` | 05 |
| `src` | `src_06` | 06 |
| `cli` | `cli_07` | 07 |
| `services` | `services_08` | 08 |
| `tests` | `tests_09` | 09 |
| `docs` | `docs_10` | 10 |
| `pompts` | `pompts_11` | 11 |
| `context` | `context_12` | 12 |
| `data` | `data_13` | 13 |
| `logs` | `logs_14` | 14 |
| `sessions` | `sessions_15` | 15 |
| `screenshots` | `screenshots_16` | 16 |
| `projects` | `projects_17` | 17 |
| `frontend` | `frontend_18` | 18 |
| `buffy-playground` | `buffy-playground_19` | 19 |
| `infa` | `infa_20` | 20 |
| `trash` | `trash_21` | 21 |
| `prototype` | `prototype_22` | 22 |

**Промты: `TT` = код темы** (устойчивый классификатор):

| TT | Тема | TT | Тема |
|----|------|----|------|
| 01 | vision | 08 | prototype |
| 02 | arhitektura | 09 | konsolidaciya |
| 03 | audit | 10 | dpe |
| 04 | integraciya | 11 | principy |
| 05 | pamyat | 12 | terminal |
| 06 | ispravleniya | 13 | kachestvo |
| 07 | agent | 14 | planirovanie |

**Промты: маппинг старых имён → новых** (полный, `pompts_11/`):

| Старое имя | Новое имя (канон) |
|-----------|-------------------|
| `promt1.md` | `001_07_pravila_dokumentirovaniya.md` |
| `promt2.md` | `002_14_planirovshchik_arhitekt.md` |
| `promt3.md` | `003_01_buffy_2_agentic_platform.md` |
| `promt4.md` | `004_01_distributed_agents_platform.md` |
| `promt5.md` | `005_04_interoperability_layer.md` |
| `promt6.md` | `006_08_prototype_lab.md` |
| `promt7.md` | `007_04_lightpanda_integration.md` |
| `promt8.md` | `008_06_fix_docs_kontur.md` |
| `promt9.md` | `009_06_fix_knowledge_structure.md` |
| `promt10.md` | `010_07_self_check_triggery.md` |
| `promt11.md` | `011_07_session_snapshot.md` |
| `promt12.md` | `012_01_evolution_cowork_platform.md` |
| `promt13.md` | `013_01_vision_2_0_universal_companion.md` |
| `promt14.md` | `014_02_leviathan_arhitektura.md` |
| `promt15.md` | `015_02_ultimate_architect_termux.md` |
| `promt16.md` | `016_02_arhitektura_reorganizaciya.md` |
| `promt17.md` | `017_02_struktura_requirements_testy.md` |
| `promt18.md` | → `trash_21/` (OBSOLETE, пустой) |
| `promt19–21` | (не существовали) |
| `promt22.md` | `022_02_architecture_reality_check.md` |
| `promt23.md` | `023_02_kanonicheskaya_model_workspace_os.md` |
| `promt24.md` | `024_02_domain_model_workspace_os.md` |
| `promt25.md` | `025_02_principy_agenta.md` |
| `promt26.md` | `026_05_engineering_memory.md` |
| `promt27.md` | `027_05_projectbook_storybook.md` |
| `promt28.md` | `028_04_notification_framework.md` |
| `promt29.md` | `029_04_integration_registry.md` |
| `promt30.md` | `030_05_knowledge_management_system.md` |
| `promt31.md` | `031_03_arhitekturnyy_audit.md` |
| `promt32.md` | `032_09_workspace_os_konsolidaciya.md` |
| `promt33.md` | `033_10_dpe_audit.md` |
| `promt34.md` | `034_10_dpe_realizaciya.md` |
| `promt35.md` | удалён (байт-дубль `034_10_dpe_realizaciya.md`, Этап 5) |
| `promt36.md` | `036_09_full_consolidation_pipeline.md` |
| `promt37.md` | `037_11_user_choice_override.md` |
| `AUDIT_PROMPT.md` | `038_03_audit_prompt.md` |
| `TERMINAL_AI_STUDIO_MOBILE.md` | `039_12_terminal_ai_studio_mobile.md` |
| `CODE_QUALITY_STANDART.md` | `040_13_code_quality_standard.md` (опечатка исправлена) |
| `promt41.md` | `041_03_inventarizaciya_proekta.md` (инвентаризация, тема 03=audit) |
| `promt42.md` | `042_06_dokumentaciya_meeting_tasks.md` (документация/meeting-задачи, тема 06=ispravleniya) |
| `promt43.md` | `043_08_frontend_workspace_os_ui.md` (фронтенд Workspace OS, тема 08=prototype) |

---

## 3. Реестр компонентов (сводка)

Полный каталог: [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md). Границы и зависимости:
[ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) §3–4. Жизненные циклы: [LIFECYCLE.md***REMOVED***(LIFECYCLE.md).

| Группа | Компоненты | Статус |
|--------|-----------|--------|
| **Core C1–C6** | MemoryEngine, KnowledgeEngine, GraphIndex, EMEngine, EventBus, Orchestrator | ✅ Production |
| **State & Knowledge S1–S7** | RAGEngine, CollaborationEngine, PresenceEngine, RoleEngine, MetricsEngine, ProjectPulse, DriftCheck | ✅ Production |
| **Инфраструктура** | ContextManager, ToolRuntime, PluginAPI, MCP Server, Bridge Layer, Runtime Abstraction, Scenario Engine, Notification, ConsistencyCheck | ✅ Production |
| **Плагины** | hello_world, system_monitor, knowledge_sync, tg_messenger | ✅ Production |
| **Runtime-провайдеры** | freebuff, claude_code, openclaw (YAML-каталог) | ✅ Production |

---

## 4. Итоги консолидации (Этапы 1–9)

### 4.1 Документы
- **Реестр статусов:** `docs_10/DOCUMENT_REGISTRY.md` — ACTIVE 64 + каталоги / LEGACY 22 /
  ARCHIVED 14 + каталоги / DRAFT 1 / OBSOLETE 5 (по состоянию на 2026-08-01).
- **LEGACY:** ARCHITECTURE_3.0, ARCHITECTURE_REVIEW, ADR_001 (full), ROADMAP.md, ROADMAP_PROMT31, 17 промтов.
- **OBSOLETE → trash_21/ (Этап 5):** error.md, new.md, structure.md, freb.md, promt18.md — артефакты/пустые перенесены в `trash_21/` (история сохранена в git).

### 4.2 Удалённые дубли
- `pompts_11/promt35.md` — байт-идентичная копия 034_10_dpe_realizaciya.md (Этап 5).
- `pompts_11/038_03_audit_prompt.md.bak`, `docs_10/core/CODE_QUALITY_STANDARD.md.bak` (Этап 4).
- Опечатка `CODE_QUALITY_STANDART.md` → `CODE_QUALITY_STANDARD.md` — переименован (Этап 5).

### 4.3 Канон (single source of truth)
| Реестр | Файл | Роль |
|--------|------|------|
| Архитектурный закон | `docs_10/core/ARCHITECTURE_MANIFEST.md` | главный канон |
| Каноническая архитектура | `docs_10/core/ARCHITECTURE_CANONICAL.md` | границы движков |
| Терминология | `docs_10/core/GLOSSARY.md` | единые термины |
| Жизненные циклы | `docs_10/core/LIFECYCLE.md` | стадии компонентов |
| Модули | `docs_10/core/MODULE_CONSOLIDATION.md` | 10 областей |
| Core Prompt | `docs_10/core/CORE_PROMPT.md` | поведение агента |

---

## 5. Принятые ADR (9)

| ID | Решение | Дата |
|----|---------|------|
| ADR-001 | Model Gateway — единый API вызова LLM | 2026-07-28 |
| ADR-002 | MCP Server — Pure Python vs Official SDK | 2026-07-28 |
| ADR-003 | MCP Streamable HTTP Transport | 2026-07-28 |
| ADR-004 | FastAPI Wrapper + Cloudflare Tunnel | 2026-07-28 |
| ADR-005 | ContextManager Bridge | 2026-07-28 |
| ADR-006 | Lightpanda Headless Browser | 2026-07-28 |
| ADR-007 | Vision 3.0 — AI Infrastructure Layer | 2026-07-29 |
| ADR-008 | Канонические правила Workspace OS (promt36) | 2026-08-01 |
| ADR-009 | Правило 11 User-Choice Override (promt37) | 2026-08-01 |

Индекс: `docs_10/decisions/DECISIONS.md`; полные ADR: `docs_10/engineering-memory/decisions/ADR_*.md`.

---

## 6. Оставшиеся задачи

### 6.1 Архитектурные долги ([ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md))
- ✅ **DEBT-001** (Resolved 2026-08-01): `AGENTS.md`, `CLAUDE.md`, `CODY.md` индексируются в KnowledgeEngine (`agents_md`/`claude_md`/`cody_md` в KNOWLEDGE, drift_check зелёный).
- ✅ **DEBT-002** (Resolved 2026-08-01): деревья `BUFFY.md`/`RULES.md` исправлены (`docs_10/core`); `02-specs` не создавать (призрак номерной схемы), `scripts_01/monitor.sh` не восстанавливать (канон — `freebuff_plugin_03/monitor.sh`).
- **DEBT-003** (🟢 Low): `sessions_15/` пуст — задокументировать или удалить.
- **DEBT-004** (🟢 Low): задокументировать top-level каталоги (частично — `prototype_22` уже описан).
- ✅ **DEBT-005/006** (Resolved 2026-08-01): `drift_check.py` path resolution — root-aware парсинг деревьев, юнит-тесты парсинга; попутно приведены `_is_knowledge_doc`/`_KNOWLEDGE_IGNORE_DIRS`/`_extract_impl_refs`/`_guess_block_paths` к новым именам каталогов.
- **DEBT-007** (🟡 Medium → ✅ Resolved 2026-08-01): дубль Telegram-ботов закрыт — общий предок `BaseTGBot` (`scripts_01/tgbot_base.py`).

### 6.2 Пост-консолидация (Phase B/C, ROADMAP_PROMT31)
- Wire real git/system publishers.
- Lifecycle FSM, Project Book compile, Architecture Map.
- Интеграционные реестры (Integration Registry).

### 6.3 Канонические шаги promt36/37 (выполнены 2026-08-01, кроме DPE; Mission Lock снят)
- ✅ **Work Area as View (выполнен 2026-08-01)**: таблица `project_resources(project_id, resource_id, created_at)` в `data_13/context.db` + CLI `freebuff resource projects <resource>` (+ link/unlink/resources/list) — `scripts_01/work_area_view.py`, тесты `tests_09/test_work_area_view.py`.
- ✅ **User Preferences (выполнен 2026-08-01)**: CLI `freebuff policy list/set/get/unset/resolve` + `unset_preference()` в `freebuff_plugin_03/policy/engine.py` (правило 11 User-Choice Override) — хранение в `runtime_05/policies.json`, сброс возвращает автовыбор системы.
- ✅ **Context-Aware Routing (правило 8, выполнен 2026-08-01)**: `Orchestrator.check_existing_context()` в `scripts_01/orchestrator.py` (поиск дублей в Knowledge перед созданием задачи) + событие `workflow.context_check`.
- ✅ **Plugin Contract Specification (правило 9, выполнен 2026-08-01)**: канонический документ `docs_10/plugin/PLUGIN_CONTRACT_SPECIFICATION.md` + валидатор `scripts_01/plugin_contract.py` + интеграция в `PluginLoader.load()` и CLI `python -m scripts_01.plugin_api contract <name>`.
- **DPE-маршрутизация** в `orchestrator.py` (promt34).

---

## 7. Критерий завершения консолидации

- [x***REMOVED*** код, документация и промты согласованы (drift_check green, consistency_check green);
- [x***REMOVED*** существует `docs_10/core/ARCHITECTURE_MANIFEST.md`;
- [x***REMOVED*** существует единый Core Prompt (`docs_10/core/CORE_PROMPT.md`);
- [x***REMOVED*** устранены критические дублирования (promt35, .bak, опечатка STANDART);
- [x***REMOVED*** вся документация имеет статус (реестр `docs_10/DOCUMENT_REGISTRY.md`);
- [x***REMOVED*** создан план автоматической проверки консистентности (`consistency_check.py` + `drift_check.py`, подключены в doctor и CI).

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [GLOSSARY.md***REMOVED***(GLOSSARY.md), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md), [MODULE_CONSOLIDATION.md***REMOVED***(MODULE_CONSOLIDATION.md), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [DOCUMENT_REGISTRY.md***REMOVED***(../DOCUMENT_REGISTRY.md), [DECISIONS.md***REMOVED***(../decisions/DECISIONS.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
