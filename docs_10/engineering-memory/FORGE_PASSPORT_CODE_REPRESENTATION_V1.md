# FORGE PASSPORT — КОДОВОЕ ПРЕДСТАВЛЕНИЕ v1

| Поле | Значение |
|------|----------|
| **Документ** | FORGE_PASSPORT_CODE_REPRESENTATION_V1.md |
| **Статус** | 🏗 ARCHITECTURAL DESIGN DOCUMENT (механизм представления паспорта кузни — НЕ реализация) |
| **Версия** | 1.0 (2026-08-11) |
| **Базируется на** | FACTORY_FORGE_ARCHITECTURE_V1.md (**v1.1** — Forge = capability, 9 полей, §5), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (**паспорта v1.1**, открытый вопрос №1: dataclass `ForgePassport` vs YAML-манифест), SCENARIO_ENGINE_DESIGN_V1.md (CapabilityRef → Factory Registry), ARB-REV-003 (Required Action 4: FactoryRegistry — аддитивный реестр), ARB/AG конституции |
| **Отвечает на** | Открытый вопрос №1 паспортов («как паспорт кузни представлен в коде») + Missing Capability #1 карты v1.1 (FactoryRegistry) — механизм, не полный реестр |
| **Материальная база (паттерны в коде)** | `core_02/scenario.py` (ScenarioManifest.from_yaml → dataclass), `core_02/scenario_registry.py` (авто-discovery из `runtime_05/scenarios/`), `core_02/forge_registry.py` (dataclass ForgeStatus + validate_schema + YAML в data_13), `runtime_05/providers/*.yaml` (манифесты без изменения ядра), `core_02/blueprint_v3.py` (registry.yaml) |

---

## 1. Executive Summary

**Вопрос:** как паспорт кузни (Forge Passport) будет представлен в коде?

**Ответ (рекомендация):** **гибрид «YAML-манифест как источник истины + dataclass `ForgePassport` как типизированная runtime-модель»**, по образцу уже существующего паттерна `ScenarioManifest.from_yaml()` → `ScenarioRegistry`. Не «или-или», а два слоя одного контракта:

```
runtime_05/factories/<factory_id>/<forge_id>.yaml   ← источник истины (человекочитаемый, декларативный)
        │  ForgePassport.from_yaml()
        ▼
dataclass ForgePassport                              ← типизированная модель (валидация, API)
        │
        ▼
FactoryRegistry                                      ← авто-discovery + query API (как ScenarioRegistry)
```

**Почему гибрид, а не чистый dataclass:** паспорт — это **контракт**, который редактируют и читают люди и документы (паспорта v1.1 — это Markdown-документы). YAML-манифест сохраняет единый канонический источник (Single Source of Truth), а dataclass даёт типизацию, автодополнение и machine-checkable инварианты (урок B10/R-127 из `ForgeRegistry.validate_schema`).

**Почему не чистый YAML (без dataclass):** без типизированной модели теряется статическая проверка полей, резко растёт число `dict.get()` в коде (анти-паттерн, с которым проект уже боролся — см. `Role` dataclass в `scenario.py` вместо голых словарей).

**Вердикт:** рекомендованная схема — YAML-манифест (источник) + `ForgePassport` dataclass (runtime) + `FactoryRegistry` (реестр). Аддитивно, без изменения существующих модулей, по образцу ScenarioRegistry.

---

## 2. Существующие паттерны в коде (материальная база)

Проект уже решил задачу «как представить контракт в коде» — несколько раз. Паспорт кузни должен следовать **тому же паттерну**, а не изобретать новый.

| Паттерн | Файл | Механика |
|---------|------|----------|
| **ScenarioManifest** | `core_02/scenario.py` | `dataclass(frozen=True)` + `from_yaml(cls, path)` — YAML → типизированная модель; `__all__` экспорт |
| **ScenarioRegistry** | `core_02/scenario_registry.py` | Авто-discovery `*.yaml` из `runtime_05/scenarios/`, dispatch `_SCENARIO_TYPES`, `find_role`/`propose_roles`/`validate_all`, fail-safe warnings |
| **ForgeRegistry + ForgeStatus** | `core_02/forge_registry.py` | `dataclass ForgeStatus` (типизированная запись) + `validate_schema()` (B10/R-127: машинные инварианты) + YAML-персистентность в `data_13/` |
| **Providers** | `runtime_05/providers/*.yaml` | Marketplace: новый Runtime = новый YAML, ядро не меняется (No core change) |
| **Blueprint registry.yaml** | `core_02/blueprint_v3.py` | YAML-реестр ролей + splice-обновление с parse-guard |

