# ADR_014: Attract-модуль (Lead Aggregator) — pull-агрегатор, Candidate A

**Status:** Accepted (Proposed 2026-08-10, encoded v5.146.0 — ADR-файл создан в документационном слое; решение принято на Фазе 2, код v1 ранее)
**Component:** `projects_17/lead_aggregator/` — Attract-модуль платформы (автономный поиск заказов)
**Deciders:** Buffy (autonomous), User (operator — утвердил Фазу 2: Kwork первым, топ-3 компетенции, юр. гейт)
**Supersedes:** N/A (новый модуль платформы)
**Related:** [pompts_11/070_07_lead_aggregator_scraper.md***REMOVED***(../../../pompts_11/070_07_lead_aggregator_scraper.md) (Lead Aggregator), [pompts_11/071_02_prompt_architect_1_7.md***REMOVED***(../../../pompts_11/071_02_prompt_architect_1_7.md) (PIPELINE_TEMPLATE + 2 встроенных промта), [P3 IDEA EXPLORER RUN***REMOVED***(../../../projects_17/lead_aggregator/IDEA_EXPLORER_RUN.md), [P3 PROMT ARCHITECT RUN***REMOVED***(../../../projects_17/lead_aggregator/PROMT_ARCHITECT_RUN.md), ADR-013 (ForgeFacade — параллельный трек P3)

---

## 1. Context

Пользователь — AI-фрилансер (Python, TG-боты, FastAPI, лендинги; реальный стек собран из живых артефактов телефона — резюме, KWORK-ledger, portfolio). Задача промт 69: **Lead Aggregator / Attract-модуль** — программа, которая сама находит клиентов по запросам («разработка Telegram-ботов»), смотрит по всему интернету (биржи, TG-каналы, вакансии), а не только по шаблонам.

Ограничения платформы (W-2..W-5 из PHASE1_RESEARCH): Termux/ARM64, Python 3.14.6, SQLite-only; отсутствуют curl_cffi/playwright/PG/Redis. Юридический гейт (W-7): сбор лидов — зона риска (ToS, 152-ФЗ, GDPR), требуется policy-гейт до деплоя адаптеров.

## 2. Decision

Реализовать **Attract-модуль v1 как pull-агрегатор (IDEA EXPLORER Candidate A)**, подтверждённый прогоном IDEA EXPLORER v2.0 (7 веток → prune → 3 кандидата → A):

1. **Pull-модель (read-only):** адаптеры читают публичные источники (Kwork-страницы поиска + 3 TG-канала-агрегатора) → нормализация в LeadRecord.
2. **Классификация L1→L2→L3:** regex-словарь (ниша) → intent-правила → ModelGateway score 0–100; порог ≥70 → доставка.
3. **Доставка в существующий TG-бот платформы** (reuse `scripts_01/notification.py`, паттерн Telethon из `core_02/_tg_client_v2.py`).
4. **Абстракции под ограничения:** `TLSClient` (httpx; curl_cffi — optional), `ProxyRotator` (stub), `CheckpointStore` (SQLite v1, дедупликация по хешу заказа).
5. **Аддитивность:** только `projects_17/lead_aggregator/`, 0 изменений в `core_02/`/`scripts_01/`.
6. **Юридический гейт:** read-only, без outbound-сообщений заказчикам (B2-ветка — park за гейтом W-7), без приватных данных.
7. **Второй трек B7 (inbound-видимость)** — отложен отдельно (автопубликация кейсов), не в v1.

## 3. Альтернативы, которые рассматривались (IDEA EXPLORER, 7 веток)

| Ветка | Тип | Вердикт |
|---|---|---|
| B1 Pull-агрегатор | DIRECT | **Принято (Candidate A)** — score 41, реалистично |
| B2 Outbound-автоотклик | ALTERNATIVE | **Park** — юридический риск W-7 |
| B3 HR-агент-мост | ADJACENT | **Merge → B1** (HR-агент как потребитель) |
| B4 TG-бот-интеграция | COMBINATION | **Merge → B1** (доставка через существующий бот) |
| B5 Minimal L1-only | SIMPLIFICATION | **Drop** (подмножество B1) |
| B6 Отдельная фабрика | SCALE | **Park** (преждевременно, Modes A-G незрелы) |
| B7 Inbound-видимость | REFRAME | **KEEP** (второй трек; reframe «заказы ищут тебя») |

**Critical decision point:** контакты заказчиков закрыты (Kwork — через отклик) → pull-агрегатор + TG-каналы (публичны) = реалистичный путь; inbound (B7) — усиление в фазе 2.

## 4. Consequences

### Положительные
- Автономный поиск заказов без ручного труда; детерминированный, безопасный (read-only).
- Reuse платформы (ModelGateway, Telethon-паттерн, notification) — без дублирования.
- Проверяемость: 26+ тестов, dry-run режим по умолчанию, CheckpointStore-дедупликация.
- Методология зафиксирована: IDEA EXPLORER + ПРОМТ АРХИТЕКТОР прогоны (промт 70) — пайплайн создан по встроенным промтам, не ad hoc.

### Отрицательные / риски
- Kwork-разметка может меняться (анти-бот) → retry + backoff, `[UNKNOWN***REMOVED***`-маркеры.
- ModelGateway недоступен → fallback на L2-only (детерминированный скор).
- Контакты заказчиков вне платформы (Kwork-отклик) — конверсия зависит от перехода в отклик (B2-гипотеза в фазе 2).
- Юридический гейт — must-have перед деплоем в бой (W-7): policy-гейт отсутствует на платформе (слабый слой).

## 5. Implementation notes (v5.145.0)

- Фаза 2 (архитектура) утверждена: `PHASE2_ARCHITECTURE.md` (Kwork первым, топ-3 компетенции, юр. гейт).
- Фаза 3 (код v1) выполнена: `app/` + `config/`, **26 тестов зелёные** (см. ROADMAP.md roll-up).
- Прогоны встроенных промтов 071_02_prompt_architect_1_7: `IDEA_EXPLORER_RUN.md` (§1-§23) + `PROMT_ARCHITECT_RUN.md` (§1-§10, исполнимый base prompt для Фазы 3).
- Паспорт проекта: `MANIFEST.md` (этот пакет).
