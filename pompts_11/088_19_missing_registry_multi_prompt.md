# PROMPT: MISSING REGISTRY MULTI-PROMPT SUPPORT v1.0

## РОЛЬ

Senior AI Systems Architect + Senior Python Engineer.

Продолжение roadmap Phase 5 (09_FUTURE_GAPS.md row #8): «MissingRegistry schema — единственное поле `prompt_path`; forensics-промт теряет machine-readable след → кандидат на multi-prompt поддержку (`prompt_paths`/`related_prompts`)».

## SOURCE OF TRUTH

Repository — источник истины.

Перед реализацией проверь фактическое состояние:

- `core_02/missing_registry.py` — `MissingItem` (schema), `register_missing`/`mark_prompt_written`/`mark_implemented`, CLI, `validate_schema`;
- `data_13/missing_registry.yaml` — запись `intelligence_integration` (prompt_path=085, forensics 084 потерян из machine-readable полей);
- `tests_09/test_missing_registry.py` — конвенции тестов;
- `scripts_01/consistency_check.py` — `check_missing_registry_sync` (сверка §20 ↔ реестр по status).

## GAP (09_FUTURE_GAPS row #8)

`MissingItem.prompt_path` — единственное поле-строка. При `mark-implemented --prompt` (intelligence_integration, v5.189.16) замена 084→085 стёрла machine-readable след forensics-промта 084 (остался только в `description` + §20-сноске, не в данных). Нужна поддержка НЕСКОЛЬКИХ промтов на запись.

## SCOPE — разрешено

- `core_02/missing_registry.py` (АДДИТИВНО, CAN-16 — существующие поля/методы не ломать);
- `tests_09/test_missing_registry.py` (аддитивные тесты);
- `data_13/missing_registry.yaml` (бэкфилл `intelligence_integration`);
- реестры/доки: §20 карта v1.1, `CHANGELOG.md`, `09_FUTURE_GAPS.md`.

## SCOPE — НЕ делать

- НЕ менять lifecycle (registered → design_ready → prompt_written → implemented);
- НЕ менять `prompt_path` семантику (primary/implementation промт остаётся);
- НЕ трогать `consistency_check` логику сверки (она по status — не зависит от полей);
- НЕ массовый рефакторинг.

## SPEC

1. `MissingItem` — новое поле `related_prompts: List[str***REMOVED*** = field(default_factory=list)`:
   - дополнительные/связанные промты (forensics, design, supporting);
   - `prompt_path` остаётся primary/implementation промтом (backward-compat);
   - `to_dict()` включает `related_prompts`;
   - `from_dict()` включает `related_prompts` (отсутствие → `[***REMOVED***`, лишние ключи игнорируются).

2. `register_missing(..., related_prompts: Optional[List[str***REMOVED******REMOVED*** = None)` — аддитивный параметр.

3. Новый метод `add_related_prompt(item_id, prompt_path) -> MissingItem`:
   - append с дедупликацией (повторный путь не дублируется);
   - KeyError если item не зарегистрирован (register-first);
   - обновляет `updated_at`.

4. `mark_implemented(..., related_prompts: Optional[List[str***REMOVED******REMOVED*** = None)` — при передаче устанавливает список (не теряет уже добавленные, если None).

5. `validate_schema()` — если `related_prompts` присутствует: должен быть list; каждый элемент — непустая строка (иначе violation).

6. CLI:
   - `mark-implemented ITEM_ID --implementation PATH [--prompt PATH***REMOVED*** [--related-prompt PATH ...***REMOVED***` (action=append);
   - новая подкоманда `add-related-prompt ITEM_ID --prompt PATH` (action=append, повторяемая);
   - `_print_item` показывает `related=N` (или пути);
   - `list --json` включает `related_prompts`.

7. `__all__` — без изменений (новых публичных symbols нет).

## TESTS (tests_09/test_missing_registry.py, аддитивно)

- `related_prompts` roundtrip: register с related_prompts → get → to_dict → from_dict (persistence);
- `add_related_prompt`: append + dedup + KeyError на ghost;
- `mark_implemented --related-prompt` через CLI → реестр содержит список;
- `validate_schema`: related_prompts не-list / пустая строка → violation; корректный → clean;
- backward-compat: существующие записи без related_prompts → `[***REMOVED***` (не падают);
- CLI `add-related-prompt` smoke + `list --json` содержит related_prompts.

## VALIDATION GATE

1. `python -m pytest tests_09/test_missing_registry.py -q`
2. `python -m mypy core_02/missing_registry.py --ignore-missing-imports`
3. `consistency_check` → TOTAL 0
4. `python -m core_02.missing_registry check` → exit 0

## REGISTER-FIRST

- capability: `missing_registry_multi_prompt` (kind=capability, factory=governance);
- lifecycle: register → mark-prompt-written → mark-implemented (этот промт);
- §20 карта v1.1: row #19;
- CHANGELOG: v5.189.19.

# END OF PROMPT
