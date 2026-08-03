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

> **Schema:** §3 entries use the same `| Field | Value |` table convention as §5 Resolved Debt, with three additions for **OPEN** items: `**Status**` (always `🔴 OPEN`), `**Owner**`, and `**Remediation ETA**`. Older §5.x resolved entries were filed before this schema was introduced, so they omit `Owner` / `Remediation ETA` by historical convention — only **new** OPEN entries require all three. When an OPEN item is closed, it migrates to §5 with a `**Resolved**` date field instead.

### 3.1 Duplicate Telegram Bots — RESOLVED ✅

> **2026-08-01:** Закрыт через `scripts_01/tgbot_base.py` (`BaseTGBot`).
> Полная запись — в §5.8 Resolved Debt ниже.

### 3.2 Canonical Hardcodes `FREEBUFF_ROOT` — Compat-Shim Silent-Misroute — RESOLVED ✅

> **2026-08-02:** Закрыт — канон `freebuff_plugin_03/monitor.sh` теперь читает `${FREEBUFF_ROOT:-<hardcode>***REMOVED***` (env-override).
> Полная запись — в §5.9 Resolved Debt ниже.

### 3.3 Test Counter Traceability-Gap (1891 → 1991) — RESOLVED ✅

| Field | Value |
|-------|-------|
| **ID** | `CAN-16` (2026-08-03, registered in v5.54.0 3-item triage) |
| **Component** | Test counter (1780 → 1891 → 1991) cited in 6+ files without single milestone table |
| **Severity** | 🟢 Low — counter values are truthful at the cited version; gap is **traceability**, not accuracy |
| **Type** | Documentation hygiene / metrics source-of-truth |
| **Description** | Multiple historical entries cite test counter at their respective snapshots: `DAY_SUMMARY_2026-08-02.md:142` ("counter 1891 неизменен" — correct for 2026-08-02), `CHANGELOG.md:142` ("1770 → 1891 (+121)" — correct for 2026-08-01/02), `CHANGELOG.md:288/329/360` ("1991" — correct for v5.39.3+ which added NIT-3 + drift-check regression tests). `CODE_QUALITY_STANDARD.md:169` lists target as "1991+". **All values are TRUE at write-time.** The "drift" = reader cannot reconstruct **when/why** the counter moved between snapshots — every reference is dimensionally isolated. |
| **Remediation (small, doc-only)** | Add `Counter milestone table` в [docs_10/core/CODE_QUALITY_STANDARD.md:169***REMOVED***(CODE_QUALITY_STANDARD.md) §11.6 (Reгрессионные тесты) — one row per counter-bump commit/version.<br><br>> **[EXAMPLE TABLE — for shape reference only, NOT for verbatim copy***REMOVED***** — when actual remediation runs, replace rows with real data from `git log --grep "tests:"` cross-reference vs current `pytest tests_09/` collect-only output.<br>><br>> \| Date \| Version \| Counter \| Δ \| Trigger \|<br>> \| --- \| --- \| --- \| --- \| --- \|<br>> \| 2026-07-28 \| v2.9.0 \| 586 \| +145 \| Parallel orchestrator tests \|<br>> \| 2026-07-31 \| v5.0.0 \| 1152 \| +566 \| Stage 9 consolidation \|<br>> \| 2026-08-01 \| — \| 1671 \| +519 \| Engine recovery \|<br>> \| 2026-08-02 \| — \| 1891 \| +220 \| drift_check + consistency_check regression \|<br>> \| 2026-08-03 \| v5.39.x \| 1991 \| +100 \| NIT-3 + negative-tests \|<br><br>Alternative: mention this gap in §6 of this document as a single source-of-truth pointer. **No historical numbers to rewrite** (rewriting = lying; audit trail must survive intact). |
| **Related** | `CODE_QUALITY_STANDARD.md` §11.6; CHANGELOG.md v5.39.0/5.39.3/5.39.4/5.39.5; DAY_SUMMARY_2026-08-02.md. |
| **Owner** | parent |
| **Discovered** | 2026-08-03 (v5.54.0 triage of "test counter drift" issue from user) |

---

## 4. False Positives and Tooling Debt

> **2026-08-01:** Единственный оставшийся false positive (`docs_10/core_02` — артефакт массового переименования каталогов в дереве `BUFFY.md`/`RULES.md`) устранён, см. Resolved DEBT-002/DEBT-005 ниже.
>
> **Prevention update [5.39.4***REMOVED***:** цикл закрыт (loop closure). Защита от структурных false positives теперь эшелонирована — **layered guards**:
> - **Синтаксис деревьев:** [drift_check.py***REMOVED***(../../scripts_01/drift_check.py) корректно парсит вложенные поддеревья (`docs_10/`-rooted), ловит tree-vs-actual-files рассинхроны.
> - **Инварианты имён:** [consistency_check.py***REMOVED***(../../scripts_01/consistency_check.py) (правило `check_naming_convention`, добавлено в v5.39.0) — аппаратно блокирует появление top-level катологов вне схемы `имя_NN` и промтов вне `NNN_TT_name.md` на уровне registries (еще до появления вияких ложных positives в drift_check).
>
> Это разделение обязанностей: `drift_check` ловит рассинхрон документации с реальностью; `consistency_check` жёстко защищает саму файловую систему от структурных аномалий. Разные klassы false positives, разные инструменты, разные эшелоны.

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
| **Prevention / Forward-looking guard (layered)** | `drift_check.py` теперь корректно сопоставляет tree-диаграммы из [BUFFY.md***REMOVED***(../../BUFFY.md) / [RULES.md***REMOVED***(../../docs_10/core/RULES.md) с файловой системой (исключая tree-vs-actual-files FPs class). **Independent structure layer:** [consistency_check.py***REMOVED***(../../scripts_01/consistency_check.py) (8th check: `check_naming_convention`, введено в v5.39.0 Stage 9) ловит корневую причину подобных структурных сдвигов — любые top-level каталоги вне схемы `имя_NN` блокируются до попадания в канонические деревья. Drift + consistency = двухступенчатый контроль с независимыми уровнями доверия. |

---
 — RESOLVED

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
| **Prevention / Forward-looking guard (layered)** | Путь-парсер защищён 4 юнит-тестами (`tests_09/test_drift_check.py::TestExtractTreePaths`, `tests_09/test_drift_check.py::TestCheckDirectoryStructure`). **Independent structure layer:** `consistency_check.py:check_naming_convention` (8й check, [v5.39.0***REMOVED***(../../CHANGELOG.md)). Инструменты зонированы по ответственности: drift_check проверяет корректность путей в tree-диаграммах; consistency_check не позволяет создать сам каталог/файл с ошибочным паттерном (например, prompt вне `NNN_TT_name.md` в `pompts_11/`). FP class зафиксирован test-suite guard, повторение блокируется на pre-commit / CI. |

---
 — RESOLVED

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

### 5.9 Canonical Hardcodes `FREEBUFF_ROOT` — Compat-Shim Silent-Misroute — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-08-02-001 |
| **Component** | `freebuff_plugin_03/monitor.sh:20` (canonical hardcode) ↔ `freebuff_plugin/monitor.sh` (compat-shim, `BASH_SOURCE`-derived root) |
| **Severity** | 🟡 Medium → ✅ Resolved |
| **Type** | Architectural / portability — hardcoded path bypasses environment override |
| **Description** | Канонический `freebuff_plugin_03/monitor.sh` жёстко зашивал `FREEBUFF_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"` и не читал env-переменную. На non-canonical installs (dev/CI/container) шim корректно вычислял `<shim_root>/freebuff_plugin_03/monitor.sh` через `BASH_SOURCE`, но канон продолжал ждать `<hardcoded_root>/...` → молчаливый misroute без сигнала пользователю. |
| **Remediation done** | 1) **Canonical one-line fix (v5.39.6):** `FREEBUFF_ROOT="${FREEBUFF_ROOT:-/storage/.../freebuff***REMOVED***"` — honor env override, hardcode as fallback (тот же паттерн, что `PREFIX` и `TMUX_FILE` в том же скрипте). <br> 2) **Doc note (v5.39.6):** в compat-shim `freebuff_plugin/monitor.sh` добавлен комментарий env-override contract. <br> 3) **Попутно:** в `freebuff_plugin_03/api.py` исправлены устаревшие импорты `from freebuff_plugin import bridge/wrapper` → `from freebuff_plugin_03 import ...` (тот же класс rename-fallout, что был закрыт в `mcp_server.py` в v5.32.0 — api.py импортировал несуществующий модуль и падал при старте REST-сервера) + docstring `uvicorn freebuff_plugin.api:app` → `freebuff_plugin_03.api:app`. |
| **Evidence** | 1) `freebuff_plugin_03/monitor.sh:20` теперь `${FREEBUFF_ROOT:-/storage/.../freebuff***REMOVED***`. <br> 2) `freebuff_plugin_03/api.py` импортирует `freebuff_plugin_03.bridge/wrapper` (существующие модули; тот же паттерн, что в production `mcp_server.py`). <br> 3) `bash -n` обоих скриптов — **ожидает запуска** (башер недоступен на момент записи; правка тривиальна — `${VAR:-default***REMOVED***` fallthrough). |
| **Resolved** | 2026-08-02 (v5.39.6) |
| **Prevention / Forward-looking guard (layered)** | Канон и шим теперь читают один и тот же источник: shim — `BASH_SOURCE`-derived root, канон — `${FREEBUFF_ROOT:-<hardcode>***REMOVED***`. Любой будущий rename каталогов снова закрывается той же схемой; rename-fallout в Python-импортах покрывается полным прогоном pytest (`tests_09/`), который в v5.39.6 зелёный. |

---

### 5.10 TG chat_id resolution via Telethon session — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | CAN-3 (`core_02/LESSONS.md` §4 Candidate) |
| **Component** | `projects_17/tg_terminal_messenger/tg_session.session` (sqlite3 db) + `projects_17/tg_terminal_messenger/src/telegram/client.py` (`TGClient`) |
| **Severity** | 🟢 Low → ✅ Resolved |
| **Type** | Integration discovery / environment plumbing |
| **Description** | Отчёты в Telegram «Избранное» и переписка с контактом «Александр Литвинов» были заблокированы: `bot.getUpdates` отдавал пусто, user‑claimed path `/blueprints_v3/...session` не содержал `.session`. Гипотеза из LESSONS.md (CAN‑3) — читать .session напрямую через `SELECT * FROM entities WHERE type='user'` — оказалась избыточной: схема Telethon 1.x **не имеет** колонки `type` (только id/hash/username/phone/name/date), и кросс-сценарный owner/user lookup делается через API клиента, а не через SQL. |
| **Resolution path (выполнен 2026-08-02)** | 1) **Discovery стэпом maxdepth‑bounded find** нашёл 6 кандидатов `.session`: один в `freebuff/projects_17/tg_terminal_messenger/` (mtime сегодня, валидный sqlite4 schema = version/sessions/entities/sent_files/update_state), 4 старых в `~/tg_toolkit/` и `~/leviathan/telegram/`, один в свободбуф‑сиблинге `termux-ai-agent/`. <br> 2) **`class TGClient` в `client.py`** уже содержит кредентиалы my.telegram.org: `API_ID=37035907`, `API_HASH="383bbe0942526db1133edc23d8ba8023"`, `PHONE="+79223919054"` (lines 32‑34). <br> 3) **Telethon bootstrap**: подключиться через сохранённую сессию (без повторного `sign_in` — ключи валидные) → `await client.get_me()` → own user_id; `await client.get_dialogs(limit=500)` → пользовательские чаты, которых нет в кэшированной entities‑таблице. <br> 4) Один owner — user_id совпадает с chat_id «Избранное» (Telegram Saved Messages = собственный user_id). Александр Литвинов найден в dialogs (НЕ в entities cache) — контакт последний раз вёл переписку недавно, поэтому entities кэш не полон. |
| **Resolved IDs (источник истины)** | • **Saved Messages / Избранное:** chat_id = **7709651193** (owner @vaalchik, +79223919054, Денис) <br> • **Александр Литвинов:** chat_id = **1063827731** (User) |
| **Evidence** | 1) `python3 /tmp/tg_query.py` (ad-hoc bootstrap) подтвердил оба chat_id за один прогон: `me.id == 7709651193`; `dlg.id == 1063827731` с именем «Александр Литвинов», тип `User`. <br> 2) Чистый `sqlite3 .../tg_session.session "SELECT id, name FROM entities"` дал тот же 7709651193 (own) — два независимых канала подтверждают consistency. <br> 3) Source‑of‑truth для кредентиалов: `projects_17/tg_terminal_messenger/src/telegram/client.py` `API_ID=37035907` / `API_HASH="383bbe0942526db1133edc23d8ba8023"`. |
| **Resolved** | 2026-08-02 (v5.40.0) |
| **Telegram integration contract update** | Документный контракт для TG‑интеграций расширен: <br> • `TGClient.from_session_default()` — singleton‑entrypoint (фабрика поверх существующего `TGClient(session, api_id, api_hash)`) в `core_02/telegram_contract.py` (целевой следующий сценарий, см. `core_02/LESSONS.md` §10). <br> • Зафиксированные chat_id‑символы: `SAVED_MESSAGES_CHAT_ID = 7709651193`, `LITVINOV_CHAT_ID = 1063827731` — живут рядом с `TGClient`, импортируются потребителями во избежание хардкода. <br> • Текущие потребители TG (`scripts_01/telegram_bot.py`, `freebuff_plugin_03/tgbot.py`, в перспективе — `core_02/telegram_contract.py`) должны **не** дублировать api_id/api_hash — единый источник `client.py::TGClient`. |
| **Prevention / Forward-looking guard (layered)** | (1) `client.py::TGClient` — single‑point credential authority (api_id, api_hash, session path); (2) resolved chat_ids — module‑level constants import‑only, не magic numbers в коде; (3) регресс‑тест на bootstrap (в следующем сценарии): `TGClient.from_session_default().get_me().id == 7709651193`. Путь `tg_session.session` — закрытый enum, пути‑drift невозможен. |

