# ADR-001: Pull-модель + порядок источников (Kwork → TG-каналы)

**Status:** Accepted (2026-08-10)
**Component:** Attract-модуль — архитектура сбора заказов
**Scope:** PROJECT-LOCAL (решение принадлежит проекту lead_aggregator)
**Related:** [MANIFEST.md***REMOVED***(../MANIFEST.md) · [PHASE2_ARCHITECTURE.md***REMOVED***(../PHASE2_ARCHITECTURE.md) · [IDEA_EXPLORER_RUN.md***REMOVED***(../IDEA_EXPLORER_RUN.md) · Platform: [ADR_014***REMOVED***(../../../docs_10/engineering-memory/decisions/ADR_014_Lead_Aggregator_Attract_Module.md) (provenance: платформенная запись остаётся; эта — self-contained копия решения)

---

## 1. Context

Проект ищет заказы для AI-фрилансера (Python, TG-боты, FastAPI, лендинги). Прогон IDEA EXPLORER v2.0 дал 7 веток (B1–B7) и 3 кандидата. Критическая развилка: **внешние контакты заказчиков**. Kwork-страницы публичны, но контакты закрыты (через отклик); TG-каналы публичны целиком.

## 2. Decision

- **Pull-модель (read-only) — Candidate A:** адаптеры читают публичные источники, ничего не отправляют.
- **Порядок источников v1:** **Kwork первым** (структурированные заказы: title/desc/budget/link), затем **3 TG-канала-агрегатора** (Telethon, последние N сообщений).
- **B7 (inbound-видимость)** — второй трек, отдельно, не в v1.
- **B2 (outbound-автоотклик)** — park за юр. гейтом (ADR-002).

## 3. Альтернативы, которые рассматривались

| Ветка | Тип | Вердикт |
|---|---|---|
| B1 Pull-агрегатор | DIRECT | **Принято** |
| B2 Outbound-автоотклик | ALTERNATIVE | Park (ADR-002) |
| B5 Minimal L1-only | SIMPLIFICATION | Drop (подмножество B1) |
| B6 Отдельная фабрика | SCALE | Park (преждевременно) |
| B7 Inbound-видимость | REFRAME | Второй трек |

## 4. Consequences

- ✅ Детерминированный, безопасный (read-only), юр.-совместимый сбор.
- ⚠️ Контакт заказчика закрыт на Kwork → конверсия зависит от перехода в отклик (B2-гипотеза, фаза 2).
- ⚠️ Kwork-анти-бот: retry + backoff, `[UNKNOWN***REMOVED***`-маркеры для API-деталей.
- ✅ Подтверждён методологией IDEA EXPLORER (не ad hoc) — см. `IDEA_EXPLORER_RUN.md` §16.
