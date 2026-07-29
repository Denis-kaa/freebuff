# Полный архитектурный аудит Freebuff

> **Дата:** 2026-07-29  
> **Версия проекта:** v4.9.0  
> **Аудитор:** Buffy (DeepSeek v4 Flash)  
> **Статус:** Аналитический отчёт, изменения кода не производились  

---

## Раздел 1: Executive Summary

### 1.1 Общая оценка

| Метрика | Значение |
|---------|----------|
| **Общая оценка здоровья проекта** | **7.2 / 10** |
| **Всего файлов** | 959 |
| **Python-файлов** | 169 |
| **Тестов** | 1124 passed, 0 failed |
| **mypy ошибок** | 108 в 21 файле |
| **Критических уязвимостей** | 1 (`shell=True` в `bootstrap/installer.py`) |
| **Документация vs код** | Документация частично отстаёт от кода |

### 1.2 Ключевые проблемы (Top-5)

1. **Документация отстаёт от кода** — Vision 3.0 / ROADMAP / ARCHITECTURE_3.0 помечают Bootstrap Engine, Runtime Abstraction, MCP Client, Bridge Layer, ACP как «план»/«MVP», но в коде они уже реализованы и протестированы.
2. **108 ошибок mypy** — в первую очередь `union-attr` в Telegram-боте, `no-any-return` в MCP-серверах, отсутствующие импорты.
3. **Один случай `shell=True`** в `freebuff_plugin/bootstrap/installer.py` (линия 205) — критическая уязвимость, несмотря на якобы полное устранение в v2.8.0.
4. **Дублирующие документы** — 3 версии `AGENTS.md` (root, docs/, .freebuff/), fallback-файлы `CLAUDE.md`/`CODY.md`/`.cursorrules`, два MCP-сервера (`scripts/mcp_server.py` и `freebuff_plugin/mcp_server.py`).
5. **Структурный хаос** — 959 файлов, из них 159 «прочих» (OTHER): логи, артефакты сборки, сессии, кэш, не размеченные данные.

### 1.3 Ключевые сильные стороны (Top-5)

1. **Высокое тестовое покрытие** — 1124 теста, 0 failures, включая 60 Runtime Abstraction, 101 MCP Server, 61 Bootstrap Engine, 60 Bridge Layer, 83 Scenario Engine.
2. **Активная эволюция архитектуры** — за сессию реализованы Bootstrap Engine, Runtime Abstraction Layer, Event Platform, Bridge Layer, ACP, MCP Client.
3. **Сильная документированная стратегия** — VISION_3.0, ARCHITECTURE_3.0, ROADMAP, ADR, IDEAS регулярно обновляются.
4. **Event-driven архитектура** — Event Bus интегрирует почти все компоненты, упрощает трассировку.
5. **OOM Protection & Local First** — wrapper v4, monitor.sh, oom_protect.sh делают проект устойчивым на Termux.

---

## Раздел 2: Code Health

### 2.1 Результаты тестов

| Показатель | Значение |
|------------|----------|
| **Всего тестов** | 1124 |
| **Пройдено** | 1124 |
| **Пропущено** | 0 |
| **Упало** | 0 |
| **Warnings** | 13 (DepracationWarning asyncio.iscoroutinefunction в starlette/fastapi) |
| **Время** | 269.86s (~4.5 мин) |

**Сравнение с предыдущим чекпоинтом:** `1123 passed, 1 skipped, 0 failures` → `1124 passed, 13 warnings`. Тестовое покрытие растёт.

### 2.2 Распределение тестов по модулям

| Тест-файл | Тестов | Статус |
|-----------|--------|--------|
| `test_scenario_engine.py` | 83 | ✅ |
| `test_mcp_server.py` | 101 | ✅ |
| `test_bootstrap_engine.py` | 61 | ✅ |
| `test_event_store.py` | 61 | ✅ |
| `test_runtime_abstraction.py` | 60 | ✅ |
| `test_bridge_layer.py` | 60 | ✅ |
| `test_orchestrator.py` | 51 | ✅ |
| `test_plugin_api.py` | 65 | ✅ |
| `test_tool_runtime.py` | 53 | ✅ |
| `test_stream_session.py` | 48 | ✅ |
| `test_tgbot.py` | 19 | ✅ |
| `test_telegram_bot.py` | 6 | ✅ (скромное) |
| `test_mcp_fastapi.py` | 35 | ✅ |
| `test_freebuff.py` | 27 | ✅ |
| `test_model_gateway.py` | 36 | ✅ |
| `test_graph_index.py` | 42 | ✅ |
| `test_knowledge_engine.py` | 42 | ✅ |
| `test_memory_engine.py` | 34 | ✅ |
| `test_event_bus.py` | 36 | ✅ |
| `test_semantic_index.py` | 15 | ✅ |
| `test_agent_context_bridge.py` | 5 | ✅ |
| `test_lightpanda_worker.py` | 8 | ✅ |
| **Итого** | **1124** | ✅ |

