# 🧠 SESSION DUMP — termux-ai-agent v3.9.1 → v4.0

> **Дата:** 2026-07-27
> **Проект:** termux-ai-agent (локальный AI-агент для Android/Termux)
> **Модели:** Qwen 2.5 0.5B (локально), deepseek-v4-flash (облако, через Freebuff)
> **Версия после сессии:** 3.9.1 (готов к переходу на 4.0)

---

## 📋 TL;DR сессии

1. **Аудит проекта** — изучили все 43 файла, архитектуру из 6 слоёв
2. **8 архитектурных фиксов** — SSoT, security, thread-safety, recursion guard, DI
3. **README.md** — написан с нуля (был пустой)
4. **5 новых тестов** — reminder fallback, _safe_dict DAG/cycle detection
5. **DI-рефакторинг** — `run()` принимает gateway/router/registry параметрами
6. **DI для Router** — `keywords_registry` передаётся в конструктор
7. **mypy clean** — 0 ошибок на 43 файлах
8. **Brainstorm архитектуры v4** — 5 слоёв как единая система
9. **Анализ blueprints_v3** — Kwork Arbitr, 17 агентов, conditional routing
10. **Исследование .qwen** — 4 проекта, 1 план, сессии, конфиг qwen2.5:1.5b

---

## 🏗 Архитектура termux-ai-agent (v3.9.1)

```
main.py (orchestrator)
    │
    ├─► normalizer/   ─── ASR, даты, санитизация
    ├─► router/       ─── keyword scoring → LLM fallback
    ├─► tools/        ─── search_web, reminder, file_reader, code_gen
    │       └─► llm_gateway/  ─── subprocess llama.cpp
    │
    ▼
UserResponse (JSON)
```

### Слои
| Слой | Файлы | Роль |
|------|-------|------|
| `contracts/` | constants, enums, interfaces, schemas | SSoT: frozen dataclasses, Protocol, enum'ы |
| `infra/` | config, logger, path_validator, termux_api, wake_lock | Runtime |
| `llm_gateway/` | gateway, parser, circuit_breaker, watchdog | llama.cpp subprocess |
| `normalizer/` | asr_corrector, date_resolver, prompt_sanitizer | Очистка ввода |
| `router/` | router, scorer, registry_loader | Маршрутизация |
| `tools/` | search_web, reminder, file_reader, code_gen, registry, factories | Инструменты |
| `tui/` | app, formatter | Rich-based терминал |
| `main.py` | — | Оркестратор пайплайна |

### Ключевые метрики
- **38 тестов**, 0 mypy errors
- **33 теста** было в начале сессии → **38** сейчас (+5)
- **Зависимости:** только `requests` + `beautifulsoup4` (без ML-библиотек)
- **LLM:** subprocess `llama-cli`, Qwen 2.5 0.5B Q4_K_M

---

## 🔧 Изменения в коде (v3.9.1)

### 1. SSoT: WRITE_BLACKLIST_PATHS
`contracts/constants.py` — вынесены пути blacklist'а из `infra/config.py`
```python
WRITE_BLACKLIST_PATHS: list[str***REMOVED*** = ["/system", HOME_DIR + "/.termux", HOME_DIR + "/../usr"***REMOVED***
```

### 2. Security: os.path.expanduser
`infra/path_validator.py` — замена наивного `str.replace('~', HOME_DIR)` на `os.path.expanduser()`
```python
def _resolve_path(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))
```

### 3. Thread-safety: Lock в singleton'ах
`tools/registry.py`, `llm_gateway/__init__.py` — double-checked locking
```python
if _registry_instance is None:
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = ToolRegistry()
```

### 4. Type safety: hasattr-валидация BaseTool
`tools/registry.py` — проверка `tool_name` и `execute` через hasattr вместо isinstance
```python
def _validate_tool_protocol(tool, tool_name):
    has_tool_name = hasattr(tool, 'tool_name')
    has_execute = hasattr(tool, 'execute') and callable(getattr(tool, 'execute', None))
```

### 5. Recursion guard: _safe_dict cycle detection
`main.py` — try/finally + _seen.discard (отличает циклы от DAG)
```python
_seen.add(obj_id)
try:
    # ... рекурсивный обход ...
finally:
    _seen.discard(obj_id)
```

### 6. Error handling: FileNotFoundError в gateway
`llm_gateway/gateway.py` — явный except перед generic Exception
```python
except FileNotFoundError as e:
    # llama-cli не в PATH
except Exception as e:
    # всё остальное
```

### 7. DI: run() принимает параметры
`main.py` — keyword-only DI параметры
```python
def run(raw_query, source="text", *, gateway=None, router=None, registry=None):
```

### 8. DI: Router принимает keywords_registry
`router/router.py` — опциональный Mapping параметр
```python
def __init__(self, llm_gateway, keywords_registry=None):
```

### 9. README.md
Написан с нуля: архитектура, быстрый старт, инструменты, конфигурация, тестирование

---

## 🧪 Новые тесты (+5)

### TestReminder (2 теста)
- `test_reminder_fallback_to_jsonl` — ics падает → jsonl-лог
- `test_reminder_all_fallbacks_fail` — все 3 канала падают → NOTIFICATION_FAILED

### TestSafeDict (3 теста)
- `test_dag_shared_reference` — DAG сериализуется корректно
- `test_true_circular_reference` — self-reference → `<circular-reference>`
- `test_nested_circular_reference` — a→b→a цикл

### E2E тесты переписаны на DI
Было: `@patch('main.Router')`, `@patch('main.get_registry')`
Стало: `run(..., router=mock_router, registry=mock_registry)`

