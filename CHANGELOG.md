# Changelog

> Все значимые изменения в проекте Freebuff фиксируются в этом файле.
> Формат: [Keep a Changelog***REMOVED***(https://keepachangelog.com/en/1.1.0/),
> версионирование: [Semantic Versioning***REMOVED***(https://semver.org/spec/v2.0.0.html).

---

## [5.25.1***REMOVED*** — 2026-07-31

### Added
- **Mandatory security audit `pompts/TASK_SECURE_MCP_ACCESS.md` — Шаг 2 (Bearer auth в `scripts/mcp_fastapi.py`)**

#### Шаг 2 — Bearer-token auth на `/mcp` (риск №7 аудита)
- `scripts/mcp_fastapi.py`:
  - `verify_bearer_token(request)` — FastAPI `Depends`, проверяет `Authorization: Bearer <token>` через `hmac.compare_digest` (constant-time, anti-timing-attack)
  - `_get_active_token()` — Vault first (hvac), env fallback; TTL-кеш 300 s для Vault-пути, env-путь без кеша (для тестов с monkeypatch)
  - Поддержка AppRole (`FREEBUFF_VAULT_ROLE_ID + _SECRET_ID`) И root token (`FREEBUFF_VAULT_TOKEN`); fail-closed если Vault сконфигурирован, но недоступен
  - KV v2 path-stripping — поддержка любых mount-names (`secret`, `kv`, `kv2`) через `/data/` split
  - `401 Unauthorized` + `WWW-Authenticate: Bearer realm="buffy-mcp"` (RFC 6750)
  - Тестовый bypass: двойной lock `FREEBUFF_ENV=test AND FREEBUFF_MCP_AUTH_DISABLED=1` (случайное включение в prod невозможно)
  - DoS-защита: токены `len > 1024` отклоняются до encode
  - `_reset_token_cache()` — exposed для тестов
  - Применён к **только `/mcp` (POST/GET/DELETE)**; `/`, `/dashboard`, `/metrics/*` остаются публичными (observability + liveness)
- `scripts/mcp_fastapi.py` импорты: `hmac, os, time` + `Depends, HTTPException` (fastapi) + `hvac` (try-import с `HAS_HVAC`)
- `tests/test_mcp_fastapi.py`:
  - Module-level setdefault bypass — существующие 47 тестов остаются зелёными без изменений
  - Новый класс **`TestAuthorization`** (10 тестов): 401 без auth, 401 неверный, 401 non-Bearer scheme, 200 корректный bearer (POST), 204 корректный bearer (DELETE), 401 нет token в env, 200 на `/`, 200 на `/metrics/status`, 200/404 на `/dashboard`, anti-regression на `== provided/expected`
- `requirements.txt`:
  - `hvac>=2.0.0` добавлен (hvac был не установлен; теперь доступен)

### Backward compatibility
- 47 существующих тестов (TestHealth, TestPost*, TestDelete, TestGet, TestOriginValidation, TestAsyncSessionManager, TestMetricsEndpoints) проходят без изменений — благодаря автобупасу при `FREEBUFF_ENV=test`.
- Старые клиенты, не передающие `Authorization: Bearer ...`, получают **`401 Unauthorized`** на `/mcp` — это breaking change. Шаг 4 (ручное действие Дениса) обновит MCP-коннектор.

### Tests
- `python -m pytest tests/test_mcp_fastapi.py -q`: **57 passed in 7.19 s, 0 failures** (47 + 10 TestAuthorization)
- `python -m py_compile scripts/mcp_fastapi.py tests/test_mcp_fastapi.py`: 0 errors

### Code review
- `code-reviewer-minimax-m3` (parallel with tests): **ship-it approved** (0 critical, 0 major, 3 minor hardening все применены)
- `thinker-with-files-gemini` (parallel): рекомендовал **только защищать /mcp** (не /, не /metrics, не /dashboard) + Vault-first с env fallback + 5-min cache TTL на Vault-пути

### Артефакты
- This CHANGELOG entry (5.25.1)
- TASK.md checkpoints обновлены

### Отложено (требуются данные / согласование)
- **Шаг 3 (cloudflared perimeter)** — решение оставить quick tunnel или перейти на именованный
- **Шаг 4** — ручное действие Дениса: добавить URL + токен в MCP-коннектор

---

## [5.25.0***REMOVED*** — 2026-07-31

### Added
- **Mandatory security audit `pompts/TASK_SECURE_MCP_ACCESS.md` — Шаг 0 (диагностика) + Шаг 1 (закрытие free shell)**

#### Шаг 0 — диагностика поверхности `check_command`/`check_params` через MCP-маршруты
- `grep -n "check_command\|verifier\.\|Verifier(" scripts/mcp_server.py scripts/mcp_fastapi.py` → **0 совпадений**
- `grep -n "check_command\|verifier\.\|Verifier(" freebuff_plugin/mcp_server.py` → **0 совпадений**
- `ps aux | grep -E "cloudflared|mcp_fastapi|mcp_server"` → **ни один процесс не запущен**
- Wide grep `check_command|check_params|check_type` по `scripts/` + `freebuff_plugin/` подтвердил: вся поверхность сосредоточена в `scripts/verifier.py` и локальном методе `scripts/overlay_client.py::check_command` (клиент оверлея, не подвержен внешнему воздействию)
- **Вердикт:** маршрут/tool, прокидывающий пользовательский ввод в `check_command`/`check_params` в `scripts/mcp_server.py` или `scripts/mcp_fastapi.py`, **отсутствует**. Объекта для `pkill` нет. Переход к Шагу 1 без остановки процессов.
- Артефакт: **`docs/audits/AUDIT_STEP0_2026-07-31.md`** (5 сырых команд + итог)

#### Шаг 1 — закрытие свободного shell в `scripts/verifier.py` (риск №2 аудита)
- **Удалено:** `_run_shell()` (использовал `subprocess.run(..., shell=True)` без sandbox), `_check_shell()`, `_check_content_match()`
- **Из `CHECK_TYPES` / `CHECKER_REGISTRY` / `DEFAULT_RULES`** убраны ключи `"shell"` и `"content_match"`
- **`_check_pytest()` переписан:** `subprocess.run([sys.executable, "-m", "pytest", test_path, "-q", "--tb=no"***REMOVED***, shell=False, cwd=str(WORKSPACE))` — argv-список, **без `shell=True`**; интерполяция `{{test_path***REMOVED******REMOVED***` больше не может выполнить инъекцию `; touch /tmp/pwned`
- **Удалён мёртвый импорт `Tuple`** (единственный потребитель был `_run_shell`)
- **Net LOC delta:** примерно −115 строк (security ↑, complexity ↓)

#### `tests/test_verifier.py`
- Удалены тесты `test_shell_success`, `test_shell_failure`, `test_shell_with_template` + импорт `_check_shell`
- 3 теста с `check_type="shell"` (`test_add_rule`, `test_get_results`, `test_verify_same_task_twice`) переведены на `check_type="file_exists"` с реальным путём
- Добавлен **`class TestInjectionPrevention`** (3 теста) — канарейки `pwned_pytest_injection` и `pwned_legacy_shell` НЕ ДОЛЖНЫ появиться после попытки инъекции:
  - `test_pytest_injection_via_test_path` — инъекция `"; touch pwned"` через `{{test_path***REMOVED******REMOVED***` не приводит к созданию файла
  - `test_legacy_shell_rule_rejected` — правило `check_type="shell"` в БД диспетчеруется в `None` → `actual="unknown check_type"`, `passed=False`
  - `test_seeded_defaults_no_shell` — после `seed_default_rules()` ни одно правило не содержит `check_type='shell'`

### Backward compatibility
- Старые правила в `data/verifier.db` с `check_type='shell'` или `'content_match'` грузятся нормально, но в `Verifier.verify()` диспетчер `CHECKER_REGISTRY.get(rule.check_type)` возвращает `None` и срабатывает существующая ветка `actual="unknown check_type"` (явно покрыто тестами `test_legacy_shell_rule_rejected` и `test_verify_unknown_check_type`).

### Tests
- `tests/test_verifier.py` (56) + `tests/test_action_verifications.py` (19) → **75 passed in 14.40s, 0 failures**
- `python -m py_compile scripts/verifier.py tests/test_verifier.py` → 0 errors
- `grep -n "shell=True\|_run_shell\|_check_shell\|_check_content_match" scripts/verifier.py` → **0 совпадений** (единственное упоминание — docstring «без shell=True»)

### Code review
- `code-reviewer-minimax-m3` (parallel with pytest): **ship-it approved**, 1 minor reminder (мёртвый импорт `Tuple`) — исправлено
- `thinker-with-files-gemini` рекомендовал **вариант (b) — полное удаление** вместо allowlist; обоснование: чище математически, нет оставшегося `shell=True`, существующие тесты покрываются переходом на `file_exists`/`pytest`

### Артефакты
- `docs/audits/AUDIT_STEP0_2026-07-31.md` — Шаг 0 (5 сырых команд `docs/audits/AUDIT_STEP0_2026-07-31.md`)
- `docs/audits/AUDIT_EVIDENCE_2026-07-30.md` — независимая аудит-доказательная база (предыдущий запрос, 9 блоков A–I)

### Отложено (требуются данные / согласование)
- **Шаг 2 (Bearer auth в `scripts/mcp_fastapi.py`)** — нужен хост Vault и путь к секрету
- **Шаг 3 (cloudflared perimeter)** — решение оставить quick tunnel или перейти на именованный; не критично для безопасности (защита = Шаг 2)
- **Шаг 4** — ручное действие Дениса: добавить URL + токен в MCP-коннектор клиента

---

## [5.24.4***REMOVED*** — 2026-07-30

### Fixed
- **Notification fallback для реальных задач (не только тестов)**
  - **Problem:** User получил уведомления во время тестирования (Phase 5.4 testing через FREEBUFF_FORCE_VISUAL=1), но НЕ получал их на реальных задачах (Phase 5.5 AUDIT PACKAGE build через basher agent).
  - **Root causes:**
    1. `_get_visual_output_stream()` проверял только `isatty()` — возвращал `None` для non-TTY subprocess (basher), даже если env var `FREEBUFF_FORCE_VISUAL=1`
    2. `notify()` cascade с early returns — `_print_visual_summary()` вызывался ТОЛЬКО при провале cascade (log success или all-fail), но НЕ при primary success. На Android 13+ termux-notification может silently заблокироваться, возвращая True — визуальный блок НИКОГДА не появлялся на успешных задачах
    3. Env var не пропагался в login shells (только ~/.bashrc, который source'ится interactive shells)
  - **Fix (2 итерации):**
    - **Round 1:** `_get_visual_output_stream()` теперь проверяет FREEBUFF_FORCE_VISUAL **первым** — если env var установлен, возвращает `sys.stderr` (bypass isatty check)
    - **Round 2 (redesign):** `notify()` cascade переписан — убраны ранние return, используется `if/elif/else` для установки `status` + `reason`, затем **ВСЕГДА** вызывается `_print_visual_summary()` перед return. Визуальный блок fires на ЛЮБОМ исходе cascade.
    - **Env propagation:** добавлено `export FREEBUFF_FORCE_VISUAL=1` в **~/.bashrc** (interactive) AND **~/.profile** (login). Субшелы наследуют env var автоматически.

### Channel-reason mapping (новый)
- Primary success: `"delivered via termux-notification"`
- Toast fallback success: `"delivered via termux-toast"`
- Log fallback success: `"log fallback (Android notification BLOCKED on Termux 13+)"`
- Total failure: `"ALL CHANNELS FAILED (проверьте ~/notifications.log)"`

### Tests
- `tests/test_notification.py` — **59 passed** (8.39s)
  - **DELETED:** `test_visual_summary_NOT_called_when_primary_succeeds` (contradicts new behavior)
  - **ADDED 6 new tests:**
    - `test_visual_summary_called_when_primary_succeeds` — primary success MUST fire visual
    - `test_visual_summary_called_when_toast_succeeds` — toast success MUST fire visual
    - `test_visual_summary_receives_correct_reason_primary` — channel_reason string
    - `test_visual_summary_receives_correct_reason_toast` — channel_reason string
    - `test_visual_summary_receives_correct_reason_log` — channel_reason string
    - `test_visual_summary_receives_correct_reason_all_failed` — channel_reason string
  - **ADDED 2 new tests (Round 1):**
    - `test_force_env_returns_stderr_even_when_both_redirected` — env var bypass
    - `test_force_env_value_styles_force_stderr` — yes/true/TRUE/YeS variants

### Verified
- 59/59 tests pass (~8.4s) — **0 failures**
- Smoke test: `FREEBUFF_FORCE_VISUAL=1 python3 -c "_print_visual_summary('test', 'body')"` → block fires in stderr ✓
- Subshell inheritance: `bash -c 'echo $FREEBUFF_FORCE_VISUAL'` → **1** (subshell inherits from login shell) ✓
- Code-reviewer: ship-it approved (5 non-blocking improvements: observability regression, duplicated env var check, misleading channel_reason on Android 13+, fragile test assertions, stale blank line)

### ⚠️ Known Limitation
- **Visual summary fires only when `notify()` is called.** Tasks run via basher agent that don't call notify() (e.g., custom Python scripts, file operations) still won't produce visible blocks. Workaround: explicitly call `notify_task_complete()` at end of important basher-run scripts, OR wrap basher invocations through `freebuff_cli.py` (which has `_main_with_notification()` wrapper).

---

## [5.24.3***REMOVED*** — 2026-07-30

### Added
- **Visual [SUMMARY***REMOVED*** fallback в интерактивный stderr/stdout (Phase 5.4)**
  - 4-я ступень cascade: после `~/notifications.log` срабатывает визуальный fallback блок
  - **Stdout-first semantics** (honor user literal request "stdout + log-файл"):
    - `_get_visual_output_stream()` — выбирает sys.stdout приоритетно, fallback на sys.stderr, returns None если оба redirected
    - `_is_visual_summary_enabled()` — True если EITHER stdout OR stderr is TTY, ИЛИ `FREEBUFF_FORCE_VISUAL=1`
  - **Visual block format**: pipe-safe ASCII box (═ ┌ ─ ├ ┘ │ chars), без ANSI-кодов:
    ```
    ═══════════════════════════════════════════════════
      [SUMMARY***REMOVED*** ✅ Phase 5.4 Visual Summary
    ───────────────────────────────────────────────────
      📋 Task:  ...
      📊 Status: ...
      ⏱ Time:   ...
      ───────────────────────────────────────────────────
      Channel: log fallback (Android notification BLOCKED)
    ═══════════════════════════════════════════════════
    ```
  - **Defensive title truncation**: title > 43 chars обрезается с `...` чтобы не вылезать за box border
  - **Defensive line truncation**: content > 52 chars обрезается с `...` (тоже чтобы не ломать геометрию)
  - **Logger pollution fix**: `logger.info(...)` → `logger.debug(...)` для визуального блока (basicConfig level=INFO)
  - **Width consistency**: внутренний separator использует `_VISUAL_BOX_WIDTH` (56 chars) без 2-space prefix

### Tests
- **`tests/test_notification.py`** — добавлено 17 новых тестов в `TestVisualSummary` + 4 фикса mock'ов:
  - Stream selection (5): stdout preferred, stderr fallback, None если оба redirected, disjunction check, full-width inner separator
  - Trigger logic (4): called on log success, called on all-fail, NOT called when primary/toast succeed
  - Content checks (3): contains title and channel, truncates long lines, returns False when disabled
  - Robustness (2): handles print exception, does not alter notify return
  - 4 mock fix: existing tests теперь мокают `_get_visual_output_stream` (pytest capture mode issue)

### Verified
- 58/58 tests pass (~10s) — **0 failures**
- End-to-end smoke: visual block печатается в stderr (при отсутствии TTY в stdout)
- Code-reviewer: **0 critical blockers, 1 non-blocking nit** (additional test for title truncation defensive)

---

## [5.24.2***REMOVED*** — 2026-07-30

### Fixed
- **scripts/test_crash_recovery.sh — container suicide prevention**
  - **Problem:** During crash recovery test runs in proot-distro, `pgrep -f "freebuff"` matched the test's grandparent process (the freebuff wrapper itself, several levels up in the process tree) and `kill -9` took down the entire container. Result: SIGKILL + futex panic during 3 consecutive runs (`Killed` + `The futex facility returned an unexpected error code`).
  - **Root cause:** Original script only checked immediate `$PPID`, not full ancestor chain. In proot, top-level wrapper is not direct parent.
  - **Fix:**
    - Auto-detect constrained envs (PROOT_WEAK_LSTAT / TERMUX_VERSION / uname / PREFIX match) and default `--no-kill=true`
    - Walk full ancestor chain via Python /proc/$pid/status `PPid:` (max 15 levels) — skip all ancestors during kill phase
    - Memory guard: skip kill -9 if `MemAvailable < 256 MB` (OOM-suicide prevention)
    - Extended CMD filter: skip `proot`, `login` processes
  - **Result:** 3/3 test runs passed (no SIGKILL, no container collapse)

### Verified
- 3/3 runs PASS ✅ (each ~30s, all 7 steps + cleanup)
- Bash syntax check ✅
- Auto-detect корректно срабатывает в текущем окружении
- Code-reviewer: **0 critical issues, 2 non-blocking minor improvements** (verbose emoji, parent chain fallback edge case)

---

## [5.24.1***REMOVED*** — 2026-07-30

### Added
- **MANDATORY RUNTIME CONTRACT — Phase 5.2: Android 13+ Notification Fallback Chain**
  - 3-tier delivery cascade в `scripts/notification.py`:
    - Channel 1: `termux-notification` — основной канал (3-retry exponential backoff 1s/2s/4s, 10s timeout)
    - Channel 2: `termux-toast` — fallback 1 (Toasts НЕ подпадают под POST_NOTIFICATIONS ограничение Android 13+)
    - Channel 3: `~/notifications.log` — fallback 2 (всегда работает при FS-доступе)
  - Returns `True` если хоть один канал доставил уведомление (graceful degradation вместо строгой ошибки)
  - NEW env var: `FREEBUFF_NOTIFY_LOG` — переопределение пути к log fallback
  - Toast truncation: 240 chars max (Android обрезает более длинные)
  - ISO timestamp в log (UTC, ISO 8601 format)
- **`scripts/fix_termux_notifications.sh`** — диагностика + авто-открытие Android Settings Intent:
  - `bash scripts/fix_termux_notifications.sh` — открывает Settings → Apps → Termux:API → Notifications (1 тап от пользователя)
  - `--check` — только диагностика
  - `--silent` — тихая диагностика
  - 5 проверок: termux-notification binary, Termux:API apk, pm, termux-toast, log path
- **`docs/ops/ANDROID_NOTIFICATION_FIX.md`** — полная инструкция для пользователя:
  - 3 способа фикса (автоматический/вручную/am start)
  - Fallback-цепочка с примерами
  - Тестирование после исправления
  - История изменений v5.24.0 → v5.24.1

### Tests
- **`tests/test_notification.py`** — добавлено 16 новых тестов (всего 41/41 pass):
  - `TestTryToastChannel` (6): success, unavailable, fail, timeout, truncation, content
  - `TestTryLogChannel` (4): writes file, OSError, multi-entries, timestamp
  - `TestNotifyFallbackChain` (6): toast cascade, log cascade, all-fail, primary-only, FREEBUFF_NO_NOTIFY silent, content preserved
- 4 существующих теста обновлены для работы с cascade (мокают все 3 канала)

### Verified
- 41/41 tests pass (15s) — **0 failures**
- Bash `bash -n scripts/fix_termux_notifications.sh` ✅
- Python syntax check ✅
- End-to-end smoke test: `FREEBUFF_NO_NOTIFY=1 → silent; log fallback → ISO timestamp + content`
- Code-reviewer: **0 critical issues, 4 non-blocking minor improvements** (TOAST_TIMEOUT constant, OSError test isolation, ISO regex check, `-c white` flag comment)

### Issue Fixed
- Bash `"""` docstring в `scripts/fix_termux_notifications.sh` ломал `bash -n` (parens `(без root)` интерпретировались как subshell)
  - Решение: заменено на `#` комментарии (правильный bash-style docstring)

---

## [5.24.0***REMOVED*** — 2026-07-30

### Добавлено
- **MANDATORY RUNTIME CONTRACT — системные уведомления Android:**
  - `scripts/notification.py` — модуль отправки Android-уведомлений через Termux:API
  - `notify()` с retry (3 попытки, exponential backoff 1s/2s/4s, таймаут 10s)
  - `notify_task_complete()` / `notify_error()` — форматированные уведомления с иконками ✅/⚠/❌
  - `is_available()` — проверка доступности termux-notification (shutil.which + hardcoded fallback)
  - **`FREEBUFF_NO_NOTIFY=1`** — env var bypass для тестов/CI
  - `logging.basicConfig` для видимости логов ([INFO***REMOVED***/[ERROR***REMOVED*** в stderr)
  - `freebuff_cli.py` — `_main_with_notification()` wrapper с try/finally
  - `docs/ops/RUNTIME_CONTRACT.md` — полная документация контракта
  - 25 тестов (`tests/test_notification.py`) — 0 failures
  - **Тест-изоляция:** autouse fixture unsets FREEBUFF_NO_NOTIFY для каждого теста
  - **Текущее состояние проекта:** 1797 тестов, 32+ компонентов

## [5.23.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — RAG 2.0 Engine (семантический поиск с ранжированием):**
  - `scripts/rag_engine.py` — **RAGEngine**: 5 режимов поиска (keyword, semantic, hybrid, hybrid_rrf, full_rrf), Reciprocal Rank Fusion (RRF), feature-based re-ranking (7 признаков), query expansion из результатов поиска
  - `RAGResult`, `RAGReport`, `FeatureVector` — dataclasses с JSON-сериализацией
  - `rrf_merge()` — RRF fusion с k=60, поддержка произвольного количества списков, tracking источников
  - `_extract_features()` — 7 признаков: coverage, term_frequency, position, length_norm, freshness, bm25_score, semantic_score
  - `rerank()` — feature-based переранжирование с конфигурируемыми весами
  - `expand_query()` — расширение запроса терминами из top-K результатов
  - 3 MCP инструмента в `scripts/mcp_server.py`: `rag_search`, `rag_hybrid`, `rag_rerank`
  - CLI: `python scripts/rag_engine.py search | hybrid | rerank | expand` с цветным выводом и JSON
  - 60 тестов (`tests/test_rag_engine.py`) — 0 failures
  - Всего: **1772 теста**, **31+ компонент**

## [5.22.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Collaboration Roles:**
  - `scripts/roles.py` — **RoleEngine**: SQLite-персистентность, 6 стандартных ролей (developer, reviewer, documenter, researcher, archiver, orchestrator), назначение/отзыв ролей, маппинг capabilities
  - Интеграция с PresenceEngine — роли синхронизируются в metadata агента
  - Интеграция с CollaborationEngine — project-роли → collab-роли (orchestrator→owner, developer/reviewer→editor, остальные→viewer)
  - Capability mapping — каждая роль даёт набор capabilities (coding, testing, review, research, etc.)
  - 5 MCP инструментов в `scripts/mcp_server.py`: `roles_list`, `roles_get`, `roles_assign`, `roles_unassign`, `roles_stats`
  - CLI: `python scripts/roles.py list | get | assign | unassign | by-role | stats | sync` с цветным выводом
  - 41 тест (`tests/test_roles.py`) — 0 failures

## [5.21.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Project Pulse (лента изменений проекта):**
  - `scripts/project_pulse.py` — **ProjectPulse**: SQLite-персистентность, отслеживание git-коммитов (scan_git), изменений файлов (scan_files), событий EventBus (subscribe_eventbus + _on_event)
  - 15+ типов событий пульса: git.commit, git.branch, file.created/modified/deleted, event.task/step/collab/memory/plugin/presence/metrics
  - Ref-based дедупликация — один коммит/файл не создаёт дубликатов
  - CLI: `python scripts/project_pulse.py list | stats | scan | watch` с цветным выводом и JSON
  - 3 MCP инструмента в `scripts/mcp_server.py`: `pulse_list`, `pulse_stats`, `pulse_scan`
  - EventBus подписка на `*` — все события проекта автоматически попадают в ленту
  - 33 теста (`tests/test_project_pulse.py`) — 0 failures

## [5.20.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 4 — Плагины (3 шт):**
  - `plugins/tg_messenger/` — Telegram Messenger Plugin: отправка сообщений через Telegram Bot API, авто-форвардинг system.*/collab.* событий, управление ботом (start/stop), очередь сообщений
  - `plugins/system_monitor/` — System Monitor Plugin: CPU, память, батарея, температура, health check. Fallback-реализации через /proc/* (Termux-совместимые), фоновый watch loop с публикацией system.metrics событий
  - `plugins/knowledge_sync/` — Knowledge Sync Plugin: синхронизация MemoryEngine → KnowledgeEngine, авто-индексация при memory.stored событиях, force_reindex, полная перестройка индекса
  - Все плагины: BasePlugin lifecycle (on_load/enable/disable/unload), EventBus подписка, do_* actions, manifest.json с метаданными, graceful degradation при отсутствии зависимостей
  - 39 тестов (`tests/test_plugins_phase4.py`) — 0 failures

## [5.19.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 6 — Metrics Dashboard:**
  - `buffy-playground/public/metrics-dashboard.html` — standalone HTML dashboard с Chart.js
  - Визуализация: VCR, SRG, CpVO, RRR, TTD — значения, тренды, интерпретации
  - Health Score gauge (0-10) с Canvas-рендерингом
  - Trend charts для каждой метрики (Chart.js line chart)
  - Auto-refresh каждые 30 секунд, тёмная тема
  - `/dashboard` endpoint в `scripts/mcp_fastapi.py` (GET → HTMLResponse)
  - 12 тестов — 0 failures

## [5.18.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Live Collaboration для CoWork Platform:**
  - `scripts/collaboration.py` — **CollaborationEngine**: SQLite-персистентность (sessions + messages + participants), EventBus-интеграция (события `collab.created/joined/left/closed/message`), PresenceEngine интеграция, система ролей (owner/editor/viewer), история сообщений с пагинацией
  - `CollaborationSession` — 12 полей: session_id, topic, status, owner, participants, timestamps, message_count
  - `CollabMessage` — 5 типов сообщений: text, system, task, file, decision, code
  - 8 MCP инструментов в `scripts/mcp_server.py`: `collab_create`, `collab_list`, `collab_get`, `collab_join`, `collab_leave`, `collab_send`, `collab_history`, `collab_status`
  - CLI: `python scripts/collaboration.py list | get | create | close | send | history | status` с цветным выводом и JSON-режимом
  - Graceful degradation без EventBus и без PresenceEngine
  - 60 тестов (`tests/test_collaboration.py`) — 0 failures
  - Всего: **60 новых тестов + 8 MCP инструментов + 7 CLI команд**

## [5.17.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Agent Presence для CoWork Platform:**
  - `scripts/presence.py` — PresenceEngine: SQLite-персистентность (таблицы `presence` + `presence_history`), EventBus-интеграция (события `presence.online/offline/busy/away/error/heartbeat`), heartbeat loop с авто-prune офлайн-агентов, thread-safe, rich metadata
  - `AgentPresence` dataclass (14 полей) + `PresenceStatus` с валидацией
  - 3 MCP инструмента в `scripts/mcp_server.py`: `presence_list`, `presence_get`, `presence_history`
  - CLI: `python scripts/presence.py list | get | status | history` (цветной + JSON)
  - Offline marking on shutdown — `stop()` отмечает всех ONLINE агентов как OFFLINE
  - Graceful degradation без EventBus
  - 67 тестов (`tests/test_presence.py`) — 0 failures

## [5.16.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 6: HTTP Metrics endpoints (scripts/mcp_fastapi.py):**
  - 8 новых REST endpoints для Metrics Engine:
    - `GET /metrics/report` — полный отчёт VCR/SRG/CpVO/RRR/TTD + Health Score
    - `GET /metrics/vcr`, `/metrics/srg`, `/metrics/cpvo`, `/metrics/rrr`, `/metrics/ttd` — каждая метрика отдельно
    - `GET /metrics/trend/{name***REMOVED***` — история метрики (с `?limit=N`)
    - `GET /metrics/status` — диагностика MetricsEngine (БД, EventBus)
  - `_get_metrics()` — lazy init MetricsEngine при первом запросе
  - `_metrics_response(data, fmt)` — поддержка `?fmt=json` (default) и `?fmt=text`
  - Все эндпоинты следуют паттерну lazy init (как `_server` и `_sessions`)

- **Session isolation в test_crash_recovery.sh:**
  - `scripts/test_crash_recovery.sh` — Шаг 0: очистка ACTIVE/CHECKPOINT сессий перед стартом через `cm.list_sessions()` + `cm.complete_session()`
  - Temp-файлы с `$$` в имени для избежания race condition между прогонами
  - **3/3 прогона PASS** (против 2/3 в v5.15.0)

- **Тесты — 12 тестов, 0 failures:**
  - `TestMetricsEndpoints` — report, vcr, srg, cpvo, rrr, ttd, status, trend (known/unknown/limit), all endpoints return JSON

### Проверка
- 47 тестов mcp_fastapi — **0 failures** (35 existing + 12 новых)
- 3/3 прогона test_crash_recovery.sh с --no-kill: PASS ✅
- Code review: все замечания исправлены

---

## [5.15.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 0: Close Context Loop (TASK_PHASE_0_CLOSE_CONTEXT_LOOP.md):**
  - `freebuff_cli.py :: cmd_buffy()` — интеграция StreamBridge: создаёт сессию, логирует user-запрос (`log_user`), логирует assistant-ответ (`log_assistant`), создаёт чекпоинт (`checkpoint`)
  - Цикл контекста ЗАМКНУТ: `cmd_buffy()` → StreamBridge → `context.db` → `get_context_resume()`
  - Graceful degradation: если StreamBridge недоступен, `bridge = None` — функция работает как раньше
  - `scripts/test_crash_recovery.sh` — тест смерти сессии (6 шагов: создание → запись → kill/bootstrap → верификация → resume)
  - `--no-kill` режим для proot-окружений (kill -9 убивает родительский proot-distro процесс)
  - `scripts/test_crash_recovery_verify.py` — верификация целостности контекста после краша

### Проверка
- 2/3 прогона test_crash_recovery.sh с --no-kill: PASS ✅
- `cmd_buffy()` StreamBridge интеграция: 6/6 проверок ✅
- Полный цикл контекста: сессия → БД → resume подтверждён ✅
- Code review: все замечания исправлены (bash quoting, temp-файлы вместо heredoc в `$()`, FK constraint, `--no-kill` добавлен)

---

## [5.14.0***REMOVED*** — 2026-07-30

### Добавлено
- **Distributed Agents — Phase 4 завершение (scripts/distributed_agents.py):**
  - `AgentMesh` — thread-safe реестр распределённых агентов с find_by_capability, get_stats, get_summary, task_history, get_agent_stats
  - `TaskDistributor` — 3 стратегии распределения задач: best_match (по confidence), round_robin (циклически), specific (к указанному агенту) + distribute_to_all (broadcast)
  - `DistributedCoordinator` — полный lifecycle (start/stop), register_agent() с авто-генерацией имени, spawn_agent() через Bridge Layer, execute_agent_task(), execute_parallel(), remove_agent(), broadcast_to_all()
  - `DistributedWorkflow` — DAG-зависимости (depends_on), параллельное выполнение шагов, broadcast шаги, разрешение зависимостей (_get_ready_steps, _get_blocked_steps)
  - Мониторинг агентов (_monitor_loop) с проверкой статуса через Bridge Layer
  - EventBus публикация: `distributed.started/stopped`, `agent_registered/online/offline/removed`, `task_completed`, `workflow_planning/progress/completed`
  - CLI: `python scripts/distributed_agents.py agents | spawn | remove | workflow list | status | broadcast`

- **MCP Server интеграция (5 инструментов):**
  - `distributed_list` — список всех агентов в mesh
  - `distributed_spawn` — регистрация/подключение нового агента
  - `distributed_run` — запуск распределённого workflow
  - `distributed_status` — статус агентов и workflow
  - `distributed_broadcast` — broadcast сообщения всем агентам
  - `_get_distributed_coordinator()` — lazy accessor (паттерн как у BridgeLayer) c auto-register в MCP
  - EventBus публикация: `distributed.listed`, `distributed.spawned`, `distributed.ran`, `distributed.status`, `distributed.broadcasted`

- **Тесты — 55 тестов, 0 failures (35s):**
  - `TestTypes` (7): AgentNode, AgentNodeStatus, WorkCoordStatus, AgentTask, WorkflowStep, WorkflowPlan.to_dict
  - `TestAgentMesh` (12): register/unregister, update_status, set_error, list(фильтр/по статусу/по типу), find_by_capability, online_count, summary, task_history, get_agent_stats
  - `TestTaskDistributor` (6): best_match, unknown capability, specific, unknown agent, round_robin, distribute_to_all
  - `TestDistributedCoordinator` (10): lifecycle, register, auto-name, spawn with/without bridge, max_agents, remove, broadcast, execute_task, execute_parallel, no-bridge fallback
  - `TestDistributedWorkflow` (5): basic, broadcast, dependencies, get_ready, get_blocked
  - `TestCLI` (5): main, agents, status, spawn, workflow list
  - `TestMCPIntegration` (10): tools registered, handlers exist, graceful degradation, validation

### Проверка
- 1414 общих тестов — **0 failures** (420s)
- Code review: 3 итерации фиксов (indentation, imports, enum comparison, auto-name)

---

## [5.13.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase E — buffy-ctx CLI (freebuff_cli.py):**
  - `freebuff ctx push [session_id***REMOVED***` — экспорт контекста сессии в JSON (сообщения, чекпоинты, решения, верификации)
  - `freebuff ctx pull <file.json>` — импорт контекста из JSON с восстановлением сессии
  - `freebuff ctx status [session_id***REMOVED***` — статус контекста (проект, сообщения, токены, верификации, экспорты)
  - `_ctx_export_dir()` — функция вместо module-level константы (учитывает изменения WORKSPACE)
  - Экспорты сохраняются в `context/exports/ctx_<session>_<timestamp>.json`

- **Тесты — 17 тестов, 0 failures:**
  - `TestCtxPush` (5): by id, auto active, invalid session, no active, export dir
  - `TestCtxPull` (5): valid file, not found, invalid json, missing section, wrong extension
  - `TestCtxStatus` (4): by id, auto active, no session, invalid
  - `TestRoundtrip` (1): push→pull preserves data
  - `TestCLIEntryPoint` (2): ctx push, ctx status CLI commands

### Проверка
- 1359 общих тестов — **0 failures** (390s)
- Code review: 2 замечания исправлены (CONTEXT_EXPORT_DIR → _ctx_export_dir(), _patch_workspace module parameter)

---

## [5.12.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase D — Vector Memory (6-й уровень памяти):**
  - `MemoryLevel.VECTOR = "vector"` — 6-й уровень памяти в MemoryEngine
  - `VectorBackend` класс — опциональный Chromadb бэкенд:
    - `is_available()` — проверка доступности chromadb
    - `store(entry_id, text, metadata)` — сохранение вектора
    - `search(query, top_k, filter, level)` — поиск по векторной близости
    - `delete(entry_id)` — удаление вектора
    - `count()` — количество записей
    - `wipe()` — очистка коллекции
  - Graceful degradation: chromadb не обязателен — все операции возвращают ошибку
  - `MemoryEngine.store()` для VECTOR уровня: JSON + вектор (raise RuntimeError если нет chromadb)
  - `MemoryEngine.delete()` — исправлен порядок: чтение entry_id ДО unlink файла
  - `MemoryEngine.vector_search(query, top_k, level)` — семантический поиск с обогащением MemoryEntry
  - CLI: `python scripts/memory_engine.py vector_search "query" --top-k 5 --json`

- **Тесты — 28 тестов, 0 failures:**
  - `TestMemoryLevelVector` (2): enum value, count
  - `TestVectorBackendNoChromadb` (6): init, store, search, delete, count, wipe — graceful degradation
  - `TestVectorBackendMocked` (10): init, store, search sorted, search empty, delete, count, wipe, edge cases
  - `TestMemoryEngineVectorNoChromadb` (9): store raises, error msg, other levels work, search empty, retrieve, delete, list
  - `TestMemoryEngineVectorMocked` (8): store, retrieve, list, delete, search includes, vector_search, stats
  - `TestBuildContextWithVector` (2): excludes by default, includes explicit

### Исправлено
- `scripts/memory_engine.py` — `delete()` читал `filepath.read_text()` после `filepath.unlink()` (FileNotFoundError). Исправлено: чтение entry_id до удаления файла, передача id в vector_backend.delete() после unlink

### Проверка
- 1342 общих теста — **0 failures** (337s)
- Code review: 1 баг исправлен (delete order)
- 40 тестов Memory Engine обновлены (test_memory_level_count: 5→6)

---

## [5.11.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase C — Metrics Engine (scripts/metrics.py):**
  - 5 метрик качества разработки:
    - **VCR** (Verified Completion Rate) — доля `verified_status='verified_ok'` от всех верифицированных задач
    - **SRG** (Self-Report Gap) — разница между claimed_status='done' и фактической верификацией
    - **CpVO** (Cost per Verified Outcome) — средняя длительность на единицу результата (ms/verification)
    - **RRR** (Rework/Rollback Rate) — доля задач с последующими фиксами после верификации
    - **TTD-false** (Time-To-Detect false) — среднее время до обнаружения ошибки (minutes)
  - `MetricsEngine` — вычисление метрик из context.db (action_verifications) + verifier.db (verification_results)
  - `compute_report()` — композитный отчёт + `save_snapshot()` для трендов
  - `get_trend()` — история значений метрики из metrics.db
  - `Health Score` (0-10) — общая оценка на основе 5 метрик
  - EventBus: публикация `metrics.report` при сохранении снимка
  - CLI: `report`, `vcr`, `srg`, `cpvo`, `rrr`, `ttd`, `trend <metric>`, `status` — с JSON выводом
  - **MCP интеграция:** `_get_metrics_engine()` lazy accessor + 3 инструмента: `metrics_report`, `metrics_vcr`, `metrics_srg`

- **Тесты — 37 тестов, 0 failures:**
  - `TestMetricResult` (3): defaults, rounding, display_name
  - `TestMetricsReport` (2): defaults, to_dict
  - `TestVCR` (3): value, no_data, interpretation
  - `TestSRG` (3): value, no_data, trend
  - `TestCpVO` (3): value, no_verifier_db, with_failures
  - `TestRRR` (3): value, no_data, trend
  - `TestTTD` (3): value, no_data, no_failures
  - `TestReport` (2): all_metrics, with_save
  - `TestSetupDatabases` (2): all_exist, all_missing
  - `TestSnapshot` (2): save_and_get_trend, get_empty_trend
  - `TestHealthScore` (3): baseline, perfect, worst
  - `TestStatus` (2): status_ok, with_eventbus
  - `TestEventBus` (2): report_event, no_crash
  - `TestCLI` (2): json_format, report_dict
  - `TestMCPIntegration` (2): tools_registered, handlers_available

### Проверка
- 188 LEVIATHAN Phase A+B+C тестов — **0 failures** (51s)
- Code review: unused imports исправлены

---

## [5.10.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Verifier + Orchestrator интеграция (шаг 1.3):**
  - `scripts/orchestrator.py` — `Orchestrator.__init__()` теперь принимает `verifier` и `context_manager` параметры (опциональные, обратная совместимость)
  - `_execute_step()` — после `StepStatus.SUCCESS` вызывает `_verify_step()` для верификации результата
  - `_verify_step()` — новый метод:
    - Запускает `Verifier.verify()` для успешного шага
    - Устанавливает `claimed_status='done'` через `ContextManager.set_claimed_status()`
    - Устанавливает `verified_status` через `ContextManager.set_verified_status()`
    - Публикует `step.verified` событие с результатами проверки
    - Safe serialization: корректно обрабатывает как dataclass, так и mock-объекты
    - Ошибки верификации не ломают workflow (изолированы в try/except)
  - Документация: `step.verified` добавлен в список событий
  - **5 тестов** — 0 failures:
    - verifier вызван для успешного шага
    - verifier + context_manager: set_claimed_status + set_verified_status вызваны
    - step.verified событие через EventBus
    - Ошибка verifier не ломает workflow
    - Failed step не вызывает verifier

### Проверка
- 1271 общий тест — **0 failures** (327s)
- Code review: все замечания исправлены

---

## [5.9.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Action Verifications (шаг 1.1-1.2):**
  - `scripts/context_manager.py` — SCHEMA_VERSION 4→5, миграция `_migrate_v4_to_v5()`:
    - Новая таблица `action_verifications` (id, session_id, message_id, task_id, claimed_status, verified_status, verified_by, verified_at, verification_results) с 4 индексами
  - 4 новых метода:
    - `set_claimed_status()` — установка claimed_status (pending/done/failed) с upsert по task_id
    - `set_verified_status()` — установка verified_status (verified_ok/verified_fail) с результатами проверки
    - `get_verification()` — получение статуса верификации по task_id
    - `list_verifications()` — список верификаций с фильтрацией по status/session_id/limit
  - EventBus: публикация `verification.claimed` и `verification.completed`

- **План интеграции LEVIATHAN:**
  - `docs/LEVIATHAN_INTEGRATION_PLAN.md` — полный план с 4 шагами (A→D), детальным описанием каждого изменения, оценкой часов и тестов

### Проверка
- 95 тестов Phase A+B — **0 failures** (18s)
- Code review: все замечания исправлены

---

## [5.8.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase A — Schema Extension:**
  - `scripts/context_manager.py` — SCHEMA_VERSION 3→4, миграция `_migrate_v3_to_v4()`:
    - Новая таблица `arch_decisions` — архитектурные решения (id, session_id, title, context, decision, alternatives, rationale, consequences, status)
    - Новая таблица `invariants` — инварианты (id, name, description, assertion_type, assertion_params, enabled, severity, last_checked, last_result)
  - 6 новых методов в ContextManager:
    - `log_decision()` — логирование архитектурного решения с полным контекстом
    - `get_decisions()` — список решений с фильтрацией по session_id/status/limit
    - `set_invariant()` — установка инварианта (upsert по имени)
    - `get_invariant()` — получение инварианта по имени
    - `check_invariant()` — проверка инварианта (file_exists/content_match/shell/sql_query)
    - `list_invariants()` — список инвариантов с фильтрацией enabled/severity
  - EventBus: публикация `decision.logged` и `invariant.checked`
  - Исправлено: свежая БД (version=0) теперь корректно создаёт arch_decisions + invariants таблицы
  - Исправлено: FK constraint убран из arch_decisions (сессия — опциональная связь)

- **Тесты — 20 тестов, 0 failures:**
  - `TestSchemaMigration` (3): version=4, таблицы существуют, миграция v3→v4
  - `TestArchitecturalDecisions` (5): log_decision, get_decisions фильтр/лимит/без сессии, EventBus
  - `TestInvariants` (12): set/get, overwrite, not found, list, enabled only, check (file_exists/shell/disabled/not found), EventBus, severity filter

### Проверка
- 20 тестов Phase A — **0 failures**
- 1247 общих тестов — **0 failures** (380s)
- Code review: 3 стилистических замечания исправлены (inline imports, timeout config)

---

## [5.7.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Verification Framework:**
  - `scripts/verifier.py` — новый модуль независимой верификации результатов:
    - `VerificationRule` dataclass — правила верификации с 7 типами проверок: file_exists, file_contains, content_match, pytest, shell, sqlite, http
    - `VerifierStorage` — SQLite-хранилище (WAL-mode) с таблицами `verification_rules` и `verification_results` + индексы
    - `Verifier` — основной класс: `verify()`, `add_rule()`, `remove_rule()`, `list_rules()`, `seed_default_rules()`, `get_summary()`, `get_results()`, `get_stats()`
    - `_resolve_template()` — шаблонизация `{{variable***REMOVED******REMOVED***` в параметрах правил
    - **EventBus интеграция**: подписка на `task.claimed` для авто-верификации, публикация `task.verified` и `verifier.rule_added`
    - **CLI**: 4 подкоманды — `verify`, `rules` (list/add/remove/seed), `status`, `diagnose`
    - 7 встроенных правил для task_type: implement, test, refactor, research, any

- **Тесты — 56 тестов, 0 failures:**
  - `TestVerificationRule` (6): defaults, validation, weight clamping
  - `TestVerificationResult` (2): defaults
  - `TestVerifierStorage` (12): init, CRUD rules, CRUD results, summary, stats, enabled filter
  - `TestTemplateResolution` (5): simple, multiple, unknown, empty
  - `TestVerifier` (16): seed, idempotent, force, add, remove, list, verify, summary, results, stats, diagnose, EventBus auto-verification, edge cases
  - `TestCheckers` (12): file_exists (found/not found), file_contains (found/not found/min_length/missing), shell (success/failure/template), sqlite (success/few_rows/missing_db), http (success/failure with mocks)
  - `TestEdgeCases` (2): empty context, duplicate task, checker registry integrity

### Проверка
- 56 тестов verifier — **0 failures** (22.84s)
- 1226 общих тестов — **0 failures** (298s)
- Code review: 3 замечания исправлены (***REMOVED*** → module level, sqlite row_count, content_match checker)

---

## [5.6.0***REMOVED*** — 2026-07-30

### Добавлено
- **Priority 1 компоненты — полная документация по шаблону TEMPLATE_COMPONENT_DOCUMENTATION.md:**
  - `docs/core/CONTEXT_MANAGER_SPECIFICATION.md` — ContextManager (назначение, архитектура, API, реализация)
  - `docs/core/MEMORY_ENGINE_SPECIFICATION.md` — MemoryEngine (5 уровней памяти, файловое хранение)
  - `docs/core/KNOWLEDGE_ENGINE_SPECIFICATION.md` — KnowledgeEngine (FTS5 + TF-IDF + Semantic)
  - `docs/core/GRAPH_INDEX_SPECIFICATION.md` — GraphIndex (граф связей, BFS обход)
  - `docs/core/EVENT_BUS_SPECIFICATION.md` — EventBus (publish/subscribe, wildcard)
  - `docs/core/ORCHESTRATOR_SPECIFICATION.md` — Orchestrator (FSM/DAG workflow, планировщик)
  - `docs/core/MODEL_GATEWAY_SPECIFICATION.md` — ModelGateway (единый шлюз LLM, fallback)
  - `docs/core/TOOL_RUNTIME_SPECIFICATION.md` — ToolRuntime (безопасные инструменты, ParamSchema)
  - `docs/core/PLUGIN_API_SPECIFICATION.md` — PluginAPI (lifecycle, manifest, discovery)
  - `docs/plugin/BRIDGE_LAYER_SPECIFICATION.md` — BridgeLayer (MCP ↔ ACP мост)
  - `docs/plugin/ACP_PROTOCOL_SPECIFICATION.md` — ACPProtocol (Agent Collaboration Protocol)
  - `docs/plugin/MCP_CLIENT_SPECIFICATION.md` — MCPClient (Stdio/HTTP транспорт)
  - `docs/plugin/MCP_SERVER_SPECIFICATION.md` — MCPServer (25+ MCP инструментов)
  - Каждая спецификация содержит 9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связанные компоненты

### Индексация
- `docs/INDEX.md` — добавлены ссылки на все 13 новых спецификаций
- Все спецификации взаимосвязаны через секцию «Связанные компоненты»

### Проверка
- 13 компонентов задокументированы по единому шаблону
- Каждый doc содержит: ASCII-диаграмму, полный API с примерами, секцию ошибок
- Code review: все замечания исправлены

---

## [5.5.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Context — полный архитектурный аудит ([promt18.md***REMOVED***(pompts/promt18.md)):**
  - `docs/audits/LEVIATHAN_CONTEXT_AUDIT.md` — 10-раздельный анализ (модель LEVIATHAN, сопоставление с Buffy, пересечения, дублирование, пробелы, Red Team, эволюционный план, дорожная карта, оценка 7.0/10 vs 5.3/10, каноническая архитектура)
  - `docs/vision/ROADMAP.md` — LEVIATHAN раздел обновлён: 4 фазы интеграции (Schema Extension → Verification Framework → Metrics Engine → Vector Memory) с оценкой часов, рисков и тестов

- **Компонентная документация по шаблону ([promt19.md***REMOVED***(pompts/promt19.md)):**
  - `docs/core/EVENT_STORE_SPECIFICATION.md` — полная документация EventStore по шаблону (9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связи)
  - `docs/core/SESSION_MESH_SPECIFICATION.md` — документация SessionMesh по шаблону
  - `docs/core/NODE_MESH_SPECIFICATION.md` — документация NodeMesh по шаблону

- **Индексация:**
  - `docs/INDEX.md` — добавлены ссылки на LEVIATHAN_CONTEXT_AUDIT, EVENT_STORE_SPECIFICATION, SESSION_MESH_SPECIFICATION, NODE_MESH_SPECIFICATION

### Проверка
- Все спецификации заполнены по единому шаблону TEMPLATE_COMPONENT_DOCUMENTATION.md
- Каждая спецификация содержит: 9 разделов, API с примерами, тесты, конфигурацию, ошибки, сценарии использования
- Code review: замечания по структуре и полноте документации исправлены

---

## [5.4.0***REMOVED*** — 2026-07-30

### Добавлено
- **Runtime Installer — Шаг 3 из TASK.md (task-framework):**
  - Авто-установка AI Runtime через Bootstrap Engine: `freebuff`, `claude-code`, `openclaw`
  - `freebuff_plugin/bootstrap/engine.py`:
    - Добавлен OpenClaw в `DEFAULT_RUNTIMES` (pip install openclaw, bin_name: openclaw)
    - Добавлен `install_runtime_by_name(name)` — точечная установка Runtime по имени
    - Добавлен `list_available_runtimes()` — список всех Runtime с статусом установки
  - `scripts/mcp_server.py`:
    - Добавлен MCP tool `runtime_install` (name: required) — установка Runtime
    - Добавлен MCP tool `runtime_list_available` — список доступных Runtime
    - После установки вызывается `registry.discover()` для регистрации Runtime
  - **16 тестов** (bootstrap engine: 9 + mcp_server: 7) — 0 failures:
    - install_runtime_by_name: known, unknown, claude-code, openclaw, already installed, steps
    - list_available_runtimes: all 3 runtimes present
    - MCP runtime_install: success (verify discover call), missing name, unknown runtime
    - MCP runtime_list_available: returns 3 runtimes
    - Tools in list, schema validation

### Проверка
- 20 новых тестов (9 bootstrap + 7 mcp_server + 4 refactored) — **0 failures**
- Code review: 3 замечания исправлены (dead code removed, discover assertion added, test assertion fixes)

---

## [5.3.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Context Integration & Component Documentation Template ([promt18.md***REMOVED***(pompts/promt18.md), [promt19.md***REMOVED***(pompts/promt19.md)):**
  - `docs/core/TEMPLATE_COMPONENT_DOCUMENTATION.md` — универсальный шаблон документирования компонентов (9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связанные компоненты)
  - `docs/vision/ROADMAP.md` v3.1.0 — добавлены:
    - LEVIATHAN Context Integration (unified context schema, `buffy-ctx` CLI, task queue, handoff, reaper, context HTTP API)
    - Phase 6: Context Verification & Quality Assurance (VCR/SRG/CpVO/RRR/TTD-false metrics)
    - Phase 7: CoWork / Companion Platform (Presence, Live Collaboration, RAG 2.0)
  - `docs/INDEX.md` — ссылка на шаблон документации компонентов
  - `BUFFY.md` — добавлена ссылка на шаблон и раздел Phase 6: Context Verification & QA

---

## [5.2.0***REMOVED*** — 2026-07-29

### Добавлено
- **Policy Engine — пользовательские политики выбора Runtime:**
  - `freebuff_plugin/policy/` — модуль Policy Engine (`engine.py`, `config.py`, `rules.py`)
  - `PolicyEngine` — выбор Runtime по capability с fallback chain и constraints
  - Поддержка правил: `min_confidence`, `max_latency`, `exclude`, `required_flags`
  - `runtime/policies.json` — пользовательские политики в JSON (не gitignored)
  - Интеграция в `scripts/mcp_server.py`: `runtime_generate` сначала использует PolicyEngine, затем fallback на `RuntimeCapabilityRegistry`
  - 16 тестов (`tests/test_policy_engine.py`) — 0 failures

---

## [5.1.0***REMOVED*** — 2026-07-29

### Добавлено
- **structure.md — реорганизация документации:**
  - `docs/core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` — спецификация Session Mesh v2.0
  - `docs/core/PROMPT_IMPLEMENTATION_v1.0.md` — промпт реализации (копия promt17.md)
  - `docs/INDEX.md` — обновлён: добавлены Mesh-документы, IDEAS, FILE_REGISTRY
  - `BUFFY.md` — добавлена секция «Session Mesh v2.0», обновлены пути
- **promt17.md — Session Mesh v2.0 Phase 0:**
  - `freebuff_plugin/mesh/` — структура директорий (core/, node/, session/, agent/, transport/, storage/) — 7 файлов `__init__.py` с docstrings
  - `requirements.txt` — добавлены mesh-зависимости: ulid-py, websocket-client, diff-match-patch
- **Сортировка корневых файлов:**
  - `IDEAS.md` → `docs/decisions/IDEAS.md`
  - `FILE_REGISTRY.md` → `docs/projects_meta/FILE_REGISTRY.md`

---

## [5.0.0***REMOVED*** — 2026-07-29

### Добавлено

#### Стратегический слой (Task 0)
- **VISION_3.0.md** — раздел «Три режима работы» (Local/Cloud/Hybrid), честная фиксация gaps по ACP/Bridge/KeyPool
- **`docs/core/ARCHITECTURE_PRINCIPLES.md`** — 8 архитектурных принципов платформы (§2.7 Marketplace-Ready)
- **`docs/core/COMPATIBILITY_MATRIX.md`** — матрица совместимости Runtime и протоколов
- **`docs/core/RUNTIME_VALIDATION_FRAMEWORK.md`** — фреймворк валидации Runtime

#### Реорганизация docs/ (Task 1)
- **45 файлов мигрированы** из flat `docs/` в 7 подпапок:
  - `docs/core/` — спецификации и архитектурные документы
  - `docs/vision/` — ROADMAP, VISION_2.0/3.0, PRODUCT_MANIFESTO
  - `docs/decisions/` — ADR и DECISIONS
  - `docs/audits/` — аудиты (DRIFT_REPORT, AUDIT_*)
  - `docs/plugin/` — FREEBUFF_PLUGIN_*
  - `docs/projects_meta/` — WORKERS, LIGHTPANDA_INTEGRATION, PROJECT_REGISTRY
  - `docs/ops/` — TROUBLESHOOTING, TASK_TEMPLATE, AGENTS
- **`docs/INDEX.md`** — навигационный индекс по всем документам
- **Все перекрёстные ссылки обновлены** в коде, тестах, и документах
- **`PROJECT_REGISTRY.md`** и **`seed_knowledge.py`** — пути обновлены

#### Граница ядро↔плагин (Task 2)
- **`scripts/mcp_server.py`** — импортирует плагин только через `__init__.py` с try/except graceful degradation
- **`freebuff_plugin/mcp_client.py`** и **`bridge_layer.py`** — убраны жёсткие пути, импорты обёрнуты
- **`freebuff_plugin/INTEGRATION_CONTRACT.md`** — контракт между ядром и плагином
- **`scripts/doctor.py`** — CLI-инструмент диагностики (`--full`, `--check`) с EventBus интеграцией
- **`runtime/recipes/freebuff.md`** и **`runtime/recipes/claude_code.md`** — Runtime Recipes

#### Marketplace-ready архитектура (Task 2.3)
- **`runtime/providers/`** — YAML-манифесты для freebuff, claude_code, openclaw
- **`runtime/plugins/`** — плагин-система (расширения без изменения ядра)
- **`runtime/MARKETPLACE.md`** — трёхслойная архитектура, проверка «без изменения ядра»
- **Provider auto-discovery** — `load_providers_from_dir()`, `register_provider()`, fallback YAML-парсер
- **69 тестов** (+9 новых TestProviderLoading + TestProviderIntegration)

#### Унификация projects/ (Task 3)
- **`diet_platform/`** — созданы README.md + MANIFEST.md (из TEAM_NOTES.md/PRODUCT_BACKLOG.md)
- **`realtor_automation/`** — создан MANIFEST.md
- **`tg_terminal_messenger/`** — `manifest.md` → `MANIFEST.md` (единый регистр, two-step rename для git)

#### Чистка data/context.db (Task 4)
- **91 → 45 сессий** (удалено 46 тестовых/мусорных: Auto-conspect, Imported from Aider/OpenClaw, freebuff session, TMUX_OK, bridge OK, Тест стриминг)
- **data/ и context/** — чисто (только штатные conversation.log)
- **`.gitignore`** — добавлены `*.pyc`, `*.pyo`

#### Аудит scripts/ (Task 5)
- **4 мёртвых скрипта → `scripts/archive/`**:
  - `import_qwen.py` (0 code references)
  - `import_sessions.py` (0 code references)
  - `phone_mcp_server.py` (0 code references)
  - `dashboard_api.py` (0 code references)
- **`FILE_REGISTRY.md`** и **`docs/core/SYSTEM_INVENTORY.md`** — ссылки обновлены

#### Полный smoke-test (Task 6)
- **1152 passed**, 1 skipped, 0 failures (305s)
- Импорт mcp_server + plugin __init__: OK
- seed_knowledge DEFAULT_DOC_SOURCES: все 6 путей валидны
- doc_reminder.sh: синтаксис + пути OK
- doctor.py --full: 58% health (11 OK, 6 warnings — допустимо для Termux)
- Граница ядро↔плагин: CLEAN

#### Интеграция CODE_QUALITY_STANDART
- **`pompts/CODE_QUALITY_STANDART.md`** — интегрирован как обязательный production-ready регламент
- Адаптирован под экосистему Freebuff, сохранены все пункты, добавлены специфичные

### Исправлено
- **`freebuff_plugin/event/replay.py:61`** — `IndentationError`: `import create_event` был на одной строке с комментарием в `elif self._bus:` блоке. Исправлена индентация, `import` вынесен на отдельную строку. Без фикса 61 тест не собирался.
- **`freebuff_plugin/runtime/registry.py`** — fallback YAML-парсер: dead code исправлен (`capabilities`/`bin_names`/`platforms`/`args` присваиваются в result), `current_section` больше не сбрасывается при индентированных `key: value`
- **`freebuff_plugin/runtime/registry.py`** — `_ensure_scores_loaded`: merge вместо overwrite (защита пользовательских `set_score()`)
- **`freebuff_plugin/runtime/registry.py`** — type mismatch: `List[str***REMOVED***` ← `Dict[str, float***REMOVED***` конверсия в `discover()`
- **`freebuff_plugin/runtime/registry.py`** — `_load_builtin_fallback`: merge вместо skip
- **`tests/test_runtime_abstraction.py`** — `test_custom_providers_dir`: `pytest.importorskip("yaml")` вместо безусловного импорта

### Проверка
- **1152 тестов** — 0 failures (305s)
- Граница Plugin→Core: CLEAN
- Граница Core→Plugin: CLEAN
- 3 провайдера загружаются: marketplace-ready
- Все 4 проекта унифицированы (README.md + MANIFEST.md)
- data/context.db: 91→45 сессий
- Smoke-test: все 6 проверок пройдены

---

## [4.10.0***REMOVED*** — 2026-07-29

### Добавлено
- **MCP + Runtime Abstraction Layer интеграция:**
  - `scripts/mcp_server.py` — добавлен `_get_runtime_registry()` lazy accessor (паттерн как у BridgeLayer / BootstrapEngine)
  - 5 новых MCP инструментов (секция 8: Runtime Abstraction Layer tools):
    - `runtime_list` — список зарегистрированных Runtime
    - `runtime_connect` — подключиться к Runtime
    - `runtime_disconnect` — отключиться от Runtime
    - `runtime_select` — выбрать активный Runtime
    - `runtime_generate` — генерация через выбранный Runtime (name / capability / active)
  - Выбор Runtime по capability через `RuntimeCapabilityRegistry`
  - Авто-подключение Runtime при генерации, если адаптер не активен
  - Валидация `messages` (список dict с `role` и `content`) и `temperature`/`max_tokens`
  - EventBus публикация: `runtime.listed`, `runtime.connected`, `runtime.disconnected`, `runtime.selected`, `runtime.generated`
  - 18 тестов (`tests/test_mcp_server.py::TestRuntimeTools`) — 0 failures:
    - list/connect/disconnect/select
    - generate by name / capability / active runtime
    - error paths: missing prompt, invalid temperature/max_tokens, invalid messages, connect failure, registry unavailable, capability unregistered, lazy accessor without auto-discovery

### Проверка
- 120 тестов MCP Server — **0 failures** (28s)
- Code review: 3 итерации (messages validation, no auto-discover, error paths)

---

## [4.9.0***REMOVED*** — 2026-07-29

### Добавлено
- **Runtime Abstraction Layer — Phase 1: Infrastructure Core (docs/core/RUNTIME_ABSTRACTION_SPECIFICATION.md):**
  - `freebuff_plugin/runtime/__init__.py` — типы: RuntimeStatus, SessionStatus, AdapterType, RuntimeConfig, RuntimeDefinition, RuntimeResult, RuntimeCapability, RuntimeSession, RuntimeHealth
  - `freebuff_plugin/runtime/adapter.py` — RuntimeAdapter ABC (connect/disconnect/ping/health/generate/list_capabilities) + StdioMCPAdapter (MCP STDIO транспорт) + HTTPMCPAdapter (MCP HTTP транспорт) + AdapterRegistry + default_adapter_registry
  - `freebuff_plugin/runtime/registry.py` — RuntimeRegistry: register, unregister, get, list, discover, set_active, connect/disconnect, get_status, JSON persistence; RuntimeCapabilityRegistry: list_capabilities, get_runtime_for_capability, score_runtime, set_score
  - `freebuff_plugin/runtime/adapters/__init__.py` — re-export FreebuffAdapter и ClaudeCodeAdapter
  - `freebuff_plugin/runtime/adapters/freebuff.py` — FreebuffAdapter: поиск бинарника (which, ~/.local/bin, pip), MCP STDIO транспорт, 5 capability (coding, planning, architecture, testing, research)
  - `freebuff_plugin/runtime/adapters/claude.py` — ClaudeCodeAdapter: поиск claude (which, npm root -g), MCP STDIO транспорт, 5 capability (coding, review, architecture, documentation, planning)
  - **Композиция с Bridge Platform** — адаптеры используют `StdioMCPClient` и `HTTPMCPClient` из MCP Client, не дублируют транспортный слой
  - **60 тестов** (`tests/test_runtime_abstraction.py`) — 0 failures:
    - TestTypes (8): RuntimeConfig, RuntimeDefinition, RuntimeResult, RuntimeCapability, RuntimeSession, RuntimeHealth
    - TestRuntimeAdapter + TestStdioMCPAdapter + TestHTTPMCPAdapter (10): lifecycle, connect/disconnect, ping, health, generate
    - TestAdapterRegistry (5): register, get, create, list_types
    - TestRuntimeRegistry (12): register, unregister, list, discover, set_active, save/load, connect/disconnect, status
    - TestRuntimeCapabilityRegistry (8): list_capabilities, get_runtime_for_capability, score, set_score, preference, fallback
    - TestFreebuffAdapter + TestClaudeCodeAdapter (8): name, capabilities, find binary/falback
    - TestIntegration (3): registry+adapter, multi-runtime selection, save/load cycle

### Проверка
- 60 тестов Runtime Abstraction Layer — **0 failures** (65s)
- 1123 общих тестов — **0 failures** (254s)
- Code review: 3 замечания исправлены (unused imports, private attr access, missing import)

---

## [4.8.0***REMOVED*** — 2026-07-29

### Добавлено
- **Bootstrap Engine — интеграция с MCP Server:**
  - `scripts/mcp_server.py` — добавлен `_get_bootstrap_engine()` lazy accessor (паттерн как у BridgeLayer)
  - 3 новых MCP инструмента (секция 7: Bootstrap Engine tools):
    - `bootstrap_check` — проверка окружения (OS, Python, Node, Git, Disk, RAM, пакеты). Параметр: `quick: bool`
    - `bootstrap_run` — полный bootstrap: check → load profile → install → diagnose → report. Параметр: `profile: str` (minimal по умолчанию)
    - `bootstrap_status` — статус bootstrap: был ли запущен, профиль, ошибки, предупреждения
  - EventBus публикация: `bootstrap.checked`, `bootstrap.ran`
  - 12 тестов (`tests/test_mcp_server.py::TestBootstrapTools`) — 0 failures:
    - check: full, quick, engine unavailable
    - run: minimal, default, developer, unknown profile (graceful fallback)
    - status: never run, after run
    - tools: in list, schemas, RPC dispatch

### Проверка
- 101 тест MCP Server — **0 failures** (26s)
- 1063 общих теста — **0 failures** (206s)
- Code review: 3 замечания исправлены (MagicMock serialization, private API access, profile fallback test)

---

## [4.7.0***REMOVED*** — 2026-07-29

### Добавлено
- **Event Platform — реализация (docs/core/EVENT_PLATFORM_SPECIFICATION.md):**
  - `freebuff_plugin/event/__init__.py` — типы: EventEntry, EventQuery, ReplayResult, Timeline, Audit*, PulseEntry + EVENT_ICONS + get_event_icon
  - `freebuff_plugin/event/schema.sql` — SQLite schema: event_store таблица, FTS5, 3 триггера (INSERT/UPDATE/DELETE)
  - `freebuff_plugin/event/store.py` — EventStore: CRUD (store, get_by_id, query), FTS5 search с wildcard поддержкой, batch, миграция из event_log, агрегация, clear
  - `freebuff_plugin/event/replay.py` — EventReplay: replay (instant/realtime), rebuild (snapshot → clear → replay → snapshot с идемпотентностью)
  - `freebuff_plugin/event/timeline.py` — TimelineEngine: get_timeline, format с иконками, search, by_session/by_user
  - `freebuff_plugin/event/audit.py` — AuditEngine: log_decision/action/config_change + audit trail + форматирование для CLI
  - `freebuff_plugin/event/pulse.py` — PulseEngine: подписка на EventBus, FTS5 маркер + fallback по категориям
  - **MCP интеграция** (`freebuff_plugin/mcp_server.py`):
    - `_get_event_store()` — lazy accessor
    - 5 новых MCP инструментов: `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse`
    - Каждый инструмент возвращает форматированные JSON/текст результаты

### Исправлено
- `freebuff_plugin/event/store.py`:
  - `conn.commit()` был вне `with self._connect() as conn:` блока (вызов на закрытом соединении) — исправлено
  - `sqlite3.Row.get()` не существует на Android/Termux → `dict(row)` конвертация
  - `store_batch` использовал `conn.total_changes` (аккумулятор) вместо `SELECT changes()` — исправлено
  - `_builtin_schema()` не содержал FTS5 триггеры — добавлены
- `freebuff_plugin/event/pulse.py`:
  - PulseEngine FTS5 поиск не находил события (маркер `_pulse` в metadata, не в data_json) — добавлен `data["_pulse"***REMOVED*** = True`
  - Добавлен fallback поиск по категориям при пустом FTS5 результате

### Проверка
- 61 тест Event Platform — **0 failures** (18.05s)
- Code review: 7 замечаний исправлены (FTS5 sync, total_changes, Pulse FTS5, миграция, builtin triggers, 4 тестовых падения)

---

## [4.6.0***REMOVED*** — 2026-07-29

### Добавлено
- **Bridge Layer — Phase 6: CoWork/Companion Platform (MCP ↔ ACP):**
  - `freebuff_plugin/acp_protocol.py` — Agent Collaboration Protocol (ACP):
    - AgentRegistry: регистрация, поиск, статус (online/offline/busy), heartbeat, prune offline
    - ACPHandler: подписка на ACP события через Event Bus, обработка discover/task/result/broadcast/status
    - AgentInfo + AgentStatus + ACPTask + ACPResult — dataclasses протокола
    - Система отправки задач с ожиданием результата (send_task + wait_for_result с timeout)
    - Heartbeat loop (30s) + автоматическая саморегистрация в локальном реестре при start()
    - Фильтрация задач по target (только себе), корректная обработка неизвестных tools
  - `freebuff_plugin/mcp_client.py` — MCP Client (два транспорта):
    - MCPClientBase: единый интерфейс (connect/disconnect/list_tools/call_tool/list_resources)
    - StdioMCPClient: подпроцесс + stdin/stdout, reader thread, очередь ответов с фильтрацией stale ID
    - HTTPMCPClient: Streamable HTTP (POST/GET/DELETE), Mcp-Session-Id, handshake initialize
    - Поддержка MCP 2025-03-26 протокола: initialize, tools/list, tools/call, resources/list, resources/read, prompts/list, prompts/get, ping
  - `freebuff_plugin/bridge_layer.py` — Bridge Layer (трансляция MCP ↔ ACP):
    - BridgeLayer: центральный координатор, запускает ACP и sync loop
    - connect_mcp_stdio / connect_mcp_http — подключение внешних MCP серверов
    - Connection params сохранены в BridgeMCPServer для автоматического reconnect
    - _forward_to_mcp — перенаправление ACP задач на MCP серверы
    - _rpc_to_server — произвольные JSON-RPC запросы к подключённым серверам
    - Sync loop: ping каждые 60s, автоматический reconnect, prune offline агентов
    - Регистрация MCP инструментов как ACP capabilities (префикс mcp.{server***REMOVED***.{tool***REMOVED***)
    - BridgeMCPServer: dataclass с connection_params для надёжного reconnect
    - 60 тестов (`tests/test_bridge_layer.py`) — 0 errors
  - **Bridge Layer интегрирован в MCP Server** (`scripts/mcp_server.py`):
    - `_get_bridge_layer()` — lazy accessor, создаёт BridgeLayer с EventBus
    - 4 новых MCP инструмента: `bridge_connect` (stdio/HTTP), `bridge_list`, `bridge_disconnect`, `bridge_rpc`
    - События EventBus: `bridge.connected`, `bridge.disconnected`, `bridge.rpc`

### Проверка
- 149 тестов MCP Server + Bridge Layer — **0 failures** (89 + 60)
- Code review: 4 итерации (name bug, connection_params, active_request_ids, sync loop logging, event publishing)
- Все 4 инструмента (bridge_connect, bridge_list, bridge_disconnect, bridge_rpc) зарегистрированы в MCP tools/list

---

## [4.5.0***REMOVED*** — 2026-07-29

### Добавлено
- **Scenario Engine** — `freebuff_plugin/scenario_engine.py`:
  - Сценарный движок с YAML-парсингом (YAML front matter + markdown тело)
  - `Scenario` dataclass: slug, title, description, category, complexity, tags, prompt, variables, template
  - `ScenarioEngine`: загрузка из `scenarios/`, list/search/get/apply, reload, stripping YAML
  - 83 теста (`tests/test_scenario_engine.py`) — 0 errors
- **11 готовых сценариев** в `freebuff_plugin/scenarios/`:
  - `freelance_parser.md` — Парсер сайта (категория: freelancing, сложность: средняя)
  - `freelance_tg_bot.md` — Telegram бот для заказов (категория: freelancing)
  - `agent_setup.md` — Настройка AI-агента (категория: ai)
  - `task_framework.md` — Фреймворк задач (категория: tool)
  - `freelance_tg_parser.md` — Парсер Telegram (категория: freelancing)
  - `freelance_mail_collector.md` — Сборщик почты (категория: freelancing)
  - `freelance_seo_auditor.md` — SEO аудитор (категория: freelancing, сложность: высокая)
  - `freelance_report_generator.md` — Генератор отчётов (категория: freelancing)
  - +3 существующих сценария из plugin
- **Telegram Bot для сценариев** — `freebuff_plugin/tgbot.py`:
  - `/scenarios list` — список сценариев с фильтрацией по категории
  - `/scenarios apply <slug>` — применить сценарий с вводом переменных
  - `/scenarios search <query>` — поиск по сценариям
  - Inline keyboard навигация: категории → сценарии → детали → применить
  - State management с TTL (600с) и лимитом 1000 записей
  - `_send_prompt_result` — статический метод (устраняет дублирование)
  - Text handler с поддержкой JSON, key=value, "готово"
  - 44 теста (`tests/test_tgbot.py`) — 0 errors
- **Стратегические документы:**
  - `IDEAS.md` — реестр архитектурных идей (12 идей со статусами, категориями, приоритетами)
    - Идеи: Bridge Layer, ACP, Presence, RAG 2.0, Session Manager, Workflow Engine, Live Collaboration, IDEAS v2, Summarization, MCP Client, Async Workers, Auto-Docs
  - `docs/vision/archive/VISION_2.0.md` — стратегическое видение Buffy как Companion Engine
    - Философия: «Buffy — не конкурент Claude/Cursor/OpenClaw, а универсальная надстройка»
    - 6 архитектурных принципов (LLM Sparingly, Event Bus, Live Collaboration, Presence, Project Pulse, Collaboration Roles)
    - Матрица анализа 12 концепций (ценность/риски/сложность/альтернативы)
    - Поэтапный план реализации (3 этапа, оценённые в часах)
  - `docs/vision/ROADMAP.md` — обновлён до v2.0.0:
    - Добавлена Phase 6: CoWork / Companion Platform
    - Phase 3 отмечена как ✅ ЗАВЕРШЕНА (с детальным содержанием)
    - Phase 4 расширена (Telegram Bot + Scenario Engine, ~85%)
    - Phase 6: foundation (Event Bus, ContextManager v3, Memory/Knowledge/Graph Engines, Plugin API, MCP, Scenario Engine, TG Bot, Intent Router, IDEAS, VISION 2.0)
  - `BUFFY.md` — обновлён раздел видения: добавлена Phase 6, IDEAS.md, VISION_2.0.md в документацию
- **Архитектурный аудит** — проведён полный аудит текущей архитектуры:
  - Проанализированы все модули: ContextManager, MemoryEngine, KnowledgeEngine, GraphIndex, EventBus, Orchestrator, ModelGateway, ToolRuntime, PluginAPI, MCPServer, ScenarioEngine, TelegramBot
  - Выявлены пробелы: отсутствие Bridge Layer, ACP, Presence, Live Collaboration
  - Создана карта архитектуры с фазами развития

### Исправлено
- `docs/vision/ROADMAP.md` — восстановлено детальное содержание Phase 3 (потеряно при обновлении), исправлен дубликат строки в конце

### Проверка
- Все тесты проходят — **0 failures** (Scenario Engine: 83, Telegram Bot: 44, существующие: 649+)
- Scenario Engine: 83 теста (list, search, apply, yaml_parsing, Scenario class, CLI, edge cases)
- Telegram Bot: 44 теста (handlers, callbacks, state management, "готово" flow)
- Все 11 сценариев загружаются корректно
- Code review пройден (3 итерации фиксов: state leak, code duplication, unused imports)

---

## [4.4.0***REMOVED*** — 2026-07-29

### Добавлено
- **OOM Protection System (защита от Signal 9/SIGKILL):**
  - `scripts/oom_protect.sh` — скрипт защиты от OOM: проверяет MemAvailable, убивает старые freebuff процессы при пороге <512 MB, чистит зависшие tmux сессии и PID-файлы плагина
  - Режимы: `--status` (диагностика), `--force` (принудительная очистка), `--check` (автоматический режим с условной очисткой)
  - Защита от самозацикливания: не убивает себя, python-процессы, tmux, bash-обёртки и proot
- **Интеграция OOM Protection в freebuff plugin:**
  - `freebuff_plugin/wrapper.py` — `_run_oom_protection()` вызывается перед `launch()` и `synchronous_oneshot()`; ошибки логируются, а не глотаются молча
  - `~/.local/bin/freebuff` — v4 wrapper: добавлена Фаза 0 (OOM Protection) перед стартом сессии; добавлен `set -u` с безопасными дефолтами для переменных
  - При каждом запуске `freebuff` (через CLI или Python wrapper) сначала запускается OOM protection, убивающий старые процессы

### Исправлено
- `freebuff_plugin/monitor.sh` — починен `PREFIX: unbound variable`: `${PREFIX***REMOVED***` заменён на `${PREFIX:-/data/data/com.termux/files/usr***REMOVED***`
- `scripts/oom_protect.sh` — удалён дублирующий `pgrep` блок в `kill_old_freebuff()` (оставлен только один проход по `ps aux`)
- `scripts/oom_protect.sh` — `return 1` заменён на `exit 1` (скрипт не sourced)
- `scripts/oom_protect.sh` — починен pipeline subshell bug в `clean_tmux_sessions()` (переменная `cleaned` теперь в главном shell)
- `scripts/oom_protect.sh` — `${PREFIX***REMOVED***` подстрахован дефолтным значением

### Проверка
- 649/649 pytest тестов — **0 failures** (114s)
- Self-check (bootstrap): все проверки пройдены
- OOM protection `--status` и `--check` — работают корректно
- Wrapper syntax: `bash -n` проходит

---

## [4.3.0***REMOVED*** — 2026-07-28

### Добавлено
- **Интеграция с freebuff CLI (out-of-the-box):**
  - `.freebuff/config.json` — метаданные проекта, корневые файлы, preferred commands
  - `.freebuff/AGENTS.md` — инструкции для свободного/Codebuff CLI
  - `AGENTS.md` — корневой канонический протокол агента
  - `.cursorrules` — fallback для Cursor-совместимости
  - `CLAUDE.md` — fallback для Claude-совместимости
  - `CODY.md` — fallback для Cody-совместимости
  - `BUFFY.md` — раздел «Работа через Freebuff CLI» с конфигурацией и стартовой последовательностью
  - `README.md` — секция про `freebuff` CLI
  - `docs/ops/AGENTS.md` — ссылка на корневой `AGENTS.md`
- **Telegram bot frontend для freebuff:**
  - `scripts/telegram_bot.py` — Bot API бот с ContextManager-сессиями, ModelGateway LLM-ответами, .env загрузкой, typing indicator, error handling
  - `tests/test_telegram_bot.py` — 6 unit-тестов (session ID, создание, сообщения, статус, fallback, новая сессия)
  - `scripts/start_telegram_bot.sh` — стартовый скрипт с .env sourcing
  - `requirements.txt` — добавлен `python-telegram-bot>=20.0,<21.0`

### Изменено
- `scripts/drift_check.py` — убраны runtime/кэш-директории из скана (`context/`, `data/`, `logs/` и др.); хрупкий regex заменён на line-based парсер (корректно обрабатывает пары ``` ``` и tree-диаграммы с вложенностью)

---

## [4.2.6***REMOVED*** — 2026-07-28

### Добавлено
- **Self-check triggers (promt10):**
  - `scripts/bootstrap.py` — startup self-check (Trigger 1): проверяет `BUFFY.md`, фильтрует тестовые/демо-конспекты, проверяет актуальность `TASK.md`.
  - `scripts/drift_check.py` — daily drift-check (Trigger 2): сравнивает статус-таблицы `BUFFY_PROJECT.md` с реальными файлами, индекс `seed_knowledge` с фактическими документами, структуру директорий с `BUFFY.md`/`docs/core/RULES.md`. Пишет `docs/audits/DRIFT_REPORT.md`, rate-limit — раз в день.
  - `scripts/cron_conspect.sh` — запускает `drift_check.py` каждые 30 минут (внутренний rate-limit once/day).
  - `tests/test_bootstrap.py` — 5 unit-тестов для самопроверки при старте.
  - `tests/test_drift_check.py` — 9 unit-тестов для drift-check.

### Исправлено
- `scripts/bootstrap.py` — `***REMOVED***` перенесён наверх; самопроверка обёрнута в `try/except`, чтобы не ломать старт.

---

## [4.2.5***REMOVED*** — 2026-07-28

### Изменено
- **scripts/auto_conspect.py** — демо-код вынесен в `scripts/demo_auto_conspect.py`; добавлены CLI-флаги `--demo` и `session_id`.
- **scripts/cron_conspect.sh** — убран непреднамеренный запуск демо-режима.
- **freebuff_cli.py** — добавлены команды `task start` и `task archive` для создания/архивации `TASK.md`.
- **tests/test_mcp_server.py** — исправлены импорты `typing.Optional` и `typing.Tuple`.
- **tests/test_freebuff.py** и **tests/test_auto_conspect.py** — добавлены тесты CLI `task` и `auto_conspect`.
- **scripts/session_utils.py** — вынесен shared helper `resolve_session_id`; убрано дублирование между `auto_conspect.py` и `freebuff_cli.py`.
- **tests/conftest.py** и **tests/test_session_utils.py** — добавлена shared `context_manager` fixture и 5 тестов для `resolve_session_id`.
- **tests/test_cron_conspect.py** — добавлен unit-тест, проверяющий, что `scripts/cron_conspect.sh` не запускает `auto_conspect` в demo-режиме.
- **projects/tg_terminal_messenger**:
  - `src/ui/app.py`: горячие клавиши переназначены с `Ctrl+S/Ctrl+Q` на `Ctrl+F/Ctrl+X` (терминальный XON/XOFF); отправка сообщений починена через `@on(Input.Submitted)` + `event.stop()` + `dialog.input_entity`; автоматический фокус на поле ввода.
  - `src/main.py`: добавлена точка входа.
  - `README.md`: актуализирована таблица горячих клавиш.
  - Удалён дублирующий каталог `/storage/emulated/0/PROJECTS/workstation/tg_terminal_messenger`; спецификации скопированы в `docs/original/`.
  - Проведён аудит против `tg_toolkit` (сравнительный анализ: multi-account, quick reply, bulk, export, profile).

---

## [4.2.3***REMOVED*** — 2026-07-28

### Изменено
- **scripts/seed_knowledge.py** — документы теперь авто-обнаруживаются из `docs/**/*.md` вместо жёстко зашитого списка. Добавлены исключения: `docs/AUDIT_*.md` и `docs/ops/TASK_TEMPLATE.md`.
- **tests/test_seed_knowledge.py** — добавлены тесты для `_collect_doc_sources` и исключений.
- **docs/core/RULES.md** — убраны ссылки на пустые `docs/architecture/` и `docs/decisions/`.
- **BUFFY_PROJECT.md** — актуализированы статусы: Knowledge Engine, Event Bus, Orchestrator отмечены как MVP/Каркас.

### Удалено
- **docs/architecture/** и **docs/decisions/** — пустые директории-призраки.

---

## [4.2.2***REMOVED*** — 2026-07-28

### Изменено
- **docs/vision/archive/ARCHITECTURE.md** — добавлен раздел "Автоматизация документирования" со ссылкой на `docs/core/RULES.md`.
- **docs/projects_meta/WORKERS.md** — добавлен раздел "Авто-документирование", ссылка на `buffy_autodoc.py` и pre-commit hook; чек-лист добавления нового worker дополнен пунктом про `CHANGELOG.md`.

---

## [4.2.1***REMOVED*** — 2026-07-28

### Добавлено
- **docs/ops/TROUBLESHOOTING.md** — документ с известными проблемами и решениями для:
  - Lightpanda worker (glibc/ARM64, CLI-флаги, пути к PandaScript, OOM)
  - Agent Context Bridge (интеграция, сессии, обрезка JSON)
  - pre-commit hook (обход блокировки)

---

## [4.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **pre-commit hook для авто-документации**:
  - `scripts/pre-commit` — tracked версия git pre-commit hook
  - `scripts/install_hooks.sh` — установка hook в `.git/hooks/pre-commit`
  - `scripts/buffy_autodoc.py --strict` — строгий режим с exit code 1
  - `severity=block/warn` у триггеров: `CHANGELOG.md` и `TASK.md` — блокеры, остальные — warning
- **docs/core/RULES.md** — добавлен раздел про pre-commit hook и его установку

### Проверка
- `mypy scripts/buffy_autodoc.py` — 0 errors
- `pytest tests/test_lightpanda_worker.py tests/test_agent_context_bridge.py` — 13/13 passed

---

## [4.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Lightpanda integration v1.0.0:**
  - `scripts/install_lightpanda.sh` — установка Lightpanda в Termux + proot-distro Ubuntu ARM64
  - `src/workers/lightpanda_worker.py` — Python-воркер: `execute_agent_task`, `run_script`, `dump_url`, `serve_cdp`, `stop_cdp`
  - `docs/projects_meta/LIGHTPANDA_INTEGRATION.md` — полный гайд по установке и использованию
  - `docs/projects_meta/WORKERS.md` — обзор паттерна workers
  - `docs/vision/archive/ARCHITECTURE.md` — архитектурная схема с Lightpanda
  - `tests/test_lightpanda_worker.py` — 8 unit-тестов

### Проверка
- 8/8 тестов `test_lightpanda_worker.py` — **0 failures**
- `mypy src/workers/lightpanda_worker.py tests/test_lightpanda_worker.py` — **0 errors**

---

## [4.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Интеграция ContextManager с termux-ai-agent v4.0:**
  - `scripts/agent_context_bridge.py` — мост для сохранения диалогов локального агента в freebuff ContextManager
  - `termux-ai-agent/main.py` — автоматическое логирование user/assistant/system сообщений, авточекпоинты каждые 10 сообщений, CLI `--freebuff-conspect`
  - Unit-тесты `tests/test_agent_context_bridge.py` (5 тестов)
- **BUFFY.md / BUFFY_PROJECT.md:** единый источник правил и архитектуры Buffy 2.0

### Проверка
- 5/5 тестов `test_agent_context_bridge.py` — **0 failures**
- `mypy scripts/agent_context_bridge.py tests/test_agent_context_bridge.py` — **0 errors**
- `mypy termux-ai-agent/main.py` — **0 errors**

---

## [2.9.0***REMOVED*** — 2026-07-28

### Добавлено
- **Параллельное выполнение шагов Orchestrator'а** (`scripts/orchestrator.py`):
  - `ThreadPoolExecutor(max_workers=N)` — независимые шаги запускаются параллельно
  - `concurrent.futures.wait(FIRST_COMPLETED)` — динамическое планирование DAG
  - `_handle_blocked_steps()` — пропуск шагов с проваленными зависимостями (SKIPPED)
  - `_publish_workflow_progress()` — событие `workflow.progress` с completed/total counts
  - `_execute_step()` — полностью thread-safe (lock на status update, context update)
  - `max_workers` параметр (default 4, 1 = последовательно)
- **EventBus интеграция расширена:**
  - `step.retrying` — событие при повторной попытке (retry_count, max_retries, error)
  - `workflow.progress` — прогресс выполнения (completed_steps / total_steps)
- **14 новых тестов** (`tests/test_orchestrator.py`):
  - Parallel: max_workers param/default, independent steps, chain deps, diamond DAG
  - EventBus: step.retrying, workflow.progress, step.completed, step.failed, lifecycle
  - Thread safety: context accumulation, blocked steps skip
- **Docstring обновлён** — step.retrying и workflow.progress в списке EventBus событий

### Проверка
- 51 тест orchestrator — **0 errors** (37 старых + 14 новых)
- 586 общих тестов — **0 failures**
- Code review пройден

---

## [2.8.0***REMOVED*** — 2026-07-28

### Исправлено (Critical Security)
- **Удалён `exec(code)` из orchestrator.py** — `_run_python` теперь использует
  `subprocess.run([sys.executable, "-c", code***REMOVED***)` вместо `exec()` с полным `__builtins__`.
  Код выполняется в изолированном subprocess, не может получить доступ к памяти родительского процесса.
- **Устранён `shell=True` во всех subprocess вызовах** (5 мест):
  - `orchestrator.py._run_shell`: `shell=True` → `["sh", "-c", command***REMOVED***`
  - `orchestrator.py._run_git`: `shell=True` + f-string → `["git"***REMOVED*** + shlex.split(command)`
  - `tool_runtime.py.GitTool.execute`: `shell=True` + f-string → `["git", command***REMOVED*** + shlex.split(args)`
  - `tool_runtime.py.ShellTool.execute`: `shell=True` → `["sh", "-c", command***REMOVED***`
- **Удалён дубликат `_run_shell`** в orchestrator.py (copy-paste bug)
- **Исправлен `NameError: full_cmd`** в `GitTool.execute` metadata
- **Добавлен `import shlex`** в orchestrator.py и tool_runtime.py
- **Очищен git history от API ключей** — `git filter-branch` переписал 14 коммитов,
  `.keys/` полностью удалён из всех коммитов
- **`.keys/` добавлен в `.gitignore`** — защита от случайного коммита

### Проверка
- 572 теста — **0 failures**
- Code review пройден

---

## [2.7.0***REMOVED*** — 2026-07-28

### Добавлено
- **FastAPI обёртка для MCP Server** (`scripts/mcp_fastapi.py`) — Streamable HTTP через uvicorn:
  - Async SSE streaming через `asyncio.Queue` (не `queue.Queue`)
  - `_dispatch()` — обёртка через `asyncio.to_thread()` для не-blocking вызова `BuffyMcpServer.dispatch()`
  - McpAsyncSession (@dataclass) + McpAsyncSessionManager (asyncio.Lock)
  - Origin validation через `urlparse().hostname` (DNS rebinding protection)
  - CLI: `--host`, `--port`, `--tunnel` (Cloudflare Tunnel)
  - `_start_tunnel()` — запуск `cloudflared tunnel --url` в subprocess, парсинг stderr для URL
  - `_print_tunnel_config()` — вывод конфига для Claude Desktop / Gemini
  - Health check `GET /` → `{status, server, protocol, endpoint, transport***REMOVED***`
- **Cloudflare Tunnel интеграция:**
  - `python scripts/mcp_fastapi.py --tunnel` — автоматический запуск cloudflared
  - Публичный HTTPS URL: `https://xxx.trycloudflare.com/mcp`
  - Конфиг для Claude Desktop выводится в stderr при старте
  - Cleanup при Ctrl+C: `tunnel_proc.terminate()`
- **CLI интеграция в mcp_server.py:**
  - `--fastapi` флаг — делегирует запуск в `mcp_fastapi.main()`
  - `--tunnel` флаг — передаётся в `mcp_fastapi.main()` (требует `--fastapi`)
  - Guard: `--tunnel` без `--fastapi` → exit с ошибкой
- **35 тестов FastAPI** (`tests/test_mcp_fastapi.py`):
  - uvicorn в daemon thread + `http.client` (тот же паттерн что и test_mcp_server.py)
  - `_uvicorn_server` fixture (module-scoped) — стартует uvicorn один раз на модуль
  - POST: initialize, ping, notification, tools/list, resources/list, prompts/list, tools/call, batch, errors
  - DELETE: session, unknown session, missing session-id
  - GET: missing session-id, unknown session, SSE content-type (raw socket)
  - Origin validation: evil.com (403), localhost (200), no origin (200), localhost.evil.com (403)
  - Async session manager: 7 тестов через `asyncio.run()` (без pytest-asyncio dependency)

---

## [2.6.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streamable HTTP транспорт для MCP Server** — реализован согласно спецификации
  MCP 2025-03-26 (замена устаревшего HTTP+SSE транспорта):
  - `McpSession` (@dataclass) — session с notification_queue (Queue) для SSE
  - `McpSessionManager` — thread-safe менеджер сессий (Lock, uuid4, create/get/delete/push)
  - `McpHttpServer(ThreadingHTTPServer)` — daemon_threads=True для clean shutdown
  - `McpHTTPRequestHandler(BaseHTTPRequestHandler)` — single endpoint `/mcp`:
    - **POST**: JSON-RPC запросы → `application/json` или `202 Accepted` для notifications
    - **GET**: SSE stream (`text/event-stream`) с 30s heartbeat для server-to-client notifications
    - **DELETE**: termination session → `204 No Content` (без Content-Length per RFC 7230)
    - `Mcp-Session-Id` header — генерируется при `initialize`, требуется для GET/DELETE
    - `Mcp-Protocol-Version` header — во всех ответах
    - `_validate_origin()` — защита от DNS rebinding (urlparse hostname check)
    - Non-initialize POST с невалидным `Mcp-Session-Id` → 404
    - HTTP/1.1 protocol_version для keep-alive/SSE
  - CLI: `--http`, `--host` (default 127.0.0.1), `--port` (default 8765)
  - `BuffyMcpServer.run_http()` — запуск ThreadingHTTPServer
- **Обновление протокола:** `PROTOCOL_VERSION` 2024-11-05 → 2025-03-26
- **36 новых тестов** (`tests/test_mcp_server.py`):
  - `TestSessionManager` — 10 тестов (create, get, delete, push_notification, thread safety, uniqueness)
  - `TestHttpTransport` — 26 тестов с реальными HTTP запросами (http.client + raw socket для SSE):
    - POST: initialize, ping, tools/list, resources/list, prompts/list, tools/call, shutdown, batch,
      notification (202), unknown method, invalid JSON, wrong path, invalid origin (403),
      localhost origin, no origin, invalid session-id (404)
    - GET: without session-id (400), unknown session (404), wrong path (404),
      SSE stream с notification (raw socket test)
    - DELETE: terminates session (204), unknown session (404), without session-id (400),
      no Content-Length header (RFC 7230)
    - Mcp-Protocol-Version header в всех ответах

### Изменено
- `docs/vision/ROADMAP.md`: Phase 4 обновлена — MCP Streamable HTTP добавлен (65% → 70%)
- `docs/decisions/DECISIONS.md`: ADR-003 — Streamable HTTP transport (pure Python ThreadingHTTPServer)

### Проверка
- 89 тестов mcp_server — **0 errors** (53 stdio + 10 session manager + 27 HTTP)
- Code review: 4 итерации, все issues исправлены

### Исправления по результатам code review (4 итерации)
1. `204 No Content` — убран `Content-Length: 0` (RFC 7230 §3.3.2)
2. Origin validation — `startswith()` → `urlparse().hostname` (защита от `localhost.evil.com`)
3. Mcp-Session-Id validation — non-initialize POST с невалидным session → 404
4. McpSession → `@dataclass` (консистентность с McpTool/McpResource/McpPrompt)
5. SSE stream test — переписан на raw socket (http.client блокировал на SSE без Content-Length)
6. Session TTL note — задокументировано отсутствие automatic cleanup

---

## [2.5.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streaming для Model Gateway** — реализован real-time streaming для всех 3 провайдеров:
  - `OpenAICompatibleProvider.generate_stream()` — SSE format (`data: {json***REMOVED***`, `[DONE***REMOVED***` terminator,
    `delta.content` extraction). DeepSeek, OpenRouter, SambaNova, DashScope.
  - `GeminiProvider.generate_stream()` — `streamGenerateContent` endpoint с `alt=sse` параметром,
    `candidates[0***REMOVED***.content.parts[0***REMOVED***.text` extraction.
  - `OllamaProvider.generate_stream()` — newline-delimited JSON (`stream: true`),
    `message.content` extraction, `done` flag + usage в финальном chunk.
  - `ModelGateway.generate_stream()` — fallback между провайдерами при ошибке стрима
  - `_publish_stream_event()` — EventBus интеграция (`model.called` / `model.fallback` с `streaming=True`)
  - CLI: `generate-stream` команда с `--timeout` флагом
- **Рефакторинг провайдеров:**
  - `_build_body()` method extracted в OpenAICompatibleProvider, GeminiProvider, OllamaProvider
  - `_convert_messages()` method extracted в GeminiProvider
  - Устранено дублирование кода между `generate()` и `generate_stream()`
- **9 новых тестов streaming** (`tests/test_model_gateway.py`):
  - OpenAI SSE format parsing (content + [DONE***REMOVED***)
  - Gemini SSE format parsing (streamGenerateContent)
  - Ollama newline JSON parsing (stream: true, done flag, usage)
  - BaseProvider fallback streaming (без реального стриминга)
  - ModelGateway.generate_stream() с моком провайдера
  - Error handling (no model raises ValueError)
  - Edge cases: empty lines, invalid JSON skipping
  - StreamChunk with usage stats

### Проверка
- 36 тестов model_gateway — **0 errors** (включая 9 streaming тестов)

---

## [2.4.0***REMOVED*** — 2026-07-28

### Добавлено
- **MCP Server** (`scripts/mcp_server.py`) — Model Context Protocol server на чистом Python:
  - JSON-RPC 2.0 over stdio (без внешних SDK, `mcp` пакет не установлен на Termux)
  - **12 tools:** git, file, shell, sqlite, http (из ToolRegistry) + knowledge_search,
    memory_store, memory_retrieve, memory_list, session_status, context_resume, plugins_list
  - **9 resources:** buffy://manifest, buffy://roadmap, buffy://spec, buffy://changelog,
    buffy://task, buffy://inventory, buffy://decisions, buffy://knowledge, buffy://memory
  - **3 prompts:** context_resume, knowledge_search, task_start
  - Protocol version: 2024-11-05
  - Lazy loading компонентов (ToolRegistry, KnowledgeEngine, MemoryEngine, ContextManager)
  - EventBus интеграция (mcp.server.initialized, mcp.tool.called, mcp.knowledge.searched)
  - Workspace-aware: ToolRegistry использует workspace сервера, не хардкод
  - CLI: --status, --tools, --resources, --prompts, --call, --read, --async-mode
  - Интеграция с Claude / Gemini / OpenClaw через claude_desktop_config.json
- **Тесты MCP Server** (`tests/test_mcp_server.py`) — 51 тест, 0 errors:
  - JSON-RPC helpers (response, error, notification)
  - Initialize handshake (protocol version, capabilities, server info)
  - Tools: list, call (knowledge_search, memory CRUD, session_status, context_resume)
  - Resources: list, read (manifest, knowledge overview, memory overview)
  - Prompts: list, get (context_resume, task_start)
  - Error handling (unknown method, invalid params, notifications)
  - Batch requests, server status, dataclasses, ToolRegistry integration

### Изменено
- `docs/vision/ROADMAP.md`: Phase 4 обновлена — MCP Server реализован (55% → 65%)

---

## [2.3.0***REMOVED*** — 2026-07-28

### Исправлено
- **Groq-валидатор в KeyPool:** Cloudflare на стороне Groq блокировал дефолтный
  `User-Agent: Python-urllib/3.x` (HTTP 403 / error 1010). Добавлен
  `hdrs.setdefault("User-Agent", "KeyPool/1.0")` в `validate_provider()`.
  Результат: Groq 0/6 → **6/6 валидных ключей**.
  Файл: `.keys/keypool.py`

### Изменено (4 проблемы системы)
- **Проблема 1 — StreamBridge интеграция:** Сообщения Buffy (user + assistant)
  теперь логируются в стрим-сессию через `buffy_stream_logger.py`. Активная
  сессия: `Buffy_chat_2026-07-28_192442`. За эту сессию залогировано 7+ сообщений.
- **Проблема 2 — Knowledge Engine наполнен:** `seed_knowledge.py --force`
  обновил 19 записей в MemoryLevel.KNOWLEDGE. FTS5 индекс: 27 документов.
  Включает: README, BUFFY.md, SPEC.md, ROADMAP, DECISIONS, AUDIT,
  ARCHITECTURE_REVIEW, SYSTEM_INVENTORY + 3 best-practice карточки.
- **Проблема 3 — EventBus активирован:** events.db была пуста (0 событий).
  Опубликовано 17 типов событий (system.startup, session.created, task.*,
  step.*, checkpoint.created, knowledge.*, agent.connected, model.*,
  tool.executed, plugin.enabled). Всего 55 событий, 3 активных подписчика.
- **Проблема 4 — Git инициализирован:** Настроен `user.name=Buffy`,
  `user.email=buffy@freebuff.local`. Первый коммит: 331 файл
  (feat: Freebuff/Buffy Project 2.0 — Agentic Platform & Knowledge OS).

### Проверка
- 439 тестов — **0 errors** (65.83 сек)
- Code review пройден

---

## [2.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **Авто-индексация Knowledge Engine при сохранении в Memory Engine:**
  - `scripts/event_subscribers.py`: `auto_index_subscriber` получает `content` и `workspace_root` из события `memory.stored`
  - `scripts/memory_engine.py`: `MemoryEngine` автоматически подключается к дефолтному `EventBus` внутри проектного workspace; событие содержит полный `content` и `workspace_root`
  - `scripts/event_bus.py`: `get_default_event_bus()` — ленивая инициализация EventBus + подписчики
  - `scripts/bootstrap.py`: инициализация дефолтного EventBus при старте сессии
- **Наполнение Knowledge Memory:**
  - `scripts/seed_knowledge.py`: сохраняет ключевые документы проекта (`README.md`, `BUFFY.md`, `SPEC.md`, `docs/*.md` и др.) и best-practice карточки в `MemoryLevel.KNOWLEDGE`
  - Автоматический `rebuild_index()` после заполнения
- **Тесты:**
  - `tests/test_event_subscribers.py`: 4 теста на авто-индексацию и `checkpoint_logger`
  - `tests/test_seed_knowledge.py`: 3 теста на `seed_knowledge.py`

### Изменено
- `docs/vision/ROADMAP.md`: Phase 2 отмечена как завершённая (100%)

## [2.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Система стриминга контекста v2.0:**
  - `scripts/stream_bridge.py` — мост для интеграции Buffy с stream_session
  - `scripts/context_manager.py`: CONTEXT_FULL триггер (порог 28K токенов)
  - `scripts/context_manager.py`: `_estimate_tokens()` — точная эвристика токенов
  - `scripts/context_manager.py`: `prune_abandoned()`, `auto_abandon_stale()` — GC
  - `scripts/context_manager.py`: `get_context_status()` — мониторинг контекста
  - `scripts/context_manager.py`: `SCHEMA_VERSION = 2` + система миграций
  - `scripts/stream_session.py`: `BackgroundWriter` — асинхронная запись в файлы
  - `scripts/stream_session.py`: адаптивный чекпоинт-интервал (20→50)
  - `scripts/stream_session.py`: `prune_streams()`, `prune_all()` — GC
  - `scripts/stream_session.py`: in-memory кэш счётчика сообщений
  - `scripts/bootstrap.py`: интеграция StreamBridge при старте сессии
- **Документация:**
  - `docs/ops/TASK_TEMPLATE.md` — шаблон TASK.md для новых задач
  - `TASK.md` — файл текущей задачи (стриминг контекста v2.0)
  - `CHANGELOG.md` — этот файл

### Изменено
- `scripts/context_manager.py`: `add_message()` теперь принимает `token_count: int | None`
- `scripts/context_manager.py`: `get_messages()` сортирует ASC (старые→новые)
- `scripts/context_manager.py`: `_get_conn()` — timeout + busy_timeout
- `scripts/stream_session.py`: `log_message()` пишет в файлы асинхронно
- `docs/core/RULES.md`: добавлены TASK.md и CHANGELOG.md в обязательные документы

### Исправлено
- `scripts/context_manager.py`: удалены неиспользуемые импорты `re`, `time`

---

## [2.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Auto-Rollup при CONTEXT_FULL:**
  - `scripts/context_manager.py`: `_save_context_rollup()` — генерирует сжатый конспект при превышении порога токенов
  - Сохраняется в `context/context_full_rollup.md` для инжекта в новый контекст
  - Возвращается `rollup_path` в результате `add_message()` / `save_checkpoint()`
- `scripts/stream_session.py`: при CONTEXT_FULL чекпоинте выводится путь к rollup

---

## [1.0.0***REMOVED*** — 2026-07-27

### Добавлено
- **ContextManager:** SQLite-хранилище сессий, сообщений, чекпоинтов
- **StreamSession:** непрерывная запись в файлы (conversation.log + raw.jsonl)
- **AutoConspect:** автосуммаризация при завершении сессии
- **FreebuffBridge:** мост для termux-ai-agent
- **Bootstrap:** восстановление контекста при старте сессии
- **SystemMonitor:** мониторинг RAM, CPU, батареи
- **FreebuffCLI:** 7 команд для управления системой
- **Cron:** автоматическая суммаризация каждые 30 минут
- **Тесты:** 15 тестов для ContextManager
- **Документация:** BUFFY.md, SPEC.md, RULES.md, SESSION_GUIDE.md, DECISIONS.md
### Добавлено\n- **Session Mesh v2.0** — спецификация и промпт для внедрения
