# ADR-024: FreeBuff Manager (FBM) Integration Strategy

> **Статус:** Proposed  
> **Дата:** 2026-08-24  
> **Автор:** Qwen Code (analysis) + Денис (owner decision pending)  
> **Теги:** frontend, tui, integration, mobile-ux  
> **Приоритет:** P2 (после Phase 7 Web UI MVP)

---

## Context

В домашней директории Termux обнаружен проект `~/fbm/` — **FreeBuff Manager**, функциональный TUI (Terminal User Interface) менеджер для Freebuff, написанный на Python с использованием `urwid`.

### Что это такое

FBM — это **легковесная обёртка над Freebuff CLI** с возможностями:

- 🖥️ **PTY-эмулятор** — полноценный VT100 терминал (ANSI colors, 24-bit RGB, wide chars)
- 📋 **Менеджер задач** — очередь задач (pending/running/done) с автоматическим запуском
- 🗂️ **Мультипроекты** — переключение между несколькими Freebuff-проектами
- 🔄 **Auto-continue** — автоматическая отправка "continue" каждые 55 минут (3300 сек)
- 📲 **Уведомления** — Termux notifications + Telegram bot integration
- 👆 **Touch-friendly UI** — свайп-жесты для переключения вкладок (левый/правый свайп)

### Архитектура

```
┌─────────────────────────────────────────────────┐
│            FreeBuff Manager (FBM)                │
│  ~/fbm/ (~800 LOC Python + urwid)               │
├─────────────────────────────────────────────────┤
│  core.py      Config, TaskStore, ProjectStore,  │
│               Notifier, PtyRunner (~180 LOC)    │
│  ui.py        TUI (3 tabs, touch gestures)      │
│               (~340 LOC)                         │
│  vt.py        VT100 emulator (CSI/SGR/OSC)      │
│               (~290 LOC)                         │
│  main.py      Entry point (~20 LOC)             │
└─────────────────────────────────────────────────┘
               │ os.forkpty() → PTY
               ▼
┌─────────────────────────────────────────────────┐
│  proot-distro login ubuntu --                   │
│  cd /storage/.../freebuff &&                    │
│  python3 freebuff_cli.py                        │
└─────────────────────────────────────────────────┘
```

### Хранилище данных

FBM хранит данные в `~/.config/freebuff-manager/`:

```
~/.config/freebuff-manager/
├── config.json     — конфигурация (auto_continue, telegram, delays)
├── tasks.json      — задачи [{id, text, status, created***REMOVED******REMOVED***
├── projects.json   — проекты [{name, cmd***REMOVED******REMOVED***
└── manager.log     — логи
```

### Текущее состояние

- ✅ **Работает** — функциональный TUI для управления Freebuff
- ✅ **Touch-friendly** — свайпы (6 колонок / 2 сек threshold)
- ✅ **Auto-continue** — таймер на 55 минут
- ⚠️ **Не интегрирован** с Freebuff ядром (context.db, memory_engine, workspace_registry)
- ⚠️ **Дублирует логику** — TaskStore в FBM ≠ TASK.md в Freebuff
- ⚠️ **Hardcoded path** — `/home/.config/manicode/freebuff` (исправлено в v5.189.68)
- 🔴 **7 ГБ core dump** — `~/fbm/core` (удалён 2026-08-24)

---

## Decision

Рассмотрены **3 стратегии** интеграции FBM с Freebuff Platform:

### Option A: Standalone Tool (текущее, минимальные изменения)

**Суть:** FBM остаётся отдельным инструментом, не интегрируется в основной проект.

**Изменения:**
1. ✅ Фикс hardcoded path (`core.py:73` — теперь `/storage/.../freebuff`)
2. ✅ Удаление core dump (7 ГБ освобождено)
3. Добавить `~/fbm/README.md` — документация для пользователя
4. Зафиксировать в roadmap как "legacy TUI tool"

**Плюсы:**
- Минимум работы (~1 день)
- Уже работает
- Легковесный (~800 LOC, без зависимостей от Freebuff ядра)
- Подходит для старых устройств (низкий battery drain)

**Минусы:**
- Дублирование логики (TaskStore vs TASK.md)
- Нет доступа к Freebuff memory/context
- Нет синхронизации workspace между FBM и Freebuff
- Нет интеграции с SmartRouter/capability routing

**Подходит, если:**
- Пользователь хочет "простой терминальный wrapper"
- Web UI (Phase 7) станет основным frontend
- FBM используется только для "quick access" или legacy-сценариев

---

### Option B: Integration Layer (REST API bridge)

**Суть:** FBM подключается к Freebuff через REST API, становится официальным TUI frontend.

**Архитектура:**

