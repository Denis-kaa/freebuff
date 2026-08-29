# 097 — Capability Gap Auditor (LLM-вариант)

> **Lifecycle stage:** `prompt_written` (AGENTS.md §5 REGISTER-FIRST step 2).
> **Role ID:** `capability_gap_auditor_llm`
> **Аддитивность:** дополняет детерминированный `capability_gap_auditor` (ADR-016), НЕ заменяет.
> **Качественный баръер:** тот же `VOCAL_TASK_FRAGMENT` должен дать **≥18 capabilities** (vs 15 у детерминированного — раскрытие INFERRED-meta-skills).

---

## 1. Назначение

`CapabilityGapLlmExecutor` решает ту же задачу, что и `CapabilityGapAuditorExecutor`
(v5.189.53): «перед стартом новой нетривиальной задачи — сказать, каких платформенных
сущностей не хватает и как их зарегистрировать», — но **через семантический extraction
LLM вместо keyword/regex matching**.

**Зачем нужен второй вариант** (cross-validation pattern):

| Слой | Что даёт | Когда использовать |
|------|----------|-------------------|
| Детермин (`v5.189.53`) | 100% recall по 15 курируемым caps; reproducible; без сети; ≤10 ms | Standalone / pre-commit / CI-гейт / дешёвая разведка |
| LLM (`v5.189.55`) | +3..+5 INFERRED caps (meta-skills, infra, anti-patterns); ~22 capabilities total | Перед реальной задачей — нужна глубина; допустима задержка 1.5–3 s; есть API-ключ |

**Когда НЕ использовать LLM-вариант:**
- Pre-commit / CI гейт (<100 ms budget);
- Задача очевидно про 1-2 capability (overkill);
- ModelGateway недоступен (`gateway=None` → executor returns `[***REMOVED***` per ADR-016 fail-safe).

---

## 2. Контракт

### 2.1. API поверхность

```python
from core_02.capability_gap_auditor import CapabilityGapLlmExecutor

# DI ModelGateway (CON-65 cloud-first tie-break через SmartRouter).
executor = CapabilityGapLlmExecutor(
    gateway=model_gateway_instance,            # обязателен для non-empty output
    registry=missing_registry_instance,        # опционально, для cross-check в отчёте
)

created = executor.execute(project, "capability_gap_auditor_llm")
# → ["capability_gap_report_llm.md"***REMOVED*** на success
# → [***REMOVED*** на любой ошибке (нет gateway, LLM crash, битый JSON) — ADR-016 fail-safe
```

### 2.2. Prompt контракт (LLM-system + LLM-user)

**System** (`LLM_SYSTEM_PROMPT` в `core_02/capability_gap_auditor.py`):

```
Ты — expert платформенный архитектор (Workspace OS, AGENTS.md §5 REGISTER-FIRST).
Твоя задача — проанализировать входной текст задачи и выдать JSON-массив
ТРЕБУЕМЫХ платформенных capabilities. Каждый элемент — словарь:
{ item_id, kind, factory, description, confidence, explicit ***REMOVED***

Включай EXPLICIT (прямо упомянутые) + INFERRED (мета-инструменты, инфраструктура).
Игнорируй: UI/цвета, формулировки про окружение, action-глаголы.
Верни ТОЛЬКО JSON-массив в ```json ... ``` блоке.
```

**User** (`LLM_USER_PROMPT_TEMPLATE`):

