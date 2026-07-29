# ПРОМПТ: Полный архитектурный аудит + реструктуризация проекта Freebuff

> **Назначение:** Запустить масштабный аудит всего проекта Freebuff
> **Когда использовать:** После перезапуска терминала
> **Команда запуска:** `cd /storage/emulated/0/PROJECTS/workstation/freebuff && freebuff`
> **Стартовая фраза:** скопируй текст ниже → отправь агенту

---

```
❗ ВАЖНО: НЕ ВЫПОЛНЯЙ НИКАКИХ ИЗМЕНЕНИЙ В КОДЕ. Только анализ, документирование и составление отчётов.
Этот запрос — аналитический. Все изменения будут сделаны после утверждения отчёта человеком.
```

---

## 📋 Контекст проекта

**Проект:** Freebuff AI Engineering Workspace
**Путь:** `/storage/emulated/0/PROJECTS/workstation/freebuff/`
**Среда:** Termux на Android (ARM64), Python 3.14, 8 ГБ RAM
**Текущая версия:** v4.9.0
**Тестов:** 1123 passed, 1 skipped, 0 failures
**Фреймворк методологии:** Kwork Arbitr v3
**Путь к blueprints_v3:** `/storage/emulated/0/PROJECTS/workstation/blueprints_v3/` (реальный путь, содержит 17 агентов-блюпринтов + registry.yaml + MANIFEST.md)

### Blueprints v3 — что это

Это методологический фреймворк для AI-разработки, основанный на 17 специализированных агентах (ролях), каждый из которых отвечает за свой этап жизненного цикла проекта:
- **Этап 1: Analysis & Estimation** — Orchestrator, Context Keeper, Explainer, LISA Estimator, Risk Manager
- **Этап 2: Architecture** — Decomposer, Architect, Auditor
- **Этап 3: Communication** — Response Writer
- **Этап 4: Implementation** — Developer, Frontend Dev, DevOps
- **Этап 5: Validation** — Tester, Fixer, Acceptance Agent
- **Этап 6: Delivery** — Documenter
- **Этап 7: Evolution** — Retrospective Agent

**Ключевые файлы blueprints_v3:** `/storage/emulated/0/PROJECTS/workstation/blueprints_v3/MANIFEST.md`, `registry.yaml`, `00_orchestrator.md`–`16_retrospective_agent.md`

### SPEC.md — ТЗ на freebuff

`/storage/emulated/0/PROJECTS/workstation/freebuff/SPEC.md` — техническое задание на платформу, написанное по методологии blueprints_v3. Должно быть эталоном для проверки соответствия.

---

## 🎯 Задание 1: Аудит функциональности кода

### 1.1 Проверка работоспособности

1. **Запусти полный тестовый прогон:** `python -m pytest tests/ -q --tb=short`
   - Зафиксируй: сколько тестов, сколько упало, какие именно упали (если есть)
   - Сравни с предыдущим результатом: **1123 passed, 1 skipped, 0 failures**

2. **Проверь импорт всех ключевых модулей:**
   - `from freebuff_plugin.runtime import ...` — Runtime Abstraction Layer
   - `from freebuff_plugin.bootstrap.engine import BootstrapEngine` — Bootstrap Engine
   - `from freebuff_plugin.bridge_layer import BridgeLayer` — Bridge Layer
   - `from freebuff_plugin.event.store import EventStore` — Event Platform
   - `from freebuff_plugin.scenario_engine import ScenarioEngine` — Scenario Engine
   - `from freebuff_plugin.tgbot import ScenarioBot` — Telegram Bot
   - `from scripts.mcp_server import BuffyMcpServer` — MCP Server
   - `from scripts.event_bus import EventBus` — Event Bus
   - `from scripts.orchestrator import Orchestrator` — Orchestrator
   - `from scripts.model_gateway import ModelGateway` — Model Gateway
   - `from scripts.knowledge_engine import KnowledgeEngine` — Knowledge Engine
   - `from scripts.memory_engine import MemoryEngine` — Memory Engine
   - `from scripts.graph_index import GraphIndex` — Graph Index
   - `from scripts.tool_runtime import ToolRegistry` — Tool Runtime
   - `from scripts.plugin_api import PluginRegistry` — Plugin API
   - `from scripts.context_manager import ContextManager` — Context Manager

