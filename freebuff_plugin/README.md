# Freebuff Plugin — Context Memory + Intent Router + MCP + Scenario Engine

**Версия:** 0.1.0 | **Строк Python:** ~2400 | **Сценариев:** 7 | **MCP инструментов:** 11

Плагин для AI-coding агентов (freebuff/Codebuff CLI, Claude Code, OpenClaw, Qwen IDE).
Работает на Termux/Android с phase-based запуском и защитой от OOM.

---

## 🚀 Быстрый старт

```bash
# Уже подключено — просто запусти:
freebuff

# REST API (отдельно):
python3 freebuff_plugin/api.py

# MCP сервер:
python3 freebuff_plugin/mcp_server.py
```

---

## 📋 Компоненты

| Компонент | Файл | Строк | Назначение |
|-----------|------|-------|------------|
| **Config** | `config.py` | 70 | Централизованная конфигурация |
| **Wrapper** | `wrapper.py` | 480 | Phase-based launch (анти-OOM) |
| **Bridge** | `bridge.py` | 196 | Мост с core-системой |
| **Monitor** | `monitor.sh` | — | Завершение сессий (bash) |
| **Router** | `router.py` | 282 | Intent Detection + Qwen 0.5B |
| **API** | `api.py` | 260 | FastAPI REST (:8410) |
| **MCP** | `mcp_server.py` | 487 | MCP STDIO/SSE (:8411) |
| **Scenario Engine** | `scenario_engine.py` | 280+ | Каталог готовых промтов |

### Дополнительно

| Компонент | Путь | Назначение |
|-----------|------|------------|
| **OOM Protection** | `scripts/oom_protect.sh` | Защита от Signal 9 |
| **CLI wrapper** | `~/.local/bin/freebuff` (v4) | Bash-обёртка с OOM + phases |

---

## 🏗 Архитектура

```
┌──────────────────────────────────────────────┐
│                ВХОДНЫЕ ТОЧКИ                  │
│  CLI freebuff │ FastAPI :8410 │ MCP :8411    │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           ФАЗА 0: OOM PROTECTION              │
│  scripts/oom_protect.sh                      │
│  • Проверка MemAvailable из /proc/meminfo    │
│  • Убивает старые freebuff процессы           │
│  • Чистит зависшие tmux сессии                │
│  • Чистит PID-файлы мёртвых процессов         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│      ФАЗА 1: СТАРТ СЕССИИ (Python)           │
│  wrapper.launch()                             │
│  • bridge.session_start() → SQLite            │
│  • AGENTS.md с задачей                        │
│  • tmux new-session → Codebuff в proot        │
│  • save_pid_file()                            │
│  • monitor.sh → background                    │
│  → Python EXIT (~0.5s)                       │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│         ФАЗА 2: CODEBUFF РАБОТАЕТ             │
│  • Единственный тяжёлый процесс               │
│  • tmux не даёт Android убить процесс         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│         ФАЗА 3: ЗАВЕРШЕНИЕ (bash)             │
│  monitor.sh                                   │
│  • Ждёт завершения Codebuff                   │
│  • Убивает tmux сессию                        │
│  • bridge.session_end() → конспект            │
│  • Очищает AGENTS.md и PID-файлы              │
└──────────────────────────────────────────────┘
```

### Intent Routing

```
Запрос → router.route()
  ├─ local_score > 0.6  → Qwen 0.5B (локально)
  ├─ freebuff_score > 0.4 → Codebuff CLI
  └─ неуверен → Codebuff (failover)
```

---

## 🔌 API Endpoints

### REST (http://127.0.0.1:8410)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/status` | Статус плагина |
| `POST` | `/chat` | Чат (авто-роутинг) |
| `POST` | `/session` | Управление сессиями |
| `POST` | `/freebuff/run` | Запустить freebuff |
| `GET` | `/context` | Последний конспект |
| `GET` | `/tasks` | Активные задачи |
| `GET` | `/scenarios` | Список сценариев |
| `GET` | `/scenarios/search` | Поиск сценариев |
| `GET` | `/scenarios/{slug***REMOVED***` | Детали сценария |
| `POST` | `/scenarios/{slug***REMOVED***/apply` | Применить сценарий |

