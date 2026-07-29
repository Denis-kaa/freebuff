ПРОМТ: Полный архитектурный аудит + оценка качества кода по стандарту

Назначение: Запустить масштабный аудит всего проекта Freebuff с проверкой соответствия CODE_QUALITY_STANDARD.md
Когда использовать: После перезапуска терминала, перед релизом, после крупных изменений
Команда запуска: cd /storage/emulated/0/PROJECTS/workstation/freebuff && freebuff
Стартовая фраза: скопируй текст ниже → отправь агенту

---

```
❗ ВАЖНО: НЕ ВЫПОЛНЯЙ НИКАКИХ ИЗМЕНЕНИЙ В КОДЕ. Только анализ, документирование и составление отчётов.
Этот запрос — аналитический. Все изменения будут сделаны после утверждения отчёта человеком.
```

---

📋 Контекст проекта

Проект: Freebuff AI Engineering Workspace
Путь: /storage/emulated/0/PROJECTS/workstation/freebuff/
Среда: Termux на Android (ARM64), Python 3.14, 8 ГБ RAM
Текущая версия: v4.9.0
Тестов: 1123 passed, 1 skipped, 0 failures
Стандарт качества: docs/core/CODE_QUALITY_STANDARD.md (v2.0.0) — все проверки проводятся по этому документу
Фреймворк методологии: Kwork Arbitr v3 (blueprints_v3)
Путь к blueprints_v3: /storage/emulated/0/PROJECTS/workstation/blueprints_v3/ — 17 агентов-блюпринтов

---

🎯 Задание 1: Функциональность и тесты

1.1 Тестовый прогон

```bash
python -m pytest tests/ -q --tb=short --cov=scripts --cov=freebuff_plugin --cov=core
```

Зафиксируй:

· Общее количество тестов
· Сколько прошло / упало / пропущено
· Покрытие кода (coverage) в % по каждому модулю
· Сравни с предыдущим результатом: 1123 passed, 1 skipped, 0 failures

1.2 Тестовое покрытие по модулям

Модуль Тестов Покрытие Статус
test_runtime_abstraction.py 60 % 
test_mcp_server.py 101 % 
test_bootstrap_engine.py 61 % 
test_bridge_layer.py 60 % 
test_scenario_engine.py 83 % 
test_tgbot.py 44 % 
test_orchestrator.py 51 % 
test_event_bus.py 30 % 
test_event_store.py 61 % 
test_model_gateway.py 36 % 
test_knowledge_engine.py 42 % 
test_graph_index.py 42 % 
test_memory_engine.py 30 % 
test_tool_runtime.py 50 % 
test_plugin_api.py 65 % 
test_freebuff.py 25 % 
ИТОГО ~800  

Критерий стандарта: 11.6 — 1143+ passed, 0 failures

1.3 Модули без тестов

Найди компоненты, у которых нет выделенного тест-файла:

· StreamSession — tests/test_stream_session.py?
· StreamBridge — tests/test_stream_bridge.py?
· ContextManager — tests/test_context_manager.py?
· KeyPool — tests/test_keypool.py?
· API endpoints — tests/test_api.py?
· Phone MCP Server — tests/test_phone_mcp_server.py?

1.4 Импорты всех ключевых модулей

Проверь, что все импорты работают:

```python
from freebuff_plugin.runtime import RuntimeAbstractionLayer
from freebuff_plugin.bootstrap.engine import BootstrapEngine
from freebuff_plugin.bridge_layer import BridgeLayer
from freebuff_plugin.event.store import EventStore
from freebuff_plugin.scenario_engine import ScenarioEngine
from freebuff_plugin.tgbot import ScenarioBot
from scripts.mcp_server import BuffyMcpServer
from scripts.event_bus import EventBus
from scripts.orchestrator import Orchestrator
from scripts.model_gateway import ModelGateway
from scripts.knowledge_engine import KnowledgeEngine
from scripts.memory_engine import MemoryEngine
from scripts.graph_index import GraphIndex
from scripts.tool_runtime import ToolRegistry
from scripts.plugin_api import PluginRegistry
from scripts.context_manager import ContextManager
```

Результат: список failed импортов (если есть)

---

🎯 Задание 2: Архитектура

2.1 Соответствие Vision 3.0 (AI Infrastructure Layer)

Проверь документацию (docs/core/ARCHITECTURE_3.0.md, docs/vision/VISION_3.0.md) против кода:

