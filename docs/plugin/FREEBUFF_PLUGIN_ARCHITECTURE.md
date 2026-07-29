# Freebuff Plugin — Архитектура

> **Версия:** 0.1.0  
> **Последнее обновление:** 2026-07-29  
> **Путь:** `freebuff_plugin/`

---

## 1. Обзор

**Freebuff Plugin** — это прослойка между AI-coding агентами (freebuff/Codebuff CLI, Claude Code, OpenClaw) и инфраструктурой Termux на Android.

Плагин решает три ключевые проблемы:

1. **OOM (Out Of Memory)** — Android убивает тяжёлые процессы Signal 9
2. **Контекстная память** — сохранение состояния между сессиями
3. **Маршрутизация запросов** — простые вопросы → freebuff, сложные → Codebuff

---

## 2. Принципиальная схема

```
┌─────────────────────────────────────────────────────────────────┐
│                    ВХОДНЫЕ ТОЧКИ                                 │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  ~/.local/bin/   │  │  FastAPI     │  │  MCP STDIO/SSE   │   │
│  │  freebuff (v4)   │  │  :8410       │  │  :8411           │   │
│  └────────┬─────────┘  └──────┬───────┘  └────────┬─────────┘   │
│           │                   │                    │             │
└───────────┼───────────────────┼────────────────────┼─────────────┘
            │                   │                    │
            ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ФАЗА 0: OOM PROTECTION                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  scripts/oom_protect.sh                                   │   │
│  │  ┌──────────┐  ┌───────────────┐  ┌──────────────────┐  │   │
│  │  │ Проверка │  │ Убить старые  │  │ Очистить tmux    │  │   │
│  │  │ памяти   │→│ freebuff PIDs │→│ и PID-файлы       │  │   │
│  │  └──────────┘  └───────────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ФАЗА 1: СТАРТ СЕССИИ                          │
│                                                                  │
│  freebuff_plugin/wrapper.py                                      │
│  ├─ _run_oom_protection()                                        │
│  ├─ bridge.session_start()                                       │
│  ├─ _make_agents_md() → AGENTS.md                                │
│  ├─ tmux new-session → Codebuff                                  │
│  └─ save_pid_file() + monitor.sh в фоне                         │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Bridge     │  │  Context     │  │  StreamBridge        │   │
│  │  (bridge.py)│  │  Manager     │  │  (stream_bridge.py)  │   │
│  │  → SQLite   │  │  (core)      │  │  → файлы на диске   │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
            │ (Python exits)
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  ФАЗА 2: CODEBUFF РАБОТАЕТ                       │
│                                                                  │
│  • Codebuff CLI → единственный тяжёлый процесс                   │
│  • Python процесса нет → память свободна                         │
│  • tmux сессия держит Codebuff                                   │
│  • monitor.sh ждёт завершения                                    │
└──────────────────────────────────────────────────────────────────┘
            │ (Codebuff exits)
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  ФАЗА 3: ЗАВЕРШЕНИЕ                              │
│                                                                  │
│  freebuff_plugin/monitor.sh                                      │
│  ├─ Ждёт завершения Codebuff                                     │
│  ├─ Убивает tmux сессию                                          │
│  ├─ Очищает AGENTS.md                                            │
│  └─ bridge.session_end() → конспект                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Компоненты

### 3.1 `config.py` (70 строк)

Централизованная конфигурация: пути, порты, ключевые слова для роутера.

| Переменная | Значение | Описание |
|-----------|---------|----------|
| `FREEBUFF_ROOT` | `/storage/emulated/0/PROJECTS/workstation/freebuff` | Корень проекта |
| `FREEBUFF_BINARY` | `~/.config/manicode/freebuff` | Бинарник Codebuff CLI |
| `FREEBUFF_WRAPPER` | `~/.local/bin/freebuff` | Bash-обёртка v4 |
| `MCP_PORT` | `8411` | Порт MCP сервера |
| `API_PORT` | `8410` | Порт FastAPI сервера |
| `PROOT_DISTRO` | `ubuntu` | Дистрибутив proot |
| `QWEN_MODEL_0_5B` | `~/models/qwen2.5-0.5b-instruct-q4_k_m.gguf` | Путь к Qwen GGUF |

### 3.2 `router.py` (282 строки)

**Intent Detection Router** — определяет, кому направить запрос:

| Категория | Группы | Куда |
|-----------|--------|------|
| **local** | greeting, status, simple_qa | Qwen 0.5B (freebuff) |
| **freebuff** | code, architecture, tools, investigation | Codebuff CLI |

**Алгоритм:**
1. Regex scoring по группам (длина совпадения / длина запроса)
2. Если `local_score > 0.6` и > `freebuff_score` → Qwen
3. Если `freebuff_score > 0.4` → Codebuff
4. Неуверен → Codebuff (failover)

**Пороги:**
- `LOCAL_THRESHOLD = 0.6`
- `FREEBUFF_THRESHOLD = 0.4`

### 3.3 `wrapper.py` (480 строк)

**Phase-based Wrapper** — запуск Codebuff CLI без OOM.

**Режимы:**

| Режим | Описание | Когда использовать |
|-------|----------|-------------------|
| `launch()` | Phase-based: Python → tmux → exit (рекомендуется) | Продакшн |
| `synchronous_oneshot()` | Python ждёт Codebuff (только отладка) | Отладка, тесты |

**Жизненный цикл launch():**
1. `_run_oom_protection()` — убить старые freebuff
2. `bridge.session_start()` — начать сессию в SQLite
3. `_make_agents_md()` — создать AGENTS.md с задачей
4. `tmux new-session -d -s fb_{sid***REMOVED***` — запустить Codebuff в proot
5. `save_pid_file()` — сохранить PID
6. `monitor.sh` — запустить в фоне (ждёт → отправляет промпт → завершает)
7. Python exit (память свободна)

**Утилиты:**
- `clean_tui_output()` — очистка ANSI/Terminfo escape-последовательностей
- `save/read/remove_pid_file()` — управление PID-файлами
- `list_active_pids()` — список активных сессий
- `_is_pid_alive()` — проверка процесса по PID

### 3.4 `bridge.py` (196 строк)

**Bridge** — мост между плагином и core-системой (ContextManager, StreamSession, AutoConspect).

**API:**
- `session_start(topic)` → session_id (8 символов)
- `session_end(sid, summary)` → путь к конспекту
- `session_list(status)` → список сессий
- `is_pid_alive(pid)` → bool

**Процесс-безопасность:** функции можно вызывать из разных процессов, обмениваясь session_id через файл.

**Внутренние функции:**
- `_make_sid()` — генерация короткого UUID (8 hex)
- `_find_stream_dir(sid)` — поиск стрим-директории по session_id
- `_log_json(sid, role, data)` — запись в raw.jsonl

### 3.5 `monitor.sh` (bash, v2)

**Monitor-скрипт** — завершает сессию после работы Codebuff.

**Жизненный цикл:**
1. `wait_for_prompt()` — ждёт приглашения Codebuff в tmux (до 45с)
2. Отправляет промпт через `tmux send-keys`
3. Ждёт завершения задачи (таймаут из аргумента)
4. По таймауту: убивает tmux сессию
5. Очищает AGENTS.md
6. `bridge.py end <sid>` — конспект

**Защита:** `set -u`, проверка всех аргументов `${1:-***REMOVED***`, fallback на пустые.

### 3.6 `api.py` (207+ строк)

**FastAPI REST сервер** на порту `8410`.

**Эндпоинты:**

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/status` | Статус плагина, активные задачи |
| POST | `/chat` | Чат с авто-роутингом (Qwen ↔ freebuff) |
| POST | `/session` | Управление сессиями (start / end) |
| POST | `/freebuff/run` | Запуск freebuff phase-based |
| GET | `/context` | Последний конспект |
| GET | `/tasks` | Список активных задач |
| GET | `/scenarios` | Список сценариев |
| GET | `/scenarios/search` | Поиск сценариев |
| GET | `/scenarios/{slug***REMOVED***` | Детали сценария |
| POST | `/scenarios/{slug***REMOVED***/apply` | Применить сценарий |

**Документация:** Swagger UI на `/docs`

### 3.7 `mcp_server.py` (487 строк)

**MCP сервер** — Model Context Protocol, транспорт STDIO и SSE.

**Инструменты (11 шт.):**

| Инструмент | Описание |
|-----------|----------|
| `start_session` | Начать стрим-сессию с памятью |
| `log_message` | Записать сообщение в стрим |
| `get_context` | Конспект последней сессии |
| `get_status` | Статус системы |
| `run_freebuff` | Запустить Codebuff phase-based |
| `get_task_result` | Проверить результат задачи |
| `end_session` | Завершить сессию с конспектом |
| `list_scenarios` | Список сценариев с фильтром |
| `get_scenario` | Детали одного сценария |
| `apply_scenario` | Применить сценарий |
| `search_scenarios` | Поиск сценариев |

**Ресурсы:**

| URI | Описание |
|-----|----------|
| `freebuff://session/current` | Текущая активная сессия |
| `freebuff://context/last` | Последний конспект |

**Протокол:** JSON-RPC 2.0, протокол `2024-11-05`.

### 3.8 `scenario_engine.py` (новое, 280+ строк)

**Scenario Engine** — каталог готовых промтов под типовые задачи.

**Сценарии (7 шт.):**

| Слаг | Категория | Описание |
|------|-----------|----------|
| `freelance_parser` | freelancing | Парсер сайта |
| `freelance_tg_bot` | freelancing | Telegram бот |
| `freelance_landing` | freelancing | Сайт-визитка / Лендинг |
| `freelance_api` | freelancing | API сервер |
| `freelance_integration` | freelancing | Интеграция API |
| `agent_setup` | agent | Настройка AI агента |
| `task_framework` | templates | Фреймворк промтов |

**API:**
- `list_scenarios(category, tag)` — фильтр по категории/тегу
- `get_scenario(slug)` — детали
- `apply_scenario(slug, variables)` — подстановка переменных
- `search_scenarios(query)` — полнотекстовый поиск
- `reload()` — перезагрузка с диска

**Формат сценария:**
```markdown
---
category: freelancing
complexity: средняя
description: ...
tags:
  - parser
  - scraper
---

# Сценарий: ...

## Промт для freebuff

```
готовый промт с {переменными***REMOVED***
```
```

### 3.9 `oom_protect.sh` (bash)

**OOM Protection** — защита от Signal 9.

**Режимы:**

| Флаг | Действие |
|------|----------|
| (без флага) / `--check` | Проверка+очистка (автоматический режим) |
| `--force` | Принудительно убить все freebuff |
| `--status` | Только показать статус |

**Что делает:**
1. Читает `MemAvailable` из `/proc/meminfo`
2. Если памяти < 512 MB → убивает старые freebuff
3. Если памяти < 256 MB → критическое предупреждение
4. Чистит зависшие tmux сессии (`fb_*`)
5. Чистит PID-файлы мёртвых процессов
6. Чистит tmux сессии без клиентов

**Защита:** не убивает себя, Python-процессы, tmux, bash, proot.

---

## 4. Потоки данных

### 4.1 Phase-based launch (анти-OOM)

```
Пользователь запускает freebuff "напиши парсер"
    │
    ▼
~/.local/bin/freebuff (bash v4)
    ├── OOM Protection (Фаза 0)
    │   ├── bash scripts/oom_protect.sh --check
    │   ├── убивает старые freebuff PIDs
    │   ├── чистит tmux сессии
    │   └── чистит PID-файлы
    │
    ├── Python wrapper (Фаза 1)
    │   ├── wrapper.launch(prompt)
    │   ├── _run_oom_protection()
    │   ├── bridge.session_start() → sid
    │   ├── AGENTS.md создан
    │   ├── tmux new-session → Codebuff
    │   ├── save_pid_file(sid, pid)
    │   ├── monitor.sh запущен в фоне
    │   └── Python EXIT (память freed)
    │
    ├── Codebuff работает (Фаза 2)
    │   └── Единственный тяжёлый процесс
    │
    └── monitor.sh (Фаза 3)
        ├── wait_for_prompt() → отправляет промпт
        ├── ждёт завершения Codebuff
        ├── kill_tmux()
        ├── bridge.session_end() → конспект
        └── чистит AGENTS.md, PID-файлы
```

### 4.2 Intent Routing

```
POST /chat {"message": "напиши парсер сайта"***REMOVED***
    │
    ▼
router.route("напиши парсер сайта")
    │
    ├── keyword scoring
    │   ├── local_greeting:    0.00
    │   ├── local_status:      0.00
    │   ├── local_simple_qa:   0.00
    │   ├── freebuff_code:     0.83  ← max
    │   ├── freebuff_arch:     0.00
    │   ├── freebuff_tools:    0.00
    │   └── freebuff_invest:   0.00
    │
    │   local_score  = 0.00
    │   freebuff_score = 0.83
    │
    ├── freebuff_score (0.83) > FREEBUFF_THRESHOLD (0.4) → freebuff
    │
    ▼
→ target: "freebuff", confidence: 0.83
```

### 4.3 Session Lifecycle

```
  START                         END
    │                            ▲
    │  session_start()           │ session_end()
    ▼                            │
┌──────────────────────────────────────────────┐
│               СЕССИЯ                          │
│                                               │
│  SQLite: sessions table                       │
│  ├─ session_id (UUID)                         │
│  ├─ status: active / completed / abandoned    │
│  ├─ project, topic, message_count             │
│  ├─ token_estimate                            │
│  └─ metadata (JSON)                           │
│                                               │
│  Stream: STREAMS_DIR/{timestamp***REMOVED***/             │
│  ├─ .session_id                               │
│  ├─ conversation.log                          │
│  └─ raw.jsonl                                 │
│                                               │
│  PID: /tmp/.freebuff_plugin/                  │
│  ├─ pid_{sid***REMOVED***                                 │
│  └─ tmux_{sid***REMOVED***                                │
└──────────────────────────────────────────────┘
    │
    │  auto_conspect() → конспект в
    ▼  context/summaries/conspect_{topic***REMOVED***_{date***REMOVED***.md
```

---

## 5. Структура файлов

```
freebuff_plugin/
├── __init__.py              # пустой
├── config.py                # конфигурация (пути, порты, ключевые слова)
├── wrapper.py               # phase-based launch + OOM protection
├── bridge.py                # мост с core-системой
├── monitor.sh               # bash-скрипт завершения сессии (v2)
├── router.py                # Intent Detection + Qwen 0.5B
├── api.py                   # FastAPI сервер (:8410)
├── mcp_server.py            # MCP сервер (STDIO/SSE, :8411)
├── scenario_engine.py       # Scenario Engine (каталог промтов)
├── README.md                # документация
│
└── scenarios/               # сценарии-шаблоны (.md)
    ├── __init__.py
    ├── agent_setup.md        # Настройка AI агента
    ├── freelance_api.md      # API сервер
    ├── freelance_integration.md  # Интеграция API
    ├── freelance_landing.md  # Сайт-визитка
    ├── freelance_parser.md   # Парсер сайта
    ├── freelance_tg_bot.md   # Telegram бот
    └── task_framework.md     # Фреймворк промтов

scripts/
├── oom_protect.sh            # OOM Protection (скрипт)

~/.local/bin/freebuff         # bash-обёртка v4 (CLI entry point)
```

---

## 6. Зависимости

### Python (requirements.txt)
- fastapi ≥ 0.99.0
- uvicorn ≥ 0.24.0
- pydantic ≥ 2.0
- python-telegram-bot ≥ 20.0 (опционально)

### Системные (Termux)
- bash (shebang: `/data/data/com.termux/files/usr/bin/bash`)
- tmux
- proot-distro (Ubuntu)
- Codebuff CLI (`~/.config/manicode/freebuff`)
- llama.cpp (опционально, для Qwen 0.5B)
- Python 3.11+

---

## 7. Безопасность

### OOM Protection
- Автоматический запуск перед каждым `launch()`
- Не убивает: себя, Python, tmux, bash, proot
- Двойной `kill` → `kill -9` если не умер
- PID-файлы для мёртвых процессов удаляются

### Phase-based
- Python процесс существует менее 1 секунды
- Codebuff — единственный тяжёлый процесс
- tmux не даёт Android убить Codebuff как фоновый процесс

### Мониторинг
- `freebuff_cli.py status` — общий статус
- `oom_protect.sh --status` — память и процессы
- `GET /status` — плагин и задачи

---

## 8. Метрики

| Метрика | Значение |
|---------|----------|
| Весь плагин | ~2400 строк Python |
| MCP инструментов | 11 |
| REST эндпоинтов | 10 |
| Сценариев | 7 |
| PID-файлов | в `/tmp/.freebuff_plugin/` |
| Память Python (bridge/api) | < 50 MB |
| Память monitor.sh | < 1 MB |
| Тестов | 649 (весь проект), с плагином ~750+ |