---

## 🌐 Исследование внешних систем

### Фреймворки
| Система | Архитектура | Применимость к Termux |
|---------|------------|----------------------|
| **Hermes Agent** | local-first, memory-first, continuous learning | ❌ Тяжело (desktop) |
| **OpenClaw** | Gateway–Node–Host, Docker sandbox | ⚠️ Возможно, но Node.js/systemd |
| **CrewAI** | Role-based teams, Manager→Workers | ❌ Промпт-оверхед убивает 0.5B |
| **AutoGen** | Conversable peer-to-peer | ⚠️ Средне |
| **LangGraph** | State-machine, cyclic graphs | ✅ Лучший fit для 0.5B-3B |

### Android/Edge
- llama.cpp работает в Termux
- 2-8GB RAM → Q4_K_M, 3B-8B модели
- Idempotency критична (Android OOM-killer)
- mobile-mcp: мост LLM ↔ Android UI

---

## 🏛 Kwork Arbitr v3 (blueprints_v3/)

17-агентный AI-конвейер для фриланса:
- **Orchestrator**: state-machine dispatcher
- **Conditional routing**: complexity-based (Small/Medium/Large/Complex)
- **Project type routing**: Web/Bot/Script/API → skip roles
- **Closed loops**: Auditor→Architect, Fixer→Tester (max 3)
- **LISA-3**: complexity estimator (0-10)
- **Self-improving**: LESSONS.md, LISA calibration
- **Knowledge verification**: 5-step chain
- **Author ≠ Verifier**: mutation testing

---

## 📂 .qwen (сессии и контекст)

**Путь:** `/data/data/com.termux/files/home/.qwen/`

| Директория | Содержимое |
|-----------|-----------|
| `plans/` | 1 активный план (`2096521a-...`) |
| `projects_17/` | 4 проекта: home, agent, leviathan-os, PROJECTS |
| `memories/` | MEMORY.md + feedback + reference + user |
| `skills/` | Пусто |
| `todos/` | 10 JSON-файлов |
| `file-history/` | 10 записей (UUID-based) |

**Конфиг:**
- Провайдер: ollama (localhost:11434)
- Модели: qwen2.5:1.5b, qwen2.5:0.5b, tinyllama
- Активная: deepseek-v4-flash (через Freebuff)
- Workspace: ~/storage/shared/PROJECTS

---

## 🎯 Архитектура v4.0: Целостная 5-слойная система

5 подходов из брейншторма — это **не альтернативы, а слои одной системы**:

```
                    ┌──────────────────────────┐
                    │    MCP Bridge (слой 5)    │  ← стандартизированный протокол
                    │    Model Context Protocol │     телефон ↔ облако
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  Micro-Chains (слой 4)    │  ← стратегия выполнения
                    │  Цепочки one-shot промптов│     для малых моделей
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │   FSM-Lite (слой 3)       │  ← control plane
                    │   Конечный автомат         │     SQLite-state, граф переходов
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │ LISA Edge Gateway (слой 2)│  ← точка входа
                    │ Роутер сложности           │     LOCAL vs CLOUD dispatch
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │ Worker Queue (слой 1)     │  ← фундамент
                    │ SQLite + идемпотентность   │     WakeLock, retry, persistence
                    └──────────────────────────┘
```

### Data flow
```
User Input
  → LISA Gateway: классификация сложности (Qwen 0.5B)
    → LOCAL (simple): Worker Queue → FSM-Lite → Micro-Chains → Tool
    → CLOUD (complex): Worker Queue → MCP Bridge → Freebuff
  → Response
```

### Переиспользование v3.9.1
| Компонент v3.9.1 | Использование в v4.0 |
|------------------|---------------------|
| `router.py` | → LISA Gateway: добавить классификатор LOCAL/CLOUD |
| `tools/` | → Micro-Chains: тулы как атомарные шаги |
| `llm_gateway/` | → локальные вызовы Qwen внутри worker'ов |
| `wake_lock.py` | → Worker Queue: защита от сна |
| `contracts/schemas.py` | → поля SQLite (UnifiedRequest/UserResponse → JSON columns) |
| `infra/logger.py` | → correlation_id через все слои |
| `normalizer/` | → preprocessing перед Gateway |

---

## 📊 Статистика сессии

| Метрика | Было | Стало |
|---------|------|-------|
| Тесты | 33 | **38** |
| mypy errors | неизвестно | **0** |
| README | пустой | **полный** |
| @patch в тестах | 7 (E2E + router) | **1** (TestToolRegistry) |
| DI-параметры у run() | 2 | **5** |
| Архитектурные фиксы | 0 | **8** |
| Новые файлы | — | **SESSION_DUMP.md** |

---

## 🚀 Что дальше (v4.0 roadmap)

1. **Слой 1: Worker Queue** — `infra/worker_queue.py` (SQLite + идемпотентность)
2. **Слой 2: LISA Gateway** — расширить `router/router.py` (классификатор LOCAL/CLOUD)
3. **Слой 3: FSM-Lite** — `orchestrator/fsm.py` (SQLite-state, граф переходов)
4. **Слой 4: Micro-Chains** — `executor/micro_chains.py` (цепочки one-shot промптов)
5. **Слой 5: MCP Bridge** — `gateway/mcp_bridge.py` (Model Context Protocol)
6. **Интеграция** — `main.py` v4.0 (сборка всех слоёв)

---

_Сгенерировано: 2026-07-27, сессия termux-ai-agent_