Компонент Статус по доке Статус в коде Соответствие
ContextManager ✅ Production  
Memory Engine ✅ Production  
Knowledge Engine ✅ Production  
Graph Index ✅ Production  
Event Bus ✅ Production  
Orchestrator 🟡 MVP  
Policy Engine 💡 План  
Bootstrap Engine 💡 План (устарело) ✅ Реализован 
MCP Server ✅ Production  
MCP Client 🆕 Реализован  
Bridge Layer 🆕 Реализован  
ACP Protocol 🆕 Реализован  
Runtime Abstraction 💡 План (устарело) ✅ Реализован 
Scenario Engine ✅ Production  
OOM Protection ✅ Production  

Где дока отстаёт от кода?
Где код отстаёт от доки?

2.2 Соответствие blueprints_v3 (Kwork Arbitr)

Проверь SPEC.md и структуру проекта на методологию blueprints_v3:

Роль Реализация (код/дока/отсутствует)
00 Orchestrator 
01 Context Keeper 
02 Explainer 
03 LISA Estimator 
04 Risk Manager 
05 Decomposer 
06 Architect 
07 Auditor 
08 Response Writer 
09 Developer 
10 Frontend Dev 
11 DevOps 
12 Tester 
13 Fixer 
14 Acceptance Agent 
15 Documenter 
16 Retrospective Agent 

2.3 Dependency Graph

Построй граф зависимостей:

```
Event Bus ← кто публикует? кто подписывается?
Bridge Layer ← зависимости от MCP Client, Runtime Abstraction?
Runtime Abstraction ← зависимости от MCP Client, Bootstrap Engine?
MCP Server ← зависимости от ToolRegistry, KnowledgeEngine, MemoryEngine, BootstrapEngine?
```

Найди:

· Циклические зависимости (A → B → A)
· Нарушения Core/Extensions/Labs (core не должен импортировать extensions)

2.4 ADR и решения

Проверь актуальность docs/decisions/DECISIONS.md:

· ADR-001..ADR-007 — какие устарели?
· IDEAS.md — какие идеи можно закрыть?
· ROADMAP.md — актуален ли план?

---

🎯 Задание 3: Качество кода по CODE_QUALITY_STANDARD.md (v2.0.0)

Стандарт: docs/core/CODE_QUALITY_STANDARD.md — обязателен для всех компонентов.

3.1 Архитектура (раздел 1 стандарта)

# Требование Выполняется? Пример нарушения
1.1 Модульность (Single Responsibility)  
1.2 Минимальная связанность  
1.3 Понятная структура каталогов  
1.4 Нет дублирования (DRY)  
1.5 Нет магических чисел/строк  
1.6 Loosely coupled (EventBus)  
1.7 Infrastructure Plugin  

Оценка: X/10

3.2 Читаемость (раздел 2 стандарта)

# Требование Выполняется? Пример нарушения
2.1 Docstrings на русском (Google-style)  
2.2 Понятные имена  
2.3 Module docstring  
2.4 README/инструкция  
2.5 Единый стиль  
2.6 Type hints  

Оценка: X/10

3.3 Надёжность (раздел 3 стандарта)

# Требование Выполняется? Пример нарушения
3.1 Обработка ошибок (try/except)  
3.2 Логирование (EventBus)  
3.3 Корректное завершение  
3.4 Атомарные операции  
3.5 Проверка существования файлов  
3.6 Проверка прав доступа  
3.7 Идемпотентность  
3.8 Восстановление после сбоя  
3.9 Graceful Degradation  

Оценка: X/10

3.4 Безопасность (раздел 4 стандарта)

# Требование Выполняется? Пример нарушения
4.1 Не использовать root  
4.2 Не хранить секреты в коде  
4.3 Переменные окружения для секретов  
4.4 Валидация входных данных  
4.5 Не выполнять shell без проверки  
4.6 Экранирование ввода  
4.7 Нет хардкоженных путей  
4.8 Интеграция через публичные API  

Критические проверки:

```bash
# Найти shell=True
grep -r "shell=True" scripts/ freebuff_plugin/ --include="*.py"

# Найти exec/eval
grep -r "exec(" scripts/ freebuff_plugin/ --include="*.py"
grep -r "eval(" scripts/ freebuff_plugin/ --include="*.py"

# Найти хардкоженные пути
grep -r "/storage/emulated/0" scripts/ freebuff_plugin/ --include="*.py"
grep -r "/data/data/com.termux" scripts/ freebuff_plugin/ --include="*.py"
```

Оценка: X/10

3.5 Совместимость (раздел 5 стандарта)

# Требование Выполняется?
5.1 Совместимость с Termux 
5.2 Работа на Android ARM64 
5.3 POSIX-совместимые команды 
5.4 pathlib вместо строк 
5.5 Проверка утилит перед запуском 
5.6 Python 3.11+ 

