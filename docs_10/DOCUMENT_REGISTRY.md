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
| `SPEC.md` | ACTIVE | Техническая спецификация |
| `TASK.md` | ACTIVE | Трекер задач |

---

## `docs_10/` (корень)

| Документ | Статус | Примечание |
|----------|--------|------------|
| `DOCUMENT_REGISTRY.md` | ACTIVE | Настоящий реестр (самодокументирование) |
| `INDEX.md` | ACTIVE | Навигация по документации |
| `DRIFT_REPORT.md` | ARCHIVED | Генерируемый артефакт `drift_check.py` (в `.gitignore`) |

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
| `COMPATIBILITY_MATRIX.md` | ACTIVE | Матрица совместимости Runtime |
| `CORE_PROMPT.md` | ACTIVE | Единый Core Prompt (цель Этапа 5) |
| `DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` | ACTIVE | Спецификация Session Mesh v2.0 |
| `EVENT_PLATFORM_SPECIFICATION.md` | ACTIVE | Спецификация Event Platform |
| `FINAL_STRUCTURE.md` | ACTIVE | Итоговый синтез Этапа 10 (схема, каталоги, реестр, ADR, задачи) |
| `GLOSSARY.md` | ACTIVE **[канон***REMOVED***** | Единая терминология (Этап 7) |
| `LIFECYCLE.md` | ACTIVE **[канон***REMOVED***** | Жизненные циклы компонентов (Этап 8) |
| `MODULE_CONSOLIDATION.md` | ACTIVE **[канон***REMOVED***** | Аудит модулей (Этап 6) |
| `POLICY_ENGINE_SPECIFICATION.md` | ACTIVE | Спецификация Policy Engine; MCP-инструмент `policy_override` (правило 11, ADR-009) в §8 |
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
| `decisions/ADR_001…ADR_007` | ACTIVE | Каноническое расположение ADR (drift_check `_ADR_CANONICAL_DIR`) |
| `templates/*.md` | ACTIVE | Шаблоны Engineering Memory |

---

## `docs_10/ops/`, `docs_10/plugin/`, `docs_10/projects_meta/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
| `docs_10/ops/` (10 файлов) | ACTIVE | Операционные гайды, шаблоны. Дубль `ops/AGENTS.md` → `trash_21/AGENTS_ops_duplicate.md` (2026-08-01); канон — корневой `AGENTS.md` |
| `docs_10/plugin/` (4 файла) | ACTIVE | Документация freebuff_plugin; `PLUGIN_CONTRACT_SPECIFICATION.md` §8 — MCP-инструменты ядра (incl. `policy_override`) |
| `docs_10/projects_meta/` (5 файлов) | ACTIVE | Интеграции: Lightpanda, Overlay, Workers |

---

## `docs_10/vision/`

| Документ | Статус | Примечание |
|----------|--------|------------|
| `PRODUCT_MANIFESTO.md` | ACTIVE | Манифест продукта |
| `ROADMAP.md` | LEGACY | Заменён на `ROADMAP_PROMT31_WORKSPACE_OS.md` + `ROADMAP_PROMT32_CONSOLIDATION.md` |
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
| `event` | `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse` | 5 |
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

## Сводка (подсчёт по таблицам выше)

| Статус | Кол-во файлов | Состав |
|--------|---------------|--------|
| ACTIVE | 65 + каталоги | корень 10 + docs_10/ 2 + core 21 + audits 7 + decisions 2 + vision 4 + pompts 19; каталоги целиком: engineering-memory, ops, plugin, projects_meta |
| LEGACY | 22 | core 2 (ARCHITECTURE_3.0, ARCHITECTURE_REVIEW) + decisions 1 (ADR_001 full) + vision 2 (ROADMAP, ROADMAP_PROMT31) + pompts 17 |
| ARCHIVED | 21 + каталоги | docs_10/DRIFT_REPORT 1 + audits 11 + vision/archive 2 + trash 7; каталоги: session_dumps, task_archive |
| DRAFT | 1 | audits 1 (AUDIT_TEMPLATE) |
| OBSOLETE | 0 | Артефакты pompts_11/ перенесены в trash_21/ (Этап 5) |

---

_Связанные документы: [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(vision/ROADMAP_PROMT32_CONSOLIDATION.md) (Этап 4), [INDEX.md***REMOVED***(INDEX.md), [ARCHITECTURE_MANIFEST.md***REMOVED***(core/ARCHITECTURE_MANIFEST.md) (§6 Архивация), [LIFECYCLE.md***REMOVED***(core/LIFECYCLE.md) (стадия Архивация)_
