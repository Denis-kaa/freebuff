# Freebuff — Session Checkpoint

**Дата:** 2026-08-01
**Версия проекта:** v5.25.1
**Тесты:** см. TASK.md / CHANGELOG.md (актуальный прогон)

> **Единый Core Prompt:** [`docs_10/core/CORE_PROMPT.md`***REMOVED***(docs_10/core/CORE_PROMPT.md) — личность, обязанности, ограничения, поведение.  
> **Стандарт качества:** [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md).  
> Этот файл — сессионный чекпоинт, он **расширяет** Core Prompt.

---

## Книга проекта (Project Book)

**Файл:** `docs_10/engineering-memory/PROJECT_BOOK.md`

Это нарративная память проекта: почему принимались решения, что ломалось, какие кризисы заставляли менять курс и какие уроки остались. При старте каждой сессии агент ДОЛЖЕН ознакомиться с ключевыми главами и использовать Project Book как первичный источник контекста проекта.

**Ключевые главы:**

- **Глава 1. Genesis: FreeBuff 2.0 (2026-07-28)** — исходная архитектура и первые 500+ тестов.
- **Глава 2. Эра протоколов: MCP, HTTP, FastAPI, туннели** — наружние интерфейсы и транспорты.
- **Глава 3. Первый security-кризис: убиваем `exec` и `shell=True`** — почему безопасность стала архитектурой.
- **Глава 4. Реструктуризация v5.0.0** — переход к `docs_10/core/`, `pompts_11/` как контракты.
- **Глава 5. Лавинное наращивание** — метрики, presence, RAG, плагины и дублирование.
- **Глава 6. The July 31 Crisis** — потеря и восстановление `metrics.py` из байткода.
- **Глава 7. Второй security-кризис** — закрытие shell-exec и Bearer auth.
- **Глава 8. Поворот к Workspace OS** — переход от наборов скриптов к операционной среде.
- **Эпилог. Engineering Memory** — зачем нужна внешняя память проекта.

**Как запросить контекст:**

```bash
# Посмотреть оглавление и путь к книге
python freebuff_cli.py project-book

# Прочитать конкретную главу (номер или подстрока)
python freebuff_cli.py project-book "Workspace OS"

# Найти релевантные фрагменты по запросу
python freebuff_cli.py project-context "July 31 Crisis"
```

---

## 🔄 Если Termux перезапустился — скажи "продолжай"

Я продолжу с ТОЧКИ останова. Вот что нужно сделать:

1. Прочитать `TASK.md` — там полный статус и следующие шаги.
2. Прочитать `CHANGELOG.md` — последние изменения (v4.8.0, v4.9.0).
3. Продолжить Phase 1.

---

## ✅ Что уже сделано в этой сессии

| Компонент | Статус | Тесты |
|-----------|--------|-------|
| **AGENTS.md задача** (TMUX_OK) | Выполнена | — |
| **Bootstrap Engine** (6 модулей) | ✅ Реализован, v4.7.0 | 61 тест |
| **Bootstrap MCP интеграция** | ✅ v4.8.0 | 12 тестов |
| **Runtime Abstraction Layer** | ✅ v4.9.0 | 60 тестов |
| **Event Platform** | ✅ v4.7.0 | 61 тест |
| **Bridge Layer** (MCP ↔ ACP) | ✅ v4.6.0 | 60 тестов |
| **Scenario Engine** | ✅ v4.5.0 | 83 теста |
| **Telegram Bot** | ✅ v4.5.0 | 44 теста |
| **MCP Server** | ✅ | 101 тест |

---

## 📋 Следующий шаг: Этап 5 консолидации (promt32) — в работе

Промты 32–36 прочитаны. Статус:
- **Этапы 1–4 промта 32** — ✅ завершены (реестр статусов: `docs_10/DOCUMENT_REGISTRY.md`)
- **Этап 5 (консолидация промтов)** — ✅ завершён: дубль promt34/35 устранён, правила promt36/37 встроены в GLOSSARY/MANIFEST (ADR-008/009), 5 файлов инструкций сверены с Core Prompt
- **Промт 36/37 (Work Area as View)** — ✅ реализован 2026-08-01: `scripts_01/work_area_view.py` (таблица `project_resources`), CLI `freebuff resource projects`, 29 тестов
- **Mission Lock** — 🔓 снят 2026-08-01 (все этапы promt32 1–10 завершены); начаты пост-консолидационные долги: DEBT-001 ✅ Resolved (AGENTS/CLAUDE/CODY в KnowledgeEngine), остались DEBT-002…007

---

## 🔑 Ключевые файлы для продолжения

- `TASK.md` — полный план и статус
- `CHANGELOG.md` — история версий
- `docs_10/DOCUMENT_REGISTRY.md` — статусы документации (Этап 4)
- `docs_10/core/CORE_PROMPT.md` — единый Core Prompt (источник истины)
- `docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md` — roadmap консолидации
- `freebuff_plugin_03/runtime/` — Runtime Abstraction Layer
- `scripts_01/mcp_server.py` — MCP Server (RAL-инструменты уже добавлены: runtime_list/connect/disconnect/select/generate)

---

## ⚡ Быстрые команды

```bash
# Запуск тестов
python -m pytest tests_09/ -q

# Тесты Runtime Abstraction Layer
python -m pytest tests_09/test_runtime_abstraction.py -v

# Тесты MCP Server (включая bootstrap)
python -m pytest tests_09/test_mcp_server.py -v

# Проверка импорта
python -c "from freebuff_plugin.runtime import RuntimeRegistry; print('OK')"
```

---

## 🛡️ CODE QUALITY STANDARD — базовый регламент (обязательно всегда)

> **Источник:** [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md)  
> **Статус:** неприкосновенные правила. Перед любым изменением или созданием кода агент ДОЛЖЕН перечитывать стандарт.  
> **Золотое правило:** если есть выбор между коротким и надёжным решением — всегда выбирать надёжное. Любой созданный код считается **production-ready**.

Кратко:
- **Архитектура:** модульность, минимальная связанность, DRY, понятная структура.
- **Читаемость:** понятные имена, docstrings, README, единый стиль.
- **Надёжность:** обработка ошибок, логирование, идемпотентность, восстановление после сбоя.
- **Безопасность:** без root, секреты в `.env`, валидация ввода, экранирование, никаких произвольных shell-команд.
- **Совместимость:** Termux / Android / ARM64, POSIX-команды.
- **Производительность:** минимум RAM/диска, кэширование.
- **UX:** DEBUG/QUIET, понятный прогресс, `--help`/`--version`, корректные exit-коды.
- **Принципы:** KISS, DRY, SOLID, код, понятный через год.

Полный регламент — в [040_13_code_quality_standard.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md).
