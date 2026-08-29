# ADR-024: Cowork Context — ContextManager поверх RemoteDB (rqlite)

**Статус:** Accepted (Implemented)
**Дата:** 2026-08-23
**Вызвано:** продолжение ADR-023 — сделать сессии/контекст общими между Termux и сервером (Cowork live).

---

## Контекст

ADR-023 подключил `MemoryStore` к `RemoteDB` (rqlite на `185.233.184.192:4001`). Но `ContextManager` (`scripts_01/context_manager.py`) — второй ключевой компонент состояния (сессии, контекст, миграции схемы) — работает напрямую с `sqlite3.connect`, в обход MemoryStore. Чтобы контекст был общим между Termux и сервером, нужен тот же паттерн: `remote_db` параметр + прозрачная маршрутизация.

## Решение

1. **`_CoworkConn` / `_CoworkCursor`** — sqlite3-совместимая обёртка поверх `RemoteDB`:
   - `execute(sql, params)` → `RemoteDB.execute` (для DML) / `_query` (для SELECT).
   - `executescript(sql)` → выполняет каждое statement по отдельности через `RemoteDB.execute`.
   - `commit()` / `close()` — no-op (rqlite пишет сразу).
   - `rowcount` — из результата RemoteDB.
   - `Cursor.fetchall()` — строки из ответа rqlite (dict-совместимые).

2. **`ContextManager(..., remote_db=None)`** — новый параметр:
   - `remote_db is None` → прежний путь `sqlite3.connect` (обратная совместимость, 0 регрессий).
   - `remote_db` задан → `_init_db` создаёт схему через `_CoworkConn` (`_create_schema_v5`), `_get_conn()` возвращает `_CoworkConn`.

3. **Миграции**: в cowork-режиме применяется текущая схема (`_create_schema_v5`), версионные миграции `PRAGMA user_version` пропускаются (rqlite не поддерживает PRAGMA user_version) — документировано, приемлемо для v0.1.

## Альтернативы

- **Прокинуть ContextManager через MemoryStore** — MemoryStore не имеет полного sqlite-интерфейса (нет executescript/схемных операций), потребовал бы большой переделки. Отклонено: обёртка меньше и аддитивна.
- **Отдельная БД контекста в rqlite** — противоречит цели «общая БД». Отклонено.

## Следствия

- **Обратная совместимость:** все существующие тесты ContextManager (24) проходят без изменений.
- **Cowork:** сессии и контекст, записанные с Termux, читаются с сервера и наоборот — одна БД, один источник истины.
- **Порядок инициализации:** схема создаётся идемпотентно (CREATE IF NOT EXISTS).
- **Тесты:** `tests_09/test_context_manager_cowork.py` — 15 hermetic (mock RemoteDB) + 2 integration (skipped без rqlite).

## Статус

Реализовано и покрыто тестами. Интеграционный smoke-тест (Termux ↔ сервер через rqlite) — выполняется при доступности сервера.
