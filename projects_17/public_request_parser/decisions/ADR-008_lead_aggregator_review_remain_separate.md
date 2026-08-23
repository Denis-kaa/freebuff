# ADR-008 — Lead Aggregator integration review (P15)

> **Статус:** Accepted — decision: remain separate
> **Дата:** 2026-08-23
> **Связано:** `ROADMAP.md` P15, `projects_17/lead_aggregator/decisions/`

## Контекст

P15 требует field-level сравнения семантики Parser (`Publication`) и
Lead Aggregator (`Request`/`Lead`) перед решением: shared, adapter или separate.

## Сравнение (evidence)

| Измерение | `public_request_parser` | `lead_aggregator` |
|---|---|---|
| Вход | открытые публикации (RSS/Atom/TG-web-preview fixtures) | pull-модель заявок с площадок с юридическим гейтом (ADR-001/002) |
| Единица | `Publication` (без модели автора) | `Request` / `Lead` с контактной семантикой |
| Matching | универсальные профили (rule-based, explainable) | компетенции + коммерческий scoring |
| Retention | TTL полного текста, metadata за срок, owner profiles | иной жизненный цикл и хранение |
| Delivery | Telegram-карточки владельцу профиля | прикладной Attract-сценарий |

## Вывод

- Совпадение имён не даёт совместимости: различаются вход, единица, scoring и
  retention.
- **Остаёмся отдельными**; общий ingestion слой возможен только после
  field-level compatibility fixtures (Publisher=Parser) и отдельного ADR,
  который отменит этот.
- Никакого переписывания `lead_aggregator` на этой фазе.

## Последствия

- Контракты P3 не позиционируются как «Lead API»;
- при P16-платформализации сначала выделяются действительно повторно
  используемые границы (SourceAdapter, SourcePolicy), а не доменные модели.