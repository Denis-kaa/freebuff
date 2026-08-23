# DECISIONS.md — Public Request Parser Bot

> **Scope:** project-local decisions for `public_request_parser`.
> **Canonical product spec:** [`../../../public-request-parser-spec.md`***REMOVED***(../../../public-request-parser-spec.md)

| # | Решение | Статус | Дата | Related |
|---|---|---|---|---|
| ADR-001 | Отдельный универсальный parser; RSS/Atom first; Telegram fixture-only до policy approval | ✅ Accepted | 2026-08-22 | `SPEC.md`, `ROADMAP.md`, Lead Aggregator boundary |
| ADR-002 | Разделять technical candidate и production `allowed`; Stack Overflow Atom — fixture candidate, Telegram live — blocked | ✅ Accepted | 2026-08-23 | `SOURCE_POLICY_MATRIX.md`, `ROADMAP.md`, P2/G2 |
| ADR-003 | Typed project-local domain contracts; отдельные policy, adapter, match и delivery error boundaries | ✅ Accepted | 2026-08-23 | `DOMAIN_CONTRACTS.md`, `ROADMAP.md`, P3/G3 |
| ADR-004 | RSS/Atom fixture engine boundary: stdlib parser, offline normalization/dedup/checkpoint; transport и polling отдельными gates | ✅ Accepted | 2026-08-23 | `RSS_ATOM_ENGINE.md`, `ROADMAP.md`, P4 |
| ADR-005 | Детерминированный rule-based matcher: hard rejects, intent gate спрос/предложение, mean-ratio score, explainability; LLM отложен до P14 | ✅ Accepted | 2026-08-23 | `MATCHING_ENGINE.md`, `ROADMAP.md`, P5 |
| ADR-006 | SQLite/WAL storage: user_version миграции, UNIQUE dedup, TTL cleanup только content (metadata/decision остаются), async CheckpointStore adapter | ✅ Accepted | 2026-08-23 | `STORAGE.md`, `ROADMAP.md`, P6 |
| ADR-007 | Delivery contract: HTML-escape renderer, MessageTransport protocol, dry-run, idempotent key, retry только failed, owner-гейт; live transport policy-gated | ✅ Accepted | 2026-08-23 | `DELIVERY.md`, `ROADMAP.md`, P7 |
| ADR-008 | Lead Aggregator review: Publication vs Request/Lead семантика различна; остаёмся отдельными (remain separate) | ✅ Accepted | 2026-08-23 | `ROADMAP.md`, P15 |
| ADR-009 | Platformization deferred до live-use evidence; кандидаты (SourceAdapter/SourcePolicy/catalog) зафиксированы, MissingRegistry не трогается | ✅ Accepted | 2026-08-23 | `ROADMAP.md`, P16, `POST_MVP_GATES.md` |
| ADR-010 | Feedback calibration: детерминированная рекомендация порогов (accuracy), без авто-apply; apply через новую версию профиля | ✅ Accepted | 2026-08-23 | `CALIBRATION.md`, `ROADMAP.md`, P14 |

## Правила ADR

1. Следующее решение получает следующий номер; принятые решения не удаляются.
2. Решение о платформенном общем слое оформляется отдельно в `docs_10/engineering-memory/decisions/`.
3. Решение о переиспользовании Lead Aggregator нельзя принимать только по совпадению названий; требуется contract comparison.
4. Live-source enablement требует отдельного evidence/policy record.