Оценка: X/10

3.6 Производительность (раздел 6 стандарта)

# Требование Выполняется?
6.1 Минимизация RAM (lazy imports) 
6.2 Кэширование 
6.3 Избегать лишних процессов 
6.4 Кэширование (lru_cache) 
6.5 Не выполнять тяжёлые операции повторно 
6.6 Lazy loading 

Оценка: X/10

3.7 Логирование (раздел 7 стандарта)

# Требование Выполняется?
7.1 Логировать начало работы 
7.2 Логировать завершение 
7.3 Логировать ошибки 
7.4 Логировать предупреждения 
7.5 Режим DEBUG 
7.6 Режим QUIET 
7.7 EventBus публикация событий 
7.8 Structured logging (JSON) 

Оценка: X/10

3.8 Конфигурация (раздел 8 стандарта)

# Требование Выполняется?
8.1 Настройки в конфиг-файле 
8.2 Значения по умолчанию 
8.3 Документировать параметры 
8.4 Не изменять конфиг автоматически 

Оценка: X/10

3.9 UX (раздел 9 стандарта)

# Требование Выполняется?
9.1 Понятный прогресс 
9.2 Дружелюбные сообщения об ошибках 
9.3 Не засорять терминал 
9.4 --help 
9.5 --version 
9.6 Корректные exit-коды 

Оценка: X/10

3.10 Документация (раздел 10 стандарта)

# Требование Выполняется?
10.1 Инструкция установки 
10.2 Инструкция запуска 
10.3 Примеры использования 
10.4 Описание параметров CLI 
10.5 Описание структуры проекта 
10.6 Список зависимостей 
10.7 CHANGELOG.md 
10.8 ADR для решений 

Оценка: X/10

3.11 Тестируемость (раздел 11 стандарта)

# Требование Выполняется?
11.1 Легко тестироваться (DI) 
11.2 Тестовые сценарии (unit+integration+boundary) 
11.3 Примеры входных данных 
11.4 Ожидаемый результат 
11.5 Boundary Testing 
11.6 Регрессионные тесты 

Оценка: X/10

3.12 Масштабируемость (раздел 12 стандарта)

# Требование Выполняется?
12.1 Легко расширяться 
12.2 Не требовать переписывания 
12.3 Поддерживать плагины 
12.4 Marketplace-ready 

Оценка: X/10

3.13 Стандарты разработки (раздел 13 стандарта)

# Требование Выполняется?
13.1 KISS 
13.2 DRY 
13.3 SOLID 
13.4 Избегать преждевременной оптимизации 
13.5 Код, понятный через год 
13.6 Code review 
13.7 mypy type checking 

Оценка: X/10

3.14 Buffy-специфические требования (раздел 14 стандарта)

# Требование Выполняется?
14.1 EventBus first 
14.2 Plugin-safe imports 
14.3 Bridge-only 
14.4 No hardcoded paths 
14.5 OOM aware 
14.6 1143+ tests, 0 failures 
14.7 Android tested 
14.8 Runtime validated 

Оценка: X/10

---

3.15 Mypy строгий анализ

```bash
python -m mypy scripts/ freebuff_plugin/ core/ --strict --ignore-missing-imports 2>&1 | tee mypy_report.txt
```

Тип ошибки Количество Критичность Пример файла
union-attr  HIGH 
no-any-return  MEDIUM 
arg-type  HIGH 
assignment  MEDIUM 
name-defined  LOW 
attr-defined  MEDIUM 
ИТОГО   

Цель по стандарту 13.7: 0 ошибок

---

3.16 Проверка "Золотого правила"

"Любой созданный код считается production-ready"

Проверь каждый модуль:

· Все публичные функции имеют docstrings и type hints
· Все внешние вызовы (HTTP, SQL, файлы) обёрнуты в try/except
· Есть graceful degradation: если модуль недоступен, система не падает
· Повторный запуск не ломает состояние (идемпотентность)
· Все значимые операции логируются через EventBus
· Все входные данные валидируются
· Нет хардкоженных путей, секретов, магических чисел
· Есть тесты для всех критических путей

