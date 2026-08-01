# FreeBuff Overlay — система уведомлений

> **Версия:** 1.0.0
> **Статус:** Заменён на Telegram Popup

## История

Overlay-система изначально создавалась для FreeBuff — мониторинга статуса агента (Buffy) в плавающем окне Termux:Float.

Позже выяснилось, что пользователю нужен Telegram как оверлей, а не мониторинг. Так появился `tg_popup.sh`.

## Компоненты

| Файл | Назначение | Статус |
|------|-----------|--------|
| `scripts_01/overlay_server.py` | IPC-сервер статуса агента | ✅ Работает |
| `scripts_01/overlay_client.py` | Клиент для отправки статуса | ✅ Работает |
| `scripts_01/overlay_float.sh` | Запуск через Termux:Float/tmux | ✅ Работает |
| `scripts_01/tg_popup.sh` | **Telegram Popup Overlay** | ✅ Основной |

## Архитектура

```bash
# Telegram — как оверлей (основной сценарий)
tg_popup.sh → start_bg() → tmux new-session tg-bg → TG TUI
           → open_popup() → tmux display-popup (55%×65%, справа-снизу)
                           → tmux attach -t tg-bg
                           → Ctrl+Q → закрыть → обратно

# FreeBuff Overlay (альтернативный сценарий)
overlay_float.sh → python overlay_server.py
                 → Unix socket → overlay_client.py
```

## Запуск

```bash
# Telegram попап (рекомендуется)
bash scripts_01/tg_popup.sh

# FreeBuff Overlay
bash scripts_01/overlay_float.sh
```

---

_Подробнее: ../ops/REFERENCES.md_
