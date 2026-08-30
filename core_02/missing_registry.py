# core_02/missing_registry.py — Missing Registry (register-first принцип)
# Workspace OS / Factory-Forge (карта v1.1 §20 — Missing Capabilities)

"""Реестр недостающих элементов (register-first).

Принцип (поправка пользователя, 2026-08-11): недостающий элемент — НЕ
«несуществующий токен», а способность/компонент, который нужно **построить**.
Любой обнаруженный недостающий элемент (capability / tool / engine / forge /
role / модуль) СНАЧАЛА фиксируется в этом реестре, потом пишется промт на
реализацию, потом — реализация. Это правило теперь в AGENTS.md §5 (register-first).

Хранение: YAML в data_13/missing_registry.yaml (по образцу ForgeRegistry:
dataclass MissingItem + validate_schema с B10/R-127 машинными инвариантами).

    reg = MissingRegistry()                       # data_13/missing_registry.yaml
    reg.register_missing("research_web", kind="tool", factory="research",
                         prompt_path="pompts_11/075_04_research_web_capability.md")
    reg.get("research_web")                       # -> MissingItem
    reg.mark_implemented("research_web")          # -> status: implemented
    reg.list_by_status("prompt_written")          # -> [MissingItem, ...]
    reg.validate_schema()                         # -> list[str] ([] = валиден)

Статусы: registered → prompt_written → implemented (фиксированный lifecycle).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

# ─── lifecycle (register-first → promt → implemented) ───────────────────────
REGISTERED = "registered"        # обнаружен и зафиксирован
DESIGN_READY = "design_ready"    # дизайн-документ готов (паспорт/дизайн-doc)
PROMPT_WRITTEN = "prompt_written"  # промт на реализацию написан
IMPLEMENTED = "implemented"      # реализован (код + тесты + словарь)

STATUSES = (REGISTERED, DESIGN_READY, PROMPT_WRITTEN, IMPLEMENTED)

# Ранг lifecycle для forward-only перехода (lifecycle не откатывается).
_STATUS_RANK: Dict[str, int] = {
    REGISTERED: 0,
    DESIGN_READY: 1,
    PROMPT_WRITTEN: 2,
    IMPLEMENTED: 3,
}


def status_rank(status: str) -> int:
    """Публичный доступ к рангу lifecycle (registered→design_ready→prompt_written→implemented).

    Неизвестный статус → 0 (как registered). Используется кросс-модульно
    (consistency_check: сверка §20 ↔ MissingRegistry) — без приватного `_STATUS_RANK`.
    """
    return _STATUS_RANK.get(status, 0)

# Допустимые kinds элементов (register-first применяется к ЛЮБЫМ элементам).
# "data" — каноничные data-артефакты платформы (YAML-хранилища, напр. lisa_calibration).
KINDS = ("capability", "tool", "engine", "forge", "role", "factory", "module", "registry", "system", "data")

# B10/R-127: обязательные поля записи (machine-checkable).
REQUIRED_FIELDS = ("item_id", "kind", "status")

# Каноническое место реестра.
DEFAULT_PATH = "data_13/missing_registry.yaml"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MissingItem:
    """Одна запись о недостающем элементе (типизированная, B10/R-127)."""

    item_id: str                 # токен: "research_web", "lisa_estimator", ...
    kind: str                    # capability / tool / engine / forge / role / ...
    status: str = REGISTERED     # registered → prompt_written → implemented
    factory: str = ""            # Research / Code / Architecture / ... ("" = вне Factory)
    description: str = ""        # что за элемент и где нужен
    prompt_path: str = ""        # pompts_11/promtNN.md — primary/implementation промт
    related_prompts: List[str] = field(default_factory=list)  # multi-prompt (promt 087):
                                 # forensics/design/supporting промты; prompt_path остаётся primary
    implementation: str = ""     # scripts_01/*.py / core_02/*.py (после реализации)
    registered_at: str = ""
    updated_at: str = ""
    backfill: bool = False       # True = зарегистрирован задним числом (минуя lifecycle)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "status": self.status,
            "factory": self.factory,
            "description": self.description,
            "prompt_path": self.prompt_path,
            "related_prompts": list(self.related_prompts),
            "implementation": self.implementation,
            "registered_at": self.registered_at,
            "updated_at": self.updated_at,
            "backfill": bool(self.backfill),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MissingItem":
        """Построить из YAML-записи, игнорируя неизвестные/лишние ключи.

        Устойчивость к ручной правке YAML (лишний ключ не роняет реестр) —
        паттерн ScenarioManifest.from_yaml.
        """
        known = {
            "item_id", "kind", "status", "factory", "description",
            "prompt_path", "related_prompts", "implementation",
            "registered_at", "updated_at", "backfill",
        }
        return cls(**{k: v for k, v in data.items() if k in known})


class MissingRegistry:
    """Реестр недостающих элементов (L-реестр, по образцу ForgeRegistry)."""

    def __init__(self, path: str | Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Any]] = self._load()
        self._schema_violations: List[str] = self.validate_schema()

    # ── persistence ─────────────────────────────────────────────────────
    def _load(self) -> Dict[str, Dict[str, Any]]:
        """Загрузить реестр. При ошибке чтения/парсинга — {] + фиксируем факт."""
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
            self._load_error = str(exc)
            return {}

    def _save(self) -> None:
        payload = {k: v for k, v in self._data.items()}
        if yaml is not None:
            self.path.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        else:  # pragma: no cover
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        self._load_error = None

    # ── B10 schema validation (R-127) ────────────────────────────────────
    def validate_schema(self) -> List[str]:
        """Машинные инварианты реестра (B10/R-127). Возвращает список нарушений.

        - обязательные поля: item_id, kind, status;
        - kind ∈ KINDS;
        - status ∈ STATUSES (registered → design_ready → prompt_written → implemented);
        - status == implemented ⇒ implementation непустой;
        - status == prompt_written ⇒ prompt_path непустой;
        - нечитаемый файл — нарушение integrity.
        """
        violations: List[str] = []
        load_error = getattr(self, "_load_error", None)
        if load_error:
            violations.append(f"registry: unreadable YAML ({load_error})")
        for item_id, entry in self._data.items():
            for f in REQUIRED_FIELDS:
                if f not in entry:
                    violations.append(f"{item_id}: missing required field {f!r}")
            kind = entry.get("kind")
            if kind is not None and kind not in KINDS:
                violations.append(f"{item_id}: invalid kind {kind!r} (allowed: {KINDS})")
            status = entry.get("status")
            if status is not None and status not in STATUSES:
                violations.append(f"{item_id}: invalid status {status!r} (allowed: {STATUSES})")
            if status == IMPLEMENTED and not entry.get("implementation"):
                violations.append(
                    f"{item_id}: status 'implemented' but implementation empty "
                    "(implemented ⇒ есть код/файл реализации)"
                )
            if status == PROMPT_WRITTEN and not entry.get("prompt_path"):
                violations.append(
                    f"{item_id}: status 'prompt_written' but prompt_path empty "
                    "(prompt_written ⇒ промт на реализацию существует)"
                )
            related = entry.get("related_prompts")
            if related is not None:
                if not isinstance(related, list):
                    violations.append(
                        f"{item_id}: related_prompts must be a list "
                        f"(got {type(related).__name__})"
                    )
                else:
                    for rp in related:
                        if not isinstance(rp, str) or not rp.strip():
                            violations.append(
                                f"{item_id}: related_prompts entries must be non-empty strings"
                            )
            backfill = entry.get("backfill")
            if backfill is not None and not isinstance(backfill, bool):
                violations.append(
                    f"{item_id}: backfill must be a bool "
                    f"(got {type(backfill).__name__})"
                )
            if backfill is True and status != IMPLEMENTED:
                violations.append(
                    f"{item_id}: backfill=true but status != 'implemented' "
                    "(backfill = регистрация задним числом уже реализованного элемента)"
                )
        return violations

    @property
    def schema_violations(self) -> List[str]:
        return list(self._schema_violations)

    # ── API (register-first) ─────────────────────────────────────────────
    def register_missing(
        self,
        item_id: str,
        kind: str,
        factory: str = "",
        description: str = "",
        prompt_path: str = "",
        related_prompts: Optional[List[str]] = None,
        implementation: str = "",
        status: str = REGISTERED,
        backfill: bool = False,
    ) -> str:
        """Зафиксировать недостающий элемент (register-first). Возвращает item_id.

        Если элемент уже зарегистрирован — обновляет поля (идемпотентно),
        НЕ сбрасывает lifecycle назад (implemented не деградирует).
        """
        item_id = item_id.strip()
        if not item_id:
            raise ValueError("item_id не может быть пустым")
        if kind not in KINDS:
            raise ValueError(f"kind {kind!r} не из списка {KINDS}")
        if status not in STATUSES:
            raise ValueError(f"status {status!r} не из списка {STATUSES}")
        if backfill and status != IMPLEMENTED:
            raise ValueError(
                f"backfill=True requires status='implemented' (got {status!r}) "
                "— backfill = регистрация задним числом уже реализованного элемента"
            )

        now = _now()
        existing = self._data.get(item_id)
        if existing is not None:
            # Lifecycle не откатывается: registered→design_ready→prompt_written→implemented.
            existing_status = existing.get("status")
            if existing_status in _STATUS_RANK and _STATUS_RANK.get(status, 0) < _STATUS_RANK[existing_status]:
                status = existing_status
            existing.update({
                "kind": kind,
                "factory": factory,
                "description": description or existing.get("description", ""),
                "prompt_path": prompt_path or existing.get("prompt_path", ""),
                "related_prompts": related_prompts if related_prompts is not None
                                   else existing.get("related_prompts", []),
                "implementation": implementation or existing.get("implementation", ""),
                "status": status,
                "updated_at": now,
                # backfill — факт регистрации, не откатывается (как lifecycle).
                "backfill": bool(backfill or existing.get("backfill", False)),
            ])
            self._save()
            return item_id

        entry = {
            "item_id": item_id,
            "kind": kind,
            "status": status,
            "factory": factory,
            "description": description,
            "prompt_path": prompt_path,
            "related_prompts": list(related_prompts or []),
            "implementation": implementation,
            "registered_at": now,
            "updated_at": now,
            "backfill": bool(backfill),
        }
        self._data[item_id] = entry
        self._save()
        return item_id

    def get(self, item_id: str) -> Optional[MissingItem]:
        entry = self._data.get(item_id)
        if entry is None:
            return None
        return MissingItem.from_dict(entry)

    def has(self, item_id: str) -> bool:
        return item_id in self._data

    def list_all(self) -> List[MissingItem]:
        out = [MissingItem.from_dict(e) for e in self._data.values()]
        out.sort(key=lambda i: i.item_id)
        return out

    def list_by_status(self, status_filter: Optional[str] = None) -> List[MissingItem]:
        out = [MissingItem.from_dict(e) for e in self._data.values()
               if status_filter is None or e.get("status") == status_filter]
        out.sort(key=lambda i: i.item_id)
        return out

    def list_by_factory(self, factory: str) -> List[MissingItem]:
        out = [MissingItem.from_dict(e) for e in self._data.values()
               if e.get("factory") == factory]
        out.sort(key=lambda i: i.item_id)
        return out

    def mark_prompt_written(self, item_id: str, prompt_path: str) -> MissingItem:
        """Шаг 2 register-first: промт на реализацию написан.

        Lifecycle не откатывается: если элемент уже implemented — не деградирует.
        """
        if item_id not in self._data:
            raise KeyError(f"Элемент {item_id} не зарегистрирован (register-first!)")
        entry = self._data[item_id]
        if _STATUS_RANK[PROMPT_WRITTEN] > _STATUS_RANK.get(entry.get("status", ""), 0):
            entry["status"] = PROMPT_WRITTEN
        entry["prompt_path"] = prompt_path
        entry["updated_at"] = _now()
        self._save()
        return MissingItem.from_dict(entry)

    def add_related_prompt(self, item_id: str, prompt_path: str) -> MissingItem:
        """Добавить related-промт (forensics/design/supporting) к записи (promt 087).

        Дедупликация: повторный путь не дублируется. Lifecycle не меняется.
        """
        if item_id not in self._data:
            raise KeyError(f"Элемент {item_id} не зарегистрирован (register-first!)")
        entry = self._data[item_id]
        related = list(entry.get("related_prompts") or [])
        if prompt_path and prompt_path not in related:
            related.append(prompt_path)
        entry["related_prompts"] = related
        entry["updated_at"] = _now()
        self._save()
        return MissingItem.from_dict(entry)

    def mark_implemented(
        self,
        item_id: str,
        implementation: str,
        prompt_path: str = "",
        related_prompts: Optional[List[str]] = None,
    ) -> MissingItem:
        """Шаг 3 register-first: элемент реализован (код + тесты)."""
        if item_id not in self._data:
            raise KeyError(f"Элемент {item_id} не зарегистрирован (register-first!)")
        entry = self._data[item_id]
        entry["status"] = IMPLEMENTED
        entry["implementation"] = implementation
        if prompt_path:
            entry["prompt_path"] = prompt_path
        if related_prompts is not None:
            entry["related_prompts"] = list(related_prompts)
        entry["updated_at"] = _now()
        self._save()
        return MissingItem.from_dict(entry)

    def count(self) -> int:
        return len(self._data)

    def unregister(self, item_id: str) -> bool:
        if item_id in self._data:
            del self._data[item_id]
            self._save()
            return True
        return False


# ═══════════════════════════════════════════════════════════════════
# CLI (python -m core_02.missing_registry)
# ═══════════════════════════════════════════════════════════════════


def _print_item(item: MissingItem) -> None:
    related = item.related_prompts or []
    print(f"{item.item_id:<24} {item.status:<15} {item.kind:<10} "
          f"factory={item.factory or '-'} prompt={item.prompt_path or '-'} "
          f"impl={item.implementation or '-'} related={len(related)} "
          f"backfill={item.backfill}")
    if item.description:
        print(f"{'':<24} {item.description}")
    for rp in related:
        print(f"{'':<24} related: {rp}")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI для MissingRegistry (register-first).

    Usage:
        python -m core_02.missing_registry list [--status STATUS] [--factory FACTORY]
        python -m core_02.missing_registry list --json
        python -m core_02.missing_registry seed
        python -m core_02.missing_registry register ITEM_ID --kind tool [--factory F] \
            [--description DESC] [--prompt PATH] [--status STATUS] [--backfill]
        python -m core_02.missing_registry mark-prompt-written ITEM_ID --prompt PATH
        python -m core_02.missing_registry mark-implemented ITEM_ID --implementation PATH \
            [--prompt PATH] [--related-prompt PATH ...]
        python -m core_02.missing_registry add-related-prompt ITEM_ID --prompt PATH \
            [--prompt PATH ...]
        python -m core_02.missing_registry check   # validate_schema → exit 0/1
    """
    import argparse

    parser = argparse.ArgumentParser(prog="missing_registry", description=__doc__)
    parser.add_argument("--path", default=DEFAULT_PATH,
                        help=f"путь к YAML-реестру (default {DEFAULT_PATH})")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="показать зарегистрированные элементы")
    p_list.add_argument("--status", choices=STATUSES, default=None, help="фильтр по статусу")
    p_list.add_argument("--factory", default=None, help="фильтр по factory")
    p_list.add_argument("--json", action="store_true", help="вывод JSON")

    # seed
    sub.add_parser("seed", help="зарегистрировать канонические записи §20 (идемпотентно)")

    # register
    p_reg = sub.add_parser("register", help="зафиксировать недостающий элемент (register-first)")
    p_reg.add_argument("item_id")
    p_reg.add_argument("--kind", required=True, choices=KINDS)
    p_reg.add_argument("--factory", default="")
    p_reg.add_argument("--description", default="")
    p_reg.add_argument("--prompt", default="", dest="prompt_path")
    p_reg.add_argument("--implementation", default="")
    p_reg.add_argument("--status", default=REGISTERED, choices=STATUSES)
    p_reg.add_argument("--backfill", action="store_true",
                       help="зарегистрировать задним числом (уже реализованный элемент, минуя lifecycle)")

    # mark-prompt-written
    p_pw = sub.add_parser("mark-prompt-written", help="шаг 2 register-first: промт написан")
    p_pw.add_argument("item_id")
    p_pw.add_argument("--prompt", required=True, dest="prompt_path")

    # mark-implemented
    p_impl = sub.add_parser("mark-implemented", help="шаг 3 register-first: элемент реализован")
    p_impl.add_argument("item_id")
    p_impl.add_argument("--implementation", required=True)
    p_impl.add_argument("--prompt", default="", dest="prompt_path")
    p_impl.add_argument("--related-prompt", action="append", default=None,
                        dest="related_prompts", help="related/forensics промт (повторяемый)")

    # add-related-prompt
    p_arp = sub.add_parser("add-related-prompt", help="добавить related-промт к записи (promt 087)")
    p_arp.add_argument("item_id")
    p_arp.add_argument("--prompt", action="append", required=True,
                       dest="related_prompts", help="related/forensics промт (повторяемый)")

    # check
    sub.add_parser("check", help="проверить B10/R-127 инварианты реестра (exit 0 = валиден)")

    args = parser.parse_args(argv)

    try:
        reg = MissingRegistry(args.path)
    except Exception as exc:  # noqa: BLE001 — CLI fail-safe
        print(f"error: не удалось открыть реестр {args.path}: {exc}", file=sys.stderr)
        return 2

    cmd = args.command
    if cmd == "list":
        items = reg.list_by_factory(args.factory) if args.factory else reg.list_all()
        if args.status:
            items = [i for i in items if i.status == args.status]
        if args.json:
            print(json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2))
            return 0
        if not items:
            print("(пусто)")
            return 0
        for item in items:
            _print_item(item)
        return 0

    if cmd == "seed":
        added = seed_defaults(reg)
        print(f"seed: добавлено {added}, всего {reg.count()}")
        return 0

    if cmd == "register":
        try:
            reg.register_missing(
                args.item_id,
                kind=args.kind,
                factory=args.factory,
                description=args.description,
                prompt_path=args.prompt_path,
                implementation=args.implementation,
                status=args.status,
                backfill=args.backfill,
            )
        except ValueError as exc:
            # Clean message + exit 1 (как KeyError в mark-* ветках), не traceback.
            print(f"error: {exc}", file=sys.stderr)
            return 1
        item_reg = reg.get(args.item_id)
        if item_reg is None:
            print("error: элемент не зарегистрирован", file=sys.stderr)
            return 1
        _print_item(item_reg)
        return 0

    if cmd == "mark-prompt-written":
        try:
            item = reg.mark_prompt_written(args.item_id, args.prompt_path)
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        _print_item(item)
        return 0

    if cmd == "mark-implemented":
        try:
            item = reg.mark_implemented(
                args.item_id, args.implementation,
                prompt_path=args.prompt_path,
                related_prompts=args.related_prompts,
            )
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        _print_item(item)
        return 0

    if cmd == "add-related-prompt":
        try:
            for rp in args.related_prompts:
                reg.add_related_prompt(args.item_id, rp)
            item_arp = reg.get(args.item_id)
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if item_arp is None:
            print("error: элемент не зарегистрирован", file=sys.stderr)
            return 1
        _print_item(item_arp)
        return 0

    if cmd == "check":
        violations = reg.validate_schema()
        if violations:
            for v in violations:
                print(f"violation: {v}")
            return 1
        print(f"ok: реестр {args.path} валиден ({reg.count()} записей)")
        return 0

    # unreachable — subparsers имеют required=True
    parser.error(f"unknown command {cmd!r}")
    return 2  # pragma: no cover