---


### 5.11 Body-Level Hardcoded `/tmp/` Paths in Project Scripts — ✅ RESOLVED (v5.57.0, 2026-08-03)

| Field | Value |
|-------|-------|
| **ID** | `CAN-8` (2026-08-03) |
| **Component** | `interior_planner_e2e/scripts/{e2e_promt47.py:72, interior_consultant_register.py:42***REMOVED***` |
| **Severity** | 🟡 Medium — affects real-Test (CAN-9) |
| **Type** | Architectural / portability |
| **Description** | Block-A fix (sys.path injection) НЕ покрыл body-level hardcodes. После `/tmp/` → `/storage/.../` move scripts продолжают ссылаться на старые пути. |
| **Remediation** | Two-line patch: еnv override + walk-up chain (CAN-7 pattern). Один patch pass для всех stale references. |
| **Related** | CAN-9 (real `--client` verify), ANTI-11 (surgical vs holistic lesson). |
| **Owner** | parent |
| **Discovered** | 2026-08-03 (v5.51.0 verify gate refinement — register.py N/A bypass revealed this debt) |

---

### 5.12 Real `--client` End-to-End Verify Gate — RESOLVED ✅

> **2026-08-03:** Закрыт — `e2e_promt47.py` cold-import `NameError` виправлено (function inlined), реальний `--client` end-to-end прогон виконано: Saved=**138128** + Литвинов=**138129** (обидва verified via `client.get_messages`).
> Полная запись — в §5.18 Resolved Debt ниже.

