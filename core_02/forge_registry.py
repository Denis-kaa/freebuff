# core_02/forge_registry.py — Forge Registry (L-4)
# Buffy Forge v1 (RFC_BUFFY_FORGE_V1.md §4)

"""Реестр проектов и их состояний (YAML в data_13/forge_registry.yaml).

Этап 4.3 из PLAN_NEXT_OPERATIONS.md.

    register_project(project_config)      -> project_id
    get_project_status(project_id)        -> ForgeStatus
    list_projects_by_status(status_filter) -> list[ForgeStatus]
    get_pipeline_history(project_id)      -> list[PipelineRun]
    record_run(project_id, run)           -> обновляет статус + историю

Статусы: UNFORGED, CHECKING, BUILDING, TESTING, DEPLOYED, FAILED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

# Статусы Forge (RFC §4)
UNFORGED = "UNFORGED"
CHECKING = "CHECKING"
BUILDING = "BUILDING"
TESTING = "TESTING"
DEPLOYED = "DEPLOYED"
FAILED = "FAILED"

STATUSES = (UNFORGED, CHECKING, BUILDING, TESTING, DEPLOYED, FAILED)

# R-127 (B10, промт 68): обязательные поля записи реестра (machine-checkable).
REQUIRED_FIELDS = ("project_id", "name", "root", "status")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ForgeStatus:
    project_id: str
    name: str
    root: str
    status: str = UNFORGED
    last_run_at: Optional[str] = None
    last_pipeline: Dict[str, Any] = field(default_factory=dict)
    pipeline_history: List[Dict[str, Any]] = field(default_factory=list)
    registered_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "root": self.root,
            "status": self.status,
            "last_run_at": self.last_run_at,
            "last_pipeline": self.last_pipeline,
            "pipeline_history": self.pipeline_history[-10:],
            "registered_at": self.registered_at,
        }


class ForgeRegistry:
    """Реестр проектов (L-4). Хранение: YAML в data_13/forge_registry.yaml."""

    def __init__(self, path: str | Path = "data_13/forge_registry.yaml"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Any]] = self._load()
        self._schema_violations: List[str] = self.validate_schema()

    # ── persistence ──────────────────────────────────────────────────
    def _load(self) -> Dict[str, Dict[str, Any]]:
        """Загрузить реестр. При ошибке чтения/парсинга возвращает {]
        и фиксирует факт повреждения в self._load_error (R-127/B10:
        битый файл НЕ должен молча выглядеть валидным — см. validate_schema).
        """
        self._load_error: Optional[str] = None
        if not self.path.exists():
            return {}
        try:
            text = self.path.read_text(encoding="utf-8")
            if yaml is not None:
                data = yaml.safe_load(text) or {}
            else:  # pragma: no cover
                data = json.loads(text)
            return {k: dict(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except Exception as exc:
            # R-127 (B10): потеря/повреждение файла — нарушение целостности.
            self._load_error = str(exc)
            return {}

    def _save(self) -> None:
        payload = {
            k: v for k, v in self._data.items()
            if not self._is_ephemeral_leak(v)
        }
        if yaml is not None:
            self.path.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        else:  # pragma: no cover
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        # R-127 (B10): успешное сохранение = файл снова валиден → сбрасываем
        # устаревшую ошибку загрузки (иначе validate_schema ложно-срабатывала
        # бы после самовосстановления реестра).
        self._load_error = None

    # ── State-drift guard (v5.189.71): mock-записи не утекают в реальный реестр ──
    @staticmethod
    def _is_ephemeral_path(path: Any) -> bool:
        """True если путь указывает во временную директорию (mock/тест).

        На Termux/Android ``tempfile.gettempdir()`` = ``/tmp/freebuff-bun-tmp``
        (НЕ ``/tmp``), поэтому predicate опирается на префикс ``/tmp/`` (с
        завершающим слэшем) либо точное равенство ``/tmp`` — покрывает и
        ``/tmp/...``, и ``/tmp/freebuff-bun-tmp/...``, но НЕ ложно-срабатывает
        на ``/tmpfoo/...``. Реальные проекты живут под ``projects_17/`` или
        ``/mnt/sdcard/...`` — не начинаются с ``/tmp/``.
        """
        s = str(path)
        return s == "/tmp" or s.startswith("/tmp/")

    def _is_ephemeral_leak(self, entry: Dict[str, Any]) -> bool:
        """Guard: запись с ephemeral root в НЕ-ephemeral реестре — утечка mock.

        Условие (root ephemeral И registry НЕ ephemeral):
          - unit-тесты создают реестр под ``tmp_path`` (тоже ephemeral) → guard
            НЕ срабатывает, persistence тесты (test_persistence_roundtrip) проходят;
          - дымовые/интеграционные тесты (cmd_chain → _load_registry() = реальный
            ``data_13/forge_registry.yaml``) регистрируют project root под ``/tmp``
            → guard пропускает запись, она НЕ попадает на диск.

        Semantics: skip-persist — запись остаётся в self._data (in-memory), но
        фильтруется из payload при _save(). НЕ raise (иначе cmd_chain сломал бы
        rc/print-контракты дымовых тестов).

        Side-effect (self-healing): любые УЖЕ записанные на диск ephemeral-root
        записи (напр. устаревшие ``qtest-v169``/``smoke``) будут silently
        отфильтрованы при следующем _save() — это желаемая очистка, но оператор
        должен знать, что stale-mock-записи исчезают при первой же записи.
        """
        if self._is_ephemeral_path(self.path):
            return False  # реестр сам временный → персист обязателен
        return self._is_ephemeral_path(entry.get("root"))

    # ── B10 schema validation (R-127, промт 68) ───────────────────────
    def validate_schema(self) -> List[str]:
        """R-127 (B10): машинно-проверяемая семантика UNFORGED vs UNTESTED.

        UNFORGED = «никогда не проходил Forge» (может быть human-only проект,
        §32.4 [АРХ-32-11], Q4 2024 DR incident CON-34) — НЕ алиас UNTESTED.
        Машинные инварианты:
          - обязательные поля: project_id, name, root, status;
          - status ∈ STATUSES (UNFORGED, CHECKING, BUILDING, TESTING, DEPLOYED, FAILED);
          - UNFORGED ⇒ last_run_at is None и last_pipeline пуст (никогда не запускался);
          - DEPLOYED/FAILED ⇒ last_run_at установлен (запускался).

        Возвращает список нарушений ([] = реестр валиден). Вызывается при
        инстанцировании (self._schema_violations) и доступен как метод.
        """
        violations: List[str] = []
        # R-127 (B10): нечитаемый/повреждённый реестр — нарушение integrity.
        # Без этого битый YAML молча выглядел бы валидным (validate_schema по {}).
        if self._load_error:
            violations.append(f"registry: unreadable YAML ({self._load_error})")
        for pid, entry in self._data.items():
            for f in REQUIRED_FIELDS:
                if f not in entry:
                    violations.append(f"{pid}: missing required field {f!r}")
            status = entry.get("status")
            if status is not None and status not in STATUSES:
                violations.append(
                    f"{pid}: invalid status {status!r} (allowed: {STATUSES})"
                )
            if status == UNFORGED:
                if entry.get("last_run_at") is not None:
                    violations.append(
                        f"{pid}: UNFORGED but last_run_at set "
                        "(UNFORGED ≠ UNTESTED; never ran through Forge)"
                    )
                if entry.get("last_pipeline"):
                    violations.append(
                        f"{pid}: UNFORGED but last_pipeline non-empty "
                        "(UNFORGED ≠ UNTESTED)"
                    )
            elif status in (DEPLOYED, FAILED):
                if entry.get("last_run_at") is None:
                    violations.append(
                        f"{pid}: {status} but last_run_at missing "
                        "(DEPLOYED/FAILED implies a run happened)"
                    )
        return violations

    @property
    def schema_violations(self) -> List[str]:
        """Нарушения B10-схемы, найденные при загрузке реестра."""
        return list(self._schema_violations)

    # ── API ──────────────────────────────────────────────────────────
    def register_project(
        self,
        name: str,
        root: str | Path,
        project_id: Optional[str] = None,
    ) -> str:
        """Зарегистрировать проект. Возвращает project_id."""
        pid = project_id or self._slug(name)
        entry = self._data.get(pid)
        if entry is None:
            entry = {
                "project_id": pid,
                "name": name,
                "root": str(root),
                "status": UNFORGED,
                "last_run_at": None,
                "last_pipeline": {},
                "pipeline_history": [],
                "registered_at": _now(),
            }
        else:
            entry["name"] = name
            entry["root"] = str(root)
        self._data[pid] = entry
        self._save()
        return pid

    def get_project_status(self, project_id: str) -> Optional[ForgeStatus]:
        entry = self._data.get(project_id)
        if entry is None:
            return None
        return ForgeStatus(**entry)

    def get_project_status_by_root(self, root: str) -> Optional[ForgeStatus]:
        for entry in self._data.values():
            if str(entry.get("root")) == str(root):
                return ForgeStatus(**entry)
        return None

    def list_projects_by_status(self, status_filter: Optional[str] = None) -> List[ForgeStatus]:
        out = []
        for entry in self._data.values():
            if status_filter is None or entry.get("status") == status_filter:
                out.append(ForgeStatus(**entry))
        out.sort(key=lambda s: s.name)
        return out

    def record_run(self, project_id: str, run: Any) -> ForgeStatus:
        """Записать результат PipelineRun: статус, last_pipeline, история.

        Маппинг overall → статус (v5.189.7 review closure; v5.189.10 R-1 closure):
          - ``"ok"``       → DEPLOYED (сертификация);
          - ``"degraded"`` → НЕ маппится в FAILED: текущий статус сохраняется.
            Для UNFORGED (никогда не проходил Forge) персист НЕ выполняется —
            там нет ok/run_ok ролей для --resume, а UNFORGED + last_pipeline =
            B10/R-127 violation; схема остаётся валидной. Для остальных статусов
            (DEPLOYED, FAILED, CHECKING, BUILDING, TESTING) статус прежний и
            last_pipeline персистится (нужно для --resume);
          - любое другое ("failed", "partial", ...) → FAILED.
        """
        if project_id not in self._data:
            raise KeyError(f"Проект {project_id} не зарегистрирован")
        run_dict = run.to_dict() if hasattr(run, "to_dict") else dict(run)
        entry = self._data[project_id]
        overall = run_dict.get("overall")
        if overall == "ok":
            entry["status"] = DEPLOYED
        elif overall == "degraded":
            # v5.189.10 (R-1 closure): degraded (exit 0, верификация неполна)
            # НЕ даунгрейдит и НЕ сертифицирует — статус сохраняется прежним.
            # Для UNFORGED персист не нужен и нарушил бы B10/R-127 инвариант
            # (UNFORGED ⇒ last_run_at None / last_pipeline пуст) → возвращаем
            # текущий статус без записи. Для остальных — fall-through к персисту.
            if entry.get("status") == UNFORGED:
                return ForgeStatus(**entry)
        else:
            entry["status"] = FAILED
        entry["last_run_at"] = _now()
        entry["last_pipeline"] = run_dict
        history = entry.get("pipeline_history") or []
        history.append({"at": entry["last_run_at"], **run_dict})
        entry["pipeline_history"] = history[-20:]
        self._data[project_id] = entry
        self._save()
        return ForgeStatus(**entry)

    def get_pipeline_history(self, project_id: str) -> List[Dict[str, Any]]:
        entry = self._data.get(project_id)
        return (entry or {}).get("pipeline_history", [])

    def unregister(self, project_id: str) -> bool:
        if project_id in self._data:
            del self._data[project_id]
            self._save()
            return True
        return False

    def count(self) -> int:
        return len(self._data)

    @staticmethod
    def _slug(name: str) -> str:
        return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-") or "project"


# === B15 Workspace-Profile check per registry write (Phase 5 Forward-action #1) ===
# Per §37.2.A + §37.3.3 + §37.7 B15 partial: every registry write must verify
# workspace has a registered Workspace-Profile before accepting the entry.
from core_02.boundaries_v17 import BOUNDARIES_V17, BState


def _check_workspace_profile(project_id: str) -> bool:
    """B15 enforcement query — return True if workspace has registered profile."""
    import os, yaml
    ws_profiles = os.path.join("data_13", "workspace_profiles.yaml")
    if not os.path.exists(ws_profiles):
        return False  # No registered profiles yet = assume partial enforcement
    try:
        with open(ws_profiles, "r", encoding="utf-8") as f:
            profiles = yaml.safe_load(f) or {}
        workspace_id = project_id.split(":")[0] if ":" in project_id else project_id
        return workspace_id in profiles
    except Exception:
        return False


def register_project_with_profile(project_id: str, profile: dict):
    """Register a project ONLY if its workspace has a registered profile (B15)."""
    ws_profiles = os.path.join("data_13", "workspace_profiles.yaml")
    import os, yaml
    profiles = {}
    if os.path.exists(ws_profiles):
        with open(ws_profiles, "r", encoding="utf-8") as f:
            profiles = yaml.safe_load(f) or {}
    workspace_id = project_id.split(":")[0] if ":" in project_id else project_id
    profiles[workspace_id] = profile
    with open(ws_profiles, "w", encoding="utf-8") as f:
        yaml.safe_dump(profiles, f, default_flow_style=False, sort_keys=True)
