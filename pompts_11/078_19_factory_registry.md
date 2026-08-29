# ПРОМТ: Factory Registry — машиночитаемые паспорта кузен (Missing Capability #1)

> **Тип:** реализация (register-first, шаг 2 — промт на реализацию)
> **Статус в MissingRegistry:** `prompt_written` (после mark-prompt-written)
> **Дата:** 2026-08-11
> **Дизайн (источник истины):** `docs_10/engineering-memory/FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` (вердикт: гибрид «YAML-манифест + dataclass `ForgePassport` + `FactoryRegistry`», Вариант C)
> **Закрывает:** Missing Capability #1 карты v1.1 (FACTORY_FORGE_ARCHITECTURE_V1.md §20, строка 1) + открытый вопрос №1 паспортов v1.1 + Required Action 4 ARB-REV-003

---

## 1. Задача

Реализовать **Factory Registry** — машиночитаемый реестр фабрик и паспортов кузен (Forge Passport), по образцу уже существующего паттерна `ScenarioManifest.from_yaml() → ScenarioRegistry`:

```
runtime_05/factories/<factory_id>/<forge_id>.yaml   ← источник истины (декларативный)
        │  ForgePassport.from_yaml()
        ▼
dataclass ForgePassport                              ← типизированная модель (валидация, API)
        │
        ▼
FactoryRegistry                                      ← авто-discovery + query API (как ScenarioRegistry)
```

**Аддитивность (CAN-16):** НЕ модифицировать `scenario.py`, `scenario_registry.py`, `forge_registry.py`, `blueprint_v3.py`. Только новые модули + новые YAML-манифесты.

## 2. DoD (Definition of Done)

1. **`core_02/forge_passport.py`** (новый) — `@dataclass(frozen=True) ForgePassport`:
   - поля 9-полей карты v1.1: `mission, inputs, production_workflow, engines, quality_gates, outputs, artifacts, interfaces, memory, knowledge` + реестровые `forge_id, factory_id, version, status (design|material|production), display_name, capabilities, metadata`;
   - `from_yaml(path)` (как `ScenarioManifest.from_yaml`), `to_yaml()` (round-trip), `to_dict()` (JSON-конвенция `ForgeStatus.to_dict`);
   - `validate()` → list[str***REMOVED*** — B10/R-127 машинные инварианты: forge_id lowercase-slug непустой, mission непустой, status ∈ {design, material, production***REMOVED***, outputs непустые (одна Forge = один производственный результат), capabilities ⊆ `KNOWN_CAPABILITIES` (закрытый словарь, ANTI-6b);
   - `REQUIRED_FIELDS` экспорт.
2. **`core_02/factory_registry.py`** (новый) — `FactoryRegistry`:
   - авто-discovery из `runtime_05/factories/<factory_id>/*.yaml` (или `$FREEBUFF_FACTORIES_DIR`); `factory.yaml` — метаданные фабрики (НЕ дублирование паспортов);
   - query API: `list_factories()`, `list_forges(factory_id)`, `get_forge(factory_id, forge_id)`, `find_by_capability(capability)` (мост к Scenario Engine §6.2), `validate_all()`, `warnings()`;
   - fail-safe: битый манифест → warning, не крашится; cross-check `factory_id == директория`; дубликаты forge_id игнорируются с warning.
3. **`runtime_05/factories/`** (новый) — `README.md` (формат манифеста) + `architecture/factory.yaml` + `architecture/review.yaml` (первая материальная кузня) + `architecture/governance.yaml` (вторая).
4. **Тесты** `tests_09/test_forge_passport.py` + `tests_09/test_factory_registry.py` (паттерн `test_scenario_registry.py`): happy-path from_yaml, missing required keys → ValueError, vocabulary drift → violation, cross-check factory_id, duplicate forge_id, validate_all, find_by_capability.
5. **§20 карты v1.1** (FACTORY_FORGE_ARCHITECTURE_V1.md, строка 1) — `Factory Registry` → «✅ реализовано (... по промту pompts_11/078_19_factory_registry.md)».
6. **MissingRegistry** — `mark-implemented factory_registry --implementation core_02/factory_registry.py --prompt pompts_11/078_19_factory_registry.md`; `check` → ok.

## 3. Ключевые решения (из дизайна, не менять)

- **Гибрид, не «или-или»:** YAML — источник истины; dataclass — типизированная runtime-модель; реестр — авто-discovery. Повторяет `ScenarioManifest → ScenarioRegistry` 1:1.
- **Списки → tuple** (иммутабельность, конвенция `scenario.py`); **`frozen=True`** (паспорт — неизменяемый контракт).
- **`_as_tuple` module-level helper** — НЕ-scalar (например, dict вместо списка) → `ValueError` (громкая ошибка, не тихая потеря данных B10/R-127).
- **`capabilities`** — мост к Scenario Engine (CapabilityRef) + закрытый словарь ANTI-6b.
- **Границы (B-Rule 4/5):** FactoryRegistry ≠ ForgeRegistry (паспорта кузен vs статусы проектов) ≠ ScenarioRegistry (мощности vs сценарии). Никакой параллельной системы.
- **Нейминг:** `runtime_05/factories/<factory_id>/<forge_id>.yaml` + один `factory.yaml` на фабрику.

## 4. Пример манифеста (review.yaml, из дизайна §4.3)

```yaml
forge_id: review
factory_id: architecture
display_name: Architecture Review Forge
version: "1.0.0"
status: material
mission: "Проверить архитектурное решение: можно ли его принимать"
inputs: [architectural_problem, architecture, models, constraints, relevant_decisions***REMOVED***
production_workflow: [problem_validation, context_analysis, impact_analysis, verdict_generation, report_generation***REMOVED***
engines: [review_engine***REMOVED***
quality_gates: [evidence_complete, context_complete, alternatives_considered, risks_assessed, single_verdict***REMOVED***
outputs: [review_verdict, review_report***REMOVED***
artifacts: ["ARB_REVIEW_<DOCUMENT>.md", findings, risks, recommendations***REMOVED***
interfaces:
  - "receives: architecture, models"
  - "produces: review_result"
  - "to_decision_forge: APPROVED → Decision Forge"
  - "from_governance: REQUIRES ARB REVIEW → повторный вход"
memory: [past_verdicts, adr, lessons***REMOVED***
knowledge: [patterns, project_context***REMOVED***
capabilities: [review, architecture, explain***REMOVED***
```

⚠️ `interfaces` — ПЛОСКИЙ список строк (не вложенный mapping): гарантия бесшовного маппинга на dataclass без silent corruption.

## 5. Валидация

- `python -m pytest tests_09/test_forge_passport.py tests_09/test_factory_registry.py -q` → зелёные;
- `python -c "from core_02.factory_registry import FactoryRegistry; r=FactoryRegistry(); print(len(r.list_forges('architecture')), len(r.validate_all()), len(r.warnings()))"` → `3 0 0` (после манифестов);
- `python -m core_02.missing_registry check` → ok;
- consistency_check build_report → naming/test_counter/missing_registry_sync без новых issues.