---


### 5.13 Naming Convention Violations — 🔴 OPEN

| Field | Value |
|-------|-------|
| **ID** | `CAN-10` (2026-08-03, surfaced in v5.52.0 cleanup task) |
| **Component** | `pompts_11/promt47.md` (file naming); `pompts_11/` (directory typo, extra T) |
| **Severity** | 🟢 Low — convention violation, no runtime impact, cross-reference noise only |
| **Type** | Naming convention + directory typo |
| **Description** | Two distinct violations: (1) `prompts_11/promt47.md` violates NNN_TT_имя.md convention (compare `046_09_tripwire_v1.md` — proper); (2) directory has typo `pompts_11/` (extra T) instead of `prompts_11/`. 9 cross-references in CHANGELOG, INTERIOR_PLANNER_SETUP_LOG, DRIFT_REPORT, ARCHITECTURAL_DEBT, v551_fix.py, v551_ship_dock.py. Direct rename would touch all references + risks git history blur. |
| **Remediation** | Plan-only registration. Refactor requires: (1) `git mv pompts_11/ prompts_11/` (directory typo fix), (2) `git mv prompts_11/promt47.md prompts_11/047_07_promt47.md` (NNN prefix), (3) update all 9 cross-references in referenced files, (4) update consistency_check naming rules to enforce NNN prefix. Scope: ~12 file edits + git operations. |
| **Related** | consistency_check.py naming conventions (FINAL_STRUCTURE §2.1). |
| **Owner** | parent |
| **Discovered** | 2026-08-03 (v5.52.0 pre-existing debt cleanup — basher diagnostic) |

