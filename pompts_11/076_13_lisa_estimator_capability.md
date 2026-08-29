# ПРОМТ 75: РЕАЛИЗАЦИЯ Estimation capability (`lisa_estimator`)

> **Статус:** 🏗 ПРОМТ НА РЕАЛИЗАЦИЮ (Missing Capability #7, зарегистрирован в §20 карты v1.1)
> **Дата:** 2026-08-11
> **Источник:** FACTORY_FORGE_ARCHITECTURE_V1.md (§20 #7, Research Factory → Research Forge → Estimation Engine), ROLE_FORGE_MATRIX_V1.md (§5.3/§8 Q2 — lisa → Research Factory, будущая Estimation Engine; LISA Estimator), blueprints_v3/03_lisa_estimator.md (роль LISA-3), SCENARIO_ENGINE_DESIGN_V1.md (§10: lisa → Research (будущая), output lisa_report.md), промт 72 (§7 Research Factory)
> **Принцип (поправка):** недостающая capability — НЕ «несуществующий токен», а способность, которую нужно **построить**. Этот документ — промт на реализацию.

---

## 1. Задача

Реализовать **`lisa_estimator`** — capability оценки сложности проекта (LISA-3 AI-Native Complexity Estimator) для **Research Factory → Research Forge → Estimation Engine**. Результат: **LISA Report** (lisa_report.md + метрики) — оценка сложности проекта по фреймворку LISA-3.

**Что НЕ делаем в этой реализации:** не создаём Research Factory целиком, не проектируем все кузни Research Factory, не решаем «Forge или Engine» окончательно (§8 Q2 матрицы — на этапе паспортов Research Factory). Реализуем только первую материальную capability `lisa_estimator` (аналог «первой материальной кузни»).

---

## 2. Контекст и место в архитектуре

```
Research Factory (v1.1 §11, будущая)
└── Research Forge  (результат: Research Report / Estimation)
        └── Engine: Estimation Engine
                └── Tool: lisa_estimator   ← ЭТА РЕАЛИЗАЦИЯ
```

**Маппинг на существующий код:**

| Что | Где |
|-----|-----|
| Capability-контракт | CapabilityRef `{kind: tool, tool: lisa_estimator***REMOVED***` (SCENARIO_ENGINE_DESIGN §6) |
| Роль-исполнитель | Роль `lisa` (Blueprint v3, `03_lisa_estimator.md`) — LISA-3 AI-Native Complexity Estimator; LIGHT · check_only сегодня (forge_facade) |
| Закрытый словарь | `lisa_estimator` — имя **Tool** (разрешение `kind: tool` → Tool Registry), НЕ модель-капабилити. Genuine capability-токен `estimation` — в `KNOWN_CAPABILITIES` (`core_02/blueprint_v3.py`) ТОЛЬКО если он реально есть в `ModelCatalog` (иначе drift-тест `test_known_capabilities_subset_of_actual_catalog` упадёт — это фича, не баг) |
| Tool Registry | Список Tools для Scenario Engine (§7: drift_check, consistency_check, doctor, research_web + новый lisa_estimator) |
| Выход роли | `lisa_report.md` (DEFAULT_ROLE_OUTPUTS, forge_facade.py), + калибровка `lisa_calibration.yaml` (обновляется retrospective) |

---

## 3. Требования к реализации

### 3.1 Функциональные

1. **Вход:** описание проекта/ТЗ (строка, файл `brief.md`/`parsed_requirements.md` или stdin);
2. **Выход:** файл `lisa_report.md` (или stdout в `--json`-режиме):
   - оценка **engineering complexity** (0–10);
   - оценка **AI-native complexity** (сложность автономной AI-реализации, 0–10);
   - **verification burden** (0–10);
   - **operational risk** и **production risk** (0–10);
   - **AI suitability** (насколько проект подходит для AI-реализации, 0–10);
   - итоговый вердикт (например, GO / COND / NO-GO или рейтинг сложности);
   - обоснование каждой оценки (по какому признаку).
3. **Режимы:**
   - `lisa_estimator "описание проекта" --out lisa_report.md` — записать отчёт;
   - `lisa_estimator --json` — stdout JSON (для Scenario Engine / API);
   - `--input brief.md` — вход из файла (parsed_requirements.md);
   - `--calibrate lisa_calibration.yaml` — принять файл калибровки (веса осей, прошлые проекты);
   - `--no-save` — без записи файла (dry-run).

### 3.2 Архитектурные (обязательные, не нарушать)

1. **ADDITIVE (CAN-16):** новый модуль `scripts_01/lisa_estimator.py`; существующие модули НЕ модифицируются (кроме пополнения закрытого словаря — см. §3.3);
2. **Безопасность (security-стандарт проекта):** никаких `exec`/`eval`, НЕ `shell=True`, НЕ `os.system`; входные файлы читаются только (read-only); валидация типов;
3. **Fail-safe:** нет входных данных / битый файл → degraded-отчёт `estimated: false` + exit 0 (как research_web: `sources_checked: 0`);
4. **Determinism:** без внешних LLM-вызовов — оценка по эвристикам/признакам из описания (детерминированный пайплайн, пригодный для unit-тестов). LLM-синтез — будущий этап (Estimation Forge с Engines, §8 Q2);
5. **Observability:** каждый вызов логируется (EventBus + Learning Loop best-effort, паттерн `_emit_events` из research_web);
6. **Закрытый словарь (ANTI-6b/CON-8):** `lisa_estimator` — имя Tool (Tool Registry, `kind: tool`). Genuine-токен `estimation` в `KNOWN_CAPABILITIES` — только если он есть в `ModelCatalog` (иначе drift-тест поднимет ложную тревогу).

### 3.3 Изменения в существующем коде (минимальные, аддитивные)

| Файл | Изменение |
|------|-----------|
| Tool Registry (список Tools для Scenario Engine) | `lisa_estimator` регистрируется как Tool (path: `kind: tool`) |
| `core_02/blueprint_v3.py` | `KNOWN_CAPABILITIES` += `estimation` (genuine capability-токен) — ТОЛЬКО если он есть в `ModelCatalog`; `lisa_estimator` — имя Tool, в этот словарь НЕ добавляется |
| `core_02/router.py` | `ModelCatalog.default()` += capability `estimation` (синхронно с KNOWN_CAPABILITIES) |
| `scripts_01/lisa_estimator.py` | **НОВЫЙ** — CLI + функция `lisa_estimator(description, out=None, calibrate=None) -> LisaReport` |
| `tests_09/test_lisa_estimator.py` | **НОВЫЙ** — unit-тесты: вход/выход, --json, fail-safe (пустой вход), vocabulary-drift (токен в KNOWN_CAPABILITIES) |

### 3.4 Качество (Code Quality Standard 040_13)

- docstrings, обработка ошибок, валидация входных данных, детерминизм;
- тесты: `python -m pytest tests_09/test_lisa_estimator.py -q` зелёные;
- mypy: `python -m mypy scripts_01/lisa_estimator.py --ignore-missing-imports`.

---

## 4. Что НЕ является частью реализации (scope)

- ❌ Research Factory целиком (каркас — следующий этап);
- ❌ решение «Estimation Forge vs Engine» (ROLE_FORGE_MATRIX §8 Q2 — при паспортах Research Factory);
- ❌ интеграция в Scenario Engine (это отдельный этап — Scenario Engine пока не реализован);
- ❌ LLM-синтез текста обоснования (детерминированные эвристики — достаточно для v1);
- ❌ обновление калибровки `lisa_calibration.yaml` из retrospective (это роль retrospective, Evolution Forge).

---

## 5. Проверка приёмки (Definition of Done)

1. [ ***REMOVED*** `python scripts_01/lisa_estimator.py "веб-платформа с каталогом, корзиной и оплатой" --out lisa_report.md` → создаёт lisa_report.md с оценками осей LISA-3 и вердиктом;
2. [ ***REMOVED*** `--json` возвращает валидный JSON (Schema: `{description, scores{...***REMOVED***, verdict, calibrated, degraded***REMOVED***`);
3. [ ***REMOVED*** Пустой/битый вход → degraded-отчёт `estimated: false`, exit 0;
4. [ ***REMOVED*** `pytest tests_09/test_lisa_estimator.py` зелёные;
5. [ ***REMOVED*** `lisa_estimator` зарегистрирован в **Tool Registry** (путь `kind: tool`); genuine-токен `estimation` в `KNOWN_CAPABILITIES` + `ModelCatalog` синхронно; drift-тест `test_known_capabilities_subset_of_actual_catalog` остаётся зелёным;
6. [ ***REMOVED*** После реализации обновить §20 карты v1.1: `lisa_estimator` из «промт написан» → «✅ реализовано».

---

## 6. Связные документы

- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §11 (Research Factory), §20 (Missing Capability #7);
- `docs_10/engineering-memory/ROLE_FORGE_MATRIX_V1.md` — §5.3 (Research Factory → Estimation Engine), §8 Q2 (lisa — новая кузня?);
- `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` — §6.2 (CapabilityRef), §10 (lisa → Research (будущая));
- `blueprints_v3/03_lisa_estimator.md` — роль LISA-3 (фреймворк оценок, вне workspace — read-only);
- `pompts_11/040_13_code_quality_standard.md` — обязательный регламент.

---

*Промт на реализацию Missing Capability #7 (lisa_estimator / Estimation Engine). Статус: готов к исполнению после утверждения.*
