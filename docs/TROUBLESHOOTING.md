# TROUBLESHOOTING.md — Частые ошибки и решения

> **Последнее обновление:** 2026-07-28

## Telegram TUI

### ❌ `database is locked`

**Симптом:** TUI показывает "database is locked" и не подключается.

**Причина:** Python-процесс Telethon остался висеть после убийства tmux-сессии и держит лок на SQLite.

**Решение:**
```bash
# Вариант 1 — через tg_popup.sh (самоисцеление)
bash scripts/tg_popup.sh kill
bash scripts/tg_popup.sh start

# Вариант 2 — вручную
pkill -9 -f "src/ui/app"
rm -f projects/tg_terminal_messenger/tg_session.session.lock
rm -f projects/tg_terminal_messenger/tg_session.session-journal
tmux kill-session -t tg-bg
bash scripts/tg_popup.sh start
```

**Профилактика:** `tg_popup.sh` теперь сам чистит лок-файлы при старте.

### ❌ `no current client` (tmux display-popup)

**Симптом:** При запуске `tg_popup.sh` — ошибка "no current client".

**Причина:** `tmux display-popup` требует активного tmux-клиента.

**Решение:** Скрипт сам определяет: если ты не в tmux → создаёт временную сессию для попапа. Просто перезапусти.

### ❌ Тёмный экран при запуске через виджет

**Симптом:** Виджет открывает Termux, но экран чёрный.

**Причина:** Сложная цепочка `tmux new-session → display-popup` ломается в окружении виджета.

**Решение:** Обновлённый `Telegram.sh` просто подключается к tg-bg напрямую. Удали и добавь виджет заново.

## FreeBuff Overlay

### ❌ `termios.error: Inappropriate ioctl for device`

**Симптом:** `overlay_server.py` падает с этой ошибкой.

**Причина:** stdout не является терминалом (запуск в фоне или пайп).

**Решение:** `overlay_server.py` теперь проверяет `sys.stdin.isatty()` перед вызовом termios.

---

_Обновляй этот файл при обнаружении новых проблем._
