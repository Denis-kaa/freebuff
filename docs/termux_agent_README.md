# 🤖 termux-ai-agent

**Локальный AI-агент для Android (Termux) с модульной архитектурой.**

Принимает текстовые и голосовые (ASR) запросы, определяет намерение через keyword scoring → LLM fallback, выполняет действия через 4 модульных инструмента и возвращает структурированный JSON-ответ.

Использует **локальную LLM** (Qwen 2.5 0.5B через `llama-cli`) — никаких облачных API, полная автономность на устройстве.

---

## Архитектура

```
пользовательский ввод (text / voice)
        │
        ▼
   main.py (orchestrator)
        │
        ├─► normalizer/   ─── ASR-коррекция, резолв дат, санитизация
        ├─► router/       ─── keyword scoring → LLM fallback
        ├─► tools/        ─── 4 инструмента: search_web, reminder, file_reader, code_gen
        │       └─► llm_gateway/  ─── subprocess llama.cpp (watchdog + circuit breaker)
        │
        ▼
   UserResponse (JSON)
```

### Слои (сверху вниз)

| Слой | Назначение |
|---|---|
| `contracts/` | **Single Source of Truth**: константы, enum'ы, frozen dataclasses, Protocol-интерфейсы |
| `infra/` | Runtime: Config, Logger (correlation_id), PathValidator, TermuxAPI, WakeLock |
| `llm_gateway/` | Единственная точка работы с `llama-cli` (watchdog, circuit breaker, 4-уровневый парсер) |
| `normalizer/` | Очистка: ASR-корректор, date resolver, prompt sanitizer |
| `router/` | Маршрутизация: keyword scoring → LLM fallback при низкой уверенности |
| `tools/` | Инструменты + реестр + фабрики `ToolResult` |
| `main.py` | Оркестратор пайплайна |
| `tui/` | Rich-based терминальный интерфейс |

### Ключевые принципы

- **Без внешних ML-библиотек**: только `stdlib` + `requests` + `beautifulsoup4`
- **Frozen dataclasses**: все контрактные схемы immutable (`@dataclass(frozen=True)`)
- **Generic context**: все инструменты принимают `context: Mapping[str, Any***REMOVED***` — унифицированный контракт v3.9.0
- **Correlation ID**: сквозной tracing через UUID v4
- **Defensive LLM**: watchdog памяти + circuit breaker (3 фейла → OPEN, автосброс 60с) + process group kill
- **3-уровневый fallback для reminder**: termux-notification → .ics файл → jsonl лог
- **Детерминированный scoring**: keyword matching с лексикографическим tie-breaker

---

## Быстрый старт

### Требования

- **Termux** на Android
- **Python 3.11+**
- **llama.cpp** (`llama-cli` в PATH)
- **Модель**: Qwen 2.5 0.5B Instruct Q4_K_M → `~/models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
- **termux-api** (для push-уведомлений, опционально)

### Установка

```bash
# 1. Клонировать репозиторий
cd ~/
git clone <repo-url> termux-ai-agent
cd termux-ai-agent

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Установить termux-api (опционально, для уведомлений)
pkg install termux-api

# 4. Скачать модель Qwen 2.5 0.5B
mkdir -p ~/models
# Скачать вручную с HuggingFace: Qwen/Qwen2.5-0.5B-Instruct-GGUF
```

### Запуск

```bash
# TUI-режим (рекомендуется)
cd ~/termux-ai-agent
python tui/app.py

# Или интерактивный режим
python interactive_test.py

# Или пакетный тест
python test_run.py
```

### Примеры запросов

```
найди информацию про python
напомни купить молоко завтра
прочитай файл /sdcard/test.txt
напиши код на python для hello world
```

---

## Инструменты

| Инструмент | Описание | LLM calls | Формат результата |
|---|---|---|---|
| `search_web` | Поиск в DuckDuckGo HTML, ротация User-Agent, retry, captcha-детект | 0 | `{"query": "...", "results": [...***REMOVED******REMOVED***` |
| `reminder` | NER-извлечение сущностей, 3-level fallback доставки | 1 | `{"person": "...", "action": "...", "deadline": "ISO8601"***REMOVED***` |
| `file_reader` | Валидация пути, чтение UTF-8, LLM-суммаризация (2-3 предложения) | 1 | `{"path": "...", "summary": "..."***REMOVED***` |
| `code_gen` | Генерация кода, сохранение в `~/storage/downloads/generated/` (БЕЗ выполнения) | 1 | `{"file_path": "...", "language": "..."***REMOVED***` |

---

## Структура проекта

```
.
├── main.py                  # Оркестратор пайплайна
├── interactive_test.py      # Интерактивный тестовый клиент
├── test_run.py              # Пакетный тест
├── requirements.txt         # requests, beautifulsoup4
├── 00_tz.md                 # Полное техническое задание
│
├── contracts/               # SSoT: константы, схемы, интерфейсы
│   ├── constants.py
│   ├── enums.py
│   ├── interfaces.py
│   └── schemas.py
│
├── infra/                   # Runtime инфраструктура
│   ├── config.py
│   ├── logger.py
│   ├── path_validator.py
│   ├── termux_api.py
│   └── wake_lock.py
│
├── llm_gateway/             # LLM subprocess + защита
│   ├── gateway.py
│   ├── parser.py
│   ├── circuit_breaker.py
│   └── watchdog.py
│
├── normalizer/              # Нормализация ввода
│   ├── normalizer.py
│   ├── asr_corrector.py
│   ├── date_resolver.py
│   └── prompt_sanitizer.py
│
├── router/                  # Маршрутизация
│   ├── router.py
│   ├── scorer.py
│   └── registry_loader.py
│
├── tools/                   # Инструменты
│   ├── registry.py
│   ├── factories.py
│   ├── search_web.py
│   ├── reminder.py
│   ├── file_reader.py
│   ├── code_gen.py
│   └── tools_registry.json
│
├── tui/                     # Терминальный UI
│   ├── app.py
│   └── formatter.py
│
└── tests/                   # Тесты (33 шт.)
    ├── test_phase2.py
    ├── test_phase3.py
    ├── test_phase4.py
    └── e2e/
        ├── conftest.py
        └── test_full_pipeline.py
```

---

## Тестирование

```bash
python -m pytest tests/ -v
```

33 теста: unit (circuit breaker, parser, scorer, factories), integration (router, tools), e2e (full pipeline).

---

## Конфигурация

Все константы живут в `contracts/constants.py` (SSoT). Runtime-значения (пути) резолвятся через `infra/config.py`.

Ключевые настройки:
- `MAX_TOTAL_TIMEOUT_MS = 90_000` — глобальный таймаут запроса
- `ROUTER_CONFIDENCE_THRESHOLD = 0.25` — порог keyword scoring
- `CIRCUIT_BREAKER_THRESHOLD = 3` — фейлов до отключения LLM
- `MAX_FILE_SIZE_BYTES = 16384` — лимит читаемых файлов
- `OOM_THRESHOLD_MB = 50` — минимум свободной RAM

---

## Лицензия

MIT