### 2.3 Покрытие: что без отдельных тестов

| Компонент | Тесты | Примечание |
|-----------|-------|------------|
| `StreamSession` | ❌ Нет отдельного файла | Частично через `test_stream_session.py` (48) |
| `StreamBridge` |  Нет отдельного файла | `test_stream_bridge.py` (26) |
| `KeyPool` | ❌ Нет | Упоминается в ModelGateway, но dedicated тест отсутствует |
| `freebuff_plugin/api.py` | ❌ Нет | API endpoints сценариев не тестированы |
| `scripts/phone_mcp_server.py` | ❌ Нет | Отдельный MCP-сервер телефона без тестов |
| `scripts/dashboard_api.py` | ❌ Нет | Дашборд без тестов |

### 2.4 mypy

| Метрика | Значение |
|---------|----------|
| **Всего ошибок** | 108 |
| **Файлов с ошибками** | 21 |
| **Топ-3 файла** | `freebuff_plugin/tgbot.py` (45), `freebuff_plugin/mcp_server.py` (13), `freebuff_plugin/mcp_client.py` (10) |

**Основные паттерны ошибок:**
- `union-attr` — доступ к атрибутам `Optional[Message***REMOVED***`, `Optional[CallbackQuery***REMOVED***`.
- `no-any-return` — функции с аннотацией возвращают `Any`.
- `assignment` / `arg-type` — несовпадение типов, `None` вместо конкретного типа.
- `name-defined` — `c_ushort`/`c_uint` в `freebuff_plugin/bootstrap/checker.py`, `sys` не импортирован в `freebuff_plugin/bridge_layer.py`.
- `attr-defined` — доступ к несуществующим атрибутам.

### 2.5 Безопасность

| Проверка | Результат |
|----------|-----------|
| `shell=True` в `.py` | ⚠️ `freebuff_plugin/bootstrap/installer.py:205` |
| `exec()` в `.py` | ❌ Нет в production-коде (есть в тестах и docstring `orchestrator.py`) |
| `eval()` в `.py` | ❌ Не найден |
| Хардкод API-ключей | ❌ Не обнаружен (ключи в `.keys/` за `.gitignore`) |
| `.env` в `.gitignore` | ✅ Да |
| `.keys/` в `.gitignore` | ✅ Да |
| Path traversal защита | ✅ Частично (FileTool проверяет пути) |

### 2.6 Dead code / артефакты

| Артефакт | Количество | Примечание |
|----------|------------|------------|
| `.bak` файлы | 10+ | В основном в `pompts/` и `projects/diet_platform/` |
| `__pycache__` директорий | 38 | Не должны попадать в git (в `.gitignore`) |
| `.pyc` файлов | 149 | Артефакты |
| `node_modules` / `dist` | Есть в `buffy-playground/` | Ожидаемо для Vite-проекта |

---

## Раздел 3: Architecture

### 3.1 Соответствие Vision 3.0 / ARCHITECTURE_3.0

