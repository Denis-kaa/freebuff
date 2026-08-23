# POST_MVP_GATES — статус P10–P19

> **Дата:** 2026-08-23
> **Статус:** честная фиксация того, что можно/нельзя сделать оффлайн, с
> evidence по каждому этапу. Ничего не «помечается done» без реализации.

## Сводка

| Этап | Статус | Что сделано | Что блокирует завершение |
|---|---|---|---|
| P8 single-tenant MVP slice | ✅ Done (offline) | `app/pipeline` + CLI `--once/--maintenance`; сквозной offline путь на fixtures, checkpoint-resume, идемпотентность | — |
| P9 Telegram technical adapter | ✅ Done (fixture) | `app/tgpreview` fixture-адаптер; live `allowed` запрещён | Live Telegram approval (policy) |
| P10 pilot | 🔴 Blocked | — | **G2**: нет production `allowed` источника (live polling запрещён) |
| P11 hardening | 🟡 Partial | `backup_to()` + CLI `--maintenance` (TTL+backup); идемпотентность/восстановление на уровне storage | scheduler, runbook, alerting — после pilot |
| P12 source expansion | 🟡 Partial | `HttpFeedAdapter` (live только для `allowed`, двойной гейт), fixture-адаптеры | Конкретные source approvals (G8) |

| P13 multi-tenant | 🟡 Partial | Schema v2: owner-isolated `profiles`, row-gates в CRUD; миграция v1→v2 | Auth-поток (Telegram bot), quotas |
| P14 feedback loop | 🟡 Partial | `feedback` табл. + идемпотентная запись + `feedback_stats()` | Калибровка порогов/ranking на pilot-данных (G10) |
| P15 Lead review | ✅ Done | ADR-008: remain separate | — |
| P16 platformization | ✅ Done (record) | ADR-009: deferred; кандидаты зафиксированы | live-use evidence |
| P17 public beta | 🔴 Blocked by G2/G9 | — | approved sources, multi-user auth, beta runbook, поддержка |
| P18 production v1.0 | 🔴 Blocked | — | все закрытые gates G2/G6/G7/G9/G13/G14 |
| P19 evolution | 🔄 Ongoing | каждый релиз — gated | — |

## Evidence-ссылки

- P8: `pipeline/__init__.py` + `tests/test_pipeline.py` (65+ тестов проекта)
- P9: `tgpreview/` + `tests/test_tgpreview.py`
- P11: `storage.sqlite.backup_to` + CLI `--maintenance` (`tests/test_pipeline.py::test_backup_creates_usable_db`)
- P12: `adapters/http_feed.py` + `tests/test_http_feed.py`
- P13/P14: `storage.profiles/feedback` + `tests/test_multi_tenant.py`
- P15/P16: ADR-008/009

## Главные открытые gates

1. **G2** — первый production-источник со статусом `allowed` (evidence + terms);
2. **G5** — e2e user journey (требует approved source или fixture-runbook);
3. **G7** — unattended-эксплуатация (scheduler, runbook, alerting);
4. **G9** — полноценная multi-tenant auth/quotas;
5. **G14** — production DoD.