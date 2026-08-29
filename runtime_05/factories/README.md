# runtime_05/factories/ — Forge Passport directory layout

> **Канонический источник:** `pompts_11/078_19_factory_registry.md` + `FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md` + `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` (дизайн-вердикт: гибрид «YAML-dataclass-Registry», Вариант C).
> **Канон нейминга:** все `factory_id` и `forge_id` — lowercase-slug, начинается с буквы (regex `^[a-z***REMOVED***[a-z0-9_***REMOVED***{1,30***REMOVED***$`).
> **Канон состояний:** `status ∈ {design, material, production***REMOVED***` (B10/R-127, ANTI-6b).

---

## 0. Структура директорий

```
runtime_05/factories/
├── README.md                       ← этот файл
├── <factory_id>/
│   ├── factory.yaml                ← метаданные фабрики (НЕ паспорт)
│   └── <forge_id>.yaml             ← паспорт Forge (ForgePassport)
└── ...
```

**Один `factory.yaml` на фабрику** — метаданные фабрики (display_name, version, description, status; НЕ паспорта конкретных кузен).

**Без ограничений на количество `<forge_id>.yaml` на фабрику** — каждая Forge (кузня) — отдельный файл. Это повторяет паттерн `runtime_05/scenarios/*.yaml` (сценарии) и `runtime_05/providers/*.yaml` (Marketruntime) — No core change на каждую новую кузню.

---

## 1. Схема `factory.yaml` (метаданные фабрики)

```yaml
factory_id: <lowercase-slug>
display_name: <Human-Readable Name>
version: "<semver>"
status: <design|material|production>     # status самой фабрики
description: |
  Свободное описание в 1-3 предложениях.
  Что фабрика охватывает; какие Forge (кузни) в неё входят типично.
metadata:
  owner: <team-or-individual>
  prompt_path: <path-to-factory-design-doc>     # опционально
  references:                                    # опционально — кросс-ссылки
    - "<doc-or-source-ref>"
```

**Cross-check защита (FactoryRegistry._load_one_forge):** `factory.yaml::factory_id` ДОЛЖЕН == имя директории. Несовпадение → warning + registry использует директорное имя как canonical.

---

## 2. Схема `<forge_id>.yaml` (ForgePassport)

**9 паспортных полей v1.1** + 7 реестровых полей (см. `core_02/forge_passport.py::ForgePassport`).

Полный пример — `architecture/review.yaml` в этой же папке. Ниже — минимальная схема:

```yaml
# ─── реестровые поля ───────────────────────────────────────────────────────────
forge_id: <lowercase-slug>
factory_id: <lowercase-slug>                   # должен совпадать с директорией
version: "<semver>"                            # 0.1.0 для design, 1.0.0 для material/production
status: <design|material|production>
display_name: <Human-Readable Name>
capabilities:                                   # ⊆ KNOWN_CAPABILITIES (см. ниже)
  - <capability_token>
  - <capability_token>
metadata:
  prompt_path: <path-to-forge-design-doc>       # обычно 'pompts_11/<spec>.md'

# ─── 9 паспортных полей v1.1 ───────────────────────────────────────────────────
mission: "<одно предложение: ЗАЧЕМ эта кузня>"

inputs:                                         # списok; непустой для material/production
  - "<kind>|<spec>"

production_workflow:                            # списok стадий
  - "<step_id>"

engines:                                        # какие @entity-движки запускает
  - "@entity <name>"

quality_gates:                                  # критерии завершения
  - "<gate_name>"

outputs:                                        # ОБЯЗАТЕЛЬНО непустой (B10/R-127: 1 Forge = 1 результат)
  - "<kind>|<spec>"

artifacts:                                      # производимые артефакты (data_13/...)
  - "<path-or-type>"

interfaces:                                     # плоский список строк (НЕ dict!)
  - "<kind> <direction>"

memory:                                         # что кузня помнит между вызовами
  - "<store-or-context>"

knowledge:                                      # внешние знания, на которые опирается
  - "<reference>"
```

**Cross-check защита:** `<forge_id>::factory_id` ДОЛЖЕН == имя родительской директории. Несовпадение → warning (registry использует директорное имя как canonical).

---

## 3. Closed vocabulary: `capabilities`

Токены `capabilities` ОБЯЗАНЫ быть подмножеством `KNOWN_CAPABILITIES` (определён в `core_02/blueprint_v3.py`):

```python
KNOWN_CAPABILITIES = frozenset({
    "local", "fast", "code", "summarize", "router", "classify",
    "reasoning", "plan", "refactor", "explain",
    "deep", "architecture", "review",
    "vision", "tools", "long_context", "multimodal", "instruct",
    "diagnose", "validate", "report",
    "research",          # веб-исследование (research_web, Missing #6)
    "estimation",        # оценка сложности (lisa_estimator, Missing #7)
***REMOVED***)
```

**ANTI-6b защита:** неизвестные capability-токены → `ValueError` на `passport.validate()`. Это **фича**, не баг: silent fallback на qwen2.5:1.5b при «зелёных» тестах запрещён (см. `core_02/LESSONS.md CON-8`).

---

## 4. Process: новая кузня = новый файл

**Не нужно править код.** Чтобы добавить новую Forge:

1. Создать `<forge_id>.yaml` в `runtime_05/factories/<factory_id>/`;
2. Валидация: `python -c "from core_02.factory_registry import FactoryRegistry; r = FactoryRegistry(); print(r.validate_all())"`;
3. Если есть нарушения — поправить YAML, повторить шаг 2;
4. Сценарии получают ForgePassport через `r.find_by_capability(...)` (мост к Scenario Engine §6.2).

---

## 5. Расширение первой фабрики

`architecture/` — стартовая фабрика для Architecture-кузен (review, governance). Это **первая материальная фабрика**; новые фабрики добавляются аналогично (idea / research / knowledge / implementation — кандидаты на Phase 1.5 / Phase 2 / Phase J).