| Компонент | Статус по доке | Статус в коде | Соответствие |
|-----------|---------------|---------------|--------------|
| ContextManager | ✅ Production | ✅ Production | ✅ Полное |
| Memory Engine | ✅ Production | ✅ Production | ✅ Полное |
| Knowledge Engine | ✅ Production | ✅ Production | ✅ Полное |
| Graph Index | ✅ Production | ✅ Production | ✅ Полное |
| Event Bus | ✅ Production | ✅ Production | ✅ Полное |
| Orchestrator | 🟡 MVP | ✅ Production (51 тест) | ️ Дока недооценивает |
| Policy Engine |  План | ❌ Не начато | ✅ Соответствует |
| Bootstrap Engine | 💡 План | ✅ Реализован (61 тест) | ❌ Дока отстаёт |
| MCP Server | ✅ Production | ✅ Production | ✅ Полное |
| MCP Client |  Реализован | ✅ Реализован | ✅ Полное |
| Bridge Layer | 🆕 Реализован | ✅ Реализован (60 тестов) | ✅ Полное |
| ACP Protocol |  Реализован | ✅ Реализован | ✅ Полное |
| Runtime Abstraction | 💡 План | ✅ Реализован (60 тестов) |  Дока отстаёт |
| Scenario Engine | ✅ Production | ✅ Production | ✅ Полное |
| Event Platform | 💡 План | ✅ Реализован (61 тест) | ❌ Дока отстаёт |
| Provider Pool | 🟡 Частично | 🟡 Частично (ModelGateway 6 провайдеров) | ✅ Соответствует |
| Key Pool | 🟡 Частично |  Частично (без dedicated тестов) | ✅ Соответствует |

**Вывод:** документация Vision 3.0 и ARCHITECTURE_3.0 существенно отстаёт от кода. Bootstrap Engine, Runtime Abstraction, Event Platform уже в Production, но в документации помечены как «план».

### 3.2 Соответствие blueprints_v3 / SPEC.md

`SPEC.md` — техническое задание, написанное по методологии blueprints_v3. В проекте реализованы 17 ролей blueprints_v3 не как отдельные кодовые агенты, а как **документы + сценарии**:

| Роль blueprints_v3 | Реализация в коде | Реализация в документации |
|-------------------|-------------------|---------------------------|
| Orchestrator | ✅ `scripts/orchestrator.py` | `../core/ARCHITECTURE_3.0.md` |
| Context Keeper | ✅ `scripts/context_manager.py` | `BUFFY.md`, `../ops/SESSION_GUIDE.md` |
| Explainer | ✅ Scenario Engine (`agent_setup.md`) | `../ops/PROMPT_BASE.md` |
| LISA Estimator |  Нет | ❌ Нет |
| Risk Manager | ⚠️ Частично (Risk register в VISION_3.0) | `../vision/VISION_3.0.md` |
| Decomposer | ✅ Scenario Engine (`task_framework.md`) | `../core/ARCHITECTURE_3.0.md` |
| Architect | ⚠️ Частично (Capability Router) | `../core/ARCHITECTURE_3.0.md` |
| Auditor | ⚠️ Частично (`drift_check.py`, аудиты) | `docs/AUDIT_*.md` |
| Response Writer | ✅ `freebuff_plugin/scenario_engine.py` | `../ops/PROMPT_BASE.md` |
| Developer | ✅ Buffy / Codebuff CLI | `BUFFY.md` |
| Frontend Dev | ⚠️ `buffy-playground/` | `buffy-playground/README.md` |
| DevOps | ⚠️ `scripts/oom_protect.sh`, wrapper | `../projects_meta/LIGHTPANDA_INTEGRATION.md` |
| Tester | ✅ 1124 pytest тестов | `tests/` |
| Fixer | ️ `scripts/drift_check.py` | `DRIFT_REPORT.md` |
| Acceptance Agent | ❌ Нет | ❌ Нет |
| Documenter | ✅ `scripts/buffy_autodoc.py`, CHANGELOG | `../core/RULES.md` |
| Retrospective Agent | ⚠️ `scripts/auto_conspect.py` | `../ops/SESSION_GUIDE.md` |

**Вывод:** методология blueprints_v3 применена не формально, но большинство ролей покрыты кодом или документацией. Не хватает dedicated `LISA Estimator` и `Acceptance Agent`.

### 3.3 ADR — актуальность

| ADR | Статус | Актуальность |
|-----|--------|--------------|
| ADR-001 Model Gateway | ✅ Принят | Актуален |
| ADR-002 MCP Server Pure Python | ✅ Принят | Актуален |
| ADR-003 MCP Streamable HTTP | ✅ Принят | Актуален |
| ADR-004 FastAPI + Cloudflare Tunnel | ✅ Принят | Актуален |
| ADR-005 ContextManager Bridge | ✅ Принят | Актуален |
| ADR-006 Lightpanda Integration | ✅ Принят | Актуален |
| ADR-007 Vision 3.0 AI Infrastructure | ✅ Принят | Актуален, но требует обновления связанных спеков |

