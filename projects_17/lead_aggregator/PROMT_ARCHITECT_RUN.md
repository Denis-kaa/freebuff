# ПРОМТ АРХИТЕКТОР 1.7 — Прогон: Attract-модуль (Lead Aggregator)

> **Промт:** `pompts_11/071_02_prompt_architect_1_7.md` стр. 1–372 (встроенный ПРОМТ АРХИТЕКТОР 1.7) — границы уточнены 2026-08-10 (live-grep, строка 373 = `IDEA EXPLORER v2.0`); ранняя оценка «1–380» исправлена, см. `docs_10/templates/PIPELINE_TEMPLATE.md` §0
> **Дата:** 2026-08-10 · **Агент:** Buffy (z-ai/glm-5.2)
> **Вход:** handoff из [`IDEA_EXPLORER_RUN.md`***REMOVED***(IDEA_EXPLORER_RUN.md) §18 (Candidate A — Pull-агрегатор v1)
> **Назначение:** скомпилировать выбранную концепцию в исполнимый base prompt для Фазы 3 (код) — закрывает пробел «промт-архитектор не применялся к пайплайну/фабрике».

---

## 1. INPUT ANALYSIS

- **Тип задачи:** код / продукт (модуль платформы Workspace OS).
- **Целевая платформа:** Termux / Android (ARM64), Python 3.14.6, SQLite-only.
- **Ожидаемый результат:** автономный pull-агрегатор заказов: адаптеры (Kwork + TG-каналы) → нормализация → L1/L2/L3-классификация → доставка в TG-бот.
- **Уровень сложности:** COMPLEX (multi-stage, требует декомпозиции).
- **Отсутствующие критические параметры:** стабильность Kwork-разметки (не проверить до запуска), доступность каналов-агрегаторов (зависит от внешнего мира).
- **Нереалистичные требования:** нет (pull-модель реалистична; outbound-отклики исключены юр.-гейтом W-7).
- **Источники галлюцинаций:** выдуманные API-эндпоинты Kwork, выдуманные лимиты, «гарантированные» контакты заказчиков.

## 2. FEASIBILITY GATE

**REALITY:**
- ✅ возможно средствами платформы: httpx (есть), telethon (есть), ModelGateway (есть), SQLite (есть).
- ✅ не требует несуществующих функций: TLSClient абстракция с fallback на httpx (PHASE2), CheckpointStore на SQLite.
- ⚠️ требует доступа к данным: публичные TG-каналы (доступны), Kwork-страницы (доступны, но без телефонов — контакт через отклик, учтено в дизайне).
- ✅ соответствует платформе: аддитивный пакет `projects_17/lead_aggregator/`.
- ✅ нет скрытого противоречия: «искать заказы» и «не спамить» совместимы в pull-модели.

**ANTI-HALLUCINATION:** неизвестные параметры помечаются `[KWORK_API***REMOVED***`, `[CHANNEL_URL***REMOVED***`, `[MODEL_GATEWAY_KEY***REMOVED***` — не выдумываются.

## 3. IDEA COMPILER

RAW IDEA → NORMALIZED SPECIFICATION → EXECUTABLE PROMPT

**Сохранить:** цель (автономный поиск заказов), ограничения (read-only, юр.-гейт, аддитивность), контекст (стек пользователя), результат (список заказов с релевантностью).
**Удалить:** эмоциональный шум («мечта», «горящие»), маркетинг, противоречия (outbound против юр.-гейта), лишние объяснения.

## 4. ROLE SELECTION

**Senior AI Systems Engineer / Workspace OS Platform Module Developer** — функциональная роль под задачу.

## 5. BASE PROMPT COMPILER

```text
ROLE
Senior AI Systems Engineer, разработчик модуля Workspace OS (Termux/Android).

OBJECTIVE
Реализовать pull-агрегатор заказов (Attract-модуль v1) по утверждённой
архитектуре PHASE2_ARCHITECTURE.md: Kwork + 3 TG-канала → нормализация →
L1/L2/L3-классификация → доставка уведомлений в TG-бот платформы.

CONTEXT
- Платформа: Workspace OS (Termux, Python 3.14.6, SQLite-only).
- Существующие модули (reuse, не дублировать): scripts_01/model_gateway.py
  (L3-скоринг), core_02/_tg_client_v2.py (Telethon-паттерн),
  scripts_01/notification.py (TG-доставка), scripts_01/tool_runtime.py.
- Документы: PHASE1_RESEARCH.md §2-§6 (матрица уязвимостей, W-1..W-13),
  PHASE2_ARCHITECTURE.md (утверждена), ROADMAP.md (этапы).
- Правила платформы: AGENTS.md (canonical), CON-40 (capability-check),
  ANTI-5 (scope discipline), аддитивность (только projects_17/lead_aggregator/).

INPUT
- Запрос пользователя (стек/ниша): "разработка Telegram-ботов" (пример).
- Список источников: Kwork (страницы поиска), 3 TG-канала-агрегатора.

EXECUTION PLAN
1. Скаффолд пакета по PHASE2 (TLSClient абстракция, CheckpointStore, adapter-интерфейс).
2. Адаптер Kwork: fetch страниц поиска → парсинг заказов (title, desc, budget, link) → нормализация в LeadRecord.
3. Адаптер TG: Telethon чтение последних N сообщений каналов → нормализация в LeadRecord.
4. Классификатор: L1 regex-словарь (ниша) → L2 intent-правила → L3 ModelGateway score 0-100.
5. Порог релевантности (>=70) → доставка в TG-бот (notification.py).
6. CheckpointStore: дедупликация по хешу заказа, last-seen для каналов.
7. Тесты: unit (адаптеры-моки, классификатор, store) + интеграция (dry-run).
8. Юридический гейт: read-only, без автопостинга в чужие каналы, без outbound.

CONSTRAINTS
- Только существующие зависимости (httpx, telethon); curl_cffi/playwright — optional (W-2).
- SQLite (W-3): CheckpointStore, не PostgreSQL/Redis.
- Без модификаций core_02/scripts_01 (аддитивность).
- Антив-галлюцинация: реальные API/лимиты помечать [UNKNOWN***REMOVED***, не выдумывать.

OUTPUT CONTRACT
- Код в projects_17/lead_aggregator/app/ (модуль + тесты).
- 26+ тестов зелёные (python -m pytest projects_17/lead_aggregator/).
- STEPS.md обновлён (этапы с acceptance), LESSONS.md — CON-/ANTI- находки.
- Команда запуска: python -m projects_17.lead_aggregator.app.cli --dry-run.

FAILURE HANDLING
- Kwork недоступен/капча → retry с backoff, пометка в логе, не падать.
- ModelGateway недоступен → fallback на L2-only (детерминированный скор).
- Канал закрыт → пропустить, записать в CheckpointStore.
- Результат не проверяется → dry-run режим по умолчанию.

PROHIBITIONS
- НЕ отправлять outbound-сообщения заказчикам (юр.-гейт W-7).
- НЕ парсить приватные данные сверх публичного контента.
- НЕ трогать core_02/, scripts_01/ (0 изменений).
- НЕ добавлять зависимости без необходимости.
```

## 6. COMPLEXITY ROUTER

**COMPLEX** → декомпозиция: INPUT → ANALYSIS → PLANNING (PHASE2 done) → EXECUTION (этапы 1-7) → VALIDATION (тесты) → OUTPUT (STEPS/LESSONS). Декомпозиция на этапы уже выполнена в ROADMAP.md (atomic-шаги с acceptance).

## 7. EXTENSIONS

- **EXTENSION 1 — ANTI-HALLUCINATION:** требуется (внешние данные: Kwork, TG). Строка «Антив-галлюцинация: проверено» включена в CONSTRAINTS/FAILURE_HANDLING.
- **EXTENSION 3 — SCALING:** требуется (COMPLEX): промежуточные проверки (тесты после каждого адаптера), точки подтверждения (ревью перед деплоем), rollback (dry-run), контроль состояния (CheckpointStore), обработка ошибок (FAILURE_HANDLING), критерии завершения (26+ тестов).
- **EXTENSION 4 — PLATFORM ADAPTER:** требуется (Termux/Python 3.14.6/SQLite) — учтено в CONTEXT/CONSTRAINTS.
- EXTENSION 2 (IDEA IMPROVEMENT) — не требуется: идея уже улучшена на этапе IDEA EXPLORER (B7-трек отдельно).

## 8. CONSISTENCY GATE

- [x***REMOVED*** Цель не изменилась (автономный поиск заказов).
- [x***REMOVED*** Нет противоречивых инструкций (pull-модель vs юр.-гейт согласованы).
- [x***REMOVED*** Нет выдуманных возможностей ([UNKNOWN***REMOVED***-маркеры).
- [x***REMOVED*** Все критические входные данные определены ([CHANNEL_URL***REMOVED*** переменные).
- [x***REMOVED*** Шаги необходимы (7 шагов = 7 модулей PHASE2).
- [x***REMOVED*** Output Contract однозначен (код + 26 тестов + STEPS/LESSONS + команда).
- [x***REMOVED*** Запреты не конфликтуют с целью.
- [x***REMOVED*** Extensions действительно нужны (1, 3, 4 — да).
- [x***REMOVED*** Промт не перегружен (base + 3 extensions, не 10).
- [x***REMOVED*** Повторения удалены.
- [x***REMOVED*** Промт можно непосредственно передать целевой модели.

## 9. STYLE FILTER — ANTI-DUST

✅ без маркетинга · ✅ сухой/точный/компактный · ✅ каждая инструкция изменяет поведение или удалена.

## 10. OUTPUT FORMAT

**ANALYSIS:** COMPLEX, реальзуемо на платформе, требует декомпозиции (7 этапов); 2 неизвестных ([KWORK_API***REMOVED***, [CHANNEL_URL***REMOVED***) помечены.
**IMPROVED IDEA:** не требуется (IDEA EXPLORER уже улучшил: B7-трек, outbound-парк).
**BASE PROMPT:** см. §5.
**EXTENSIONS:** 1 (anti-hallucination) + 3 (scaling) + 4 (platform adapter).
**FINAL CHECK:** ✅ цель сохранена · ✅ шаги проверяемы · ✅ output однозначен · ✅ запреты согласованы.

**Антив-галлюцинация: проверено.**

---

## Вывод

ПРОМТ АРХИТЕКТОР 1.7 применён к пайплайну Attract-модуля: входная концепция (из IDEA EXPLORER Candidate A) скомпилирована в исполнимый base prompt для Фазы 3. Промт подтверждает, что PHASE2_ARCHITECTURE.md соответствует всем 11 пунктам CONSISTENCY GATE — архитектура готова к кодированию без переделок.
