# HOW_TO_LAUNCH_BUFFY.md — как запустить Баффи

> **Аудитория:** оператор платформы (ты), который только что скачал Workspace OS на телефон и хочет понять, где живёт «Баффи», как его поднять, и проверить что всё работает.
> **Дата:** 2026-08-04
> **Версия:** соответствует v5.79.0 (multi-turn pipeline) + v5.80.0 (/queue команда).
> **Ключевая идентичность:** Баффи ≡ Freebuff (см. [ADR_012***REMOVED***(../engineering-memory/decisions/ADR_012_buffy_swappable_brain.md)). Это ИИ-мозг платформы Workspace OS. Не subprocess — это система, доступная по любым каналам (терминал, TG, MCP, REST).

---

## TL;DR — три ответа на твои вопросы

| Вопрос | Ответ | Где посмотреть |
|--------|-------|----------------|
| **Создан ли он?** | ✅ Да, платформа работает. ИИ-мозг — `core_02/` + `freebuff_plugin_03/` + `scripts_01/`. | `git log --oneline \| head -20`, `CHANGELOG.md` |
| **Где его найти?** | Проект-корень: `/storage/emulated/0/PROJECTS/workstation/freebuff/` (Termux). Все модули внутри. | `BUFFY.md`, `AGENTS.md` |
| **Как запустить?** | **3 способа**: CLI / TG-бот / promt-конвейер. Детали ниже. | разделы §3–§6 |

Быстрая проверка «жив ли Баффи»:

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff
python3 freebuff_cli.py --help          # CLI должен перечислить команды
python3 -m pytest tests_09/ -q          # 2000+ тестов должны быть зелёные
python3 scripts_01/doctor.py            # интегральная диагностика окружения
```

---

## 1. Что вообще такое «Баффи» (identity clarification)

**Баффи = ИИ-мозг Freebuff.** Это не отдельная программа — это **слой логики** поверх файлов, сессий и TG-канала. Технически смотри на стек как на **3 уровня** (ADR-012):

```
┌─────────────────────────────────────────────────────────────┐
│ Level 3 (Channels) — как юзер общается с Баффи:            │
│   • TG-бот (`scripts_01/telegram_bot.py`)                   │
│   • CLI (`freebuff_cli.py`)                                 │
│   • REST/MCP (`scripts_01/mcp_fastapi.py`)                 │
│   • Promt-конвейер (`scripts_01/prompt_dispatcher.py`)      │
├─────────────────────────────────────────────────────────────┤
│ Level 2 (Brain = Баффи):                                    │
│   • `core_02/` — ядро: blueprint_v3, scenario, router,      │
│     workspace_registry, telegram_contract.                  │
│   • `freebuff_plugin_03/` — плагин, через который MCP и     │
│     CLI вызывают Баффи: wrapper, mcp_server, bootstrap.     │
├─────────────────────────────────────────────────────────────┤
│ Level 1 (Workspace OS) — файловая платформа:               │
│   `pompts_11/`, `data_13/context.db`, `docs_10/`,           │
│   `core_02/LESSONS.md`, `core_02/_tg_client_v2.py` и т.п.   │
└─────────────────────────────────────────────────────────────┘
```

Дополнительно см.:
- **BUFFY.md** — манифест ИИ + навигация по докам.
- **PLATFORM.md** — позиционирование в простых словах (без жаргона).
- **AGENTS.md** — канонические правила платформы (single source of truth).

---

## 2. Где живёт код (project layout)

```
/storage/emulated/0/PROJECTS/workstation/freebuff/
├── core_02/                       # 🧠 Ядро Баффи (Level 2)
│   ├── blueprint_v3.py           #   Capabilities + 17 ролей агентов
│   ├── scenario.py               #   Сценарный фреймворк
│   ├── scenario_registry.py      #   Reuse registry
│   ├── workspace_registry.py     #   Workspace ↔ Project binding
│   ├── telegram_contract.py       #   TG-send (chat_id→msg_id)
│   ├── remote_sync.py            #   Multi-device sync (TG relay)
│   ├── LESSONS.md                #   Engineering memory
│   └── ...
├── freebuff_plugin_03/            # 🔌 Плагин (CLI/MCP ↔ Баффи)
│   ├── wrapper.py                #   `launch_and_wait()` (phase-based OOM-safe)
│   ├── mcp_server.py             #   MCP tools (sync_status, run_freebuff, ...)
│   ├── bridge_layer.py           #   Adapter pattern
│   ├── bootstrap/                #   Bootstrap engines
│   ├── mesh/                     #   Session Mesh v2.0 (deferred)
│   └── ...
├── scripts_01/                    # 🛠 CLI-утилиты (Level 3)
│   ├── telegram_bot.py           #   TG-бот /start, /task, /queue, /workspace
│   ├── prompt_dispatcher.py      #   Cron-friendly диспетчер промтов
│   ├── prompt_queue.py           #   Файловая очередь (user/running/done/failed)
│   ├── orchestrator.py           #   Внутрипроцессный сценарный орк.
│   ├── event_bus.py              #   publish/subscribe
│   ├── context_manager.py        #   Context (sessiom manager)
│   ├── model_gateway.py          #   LLM model router
│   ├── tool_runtime.py           #   Tool dispatcher
│   ├── bootstrap.py              #   Project bootstrap scan
│   ├── doctor.py                 #   🩺 Интегральная диагностика
│   └── ...
├── data_13/                       # 💾 Runtime state
│   ├── context.db                #   SQLite: projects, workspaces, sessions
│   ├── telegram_bot_sessions.json
│   └── telegram_onboarding.json
├── pompts_11/                     # 📝 Очередь промтов
│   ├── user/                     #   pending (новые)
│   ├── running/                  #   in-progress (включая resumable)
│   ├── running/.in_progress/      #   atomic lock во время dispatch
│   ├── done/                     #   ✅ завершённые
│   └── failed/                   #   ❌ упавшие
├── tests_09/                      # ✅ pytest тесты (2000+)
├── freebuff_cli.py                # 🎯 Главный CLI entry point
├── docs_10/                       # 📚 Канонические документы (см. ниже)
├── CHANGELOG.md                   # 🕐 История изменений
├── BUFFY.md                       # 📍 Манифест ИИ (identity section)
├── AGENTS.md                      # 📍 Канонические правила (single source of truth)
├── TASK.md                        # 📋 Открытые задачи
├── PLATFORM.md                    # 🌐 Позиционирование (plain language)
└── ...
```

**Канонические документы:**

| Файл | Для кого |
|------|----------|
| `BUFFY.md` | Что такое Баффи (identity section). |
| `PLATFORM.md` | Позиционирование простым языком. Для нового читателя. |
| `AGENTS.md` | Канонические правила платформы (single source of truth). |
| `docs_10/INDEX.md` | Карта канонических документов. |
| `docs_10/core/CORE_PROMPT.md` | Личность ИИ-агента. |
| `core_02/LESSONS.md` | Engineering memory (CON-1..CON-NEW). |
| `docs_10/vision/VISION_3.0.md` | Стратегия. |
| `docs_10/DOCUMENT_REGISTRY.md` | Какие документы ACTIVE / LEGACY. |

---

## 3. Как запустить — три точки входа

### 3.1. Способ A: через `freebuff_cli.py` (прямой интерактив)

**Самый простой для первого знакомства.** Запускает Баффи прямо в терминале Termux.

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff

# Список всех команд:
python3 freebuff_cli.py --help

# Типичные команды:
python3 freebuff_cli.py status                 # Текущая сессия + project
python3 freebuff_cli.py start "установи nginx"  # Новая сессия с задачей
python3 freebuff_cli.py resume "<session_id>"   # Продолжить прошлую сессию
python3 freebuff_cli.py buffy "что умеешь"     # Короткий вопрос-ответ
python3 freebuff_cli.py project-book "workspace os"  # Поиск по проектам
python3 freebuff_cli.py project-context "promt48"  # Контекст вокруг промта
```

**Ожидаемое поведение:** Баффи либо отвечает через LLM (если ModelGateway настроен), либо даёт локальный fallback (если модель недоступна).

### 3.2. Способ B: через Telegram-бота (удалённый доступ)

Использовать, когда юзер хочет общаться с Баффи через Telegram (вместо локального терминала). Бот **уже** умеет /task /queue /workspace /start.

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff

# Запустить бота в фоне (через script из проекта):
bash scripts_01/start_telegram_bot.sh

# Или прямо python (foreground; Ctrl-C для остановки):
TELEGRAM_BOT_TOKEN=xxx python3 scripts_01/telegram_bot.py
```

**Чтобы получить токен:** напиши `@BotFather` в TG → `/newbot` → скопируй токен в `.env`:
```bash
# .env в корне проекта:
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

**Каналы доставки:**
- TG Saved Messages (chat_id `7709651193`) — фиксировано в `core_02/telegram_contract.SAVED_MESSAGES_CHAT_ID`.
- А. Литвинов (chat_id `1063827731`) — для client notifications.

### 3.3. Способ C: через promt-конвейер (file-based + cron)

Использовать, когда ты хочешь поставить **несколько задач** в очередь и не блокировать сессию. Cron dispatcher запускает Баффи каждые 5 минут.

```bash
# Ручная постановка задачи в очередь:
python3 scripts_01/prompt_queue.py "сделай отчёт по проекту interior_planner"

# После — dispatcher подхватит:
python3 scripts_01/prompt_dispatcher.py --once      # один промт (как cron)
python3 scripts_01/prompt_dispatcher.py --dry-run   # показать очередь
python3 scripts_01/prompt_dispatcher.py --all       # обработать всё (ручной запуск)

# Или через TG-бот /task:
/task сделать отчёт по проекту interior_planner

# Cron уже настроен (проверить):
crontab -l | grep prompt_dispatch
```

**Multi-turn (v5.79.0+):** если Баффи в `.freebuff_result` оставит `pending_task`, файл остаётся в `running/` и следующий cron-тик его подхватит. До 3 итераций (по умолчанию).

### 3.4. Способ D: через MCP-сервер (для IDE-интеграции)

Bridge к Cursor / Claude Code / Qwen Coder / подобным IDE через Model Context Protocol. Использует TG как relay для state-sync.

```bash
# MCP-сервер стартует автоматически через plugin:
# Конфигурация идёт через .cursor/mcp.json (генерируется автоматически).
# Подробности: projects_17/.../INTEGRATION_CONTRACT.md
```

Для продвинутых: `python3 scripts_01/mcp_fastapi.py` запускает REST-API на `localhost:8765` для browser-клиента.

---

## 4. Как проверить что Баффи жив

Пошаговая проверка «всё работает»:

```bash
# Step 1: код компилируется
cd /storage/emulated/0/PROJECTS/workstation/freebuff
python3 -m py_compile core_02/*.py scripts_01/*.py freebuff_plugin_03/*.py  # exit 0

# Step 2: тесты зелёные
python3 -m pytest tests_09/ -q  # 2000+tests pass

# Step 3: canonical index не сломан
python3 scripts_01/drift_check.py --force         # exit 0 (no drift)
python3 scripts_01/consistency_check.py          # exit 0 (или pre-existing warnings)

# Step 4: doctor (интегральная диагностика)
python3 scripts_01/doctor.py

# Step 5: smoke-tests отдельных компонентов
python3 freebuff_cli.py status                    # CLI работает
python3 scripts_01/prompt_queue.py "smoke test"  # очередь работает
python3 scripts_01/prompt_dispatcher.py --dry-run # диспетчер пуст = ок
```

**Если что-то падает:**
- `consistency_check` покажет pre-existing warnings (это OK, но могут маскировать новые баги).
- `doctor.py` — диагностика окружения: TG session alive? .env загружен? Cron установлен?
- `git status` — проверить что нет uncommitted изменений (workspace projects могут быть dirty, но core код clean).

---

## 5. Promt dispatcher (multi-turn cycle)

Cron-driven (каждые 5 мин) или ручной (`--once`).

```
Telegram: /task <text>
       │
       ▼ prompt_queue.write_user_prompt()
pompts_11/user/task_<id>_<chat>.md   (pending)
       │
       ▼ cron (5 мин)
pompts_11/running/<file>.md         (in-progress)
       │
       ▼ wrapper.launch_and_wait(meta.body, WORKSPACE, 300)
       ▼ (phase-based: launch → опрос .freebuff_result)
успех → pompts_11/done/<file>.md
       │
       + TG report: Saved (msg_id) + Литвинов (msg_id)

Multi-turn (v5.79.0+):
  ЕСЛИ .freebuff_result.pending_task != null:
    → append_iteration(N+1, pending_task)
    → file stays in running/ (next cron picks up)
  ELSE: terminal done/failed.
```

**Команды:**
- `python3 scripts_01/prompt_dispatcher.py --dry-run` — посмотреть очередь.
- `python3 scripts_01/prompt_dispatcher.py --once` — обработать один (как cron).
- `python3 scripts_01/prompt_dispatcher.py --all` — обработать всё (ручной запуск).
- `python3 scripts_01/prompt_dispatcher.py --recover --dry-run` — восстановить зависшие.

---

## 6. Управление недостающими элементами (register-first, MissingRegistry)

Когда Баффи (или ревью) обнаруживает, что capability / tool / engine / forge / роль отсутствует — это **НЕ «несуществующий токен»**, а **недостающая способность, которую нужно построить** (принцип register-first, AGENTS.md §5). Молча игнорировать недостающее, использовать незарегистрированный токен или реализовывать «на лету» без записи в реестре — **запрещено**.

Реестр: `core_02/missing_registry.py` (данные: `data_13/missing_registry.yaml`). Lifecycle **forward-only**: `registered → design_ready → prompt_written → implemented` (не откатывается).

```bash
# 1. Зафиксировать недостающий элемент (до любой реализации!)
python3 -m core_02.missing_registry register my_tool --kind tool --factory code --description "..."

# 2. Написан промт на реализацию (pompts_11/promtNN.md)
python3 -m core_02.missing_registry mark-prompt-written my_tool --prompt pompts_11/promtNN.md

# 3. Реализовано (плюс пополнить KNOWN_CAPABILITIES / Tool Registry)
python3 -m core_02.missing_registry mark-implemented my_tool --implementation scripts_01/x.py

# Просмотр и проверка
python3 -m core_02.missing_registry list [--status registered|design_ready|prompt_written|implemented***REMOVED*** [--factory F***REMOVED*** [--json***REMOVED***
python3 -m core_02.missing_registry check     # B10/R-127 инварианты → exit 0 = валиден
python3 -m core_02.missing_registry seed      # восстановить канонические записи §20 (идемпотентно)
```

**Допустимые `--kind`:** `capability | tool | engine | forge | role | factory | module | registry | system`.
Полный операционный мануал (exit codes, troubleshooting, пошаговый гайд): [`docs_10/runbook/MISSING_REGISTRY_RUNBOOK.md`***REMOVED***(runbook/MISSING_REGISTRY_RUNBOOK.md).

---

## 7. Часто задаваемые вопросы / Troubleshooting

### Q: `python3 freebuff_cli.py` ничего не делает, висит долго

**Возможная причина:** ModelGateway пытается подключиться к remote LLM (DeepSeek / Claude / Qwen), но нет API-ключа в `.env`. Решение: ждать fallback (через 60-120 сек) или настроить `TELEGRAM_BOT_FALLBACK_MODEL` в `.env`.

### Q: TG-бот стартует, но не отвечает на `/task`

**Возможная причина:** бот не имеет прав отправлять сообщения юзеру, или чат-ID не в белом списке `ALLOWED_CHAT_IDS` (если установлен). Проверить: `python3 scripts_01/tg_smoke.py`.

### Q: `tests_09/` падает с `ImportError: python-telegram-bot`

**Решение:** установить `pip install python-telegram-bot`. Проверить: `pip list | grep telegram`.

### Q: Multi-turn cycle не прогрессирует (файл застрял в `running/`)

**Возможные причины:**
- Cron не запускается (`crontab -l | grep prompt_dispatch` пусто).
- `pending_task` возвращается слишком часто → превышен `max_iterations=3` → файлы в `failed/` с reason `max_iterations_reached`.
- Orphan lock в `running/.in_progress/` (диспетчер упал во время итерации). Решение: ручной `mv running/.in_progress/foo.md running/foo.md` + `python3 scripts_01/prompt_dispatcher.py --once`.

### Q: Где увидеть историю запусков?

- `CHANGELOG.md` — все релизы (v5.x → v5.79.0).
- `core_02/LESSONS.md` — инженерные уроки (CON-1..CON-NEW).
- `docs_10/promt48_report.md` — отчёт по promt-конвейеру.
- `docs_10/canonical/architecture.md` — каноническая архитектура (planned, см. TODO).

### Q: Как Баффи отвечает, если нет интернета?

Зависит от `model_gateway`. Если настроен локальный Ollama — работает offline. Если remote API — без интернета fallback handshake (timeout → локальный ответ «модель недоступна»).

---

## 8. Как остановить / откатить

```bash
# Остановить TG-бот:
killall -9 telegram_bot.py      # или Ctrl-C если foreground

# Остановить cron dispatcher:
crontab -e  # удалить строку */5 * * * * .../prompt_dispatch.sh

# Откатить код (до последнего коммита):
cd /storage/emulated/0/PROJECTS/workstation/freebuff
git reset --hard HEAD~1          # откатить 1 коммит
git stash                        # спрятать uncommitted
```

⚠️ **`git reset --hard HEAD~1` удалит все uncommitted данные в `core_02/`, `scripts_01/`, и т.д.** Использовать аккуратно.

---

## 9. ЧаВО про Баффи (FAQ)

**Кто такой Баффи?**
ИИ-мозг платформы Workspace OS. Не subprocess. Не отдельный продукт. Логика в `core_02/` + `freebuff_plugin_03/`.

**Кто его написал?**
ИИ-агент (он же сам Баффи, рекурсивно) в итеративных сессиях с пользователем (оператором платформы). Сессии задокументированы в `core_02/LESSONS.md` (CON-1..CON-NEW).

**Можно ли поменять мозг?**
Да (ADR-012). `core_02/router.py` + `freebuff_plugin_03/wrapper.py` абстрагируют LLM-backend; можно подключить Claude / DeepSeek / Ollama / локальный fine-tune.

**Безопасен ли он?**
`docs_10/core/CODE_QUALITY_STANDARD.md` фиксирует: нет `exec`/`shell=True`, секреты в `.env`, валидация ввода. `core_02/LESSONS.md` содержит CON-3 security guard.

**Как отлаживать?**
- Tests: pytest 2000+ зелёных.
- Visible logs: `logs_14/prompt_dispatch.log` (cron), TG message is debug surface.
- `git log --grep "..."` — поиск по сообщениям коммитов для исторических расследований.

---

## 10. Связанные документы

| Файл | Что внутри |
|------|------------|
| `BUFFY.md` | Identity + навигация. |
| `PLATFORM.md` | Позиционирование (plain language). |
| `AGENTS.md` | Канонические правила платформы (single source of truth). |
| `docs_10/core/CORE_PROMPT.md` | Личность ИИ-агента. |
| `docs_10/core/CODE_QUALITY_STANDARD.md` | Регламент кода. |
| `docs_10/runbook/MISSING_REGISTRY_RUNBOOK.md` | Операционный мануал MissingRegistry (register-first). |
| `docs_10/promt48_report.md` | Отчёт по multi-turn промт-конвейеру. |
| `core_02/LESSONS.md` | Все CON-* lessons. |
| `docs_10/DOCUMENT_REGISTRY.md` | Какие документы ACTIVE/LEGACY. |
| `CHANGELOG.md` | История релизов. |
| `docs_10/vision/VISION_3.0.md` | Стратегия. |

---

*Документ создан по запросу оператора «как запустить брата, где его вообще найти, создан ли он, в общем инструкцию в мд нужно» (2026-08-04). Если что-то изменилось (новые entry points / переименования / deprecation), обновить раздел §3 и поправить CHANGELOG.md.*
