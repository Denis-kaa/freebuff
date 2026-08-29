# Scenarios — реестр ролевых источников

> Каждый YAML в этом каталоге — один **scenario**, источник ролей для wizard
> и платформенного self-learning loop. Сегодня — один сценарий
> `blueprint_v3` (Kwork Arbitr v3, 17+ ролей). В будущем —
> дополнительные сценарии (Remote Personas, Plugin Scenarios, ...).

## Философия

**Wizard должен спрашивать "какая роль нужна" и искать по всем зарегистрированным
сценариям, а не хардкодить Arbitr как единственную возможность.**

Это контраст к предыдущему дизайну, в котором `BlueprintCorpus` был
единственным путём и хардкодился в `core_02/wizard_lib.run_wizard(corpus=...)`.
Теперь wizard принимает `ScenarioRegistry`, ищет по всем сценариям
кросс-сценарно (`propose_roles(query)`), и **может выбрать роль из любого
активного сценария**.

Auto-discovery работает по той же схеме, что `runtime_05/providers/` для
Runtime Marketplace (см. `runtime_05/MARKETPLACE.md`).

## Формат манифеста

Минимум:

```yaml
id: my-scenario           # unique registry-wide
type: blueprint_v3        # dispatched в core_02/scenario_registry._SCENARIO_TYPES
root: /path/to/source     # depends on type
```

Опционально:

| Ключ | Тип | Описание |
|------|-----|----------|
| `display_name` | str | человекочитаемое имя для UI (default = id) |
| `enabled` | bool | false → manifest грузится, но сценарий не регистрируется |
| `capabilities` | list[str***REMOVED*** | **scenario-level** capabilities (отдельны от per-role `routing_hint`) |
| `metadata` | dict | свободный словарь для произвольных метаданных |

Контракт см. в `core_02/scenario.py::ScenarioManifest.from_yaml`.

## Как добавить новый scenario

### Вариант A: новый тип сценария (например, RemoteScenario)

1. Реализовать `class RemoteScenario(Scenario)` в `core_02/scenario_subclass_remote.py`:
   - constructor `(scenario_id: str, root: Path, **kwargs)`,
   - методы `scenario_id`, `display_name`, `list_roles`, `load_role_text`, `routing_hint`, `validate`.
2. Добавить в dispatch dict `core_02/scenario_registry.py::_SCENARIO_TYPES`:
   ```python
   _SCENARIO_TYPES["remote"***REMOVED*** = RemoteScenario
   ```
3. Создать manifest `runtime_05/scenarios/my-remote.yaml`:
   ```yaml
   id: my-remote
   type: remote
   root: https://example.com/personas  # subclass знает что с этим делать
   enabled: true
   ```

### Вариант B: второй backend того же типа (например, ещё один Blueprint v3 корпус)

1. Создать manifest `runtime_05/scenarios/blueprint_v3_alt.yaml`:
   ```yaml
   id: blueprint_v3_alt
   type: blueprint_v3
   root: /path/to/alt/blueprints_v3
   enabled: true
   ```

Registry автоматически создаст второй экземпляр `BlueprintScenario` (= `BlueprintCorpus`).
Если `role_id` пересекается с первым корпусом — `find_role` вернёт первый
(с предупреждением в `validate_all`).

## Env override

```bash
FREEBUFF_SCENARIOS_DIR=/path/to/scenarios wizard ...
```

Используется при тестах и в dev. Resolution order в
`core_02/scenario_registry._default_scenarios_dir`:
1. `$FREEBUFF_SCENARIOS_DIR`
2. `<freebuff_repo>/runtime_05/scenarios/` (default)

## Failure modes

| Событие | Поведение |
|---------|-----------|
| Manifest YAML parse fails | warning + skip |
| `type` unknown | warning + skip |
| `root` missing | subclass instantiation raises → caught → warning + skip |
| Duplicate `scenario_id` | first wins, second records warning |
| Empty `scenarios_dir` | registry empty; `warnings()` сообщает "no scenarios_dir resolved" |

Все warnings возвращаются через `ScenarioRegistry.warnings()`. По умолчанию
также пишутся в stderr (флаг `silent=True` для тестов).

## Файлы

| Файл | Роль |
|------|------|
| `core_02/scenario.py` | Scenario ABC + Role + ScenarioManifest |
| `core_02/scenario_registry.py` | ScenarioRegistry с auto-discovery |
| `core_02/blueprint_v3.py` | BlueprintScenario (= BlueprintCorpus BC alias) — concrete |
| `runtime_05/scenarios/*.yaml` | discovery-friendly manifests |
| `runtime_05/scenarios/README.md` | этот документ |
