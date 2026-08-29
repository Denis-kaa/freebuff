# FreeBuff — AI Engineering Workspace

> **Версия:** 4.0.0
> **Платформа:** Android (Termux)
> **Роль:** Основная рабочая среда для AI-агентов и Telegram-клиента

## 📋 Что здесь есть

### 🚀 Telegram TUI (tg-terminal-toolkit)

Терминальный Telegram-клиент с экранной навигацией.

```
Список чатов → Enter → Полный экран чата → строка ввода
```

**Возможности:**
- ✅ Двухэкранная навигация: список чатов + полный экран переписки
- ✅ Поиск по чатам (Ctrl+S)
- ✅ Избранные чаты ⭐ (Ctrl+E)
- ✅ Отправка сообщений (Enter в строке ввода)
- ✅ Счётчик непрочитанных + звуковой сигнал
- ✅ Автообновление каждые 10 секунд

**Как запустить:**
```bash
# Прямой запуск
cd projects_17/tg_terminal_messenger && python src_06/ui/app.py

# Через попап-оверлей (рекомендуется)
bash scripts_01/tg_popup.sh             # попап справа-снизу

# Через виджет на домашнем экране
# Добавь Termux:Widget → выбери Telegram.sh
```

**Управление:**
| Клавиша | Действие |
|---------|----------|
| `↑↓` | Навигация по чатам |
| `Enter` | Открыть чат (полный экран) |
| `Esc` | Назад к списку чатов |
| `Ctrl+E` | ⭐ Избранное |
| `Ctrl+F` | Фокус на ввод сообщения |
| `Enter` (в чате) | Отправить сообщение |
| `Ctrl+S` | Поиск по чатам |
| `Ctrl+R` | Обновить чаты |
| `Ctrl+Q` | Выход |

### 🩺 Самоисцеление

При ошибке `database is locked` — просто перезапусти:
```bash
bash scripts_01/tg_popup.sh kill
bash scripts_01/tg_popup.sh start
```
Скрипт сам убьёт зависшие процессы и почистит лок-файлы.

### 🔌 External Agent Integration

Freebuff теперь интегрирован с локальным агентом и веб-автоматизацией:

- **`scripts_01/agent_context_bridge.py`** — сохраняет диалоги `termux-ai-agent` в `freebuff/data_13/context.db`.
- **`src_06/workers/lightpanda_worker.py`** — управляет headless-браузером Lightpanda (Agent Mode, PandaScript, CDP).
- **`scripts_01/install_lightpanda.sh`** — устанавливает Lightpanda в Termux + proot-distro Ubuntu ARM64.

**Как запустить:**
```bash
# Интеграция termux-ai-agent — сообщения автоматически пишутся в freebuff
python termux-ai-agent/main.py "найди документацию Python"

# Lightpanda dump
python - <<'PY'
from src.workers.lightpanda_worker import LightpandaWorker
w = LightpandaWorker()
print(w.dump_url("https://example.com").data)
PY
```

### 📊 FreeBuff CLI

```bash
python freebuff_cli.py status    # состояние системы
python freebuff_cli.py start     # новая сессия
python freebuff_cli.py list      # все сессии
```

### 📝 Документация

| Файл | О чём |
|------|-------|
| `docs_10/ops/TROUBLESHOOTING.md` | Частые ошибки и решения |
| `docs_10/decisions/DECISIONS.md` | Индекс архитектурных решений |
| `docs_10/core/RULES.md` | Правила документирования |
| `docs_10/ops/REFERENCES.md` | Ссылки на инструменты |
| `docs_10/HOW_TO_LAUNCH_BUFFY.md` | Operator runbook — как найти и запустить Баффи (CLI/TG-бот/promt-конвейер) |
| `BUFFY.md` | Главный файл агента |
| `AGENTS.md` | Инструкции для Freebuff/Codebuff CLI |
| `.freebuff/AGENTS.md` | Контекст специально для Freebuff CLI |
| `.freebuff/config.json` | Метаданные проекта для Freebuff CLI |

###  Freebuff CLI

Этот проект готов к работе через `freebuff` CLI:

```bash
cd /mnt/sdcard/PROJECTS/workstation/freebuff
freebuff
```

Агент получит контекст из `AGENTS.md`, `BUFFY.md`, `TASK.md` и `CHANGELOG.md`.

### 🗺️ Навигация по git-истории (переименование каталогов 2026-08-01)

Каталоги переименованы по схеме `имя_NN` (суффикс-ID; цифра спереди невозможна —
ломает Python-импорты). Для `git log` / `git show` по **старым** путям используй
соответствие:

| Старое имя | Новое имя | № |
|-----------|-----------|---|
| `scripts` | `scripts_01` | 01 |
| `core` | `core_02` | 02 |
| `freebuff_plugin` | `freebuff_plugin_03` | 03 |
| `plugins` | `plugins_04` | 04 |
| `runtime` | `runtime_05` | 05 |
| `src` | `src_06` | 06 |
| `cli` | `cli_07` | 07 |
| `services` | `services_08` | 08 |
| `tests` | `tests_09` | 09 |
| `docs` | `docs_10` | 10 |
| `pompts` | `pompts_11` | 11 |
| `context` | `context_12` | 12 |
| `data` | `data_13` | 13 |
| `logs` | `logs_14` | 14 |
| `sessions` | `sessions_15` | 15 |
| `screenshots` | `screenshots_16` | 16 |
| `projects` | `projects_17` | 17 |
| `frontend` | `frontend_18` | 18 |
| `buffy-playground` | `buffy-playground_19` | 19 |
| `infa` | `infa_20` | 20 |
| `trash` | `trash_21` | 21 |
| `prototype` | `prototype_22` | 22 |

> ⚠️ Только top-level каталоги получили суффикс `_NN`. Вложенные подкаталоги имя
> **не** меняли: `freebuff_plugin_03/runtime/`, `runtime_05/plugins/`, `docs_10/core/`.
> Эта таблица — **удобная копия канона** (`docs_10/core/FINAL_STRUCTURE.md` §2.1,
> включая маппинг промтов `NNN_TT_имя`); при расхождении главенствует канон.

Примеры:
```bash
# История по старому пути (до переименования)
git log --oneline -- scripts/context_manager.py
# Полная история файла, включая перенос между каталогами
git log --oneline --follow -- scripts_01/context_manager.py
```

---

_Запускай `bash scripts_01/tg_popup.sh` и переписывайся в Telegram!_ 🚀
