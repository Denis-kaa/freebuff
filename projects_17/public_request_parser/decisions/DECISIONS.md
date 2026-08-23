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

## Правила ADR

1. Следующее решение получает следующий номер; принятые решения не удаляются.
2. Решение о платформенном общем слое оформляется отдельно в `docs_10/engineering-memory/decisions/`.
3. Решение о переиспользовании Lead Aggregator нельзя принимать только по совпадению названий; требуется contract comparison.
4. Live-source enablement требует отдельного evidence/policy record.
