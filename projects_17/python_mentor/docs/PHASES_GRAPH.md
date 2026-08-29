# PHASES_GRAPH.md — визуальная схема фаз B+C…N

> **Версия:** 0.1.1 · **Дата:** 2026-08-24 · Источник: ROADMAP.md (ROADMAP-PYM-001)
> Назначение: наглядный граф фаз с зависимостями и открытыми вопросами (рисунок — живой артефакт, обновляется при каждом гейте).

## Граф зависимостей

```
P0 ──────────────── ✅  P1 ─────────────── 🟡
                                        │
                                        ▼
        ┌───────────────────────────────────────────────┐
        │  ╔══ B+C ══  ✅ COMPLETE (G-BC)                 │
        │  0-11 структура · license · ingestion · reports │
        │  ╚═══════════════════════╤═══════════════════╝
        │                          │
        ▼                          ▼
   ┌──────────┐   contract    ┌──────────┐   limits   ┌──────────┐
   │ G •D     │──────────────►│ G •E     │───────────►│ G •F     │
   │ Autograder │             │ Sandbox   │            │ AST/Static│
   └──────────┘               └──────────┘            └────┬─────┘
        │                       │                         │
        │  results/candidates   │  exec безопасность       │ diagnostics
        ▼                       ▼                         ▼
   ┌──────────┐            ┌──────────┐            ┌──────────┐
   │ G •G       │            │ H        │◄──────────┤ (паттерны)│
   │ Hint Engine │            │ Evidence│            │          │
   └──────────┘              └────┬─────┘            └──────────┘
        │                         │  state folds (S0-S5)
        ▼                         ▼
                              ┌──────────┐   due/overdue
                              │ I •Sync   │──────────────► J: Selector
                              └──────────┘                  (Куратор)
                                                  │
   ┌ K: Project Engine ◄────── competency map ────┘
   └──────────────────────────────┬────────────────────────────►
                                  ▼
                        L: FastAPI (thin, 0 logic) → M: UI → N: E2E → O: LLM (опц.)
```

**Принцип:** строго последовательные гейты G-BC → G-D → G-E → G-F → G-G → G-H → G-I → G-J → G-K → G-L → G-M → G-N (перескоки запрещены: ADR-002, ANTI-5).

## Открытые вопросы (сводка)

| # | Вопрос | Фаза | Статус |
|---|---|---|---|
| 1 | FSRS-библиотека (fsrs/SM-2) | I | ✅ `fsrs 6.3.2` установлена; ADR при старте I |
| 2 | Evidence→rating mapping | I | ✅ таблица в FSRS_NOTE.md §3 |
| 3 | unshare/RLIMIT | E | 🚠 RLIMIT ✅; userns ⚠️ proot — изоляция не обещается (MVP=subprocess+limits) |
| 4 | pylint/radon/bandit | F | ✅ установлены 4.0.7/6.0.1/7.3.0/1.9.4; ruff не ставили |
| 5 | Источники после Exercism | после B+C | ⏳ отдельный license gate + gap-анализ |
| 6 | Приоритизация в J | J | ⏳ ADR до старта J |
| 7 | Forge pipeline (core_02) для исполнения | все | 🟡 опция |
| 8 | fastapi+uvicorn в Termux | L | ⏳ проверка при старте L |
| 9 | Upstream exercism изменён после `1f6aab8` | B+C | 🟡 commit-pin + переаудит change-detection |
| 10 | foregone-упражнения (3) | B+C | ✅ не импортируются |

## Текущий прогресс

B+C ✅ (G-BC) · D ✅ (G-D) · E ✅ (G-E) · F ✅ (G-F: 7 AST rules, 4 adapters, 14 diagnostic-only tests).
Следующий гейт: G-G — Hint Engine; затем H Evidence/State.

## Cross-links
- `ROADMAP.md` — главный документ (фазы/гейты/риски/открытые вопросы)
- `PHASE_BC_PLAN.md` — операционный план B+C (11 шагов, CP-0…CP-11)
- `STEPS.md` — журнал шагов с «почему»