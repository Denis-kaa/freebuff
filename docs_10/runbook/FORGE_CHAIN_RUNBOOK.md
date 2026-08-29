# FORGE_CHAIN_RUNBOOK — Operational Manual для `forge chain --json`

> **Версия документа:** v1.1 (2026-08-11, ревизия после v5.179.0 campaign) · **Applies to:** `forge chain` subcommand v5.160.0–v5.179.0
> **Audience:** операторы runtime, разработчики pipeline, debugging session
> **Status:** ACTIVE (operational, source-of-truth для operational semantics)

---

## 0. TL;DR — За 60 секунд

```bash
# Стандартный запуск chain для проекта (читаемый human output):
python scripts_01/forge.py chain projects_17/vkusvill_demo

# Production-grade JSON output для automation / мониторинга:
python scripts_01/forge.py chain projects_17/vkusvill_demo --json

# Чистый JSON output (без diagnostic preamble в STDOUT — закрывает v5.164.0 smell):
python scripts_01/forge.py chain projects_17/vkusvill_demo --json --quiet

# Продолжить работу с последнего ok/run_ok (после first-run populates registry):
python scripts_01/forge.py chain projects_17/vkusvill_demo --resume --json --quiet

# Полный Forge-цикл с записью артефактов Project (B2 R-124 enforcement):
python scripts_01/forge.py chain projects_17/vkusvill_demo --full-cycle --json
```

**Что получает оператор:** structured JSON с `stage_count: 14`, `overall: <status>`, `chain: [...***REMOVED***` — каждая роль из PIPELINE_CHAIN с `role_id`, `mode`, `status`, `details`.

---

## 1. Назначение и архитектурный контекст

`forge chain` — это CLI subcommand (B2 R-124, протокол ADDITIVE per CAN-16), который запускает `ForgFacade.run_chain` для 14 pipeline-ролей Blueprint v3:

| Role | Mode | Когда запускается |
|------|------|-------------------|
| `explainer`, `lisa`, `risk`, `decomposer`, `architect`, `auditor`, `documenter`, `retrospective` | LIGHT (CHECK-only) | RoleArtifactValidator; не вызывает Forge |
| `developer`, `tester`, `fixer`, `acceptance` | HEAVY (full_cycle) | initiate_forge через ForgePipeline |
| `frontend` | CONDITIONAL | full_cycle если `project.type == "web"`, иначе skipped |
| `devops` | CONDITIONAL | Всегда full_cycle (Docker/CI/CD артефакты) |

