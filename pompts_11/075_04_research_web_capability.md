# ПРОМТ 74: РЕАЛИЗАЦИЯ Web Research capability (`research_web`)

> **Статус:** 🏗 ПРОМТ НА РЕАЛИЗАЦИЮ (Missing Capability #6, зарегистрирован в §20 карты v1.1)
> **Дата:** 2026-08-11
> **Источник:** SCENARIO_ENGINE_DESIGN_V1.md (§6.2/§13.2 — шаг `research` использует `research_web`), FACTORY_FORGE_ARCHITECTURE_V1.md (§20 #6, Research Factory → Research Forge), карта v1.1 (§11 Research Factory), промт 72 (§7 Research Factory: Web Research Forge)
> **Принцип (поправка):** недостающая capability — НЕ «несуществующий токен», а способность, которую нужно **построить**. Этот документ — промт на реализацию.

---

## 1. Задача

Реализовать **`research_web`** — capability веб-исследования для **Research Factory → Research Forge** (карта v1.1 §11). Результат: **Research Report** (research_report.md) — синтез веб-исследования по заданной теме.

**Что НЕ делаем в этой реализации:** не создаём Research Factory целиком, не проектируем все кузни Research Factory — только первая материальная capability `research_web` (аналог «первой материальной кузни» для Research Factory).

---

## 2. Контекст и место в архитектуре

```
Research Factory (v1.1 §11)
└── Research Forge  (результат: Research Report)
        └── Engine: Web Research Engine
                └── Tool: research_web   ← ЭТА РЕАЛИЗАЦИЯ
```

**Маппинг на существующий код:**

| Что | Где |
|-----|-----|
| Capability-контракт | CapabilityRef `{kind: tool, tool: research_web***REMOVED***` (SCENARIO_ENGINE_DESIGN §6) |
| Закрытый словарь | `research_web` — имя **Tool** (разрешение `kind: tool` → Tool Registry), НЕ модель-капабилити. В `KNOWN_CAPABILITIES` (`core_02/blueprint_v3.py`) — только genuine capability-токен `research`, и только если он реально есть в `ModelCatalog` (иначе drift-тест `test_known_capabilities_subset_of_actual_catalog` упадёт — это фича, не баг) |
| Tool Registry | Список Tools для Scenario Engine (§7: Tool Invoker вызывает drift_check/consistency_check/doctor + новый research_web) |
| Роль-исполнитель | Роли `explainer`/`lisa` (Research-разведка, v1.1 §17.1) могут использовать research_web как Tool |

---

## 3. Требования к реализации

### 3.1 Функциональные

1. **Вход:** тема/запрос исследования (строка или короткое ТЗ);
2. **Выход:** файл `research_report.md` (или stdout в `--json`-режиме):
   - цель исследования;
   - найденные источники (URL + заголовок + фрагмент);
   - проверка evidence (что подтверждено несколькими источниками);
   - синтез (выводы по теме);
   - ограничения/непроверенное (как CON-55 anti-hallucination паттерн).
3. **Режимы:**
   - `research_web "тема" --out research_report.md` — записать отчёт;
   - `research_web "тема" --json` — stdout JSON (для Scenario Engine / API);
   - `--max-sources N` — лимит источников (default 10);
   - `--timeout S` — таймаут на источник (default 10);
   - `--no-save` — без записи файла (dry-run).

### 3.2 Архитектурные (обязательные, не нарушать)

1. **ADDITIVE (CAN-16):** новый модуль `scripts_01/research_web.py`; существующие модули НЕ модифицируются (кроме пополнения закрытого словаря — см. §3.3);
2. **Безопасность (security-стандарт проекта):** веб-запросы через библиотеку (requests/httpx) с таймаутами; НЕ `shell=True`, НЕ `os.system`, НЕ прямой curl-инжект URL; валидация и экранирование;
3. **Fail-safe:** любой сбой источника → warning в отчёте + continue (не падать на одном битом URL); нет сети → degraded-отчёт с пометкой `sources_checked: 0`;
4. **Observability:** каждый вызов логируется (event_log), результат пригоден для Learning Loop (`record_learning_event`);
5. **Закрытый словарь (ANTI-6b/CON-8):** `research_web` — **имя Tool** (разрешается через Tool Registry, путь `kind: tool`), НЕ модель-капабилити. В `KNOWN_CAPABILITIES` НЕ добавляем имя тула — туда идёт только genuine capability-токен `research`, и только если он есть в `ModelCatalog` (`core_02/router.py`); иначе drift-тест `test_known_capabilities_subset_of_actual_catalog` поднимет ложную тревогу. Tool регистрируется в Tool Registry (список Tools для Scenario Engine §7).

### 3.3 Изменения в существующем коде (минимальные, аддитивные)

| Файл | Изменение |
|------|-----------|
| `core_02/blueprint_v3.py` | `KNOWN_CAPABILITIES` += `research` (genuine capability-токен) — ТОЛЬКО если он есть в `ModelCatalog`; `research_web` — имя Tool, в этот словарь НЕ добавляется |
| Tool Registry (список Tools для Scenario Engine) | `research_web` регистрируется как Tool (path: `kind: tool`) |
| `scripts_01/research_web.py` | **НОВЫЙ** — CLI + функция `research_web(query, out=None, max_sources=10, timeout=10) -> ResearchReport` |
| `tests_09/test_research_web.py` | **НОВЫЙ** — unit-тесты: вход/выход, --json, fail-safe на битый источник, vocabulary-drift (токен в KNOWN_CAPABILITIES) |

### 3.4 Качество (Code Quality Standard 040_13)

- docstrings, обработка ошибок, таймауты, идемпотентность;
- тесты: `python -m pytest tests_09/test_research_web.py -q` зелёные;
- mypy: `python -m mypy scripts_01/research_web.py --ignore-missing-imports`.

---

## 4. Что НЕ является частью реализации (scope)

- ❌ Research Factory целиком (каркас — следующий этап);
- ❌ другие кузни Research Factory (Competitive, Market, Source Verification);
- ❌ интеграция в Scenario Engine (это отдельный этап — Scenario Engine пока не реализован);
- ❌ поиск по локальным базам/knowledge_engine (это отдельный Tool).

---

## 5. Проверка приёмки (Definition of Done)

1. [ ***REMOVED*** `python scripts_01/research_web.py "конкуренты Workspace OS" --max-sources 3` → создаёт research_report.md с источниками и синтезом;
2. [ ***REMOVED*** `--json` возвращает валидный JSON (Schema: `{query, sources[***REMOVED***, synthesis, evidence_checked, degraded***REMOVED***`);
3. [ ***REMOVED*** Битый источник (недоступный URL) → warning, НЕ падение;
4. [ ***REMOVED*** Нет сети / 0 источников → degraded-отчёт `sources_checked: 0`, exit 0;
5. [ ***REMOVED*** `pytest tests_09/test_research_web.py` зелёные;
6. [ ***REMOVED*** `research_web` зарегистрирован в **Tool Registry** (путь `kind: tool`); genuine-токен `research` в `KNOWN_CAPABILITIES` — только если он есть в `ModelCatalog`; drift-тест `test_known_capabilities_subset_of_actual_catalog` остаётся зелёным;
7. [ ***REMOVED*** После реализации обновить §20 карты v1.1: `research_web` из «промт написан» → «✅ реализовано».

---

## 6. Связные документы

- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §11 (Research Factory), §20 (Missing Capability #6);
- `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` — §6.2 (CapabilityRef), §13.2 (сценарий «Создать продукт»);
- `docs_10/engineering-memory/ROLE_FORGE_MATRIX_V1.md` — explainer/lisa → Research (разведка);
- `pompts_11/040_13_code_quality_standard.md` — обязательный регламент.

---

*Промт на реализацию Missing Capability #6 (research_web). Статус: готов к исполнению после утверждения.*