**Вывод:** в проекте уже есть канонический ответ — «YAML-манифест + dataclass + реестр с авто-discovery». Паспорт кузни ложится в этот паттерн без изменений архитектуры.

---

## 3. Анализ вариантов: dataclass vs YAML vs гибрид

### Вариант A: чистый dataclass `ForgePassport` (в коде)

```python
@dataclass(frozen=True)
class ForgePassport:
    forge_id: str
    mission: str
    inputs: tuple[str, ...***REMOVED***
    ...
```

| Плюсы | Минусы |
|-------|--------|
| Типизация, автодополнение | Паспорт — контракт, редактируемый людьми/документами; добавление кузни = правка кода (нет No core change) |
| Меньше файлов | Markdown-паспорта (v1.1) и код рассинхронизируются (drift) — нужен отдельный механизм синхронизации |
| | Нет авто-discovery (каждая кузня — ручной import в реестре) |

### Вариант B: чистый YAML-манифест (без dataclass)

```yaml
# runtime_05/factories/architecture/review.yaml
forge_id: review
mission: "Проверить архитектурное решение"
...
```

| Плюсы | Минусы |
|-------|--------|
| Декларативность, человекочитаемость, No core change | `dict.get()` по всему коду (анти-паттерн) |
| Авто-discovery из директории | Нет статической валидации обязательных полей (B10/R-127 урок) |
| Единый источник с Markdown | Нет типов: `tuple[str,...***REMOVED***` vs `list`, числа, вложенность — всё «сырое» |

### Вариант C (РЕКОМЕНДОВАН): YAML-манифест (источник) + dataclass `ForgePassport` (runtime) + `FactoryRegistry` (реестр)

Комбинирует плюсы обоих, **повторяя существующий паттерн ScenarioManifest 1:1**:

```python
@dataclass(frozen=True)
class ForgePassport:
    forge_id: str
    factory_id: str
    version: str
    mission: str
    inputs: tuple[str, ...***REMOVED***
    production_workflow: tuple[str, ...***REMOVED***
    engines: tuple[str, ...***REMOVED***          # EngineRef/role names — уровень Engine
    quality_gates: tuple[str, ...***REMOVED***
    outputs: tuple[str, ...***REMOVED***
    artifacts: tuple[str, ...***REMOVED***
    interfaces: tuple[str, ...***REMOVED***
    memory: tuple[str, ...***REMOVED***
    knowledge: tuple[str, ...***REMOVED***

    @classmethod
    def from_yaml(cls, path: Path) -> "ForgePassport": ...   # как ScenarioManifest.from_yaml
    def to_yaml(self) -> str: ...                             # round-trip для генерации
    def validate(self) -> list[str***REMOVED***: ...                      # машинные инварианты (B10/R-127)
```

| Плюсы | Минусы |
|-------|--------|
| Типизация + декларативность одновременно | Чуть больше кода, чем чистый вариант (dataclass + parser) |
| Авто-discovery + No core change (новая кузня = новый YAML) | |
| Единый источник: YAML ↔ Markdown-паспорт (можно генерировать друг из друга) | |
| Валидация обязательных полей и закрытого словаря (ANTI-6b) | |

**Решение принято: Вариант C.**

---

## 4. Структура: где живёт паспорт

### 4.1 Расположение манифестов

```
runtime_05/factories/
├── README.md                       # формат манифеста (как scenarios/README.md)
└── architecture/
│   ├── factory.yaml                # манифест Factory (6 блоков, метаданные)
│   ├── discovery.yaml              # паспорт Forge Discovery
│   ├── design.yaml                 # паспорт Forge Design
│   ├── review.yaml                 # паспорт Forge Review
│   ├── decision.yaml
│   ├── governance.yaml
│   └── evolution.yaml
├── code/
│   ├── factory.yaml
│   ├── planning.yaml
│   ├── generation.yaml
│   └── ...
├── research/
└── content/
```

**Схема директорий** — `runtime_05/factories/<factory_id>/<forge_id>.yaml` + один `factory.yaml` на фабрику (аналог `runtime_05/scenarios/*.yaml` для сценариев и `runtime_05/providers/*.yaml` для Runtime).