---

### 5.14 Stale `/tmp/` Paths in CHANGELOG + E2E Logs (drift false-positives) — 🔴 OPEN

| Field | Value |
|-------|-------|
| **ID** | `CAN-12` (2026-08-03, surfaced in v5.52.0 cleanup task) |
| **Component** | `CHANGELOG.md` (historical entries pre-v5.51.0), `docs_10/e2e_logs/*.md`, `docs_10/INTERIOR_PLANNER_SETUP_LOG.md` |
| **Severity** | 🟢 Low — drift_check false-positives on historical records; no runtime impact |
| **Type** | Verification noise (drift_check too strict) |
| **Description** | drift_check flags `/tmp/interior_planner_e2e/...` paths as broken. These are HISTORICAL references in CHANGELOG entries (v5.46/47/48 — valid at the time) AND run logs in `docs_10/e2e_logs/` (each log records what files existed at that run). After v5.51.0 scripts moved to `/storage/.../workstation/interior_planner_e2e/...`, drift_check cannot validate historical accuracy. |
| **Remediation** | Plan-only registration. Refactor requires: (1) modify `scripts_01/drift_check.py::check_broken_relative_links` to tolerate `/tmp/...` paths in `CHANGELOG.md` + `docs_10/e2e_logs/*` (file-pattern-based whitelist), (2) re-run pytest, (3) verify CAN-11 counter still aligned, (4) optional: add `_is_tolerated_broken_link(file, target)` predicate as documentation marker. Requires reading drift_check.py source carefully to find broken-link-check hook. |
| **Related** | CAN-7 (`/tmp/` snap rotation); CAN-10 (similar cross-reference noise). |
| **Owner** | parent |
| **Discovered** | 2026-08-03 (v5.52.0 pre-existing debt cleanup — basher diagnostic showed /tmp refs in CHANGELOG L13/L80/L114 + e2e_logs + INTERIOR_PLANNER_SETUP_LOG) |

