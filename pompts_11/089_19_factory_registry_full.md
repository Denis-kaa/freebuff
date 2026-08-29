# PROMPT: FACTORY REGISTRY FULL — FactoryPassport + capability-каталог (C-2)

## РОЛЬ

Senior AI Systems Architect + Senior Python Engineer.

Продолжение roadmap 09_FUTURE_GAPS.md C-2: «Полноценный FactoryRegistry (паспорт
factory.yaml, capability-каталог) — разблокирует Factory-путь в цикле».

## SOURCE OF TRUTH

Repository — источник истины. Перед реализацией проверь фактическое состояние:

- `core_02/factory_registry.py` — FactoryRegistry (auto-discovery, query API, factory.yaml как сырой dict);
- `core_02/forge_passport.py` — ForgePassport (паттерн для FactoryPassport);
- `runtime_05/factories/architecture/factory.yaml` — реальный манифест фабрики;
- `core_02/blueprint_v3.py` — `KNOWN_CAPABILITIES` (закрытый словарь, ANTI-6b);
- `tests_09/test_factory_registry.py` + `tests_09/test_forge_passport.py` — конвенции тестов.

## GAP (09_FUTURE_GAPS C-2 / §15)

`FactoryRegistry` грузит `factory.yaml` как сырой dict (без типизированного паспорта),
не имеет factory-level capability-каталога и API селекции (factory/forge по capability) —
Factory-путь в цикле (opportunity-capability → factory → forge) не разблокирован.

## SCOPE — разрешено

- `core_02/factory_passport.py` (НОВЫЙ модуль — FactoryPassport);
- `core_02/factory_registry.py` (АДДИТИВНО, CAN-16 — существующие методы/поля не ломать);
- `runtime_05/factories/architecture/factory.yaml` (добавить `capabilities`);
- `tests_09/test_factory_passport.py` (новый) + `tests_09/test_factory_registry.py` (аддитивно);
- реестры/доки: §20 карта v1.1, `CHANGELOG.md`, `09_FUTURE_GAPS.md`.

## SCOPE — НЕ делать

- НЕ менять `ForgePassport` / `ForgeRegistry` / `ScenarioRegistry` / `blueprint_v3`;
- НЕ менять существующие методы `FactoryRegistry` (только НОВЫЕ методы);
- НЕ трогать `opportunity_engine` / `ForgeFacade` (Factory-путь разблокируется API,
  не переписыванием цикла);
- НЕ массовый рефакторинг.

## SPEC

1. **`FactoryPassport`** (`core_02/factory_passport.py`, зеркалит `ForgePassport`):
   - frozen dataclass; поля: `factory_id`, `display_name`, `version`, `status`,
     `description`, `capabilities: tuple[str, ...***REMOVED***`, `metadata: dict`;
   - `REQUIRED_FIELDS = ("factory_id", "display_name", "version", "status", "description")`;
   - `from_yaml` / `_from_dict` / `to_yaml` / `to_dict` / `validate`;
   - `validate()`: `factory_id` lowercase-slug; `status ∈ {design, material, production***REMOVED***`;
     `display_name`/`description` непустые; `capabilities ⊆ KNOWN_CAPABILITIES` (ANTI-6b).

2. **`FactoryRegistry`** (аддитивно):
   - `self._factory_passports: dict[str, FactoryPassport***REMOVED***`;
   - `get_factory(factory_id) -> Optional[FactoryPassport***REMOVED***`;
   - `factory_capabilities(factory_id) -> tuple[str, ...***REMOVED***` — union capabilities
     из factory.yaml + forge passports фабрики (dedup, sorted);
   - `find_factories_by_capability(capability) -> list[FactoryPassport***REMOVED***`;
   - `select_forge(capability, prefer_status=None) -> Optional[Tuple[FactoryPassport, ForgePassport***REMOVED******REMOVED***`
     — лучшая (factory, forge) пара по capability: status-priority
     (production > material > design) на factory затем forge, детерминированный
     tie-break (factory_id, forge_id);
   - `capability_catalog() -> dict[str, list[str***REMOVED******REMOVED***` — capability → sorted factory_ids.

3. **`runtime_05/factories/architecture/factory.yaml`**: добавить `capabilities`
   (factory-level capability-каталог; подмножество KNOWN_CAPABILITIES).

## TESTS

- `test_factory_passport.py`: `from_yaml` happy-path, missing required → ValueError,
  invalid status → ValueError, vocab drift → validate() violation, `to_dict` roundtrip;
- `test_factory_registry.py` (additive): `get_factory`, `factory_capabilities`
  (union), `find_factories_by_capability`, `select_forge` (status-priority +
  tie-break), `capability_catalog`.

## VALIDATION GATE

1. `python -m pytest tests_09/test_factory_passport.py tests_09/test_factory_registry.py -q`
2. `python -m mypy core_02/factory_passport.py core_02/factory_registry.py --ignore-missing-imports`
3. `consistency_check` → TOTAL 0
4. `python -m core_02.missing_registry check` → exit 0

## REGISTER-FIRST

- capability: `factory_registry_full` (kind=capability, factory=governance);
- lifecycle: register → mark-prompt-written → mark-implemented (этот промт);
- §20 карта v1.1: row #20;
- CHANGELOG: v5.189.21.

# END OF PROMPT