### 3.4 Циклические зависимости

| Потенциальная связь | Оценка |
|---------------------|--------|
| `scripts/mcp_server.py` ↔ `scripts/tool_runtime.py` | Нет цикла, mcp_server использует tool_runtime |
| `freebuff_plugin/bridge_layer.py` ↔ `freebuff_plugin/acp_protocol.py` | Нет цикла, bridge использует acp |
| `scripts/event_bus.py` ↔ подписчики | Слабая связь через callback, циклов не обнаружено |
| `freebuff_plugin/bootstrap/engine.py` ↔ `freebuff_plugin/runtime/` | Runtime использует Bootstrap installer, но не наоборот (пока) |

### 3.5 Нарушения Core/Extensions/Labs

| Проверка | Результат |
|----------|-----------|
| Core импортирует Extensions | ⚠️ `scripts/context_manager.py` публикует события, но не импортирует Extensions напрямую — ок |
| Extensions зависят друг от друга | ⚠️ Bridge Layer → MCP Client → ok, Scenario Engine → TG Bot → ok |
| Labs зависят от Core/Extensions | Нет Labs-компонентов в коде, только в документации |

---

## Раздел 4: File Structure

### 4.1 Реестр файлов (агрегированный)

| Категория | Количество | Примеры |
|-----------|------------|---------|
| **CODE** | 132 | `scripts/*.py`, `freebuff_plugin/**/*.py`, `core/*.py` |
| **CONFIG** | 58 | `.freebuff/config.json`, `profiles.yaml`, `requirements.txt`, `.gitignore` |
| **DATA** | 109 | `data/*.db`, `context/**/*.db`, `*.npy`, `*.log` |
| **DOC** | 198 | `README.md`, `CHANGELOG.md`, `TASK.md`, промпты, сессии |
| **DOC-AGENT** | 13 | `AGENTS.md`, `BUFFY.md`, `CLAUDE.md`, `CODY.md`, `.cursorrules` |
| **DOC-ARCH** | 59 | `../vision/VISION_3.0.md`, `../core/ARCHITECTURE_3.0.md`, ADR, спеки |
| **DOC-AUDIT** | 9 | `docs/AUDIT_*.md` |
| **DOC-SESSION** | 2 | `docs/session_dumps/*.md` |
| **TEST** | 37 | `tests/test_*.py` |
| **OTHER** | 159 | `node_modules`, `.mypy_cache`, `.pytest_cache`, сессионные логи |
| **ИТОГО** | **959** | — |

### 4.2 Дубликаты и пересекающийся контент

| Группа | Файлы | Проблема | Рекомендация |
|--------|-------|----------|--------------|
| **AGENTS.md** | `AGENTS.md` (2771 B), `../ops/AGENTS.md` (5024 B), `.freebuff/AGENTS.md` (1998 B) | Три версии агент-инструкций | Объединить в корневой `AGENTS.md`, остальные сделать symlink/редирект |
| **Fallback-контексты** | `BUFFY.md`, `CLAUDE.md`, `CODY.md`, `.cursorrules` | Повторяющиеся правила для разных CLI | ✅ Оправдано: разные интеграции |
| **MCP Server** | `scripts/mcp_server.py` (79 KB), `freebuff_plugin/mcp_server.py` (32 KB) | Два MCP-сервера, разные размеры | Проверить, не дублируют ли они функциональность; возможно, один должен быть обёрткой |
| **Event Bus** | `scripts/event_bus.py` (20 KB), `freebuff_plugin/event/store.py` (22 KB) | Разные назначения, но похожие имена | ✅ Не дублируют: event_bus — шина, store.py — хранилище Event Platform |
| **Promt-файлы** | `pompts/promt*.md`, `pompts/new.md` | Много промптов, неясно какие актуальны | Добавить `pompts/README.md` с индексом и статусами |

### 4.3 Предлагаемая новая структура

