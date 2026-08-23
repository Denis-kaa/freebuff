# DOMAIN_CONTRACTS — P3

> **Проект:** `public_request_parser`
> **Версия контракта:** 0.1.0
> **Статус:** implemented locally, review-ready
> **Ограничение:** контракты не выполняют сетевые операции и не включают live polling.

## 1. Назначение

P3 фиксирует границы между source adapters, нормализованными публикациями,
профилями поиска, explainable matching, retention/storage и Telegram delivery.
Контракты project-local и не импортируют `core_02`, `scripts_01` или
`freebuff_plugin_03`, поэтому standalone runtime сохраняет переносимость.

## 2. Domain entities

### `SourceItem`

Минимальный элемент, возвращаемый адаптером до нормализации:

- `item_id` — стабильный ID источника;
- `canonical_url` — абсолютный HTTP(S) URL;
- `title` — обязательный заголовок;
- `published_at` — timezone-aware дата или `None`;
- `summary`/`content` — контент, который storage layer может обрезать/удалить;
- `metadata` — минимальные source-specific технические поля.

### `Publication`

Каноническая публикация после нормализации:

- `source_id + item_id` образуют стабильный `item_key` для deduplication;
- `canonical_url`, `title`, даты и технические metadata обязательны по смыслу;
- `content` является временным полем;
- автор, ник, email, телефон, аватар и пользовательский профиль не являются
  частью контракта.

### `SearchProfile`

Версионируемый профиль владельца:

- `owner_scope` изолирует single-tenant и будущие tenant scopes;
- required/optional terms, synonyms, exclusions и intent terms задаются явно;
- `0 <= pending_threshold <= accept_threshold <= 1`;
- если snapshot не передан, он строится при создании профиля и сохраняется в
  immutable dataclass.

### `MatchDecision`

Результат детерминированного matcher:

- ссылается на `publication_key`, `profile_id` и `profile_version`;
- имеет outcome `accept`, `pending` или `reject`;
- score нормирован в диапазон `0..1`;
- accepted decision требует `reasons`;
- matched/rejected terms и `rules_snapshot` позволяют объяснить результат.

## 3. Policy и retention

### `SourcePolicy`

Статус относится к конкретному endpoint, access mode, scope и полям, а не ко
всей площадке. `allowed` требует хотя бы одну `evidence_url`. Только `allowed`
может иметь `can_poll=True` или `user_facing=True`.

Текущие `technical_candidate`, `conditional`, `manual_review` и
`policy_blocked` из `SOURCE_POLICY_MATRIX.md` не могут быть включены в live
config через этот контракт.

### `RetentionPolicy`

- `allow_full_text=False` запрещает задавать TTL полного текста;
- `effective_text_ttl(source_limit)` выбирает более строгий из двух TTL;
- отрицательные TTL и отрицательный `max_text_chars` запрещены;
- metadata TTL отделён от full-text TTL.

## 4. Infrastructure ports

### `SourceAdapter`

Асинхронный read-only порт:

```python
async def fetch(
    *, limit: int = 50, checkpoint: str | None = None
) -> AsyncIterator[SourceItem***REMOVED***
async def health() -> bool
```

Адаптер обязан соблюдать bounded batch, checkpoint semantics и policy gate.
Ошибка одного адаптера представляется `AdapterError` и не должна превращаться
в domain rejection другого источника.

### `CheckpointStore`

Идемпотентный async-порт:

```python
async def get(source_id: str) -> str | None
async def commit(source_id: str, item_id: str) -> None
```

`commit` означает подтверждённую обработку, а не только получение элемента.
Конкретная SQLite/WAL реализация относится к P6.

### `Delivery`

Доставляет `Publication + MatchDecision` только в канал владельца через
`owner_scope`. Контракт не содержит операции связи с автором публикации.

`DeliveryAttempt` требует доказательство результата:

- `sent` → `provider_message_id`;
- `failed` → `error_code`;
- `skipped` допустим для dry-run/disabled delivery.

Конкретный Telegram transport относится к P7.

## 5. Error boundary

| Ситуация | Контракт |
|---|---|
| Невалидный URL, ID, timezone или threshold | `ContractValidationError` |
| Сбой конкретного feed/API adapter | `AdapterError` |
| Публикация не совпала с профилем | `MatchDecision(outcome=reject)`, не exception |
| Источник не прошёл policy | `SourcePolicy` не даёт `can_poll/user_facing` |
| Ошибка доставки | `DeliveryAttempt(status=failed, error_code=...)` |

## 6. Test evidence

Hermetic tests: `tests/test_domain_contracts.py`.

Проверяются:

- source-scoped dedup key;
- timezone validation;
- profile snapshot/version;
- threshold boundaries;
- explainability of accepted decisions;
- strict source TTL;
- policy gate for polling/user-facing mode;
- delivery result evidence.

P3 не утверждает наличие approved live source и не закрывает G2. Следующий
этап — P4 RSS/Atom parser на fixtures.