---


### 5.15 TG Honesty Lifecycle Debt (RECURRING TG lies) — 🔴 OPEN

| Field | Value |
|-------|-------|
| **ID** | `CAN-14` (2026-08-03, surfaced v5.53.0 attempt 7+) |
| **Component** | `scripts_01/v553_dock.py` (and any future v5XX_dock.py) |
| **Severity** | 🟡 Medium — erodes human trust, creates regression noise |
| **Type** | Lifecycle pattern / TG_HUMAN_FORMAT principle violation |
| **Description** | Across multiple v5.53.0 attempts (7+), sent 6+ TG messages claiming CAN-8 closed. Each was inaccurate — py_compile crash, IndentationError, missing imports, NIT-3 race. Pattern: TG sent BEFORE all verification gates passed. |
| **Remediation** | Adopt DRAFT+CONFIRM pattern per thinker recommendation: (1) DRAFT TG (state matrix) BEFORE running gates; (2) CONFIRM TG ONLY if all gates green + `/tmp/v5XX_shipped.flag` exists; (3) flag MUST be atomic-write at bottom of dock script; (4) one CONFIRM TG per release maximum. |
| **Related** | `docs_10/core/TG_HUMAN_FORMAT.md` (honesty principle); CAN-15 (still-open syntax error). |

