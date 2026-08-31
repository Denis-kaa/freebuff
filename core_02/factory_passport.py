"""core_02/factory_passport.py — Factory Passport dataclass (машиночитаемый контракт фабрики).

Источник истины: декларативный YAML-манифест ``runtime_05/factories/<factory_id>/factory.yaml``.
Этот модуль — типизированная runtime-модель с валидацией и round-trip YAML serialization.

Pattern mirrors ``ForgePassport`` (core_02/forge_passport.py): dataclass from_yaml +
frozen=True + tuple для списков (иммутабельность + конвенция scenario.py).

Закрывает GAP 09_FUTURE_GAPS C-2 (roadmap): «паспорт factory.yaml, capability-каталог».
До C-2 ``FactoryRegistry`` грузил factory.yaml как сырой dict — без типизированного
паспорта и factory-level capability-каталога.

CAN-16 ADDITIVE: НЕ модифицирует forge_passport / factory_registry / blueprint_v3.
Только новый модуль.

Usage::

    from core_02.factory_passport import FactoryPassport
    fp = FactoryPassport.from_yaml("runtime_05/factories/architecture/factory.yaml")
    fp.validate()  # list[str] violations; empty = valid
    fp.to_dict()   # JSON-convention
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, Union, cast


# ─── Closed vocab (ANTI-6b) — imported lazily to avoid hard dep at import-time ──
_KNOWN_CAPABILITIES_CACHE: Optional[frozenset[str]] = None


def _get_known_capabilities() -> frozenset[str]:
    """Lazy import of KNOWN_CAPABILITIES from blueprint_v3 (avoid hard dep up-front)."""
    global _KNOWN_CAPABILITIES_CACHE
    if _KNOWN_CAPABILITIES_CACHE is None:
        try:
            from core_02.blueprint_v3 import KNOWN_CAPABILITIES
            _KNOWN_CAPABILITIES_CACHE = KNOWN_CAPABILITIES
        except ImportError:
            _KNOWN_CAPABILITIES_CACHE = frozenset()
    return _KNOWN_CAPABILITIES_CACHE


# ─── module-level safety helpers ──────────────────────────────────────────────

_SLUG_RE = re.compile(r"^[a-z)[a-z0-9_]{1,30]$")
_VALID_STATUSES: tuple[str, ...] = ("design", "material", "production")


def _as_tuple(value: Any, *, field_name: str) -> tuple[Any, ...]:
    """Convert list-like → tuple. Raises ValueError if dict/None/non-iterable
    (громкая ошибка per B10/R-127 — НЕ тихая потеря данных)."""
    if value is None or value == "":
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    raise ValueError(
        f"{field_name}: ожидался YAML список; получено {type(value).__name__}. "
        f"НЕ-scalar → НЕ тихая потеря (B10/R-127)."
    )


def _as_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    """Convert dict-like → dict. Raises if scalar (per B10/R-127)."""
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(
        f"{field_name}: ожидался YAML-объект (dict); получено {type(value).__name__}. "
        f"НЕ-scalar-для-объекта → НЕ тихая потеря (B10/R-127)."
    )


@dataclass(frozen=True)
class FactoryPassport:
    """Машиночитаемый паспорт одной Factory (фабрики).

    Frozen contract: after load → immutable. Mutations require re-loading the
    source YAML manifest (``runtime_05/factories/<factory_id>/factory.yaml``).

    Schema (per runtime_05/factories/README.md §1 + C-2):
      - factory_id: lowercase-slug (обязательное);
      - display_name: человекочитаемое имя (обязательное);
      - version: semver-строка (обязательное);
      - status: 'design' | 'material' | 'production' (обязательное);
      - description: свободное описание 1-3 предложения (обязательное);
      - capabilities: factory-level capability-каталог (⊆ KNOWN_CAPABILITIES);
      - metadata: произвольные метаданные (owner, prompt_path, references).
    """

    factory_id: str
    display_name: str
    version: str
    status: str  # 'design' | 'material' | 'production'
    description: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    REQUIRED_FIELDS: tuple[str, ...] = (
        "factory_id", "display_name", "version", "status", "description",
    )

    # ─── YAML load / dump ──────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "FactoryPassport":
        """Load passport from deterministic YAML manifest.

        Raises FileNotFoundError if path missing; ValueError on schema errors
        (per B10/R-127 — громкая ошибка, не silent corruption).
        """
        import yaml  # local import — keeps import-time cheap
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Манифест фабрики не найден: {p}. Паспорт живёт в "
                f"runtime_05/factories/<factory_id>/factory.yaml."
            )
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Манифест фабрики повреждён (невалидный YAML) в {p}: {exc}. "
                f"Восстанови из .bak.* или почини синтаксис."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Манифест {p} не является YAML-словарём (ожидался dict, "
                f"получено {type(data).__name__})."
            )

        return cls._from_dict(data, source=str(p))

    @classmethod
    def _from_dict(cls, data: dict[str, Any], *, source: str = "<dict>") -> "FactoryPassport":
        """Internal: build from already-parsed dict (used by from_yaml + tests)."""

        def err(field: str, why: str) -> ValueError:
            return ValueError(f"{source}: factory_passport::{field} — {why}")

        factory_id = str(data.get("factory_id", "")).strip()
        if not factory_id:
            raise err("factory_id", "обязательное поле, непустое")
        if not _SLUG_RE.match(factory_id):
            raise err(
                "factory_id",
                f"должен соответствовать {_SLUG_RE.pattern} (lowercase, начинается с буквы)",
            )

        display_name = str(data.get("display_name", "")).strip()
        if not display_name:
            raise err("display_name", "обязательное поле, непустое")

        version = str(data.get("version", "")).strip()
        if not version:
            raise err("version", "обязательное поле, непустое")

        status = str(data.get("status", "")).strip()
        if status not in _VALID_STATUSES:
            raise err(
                "status",
                f"должен быть ∈ {_VALID_STATUSES}, получено {status!r}",
            )

        description = str(data.get("description", "")).strip()
        if not description:
            raise err("description", "обязательное поле, непустое")

        return cls(
            factory_id=factory_id,
            display_name=display_name,
            version=version,
            status=status,
            description=description,
            capabilities=_as_tuple(data.get("capabilities", []), field_name="capabilities"),
            metadata=_as_dict(data.get("metadata", {}), field_name="metadata"),
        )

    def to_yaml(self) -> str:
        """Render back to deterministic YAML (round-trippable)."""
        import yaml  # local import — keeps import-time cheap
        out = asdict(self)
        return cast(str, yaml.safe_dump(out, sort_keys=False, allow_unicode=True, default_flow_style=False))

    def to_dict(self) -> dict[str, Any]:
        """JSON-convention dict (lists instead of tuples for JSON-friendliness)."""
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, tuple):
                d[k] = list(v)
        return d

    # ─── validation (B10/R-127 invariants + ANTI-6b vocab guard) ──────────

    def validate(self) -> list[str]:
        """Return list of violation strings (empty = valid).

        Invariants (per runtime_05/factories/README.md §1 + B10/R-127 + ANTI-6b):
        - factory_id lowercase-slug non-empty;
        - display_name non-empty;
        - status ∈ {'design', 'material', 'production'};
        - description non-empty (фабрика без описания — фабрика без смысла);
        - capabilities ⊆ KNOWN_CAPABILITIES (закрытый словарь, ANTI-6b).
        """
        violations: list[str] = []
        if not self.factory_id:
            violations.append("factory_id must be non-empty (B10)")
        elif not _SLUG_RE.match(self.factory_id):
            violations.append(
                f"factory_id {self.factory_id!r} must match {_SLUG_RE.pattern} "
                f"(lowercase + starts-with-letter; B10/R-127)"
            )
        if not self.display_name:
            violations.append("display_name must be non-empty (B10)")
        if self.status not in _VALID_STATUSES:
            violations.append(
                f"status {self.status!r} must be ∈ {_VALID_STATUSES}"
            )
        if not self.description:
            violations.append(
                "description must be non-empty (factory without description = factory without purpose)"
            )
        if self.capabilities:
            known = _get_known_capabilities()
            if known:  # only validate when KNOWN_CAPABILITIES is importable
                unknown = [c for c in self.capabilities if c not in known]
                if unknown:
                    violations.append(
                        f"capabilities содержат unknown tokens {unknown} (закрытый "
                        f"словарь KNOWN_CAPABILITIES требует ANTI-6b compliance; "
                        f"silently demoting routing запрещено)."
                    )
        return violations

    # ─── equality / hashing (frozen=True gives both for free) ──────────────
    def __post_init__(self) -> None:
        if self.factory_id and not _SLUG_RE.match(self.factory_id):
            raise ValueError(
                f"factory_id {self.factory_id!r} must match {_SLUG_RE.pattern}"
            )


__all__ = [
    "FactoryPassport",
    "REQUIRED_FIELDS",  # backward-compat re-export
]


# Module-level re-export for `from core_02.factory_passport import REQUIRED_FIELDS`.
REQUIRED_FIELDS = FactoryPassport.REQUIRED_FIELDS
