# PROMPT: ADVANCED OPPORTUNITY RANKING v1.0

## РОЛЬ

Senior AI Systems Architect + Senior Python Engineer.

Продолжение roadmap Phase 5 (09_FUTURE_GAPS.md §C-1): «Advanced Opportunity Ranking — быстрый выигрыш поверх provenance confidence».

## SOURCE OF TRUTH

Repository — источник истины.

Перед реализацией проверь фактическое состояние:

- `scripts_01/opportunity_engine.py` — `discover_candidates()`, `provenance['confidence'***REMOVED***`, `priority`, CLI;
- `tests_09/test_intelligence_loop_phase5.py` / `test_opportunity_engine.py` — конвенции герметичных тестов;
- `data_13/missing_registry.yaml` + §20 карта v1.1 (`FACTORY_FORGE_ARCHITECTURE_V1.md`) — register-first.

Если GAP уже закрыт — зафиксируй ALREADY RESOLVED, не реализуй повторно.

## GAP (зафиксирован в 09_FUTURE_GAPS.md A-2)

Сейчас кандидаты DISCOVER ранжируются только:

- порядком источников (whim → pulse → events → knowledge);
- raw `provenance['confidence'***REMOVED***` из источника.

Нет композитного score, нет traceability ранга, нет способа «взять топ-N лучших по совокупности сигналов».

## SCOPE — разрешено

- `scripts_01/opportunity_engine.py` (АДДИТИВНО, CAN-16 — существующие функции не переписывать);
- `tests_09/test_opportunity_ranking.py` (НОВЫЙ файл);
- реестры/доки: `data_13/missing_registry.yaml`, §20 карта v1.1, `CHANGELOG.md`.

## SCOPE — НЕ делать

- новый storage / БД;
- новый EventBus / Memory / Learning;
- новый CLI-фреймворк;
- массовый рефакторинг;
- изменение lifecycle opportunity / state machine.

## SPEC

1. Константы (module-level, документированные веса, сумма = 1.0):

   - `RANK_WEIGHTS = {"confidence": 0.5, "source": 0.2, "recency": 0.2, "priority": 0.1***REMOVED***`
   - `SOURCE_WEIGHTS = {"whim": 1.0, "hand": 1.0, "knowledge": 0.8, "project_pulse": 0.6, "event_bus": 0.5***REMOVED***`
   - `_RECENCY_DAYS = 30.0` (линейный decay свежести)

2. `rank_score(opp, *, now=None, weights=None) -> float` — композитный score в [0,1***REMOVED***:

   score = confidence·w_conf + source·w_src + recency·w_rec + priority·w_pri

   - confidence: из `provenance['confidence'***REMOVED***`, clamp [0,1***REMOVED***, default 0.5;
   - source: `SOURCE_WEIGHTS.get(source, 0.5)`;
   - recency: свежий (0 дней) = 1.0 → 30+ дней = 0.0; нет даты = 0.5;
   - priority: `(priority - 1) / 9` clamp [0,1***REMOVED***, default 5 → 0.444;
   - `weights` — опциональный override (аддитивно к дефолту).

3. `rank_candidates(candidates, *, now=None, weights=None, persist_score=True) -> List[Opportunity***REMOVED***`
   — сортировка по убыванию score; tie-break: новее `created_at` → раньше, затем стабильность исходного порядка.
   При `persist_score=True` пишет `provenance['rank_score'***REMOVED***` + `provenance['rank_factors'***REMOVED***`
   (breakdown confidence/source/source_weight/recency/priority_norm) — traceability.

4. `discover_candidates(..., rank=False)`:
   - `rank=True` → собрать пул со всех источников БЕЗ раннего обрыва по max_results, дедуп, `rank_candidates()`, срез top-N;
   - `rank=False` → РОВНО текущее поведение (backward-compat, ранний обрыв сохранён).

5. CLI:
   - `discover --rank` (флаг на подкоманде discover);
   - подкоманда `rank` — read-only: ранжирование существующих stored opportunities (score в выводе, store НЕ мутируется).

6. `__all__` дополнить: `rank_score`, `rank_candidates`, `RANK_WEIGHTS`, `SOURCE_WEIGHTS`.

## TESTS (tests_09/test_opportunity_ranking.py, герметичные)

- unit `rank_score`: дефолтные веса, clamp confidence, source-weights (whim=1.0 / event_bus=0.5 / unknown=0.5), recency decay (свежий vs 40 дней назад), priority norm (1→0, 5→0.444, 10→1), custom weights override;
- `rank_candidates`: сортировка по убыванию, tie-break по свежести, стабильность полного тай-брейка, persist rank_score/rank_factors;
- интеграция `discover_candidates(rank=True)`: top-N по score (whim PROMOTE_CANDIDATE 0.8 выше plain 0.6);
- backward-compat: `rank=False` сохраняет порядок источников;
- CLI smoke: `rank` subcommand через `main()` на tmp-store.

## VALIDATION GATE

1. `python -m pytest tests_09/test_opportunity_ranking.py tests_09/test_opportunity_engine.py tests_09/test_intelligence_loop_phase5.py -q`
2. `python -m mypy scripts_01/opportunity_engine.py --ignore-missing-imports` (только pre-existing)
3. `consistency_check` → TOTAL 0
4. `missing_registry check` → exit 0 (register-first цикл закрыт: registered → prompt_written → implemented)

## REGISTER-FIRST

- capability: `opportunity_ranking` (kind=capability, factory=content);
- lifecycle: register → mark-prompt-written → mark-implemented (этот промт);
- §20 карта v1.1: row #18;
- CHANGELOG: v5.189.18.

# END OF PROMPT