3. **Проверь CLI:** `python freebuff_cli.py status` — работает ли?

### 1.2 Анализ тестового покрытия

1. Для каждого модуля определи количество тестов:
   - `tests/test_runtime_abstraction.py` — 60 тестов
   - `tests/test_mcp_server.py` — 101 тест (включая 12 bootstrap)
   - `tests/test_bootstrap_engine.py` — 61 тест
   - `tests/test_bridge_layer.py` — 60 тестов
   - `tests/test_scenario_engine.py` — 83 теста
   - `tests/test_tgbot.py` — 44 теста
   - `tests/test_orchestrator.py` — 51 тест
   - `tests/test_event_bus.py` — 30 тестов
   - `tests/test_event_store.py` — 61 тест
   - `tests/test_model_gateway.py` — 36 тестов
   - `tests/test_knowledge_engine.py` — 42 теста
   - `tests/test_graph_index.py` — 42 теста
   - `tests/test_memory_engine.py` — 30 тестов
   - `tests/test_tool_runtime.py` — 50 тестов
   - `tests/test_plugin_api.py` — 65 тестов
   - `tests/test_freebuff.py` — 25 тестов

2. Найди модули без своих тестов:
   - StreamSession — нет отдельного теста?
   - StreamBridge — нет отдельного теста?
   - Plugin API — какие файлы без покрытия?
   - Docker/конфиг-файлы без тестов?

3. Оцени общее покрытие: какие критические модули не имеют тестов?

### 1.3 Dead code / неиспользуемые файлы

1. Найди `.py` файлы, которые никуда не импортируются
2. Найди `__pycache__/` и другие артефакты
3. Найди `.bak` и дублирующие файлы
4. Найди файлы, на которые нет ссылок ни в одном документе

---

## 🎯 Задание 2: Архитектурный анализ

### 2.1 Соответствие Vision 3.0 — AI Infrastructure Layer

Проверь текущую архитектуру (`docs/core/ARCHITECTURE_3.0.md`, `docs/vision/VISION_3.0.md`) против реального кода:

| Компонент | Статус по доке | Статус в коде | Соответствие |
|-----------|---------------|---------------|--------------|
| ContextManager | ✅ Production | | |
| Memory Engine | ✅ Production | | |
| Knowledge Engine | ✅ Production | | |
| Graph Index | ✅ Production | | |
| Event Bus | ✅ Production | | |
| Orchestrator | 🟡 MVP | | |
| Policy Engine | 💡 План | | |
| Bootstrap Engine | 💡 План (по доке — устарело) | ✅ Реализован | |
| MCP Server | ✅ Production | | |
| MCP Client | 🆕 Реализован | | |
| Bridge Layer | 🆕 Реализован | | |
| ACP Protocol | 🆕 Реализован | | |
| Runtime Abstraction | 💡 План (по доке — устарело) | ✅ Реализован | |
| Scenario Engine | ✅ Production | | |
| Provider Pool | 🟡 Частично | | |
| Key Pool | 🟡 Частично | | |
| OOM Protection | ✅ Production | | |

Обнови таблицу: где дока отстаёт от кода, где код отстаёт от доки.

### 2.2 Соответствие blueprints_v3 (Kwork Arbitr)

Проверь структуру проекта на соответствие методологии blueprints_v3:

1. **Проанализируй `SPEC.md`** — соответствует ли ТЗ текущей реализации?
2. **Найди 17 ролей blueprints_v3** в реальной структуре проекта:
   - Какие роли реализованы как код?
   - Какие роли реализованы как документация?
   - Какие роли отсутствуют?
