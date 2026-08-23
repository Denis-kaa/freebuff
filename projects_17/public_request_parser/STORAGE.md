# STORAGE — P6

> **Статус:** implemented locally, SQLite/WAL
> **Версия:** 0.1.0
> **Ограничение:** единое локальное хранилище single-tenant; multi-tenant изоляция — P13.

## Назначение

P6 сохраняет публикации, решения matcher, чекпоинты источников и попытки
доставки в одном SQLite-файле с WAL:

- **публикации** с dedup-индексами (UNIQUE item_key + UNIQUE canonical_url);
- **полный текст** — временное поле с `text_expires_at` (TTL);
- **решения** — идемпотентный UNIQUE по (publication_key, profile_id, profile_version);
- **чекпоинты** — source-scoped upsert (порт `CheckpointStore` P3);
- **доставка** — идемпотентная по delivery_key.

## API

### `SqliteStorage(db_path)`

```python
storage = SqliteStorage("parser.db")   # создаёт WAL + schema
storage.close()
```

| Метод | Назначение |
|---|---|
| `save_publication(pub, *, text_ttl, max_text_chars, allow_full_text) -> bool` | INSERT OR IGNORE; True если создана |
| `get_publication(item_key) -> Publication \| None` | чтение по source-scoped ключу |
| `list_publications(*, source_id=None, limit=100) -> list[Publication***REMOVED***` | последние публикации |
| `expire_full_text(now=None) -> int` | обнулить истёкший `content`; идемпотентен |
| `get_checkpoint(source_id) / set_checkpoint(source_id, item_id)` | позиция обработки |
| `save_decision(decision) -> bool` / `get_decision(pk, pid, ver)` | explainable decisions |
| `save_delivery_attempt(attempt, *, publication_key, profile_id, profile_version) -> bool` | попытки доставки |
| `count_publications() / count_decisions()` | метрики |
| `close()` | закрыть соединение |

### `SqliteCheckpointStore(storage)`

Async-реализация порта `CheckpointStore` из P3 (`get`/`commit`), готовая для
pipeline P6/P7 (например, `FixtureFeedAdapter` + `SqliteCheckpointStore`).

### Политика `RetentionPolicy` → параметры записи

| `RetentionPolicy` поле | В `save_publication` |
|---|---|
| `text_ttl` | `text_ttl` (срок с `fetched_at`) |
| `max_text_chars` | `max_text_chars` (cap перед записью) |
| `allow_full_text=False` | `allow_full_text=False` (текст не сохраняется вообще) |

Эффективный TTL никогда не ослабляется — строгий минимум по source policy
применяется вызывающим слоем (см. `effective_text_ttl` в `DOMAIN_CONTRACTS.md`).

## Схема и миграции

Версия схемы — `PRAGMA user_version = 1`. `_migrate()` идемпотентен:
повторный open существующей БД не трогает данные.

| Таблица | Ключ | Примечание |
|---|---|---|
| `publications` | `item_key` PK, `canonical_url` UNIQUE | `content` + `text_expires_at`; `metadata_json`; `status` |
| `checkpoints` | `source_id` PK | `last_item_id`, `updated_at` |
| `decisions` | UNIQUE pk+profile+version | JSON-колонки terms/reasons/snapshot |
| `delivery_attempts` | `delivery_key` PK | FK на publication; каскадное удаление |

## TTL lifecycle

1. Публикация сохраняется с `text_expires_at = fetched_at + ttl` (если контент есть).
2. Периодический `expire_full_text(now)` стирает истёкший контент:
   `UPDATE publications SET content = NULL, text_expires_at = NULL WHERE text_expires_at <= now`.
3. Строка, metadata, decisions и delivery_attempts **остаются** — удаляется
   только временный полный текст. Повторный вызов возвращает 0 (идемпотентность).

## Проверки

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/test_storage_sqlite.py -q
python -m mypy app tests --strict
```

## Не закрыто P6

- Multi-tenant owner scope и user isolation (P13);
- schema migrations beyond v1 (bucket-versioned procedure — P11/P13);
- backup/restore и crash recovery проверки (P11);
- scheduler/регулярный TTL-проход (P11);
- постоянный `SqliteCheckpointStore` в составе живого pipeline (P8, после G2).

## Не закрыто G4/P4-P7

- P4 parser offlile (fixture), P5 matcher, P6 storage — ингредиенты G4;
  P7 delivery и end-to-end pipeline P8 остаются следующими;