### 4.2 Factory.yaml (манифест фабрики)

```yaml
# runtime_05/factories/architecture/factory.yaml
factory_id: architecture
display_name: Architecture Factory
version: "1.1.0"
status: design           # design | material | production (зрелость фабрики)
governance: [factory_constitution, standards, policies***REMOVED***
registry: [forges, artifacts, decisions, baselines***REMOVED***
knowledge: [architecture_knowledge, om, lessons, patterns***REMOVED***
quality_system: [gates, validation, conformance, consistency, traceability***REMOVED***
interfaces:
  input_contracts: [problem, requirements***REMOVED***
  output_contracts: [architecture, adr, conformance***REMOVED***
forges: [discovery, design, review, decision, governance, evolution, modeling***REMOVED***
```

> ⚠️ **Важно:** манифест фабрики — это **реестровая запись** (метаданные + перечень кузен), НЕ дублирование паспортов. Single Source of Truth для содержания паспорта — сам паспорт Forge; `forges:` в factory.yaml — индекс для навигации (может быть вычислен из директории, но явный список даёт контроль порядка и валидацию).

### 4.3 Forge.yaml (паспорт кузни) — пример Architecture Review Forge

```yaml
# runtime_05/factories/architecture/review.yaml
forge_id: review
factory_id: architecture
display_name: Architecture Review Forge
version: "1.0.0"
status: material          # design | material | production

mission: "Проверить архитектурное решение: можно ли его принимать"

inputs:
  - architectural_problem
  - architecture
  - models
  - constraints
  - relevant_decisions

production_workflow:
  - problem_validation
  - context_analysis
  - impact_analysis
  - dependency_analysis
  - evolution_analysis
  - debt_analysis
  - alternatives
  - principle_compliance
  - risk_assessment
  - platform_intelligence
  - verdict_generation
  - report_generation

engines:
  - review_engine          # Modules → Skills/Tools/Agents внутри (не на карте)

quality_gates:
  - evidence_complete
  - context_complete
  - alternatives_considered
  - risks_assessed
  - single_verdict

outputs:
  - review_verdict         # один из 6: APPROVED...REJECTED
  - review_report          # 12-частный формат ARB

artifacts:
  - ARB_REVIEW_<DOCUMENT>.md
  - findings
  - risks
  - recommendations

interfaces:
  - "receives: architecture, models"
  - "produces: review_result"
  - "to_decision_forge: APPROVED → Decision Forge"
  - "from_governance: REQUIRES ARB REVIEW → повторный вход"

# ⚠️ interfaces — ПЛОСКИЙ список строк (как inputs/outputs), НЕ вложенный mapping.
# Это гарантирует бесшовный маппинг на dataclass `interfaces: tuple[str, ...***REMOVED***`
# без молчаливой потери данных (урок B10/R-127: никакого silent corruption).

memory:
  - past_verdicts
  - adr
  - lessons
knowledge:
  - patterns
  - project_context

capabilities: [review, architecture, explain***REMOVED***   # ← для CapabilityRef (Scenario Engine §6)
```

---

## 5. dataclass `ForgePassport` (типизированная модель)

```python
# core_02/forge_passport.py (новый модуль, аддитивный)
"""core_02/forge_passport.py — типизированная модель паспорта кузни.

Повторяет паттерн core_02/scenario.py::ScenarioManifest (from_yaml → dataclass),
но для Forge (кузня) внутри Factory. YAML-манифест — источник истины;
dataclass — runtime-представление с валидацией (B10/R-127 урок).
"""

from __future__ import annotations

from dataclasses import dataclass, field
***REMOVED***
from typing import Optional

REQUIRED_FIELDS: tuple[str, ...***REMOVED*** = (
    "forge_id", "factory_id", "version", "mission",
    "inputs", "production_workflow", "outputs",
)


def _as_tuple(v: object) -> tuple[str, ...***REMOVED***:
    """Нормализует список строк из YAML в кортеж (module-level helper).

    Явно принимает только list/tuple; НЕ-scalar значение (например, dict)
    НЕ должен молча превращаться в () — это была бы тихая потеря данных
    (B10/R-127). Вместо этого поднимается ValueError, чтобы битый манифест
    падал громко, а не деградировал молча.
    """
    if v is None:
        return ()
    if isinstance(v, (list, tuple)):
        return tuple(str(x) for x in v)
    raise ValueError(
        f"ожидался список строк, получено {type(v).__name__***REMOVED***: {v!r***REMOVED*** "
        "(паспорт Forge: поля inputs/outputs/interfaces/... — плоские списки)"
    )


@dataclass(frozen=True)
class ForgePassport:
    """Паспорт кузни — 9 полей карты v1.1 + реестровые метаданные.

    Поля карты v1.1 (§5): Mission, Input, Production Workflow, Engines,
    Quality Gates, Output, Artifacts, Interfaces, Memory/Knowledge.
    Skills / Prompts / Tools / Agents — уровень Engine, на карту не попадают.
    """

    forge_id: str
    factory_id: str
    version: str
    mission: str
    inputs: tuple[str, ...***REMOVED*** = ()
    production_workflow: tuple[str, ...***REMOVED*** = ()
    engines: tuple[str, ...***REMOVED*** = ()            # EngineRef — уровень Engine
    quality_gates: tuple[str, ...***REMOVED*** = ()
    outputs: tuple[str, ...***REMOVED*** = ()
    artifacts: tuple[str, ...***REMOVED*** = ()
    interfaces: tuple[str, ...***REMOVED*** = ()
    memory: tuple[str, ...***REMOVED*** = ()
    knowledge: tuple[str, ...***REMOVED*** = ()
    capabilities: tuple[str, ...***REMOVED*** = ()       # для CapabilityRef (Scenario Engine §6)
    status: str = "design"                   # design | material | production
    display_name: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "ForgePassport":
        """Парсит YAML-манифест паспорта (аналог ScenarioManifest.from_yaml).

        Требуемые ключи: forge_id, factory_id, version, mission.
        Опциональные: inputs, production_workflow, engines, quality_gates,
        outputs, artifacts, interfaces, memory, knowledge, capabilities,
        status, display_name, metadata.
        """
        import yaml  # local — missing PyYAML fails only here
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path***REMOVED***: manifest must be a YAML mapping")
        missing = [k for k in ("forge_id", "factory_id", "version", "mission")
                   if not raw.get(k)***REMOVED***
        if missing:
            raise ValueError(f"{path***REMOVED***: required keys missing: {missing***REMOVED***")
        return cls(
            forge_id=str(raw["forge_id"***REMOVED***),
            factory_id=str(raw["factory_id"***REMOVED***),
            version=str(raw["version"***REMOVED***),
            mission=str(raw["mission"***REMOVED***),
            inputs=_as_tuple(raw.get("inputs")),
            production_workflow=_as_tuple(raw.get("production_workflow")),
            engines=_as_tuple(raw.get("engines")),
            quality_gates=_as_tuple(raw.get("quality_gates")),
            outputs=_as_tuple(raw.get("outputs")),
            artifacts=_as_tuple(raw.get("artifacts")),
            interfaces=_as_tuple(raw.get("interfaces")),
            memory=_as_tuple(raw.get("memory")),
            knowledge=_as_tuple(raw.get("knowledge")),
            capabilities=_as_tuple(raw.get("capabilities")),
            status=str(raw.get("status", "design")),
            display_name=str(raw.get("display_name", raw["forge_id"***REMOVED***)),
            metadata=dict(raw.get("metadata") or {***REMOVED***),
        )

    def to_yaml(self) -> str:
        """Обратная сериализация (round-trip) для генерации/сверки манифестов.

        Позволяет генерировать YAML из dataclass (например, при обновлении
        паспорта через код) и даёт инвариант from_yaml(to_yaml(p)) == p.
        """
        import yaml  # local — как в from_yaml
        payload = {
            "forge_id": self.forge_id,
            "factory_id": self.factory_id,
            "display_name": self.display_name,
            "version": self.version,
            "status": self.status,
            "mission": self.mission,
            "inputs": list(self.inputs),
            "production_workflow": list(self.production_workflow),
            "engines": list(self.engines),
            "quality_gates": list(self.quality_gates),
            "outputs": list(self.outputs),
            "artifacts": list(self.artifacts),
            "interfaces": list(self.interfaces),
            "memory": list(self.memory),
            "knowledge": list(self.knowledge),
            "capabilities": list(self.capabilities),
        ***REMOVED***
        if self.metadata:
            payload["metadata"***REMOVED*** = self.metadata
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    def to_dict(self) -> dict:
        """JSON-сериализуемое представление (конвенция ForgeStatus/ChainRun).

        Нужно для Scenario Engine (§8: CapabilityRef → паспорт → контракт
        шага) и для логов/отчётов FactoryRegistry.
        """
        return {
            "forge_id": self.forge_id,
            "factory_id": self.factory_id,
            "display_name": self.display_name,
            "version": self.version,
            "status": self.status,
            "mission": self.mission,
            "inputs": list(self.inputs),
            "production_workflow": list(self.production_workflow),
            "engines": list(self.engines),
            "quality_gates": list(self.quality_gates),
            "outputs": list(self.outputs),
            "artifacts": list(self.artifacts),
            "interfaces": list(self.interfaces),
            "memory": list(self.memory),
            "knowledge": list(self.knowledge),
            "capabilities": list(self.capabilities),
            "metadata": self.metadata,
        ***REMOVED***

    def validate(self) -> list[str***REMOVED***:
        """Машинные инварианты паспорта (B10/R-127 урок).

        Возвращает список нарушений ([***REMOVED*** = валиден). Проверяет:
        1. forge_id непустой и lowercase (slug-конвенция);
        2. обязательные поля непустые;
        3. status ∈ {design, material, production***REMOVED***;
        4. capabilities ⊆ закрытый словарь (ANTI-6b/CON-8) — см. KNOWN_CAPABILITIES
           или FactoryRegistry.known_capabilities();
        5. outputs непустые (Forge = собственный производственный результат —
           правило карты v1.1 §5).
        """
        errors: list[str***REMOVED*** = [***REMOVED***
        if not self.forge_id or self.forge_id != self.forge_id.lower():
            errors.append(f"{self.forge_id***REMOVED***: forge_id must be non-empty lowercase slug")
        if not self.mission:
            errors.append(f"{self.forge_id***REMOVED***: mission is required")
        if self.status not in ("design", "material", "production"):
            errors.append(
                f"{self.forge_id***REMOVED***: invalid status {self.status!r***REMOVED*** "
                "(allowed: design, material, production)"
            )
        if not self.outputs:
            errors.append(
                f"{self.forge_id***REMOVED***: outputs must be non-empty "
                "(Forge = capability with its own production result, v1.1 §5)"
            )
        # Словарная защита (ANTI-6b): capability токены — закрытое множество.
        from core_02.blueprint_v3 import KNOWN_CAPABILITIES
        unknown = [c for c in self.capabilities if c not in KNOWN_CAPABILITIES***REMOVED***
        if unknown:
            errors.append(
                f"{self.forge_id***REMOVED***: capabilities {unknown***REMOVED*** вне закрытого словаря "
                f"KNOWN_CAPABILITIES (core_02/blueprint_v3.py) — silent fallback риск"
            )
        return errors


__all__ = ["ForgePassport", "REQUIRED_FIELDS"***REMOVED***
```

**Ключевые решения dataclass:**

1. **`frozen=True`** — паспорт неизменяемый контракт (как `ScenarioManifest`, `Role`, `ChainStage`).
2. **Списки → `tuple`** — иммутабельность и хэшируемость (конвенция `scenario.py`).
3. **`validate()`** — B10/R-127 урок: паспорт не должен «молча» принимать невалидные данные. Валидация вызывается при загрузке реестром.
4. **`to_yaml()` / `to_dict()`** — round-trip (from_yaml(to_yaml(p)) == p) и JSON-сериализация по конвенции `ForgeStatus.to_dict`/`ChainRun.to_dict`; нужны для генерации Markdown (§10.6) и Scenario Engine (§8).
5. **`_as_tuple` на уровне модуля** — общий helper; НЕ-scalar значение (например, dict вместо списка) вызывает ValueError (громкая ошибка, не молчаливая потеря данных B10/R-127).
6. **`capabilities`** — мост к Scenario Engine (CapabilityRef разрешение, §6.2 SCENARIO_ENGINE_DESIGN) + защита закрытого словаря ANTI-6b (урок `BlueprintCorpus.validate_override_vocabulary`).
7. **`status`** — зрелость кузни (design → material → production): реестровое поле, не из 9 полей карты.

---

## 6. FactoryRegistry (реестр фабрик и кузен)

```python
# core_02/factory_registry.py (новый модуль, аддитивный)
"""core_02/factory_registry.py — реестр Factory и их Forge-паспортов.

Повторяет паттерн core_02/scenario_registry.py (авто-discovery YAML из
директории + dispatch + fail-safe warnings), но для производственных
мощностей: Factory (фабрики) → ForgePassport (паспорта кузен).
"""

from __future__ import annotations

***REMOVED***
from typing import Optional

from core_02.forge_passport import ForgePassport


def _default_factories_dir() -> Optional[Path***REMOVED***:
    """Resolution: $FREEBUFF_FACTORIES_DIR → runtime_05/factories/."""
    import os
    env = os.environ.get("FREEBUFF_FACTORIES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[1***REMOVED***
    default = repo_root / "runtime_05" / "factories"
    return default if default.exists() else None


class FactoryRegistry:
    """Реестр фабрик и паспортов кузен (аддитивный, по образцу ScenarioRegistry).

    Auto-discovery: обходит runtime_05/factories/<factory>/*.yaml,
    инстанцирует ForgePassport.from_yaml, собирает warnings при сбоях
    (манифест битый / forge_id дублируется / vocabulary drift).
    """

    def __init__(self, factories_dir: Optional[Path***REMOVED*** = None, silent: bool = False):
        self.factories_dir = factories_dir or _default_factories_dir()
        self._passports: dict[tuple[str, str***REMOVED***, ForgePassport***REMOVED*** = {***REMOVED***  # (factory, forge)
        self._factory_meta: dict[str, dict***REMOVED*** = {***REMOVED***
        self._load_warnings: list[str***REMOVED*** = [***REMOVED***
        if self.factories_dir and self.factories_dir.exists():
            self._load_from_dir(self.factories_dir, silent=silent)

    def _load_from_dir(self, d: Path, silent: bool) -> None:
        """Обход <factory_id>/*.yaml; factory.yaml — метаданные фабрики."""
        for factory_dir in sorted(p for p in d.iterdir() if p.is_dir()):
            factory_id = factory_dir.name
            for yaml_path in sorted(factory_dir.glob("*.yaml")):
                if yaml_path.name == "factory.yaml":
                    self._load_factory_meta(yaml_path, silent)
                    continue
                try:
                    passport = ForgePassport.from_yaml(yaml_path)
                except (ValueError, Exception) as exc:
                    self._load_warnings.append(
                        f"{yaml_path.name***REMOVED***: manifest parse failed — {exc***REMOVED***"
                    )
                    if not silent:
                        print(f"warning: {yaml_path.name***REMOVED***: {exc***REMOVED***")
                    continue
                # cross-check: factory_id в манифесте == директория
                if passport.factory_id != factory_id:
                    self._load_warnings.append(
                        f"{yaml_path.name***REMOVED***: factory_id {passport.factory_id!r***REMOVED*** "
                        f"!= directory {factory_id!r***REMOVED*** — skipped"
                    )
                    continue
                key = (passport.factory_id, passport.forge_id)
                if key in self._passports:
                    self._load_warnings.append(
                        f"duplicate forge {key!r***REMOVED*** — second ignored"
                    )
                    continue
                self._passports[key***REMOVED*** = passport

    def list_factories(self) -> list[str***REMOVED***:
        return sorted({f for (f, _) in self._passports***REMOVED***)

    def list_forges(self, factory_id: str) -> list[ForgePassport***REMOVED***:
        return [
            p for (f, _), p in self._passports.items() if f == factory_id
        ***REMOVED***

    def get_forge(self, factory_id: str, forge_id: str) -> Optional[ForgePassport***REMOVED***:
        return self._passports.get((factory_id, forge_id))

    def find_by_capability(self, capability: str) -> list[ForgePassport***REMOVED***:
        """Для CapabilityRef (Scenario Engine §6.2): кузни с нужной capability."""
        return [p for p in self._passports.values() if capability in p.capabilities***REMOVED***

    def validate_all(self) -> list[str***REMOVED***:
        """Агрегированные ошибки всех паспортов (B10/R-127)."""
        errors: list[str***REMOVED*** = [***REMOVED***
        for (f, g), p in self._passports.items():
            for err in p.validate():
                errors.append(f"[{f***REMOVED***/{g***REMOVED******REMOVED*** {err***REMOVED***")
        return errors

    def warnings(self) -> list[str***REMOVED***:
        return list(self._load_warnings)


__all__ = ["FactoryRegistry", "_default_factories_dir"***REMOVED***
```

**Ключевые решения FactoryRegistry:**

1. **Авто-discovery** — новая кузня = новый YAML в `runtime_05/factories/`, ядро не меняется (No core change, паттерн Marketplace/providers).
2. **Fail-safe warnings** — битый манифест не роняет реестр, а попадает в `warnings()` (паттерн `ScenarioRegistry`).
3. **Cross-check factory_id == директория** — защита от ошибок раскладки.
4. **`find_by_capability`** — прямой мост к Scenario Engine (`CapabilityRef` → `FactoryRegistry` → исполнитель).
5. **`validate_all()`** — вызывается при старте (как `ScenarioRegistry.validate_all`), даёт machine-checkable инварианты.

---

## 7. Связь с существующими реестрами (без параллельной системы)

| Реестр | Отвечает за | Взаимодействие с FactoryRegistry |
|--------|-------------|----------------------------------|
| **ForgeRegistry** (`core_02/forge_registry.py`) | **Проекты** и их статусы (UNFORGED…DEPLOYED) в `data_13/forge_registry.yaml` | Независим: статусы прогонов проектов, НЕ паспорта. FactoryRegistry читает только `runtime_05/factories/` |
| **ScenarioRegistry** (`core_02/scenario_registry.py`) | **Сценарии** (корпуса ролей) в `runtime_05/scenarios/` | Независим: сценарии → роли. Scenario Engine будет вызывать FactoryRegistry для разрешения CapabilityRef |
| **FactoryRegistry** (новый) | **Фабрики + паспорта кузен** в `runtime_05/factories/` | Источник для CapabilityRef (Scenario Engine §6); паспорта — машиночитаемый контракт (Required Action 4 ARB-REV-003) |

**Границы (B-правила, карта v1.1):**
- ForgeRegistry = статусы **проектов** (состояние прогона); FactoryRegistry = паспорта **кузен** (контракт способности). Разные namespace, разные owner-file → разные границы (B-Rule 4/5).
- ScenarioRegistry = сценарии (роли); FactoryRegistry = мощности (кузни). Scenario — единственный комбинатор Factory (v1.1 §15.1).

---

## 8. Интеграция с Scenario Engine

Паспорт — машиночитаемый контракт для разрешения capabilities (`SCENARIO_ENGINE_DESIGN_V1.md` §6.2):

```
Scenario step
   └── CapabilityRef {kind: forge, factory: architecture, forge: review***REMOVED***
          │
          ▼
   FactoryRegistry.get_forge("architecture", "review")
          │
          ├── passport.outputs      → контракт выхода (что ждём)
          ├── passport.quality_gates → Quality Gates шага (§8 SCENARIO_ENGINE_DESIGN)
          ├── passport.capabilities → vocabulary check (ANTI-6b)
          └── исполнитель          → ForgeFacade.initiate_forge (роль в PIPELINE_ROLES)
                                     ИЛИ паспортная реализация кузни (будущее)
```

**Правило §7.3 / B2 R-124 не нарушается:** ForgePipeline инстанцируется только в `ForgeFacade`. FactoryRegistry выдаёт **контракт** (паспорт), а не прямой вызов Forge — исполнение всегда через санкционированный мост.

---

## 9. Маппинг: Markdown-паспорт ↔ YAML ↔ dataclass

Одна кузня имеет три представления одного контракта (Single Source of Truth):

```
docs_10/engineering-memory/
  FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md   ← человекочитаемый документ (v1.1, 9 полей)
        │  (генерация/ручная сверка)
        ▼
runtime_05/factories/architecture/review.yaml   ← машиночитаемый источник истины
        │  ForgePassport.from_yaml()
        ▼
core_02 ForgePassport dataclass                 ← типизированная runtime-модель
```

**Конвенция:** Markdown-паспорт — документация (что кузня делает), YAML — контракт (данные для кода), dataclass — runtime. При расхождении YAML и Markdown приоритет у YAML (машиночитаемое проверяемо через `validate_all`); расхождение фиксируется drift-check'ом (как `consistency_check.py` для доков).

---

## 10. Внедрение (additive, по шагам)

1. **Шаг 1:** новый `core_02/forge_passport.py` (dataclass + from_yaml + validate) — без реестра, unit-тестируемый.
2. **Шаг 2:** новый `core_02/factory_registry.py` (авто-discovery + query API + validate_all).
3. **Шаг 3:** `runtime_05/factories/` структура + README.md + первые манифесты: `architecture/factory.yaml` + `architecture/review.yaml` (первая материальная кузня) + `architecture/governance.yaml` (вторая).
4. **Шаг 4:** тесты `tests_09/test_forge_passport.py` + `test_factory_registry.py` (паттерн `test_scenario_registry.py`): from_yaml happy-path, missing required keys, vocabulary drift → ValueError, cross-check factory_id, duplicate forge_id, validate_all.
5. **Шаг 5:** интеграция с Scenario Engine (`CapabilityRef` → `FactoryRegistry.get_forge`) — по мере реализации Scenario Engine.
6. **Шаг 6:** генератор Markdown-паспорта из YAML (или наоборот) — синхронизация доков и контракта.

**Что НЕ делаем:** не модифицируем `scenario.py`, `scenario_registry.py`, `forge_registry.py`, `blueprint_v3.py` (аддитивность CAN-16). Новые модули + новые YAML.

---

## 11. Открытые вопросы

1. **Глубина Engines в манифесте:** `engines: [review_engine***REMOVED***` — только имена, или структура Engine (Modules → Skills/Tools) тоже в YAML? (Карта v1.1: не спускаться ниже Engine на карте; детали — при реализации Engine.) **Рекомендация:** на паспорте — имена Engines; детали Engine — отдельные манифесты уровня Engine (будущее).
2. **YAML ↔ Markdown синхронизация:** генерация паспортов из Markdown (docs → YAML) или Markdown из YAML (контракт → доки)? **Рекомендация:** YAML источник для кода; генерация Markdown-карточки — опция.
3. **Закрытый словарь capabilities:** расширять `KNOWN_CAPABILITIES` (`blueprint_v3.py`) или вводить Factory-level словарь? **Рекомендация:** переиспользовать `KNOWN_CAPABILITIES` (single vocabulary, ANTI-6b) + пополнять при новых способностях.
4. **Registry-состояние кузен:** нужен ли `FactoryRegistry` для хранения статусов прогонов кузен (как ForgeRegistry для проектов), или статусы кузен живут в `ForgeRegistry.last_pipeline` (как сейчас)? **Рекомендация v1:** зрелость кузни (`status: design|material|production`) в паспорте; статусы прогонов — в существующем ForgeRegistry.
5. **Нейминг:** `runtime_05/factories/` vs `runtime_05/forges/` — директория называется factories (по промту 72 открытый вопрос «хранилище манифестов»); внутри подпапки по factory_id.

---

## 12. Вердикт

**Механизм представления паспорта кузни в коде — гибрид: YAML-манифест (источник истины) + dataclass `ForgePassport` (runtime) + `FactoryRegistry` (реестр с авто-discovery).**

- ✅ **Паттерн проекта:** 1:1 повторяет `ScenarioManifest.from_yaml` → `ScenarioRegistry` (scenarios) и providers (marketplace) — не изобретает новую механику.
- ✅ **No core change:** новая кузня = новый YAML в `runtime_05/factories/<factory>/<forge>.yaml`; существующие модули не модифицируются (CAN-16).
- ✅ **Типизация + валидация:** `frozen=True` dataclass, обязательные поля, `status ∈ {design, material, production***REMOVED***`, outputs непустые (правило «одна Forge = один результат»), vocabulary-защита ANTI-6b.
- ✅ **Интеграция:** `FactoryRegistry.find_by_capability`/`get_forge` — контракт для Scenario Engine (CapabilityRef §6.2); границы B-Rule 4/5 с ForgeRegistry/ScenarioRegistry соблюдены.
- ✅ **Закрывает:** открытый вопрос №1 паспортов + Missing Capability #1 карты v1.1 (механизм; полный реестр со статусами прогонов — следующий этап).

**Следующий шаг после утверждения:** Шаг 1–2 (модули `forge_passport.py` + `factory_registry.py` с unit-тестами), затем Шаг 3 — первые манифесты `runtime_05/factories/architecture/{factory,review,governance***REMOVED***.yaml`.

---

*Документ спроектирован на базе: FACTORY_FORGE_ARCHITECTURE_V1.md (v1.1), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (паспорта v1.1, вопрос №1), SCENARIO_ENGINE_DESIGN_V1.md (CapabilityRef), ARB-REV-003 (Required Action 4), и реального кода: core_02/{scenario,scenario_registry,forge_registry,blueprint_v3***REMOVED***.py, runtime_05/{scenarios,providers***REMOVED***. Статус: ARCHITECTURAL DESIGN DOCUMENT — проектирование, не реализация.*