3. **Проверь пайплайн:** есть ли conditional routing? Есть ли closed loops (Auditor ↔ Architect)?
4. **LESSONS.md** — существует ли механизм самообучения?

### 2.3 Зависимости и связи между модулями

1. Построй dependency graph:
   - `Event Bus` → кто публикует, кто подписывается
   - `Bridge Layer` → зависимости от MCP Client
   - `Runtime Abstraction` → зависимость от MCP Client, Bootstrap Engine
   - `MCP Server` → зависимости от ToolRegistry, KnowledgeEngine, MemoryEngine, BootstrapEngine, BridgeLayer

2. Найди циклические зависимости (A → B → A)
3. Найди нарушения Core/Extensions/Labs: core-компоненты не должны импортировать extensions

### 2.4 Архитектурные решения

1. **Прочитай `docs/decisions/DECISIONS.md`** — все ли ADR актуальны?
   - ADR-001..ADR-007 — какие решения устарели?
2. **Проверь `IDEAS.md`** — какие идеи можно закрыть как реализованные?
3. **Проверь `ROADMAP.md`** — актуален ли план?

---

## 🎯 Задание 3: Чистота кода

### 3.1 Качество кода

1. **mypy:** `python -m mypy scripts/ freebuff_plugin/ core/ --ignore-missing-imports --strict-optional 2>&1 | tail -50`
2. **Стиль:** проверь на violations:
   - Длинные строки (>120 символов)
   - Неиспользуемые импорты
   - Хардкоженные пути вместо `Path()`
   - Голый `except:` вместо `except Exception:`
   - `shell=True` в subprocess — критическая уязвимость!
   - `exec()` / `eval()` — критическая уязвимость!

3. **Документирование:**
   - У всех ли модулей есть docstring?
   - У всех ли публичных функций/методов есть docstring?
   - Есть ли модули без единой документации?

### 3.2 Конфигурация и пути

1. Найди все хардкоженные пути (например, `/storage/emulated/0/PROJECTS/workstation/`)
2. Проверь что все они используют `Path(__file__).resolve().parent`
3. Проверь `.gitignore` — не забыты ли `.env`, `.keys/`, `__pycache__`

### 3.3 Безопасность

1. Нет ли где-то `shell=True` в subprocess? (было исправлено в v2.8.0, но могло вернуться)
2. Нет ли хардкоженных API-ключей?
3. Есть ли защита от path traversal?
4. Есть ли .env в gitignore?

---

## 🎯 Задание 4: Структура файлов и реструктуризация

### 4.1 Текущее состояние хаоса

Проект разросся, файлы разбросаны хаотично:
- `scripts/` — 30+ скриптов разного назначения
- `freebuff_plugin/` — 8 поддиректорий, нужна систематизация
- `docs/` — 30+ документов без иерархии
- `pompts/` — 20+ промптов, неясно какие актуальны
- Корень — 15+ файлов (AGENTS, BUFFY, CLAUDE, CODY, README, SPEC, TASK...)
- `projects/` — внешние проекты, встроенные в структуру freebuff

### 4.2 Задача: создать реестр документов и файлов

Составь таблицу КАЖДОГО файла в проекте:

```
| Путь | Тип | Категория | Краткое содержание | Статус | Примечание |
|------|-----|-----------|-------------------|--------|------------|
```

Категории:
- **CODE** — исполняемые скрипты, модули
- **CONFIG** — конфигурация, env, yaml, json
- **TEST** — тесты
- **DOC-ARCH** — архитектурная документация
- **DOC-AUDIT** — аудиты
- **DOC-SPEC** — спецификации
- **DOC-AGENT** — инструкции для агентов
- **DOC-SESSION** — дампы сессий
- **PROMPT** — промпты
- **PROJECT** — внешние проекты
- **DATA** — данные, БД
- **PLUGIN** — плагин-модули
- **SCRIPT-UTIL** — утилиты
- **SCRIPT-SERVICE** — сервисы (EventBus, Orchestrator...)
- **OTHER** — прочее

