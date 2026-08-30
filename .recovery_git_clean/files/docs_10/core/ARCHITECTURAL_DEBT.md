# Architectural Debt Register

> **Document:** `docs_10/core/ARCHITECTURAL_DEBT.md`  
> **Source:** `scripts_01/drift_check.py`  
> **Generated:** 2026-07-31  
> **Status:** Living document — regenerate after each drift check  

---

## 1. Purpose

This document tracks **architectural debt** identified by the daily self-audit in `scripts_01/drift_check.py`. It is not a task list for features; it records structural gaps, documentation drift, and maintenance obligations that accumulate as the codebase grows.

**Principles:**

- *Debt must be observable.* Every entry references evidence (drift report, file, or test).
- *Debt must be prioritised.* Severity and owner are explicit.
- *Debt must be actionable.* Each entry has a clear remediation step and an ETA.

---

## 2. How This Document Is Maintained

1. `scripts_01/drift_check.py --force --report` generates the current drift report.
2. Findings are triaged: false positives are documented, real issues become debt entries.
3. This file is updated manually; a future enhancement may automate debt entry creation.
4. When a debt item is resolved, it is moved to the **Resolved Debt** section with a reference to the fixing commit.

---

## 3. Current Debt Register

### 3.1 Duplicate Telegram Bots — RESOLVED ✅

> **2026-08-01:** Закрыт через `scripts_01/tgbot_base.py` (`BaseTGBot`).
> Полная запись — в §5.8 Resolved Debt ниже.

---

## 4. False Positives and Tooling Debt

> **2026-08-01:** Единственный оставшийся false positive (`docs_10/core_02` — артефакт массового переименования каталогов в дереве `BUFFY.md`/`RULES.md`) устранён, см. Resolved DEBT-002/DEBT-005 ниже.

## 5. Resolved Debt

### 5.3 Directory Structure Drift — Missing Described Directories — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-002 |
| **Component** | `BUFFY.md` / `docs_10/core/RULES.md` tree diagrams + `scripts_01/drift_check.py` |
| **Severity** | 🟡 Medium → ✅ Resolved |
| **Type** | Documentation accuracy |
| **Description** | `drift_check.py` сообщал о "described but missing": `02-specs`, `INDEX.md`, `audits`, `decisions`, `ops`, `plugin`, `projects_meta`, `scripts_01/monitor.sh`, `vision`. Разбор (2026-08-01): большинство позиций существует под `docs_10/`; единственный настоящий артефакт — `docs_10/core_02` в деревьях `BUFFY.md:269` и `RULES.md:117` (побочный эффект массового переименования каталогов: подкаталог docs `core/` не переименовывался, но sed переписал `core/` → `core_02/` в ссылках). Деревья исправлены на `docs_10/core`. |
| **Evidence** | 1) `drift_check.py --force --report` → directory structure drift: **No discrepancies found**. 2) `python -m pytest tests_09/test_drift_check.py -q` → 30 passed (включая новые тесты парсинга дерева). |
| **Fate: `docs_10/02-specs`** | **Не создавать.** Это призрак отвергнутой номерной схемы `01-architecture/02-specs/03-audits/...` (встречается только в исторических аудитах `AUDIT_FULL_2026-07-29.md`, `pompts_11/038_03_audit_prompt.md`). Канон — `docs_10/core/`, `docs_10/vision/`, `docs_10/decisions/`, `docs_10/audits/`, `docs_10/plugin/`, `docs_10/projects_meta/`, `docs_10/ops/`. В канонических деревьях отсутствует — фантом из деревьев аудитов не порождает drift. |
| **Fate: `scripts_01/monitor.sh`** | **Не восстанавливать.** В `scripts_01/` этого файла никогда не было (git history пуст). Каноническое расположение — `freebuff_plugin_03/monitor.sh` (документировано в `docs_10/plugin/FREEBUFF_PLUGIN_ARCHITECTURE.md` §3.5). В канонических деревьях `monitor.sh` не значится — false positive снят. |
| **Resolved** | 2026-08-01 |

---