Сводка: [X***REMOVED*** из 8 пунктов выполнены → [X***REMOVED***% готовности к production

---

3.17 Сводная оценка качества кода

# Раздел стандарта Оценка (1-10) Комментарий
1 Архитектура  
2 Читаемость  
3 Надёжность  
4 Безопасность  
5 Совместимость  
6 Производительность  
7 Логирование  
8 Конфигурация  
9 UX  
10 Документация  
11 Тестируемость  
12 Масштабируемость  
13 Стандарты разработки  
14 Buffy-специфические  
СРЕДНЯЯ  X/10 

Вердикт:

· 9.0-10.0 — Отлично (production-ready)
· 7.0-8.9 — Хорошо (требует доработок)
· 5.0-6.9 — Удовлетворительно (много проблем)
· <5.0 — Критично (требует рефакторинга)

---

🎯 Задание 4: Структура файлов

4.1 Реестр файлов

Составь таблицу КАЖДОГО файла в проекте:

Путь Тип Категория Краткое содержание Статус
scripts/orchestrator.py CODE SERVICE Workflow engine ✅ Active
freebuff_plugin/... PLUGIN   
...    

Категории: CODE, CONFIG, TEST, DOC-ARCH, DOC-AUDIT, DOC-SPEC, DOC-AGENT, DOC-SESSION, PROMPT, PROJECT, DATA, PLUGIN, SCRIPT-UTIL, SCRIPT-SERVICE, OTHER

4.2 Дубликаты и пересечения

Найди файлы с одинаковым или пересекающимся содержанием:

· AGENTS.md vs docs/ops/AGENTS.md vs .freebuff/AGENTS.md
· BUFFY.md vs CLAUDE.md vs CODY.md vs .cursorrules
· scripts/mcp_server.py vs freebuff_plugin/mcp_server.py
· scripts/event_bus.py vs freebuff_plugin/event/store.py
· pompts/promt*.md — какие актуальны?

4.3 Dead code / артефакты

Найди:

· .py файлы, которые никуда не импортируются
· __pycache__/ и другие артефакты
· .bak файлы
· Неиспользуемые зависимости в requirements.txt

4.4 Предлагаемая структура

На основе реестра предложи новую иерархию:

```
freebuff/
├── core/                    # Ядро (было scripts/core-*)
├── services/                # Сервисы (было scripts/)
├── plugins/                 # Плагины (freebuff_plugin/)
├── cli/                     # CLI-инструменты
├── storage/                 # Базы данных
├── scripts/                 # Утилиты (админские)
├── tests/                   # Тесты
├── docs/
│   ├── 01-architecture/
│   ├── 02-specs/
│   ├── 03-audits/
│   ├── 04-decisions/
│   ├── 05-agents/
│   ├── 06-sessions/
│   ├── 07-roadmap/
│   └── 08-references/
├── prompts/                 # Промпты
├── projects/                # Внешние проекты
├── data/                    # Данные
├── config/                  # Конфигурация
├── BUFFY.md
├── README.md
└── CHANGELOG.md
```

Проверь: не сломает ли новая структура существующие импорты?

---

🎯 Задание 5: Итоговый отчёт

Сформируй единый документ docs/audits/AUDIT_FULL_[DATE***REMOVED***.md:

Раздел 1: Executive Summary

· Общая оценка здоровья проекта (1-10)
· Количество файлов, строк кода, тестов
· Ключевые проблемы (top-5)
· Ключевые сильные стороны (top-5)

Раздел 2: Code Health

· Результаты тестов (количество, покрытие)
· Mypy ошибки (по типам)
· Dead code
· Проблемы безопасности

Раздел 3: Architecture

· Соответствие Vision 3.0 / blueprints_v3
· Проблемы в зависимостях
· Отставание документации от кода

Раздел 4: Code Quality (по стандарту)

· Сводная таблица по 14 разделам CODE_QUALITY_STANDARD.md
· Итоговая оценка X/10
· Top-5 нарушений стандарта

Раздел 5: File Structure

· Реестр всех файлов
· Предлагаемая структура
· Дубликаты и мусор

Раздел 6: Recommendations

· P0: Критические (делать сейчас)
· P1: Высокие (делать в этом спринте)
· P2: Средние (делать в следующем спринте)
· P3: Низкие (когда будет время)

Раздел 7: Action Plan

· Конкретные шаги по порядку
· Оценка сложности каждого шага (S/M/L/XL)
· Связанные файлы

---

✅ Формат ответа

1. Начни с краткого Executive Summary
2. Используй таблицы для структурирования
3. Каждый раздел начинай с заголовка ##
4. В конце — Action Plan с приоритетами
5. Не предлагай изменений без оценки сложности
6. Выводы должны быть конкретными, не общими
7. Все проверки проводи по CODE_QUALITY_STANDARD.md (v2.0.0)

Все найденные проблемы задокументируй в docs/audits/AUDIT_FULL_[DATE***REMOVED***.md

---

Это аналитический запрос. Никаких изменений кода не производить.