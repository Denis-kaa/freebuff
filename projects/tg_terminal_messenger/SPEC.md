# SPEC.md — tg-terminal-toolkit

> **Проект в freebuff:** `projects/tg_terminal_messenger/`
> **Исходный проект:** `/storage/emulated/0/PROJECTS/workstation/tg_terminal_messenger/`
> **Методология:** Kwork Arbitr v3 (blueprints_v3)
> **LISA Score:** 4.86 (MEDIUM)
> **TG Credentials:** `~/leviathan/opt/tg_pass/pass.md` (api_id=37035907)

---

## 📋 Техническое задание

### Что это

Терминальный Telegram-клиент с TUI-интерфейсом для Android (Termux):
- Отправка медиафайлов
- Навигация по чатам
- Скачивание и архивация переписок
- Встроенный файловый менеджер

### Стек

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Язык | Python 3.10+ | Основной |
| Telegram API | Telethon (MTProto) | Работа с Telegram |
| TUI | Textual | Интерфейс |
| Файлы | aiofiles | Асинхронный I/O |
| БД | SQLite (aiosqlite) | Кеш чатов, сообщений |
| Тесты | pytest + pytest-asyncio | Тестирование |

### Функциональные требования

- 🔐 **Авторизация:** телефон + 2FA, сессия с правами `600`
- 🖥️ **TUI:** двухпанельный (чаты/сообщения), асинхронная загрузка, горячие клавиши
- 📎 **Медиа:** отправка файлов через `FilePicker` (Ctrl+F)
- 📦 **Архивация:** экспорт истории, скачивание медиа по `chat_id` с прогресс-баром

### Нефункциональные требования

- Устойчивость к `FloodWaitError` (retry с экспоненциальной задержкой)
- Неблокирующий UI (все сетевые операции асинхронны)
- Кроссплатформенность терминала (xterm, tmux, screen)
- RAM ≤ 200 MB в простое

---

## 🏗️ Архитектура (4 слоя)

```
src/
├── ui/          # Textual TUI: ChatList, MessageView, FilePicker
├── telegram/    # Telethon-клиент: авторизация, отправка, получение
├── core/        # Бизнес-логика: archive engine, message cache
└── storage/     # SQLite + файловая система
```

---

## 🚦 Blueprints v3 Pipeline

| Стадия | Агент | Статус | Артефакт |
|--------|-------|--------|----------|
| 1 | Explainer | ✅ | `doc/brief.md`, `doc/parsed_requirements.md` |
| 2 | LISA Estimator | ✅ | `doc/lisa_report.md` (4.86, MEDIUM) |
| 3 | Risk Manager | ✅ | `doc/risk_manager_report.md` |
| 4 | Architect | ✅ | `doc/architect/report_v1.md` |
| 5 | Decomposer | 🔲 | Разбивка на bounded contexts |
| 6 | Developer | 🔲 | Код |
| 7 | Tester | 🔲 | Тесты |
| 8 | Fixer | 🔲 | Исправления |
| 9 | Acceptance | 🔲 | Приёмка |
| 10 | Documenter | 🔲 | Документация |

---

## 🔑 TG Credentials

Источник: `~/leviathan/opt/tg_pass/pass.md`

| Параметр | Значение |
|----------|----------|
| api_id | `37035907` |
| api_hash | `383bbe0942526db1133edc23d8ba8023` |
| Сессия | ❌ НЕ НАЙДЕНА — `/storage/BA73-022B/denis_tg_session.session` отсутствует |

**Действие:** Создать новую сессию через Telethon при первом запуске.

---

## 🔍 Пропущенные проекты (из аудита)

| Проект | Статус |
|--------|--------|
| `/triton` | ❌ Не найден — ни в `/storage/emulated/0/PROJECTS/workstation/triton/`, ни в `~/triton/` |

---

## 📁 Структура проекта

```
projects/tg_terminal_messenger/
├── SPEC.md              # ← этот файл
├── manifest.md          # blueprints_v3 manifest
├── README.md            # Быстрый старт
├── ARCHITECTURE.md      # Детальная архитектура
├── src/
│   ├── main.py          # Точка входа
│   ├── ui/              # Textual TUI
│   ├── telegram/        # Telethon-клиент
│   ├── core/            # Бизнес-логика
│   └── storage/         # SQLite + файлы
├── tests/
├── docs/
└── requirements.txt
```

---

## 🎯 Ближайшие шаги

1. Decomposer: разбить на bounded contexts
2. Developer: реализовать `src/telegram/client.py` (авторизация)
3. Developer: реализовать `src/ui/app.py` (TUI-каркас)
4. Tester: написать тесты на авторизацию и UI