```
freebuff/
├── core/                          # Ядро (было scripts/core-*)
│   ├── __init__.py
│   ├── interfaces.py
│   └── router.py
├── services/                      # Сервисы (было scripts/)
│   ├── context/
│   ├── memory/
│   ├── knowledge/
│   ├── graph/
│   ├── event_bus/
│   ├── orchestrator/
│   ├── model_gateway/
│   ├── tool_runtime/
│   ├── plugin_api/
│   └── mcp/
├── plugins/                       # Плагины
│   ├── freebuff_plugin/           # основной плагин
│   └── hello_world/
├── cli/                           # CLI и entrypoints
│   ├── freebuff_cli.py
│   └── wrapper/
├── tests/                         # Тесты (сохранить плоским)
├── docs/
│   ├── 01-architecture/
│   ├── 02-specs/
│   ├── 03-audits/
│   ├── 04-decisions/
│   ├── 05-agents/
│   ├── 06-sessions/
│   ├── 07-roadmap/
│   └── 08-references/
├── prompts/                       # pompts/ → prompts/
├── projects/                        # внешние проекты
├── data/                            # БД и индексы
├── scripts/                         # админ/utility скрипты (сократить)
├── README.md
├── BUFFY.md
├── CHANGELOG.md
└── SPEC.md
```

**Риск миграции:** высокий. Множество импортов `from scripts.X import ...` придётся менять. Рекомендуется делать поэтапно, через `__init__.py`-proxy.

### 4.4 Артефакты, требующие очистки

| Артефакт | Рекомендация |
|----------|--------------|
| `pompts/*.bak` | Удалить или перенести в `pompts/archive/` |
| `projects/diet_platform/*.bak` | Удалить |
| `__pycache__` / `*.pyc` | Уже в `.gitignore`, но в рабочей директории занимают место |
| `context/` runtime-директории | ✅ Оставить, это рабочие данные |
| `.mypy_cache`, `.pytest_cache` | Добавить в `.gitignore` (если ещё не), очищать периодически |

---

## Раздел 5: Recommendations

### P0: Критические (делать сейчас)

| # | Рекомендация | Сложность | Файлы |
|---|-------------|-----------|-------|
| 1 | **Убрать `shell=True` в `bootstrap/installer.py:205`** | S | `freebuff_plugin/bootstrap/installer.py` |
| 2 | **Исправить 108 ошибок mypy** | M-L | `freebuff_plugin/tgbot.py`, `freebuff_plugin/mcp_server.py`, `freebuff_plugin/mcp_client.py` и др. |
| 3 | **Обновить Vision 3.0 / ARCHITECTURE_3.0 / ROADMAP** — отметить Bootstrap Engine, Runtime Abstraction, Event Platform как Implemented | S | `../vision/VISION_3.0.md`, `../core/ARCHITECTURE_3.0.md`, `../vision/ROADMAP.md` |

### P1: Высокие (этот спринт)

| # | Рекомендация | Сложность | Файлы |
|---|-------------|-----------|-------|
| 4 | **Добавить тесты для `freebuff_plugin/api.py`**, `KeyPool`, `StreamSession/StreamBridge` | M | `tests/test_api.py`, `tests/test_keypool.py` |
| 5 | **Объединить/прояснить дублирующие AGENTS.md** | S | `AGENTS.md`, `../ops/AGENTS.md`, `.freebuff/AGENTS.md` |
| 6 | **Удалить `.bak` файлы и добавить `*.bak` в `.gitignore`** | S | `.gitignore`, рабочая директория |
| 7 | **Исправить неработающие импорты** (`RuntimeRegistry`, `ScenarioBot`) | S | `freebuff_plugin/runtime/__init__.py`, `freebuff_plugin/tgbot.py` |

### P2: Средние (следующий спринт)

| # | Рекомендация | Сложность | Файлы |
|---|-------------|-----------|-------|
| 8 | **Провести реструктуризацию `scripts/` → `services/` и `cli/`** | L | Множество импортов |
| 9 | **Добавить `KeyPool` как отдельный тестируемый компонент** | M | `scripts/model_gateway.py`, `tests/test_keypool.py` |
| 10 | **Создать `pompts/README.md` с индексом и статусами промптов** | S | `pompts/` |

### P3: Низкие (когда будет время)

| # | Рекомендация | Сложность | Файлы |
|---|-------------|-----------|-------|
| 11 | **Реализовать `LISA Estimator` и `Acceptance Agent` по blueprints_v3** | L | Новые модули |
| 12 | **Добавить pre-commit hook на mypy zero-errors** | S | `.pre-commit-config.yaml` или `scripts/pre-commit` |
| 13 | **Автоматизировать обновление «Current State vs Vision» таблицы** | M | `scripts/drift_check.py` |