**Swagger UI:** http://127.0.0.1:8410/docs

### MCP (STDIO / SSE :8411)

**11 инструментов:**

| Инструмент | Описание |
|-----------|----------|
| `start_session` | Начать сессию |
| `log_message` | Записать сообщение |
| `get_context` | Последний конспект |
| `get_status` | Статус системы |
| `run_freebuff` | Запустить Codebuff |
| `get_task_result` | Проверить результат |
| `end_session` | Завершить сессию |
| `list_scenarios` | Список сценариев |
| `get_scenario` | Детали сценария |
| `apply_scenario` | Применить сценарий |
| `search_scenarios` | Поиск сценариев |

**Ресурсы:** `freebuff://session/current`, `freebuff://context/last`

---

## 📚 Сценарии (7 шт.)

| Слаг | Категория | Описание |
|------|-----------|----------|
| `freelance_parser` | freelancing | Парсер сайта |
| `freelance_tg_bot` | freelancing | Telegram бот |
| `freelance_landing` | freelancing | Сайт-визитка |
| `freelance_api` | freelancing | API сервер |
| `freelance_integration` | freelancing | Интеграция API |
| `agent_setup` | agent | Настройка AI агента |
| `task_framework` | templates | Фреймворк промтов |

Каждый сценарий — `.md` файл с YAML метаданными и готовым промтом с `{переменными***REMOVED***`.

```bash
# Применить сценарий
python3 freebuff_plugin/scenario_engine.py apply freelance_parser \
  --vars '{"URL":"https://example.com","формат":"JSON"***REMOVED***'
```

---

## 🛡 OOM Protection

Запускается автоматически перед каждым `launch()`.

```bash
# Проверить статус
bash scripts/oom_protect.sh --status

# Принудительно очистить
bash scripts/oom_protect.sh --force
```

**Пороги:**
- 🟢 > 512 MB MemAvailable — всё ОК
- 🟡 < 512 MB — убивает старые freebuff
- 🔴 < 256 MB — критическое предупреждение

---

## 🔧 CLI команды

```bash
# Wrapper
python3 freebuff_plugin/wrapper.py launch "задача" --cwd .
python3 freebuff_plugin/wrapper.py status

# Bridge
python3 freebuff_plugin/bridge.py start
python3 freebuff_plugin/bridge.py end <sid>

# Scenario Engine
python3 freebuff_plugin/scenario_engine.py list
python3 freebuff_plugin/scenario_engine.py get <slug>
python3 freebuff_plugin/scenario_engine.py search <query>
python3 freebuff_plugin/scenario_engine.py apply <slug> --vars '{***REMOVED***'

# Router
python3 freebuff_plugin/router.py "запрос"
python3 freebuff_plugin/router.py -i     # интерактивный

# Servers
python3 freebuff_plugin/api.py           # REST на :8410
python3 freebuff_plugin/mcp_server.py     # MCP STDIO
python3 freebuff_plugin/mcp_server.py --transport sse --port 8411
```

---

## 🔗 Интеграция с AI-агентами

### Claude Code (`~/.claude.json`)
```json
{
  "mcpServers": {
    "freebuff-plugin": {
      "command": "python3",
      "args": [".../freebuff_plugin/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

### Qwen Code (через CLI)
Уже работает — команда `freebuff` запускает MCP сервер плагина.

### Любой HTTP-клиент
```bash
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"напиши парсер"***REMOVED***'
```

---

## 📖 Документация

| Документ | Описание |
|----------|----------|
| `docs/FREEBUFF_PLUGIN_ARCHITECTURE.md` | Полная архитектура системы |
| `docs/FREEBUFF_PLUGIN_API.md` | REST + MCP справочник |
| `docs/FREEBUFF_PLUGIN_QUICKSTART.md` | Быстрый старт |

---

## 🧪 Статус

- **Тестов в основном проекте:** 649 ✅ (из них ~100 с плагином)
- **Проверка синтаксиса:** bash + Python ✅
- **Code review:** пройден по всем компонентам ✅
