# ARTIFACT_CONTRACT_DESIGN_V1.md — Единый Artifact-контракт (файл ↔ dict ↔ ChainRun)

> **Статус:** IMPLEMENTED (v5.189.78; код и hermetic-тесты добавлены аддитивно).
> **Дата:** 2026-08-22
> **Проблема:** обнаружена в этой сессии (ARCHITECTURE_DECISION_108_V1 §H GAP P2 «Единый Artifact-контракт»,
> CONTRACT_GRAPH_V1 §G8 FORGE→ARTIFACT PARTIAL): результат Forge представлен **тремя несвязанными формами**.
> **Цель:** единый канонический контракт артефакта + двусторонние адаптеры (файл ↔ dict ↔ ChainRun) —
> аддитивно (CAN-16), без переписывания существующих модулей; `factory_base.normalize_output` делегирует новому контракту.

---

## 1. Три текущих представления (evidence)

| # | Форма | Где создаётся | Поля (фактические) | Evidence |
|---|-------|--------------|--------------------|----------|
| **A** | `ChainRun` (frozen dataclass) | `core_02/forge_facade.py:258` | `project_id, project_root, stage_count, chain: tuple[ChainStage***REMOVED***, overall, started_at, finished_at, validation_registry_status, validation_summary` | `forge_facade.py:258-296` |
| **B** | `Artifact` (dict) | `core_02/factory_base.py::normalize_output` | `id, kind, opportunity_id, project_id, capability, factory_id, forge_id, target, overall, validation, created_at` | `factory_base.py:401-420` |
| **C** | Файлы на диске | `core_02/forge_pipeline.py::_ensure_artifacts` | `RUNNABLE.md`, `CHECKLIST.md` + role-специфичные (DEFAULT_ROLE_OUTPUTS: `brief.md`, `architecture.md`, `src/**/*.py`, `adr/*.md`…) | `forge_pipeline.py:267-281`, `forge_facade.py:101-130` |
| — | `opp.artifacts` (list[dict***REMOVED***) | `scripts_01/opportunity_engine.py:963` | `[{"raw": ChainRun.to_dict()***REMOVED******REMOVED***` | `opportunity_engine.py:963` |

**Проблема:** A — детали исполнения (stages/validation), B — трассировка домена (capability/factory/forge),
C — физические файлы. Никто не связывает их; `opp.artifacts` хранит только сырой `ChainRun.to_dict()`.

---

## 2. Принципы контракта

1. **ADDIITIVE (CAN-16):** новый модуль `core_02/artifact.py` + новый dataclass `Artifact`; существующие
   ChainRun/dict/файлы НЕ переписываются — контракт их **оборачивает** (WRAP, промт 108 §18).
2. **Двусторонние адаптеры:** `Artifact.from_chain_run(...)`, `Artifact.to_dict()`, `Artifact.resolve_files()`,
   `Artifact.from_dict(...)` — конвертация БЕЗ потери данных.
3. **Единый источник truth:** каноническое представление — dataclass `Artifact`; dict и ChainRun — проекции. Для ChainRun сохраняются `started_at`, `finished_at` и `validation_registry_status` без потери данных.
4. **Backward compatibility:** существующие потребители (opportunity_engine `opp.artifacts`, factory_base
   `normalize_output`) продолжают работать; контракт подключается аддитивно (factory_base может начать
   возвращать `Artifact` через тот же `to_dict()`).
5. **Закрытые словари:** `overall` ∈ {ok, partial, failed, degraded, unknown***REMOVED***; `artifact_kind` — токены из
   factory_base (`generic_artifact`, `content`, `research`, `test`…) — без дрейфа (ANTI-6b).

---

## 3. Целевой контракт `Artifact`

```python
# core_02/artifact.py (NEW, additive — design, НЕ реализация)

@dataclass(frozen=True)
class Artifact:
    """Канонический артефакт Forge-исполнения. Проекция: файлы ↔ dict ↔ ChainRun."""

    # ── Идентификация (из B: factory_base.normalize_output) ──
    id: str                       # art_... (ID_PREFIX)
    kind: str                     # artifact_kind (closed-set)
    opportunity_id: str
    project_id: str

    # ── Домен/трассировка (из B) ──
    capability: str               # closed-set токен (KNOWN_CAPABILITIES)
    factory_id: str               # адвизорный (traceability)
    forge_id: str                 # адвизорный (traceability)

    # ── Результат (из A: ChainRun) ──
    overall: str                  # ok | partial | failed | degraded | unknown
    chain: Tuple[Dict[str, Any***REMOVED***, ...***REMOVED***     # проекция ChainStage.to_dict() (mode/status/details)
    stage_count: int
    validation: Optional[Dict[str, Any***REMOVED******REMOVED***  # проекция ValidationSummary.to_dict()

    # ── Физические файлы (из C: forge_pipeline + DEFAULT_ROLE_OUTPUTS) ──
    target: str                   # "projects_17/<id>/forge/"
    files: Tuple[str, ...***REMOVED*** = ()   # относительные пути созданных артефактов (RUNNABLE.md, …)

    # ── Мета ──
    created_at: str
    project_root: str = ""

    # ── Адаптеры ──
    def to_dict(self) -> Dict[str, Any***REMOVED***: ...            # → B (обратно совместим с factory_base)
    def to_chain_run_dict(self) -> Dict[str, Any***REMOVED***: ...  # → A (сырой ChainRun.to_dict() для opp.artifacts)
    def resolve_files(self, root: Path) -> List[Path***REMOVED***:  # → C (существующие файлы в target)
    @classmethod
    def from_chain_run(cls, run, request, files, now) -> "Artifact": ...  # A+B+C → Artifact
    @classmethod
    def from_dict(cls, d: Dict[str, Any***REMOVED***) -> "Artifact": ...              # B → Artifact (round-trip)
```

---

## 4. Маппинг полей (три → один)

| `Artifact` поле | Источник (форма) | Фактическое поле |
|-----------------|------------------|------------------|
| `id` | B | `self._new_id()` (factory_base:405) |
| `kind` | B | `request.output_spec["artifact_kind"***REMOVED***` (:406) |
| `opportunity_id` | B | `request.opportunity_id` (:407) |
| `project_id` | B | `request.project_id` (:408) |
| `capability` | B | `request.capability` (:409) |
| `factory_id` | B | `request.factory_id` (:410) |
| `forge_id` | B | `request.forge_id` (:411) |
| `overall` | B/A | `run.overall` (:413) / ChainRun.overall (forge_facade:283) |
| `validation` | B/A | `run.validation_summary.to_dict()` (:414-419) |
| `target` | B | `request.output_spec["target"***REMOVED***` (:412) |
| `chain` | A | `ChainRun.chain → [s.to_dict()***REMOVED***` (forge_facade:289) |
| `stage_count` | A | `ChainRun.stage_count` (:281) |
| `files` | C | `_ensure_artifacts() → created` + `DEFAULT_ROLE_OUTPUTS` (forge_pipeline:267-281) |
| `created_at` | B | `_now_iso()` (:420) |
| `project_root` | A | `ChainRun.project_root` (:280) |

**Обратная совместимость:**
- `Artifact.to_dict()` == текущему dict из `factory_base.normalize_output` + 2 новых ключа (`chain`, `stage_count`,
  `files`, `project_root`) — **надмножество**, существующие потребители не ломаются.
- `Artifact.to_chain_run_dict()` == `ChainRun.to_dict()` 1:1 (для `opp.artifacts` и event payloads).
- Если контракт внедряется в `factory_base.normalize_output` — сигнатура метода не меняется (возвращает
  `Dict`), внутри — строит `Artifact.from_chain_run(...).to_dict()`.

---

## 5. Lifecycle-интеграция (аддитивно)

```
ChainRun (forge_facade)
   │  from_chain_run(request, run, files)
   ▼
Artifact (canonical)
   │  to_dict() → factory_base.normalize_output (существующий контракт B)
   │  to_chain_run_dict() → opp.artifacts / events (существующий контракт A)
   │  resolve_files() → pipeline-файлы на диске (существующий контракт C)
   ▼
accumulate(): MemoryStore kind=candidate + LearningLoop (не меняется)
```

**Кто пишет / кто читает (промт 108 §11):**

| Роль | Кто | Форма |
|------|-----|-------|
| Пишет | `factory_base.normalize_output` (→ Artifact.to_dict) | B (dict) |
| Пишет | `opportunity_engine.execute` (opp.artifacts) | A (ChainRun dict) |
| Читает | `opportunity_engine.accumulate` (memory) | B + A |
| Читает | `forge_facade.validate_role_artifacts` (existence) | C (файлы) |
| Читает | EventBus-подписчики (`execution.completed`) | A |

---

## 6. Что контракт НЕ делает (scope discipline, ANTI-5)

- ❌ НЕ переписывает ChainRun / forge_pipeline; `normalize_output` только делегирует новому адаптеру.
- ❌ НЕ вводит новый storage (артефакты остаются файлами + memory KO).
- ❌ НЕ решает task ×2 / memory ×4 (отдельные P2).
- ✅ Реализован отдельным additive-заходом: `core_02/artifact.py` + `tests_09/test_artifact.py` (13 hermetic-тестов).

---

## 7. Риски миграции (промт 108 §L)

| Риск | Митигация |
|------|-----------|
| Дрейф vocabulary (`kind`, `overall`) | closed-set + ANTI-6b валидация в `Artifact.__post_init__` (ValueError при неизвестном токене) |
| `files` — расхождение с диском | `resolve_files()` проверяет `Path.exists()`, возвращает только реальные; отсутствующие — в `validation` |
| Слом `opp.artifacts` (ожидает list[dict***REMOVED***) | `to_chain_run_dict()` 1:1 с ChainRun.to_dict() — BC |
| Двойное написание (dict в 2 местах) | единый `Artifact`; `normalize_output` и `execute` оба строят из него (аддитивно) |
| Период внедрения | контракт подключается по одному потребителю за раз (factory_base → opportunity_engine → events) |

---

## 8. Реализация (v5.189.78)

1. **REGISTER-FIRST:** `artifact_contract` зарегистрирован в `data_13/missing_registry.yaml` как `module`,
   затем прошёл lifecycle `registered → prompt_written → implemented`.
2. **Runtime:** `core_02/artifact.py` — frozen dataclass + `from_chain_run`/`from_dict`/`to_dict`/
   `to_chain_run_dict`/`resolve_files`; `core_02/factory_base.py::normalize_output` подключён без изменения сигнатуры.
3. **Тесты:** `tests_09/test_artifact.py` — 13 hermetic-тестов, включая round-trip, точное сохранение
   ChainRun metadata, BC-ключи, path-traversal guard и integration с `normalize_output`.
4. **Проверка:** релевантный regression-suite — `106 passed, 1 xpassed`; `mypy core_02/artifact.py` — без ошибок;
   `mypy core_02/factory_base.py` не завершился за 180 секунд (ограничение времени проверки, не ошибка typecheck).

---

## 9. Связь с baseline / ADR

- **CONTRACT_GRAPH_V1.md §G8:** FORGE→ARTIFACT переведён PARTIAL → CONFIRMED (v5.189.78).
- **ARCHITECTURE_DECISION_108_V1.md §H GAP P2:** GAP закрыт реализацией `core_02/artifact.py`.
- **COMPETING_ABSTRACTIONS_MATRIX_V1.md:** артефакт — не дублирование, а **3 проекции одной сущности** (WRAP, не MERGE).
- **MissingRegistry:** `artifact_contract` lifecycle `registered → prompt_written → implemented`.
- **Порядок (промт 108 §27):** baseline (✅) → contract design → implementation → tests (✅).

---

## 10. История

- **v1.1 (2026-08-22):** контракт реализован аддитивно: `core_02/artifact.py`, интеграция в `factory_base.normalize_output`, 13 hermetic-тестов; добавлены сохранение полного ChainRun metadata и path-traversal guard.
- **v1.0 (2026-08-22):** дизайн-контракт создан по результатам ARCHITECTURE_DECISION_108_V1 (TOP 4).
  Источники полей: `forge_facade.py:258-296`, `factory_base.py:401-420`,
  `forge_pipeline.py:267-281`, `opportunity_engine.py:963`.
