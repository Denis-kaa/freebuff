# ADR-004 — RSS/Atom fixture engine boundary

> **Статус:** Accepted
> **Дата:** 2026-08-23
> **Scope:** `projects_17/public_request_parser`

## Context

P4 должен проверить parsing, normalization, deduplication и checkpoint
семантику до утверждения первого user-facing source. Добавление HTTP polling
на этом этапе смешало бы технический parser с policy gate, rate limits,
credentials и эксплуатацией.

## Options

1. Добавить live HTTP client и scheduler одновременно с parser.
2. Использовать внешнюю feed parsing dependency и привязать engine к transport.
3. Реализовать project-local parser на `xml.etree.ElementTree`, а transport и
   polling оставить отдельными портами.

## Decision

Выбран вариант 3:

- RSS 2.x и Atom 1.0 разбираются из переданных bytes/string;
- XML namespace обрабатывается через local-name;
- даты поддерживают RFC 2822 и ISO-8601 и нормализуются в UTC;
- неполные optional поля дают `FeedWarning`, повреждённый документ даёт
  `AdapterError`;
- source item нормализуется в существующий `Publication`;
- dedup использует source-scoped item key и canonical URL;
- `FixtureFeedAdapter` и `InMemoryCheckpointStore` закрывают только
  hermetic contract slice;
- policy со статусом `allowed` не может быть передана fixture adapter как
  live transport;
- HTTP, conditional requests, scheduler, SQLite/WAL и live canary добавляются
  отдельными этапами после соответствующих gates.

## Rationale

Стандартная библиотека достаточна для XML формата, не требует новой runtime
зависимости и сохраняет переносимость проекта. Явное разделение parser и
transport позволяет тестировать формат независимо от разрешения на сбор
контента и от доступности конкретной площадки.

## Consequences

### Положительные

- P4 полностью тестируется offline и не требует credentials.
- Ошибки одного item контролируемо изолируются от остальных элементов feed.
- Дедупликация и checkpoint semantics доступны P5/P6 без переписывания API.
- G2 остаётся честно открытым; technical fixture не превращается в product
  approval.

### Ограничения

- P4 не обещает live freshness или source SLA.
- `InMemoryCheckpointStore` не заменяет crash-safe SQLite persistence.
- ETag/Last-Modified и backoff требуют отдельного transport contract.

## Evidence

- `app/rss_atom/engine.py`
- `tests/test_rss_atom.py`
- `fixtures/rss/sample_rss.xml`
- `fixtures/atom/sample_atom.xml`
- `RSS_ATOM_ENGINE.md`