```
┌──────────────────────┐
│    FBM (TUI)         │
│  urwid + vt.py       │
└──────────┬───────────┘
           │ HTTP REST
           ▼
┌──────────────────────┐
│  Freebuff REST API   │
│  core_02/web_api.py  │  ← расширение mcp_fastapi.py
├──────────────────────┤
│  /workspaces         │
│  /projects           │
│  /tasks              │  ← sync с TASK.md
│  /chat (WebSocket)   │  ← streaming ответы агента
│  /memory             │
└──────────────────────┘
           ▼
┌──────────────────────┐
│  Freebuff Core       │
│  workspace_registry  │
│  memory_engine       │
│  context.db          │
└──────────────────────┘
```

**Изменения:**

1. **Переместить** `~/fbm/` → `/storage/.../freebuff/frontend_18/fbm/`
2. **Расширить REST API:**
   - `core_02/web_api.py` (из `mcp_fastapi.py`)
   - Endpoints: `/workspaces`, `/projects`, `/tasks`, `/chat`, `/memory`
   - WebSocket для real-time chat streaming
3. **Рефакторинг FBM:**
   - Убрать `PtyRunner` (PTY fork)
   - Заменить `TaskStore` → REST API `/tasks` (sync с TASK.md)
   - Заменить `ProjectStore` → REST API `/workspaces`
   - Добавить WebSocket client для chat
4. **Унифицировать конфиг:**
   - `~/.config/freebuff-manager/config.json` → `core_02/workspace_registry.py`
   - Auto-continue интеграция с `scripts_01/auto_continue.sh`
5. **Тесты:**
   - `tests_09/frontend/test_fbm_api_client.py` (~30 тестов)

**Плюсы:**
- Единая source-of-truth (context.db, memory_engine)
- Задачи синхронизированы с TASK.md
- Доступ к SmartRouter/capability routing
- Можно использовать как альтернативу Web UI (для терминальных энтузиастов)
- Touch-friendly + low battery drain

**Минусы:**
- Средняя трудоёмкость (~2-3 недели)
- Зависимость от REST API (нужен запущенный backend)
- Потеря "standalone" режима (нельзя запустить FBM без Freebuff backend)

**Подходит, если:**
- FBM должен стать официальным TUI frontend
- Нужна альтернатива Web UI для терминальных сессий
- Пользователь готов запускать backend (`freebuff web start`)

---

### Option C: Replace with Web UI (deprecate FBM)

**Суть:** Отказаться от FBM в пользу React Web UI (Phase 7 roadmap).

**План:**

1. FBM остаётся как legacy tool (Option A фикс: hardcoded path + README)
2. Phase 7: Web UI становится основным frontend (React + TypeScript + PWA)
3. После Web MVP (Q1 2027): FBM deprecated, README → "use Web UI instead"
4. Phase 10 (Q4 2027): Flutter Mobile заменяет оба (Web UI + FBM)

**Плюсы:**
- Нет дублирования работы (фокус на Web UI)
- Web UI лучше для accessibility (screen reader, keyboard nav)
- PWA работает как mobile app (Add to Home Screen)
- Единая кодовая база (React) для Web + будущего Flutter

**Минусы:**
- Потеря TUI (терминальные энтузиасты останутся без UI)
- Web UI тяжелее (battery drain выше чем TUI)
- FBM уже работает, а Web UI ещё нет (MVP — Q1 2027)

**Подходит, если:**
- Пользователь не планирует использовать TUI долгосрочно
- Web UI (Phase 7) — основной приоритет
- Battery drain не критичен (или есть foreground service, Phase 10)

---

## Recommended Decision

**Рекомендация:** **Option A (Standalone Tool)** + потенциальный переход к **Option B** после Phase 7 MVP.

### Обоснование

1. **FBM уже работает** — зачем ломать работающий инструмент до появления альтернативы (Web UI).
2. **Минимальная трудоёмкость** — фикс hardcoded path (✅ done) + README (~1 день).
3. **Web UI — приоритет** (Phase 7, Q1 2027) — фокус на React MVP, а не на TUI интеграцию.
4. **Гибкость** — после Web MVP можно пересмотреть:
   - Если Web UI успешен → Option C (deprecate FBM).
   - Если TUI востребован → Option B (интеграция через REST API).

### Implementation Plan (Option A)

**Immediate (done 2026-08-24):**
- ✅ Удалить `~/fbm/core` (7 ГБ core dump)
- ✅ Фикс hardcoded path в `core.py` (`/storage/.../freebuff`)