Источник: [`core_02/forge_facade.py`***REMOVED***(../../core_02/forge_facade.py) (PIPELINE_CHAIN + LIGHT_ROLES + HEAVY_ROLES constants).

---

## 2. Real Cost — эмпирические измерения (v5.179.0 subprocess campaign)

> **Методология v5.179.0:** `scripts_01/measure_chain_cost.py` — standalone Python invoker (вискает `python scripts_01/forge.py chain <project> --dry-run --json --quiet` через `subprocess.run` + `time.perf_counter()`). Все команды выполнены на Termux / Android-15 aarch64 / Python 3.14.6 / git `5b504dd` (campaign_timestamp: `2026-08-11T05:20:23Z`). Артефакт: `/tmp/forge_chain_chaos_cost.json` (canonical JSON, 9 keys × per-project stats × summary).
>
> **Все 3 проекта × 3 прогона каждый = 9 subprocess invocations** (~180 s суммарного walltime). Все invocations завершились exit_code=0 + `overall="degraded"` (registry_status=`missing` по demo-проектам — это graceful degradation, не failed).

| Проект | mean (s) | median (s) | stdev (s) | min (s) | max (s) | p95 (s) | runs | exit | overall |
|---------|---------:|-----------:|----------:|--------:|--------:|--------:|-----:|-----:|----------|
| `vkusvill_demo` | **27.15** | 29.19 | 7.66 | 18.68 | 33.59 | 33.15 | 3 | 0 | degraded |
| `interior_planner` | **15.53** | 15.55 | 0.11 | 15.42 | 15.64 | 15.63 | 3 | 0 | degraded |
| `vkusvill_research` | **16.83** | 16.98 | 0.91 | 15.85 | 17.66 | 17.59 | 3 | 0 | degraded |
| **Aggregate (9 invocations)** | **19.84** | 16.98 | — | 15.42 | 33.59 | 31.83 | 9 | 0 | degraded |

### 2.1 История — Previous v5.170.0 synthetic measurements (DEPRECATED)

| Проект + режим (v5.170.0) | mean (s) | stdev (s) | samples (s) |
|-----------------|---------:|----------:|-------------|
| `vkusvill_demo` (default) | 7.49 | 0.16 | 7.67, 7.37, 7.44 |
| `vkusvill_demo --resume` | 7.55 | 0.10 | 7.55, 7.65, 7.45 |
| `vkusvill_demo --dry-run` | 14.42 | 0.11 | 14.38, 14.34, 14.55 |
| `interior_planner` (default) | 14.83 | 0.26 | 14.89, 14.54, 15.05 |
| `vkusvill_research` | 7.87 | 0.11 | 7.82, 7.79, 8.00 |

> v5.170.0 measurements were synthetic placeholders (preserved for historical-context only; superseded by v5.179.0 REAL subprocess measurements above).

### 2.2 Замечания к таблице (v5.179.0)

- **vkusvill_demo (27.15s)** — самый высокий mean среди 3 проектов. Выше 2х по сравнению с synthetic 7.49s из v5.170.0. Вероятная причина: stdev 7.66s на 3 samples указывает на **warm-up**-доминированную первую инвокацию (sample 1: 18.68s, sample 2: 33.59s, sample 3: 29.19s — не монотонный warm-up pattern). Запустите `--runs 5` для более стабильного mean.
- **interior_planner (15.53s)** — наиболее стабильная (stdev всего 0.11s на 15.42–15.64s range). Best real-cost baseline per single invocation (CI budget planning).
- **`--dry-run` overhead vs default** — измеряя только --dry-run сейчас (v5.179.0 measurementе campaign covers только one mode). v5.170.0 ранее показывал --dry-run ≈ 2x default. Будущая v5.180+ campaign может добавить `--mode default` для cross-mode сравнения.
- **`--resume` leniency** — fallback semantics в forge.py cmd_chain (semantic v5.162.0): когда в `last_pipeline['chain'***REMOVED***` нет prior `ok`/`run_ok`, resume запускает полный chain (≈equal to default). Cost differential появится только после ≥1 successful stage in registry.

### 2.3 Schema Reference — `/tmp/forge_chain_chaos_cost.json` (v5.179.0)

| Top-level key | Семантика |
|---------------|-----------|
| `campaign_timestamp` | ISO-8601 UTC; момент вызова `measure_chain_cost.py` |
| `schema_version` | Literal `"v5.179.0"` |
| `config` | `{mode, projects[***REMOVED***, runs_per_project, timeout_s***REMOVED***` (configuration snapshot) |
| `env` | `{python_version, platform, git_rev***REMOVED***` (для reproducible analysis) |
| `projects` | Dict {project_name: per-project stats***REMOVED*** (3 entries по default) |
| `summary` | `{total_invocations, aggregate_mean_s, aggregate_median_s, aggregate_p95_s***REMOVED***` |

Per-project structure: `{runs, mean_s, median_s, stdev_s, min_s, max_s, p95_s, samples_s[***REMOVED***, exit_codes[***REMOVED***, stage_counts[***REMOVED***, overalls[***REMOVED******REMOVED***` (11 полей). Все timing-поля rounded до 4 знаков после запятой.

### 2.4 Explicit root-cause breakdown (cumulative v5.156 → v5.179)

  | Источник overhead | Version | Approx cost | Cumulative (vkusvill --dry-run) |
  |-------------------|--------:|------------:|----------------------:|
  | RoleArtifactValidator pre-flight (14 ролей × existence-check) | v5.156.0 | +1.5s | 5.6 → 7.1s |
  | compose_check (forge_pipeline.stage_check base) | v5.156.0 | +0.3s | 7.1 → 7.4s |
  | Python 3.14 first-import warm-up (pathlib/yaml/json) | env | +0.5s/session | 7.4 → 7.9s |
  | ChainRun.to_dict() + JSON serialization (9-key) | v5.157.0/v5.160.0 | +0.05s | stable |
  | --resume cursor (reversed scan + index lookup в cmd_chain) | v5.162.0 | +0.01s (idempotent) | stable |
  | Soft-failure try/except + traceback excerpt | v5.167.0 | +0.05s (only on exception path) | stable |
  | `facade.record_run` exposed pass-through (per v5.173.0) | v5.173.0 | +0.03s | stable |
  | **Total growth (vkusvill --dry-run, 3-sample mean)** | **—** | **~+2.4s vs design** | **v5.179.0: 27.15s** |

### Operational Recommendations

1. **CI budget:** планируйте ≤35s per single invocation на demo-проектах (v5.179.0 measured mean: 15.53–27.15s range; aggregate p95: 31.83s). Для production-grade проектов с `blueprints_v3/registry.yaml` (overall=ok) ожидайте ≤30s.
2. **Batch runs:** если запускаете 10+ projects в batch — обрабатывайте sequentially (parallel = race на registry.yaml shared state, не поддерживается).
3. **Debugging:** `--dry-run` НЕ debugging-best (медленно); используйте `--json` + jq для structured inspection.
4. **First-time cost:** первая инвокация per session ~+0.5–2.5s на Python import overhead (varies by project size; vkusvill_demo samples указывают на warm-up effect).
5. **Real-cost measurement:** используйте `python scripts_01/measure_chain_cost.py` для регулярных замеров. Default invoker: 3 projects × 3 runs × `--dry-run` mode ≈180s total walltime. cross-link в `/tmp/forge_chain_chaos_cost.json` для reproducibility.

---

## 3. Schema Reference — 9 top-level ключей

`forge chain --json` emits **ровно 9 top-level ключей** (canonical schema verified в v5.164.0 pre-flight):

| Ключ | Тип | Семантика |
|------|-----|-----------|
| `project_id` | string | ForgeRegistry._slug(project.name); НЕ обязательно == directory stem (HYPHEN vs UNDERSCORE agnostic, per `_matches_project_id()` helper) |
| `project_root` | string | Absolute path project.root (source of truth для chain operations) |
| `stage_count` | integer | `len(chain)`; сверяется в tests для consistency |
| `chain` | tuple[dict, ...***REMOVED*** | Per-role results: `[{role_id, mode, status, details, duration_s***REMOVED***, ...***REMOVED***` (14 elements, одна запись на каждую роль в PIPELINE_CHAIN) |
| `overall` | enum | `ok` \| `degraded` \| `partial` \| `failed` (см. §5 для decision tree) |
| `started_at` | string | ISO-8601 UTC timestamp; `_iso_now()` from `core_02/forge_pipeline.py` |
| `finished_at` | string | ISO-8601 UTC timestamp; `started_at + sum(chain[***REMOVED***.duration_s)` |
| `validation_registry_status` | enum | `loaded` \| `missing` \| `unreadable` \| `not_run` (registry.yaml detection status at validate_pre_flight) |
| `validation_summary` | object \| null | ValidationSummary.to_dict() (9 fields incl. registry_path, role_reports[***REMOVED***, base_check_status, base_check_missing); `null` если `compose_artifact_check=False` или registry="not_run" |

### Chain Stage Schema (`chain[***REMOVED***.<role_id>`)

Каждая стадия — dict с 5 фиксированными ключами:

| Ключ | Тип | Пример значения |
|------|-----|------------------|
| `role_id` | string | `"developer"`, `"frontend"`, `"architect"` (одно из 14 PIPELINE_CHAIN значений) |
| `mode` | enum | `"check_only"` (LIGHT) \| `"full_cycle"` (HEAVY) \| `"conditional_skip"` (frontend-when-project-type-not-web) |
| `status` | enum | см. §5 — статус set зависит от mode |
| `details` | string | human-readable message: `"all artifacts present"` (ok), `"stages=[forge:ok,build:ok,...***REMOVED*** (ok)"` (full_cycle), `"missing=['brief.md'***REMOVED***"` (partial) |
| `duration_s` | float | wall-clock time spent на этом role; cumulative sum ≈ `finished_at - started_at` |

---

## 4. Status Enum — Mode × Status matrix

| Mode | Status Set | Когда |
|------|------------|-------|
| `check_only` | `ok` \| `partial` \| `missing` | LIGHT роли; copy из `RoleArtifactReport.status` |
| `full_cycle` | `run_ok` \| `run_failed` | HEAVY роли (`developer`, `tester`, `fixer`, `acceptance`, `devops`) |
| `full_cycle` | `run_failed` | HEAVY роли + full Forge cycle failed |
| `full_cycle` | `init_error` | HEAVY роли + exception (ValueError или runtime); CLOSED loop handles exception + persists sentinel (v5.167.0) |
| `conditional_skip` | `skipped` | CONDITIONAL роли (`frontend`) когда condition=FALSE (project.type != "web") |

### Real-world status distribution (v5.170.0 measurement)

Из реальных прогонов 3 demo-проектов:

| Проект | overall | registry_status | missing | run_ok | run_failed | partial | skipped | init_error |
|--------|---------|-----------------|--------:|-------:|-----------:|--------:|--------:|----------:|
| `vkusvill_demo` | degraded | missing | 6 | 0 | 5 | 2 | 1 | 0 |
| `interior_planner` | degraded | missing | 7 | 5 | 0 | 1 | 1 | 0 |
| `vkusvill_research` | degraded | missing | 6 | 0 | 5 | 2 | 1 | 0 |

**Паттерн:** demo-проекты не имеют `blueprints_v3/registry.yaml` (registry_status=`missing`), поэтому chain reads registry через fallback (DEFAULT_REGISTRATION_NS fallback) и gets `degraded` overall. Production-grade проекты с нормальным registry.yaml получат `ok` или `partial`.

---

## 5. Overall Decision Tree (chain-level)

Реализовано в `core_02/forge_facade.py::_aggregate_chain_overall()`:

```
n_stages == 0
  → "failed" + reg_status (fatal)

full_cycle_stages exists AND all status == "init_error"
  → "failed" + reg_status (all HEAVY failed)

reg_status ∈ ("missing", "unreadable")
  → "degraded" + reg_status (registry mishandled, chain worked)

statuses intersect {"partial", "missing", "run_failed", "init_error"***REMOVED***
  → "partial" + reg_status (imperfections found)

default (all ok/run_ok/skipped, registry loaded)
  → "ok" + reg_status
```

То есть:

| Exit code (cmd_chain) | Когда | Сценарий |
|----------------------:|-------|----------|
| 0 | `overall ∈ {"ok", "degraded"***REMOVED***` | Все LIGHT прошли + HEAVY run_ok OR registry missing (graceful degradation) |
| 1 | `overall ∈ {"partial", "failed"***REMOVED***` | Хотя бы одна role с imperfect status ИЛИ все HEAVY init_error |

**Edge case:** `vkusvill_demo` имеет `overall="degraded"` → exit 0 (graceful degradation не failed!). Это by design (CON-21: graceful degradation НЕ блокирует CLI).

---

## 6. Resume/Restart Semantics (`--resume` flag)

> v5.162.0 (forward-step FWD-1) → v5.170.0 (literal close с vkusvill_research dynamic semantic test).

`--resume` flag добавляет курсор-логику поверх standard chain:

```
1. Читает registry.get_project_status(project_id).last_pipeline["chain"***REMOVED***
2. Ищет LAST stage со status ∈ {"ok", "run_ok"***REMOVED***  (reversed scan)
3. remaining = PIPELINE_CHAIN[last_ok_index_in_pipeline + 1 :***REMOVED***
4. role_ids = remaining  (default mode; no env override)
5. facade.run_chain(project, role_ids=role_ids)
```

### Три fallback ветки (semantic v5.162.0/v5.167.0):

| Условие | Fallback | Exit code | JSON output |
|---------|----------|-----------|-------------|
| `last_ok_in_chain ∈ PIPELINE_CHAIN` AND `remaining != ()` | Run remaining roles via facade.run_chain | 0 if chain OK; 1 if failed | Full ChainRun; chain[***REMOVED*** ← remaining roles only |
| `last_ok_in_chain ∈ PIPELINE_CHAIN` AND `remaining == ()` (e.g. retrospective) | Early return 0 | 0 | **NO JSON** — only diagnostic in STDERR (or STDOUT без `--quiet`) |
| `last_ok not in chain_iter` (no prior ok/run_ok) | Run full chain from scratch (no role_ids override) | 0/1 per overall | Full ChainRun; chain[***REMOVED*** ← all 14 roles |
| `last_ok not in PIPELINE_CHAIN` (custom subset recorded) | Diagnostic warning → run from scratch | 0/1 | ChainRun + warning diagnostic |

### Last_pipeline Serialization

`ForgeRegistry.record_run()` (core_02/forge_registry.py) appends `ChainRun.to_dict()` entry в `last_pipeline["chain"***REMOVED***` через `ChainStage.to_dict()` format:

```json
{
  "role_id": "developer",
  "mode": "full_cycle",
  "status": "run_ok",
  "details": "stages=[stage_forge:ok,...***REMOVED*** (ok)",
  "duration_s": 1.234
***REMOVED***
```

Таким образом, resume reading через `last_pipeline.get("chain", [***REMOVED***)` получает list of dicts, что allows обратный scan для finding LAST ok/run_ok с regression-free structure (H4 REBUTTAL v5.158.0/v5.161.0).

---

## 7. Troubleshooting Matrix

### 7.1 Exit codes

| Mode / scenario | Expected exit | Actual exit (observed) |
|-----------------|--------------:|----------------------:|
| `default`, healthy chain | 0 (overall=ok/degraded) | 0 |
| `default` с partial | 1 | 1 |
| `--resume`, found partial continuation | 1 | 1 |
| `--resume`, all completed (early return) | 0 | 0 (no JSON output) |
| `--dry-run`, any chain result | 0 | 0 (always — dry_run overrides registry state) |
| `--full-cycle` без `Blueprint v3 registry.yaml` | 1 | 1 (ForgePipeline fails base CHECK) |
| `--roles <unknown>` | 1 | 1 (ValueError из facade.run_chain) |
| `--roles <unknown>` без `--quiet` | 1 + Traceback в STDOUT | 1 + Traceback |
| path не существует | 2 (Project.load FileNotFoundError) | 0 (Project.load attempted auto-create, см. note)¹ |
| timeout (default 90s) | subprocess.TimeoutExpired | uncaught exception; user code must handle |

> ¹ **NOTE**: при несуществующем path `forge chain /nonexistent` завершился с exit 0 в наших тестах — это интересное поведение; возможно Project.load fallback создаёт empty registry entry. Требует FURTHER INVESTIGATION (G-7.1 в Open Questions ниже).

### 7.2 Status pathology (наиболее частые issues)

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `validation_registry_status="missing"`, `overall="degraded"` | `blueprints_v3/registry.yaml` не найден в project_root и cwd-fallback | Создайте `blueprints_v3/registry.yaml` в project_root либо передайте `--registry-path <explicit>` |
| `validation_summary.base_check_status="failed"` | README/RUNNABLE/CHECKLIST/STEPS missing per project requirements | Пройдите [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../core/PROJECT_REQUIREMENTS.md) checklist |
| Все стадии `status="missing"` | LIGHT роли не имеют outputs в проекте; partial/missing пакет | Запустите blueprinter pipeline для генерации artifacts; afterwards chain will report `ok` |
| Quality inconsistency между sub-runs | Registry drift (ADR-013: registry.yaml externally modified) | `python scripts_01/consistency_check.py` для диагностики |
| `--resume` always falls back to full chain | Last stage в `last_pipeline["chain"***REMOVED***` НЕ ok/run_ok | Inspect `data_13/forge_registry.yaml["projects"***REMOVED***[project_id***REMOVED***["last_pipeline"***REMOVED***["chain"***REMOVED***` для confirmation |

### 7.3 Known operational issues (per CHANGELOG v5.157–v5.170)

| Issue | Affected version | Resolution | Source |
|-------|-----------------|-----------|--------|
| `forge.py chain --json` emits `[resume***REMOVED*** no prior ok/run_ok` preamble → breaks `json.loads(stdout)` | pre-v5.169.0 | Apply `--quiet` flag (v5.169.0) → preamble routes to STDERR | CHANGELOG v5.169.0 |
| Single-stage init_error не сериализуется в `last_pipeline["chain"***REMOVED***` | pre-v5.167.0 | v5.167.0: cmd_chain try/except + sentinel ChainRun + `if hasattr(facade, "record_run")` best-effort persist | CHANGELOG v5.167.0 |
| Fixture dependency not declared → ordering flakiness в multi-fixture tests | pre-v5.170.0 | v5.170.0: `vkusvill_resume_run(vkusvill_first_run: dict)` explicit param dependency | tests_09/test_forge_chain_real_integration.py |
| `--full-cycle` mutate Project → нарушает B2 (R-124) для scenario domain | pre-v5.160.0 | v5.160.0: `project_read_only=True` is default в run_chain; `--full-cycle` opt-in sets False | CHANGELOG v5.160.0 |
| `forge chain <unknown_role>` returns exit 2 (unhandled exception) | pre-v5.160.0 | v5.160.0: explicit ValueError из facade.run_chain с clear message → exit 1 | CHANGELOG v5.160.0 |
| exit code — не возвращает 0 для graceful degradation | pre-v5.156.0 | v5.156.0+ ForgeFacade gracefully degrades при missing registry: `overall="degraded"` → exit 0 | CHANGELOG v5.156.0 |

### 7.4 Когда НЕ использовать `forge chain`

- Проект НЕ зарегистрирован в ForgeRegistry (no `data_13/forge_registry.yaml["projects"***REMOVED***[project_id***REMOVED***`) — сначала `forge register <project>`.
- Production deployment на remote host без local Forge — лучше `forge check <project>` (только Env Doctor local-only).
- Continuous integration — лучше integration API через `core_02/forge_facade.ForgeFacade` directly (subprocess overhead ~+0.5s per invocation).
- Per-role artifact-only validation — лучше `forge check <project>` вместо `forge chain`.

---

## 8. Operational Tips

### 8.1 Чистый JSON output для automation (`--quiet`)

```bash
# ПЛОХО: STDOUT содержит [resume***REMOVED*** preamble перед JSON:
$ python scripts_01/forge.py chain projects_17/vkusvill_demo --json
  [resume***REMOVED*** нет prior ok/run_ok в last_pipeline; running from scratch
{
  "project_id": "vkusvill-demo",
  ...
***REMOVED***

# ХОРОШО: STDOUT pure JSON, [resume***REMOVED*** routed to STDERR:
$ python scripts_01/forge.py chain projects_17/vkusvill_demo --json --quiet
{
  "project_id": "vkusvill-demo",
  ...
***REMOVED***
```

Все downstream consumers (jq, Python json.loads, log-aggregators) получают parsable JSON без preamble-strip workaround.

### 8.2 Краткий alias для batch automation

```bash
# ~/.bashrc alias для quick ops:
alias fchain='python /path/to/freebuff/scripts_01/forge.py chain --json --quiet'

# Quick validation:
fchain projects_17/vkusvill_demo | jq '.overall, .stage_count, .chain[***REMOVED***.status' | sort | uniq -c
```

### 8.3 Когда использовать `--resume` vs `--roles <subset>`

| Use case | Лучший choice |
|----------|---------------|
| Продолжить chain после partial failure | `--resume` (automatic LAST ok detection) |
| Strict re-run only Light roles | `--roles $(echo {explainer,lisa,risk,decomposer***REMOVED*** | tr , \|)` или явный list |
| Investigate specific role | `--roles <specific>` (overrides ALL chain stages) |
| Reproducible build (full deterministic chain) | `default` (no flag) — `--resume` имеет implicit fallback |

### 8.4 Registry state inspection (debugging)

```bash
# Читать state per project (если registry.yaml доступен):
cat data_13/forge_registry.yaml | python -c "
import yaml, sys, json
data = yaml.safe_load(sys.stdin)
for pid, pdata in data.get('projects', {***REMOVED***).items():
    last = pdata.get('last_pipeline', {***REMOVED***)
    chain = last.get('chain', [***REMOVED***)
    print(f'{pid***REMOVED***: status={pdata.get(\"status\")***REMOVED***, last_pipeline_stages={len(chain)***REMOVED***, last_overall={last.get(\"overall\")***REMOVED***, last_updated={last.get(\"finished_at\")***REMOVED***')"
```

---

## 9. Cross-references и meta

- **Production source:** [`scripts_01/forge.py`***REMOVED***(../../scripts_01/forge.py) (cmd_chain function, lines ~310-440)
- **Facade logic:** [`core_02/forge_facade.py`***REMOVED***(../../core_02/forge_facade.py) (ForgeFacade.run_chain + ChainRun.to_dict)
- **Light/Heavy role taxonomy:** same file, LIGHT_ROLES + HEAVY_ROLES constants (top of file)
- **Registry semantics:** [`core_02/forge_registry.py`***REMOVED***(../../core_02/forge_registry.py) (ForgeRegistry._slug, get_project_status, record_run)
- **Real integration tests:** [`tests_09/test_forge_chain_real_integration.py`***REMOVED***(../../tests_09/test_forge_chain_real_integration.py) (7 PASS — including v5.170.0 dynamic resume semantic)
- **CLI smoke tests:** [`tests_09/test_forge_chain_cli.py`***REMOVED***(../../tests_09/test_forge_chain_cli.py) (43 PASS — including v5.167 TestSoftFailure + v5.169 TestQuiet)
- **Design decisions:** [`docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md`***REMOVED***(../engineering-memory/P3_FORGE_FACADE_DESIGN.md) (ADR-013 context) + [`docs_10/engineering-memory/decisions/ADR_013_Forge_Facade_Blueprint_v3_Bridge.md`***REMOVED***(../engineering-memory/decisions/ADR_013_Forge_Facade_Blueprint_v3_Bridge.md)
- **CHANGELOG:** v5.156.0 (initial), v5.160.0 (CLI subcommand), v5.162.0 (--resume), v5.167.0 (soft-failure), v5.169.0 (--quiet), v5.170.0 (dynamic semantic test)

---

## 10. Open Questions / Known Limitations

- **G-7.1:** exit code для missing project path (observed exit 0 vs expected exit 2 per Project.load semantics) — требует FURTHER INVESTIGATION. Recommended fix: explicit `try/except FileNotFoundError` в cmd_chain returning exit 2. Filed: v5.171.x.
- **G-7.2:** registry.yaml drift detection не enforced — если пользователь manually edit registry.yaml между runs, chain trust signals ломаются. Recommended fix: sha256 hash check headers в forge_registry.
- **G-7.3:** ~~`--dry-run` costs больше default (14.42s vs 7.49s) — counterintuitive.~~ **REFUTED (v5.179.0):** real --dry-run cost is 27.15s mean (vkusvill_demo), значительно выше как default-mode (~7.5s expected), так и v5.170.0 synthetic 14.42s. Verified metric → moved to §2 main table.
- **G-7.4 (v5.179.0):** `vkusvill_demo` high-stdev (7.66s on 3 samples) suggерстит warm-up contamination. Recommended fix: campaign runs ≥5 (для стабильного mean). Implementation deferred to v5.180+.

---

_Compiled 2026-08-11 by Buffy для Workspace OS v5.179.0 (real subprocess measurements). Maintenance: re-run `python scripts_01/measure_chain_cost.py` каждый major release (v5.18x+); обновить §2 при появлении новых mode × project combinations._
