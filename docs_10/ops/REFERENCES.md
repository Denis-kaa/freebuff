# REFERENCES.md — Ссылки и ресурсы

> **Последнее обновление:** 2026-07-28

## Основные компоненты

| Компонент | Ссылка | Назначение |
|-----------|--------|------------|
| **Textual** | https://textual.textualize.io/ | TUI-фреймворк для Python |
| **Telethon** | https://docs.telethon.dev/ | MTProto Telegram-клиент |
| **tmux** | https://github.com/tmux/tmux | Терминальный мультиплексор |
| **Termux** | https://termux.com/ | Android-терминал |
| **Rich** | https://rich.readthedocs.io/ | Markup-разметка для терминала |

## Termux-аддоны

| Аддон | F-Droid | Назначение |
|-------|---------|------------|
| **Termux:Float** | https://f-droid.org/packages/com.termux.window/ | Плавающее окно терминала |
| **Termux:Widget** | https://f-droid.org/packages/com.termux.widget/ | Виджеты на домашний экран |
| **Termux:API** | https://f-droid.org/packages/com.termux.api/ | API-доступ (уведомления, сенсоры) |
| **Termux:Boot** | https://f-droid.org/packages/com.termux.boot/ | Скрипты при загрузке |

## Установка Termux-аддонов

```bash
# Termux:Float — плавающее окно
pkg install termux-api        # мост между APK и CLI
termux-float python script.py # запуск в плавающем окне

# Termux:Widget — иконки на домашнем экране
# Скрипты класть в: ~/.shortcuts/*.sh
# После установки APK — добавить виджет на экран

# Termux:Notification — системные уведомления
termux-notification --title "TG" --content "Новое сообщение" --action "bash scripts_01/tg_popup.sh"
```

## Проекты

| Проект | Путь | Описание |
|--------|------|----------|
| tg-terminal-toolkit | `projects_17/tg_terminal_messenger/` | Telegram TUI клиент |
| FreeBuff Overlay | `scripts_01/overlay_server.py` | Плавающий мониторинг агента |

---

_Обновляй при добавлении новых зависимостей._
