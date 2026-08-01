# SPEC.md — Техническое задание: Freebuff AI Engineering Platform

> **Фреймворк:** Kwork Arbitr v3 (blueprints_v3)
> **Версия ТЗ:** 1.0.0
> **Дата:** 2026-07-27
> **Статус:** Проектирование архитектуры

---

## 📋 Обзор проекта

**Freebuff** — AI Engineering Platform для Android (Termux), объединяющая:
- Локального AI-агента (termux-ai-agent) на Qwen 0.5B
- Облачного coding assistant (Buffy на DeepSeek v4)
- Систему управления контекстом и сессиями
- MCP Bridge для взаимодействия локального и облачного агентов
- Автосуммаризацию и восстановление контекста между сессиями

---

## 🎯 Цели и границы

### Цели (MVP)
1. ✅ Контекст-менеджер: SQLite БД сессий, чекпоинты, автосуммаризация
2. ✅ BUFFY.md: мастер-промт главного ассистента
3. ✅ Документация для агентов и пользователя
4. 🔲 Интеграция ContextManager с termux-ai-agent (v4.0)
5. 🔲 MCP Bridge: связка локальный агент ↔ облачный Buffy
6. 🔲 Дашборд состояния системы (CLI: `freebuff status`)
7. 🔲 Автоматическое восстановление после OOM-kill

### Не в MVP
- ❌ Flutter-приложение (039_12_terminal_ai_studio_mobile.md — отдельный проект)
- ❌ Web-интерфейс
- ❌ Мульти-пользовательская поддержка

---

## 🏗 Архитектура (LISA TC: ~7 — Large)

### Компонентная схема

```
┌─────────────────────────────────────────────────────────┐
│                    Freebuff Platform                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  CLI / TUI   │  │  MCP Bridge  │  │  OpenClaw GW │  │
│  │  (main.py)   │  │  (JSON-RPC)  │  │  (Node.js)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│  ┌──────▼─────────────────▼─────────────────▼───────┐  │
│  │              Orchestrator v4.0                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │  │
│  │  │  LISA GW  │  │ FSM-Lite │  │ Worker Queue │   │  │
│  │  │ (router)  │  │ (states) │  │  (SQLite)    │   │  │
│  │  └──────────┘  └──────────┘  └──────────────┘   │  │
│  └─────────────────────┬────────────────────────────┘  │
│                        │                                │
│  ┌─────────────────────▼────────────────────────────┐  │
│  │            Execution Layer                        │  │
│  │  ┌──────────────┐  ┌──────────────────────────┐  │  │
│  │  │ Micro-Chains │  │  Cloud Executor (Freebuff)│  │  │
│  │  │ (Qwen 0.5B)  │  │  (DeepSeek v4)           │  │  │
│  │  └──────────────┘  └──────────────────────────┘  │  │
│  └─────────────────────┬────────────────────────────┘  │
│                        │                                │
│  ┌─────────────────────▼────────────────────────────┐  │
│  │            Persistence Layer                      │  │
│  │  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ Context DB   │  │  File System │              │  │
│  │  │ (SQLite)     │  │  (docs_10/logs) │              │  │
│  │  └──────────────┘  └──────────────┘              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### База данных (SQLite)

```sql
-- Основная БД: data_13/context.db
-- Уже создана ContextManager'ом

-- Сессии
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, checkpoint, completed, abandoned
    project TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    message_count INTEGER NOT NULL DEFAULT 0,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    last_summary TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{***REMOVED***',     -- JSON: теги, приоритет, версии
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Сообщения
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    role TEXT NOT NULL,                     -- user, assistant, system
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL
);

-- Чекпоинты
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    checkpoint_type TEXT NOT NULL,          -- manual, auto_interval, pre_critical, post_step, context_full
    summary TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Индексы
CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX idx_checkpoints_session ON checkpoints(session_id, created_at);
```

---

## 📦 Компоненты для реализации

### 1. ContextManager (✅ реализован)
- **Файл:** `scripts_01/context_manager.py`
- **Назначение:** Управление сессиями, сообщениями, чекпоинтами
- **API:** `start_session()`, `add_message()`, `save_checkpoint()`, `get_session()`, `list_sessions()`, `complete_session()`, `export_markdown()`, `export_checkpoint_summary()`

### 2. Auto-Conspect (✅ реализован)
- **Файл:** `scripts_01/auto_conspect.py`
- **Назначение:** Автосуммаризация при завершении сессии, создание конспекта для следующей
- **API:** `auto_conspect(session_id)`

### 3. CLI-интерфейс (🔲 требуется)
- **Файл:** `freebuff_cli.py`
- **Назначение:** Командный интерфейс для управления Freebuff
- **API:**
  - `def cmd_start(project: str, topic: str = "") -> str` — начать сессию, вернуть session_id
  - `def cmd_status() -> dict` — статус: активные сессии, RAM, батарея, последний конспект
  - `def cmd_resume() -> str | None` — найти последнюю ACTIVE/CHECKPOINT сессию
  - `def cmd_conspect(session_id: str | None = None) -> str` — создать конспект
  - `def cmd_list(status: str | None = None) -> list[dict***REMOVED***` — список сессий
  - `def cmd_checkpoint(session_id: str, summary: str) -> None` — ручной чекпоинт
  - `def cmd_restore(session_id: str) -> str` — вернуть конспект для инжекта в контекст

### 4. Системный монитор (🔲 требуется)
- **Файл:** `scripts_01/system_monitor.py`
- **Назначение:** Мониторинг RAM, CPU, батареи, температуры
- **API:**
  - `def get_memory() -> dict` — `{"available_mb": int, "total_mb": int, "percent": float***REMOVED***`
  - `def get_cpu() -> dict` — `{"loadavg": str, "percent": float***REMOVED***`
  - `def get_battery() -> dict | None` — `{"level": int, "charging": bool***REMOVED***` или None
  - `def get_temperature() -> float | None` — температура в °C или None
  - `def health_check() -> dict` — сводка: `{"memory_ok": bool, "cpu_ok": bool, ...***REMOVED***`
- **Интеграция:** переиспользовать `llm_gateway/watchdog.py:check_available_memory()`

### 5. Интеграция с termux-ai-agent (✅ реализовано v4.0)
- **Файл:** `scripts_01/agent_context_bridge.py` + `termux-ai-agent/main.py`
- **Назначение:** Подключить ContextManager к основному пайплайну
- **Изменения:**
  - `AgentContextBridge` сохраняет user/assistant/system сообщения в `freebuff/data_13/context.db`
  - При старте: восстановление активной сессии проекта `termux-ai-agent`
  - При каждом запросе: `add_message()` + авточекпоинт каждые 10 сообщений
  - CLI `--freebuff-conspect` для ручного конспекта
  - Unit-тесты: `tests_09/test_agent_context_bridge.py`

### 6. Миграция существующих сессий (🔲 требуется)
- **Файл:** `scripts_01/import_sessions.py`
- **Назначение:** Импорт истории из OpenClaw, Aider, termux-ai-agent
- **Источники:**
  - `~/.openclaw/logs_14/` → sessions
  - `~/.aider.chat.history.md` → messages
  - `last_context.txt` → чекпоинт

---

## 🔄 Этапы реализации (по Kwork Arbitr v3)

### Stage 1: Analysis & Estimation
| Роль | Что делает |
|------|-----------|
| **Explainer** | Анализ ТЗ → parsed_requirements.md |
| **LISA Estimator** | TC = 7 (Large) → полный конвейер |
| **Risk Manager** | Риски: OOM-kill, потеря контекста, несовместимость версий |

### Stage 2: Architecture (текущий этап)
| Роль | Что делает |
|------|-----------|
| **Decomposer** | Разбивка на bounded contexts (см. схему выше) |
| **Architect** | Проектирование БД, API, интеграций |
| **Auditor** | Проверка: связи между компонентами, индексы БД |

### Stage 3: Implementation
| Роль | Файлы |
|------|-------|
| **Developer** | `freebuff_cli.py`, `system_monitor.py`, `import_sessions.py`, интеграция с termux-ai-agent |
| **Tester** | Тесты для ContextManager, auto_conspect, CLI |
| **Fixer** | Исправление багов по результатам тестов |

### Stage 4: Delivery
| Роль | Файлы |
|------|-------|
| **Acceptance Agent** | Проверка: все ли компоненты работают на телефоне |
| **Documenter** | `README.md`, `AGENTS.md`, `SESSION_GUIDE.md` (✅ готовы) |

---

## 📊 Метрики успеха

| Метрика | Цель | Текущее |
|---------|------|---------|
| Тестовое покрытие | >80% | 38 тестов (покрытие ~60%) |
| Время старта сессии | <5 сек | ~1 сек |
| Восстановление после OOM-kill | <10 сек | не реализовано |
| Конспект сессии (100 сообщений) | <5 KB | зависит от content |
| Токенов в конспекте для инжекта | <2000 | зависит от суммаризации |

---

## ⚠️ Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-----------|---------|-----------|
| OOM-kill Android | Высокая | Среднее | SQLite на диске, WakeLock |
| Потеря контекста между сессиями | Средняя | Высокое | Автосуммаризация + чекпоинты |
| LLM галлюцинации в конспектах | Средняя | Среднее | Детерминированные чекпоинты |
| Раздувание БД | Низкая | Низкое | Ваккум + архивация старых сессий |

---

## 📚 Референсы

- **Kwork Arbitr v3:** `/storage/emulated/0/PROJECTS/workstation/blueprints_v3/`
- **termux-ai-agent (v4.0):** `.../ai-engineering-pipeline/projects_17/termux-ai-agent/`
- **039_12_terminal_ai_studio_mobile.md:** `freebuff/pompts_11/039_12_terminal_ai_studio_mobile.md`
- **BUFFY.md:** `freebuff/BUFFY.md`

---

_Готово к реализации. Следующий шаг: Auditor проверяет архитектуру._
