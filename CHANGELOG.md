# Changelog

> Все значимые изменения в проекте Freebuff фиксируются в этом файле.
> Формат: [Keep a Changelog***REMOVED***(https://keepachangelog.com/en/1.1.0/),
> версионирование: [Semantic Versioning***REMOVED***(https://semver.org/spec/v2.0.0.html).

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