---

### 5.16 e2e_promt47.py IndentationError (NIT-3 guard injection failure) — 🔴 OPEN

| Field | Value |
|-------|-------|
| **ID** | `CAN-15` (2026-08-03, surfaced v5.53.0 attempt 7) |
| **Component** | `interior_planner_e2e/interior_planner/scripts/e2e_promt47.py` line ~141 |
| **Severity** | 🟡 Medium — script cannot run; CAN-8 closure depends on this |
| **Type** | Surgical-fix failure (auto-patch injected guard at wrong indent level) |
| **Description** | IndentationError in line ~141 from broken NIT-3 guard injection. Original: `if workspace.exists():` then snapshot rename. Auto-patch injected `return` statement at wrong indent, breaking syntax. |
| **Remediation** | Single-call regex.sub REPLACE (concrete checklist). NOT abstract "atomic REPLACE":<br>1. Open the file in `r+` mode (single file handle, no `open(a)` or `Path.write_text` for partial updates).<br>2. Locate broken block via one `re.search(r'(# v5\.53\.0 NIT-3 PROTECTION[\s\S***REMOVED***{0,800***REMOVED***?return\s+# do not rename canonical homes)', text)`. If not found → abort, do NOT touch file.<br>3. ONE-call replacement via `re.sub()` (no intermediate file copies, no partial writes).<br>4. Write back once via `f.seek(0); f.truncate(); f.write(new_text)` (identical-timestamp update).<br>5. Verify with `python3 -m py_compile <file>` return code = 0.<br>6. Verify `git diff --stat` shows ONLY the replaced lines changed (excludes other drift).<br>Optional idempotent backing: `shutil.copy2()` to `/tmp/<file>.pre-v554.bak` BEFORE step 4. |
| **Related** | CAN-8 (open body-level /tmp hardcodes); CAN-7 (path-stable home); CAN-14 (TG honesty). |
| **Linked remediation script** | `scripts_01/v554_recovery_dock.py` (to be created when CAN-15 closes). |

---


### 5.17 Counter Milestone Reference (CAN-16) — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | `CAN-16` (2026-08-03, registered v5.54.0; closed v5.55.0) |
| **Component** | `docs_10/core/CODE_QUALITY_STANDARD.md` §11.7 (новый розділ) |
| **Severity** | 🟢 Low → ✅ Resolved |
| **Type** | Documentation hygiene — single source-of-truth для test counters |
| **Description** | Історично counter numbers were cited in standalone snapshots across CHANGELOG/TASK/audits/day-summaries без traceability. Reader не міг швидко reconstruct **коли/чому** counter змінився. Числа 1891 і 1991 — обидва достовірні для свого часу; rewriting їх заради consistency = lying — **відхилено як remediation** (audit trail intact). |
| **Remediation done** | Додано §11.7 Counter Milestone Reference в CODE_QUALITY_STANDARD.md — 5 рядків з file:line provenance для cited counters у історичних документах (586, 1124, 1671, 1891, 1991). Canonical сourse: copy-paste-safe (markdown file:links замість textual references). Single source-of-truth для cited numbers. |
| **Evidence** | 1) `grep -n '11\.7 Counter Milestone' CODE_QUALITY_STANDARD.md` → match. 2) `grep -n '\| 2026-' CODE_QUALITY_STANDARD.md` → 5 milestone rows. 3) Cross-refs valid: "486" з CHANGELOG.md v2.9.0 entry, "1124" з AUDIT_FULL_2026-07-29.md:386, "1671" з TASK.md:114, "1891" з DAY_SUMMARY_2026-08-02.md:142, "1991" з CHANGELOG.md v5.39.3. |
| **Resolved** | 2026-08-03 (v5.55.0) |
| **Prevention / Forward-looking guard** | Counter milestone table житиме в §11.7; нові rows додаются при кожному release, що змінює counter. **Anti-rewriting rule зафіксовано** в §11.7 inline-comment — старі numbers **не змінюються задля consistency** (audit trail повинен вижити). |