### 4.3 Задача: предложить новую структуру папок

На основе реестра предложи новую иерархию:

```
freebuff/
├── core/                    # Ядро системы (было scripts/ — часть)
├── services/                # Сервисы (EventBus, ModelGateway, Orchestrator...)
├── plugins/                 # Плагины (freebuff_plugin/*)
├── cli/                     # CLI-инструменты (freebuff_cli.py)
├── storage/                 # Базы данных, хранилища
├── scripts/                 # Утилиты (админские скрипты)
├── tests/                   # Тесты
├── docs/
│   ├── 01-architecture/     # Архитектурные документы
│   ├── 02-specs/            # Спецификации
│   ├── 03-audits/           # Аудиты
│   ├── 04-decisions/        # ADR
│   ├── 05-agents/           # Инструкции для агентов
│   ├── 06-sessions/         # Дампы сессий
│   ├── 07-roadmap/          # Планы развития
│   └── 08-references/       # Референсы
├── prompts/                 # Промпты
├── projects/                # Внешние проекты
├── data/                    # Данные
├── BUFFY.md                 # Оставить в корне
├── README.md                # Оставить в корне
├── CHANGELOG.md             # Оставить в корне
└── config/                  # Конфигурация (новое)
```

Проверь: не сломает ли новая структура существующие импорты?

### 4.4 Определи дубликаты

Найди файлы с одинаковым или пересекающимся содержанием:
- `AGENTS.md` vs `docs/ops/AGENTS.md` vs `.freebuff/AGENTS.md`
- `BUFFY.md` vs `CLAUDE.md` vs `CODY.md` vs `.cursorrules`
- `scripts/mcp_server.py` vs `freebuff_plugin/mcp_server.py`
- `scripts/event_bus.py` vs `freebuff_plugin/event/store.py`
- pompts/promt*.md — какие актуальны, какие устарели?

---

## 🎯 Задание 5: Итоговый отчёт

Сформируй единый документ `docs/audits/AUDIT_FULL_2026-07-29.md` со следующими разделами:

### Раздел 1: Executive Summary
- Общая оценка здоровья проекта (1-10)
- Количество файлов, строк кода, тестов
- Ключевые проблемы (top-5)
- Ключевые сильные стороны (top-5)

### Раздел 2: Code Health
- Результаты тестов: сколько, покрытие, узкие места
- Mypy errors
- Dead code
- Проблемы безопасности

### Раздел 3: Architecture
- Соответствие Vision 3.0 / blueprints_v3
- Проблемы в зависимостях
- Отставание документации от кода
- ADR — какие актуальны

### Раздел 4: File Structure
- Реестр всех файлов с категориями
- Предлагаемая новая структура
- Дубликаты и мусор

### Раздел 5: Recommendations
- P0: Критические (делать сейчас)
- P1: Высокие (делать в этом спринте)
- P2: Средние (делать в следующем спринте)
- P3: Низкие (когда будет время)

### Раздел 6: Action Plan
- Конкретные шаги по порядку
- Оценка сложности каждого шага (S/M/L/XL)
- Связанные файлы для каждого шага

---

## ✅ Формат ответа

1. Начни с краткого Executive Summary
2. Используй таблицы для структурирования
3. Каждый раздел начинай с заголовка `##`
4. В конце — Action Plan с приоритетами
5. Не предлагай изменений без оценки сложности
6. Выводы должны быть конкретными, не общими

**Все найденные проблемы задокументируй в `docs/audits/AUDIT_FULL_2026-07-29.md`**

---

**Это аналитический запрос. Никаких изменений кода не производить.**