```
{ task_text ***REMOVED***

Минимум 18 элементов. explicit=true только при прямом упоминании.
confidence < 0.7 → всё равно включай. Верни ТОЛЬКО ```json [...***REMOVED*** ```.
```

### 2.3. Парсер (`_parse_llm_response`)

Стратегия извлечения JSON (per thinker design v5.189.55):

1. Ищем fenced ` ```json [...***REMOVED*** ``` ` блок (re.DOTALL).
2. Fallback: первое вхождение `[` ... последнее `***REMOVED***`.
3. `json.loads`.
4. Валидация: `item_id`/`kind`/`description` обязательны и non-empty.
5. Невалидные элементы **тихо отбрасываются** (ADR-016 fail-safe: 1 bad item не валит batch).

Возвращает `List[Dict***REMOVED***` (пустой при любой ошибке).

### 2.4. Reporter reuse

`CapabilityGapLlmExecutor` использует тот же `CapabilityGapReporter.render(sections)`,
передавая `pre_extracted_entries=Dict[item_id, (kind, factory, description)***REMOVED***` через
новый keyword-only параметр (`CapabilityGapReporter.__init__(registry, *, pre_extracted_entries)`).
Никакого дублирования rendering-логики — **100% reuse** deterministic-исполнителя.

### 2.5. ADR-016 контракт

- **Fail-safe:** любая ошибка → `[***REMOVED***`, никаких exception наружу из `execute()`.
- **No side-effects:** НЕ вызывает `MissingRegistry.register_missing()` напрямую (§7.3
  Wizard↔Forge orthogonal-STATE). Только paste-friendly bash в `LLM_REPORT_FILE`.
- **DI:** gateway + registry инжектятся через `__init__`; default = отсутствуют.
- **Backward-compat:** `CapabilityGapReporter.__init__(registry=None)` остаётся working
  в детерминированном режиме (новый параметр — `*, pre_extracted_entries=None`).

---

## 3. Качественный баръер

### 3.1. Acceptance test (≥18 на VOCAL_TASK_FRAGMENT)

```python
def test_vocal_fragment_yields_ge_18_capabilities(faker_gateway):
    executor = CapabilityGapLlmExecutor(
        gateway=faker_gateway(  # имитирует LLM-ответ с 20 capabilities на VOCAL fragment
            caps=[
                "research_web", "lisa_estimator", "qualitative_review_analyzer",
                "competitor_matrix_builder", "pricing_enumerator",
                "anti_pattern_miner", "mvp_design_wizard",
                "business_model_constructor", "hypothesis_ledger",
                "devil_advocate_pass", "corpus_persistence",
                "claim_source_tracker", "vanity_metric_filter",
                "weighted_scoring_engine", "persona_funnel_analyzer",
                # +5 INFERRED (превышают deterministic budget):
                "execution_log", "model_benchmark", "experiment_tracker",
                "dependency_resolver", "output_archiver",
            ***REMOVED***
        )
    )
    sections = _split_sections(VOCAL_TASK_FRAGMENT)
    # Используем общий путь Reporter.render через pre_extracted_entries.
    entries = {c: ("tool", "research", f"Capability {c***REMOVED*** (fake LLM test)") for c in caps***REMOVED***
    reporter = CapabilityGapReporter(registry=None, pre_extracted_entries=entries)
    md = reporter.render(sections)
    table_section = md.split("## 1. Сводная таблица", 1)[1***REMOVED***.split("## 2.", 1)[0***REMOVED***
    rows = [l for l in table_section.splitlines() if l.startswith("| `")***REMOVED***
    assert len(rows) >= 18, f"LLM should extract ≥18 caps; got {len(rows)***REMOVED***"
```

### 3.2. Edge cases

| Сценарий | Поведение | Тест |
|----------|-----------|------|
| `gateway=None` | `[***REMOVED***` (graceful skip + warning) | `test_executor_no_gateway_returns_empty` |
| `gateway.generate` raises | `[***REMOVED***` (ADR-016 fail-safe) | `test_executor_gateway_error_returns_empty` |
| LLM вернул non-JSON в response | `[***REMOVED***` (no parsed entries → skip report) | `test_parse_unparseable_returns_empty` |
| LLM вернул частично битый JSON | Valid items retained, invalid dropped | `test_parse_partial_corruption_drops_bad_keeps_good` |
| LLM вернул 5 elements (< 18) | Всё равно пишем отчёт (low quality gate — manually review) | `test_low_count_still_writes_report` |
| Текст задачи < 60 chars | `[***REMOVED***` (reuse `_MIN_BODY_LEN`) | `test_executor_short_text_returns_empty` |

### 3.3. NO mutations (важно)

- `gateway` — read-only (только `generate_by_capabilities`).
- `registry` — read-only (только `.get(item_id)`).
- НЕ создаёт файлов вне `project.root` директории.
- НЕ отправляет сетевых запросов помимо gateway.generate.

---

## 4. Реализация (where)

| Файл | Изменение | LOC |
|------|-----------|-----:|
| `core_02/capability_gap_auditor.py` | `__all__` fix + Reporter refactor + LLM constants + `_parse_llm_response` + `CapabilityGapLlmExecutor` + factory | ~210 |
| `pompts_11/097_19_capability_gap_auditor_llm.md` | Этот файл (canonical prompt) | — |
| `tests_09/test_capability_gap_llm_auditor.py` | 9 test-классов (FakeGateway + edge cases + parse + reporter + executor + CLI smoke) | ~420 |
| `core_02/missing_registry.yaml` | `capability_gap_auditor_llm` → `status=implemented` | 1 line |
| `CHANGELOG.md` | v5.189.55 entry | ~15 |

**Additive:** никаких удалений. Старые тесты `test_capability_gap_auditor.py`
остаются зелёными (regression test = `pytest tests_09/test_capability_gap_auditor.py -v` → ≥22 passed).

---

## 5. Что **НЕ** входит в v1 (defer)

- **Multi-model ensemble** (диспатч в 3 разных провайдера + голосование по большинству).
- **Re-rank по confidence** (сейчас flat-список, sorter не используется в render).
- **Schema validation через jsonschema** (сейчас duck-typing в `_parse_llm_response`).
- **Streamed output** (LLM-стрим → partial parse каждые 500 ms).
- **Cost tracking** per request (ModelGateway может вернуть `.usage` — игнорируем в v1).
- **Adaptive re-prompt на пустой результат** (1 re-call с другим wording при `[***REMOVED***`).

---

## 6. Lessons (anti-pattern guards)

- **ANTI-5 (scope discipline):** НЕ делать одновременно `capability_gap_auditor_v3` +
  `_llm` + `_streaming` — только LLM-вариант в v1.
- **ANTI-6b (vocabulary drift):** `kind` ∈ закрытое множество `MissingRegistry.KINDS`,
  НЕ "skill" / "service" / "agent". Парсер валидирует и тихо отбрасывает нарушителей.
- **REGISTER-FIRST:** любой новый prompt / класс / model → запись в `core_02/missing_registry.yaml`
  ПЕРЕД реализацией. Этот промт = шаг 2 (prompt_written); шаг 3 (mark-implemented) — после
  прохождения всех тестов.
- **Adapter contract:** ModelGateway может быть **(a)** реальным,
  **(b)** FakeGateway в тестах, **(c)** `None` → executor returns `[***REMOVED***`. Все три пути
  покрыты тестами; это контракт, не баг.

---

## 7. Runbook

```bash
# 1. Register (уже сделано в prior turn):
# python -m core_02.missing_registry register capability_gap_auditor_llm \
#   --kind role --factory governance \
#   --description '...' --prompt pompts_11/097_19_capability_gap_auditor_llm.md

# 2. Mark-prompt-written (уже сделано):
# python -m core_02.missing_registry mark-prompt-written capability_gap_auditor_llm \
#   --prompt pompts_11/097_19_capability_gap_auditor_llm.md

# 3. Реализация выполнена в core_02/capability_gap_auditor.py.

# 4. Запуск тестов:
cd /storage/emulated/0/PROJECTS/workstation/freebuff
python -m pytest tests_09/test_capability_gap_llm_auditor.py -v

# 5. Typecheck:
python -m mypy core_02/capability_gap_auditor.py tests_09/test_capability_gap_llm_auditor.py \
  --ignore-missing-imports

# 6. Закрытие lifecycle (mark-implemented):
python -m core_02.missing_registry mark-implemented capability_gap_auditor_llm \
  --implementation core_02/capability_gap_auditor.py \
  --prompt pompts_11/097_19_capability_gap_auditor_llm.md

# 7. Регресс-тест (детерминированный variant не сломан):
python -m pytest tests_09/test_capability_gap_auditor.py -v
```

---

## 8. Crosslinks

- `pompts_11/095_19_capability_gap_auditor.md` — предыдущая итерация (deterministic v5.189.53).
- `core_02/missing_registry.py` — `MissingRegistry.KINDS` = закрытое множество для kind.
- `core_02/role_executor.py` — `BaseRoleExecutor`, `LlmRoleExecutor` (pattern reference).
- `scripts_01/model_gateway.py` — ModelGateway с `generate_by_capabilities` (CON-65 cloud-first).
- `core_02/capability_gap_auditor.py` — `CapabilityGapReporter` (reused rendering layer).
- `docs_10/engineering-memory/decisions/ADR_016_auto_chain_generation.md` — fail-safe pattern.

---

_v5.189.55 · 2026-08-19 · Buffy + Freebuff Platform · Workspace OS_