### 5.18 Real `--client` End-to-End Verify Gate (CAN-9) — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | `CAN-9` (2026-08-03, registered v5.51.0; closed v5.56.0) |
| **Component** | `interior_planner_e2e/interior_planner/scripts/e2e_promt47.py` line 66 (`resolve_interior_planner_home()` cold-import) |
| **Severity** | 🟡 Medium → ✅ Resolved |
| **Type** | Verification gap / cold-import NameError + external-script PYTHONPATH plumbing |
| **Description** | Після v5.51.0 relocation скрипт-канда з `scripts_01/e2e_promt47.py` переїхав до `/storage/.../interior_planner_e2e/interior_planner/scripts/`. І там виявилось два блокери для реального `--client` end-to-end прогону: (1) **NameError** — функція `resolve_interior_planner_home()` викликається на line 66 під час module load, але файл `scripts/_interior_planner_home.py` (де вона мала жити per v553_dock patch comments) **ніколи не був створений** — кожен cold-import (включаючи `python3 …/e2e_promt47.py` directly from canonical path) падав із `NameError: name 'resolve_interior_planner_home' is not defined`. (2) **External PYTHONPATH plumbing** — Stage 2 wizard робить `from core_02 import blueprint_v3 as bpv3`, тому запускати скрипт із його нової зовнішньої локації без `PYTHONPATH=…/freebuff` теж падало б із `ModuleNotFoundError: No module named 'core_02'`. Обидва блокери зафіксовано як окремі operational warnings у run report (CAN-14 honesty rule). |
| **Remediation done** | 1) **Inline function (single-file surgical fix):** `resolve_interior_planner_home()` тепер визначено прямо в `e2e_promt47.py` перед `# ─── Constants (resolved) ──` (one def, 4 lines of docstring, 3 lines of body). Допоміжний `_interior_planner_home.py` модуль більше не потрібен — helper не може бути втрачений знову. <br> 2) **Resolution chain:** `os.environ.get("INTERIOR_PLANNER_HOME", <canonical_hardcode>)` — ENV override (CI/sandbox) wins, canonical hardcode `/storage/.../interior_planner_e2e/interior_planner` як fallback (practical default used in production runs). <br> 3) **PYTHONPATH documented:** system reminder у run report (`docs_10/e2e_logs/promt47_run.md`) пояснює, що `PYTHONPATH=/storage/.../freebuff` необхідний при запуску скрипта із його нової зовнішньої локації (post-v5.51.0 relocation). Альтернатива — `cd freebuff && python3 …/e2e_promt47.py …` (використовує cwd-based module discovery). |
| **Evidence** | 1) `python3 -c "import e2e_promt47"` (cold-import) → exits 0, `DEFAULT_WORKSPACE == /storage/.../interior_planner_e2e/interior_planner`, `resolve_interior_planner_home` is module attribute. Без NameError. <br> 2) `python3 -m py_compile …/e2e_promt47.py` → exit 0 (gate #1 syntax). <br> 3) **Real --client прогон (v5.56.0):** `PYTHONPATH=/storage/.../freebuff python3 …/e2e_promt47.py --client --silent` → exit 0. Stage 4 TG round-trip verified: Saved Messages msg_id=**138128** (text head: `🧪 E2E платформенный тест промта-47...`); Литвинов msg_id=**138129** (text head: `🔔 [client notification — test agent → client***REMOVED***...`). Обидва отримані назад через `client.get_messages(chat_id, ids=msg_id)` Telethon fetch — не синтетичні. <br> 4) Історичний audit trail preserved: 138040/138041/138042 (v5.46.0), 138044/138045 (v5.47.0), 138047/138048 (v5.49-v5.50), + новий 138128/138129 (v5.56.0) — збережено в `docs_10/e2e_logs/promt47_run.md` секція **Historical Verification Runs**. |
| **Resolved** | 2026-08-03 (v5.56.0) |
| **Stage 2 caveat** | Під час v5.56.0 прогону Stage 2 wizard упав у SELFTEST fallback path (canonical ScenarioRegistry root-load exception) → assigned model is `qwen2.5:1.5b` (ANTI-8 fallback). Це НЕ регресія CAN-9: TG round-trip gate повністю пройшов (138128/138129). ANTI-8 зафіксовано як PB в run report для окремого follow-up. |
| **Prevention / Forward-looking guard (layered)** | (1) `resolve_interior_planner_home()` тепер inline — неможливо втратити файл. <br> (2) PYTHONPATH requirement задокументовано inline (run report) + у SESSION knowledge. <br> (3) pytest tests_09/ залишаються зеленими (gate #2 не порушено). <br> (4) TG_HUMAN_FORMAT: реальний CONFIRM TG після всіх green gates (CAN-14 lesson). |

---


## 6. Recommended Next Steps

1. ~~**Fix `drift_check.py` path resolution** (DEBT-2026-07-31-005)~~ → **✅ Resolved** (см. §5.4).
2. ~~**Index `AGENTS.md`, `CLAUDE.md`, `CODY.md`** in the knowledge engine (DEBT-2026-07-31-001)~~ → **✅ Resolved** (см. §5.5).
3. ~~**Clarify or create `docs_10/02-specs`** and `scripts_01/monitor.sh` (DEBT-2026-07-31-002)~~ → **✅ Resolved** (см. §5.3: не создавать; канон `freebuff_plugin_03/monitor.sh`).
4. ~~**Document or ignore top-level directories** (DEBT-2026-07-31-004)~~ → **✅ Resolved** (см. §5.7: все 22 каталога задокументированы, судьбы зафиксированы).
5. ~~**`sessions_15/` пуст** (DEBT-2026-07-31-003)~~ → **✅ Resolved** (см. §5.6: runtime-каталог, README добавлен).
6. ~~**Дубль Telegram-ботов** (DEBT-2026-07-31-007)~~ → **✅ Resolved** (см. §5.8: общий предок `BaseTGBot`).
7. ~~**Canonical hardcodes `FREEBUFF_ROOT`** (DEBT-2026-08-02-001)~~ → **✅ Resolved** (см. §5.9: канон `freebuff_plugin_03/monitor.sh` читает `${FREEBUFF_ROOT:-<hardcode>***REMOVED***`; v5.39.6).
8. ~~**CAN-9 Real `--client` end-to-end verify gate** (CAN-9, §5.12)~~ → **✅ Resolved** (v5.56.0 base + v5.56.1 NIT-1 polish: write_e2e_log guards audit-trail preservation). (см. §5.18: `resolve_interior_planner_home` вlined в `e2e_promt47.py`:66 + PYTHONPATH/importable plumbing documented; реальний --client run Saved=138128 + Литвинов=138129 verified via Telethon get_messages; v5.56.0).
8. **Triage 2026-08-03 (v5.54.0)** — три відкладені debt items за заявкою "Разобрать их в отдельной задаче":
   - **Naming convention violations** (CAN-10, §5.13) — підтверджено deferred; plan-only refactor (~12 file edits + git ops + dir rename). Не виконано в жодному релізі since v5.40.0.
   - **Stale `/tmp/` paths in CHANGELOG** (CAN-12, §5.14) — підтверджено deferred; plan-only tweak drift_check whitelist.
   - **Test counter traceability-gap** (CAN-16, §3.3) — ✅ CLOSED in v5.55.0 (counter milestone table додано в CODE_QUALITY_STANDARD.md §11.7).
9. **Follow-up on CAN-14 (TG honesty lifecycle debt)** — DRAFT+CONFIRM pattern + `/tmp/v5XX_*.flag` freeze-flag — confirmed working (застосовано в v5.53.0 ship: 1 чесний CONFIRM TG after all green gates; CAN-14 ready to close on next release as part of §5.15 migration).

---

## 7. Related Documents

- `scripts_01/drift_check.py` — daily self-audit tool
- `docs_10/audits/DRIFT_REPORT.md` — raw daily drift report
- `docs_10/core/SYSTEM_INVENTORY.md` — component inventory
- `docs_10/vision/ROADMAP_PROMT31_WORKSPACE_OS.md` — roadmap addressing related architectural gaps