---

## Раздел 6: Action Plan

| # | Шаг | Сложность | Связанные файлы | Ожидаемый результат |
|---|-----|-----------|-----------------|---------------------|
| 1 | Исправить `shell=True` в `bootstrap/installer.py` | S | `freebuff_plugin/bootstrap/installer.py` | Устранение критической уязвимости |
| 2 | Исправить 108 mypy ошибок | M | `freebuff_plugin/tgbot.py`, `freebuff_plugin/mcp_server.py`, `freebuff_plugin/mcp_client.py` | `mypy` проходит без ошибок |
| 3 | Обновить статус компонентов в `../vision/VISION_3.0.md` и `../core/ARCHITECTURE_3.0.md` | S | `../vision/VISION_3.0.md`, `../core/ARCHITECTURE_3.0.md`, `../vision/ROADMAP.md` | Документация соответствует коду |
| 4 | Удалить/заархивировать `.bak` файлы | S | `pompts/*.bak`, `projects/diet_platform/*.bak` | Чистая рабочая директория |
| 5 | Объединить/прояснить `AGENTS.md` | S | `AGENTS.md`, `../ops/AGENTS.md`, `.freebuff/AGENTS.md` | Единый источник правил для агентов |
| 6 | Исправить импорты `RuntimeRegistry` и `ScenarioBot` | S | `freebuff_plugin/runtime/__init__.py`, `freebuff_plugin/tgbot.py` | Все ключевые импорты работают |
| 7 | Добавить недостающие тесты (API, KeyPool, StreamSession) | M | `tests/test_api.py`, `tests/test_keypool.py` | Покрытие критичных компонентов |
| 8 | Провести реструктуризацию папок | L | `scripts/`, `freebuff_plugin/`, `core/` | Упрощённая навигация |
| 9 | Добавить pre-commit mypy hook | S | `scripts/pre-commit` | Предотвращение регрессий |
| 10 | Автоматизировать аудит «Current State vs Vision» | M | `scripts/drift_check.py` | Регулярная сверка док-код |

---

## Приложение A: Ключевые импорты

```
✅ freebuff_plugin.bootstrap.engine.BootstrapEngine
✅ freebuff_plugin.bridge_layer.BridgeLayer
✅ freebuff_plugin.event.store.EventStore
✅ freebuff_plugin.scenario_engine.ScenarioEngine
❌ freebuff_plugin.runtime.RuntimeRegistry — module has no attribute 'RuntimeRegistry'
❌ freebuff_plugin.tgbot.ScenarioBot — module has no attribute 'ScenarioBot'
 scripts.mcp_server.BuffyMcpServer
✅ scripts.event_bus.EventBus
✅ scripts.orchestrator.Orchestrator
✅ scripts.model_gateway.ModelGateway
✅ scripts.knowledge_engine.KnowledgeEngine
✅ scripts.memory_engine.MemoryEngine
✅ scripts.graph_index.GraphIndex
✅ scripts.tool_runtime.ToolRegistry
✅ scripts.plugin_api.PluginRegistry
✅ scripts.context_manager.ContextManager
```

**Примечание:** `RuntimeRegistry` реализован в `freebuff_plugin/runtime/registry.py`, но не экспортирован из `freebuff_plugin/runtime/__init__.py`. `ScenarioBot` либо переименован, либо отсутствует в `freebuff_plugin/tgbot.py`.

---

## Приложение B: Тестовая сводка

```
1124 passed, 13 warnings in 269.86s
```

| Модуль | Тестов | Покрытие |
|--------|--------|----------|
| Runtime Abstraction | 60 | Высокое |
| Bootstrap Engine | 61 | Высокое |
| Bridge Layer | 60 | Высокое |
| Event Platform | 61 | Высокое |
| Scenario Engine | 83 | Высокое |
| Telegram Bot (tgbot) | 44 | Среднее |
| MCP Server | 101 | Высокое |
| Orchestrator | 51 | Высокое |
| Plugin API | 65 | Высокое |
| Tool Runtime | 53 | Высокое |

---

*Отчёт создан на основе промпта `pompts/AUDIT_PROMPT.md`. Никакие изменения в код не внесены.*