**Short-term (1 день):**
- [ ***REMOVED*** Создать `~/fbm/README.md` — как запустить, hotkeys, конфигурация
- [ ***REMOVED*** Добавить в roadmap как "FBM (TUI legacy tool)"
- [ ***REMOVED*** Зафиксировать в `CHANGELOG.md` v5.189.68:
  ```
  ### 🔧 External Tools
  - FreeBuff Manager (FBM) — обнаружен legacy TUI wrapper в ~/fbm/
    - Удалён core dump (7 ГБ)
    - Исправлен hardcoded path → /storage/.../freebuff
    - ADR-024: Integration Strategy (Option A: Standalone)
  ```

**Mid-term (после Phase 7 MVP, Q2 2027):**
- [ ***REMOVED*** Review: сколько пользователей используют FBM vs Web UI
- [ ***REMOVED*** Decision: Option B (integrate) или Option C (deprecate)

---

## Alternatives Considered

### Alt 1: Port FBM to React Native (вместо urwid)

**Проблема:** React Native требует Metro bundler, не работает в чистом Termux без patch.

**Вывод:** Не рассматривается до Phase 10 (Flutter Mobile).

### Alt 2: FBM как MCP tool (вместо REST API)

**Проблема:** MCP — для инструментов, вызываемых агентом, а не для UI.

**Вывод:** Некорректное использование MCP protocol.

### Alt 3: Embed FBM в Freebuff CLI (single binary)

**Проблема:** urwid + vt.py — тяжёлые зависимости для CLI, который должен быть быстрым.

**Вывод:** TUI и CLI должны быть раздельными.

---

## Trade-offs

| Аспект | Option A (Standalone) | Option B (Integration) | Option C (Replace) |
|--------|----------------------|------------------------|-------------------|
| **Трудоёмкость** | 🟢 1 день | 🟡 2-3 недели | 🟢 1 день + Phase 7 |
| **Source-of-truth** | 🔴 Дубли (TaskStore ≠ TASK.md) | 🟢 Единый (context.db) | 🟢 Единый (Web UI) |
| **Accessibility** | 🔴 Нет screen reader | 🔴 Нет screen reader | 🟢 Radix UI |
| **Battery drain** | 🟢 Низкий | 🟢 Низкий | 🟡 Средний (PWA) |
| **Touch-friendly** | 🟢 Свайпы | 🟢 Свайпы | 🟢 Full touch |
| **Offline mode** | 🟢 Полный | 🔴 Нужен backend | 🟡 PWA cache |
| **Долгосрочность** | 🔴 Legacy tool | 🟢 Официальный TUI | 🟢 Основной UI |

---

## Consequences

### If Option A (Recommended)

**Immediate:**
- FBM остаётся работающим инструментом для "quick TUI access"
- Нет дублирования работы (фокус на Web UI, Phase 7)
- Hardcoded path исправлен, core dump удалён

**Short-term (Phase 7):**
- Web UI становится основным frontend
- FBM — альтернатива для терминальных сессий

**Long-term (после Phase 7 MVP):**
- Decision point: интегрировать (Option B) или deprecate (Option C)
- Если FBM не используется → deprecate
- Если востребован → интегрировать через REST API

### If Option B

**Immediate:**
- Нужна REST API extension (web_api.py)
- Рефакторинг FBM (убрать PTY, добавить HTTP client)

**Short-term:**
- FBM становится официальным TUI frontend
- Задачи синхронизированы с TASK.md

**Long-term:**
- Поддержка двух UI (TUI + Web) → двойная трудоёмкость

### If Option C

**Immediate:**
- FBM deprecated, пользователи переходят на CLI
- Потеря touch-friendly TUI до Phase 7

**Short-term:**
- Web UI — единственный UI (кроме CLI)

**Long-term:**
- Единая кодовая база (React → Flutter)

---

## Verification

**Acceptance Criteria (Option A):**

- [ ***REMOVED*** `~/fbm/core` удалён (7 ГБ освобождено) ✅ **done 2026-08-24**
- [ ***REMOVED*** `~/fbm/core.py` фикс hardcoded path ✅ **done 2026-08-24**
- [ ***REMOVED*** `~/fbm/README.md` создан (как запустить, hotkeys)
- [ ***REMOVED*** ADR-024 зафиксирован в `docs_10/decisions/DECISIONS.md`
- [ ***REMOVED*** CHANGELOG.md v5.189.68 включает FBM-секцию
- [ ***REMOVED*** ROADMAP обновлён: FBM как "legacy TUI tool"

**Test Plan:**

```bash
# 1. Запуск FBM
cd ~/fbm && python3 main.py

# 2. Проверка вкладок
# Tab → FreeBuff / Задачи / Проекты

# 3. Добавление задачи
# 'a' → введите "test task" → Enter

# 4. Запуск задачи
# Tab → Задачи → Enter на задаче

# 5. Auto-continue
# F9 → "continue" отправлен в Freebuff

# 6. Свайп-жест (на Android touch)
# Свайп вправо → следующая вкладка
```

---

## References

- **FBM Source:** `~/fbm/` (~800 LOC: core.py, ui.py, vt.py, main.py)
- **Freebuff Platform:** `/storage/emulated/0/PROJECTS/workstation/freebuff/`
- **Phase 7 Roadmap:** `docs_10/vision/ROADMAP_2026_2027.md` §7 (Web UI MVP)
- **Phase 10 Roadmap:** `docs_10/vision/ROADMAP_2026_2027.md` §10 (Flutter Mobile)
- **Related ADR:** ADR-020 (Integration Adapter Boundary)

---

## История

- **v1.0 (2026-08-24):** Initial ADR — Option A (Standalone) рекомендован, Option B/C рассмотрены.
