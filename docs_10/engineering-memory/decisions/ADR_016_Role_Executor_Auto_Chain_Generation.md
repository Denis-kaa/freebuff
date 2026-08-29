# ADR-016: RoleExecutorRegistry — автоисполнение LIGHT-ролей Blueprint v3

> **Статус:** Proposed (дизайн зафиксирован; реализация — отдельный заход)
> **Дата:** 2026-08-18
> **Связанные:** ADR-013 (ForgeFacade Blueprint v3 bridge), CON-60 (routing canon), CON-61 (автоисполнение конвейера).

## Context
Проход по 14 ролям Blueprint v3 должен быть **автоматическим сценарием**: один запуск, все роли до конца, без ручного «продолжай / следующий шаг». Кейс `sheet_project` выявил разрыв: `ForgeFacade.run_chain` (core_02/forge_facade.py) для LIGHT-ролей выполняет только `check_only` — `RoleArtifactValidator` проверяет **существование** файлов (`DEFAULT_ROLE_OUTPUTS`), но **не генерирует** их. HEAVY-роли проходят full_cycle ForgePipeline, но в read-only тоже не создают код. Сценарий (`blueprint_v3.py` = role corpus) хранит блюпринты ролей, но не исполняет их. Генерация LIGHT-артефактов (brief.md, lisa_report.md, risk_matrix.md, decomposition.md, architecture.md, contracts.yaml, adr/, audit_report.md) выполнялась агентом вручную, по одному за сообщение.

## Decision
Ввести аддитивный слой **`RoleExecutorRegistry`** (`core_02/role_executor.py`) — реестр `role_id → executor`, **отдельный от Scenario** (Scenario остаётся чистым корпусом данных, §7.3 не нарушается). Унифицированный интерфейс:

```python
class BaseRoleExecutor(ABC):
    def execute(self, project: Project, role: Role, **kwargs) -> list[str***REMOVED***:
        """Вход: контекст проекта + манифест роли. Выход: список созданных файлов (relative paths)."""
```

- **Детерминированные роли** — tool-обёртки (пример: `lisa` → `scripts_01/lisa_estimator.py` уже генерирует `lisa_report.md`).
- **LLM-роли** (explainer / risk / decomposer / architect / auditor / documenter) — вызов модели по blueprint-промпту роли (`Scenario.load_role_text(role_id)`), без eval/exec/shell.

`ForgeFacade.run_chain` получает параметр `light_mode: "check_only" | "generate"` (дефолт `check_only`) и опциональный `executor_registry`. В режиме `generate`, если артефакт роли отсутствует/partial — вызывается `executor.execute()`, затем `RoleArtifactValidator` подтверждает существование. CLI: `forge.py chain --generate` (одна команда = весь конвейер до конца).

## Alternatives
- **(а) Сделать Scenario исполняемым** (role → generator-функция) — отвергнуто: Scenario = данные/DTO (корпус блюпринтов); загрузка логики генерации смешивает данные и логику и раздувает корпус.
- **(б) Зашить генерацию в ForgeFacade напрямую** — отвергнуто: Forge = оркестратор (порядок/валидация/персистенс/resume); конкретная генерация роли — отдельная ответственность.
- **(в) Отдельный RoleExecutorRegistry + флаг режима на run_chain** — **ВЫБРАНО**: минимально аддитивно, сохраняет layering scenario(данные) / forge(оркестрация) / executor(генерация) и границу §7.3.

## Trade-offs
- **Выигрываем:** автоисполнение конвейера без ручных шагов; поэтапное внедрение (по одной роли, начиная с детерминированных); обратная совместимость (дефолт остаётся `check_only`, существующие тесты не ломаются).
- **Теряем:** ещё один слой/реестр; LLM-роли требуют реальных model-вызовов (частичная потеря детерминизма, требуется observability/retry).

## Consequences
- `run_chain` обзаводится режимом генерации; существующие тесты (`test_forge_chain_real_integration.py`, `test_run_chain.py`) не затрагиваются при дефолте.
- **Первый вертикальный срез:** `LisaExecutor` (детерминированный, обёртка lisa_estimator) + plumbing `--generate` + тесты; затем LLM-экзекьюторы для explainer/risk/decomposer/architect/auditor/documenter.
- **Точка входа:** `forge.py chain --generate`; Factory впоследствии может вызывать `run_chain(..., light_mode="generate")` (вертикальный срез через существующий execution boundary).