# ─── seed: записи из §20 карты v1.1 (регистрируются при первом вызове) ──────

_SEED: List[Dict[str, Any]] = [
    {
        "item_id": "factory_registry",
        "kind": "registry",
        "factory": "",
        "status": DESIGN_READY,
        "description": "Реестр фабрик и кузен, статусы, паспорта (Missing Capability #1) — дизайн готов",
        "prompt_path": "docs_10/engineering-memory/FORGE_PASSPORT_CODE_REPRESENTATION_V1.md",
        "implementation": "",
    },
    {
        "item_id": "scenario_engine",
        "kind": "system",
        "factory": "",
        "status": DESIGN_READY,
        "description": "Исполнение сценариев-композиторов поверх Factory (Missing Capability #2) — дизайн готов",
        "prompt_path": "docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md",
        "implementation": "",
    },
    {
        "item_id": "decision_registry",
        "kind": "registry",
        "factory": "decision",
        "status": REGISTERED,
        "description": "ADR-реестр как структура данных (Missing Capability #3)",
        "prompt_path": "",
        "implementation": "",
    },
    {
        "item_id": "conformance_checker",
        "kind": "tool",
        "factory": "governance",
        "status": REGISTERED,
        "description": "Машиночитаемый Conformance checker (Missing Capability #4)",
        "prompt_path": "",
        "implementation": "",
    },
    {
        "item_id": "model_diagram_autogen",
        "kind": "tool",
        "factory": "modeling",
        "status": REGISTERED,
        "description": "Автогенерация моделей/диаграмм (Missing Capability #5)",
        "prompt_path": "",
        "implementation": "",
    },
    {
        "item_id": "research_web",
        "kind": "tool",
        "factory": "research",
        "status": IMPLEMENTED,
        "description": "Web Research — веб-исследование (Missing Capability #6)",
        "prompt_path": "pompts_11/075_04_research_web_capability.md",
        "implementation": "scripts_01/research_web.py",
    },
    {
        "item_id": "lisa_estimator",
        "kind": "tool",
        "factory": "research",
        "status": IMPLEMENTED,
        "description": "Estimation — оценка сложности LISA-3 (Missing Capability #7)",
        "prompt_path": "pompts_11/076_13_lisa_estimator_capability.md",
        "implementation": "scripts_01/lisa_estimator.py",
    },
]


def seed_defaults(registry: MissingRegistry) -> int:
    """Зарегистрировать канонические записи из §20 карты v1.1 (идемпотентно).

    Возвращает количество вновь добавленных записей. Используется при первом
    запуске / миграции; повторные вызовы ничего не ломают (lifecycle не
    откатывается — implemented/prompt_written сохраняются).
    """
    added = 0
    for item in _SEED:
        if not registry.has(item["item_id"]):
            registry.register_missing(**item)
            added += 1
    return added


__all__ = [
    "MissingItem",
    "MissingRegistry",
    "REGISTERED",
    "DESIGN_READY",
    "PROMPT_WRITTEN",
    "IMPLEMENTED",
    "KINDS",
    "STATUSES",
    "REQUIRED_FIELDS",
    "DEFAULT_PATH",
    "seed_defaults",
    "status_rank",
]


if __name__ == "__main__":
    sys.exit(main())
