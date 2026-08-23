# ADR-006 — SQLite/WAL storage and retention (P6)

> **Статус:** Accepted
> **Дата:** 2026-08-23
> **Связано:** `STORAGE.md`, `ROADMAP.md` P6, `DOMAIN_CONTRACTS.md` (RetentionPolicy)

## Контекст

P3 определил `RetentionPolicy` (TTL полного текста, cap, запрет текста) и порт
`CheckpointStore`. P4/P5 дают parser и matcher. Для P6 нужно выбрать способ
хранения, не вводя внешний сервис и не нарушая TTL/идам-инварианты.

## Решение

1. **SQLite с WAL** (`app/storage/sqlite.py`) — единственный файл, stdlib,
   WAL + `foreign_keys=ON` + busy_timeout. Никакого внешнего сервиса для MVP.
2. **Версия схемы — `PRAGMA user_version`** → миграции идемпотентны;
   `_SCHEMA_VERSION = 1` создаёт 4 таблицы.
3. **Dedup-инварианты** — UNIQUE `item_key` и UNIQUE `canonical_url`;
   `INSERT OR IGNORE` возвращает False при конфликте. Повторный прогон
   фида не создаёт строк.
4. **TTL cleanup отдельно от строки** — `expire_full_text()` обнуляет только
   `content`/`text_expires_at`; metadata, decisions, delivery_attempts и сама
   строка остаются. Идемпотентность: повторный вызов → 0 строк.
5. **cap текста при записи** — `max_text_chars` и `allow_full_text=False`
   применяются до INSERT, на уровне хранилища (контрактная защита, а не
   только normalization P4).
6. **`SqliteCheckpointStore`** — async-адаптер поверх sync-методов, реализует
   порт P3 без изменения доменного слоя.

## Альтернативы

- **PostgreSQL/Redis** — избыточны для single-tenant MVP; отложены до P16/P19
  (Track D) при измеренных лимитах.
- **JSON/YAML files** — не дают атомарных writes, индексов и идемпотентного
  UNIQUE; риск потери данных при прерывании.
- **TTL через DELETE строк** — противоречит цели «metadata/decision остаются»;
  выбран UPDATE только content.

## Последствия

- P7 delivery может доставлять Publication из persist-слоя после TTL, потому
  что минимальные поля (title/URL) не удаляются;
- дубли доставки различаются на уровне `delivery_attempts.delivery_key`;
- миграции остаются forward-only; новая схема требует новый `_SCHEMA_VERSION`
  и тест миграции (P11);
- multi-tenant owner isolation — строго отдельный слой/миграция (P13).