### 5.4 `drift_check.py` Path Resolution — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-005 |
| **Component** | `scripts_01/drift_check.py` (`_extract_tree_paths`, `check_directory_structure`) |
| **Severity** | 🟡 Medium → ✅ Resolved |
| **Type** | Tool accuracy |
| **Description** | Чекер трактовал пути из tree-диаграмм как относительные к корню воркспейса, даже когда диаграмма описывает поддерево (`docs_10/`-rooted trees). Парсер не распознавал корневой узел дерева: bare-корень (`docs_10/`) выбрасывался, а дети (`INDEX.md`, `audits/`) трактовались как корневые пути → false positives. |
| **Remediation done** | 1) `_extract_tree_paths()` теперь детектирует bare root-узел и возвращает `(path, root)`; дети резолвятся относительно корня. <br> 2) `check_directory_structure()` резолвит детей относительно root, если root — реальный подкаталог. <br> 3) Попутно: `_is_knowledge_doc()` переведён с `docs` на `docs_10`, `_KNOWLEDGE_IGNORE_DIRS` — с `context/data/logs/sessions` на `context_12/data_13/logs_14/sessions_15`, `_extract_impl_refs()`/`_guess_block_paths()` — на новые имена каталогов. <br> 4) Добавлены юнит-тесты парсинга дерева: `test_extract_tree_paths_detects_bare_root_node`, `test_extract_tree_paths_no_root_block`, `test_extract_tree_paths_deep_nesting`, `test_check_directory_structure_resolves_docs_subtree_root`. |
| **Evidence** | 1) `drift_check.py --force --report` → **No discrepancies found** во всех секциях. 2) `python -m pytest tests_09/test_drift_check.py -q` → 30 passed. |
| **Resolved** | 2026-08-01 |

---

### 5.5 Knowledge Index Drift — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-001 |
| **Component** | `scripts_01/seed_knowledge.py` / `scripts_01/drift_check.py` |
| **Severity** | 🟢 Low → ✅ Resolved |
| **Type** | Documentation hygiene |
| **Description** | Three root-level project documents were not indexed by the knowledge engine: `AGENTS.md`, `CLAUDE.md`, `CODY.md`. Now all three are part of `DEFAULT_DOC_SOURCES` in `seed_knowledge.py` and `_collect_indexed_sources()` in `drift_check.py`, are stored in MemoryLevel.KNOWLEDGE (`agents_md`, `claude_md`, `cody_md`), and are searchable via KnowledgeEngine/RAG. |
| **Evidence** | 1) `_collect_doc_sources(Path('.'))` returns all three files. 2) MemoryEngine KNOWLEDGE entries present: `agents_md`, `claude_md`, `cody_md`. 3) `drift_check.py --force` → Knowledge index drift: **No discrepancies found**. |
| **Resolved** | 2026-08-01, commit `c1b70da` (Stage 9: full drift fix) + registry update |

---

### 5.6 Directory Structure Drift — Empty `sessions_15/` — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-003 |
| **Component** | `sessions_15/` directory / Stream Session management |
| **Severity** | 🟢 Low → ✅ Resolved |
| **Type** | Operational / cleanup |
| **Description** | `sessions_15/` описывался в документации, но был пуст → `drift_check.py` флаговал «described but empty». Разбор (2026-08-01): каталог — **намеренный runtime-артефакт** для сырых логов стрим-сессий (`scripts_01/stream_session.py`, `stream_bridge.py`); пустота после прунинга — норма. |
| **Remediation done** | 1) `sessions_15/.gitkeep` уже присутствует (каталог не пуст для git). <br> 2) Добавлен `sessions_15/README.md` с описанием назначения (рекомендация Remediation п.1). <br> 3) `drift_check.py` более не флагует каталог (runtime-каталоги с содержимым/README не считаются пустыми). |
| **Evidence** | 1) `ls -la sessions_15/` → `.gitkeep` + `README.md`. 2) `drift_check.py --force --report` → **No discrepancies found**. |
| **Resolved** | 2026-08-01 |

---

### 5.7 Directory Structure Drift — Undocumented Top-Level Directories — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-004 |
| **Component** | `BUFFY.md` / `docs_10/core/RULES.md` top-level structure |
| **Severity** | 🟢 Low → ✅ Resolved |
| **Type** | Documentation completeness |
| **Description** | `drift_check.py` сообщал о top-level каталогах «exists but not described»: `buffy-playground_19/`, `cli_07/`, `frontend_18/`, `infa_20/`, `plugins_04/`, `projects_17/`, `screenshots_16/`, `services_08/`, `src_06/`, `trash_21/`. Разбор (2026-08-01): после массового переименования каталогов и обновления дерева `BUFFY.md` **все 22 top-level каталога задокументированы** в каноническом дереве (`core_02`…`data_13` + `prototype_22` добавлен). |
| **Remediation done** | 1) Дерево `BUFFY.md` §«Структура freebuff» описывает все 22 top-level каталога (включая `prototype_22/` — UI-прототип). <br> 2) Судьбы «неоднозначных» зафиксированы (см. Fate ниже) — ни один не переносится в `.gitignore`: все намеренные. |
| **Fate: `screenshots_16/`** | **Сохранить, задокументирован.** Персональные артефакты (скриншоты, `Screenshot_*.png`). В дереве BUFFY.md — «скриншоты». |
| **Fate: `trash_21/`** | **Сохранить как архив.** Содержит OBSOLETE-файлы из Этапа 5 (`error.md`, `new.md`, `structure.md`, `freb.md`, `promt18.md`) + ретроспективы/дампы — история сохранена (запрет на удаление истории). В дереве — «временный мусор/архив». |
| **Fate: `infa_20/`** | **Сохранить, задокументирован.** Инфраструктурные материалы (`RUNTIME_INTELLIGENCE.md`). В дереве — «инфраструктурные материалы». |
| **Fate: `prototype_22/`** | **Сохранить, задокументирован.** UI-прототип Workspace OS (`index.html`, Project-Centric + Graph View). Добавлен в дерево BUFFY.md (2026-08-01). |
| **Evidence** | 1) `BUFFY.md` дерево перечисляет все 22 каталога. 2) `drift_check.py --force --report` → **No discrepancies found** (нет «exists but not described»). |
| **Resolved** | 2026-08-01 |

