# ADR-021: Unified Artifact contract — файл ↔ dict ↔ ChainRun

> **Статус:** Accepted/Implemented (v5.189.78)
> **Дата:** 2026-08-22
> **Связанные:** ARCHITECTURAL_BASELINE_V1.md §1/§4, ARCHITECTURE_DECISION_108_V1.md §H, CONTRACT_GRAPH_V1.md §G8, ADR-018, CAN-16.

## Context

Forge-результат имел три несвязанных представления:

1. `ChainRun` (`core_02/forge_facade.py:258`) — стадии, overall и validation.
2. Artifact-dict (`core_02/factory_base.py::normalize_output`) — capability/factory/forge/target.
3. Файлы проекта (`core_02/forge_pipeline.py::_ensure_artifacts`) — физические outputs.

`opp.artifacts` сохранял raw `ChainRun.to_dict()`, а единой модели, связывающей эти формы,
не было. Это классифицировалось как FORGE→ARTIFACT PARTIAL (promt 108 §9).

## Evidence

- `core_02/artifact.py::Artifact` — frozen canonical dataclass.
- `core_02/factory_base.py::BaseFactory.normalize_output` — делегирует `Artifact.from_chain_run(...).to_dict()` без изменения сигнатуры.
- `Artifact.to_dict()` сохраняет legacy-ключи и добавляет chain/stage/files/metadata.
- `Artifact.to_chain_run_dict()` сохраняет полный ChainRun contract, включая `started_at`, `finished_at`, `validation_registry_status`.
- `Artifact.resolve_files()` проверяет существующие файлы и отклоняет path traversal.
- `tests_09/test_artifact.py` — 13 hermetic-тестов; релевантный suite: 106 passed, 1 xpassed.

## Decision

Каноническим представлением результата является `Artifact` (`core_02/artifact.py`).
Существующие `ChainRun`, legacy dict и файлы не переписываются; они представлены через адаптеры:

- `from_chain_run` / `to_chain_run_dict` — ChainRun projection;
- `from_dict` / `to_dict` — backward-compatible dict projection;
- `resolve_files` — безопасная файловая projection.

`normalize_output` сохраняет прежний return type `Dict[str, Any***REMOVED***`; интеграция является additive.
`overall` использует closed set `{ok, partial, failed, degraded, unknown***REMOVED***`.

## Alternatives

- **MERGE/переписать ChainRun** — отвергнуто: нарушает BC и Forge boundary.
- **Оставить три независимые формы** — отвергнуто: теряется traceability.
- **Новый storage** — отвергнуто: контракт нормализует существующие outputs, не меняет persistence.

## Consequences

- FORGE→ARTIFACT переводится из PARTIAL в CONFIRMED.
- Legacy consumers продолжают получать dict с прежними ключами.
- Полный ChainRun metadata не теряется при round-trip.
- Файловая projection получает path-traversal guard.
- Дальнейшая интеграция в `opportunity_engine` и events выполняется отдельными малыми шагами.

## Implementation

- MissingRegistry: `artifact_contract` → `registered → prompt_written → implemented`.
- Runtime: `core_02/artifact.py`, `core_02/factory_base.py`.
- Tests: `tests_09/test_artifact.py`.
