# Freebuff — Session Checkpoint

**Дата:** 2026-08-03
**Версия проекта:** v5.65.0

> См. [`TASK.md`***REMOVED***(TASK.md) для актуального состояния проекта (v5.65.0). CHANGELOG.md содержит полную историю 41 релиза (v5.21.0 → v5.65.0).
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

1. Прочитать [`TASK.md`***REMOVED***(TASK.md) — полный статус и список open tasks (Phase 5 Flutter UI, см. §5.1/§5.2/§5.3).
2. Прочитать [`CHANGELOG.md`***REMOVED***(CHANGELOG.md) — последние релизы (v5.58.0 Block-A recovery, v5.59.0 CAN-9 final closure).
3. Продолжить работу по [`TASK.md`***REMOVED***(TASK.md) §5.1 (Flutter UI) ИЛИ закрыть долги §5.13–§5.16 ([`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md)).

---

## ✅ Ключевые вехи к v5.59.0 (current state at session-start)

> **Полная история:** см. [`CHANGELOG.md`***REMOVED***(CHANGELOG.md) (38 релизов v5.0.0 → v5.59.0). **Подробный план:** [`TASK.md`***REMOVED***(TASK.md). **Открытые долги:** [`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) §5.13–§5.16.

| Веха | Версия | Тесты |
|------|:------:|------:|
| **LEVIATHAN integration** (Phase A–E + Distributed Agents) | v5.7.0–v5.14.0 | 230 |
| **Phase 0 Close Context Loop + StreamBridge** | v5.15.0 | — |
| **HTTP `/metrics/*` endpoints + Metrics Dashboard** | v5.16.0 / v5.19.0 | — |
| **Phase 7 CoWork Platform** (Presence + Collab + Roles + Project Pulse + RAG 2.0) | v5.17.0–v5.23.0 | — |
| **Phase 4 Plugins** (tg_messenger + system_monitor + knowledge_sync) | v5.20.0 | — |
| **Phase 5.1 MANDATORY RUNTIME CONTRACT + notification.py** | v5.24.0 | 25 |
| **Security audit Шаги 0/1/2** (kill exec/shell + Bearer auth) | v5.25.1 | 132 (75 + 57) |
| **Workspace OS consolidation** (promt32 1–10 + ADR-001…009 + promt36/37 canonical steps) | v5.39.x–v5.42.1 | tests green |
| **TG integration contract + chat_id resolution** | v5.40.0 / v5.42.0 | 26 (13 + 5 + 8) |
| **CAN-8/9/16 closure** (body-level /tmp + e2e locator + counter milestone) | v5.55–v5.59.0 | tests green |
| **Block-A recovery** (`_freebuff_locator.py`) | v5.58.0 | 0 regressions |

> 📜 **Pre-LEVIATHAN history (v3.x–v4.x):** MCP Server (101), Telegram Bot (44), Scenario Engine (83), Bridge Layer (60), Event Platform (61), Bootstrap Engine (61), Bootstrap MCP (12) — captured в `CHANGELOG.md` pre-v5.0 history per **CAN-17 anti-rewriting rule** (audit-trail не переписываем).

---

## 📋 Следующий шаг: Phase 5 Flutter UI (см. [`TASK.md`***REMOVED***(TASK.md))

Консолидация промт32 полностью закрыта (все этапы 1–10 + DEBT-001…007 ✅ Resolved per [`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) §3.1–§3.3). Mission Lock 🔓 снят 2026-08-01. Сейчас в фокусе — единственный user-facing open task:

- **[§5.1 Flutter-приложение***REMOVED***(TASK.md)** — мобильное приложение Freebuff на Flutter (Android).
  - Спецификация: [`pompts_11/039_12_terminal_ai_studio_mobile.md`***REMOVED***(pompts_11/039_12_terminal_ai_studio_mobile.md).
  - Зависимости: §5.2 Foreground Service + §5.3 Remote Sync.
- Альтернативный путь: закрыть долги §5.13–§5.16 ([`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md)) — НЕ блокируют Flutter, повышают docs/tests harmony.
- Пост-консолидационные миссии (отдельный трек): promt42 / promt43 — [`docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md`***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) §9.

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