---

### 5.2 Missing Tests for 6 Engines (S1–S6) — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-006 |
| **Component** | `RAGEngine`, `CollaborationEngine`, `PresenceEngine`, `RoleEngine`, `MetricsEngine`, `ProjectPulse` |
| **Severity** | 🔴 Critical → ✅ Resolved |
| **Type** | Test coverage |
| **Description** | Test files for 6 engines were absent from `tests_09/` and git history despite CHANGELOG claims of 60+ tests (noted in `ARCHITECTURE_CANONICAL.md` §3.2). Restored on 2026-07-31: `test_rag_engine.py` (34), `test_collaboration.py` (48), `test_presence.py` (42), `test_roles.py` (44), `test_metrics.py` (23), `test_project_pulse.py` (34). |
| **Evidence** | `python -m pytest tests_09/test_rag_engine.py tests_09/test_collaboration.py tests_09/test_presence.py tests_09/test_roles.py tests_09/test_metrics.py tests_09/test_project_pulse.py -q` → **225 passed, 0 failed** (~56s). |
| **Resolved** | 2026-07-31, commit `c2df854` — test: restore test suites for 6 engines (close critical debt). |

---

### 5.8 Duplicate Telegram Bots — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-007 |
| **Component** | `scripts_01/tgbot_base.py` (`BaseTGBot`) — новый общий предок |
| **Severity** | 🟡 Medium → ✅ Resolved |
| **Type** | Duplicate functionality (found in Stage 6 module consolidation) |
| **Description** | Two independent Telegram bots with overlapping infrastructure (`.env` loading, token, ApplicationBuilder, polling loop, error handler). |
| **Remediation (выполнено)** | Общий `BaseTGBot` в `scripts_01/tgbot_base.py`: `load_dotenv`, `build_application`, `run_polling`, `error_handler`. `TelegramFreebuffBot` (scripts_01/telegram_bot.py) и `ScenarioTGBot` (freebuff_plugin_03/tgbot.py) наследуют его, оставаясь в своих слоях (scripts = уведомления, freebuff_plugin = сценарии). Дублирующийся polling-цикл и .env-загрузка удалены из обоих ботов. |
| **Tests** | `tests_09/test_tgbot_base.py` (новый, 18 тестов: load_dotenv, BaseTGBot, наследование) + существующие `test_telegram_bot.py`, `test_tgbot.py` — зелёные |
| **Resolved** | 2026-08-01 |

---

## 6. Recommended Next Steps

1. ~~**Fix `drift_check.py` path resolution** (DEBT-2026-07-31-005)~~ → **✅ Resolved** (см. §5.4).
2. ~~**Index `AGENTS.md`, `CLAUDE.md`, `CODY.md`** in the knowledge engine (DEBT-2026-07-31-001)~~ → **✅ Resolved** (см. §5.5).
3. ~~**Clarify or create `docs_10/02-specs`** and `scripts_01/monitor.sh` (DEBT-2026-07-31-002)~~ → **✅ Resolved** (см. §5.3: не создавать; канон `freebuff_plugin_03/monitor.sh`).
4. ~~**Document or ignore top-level directories** (DEBT-2026-07-31-004)~~ → **✅ Resolved** (см. §5.7: все 22 каталога задокументированы, судьбы зафиксированы).
5. ~~**`sessions_15/` пуст** (DEBT-2026-07-31-003)~~ → **✅ Resolved** (см. §5.6: runtime-каталог, README добавлен).
6. ~~**Дубль Telegram-ботов** (DEBT-2026-07-31-007)~~ → **✅ Resolved** (см. §5.8: общий предок `BaseTGBot`).

---

## 7. Related Documents

- `scripts_01/drift_check.py` — daily self-audit tool
- `docs_10/audits/DRIFT_REPORT.md` — raw daily drift report
- `docs_10/core/SYSTEM_INVENTORY.md` — component inventory
- `docs_10/vision/ROADMAP_PROMT31_WORKSPACE_OS.md` — roadmap addressing related architectural gaps

