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
cd projects/tg_terminal_messenger && python src/ui/app.py

# Через попап-оверлей (рекомендуется)
bash scripts/tg_popup.sh             # попап справа-снизу

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
bash scripts/tg_popup.sh kill
bash scripts/tg_popup.sh start
```
Скрипт сам убьёт зависшие процессы и почистит лок-файлы.

### 🔌 External Agent Integration

Freebuff теперь интегрирован с локальным агентом и веб-автоматизацией:

- **`scripts/agent_context_bridge.py`** — сохраняет диалоги `termux-ai-agent` в `freebuff/data/context.db`.
- **`src/workers/lightpanda_worker.py`** — управляет headless-браузером Lightpanda (Agent Mode, PandaScript, CDP).
- **`scripts/install_lightpanda.sh`** — устанавливает Lightpanda в Termux + proot-distro Ubuntu ARM64.

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
| `docs/TROUBLESHOOTING.md` | Частые ошибки и решения |
| `docs/DECISIONS.md` | Архитектурные решения |
| `docs/RULES.md` | Правила документирования |
| `docs/REFERENCES.md` | Ссылки на инструменты |
| `BUFFY.md` | Главный файл агента |

---

_Запускай `bash scripts/tg_popup.sh` и переписывайся в Telegram!_ 🚀
