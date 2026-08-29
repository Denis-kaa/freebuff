"""workspace_registry.py — Phase 5.4 prototype.

Workspace \u2194 Project mapping with privacy isolation guard.

Adds two additive tables to `data_13/context.db`:
  - workspaces(slug PK, name, owner_chat_id, created_at, status, description)
  - workspace_projects(path PK, workspace_slug FK, name, created_at, status)

Privacy invariant (enforced at schema level):
  - workspace_projects.path is PRIMARY KEY \u2192 a path can belong to AT MOST ONE workspace.
  - Функции `add_project`, `assert_path_privacy`, `find_workspace_for_project`
    ловят попытки пересечь границу workspace и поднимают `PrivacyViolationError`
    (CAN-14 fail-loud).

Default seeding:
  - Работа (slug "rabota"): projects_17/interior_planner + tg_terminal_messenger
  - Учёба  (slug "ucheba"): projects_17/buffy-playground_19
  - Хобби  (slug "hobbi"): projects_17/freebuff_flutter_app + diet_platform
  Idempotent: missing paths in projects_17/ are skipped с logger.warning,
  не падает (CON-21 anti-fragility; добавление проекта через `add_project`
  никогда не должно блокироваться структурой registry).

Reuse (CON-19 single-source-of-truth):
  - DB path: `data_13/context.db` (тот же что у `scripts_01/scan_projects.py`).
  - WAL pragma (mirror `scan_projects.py`) — для параллельных операций с существующими
    проектами через scan + здесь через add.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field, field
***REMOVED***
from typing import Any

logger = logging.getLogger(__name__)

# ── custom exception (CAN-14: fail-loud на privacy-violation) ──


class PrivacyViolationError(Exception):
    """Raised when a path accessed by/added to a workspace it does not belong to."""

    def __init__(self, path: str, expected_slug: str, actual_slug: str | None) -> None:
        self.path = path
        self.expected_slug = expected_slug
        self.actual_slug = actual_slug
        msg = (
            f"Privacy violation: path '{path***REMOVED***' expected to be in workspace "
            f"'{expected_slug***REMOVED***' but"
        )
        if actual_slug is None:
            msg += " is NOT registered to any workspace."
        else:
            msg += f" is registered to workspace '{actual_slug***REMOVED***'."
        super().__init__(msg)


# ── dataclasses ──


@dataclass
class Workspace:
    name: str
    slug: str
    project_paths: list[str***REMOVED*** = field(default_factory=list)
    created_at: float = 0.0
    status: str = "active"
    description: str = ""
    owner_chat_id: int = 0  # 0 == неизвестно/общий prototype; bind chat_id в follow-up.


@dataclass
class SyncReport:
    """Structured return for sync_from_config() (ADR-017 §2).

    One-way YAML→SQLite sync report: what was created, skipped, conflicted.
    Idempotent: повторный sync → created_workspaces=0, created_projects=0,
    skipped = все существующие, conflicts = прежние.

    Fields:
      - created_workspaces: NEW workspace slugs inserted.
      - created_projects: NEW project paths bound.
      - skipped_workspaces: workspace slugs already present (idempotent).
      - skipped_projects: project paths already bound to same workspace.
      - conflicts: (path, current_slug, expected_slug) tuples — privacy conflict.
    """

    created_workspaces: list[str***REMOVED*** = field(default_factory=list)
    created_projects: list[str***REMOVED*** = field(default_factory=list)
    skipped_workspaces: list[str***REMOVED*** = field(default_factory=list)
    skipped_projects: list[str***REMOVED*** = field(default_factory=list)
    conflicts: list[tuple[str, str, str***REMOVED******REMOVED*** = field(default_factory=list)


@dataclass
class SeedResult:
    """Structured return for seed_defaults() (CAN-14 fail-loud, RTX-style).

    Caller knows BOTH how many NEW workspaces were seeded AND which
    project paths were missing on filesystem (RTX-default warn-and-skip).
    Replaces the prior opaque `int` return so operators can build
    "3 created, 2 missing" UI without re-running discovery.

    Fields:
      - created: number of NEW workspaces seeded (idempotent re-runs = 0).
      - missing: absolute project_path strings absent on FS at seed time.
    """

    created: int = 0
    missing: list[str***REMOVED*** = field(default_factory=list)


@dataclass
class Project:
    name: str
    path: str
    workspace_slug: str
    created_at: float = 0.0
    status: str = "active"


# ── Cyrillic ⇄ Latin slug helper (CON-21 inline — единичный map в 1 месте) ──

_SLUG_TRANSLIT = {
    "\u0410": "A", "\u0411": "B", "\u0412": "V", "\u0413": "G", "\u0414": "D",
    "\u0415": "E", "\u0416": "Zh", "\u0417": "Z", "\u0418": "I", "\u0419": "Y",
    "\u041a": "K", "\u041b": "L", "\u041c": "M", "\u041d": "N", "\u041e": "O",
    "\u041f": "P", "\u0420": "R", "\u0421": "S", "\u0422": "T", "\u0423": "U",
    "\u0424": "F", "\u0425": "H", "\u0426": "Ts", "\u0427": "Ch", "\u0428": "Sh",
    "\u0429": "Sch", "\u042a": "", "\u042b": "Y", "\u042c": "", "\u042d": "E",
    "\u042e": "Yu", "\u042f": "Ya",
    "\u0430": "a", "\u0431": "b", "\u0432": "v", "\u0433": "g", "\u0434": "d",
    "\u0435": "e", "\u0436": "zh", "\u0437": "z", "\u0438": "i", "\u0439": "y",
    "\u043a": "k", "\u043b": "l", "\u043c": "m", "\u043d": "n", "\u043e": "o",
    "\u043f": "p", "\u0440": "r", "\u0441": "s", "\u0442": "t", "\u0443": "u",
    "\u0444": "f", "\u0445": "h", "\u0446": "ts", "\u0447": "ch", "\u0448": "sh",
    "\u0449": "sch", "\u044a": "", "\u044b": "y", "\u044c": "", "\u044d": "e",
    "\u044e": "yu", "\u044f": "ya",
    "\u0451": "yo", "\u0401": "Yo",
    " ": "_", "-": "_", ".": "_", "/": "_", "\\": "_",
***REMOVED***


def _slugify_name(name: str) -> str:
    """Cyrillic → Latin slug: 'Работа' → 'rabota'. Idempotent для одного input.

    Bugfix: финальный `.lower()` чтобы нормализовать к lowercase (Transliteration map
    содержит U/U+ для заглавных кириллических букв; без .lower() slug был бы
    'Uchyoba' а не 'uchyoba' — ломал сравнение в PrivacyViolationError).
    """
    out = [***REMOVED***
    for ch in name:
        out.append(_SLUG_TRANSLIT.get(ch, ch.lower() if ch.isalpha() else ch))
    slug = "".join(out).strip("_").lower()
    # collapse multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "workspace"


# ── three default implicit workspaces (Phase 5.4 user-spec) ──

DEFAULT_WORKSPACES: list[tuple[str, list[str***REMOVED***, str***REMOVED******REMOVED*** = [
    (
        "Работа",
        ["projects_17/interior_planner", "projects_17/tg_terminal_messenger"***REMOVED***,
        "Рабочие проекты: interior_planner + tg_terminal_messenger",
    ),
    (
        "Учёба",
        ["projects_17/buffy-playground_19"***REMOVED***,
        "Учебные проекты: buffy-playground_19 (Vite/React playground)",
    ),
    (
        "Хобби",
        ["projects_17/freebuff_flutter_app", "projects_17/diet_platform"***REMOVED***,
        "Хобби-проекты: Flutter app + diet platform",
    ),
***REMOVED***


# ── WorkspaceRegistry ──


class WorkspaceRegistry:
    """Phase 5.4 prototype: workspace(project)+privacy guard на data_13/context.db.

    Public API:
        seed_defaults() → int
        create_workspace(name, project_paths) → Workspace
        add_project(workspace_slug, project_path) → None
        list_workspaces() → list[Workspace***REMOVED***
        list_projects(workspace_slug) → list[str***REMOVED***
        find_workspace_for_project(project_path) → Workspace | None
        assert_path_privacy(project_path, expected_workspace_slug) → None
    """

    DEFAULT_DB_PATH = Path("data_13") / "context.db"
    MAX_NAME_LEN = 64  # CON-19 single-source-of-truth для длины имён

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else self.DEFAULT_DB_PATH
        self._init_db()

    # ── DB plumbing ──

    def _init_db(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.exception("Cannot create db parent dir %s: %s", self.db_path.parent, exc)
            raise
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    slug          TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    owner_chat_id INTEGER NOT NULL DEFAULT 0,
                    created_at    REAL NOT NULL,
                    status        TEXT DEFAULT 'active',
                    description   TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS workspace_projects (
                    path           TEXT PRIMARY KEY,
                    workspace_slug TEXT NOT NULL,
                    name           TEXT NOT NULL,
                    created_at     REAL NOT NULL,
                    status         TEXT DEFAULT 'active',
                    FOREIGN KEY(workspace_slug) REFERENCES workspaces(slug)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_wp_workspace
                    ON workspace_projects(workspace_slug);
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    # ── seeding ──

    def seed_defaults(self, workspace_root: Path | None = None) -> SeedResult:
        """Idempotent seed of the 3 default implicit workspaces (CAN-14 fail-loud).

        Args:
            workspace_root: Optional anchor для относительных pathов в
                DEFAULT_WORKSPACES. Defaults to freebuff project root
                (parent of this module) — production path. Tests should
                pass `tmp_path` to isolate.

        Returns SeedResult with:
          - .created: count of NEW workspaces seeded (0 if all already present).
          - .missing: list of absolute path strings absent on FS (RTX-default
            warn-and-skip, NOT raised). Caller can build operator-visible UI.

        Missing paths in projects_17/ are skipped with logger.warning
        (CON-21 anti-fragility: registry не должен падать из-за файловой
        рассинхронизации). For strict fail-loud, callers can use
        add_project(strict=True) explicitly.
        """
        if workspace_root is None:
            # workspace_registry.py lives at <freebuff>/core_02/workspace_registry.py
            # → .parent = core_02/, .parent.parent = <freebuff>/ (correct anchor)
            workspace_root = Path(__file__).resolve().parent.parent
        seeded = 0
        missing_paths: list[str***REMOVED*** = [***REMOVED***
        now = time.time()
        with self._connect() as conn:
            for name, paths, desc in DEFAULT_WORKSPACES:
                slug = _slugify_name(name)
                existing = conn.execute(
                    "SELECT slug FROM workspaces WHERE slug = ?", (slug,)
                ).fetchone()
                if not existing:
                    # Insert only if slug doesn't exist yet. Falls through to fs-scan loop
                    # so idempotent re-runs STILL populate missing_paths (CAN-14 fail-loud).
                    try:
                        conn.execute(
                            """
                            INSERT INTO workspaces
                                (slug, name, owner_chat_id, created_at, status, description)
                            VALUES (?, ?, ?, ?, 'active', ?)
                            """,
                            (slug, name, 0, now, desc),
                        )
                        seeded += 1
                    except sqlite3.IntegrityError as exc:
                        # race-condition guard: another connection won the INSERT.
                        # Warn (don't raise) — caller (TG-bот batch / MCP) does NOT crash
                        # on concurrent seed, but operator gets observability (fix #2 polish).
                        # Per test_seed_defaults_integrity_error_logs_warning.
                        logger.warning(
                            "WorkspaceRegistry.seed_defaults: workspace slug=%r"
                            " already inserted by concurrent connection; race-loser"
                            " skip (no data loss): %s",
                            slug,
                            exc,
                        )
                registered_paths: list[str***REMOVED*** = [***REMOVED***
                for p in paths:
                    full_path = (workspace_root / p).resolve()
                    if not full_path.exists():
                        logger.warning(
                            "WorkspaceRegistry.seed_defaults: path %s"
                            " not found on filesystem; skipping",
                            full_path,
                        )
                        missing_paths.append(str(full_path))
                        continue
                    # Use resolved absolute path for the registry (canonical).
                    abs_path = str(full_path)
                    try:
                        conn.execute(
                            """
                            INSERT INTO workspace_projects
                                (path, workspace_slug, name, created_at, status)
                            VALUES (?, ?, ?, ?, 'active')
                            """,
                            (abs_path, slug, full_path.name, now),
                        )
                        registered_paths.append(abs_path)
                    except sqlite3.IntegrityError as exc:
                        logger.warning(
                            "WorkspaceRegistry.seed_defaults: path %s уже"
                            " привязан к другому workspace (%s); skip",
                            abs_path,
                            exc,
                        )
                logger.info(
                    "WorkspaceRegistry.seed_defaults: workspace %r (%s)"
                    " seeded with %d project(s)",
                    name,
                    slug,
                    len(registered_paths),
                )
            conn.commit()
        return SeedResult(created=seeded, missing=missing_paths)

    # ── ADR-017: YAML → SQLite one-way sync contract ──

    def sync_from_config(self, workspace_root: Path | None = None) -> "SyncReport":
        """YAML (workspace.yaml/project.yaml) → SQLite sync (ADR-017 §2).

        One-way, idempotent, additive:
          - workspace не в SQLite → INSERT (slug = _slugify_name(name)).
          - workspace уже есть → skip (owner/status не перезаписываются).
          - project path не привязан → INSERT.
          - path привязан к ДРУГОЙ workspace → warn + skip (privacy invariant).
          - УДАЛЕНИЙ нет: отсутствие проекта в YAML НЕ удаляет строку.

        Returns SyncReport with created/skipped/conflicts.
        """
        if workspace_root is None:
            workspace_root = Path(__file__).resolve().parent.parent
        root = Path(workspace_root)
        import yaml as _yaml

        cfg_path = root / "workspace.yaml"
        cfg: dict = {***REMOVED***
        if cfg_path.exists():
            try:
                cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {***REMOVED***
            except Exception:
                cfg = {***REMOVED***

        report = SyncReport()
        now = time.time()
        ws_name = cfg.get("name") or root.name
        ws_slug = _slugify_name(ws_name)

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT slug FROM workspaces WHERE slug = ?", (ws_slug,)
            ).fetchone()
            if existing:
                report.skipped_workspaces.append(ws_slug)
            else:
                try:
                    conn.execute(
                        "INSERT INTO workspaces (slug, name, owner_chat_id, created_at, status, description)"
                        " VALUES (?, ?, 0, ?, 'active', ?)",
                        (ws_slug, ws_name, now, cfg.get("description", "")),
                    )
                    report.created_workspaces.append(ws_slug)
                except sqlite3.IntegrityError as exc:
                    logger.warning("sync_from_config: workspace %s already inserted (race): %s", ws_slug, exc)
                    report.skipped_workspaces.append(ws_slug)

            configured = [str(p) for p in cfg.get("projects", [***REMOVED***)***REMOVED***
            scan_targets = configured or [
                d.name for d in root.iterdir()
                if d.is_dir() and not d.name.startswith(".")
                and ((d / "project.yaml").exists() or (d / "README.md").exists())
            ***REMOVED***

            for name in scan_targets:
                p = root / name
                if not p.is_dir():
                    continue
                abs_path = str(p.resolve())
                row = conn.execute(
                    "SELECT workspace_slug FROM workspace_projects WHERE path = ?",
                    (abs_path,),
                ).fetchone()
                if row:
                    current_slug = row["workspace_slug"***REMOVED***
                    if current_slug != ws_slug:
                        report.conflicts.append((abs_path, current_slug, ws_slug))
                        logger.warning(
                            "sync_from_config: path %s already in workspace '%s' (expected '%s'); skipped",
                            abs_path, current_slug, ws_slug,
                        )
                    else:
                        report.skipped_projects.append(abs_path)
                else:
                    try:
                        conn.execute(
                            "INSERT INTO workspace_projects (path, workspace_slug, name, created_at, status)"
                            " VALUES (?, ?, ?, ?, 'active')",
                            (abs_path, ws_slug, name, now),
                        )
                        report.created_projects.append(abs_path)
                    except sqlite3.IntegrityError as exc:
                        logger.warning(
                            "sync_from_config: path %s already bound (race): %s", abs_path, exc
                        )
                        report.skipped_projects.append(abs_path)

            conn.commit()
        return report
    def create_workspace(
        self,
        name: str,
        project_paths: list[str***REMOVED*** | None = None,
        description: str = "",
        owner_chat_id: int = 0,
        *,
        strict: bool = False,
    ) -> Workspace:
        slug = _slugify_name(name)
        if not slug or len(name) > self.MAX_NAME_LEN:
            raise ValueError(
                f"workspace name must be 1-{self.MAX_NAME_LEN***REMOVED*** chars; got {name!r***REMOVED***"
            )
        # Pre-validate (CAN-14 strict mode — fix #3 polish): if ANY path is missing
        # on FS and strict=True, raise FileNotFoundError BEFORE inserting workspace.
        # This ELIMINATES partial-state under create_workspace(strict=True, multi-path):
        # without pre-validation, add_project(valid) would commit durably before
        # add_project(ghost) raises, leaving DB with orphan workspace + already-bound project.
        # RTX-default (strict=False) still proceeds with warn-and-skip in add_project loop.
        # NOTE: narrow TOCTOU window between pre-validate and add_project; acceptable for
        # Termux single-user prototype (no concurrent FS ops). Verified by
        # test_create_workspace_strict_no_partial_state_on_ghost_path.
        if strict and project_paths:
            for p in project_paths:
                full = Path(p).expanduser().resolve()
                if not full.exists():
                    raise FileNotFoundError(
                        f"WorkspaceRegistry.create_workspace(strict=True):"
                        f" path not found on FS: {full***REMOVED***."
                        f" Switch to strict=False for warn-and-skip behavior,"
                        f" or create the path first."
                    )
        now = time.time()
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO workspaces
                        (slug, name, owner_chat_id, created_at, status, description)
                    VALUES (?, ?, ?, ?, 'active', ?)
                    """,
                    (slug, name, owner_chat_id, now, description),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"workspace with slug {slug!r***REMOVED*** already exists: {exc***REMOVED***"
                ) from exc
        # add_project loop FIRST so self.list_projects(slug) sees post-insert DB state
        # (the ghost paths warned-and-skipped during the loop will be EXCLUDED in Workspace.project_paths)
        for p in project_paths or [***REMOVED***:
            self.add_project(slug, p, strict=strict)
        ws = Workspace(
            name=name,
            slug=slug,
            project_paths=self.list_projects(slug),
            created_at=now,
            description=description,
            owner_chat_id=owner_chat_id,
        )
        return ws

    def add_project(self, workspace_slug: str, project_path: str, *, strict: bool = False) -> bool:
        """Bind a project path to a workspace. Privacy: path can belong to ONE workspace.

        Atomic (single transaction, BEGIN IMMEDIATE для защиты от race:
        check-then-insert теперь защищён за счёт write-lock уровня WAL+exclusive).
        Filesystem validation: missing paths →
            - strict=False (default): logger.warning + return False (silent skip,
              backwards-compatible with TG-bot/MCP flows that must not crash).
            - strict=True (RTX-style opt-in): raise FileNotFoundError (fail-loud).

        Returns:
          - True if bound (inserted OR idempotent same-workspace).
          - False if path missing on FS and strict=False (warn-and-skip).

        Raises:
          - FileNotFoundError if path missing on FS and strict=True.
          - ValueError if project_path is empty / workspace_slug missing.
          - PrivacyViolationError if path is owned by another workspace.
        """
        if not project_path:
            raise ValueError("project_path must be non-empty")
        full = Path(project_path).expanduser().resolve()
        if not full.exists():
            if strict:
                # RTX-style fail-loud: opt-in via strict=True.
                raise FileNotFoundError(
                    f"WorkspaceRegistry.add_project(strict=True): path not found on FS: {full***REMOVED***. "
                    f"Switch to strict=False for warn-and-skip behavior."
                )
            logger.warning(
                "WorkspaceRegistry.add_project: path %s not found"
                " on filesystem; skipping insertion (strict=False)",
                full,
            )
            return False
        abs_path = str(full)
        with self._connect() as conn:
            # BEGIN IMMEDIATE acquires a RESERVED lock — guarantees no
            # other connection writes between our check and insert.
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT workspace_slug FROM workspace_projects WHERE path = ?",
                    (abs_path,),
                ).fetchone()
                if existing and existing["workspace_slug"***REMOVED*** != workspace_slug:
                    raise PrivacyViolationError(
                        path=abs_path,
                        expected_slug=workspace_slug,
                        actual_slug=existing["workspace_slug"***REMOVED***,
                    )
                if existing and existing["workspace_slug"***REMOVED*** == workspace_slug:
                    # already in same workspace: idempotent no-op
                    conn.commit()
                    return True
                conn.execute(
                    """
                    INSERT INTO workspace_projects
                        (path, workspace_slug, name, created_at, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (
                        abs_path,
                        workspace_slug,
                        full.name or abs_path,
                        time.time(),
                    ),
                )
                conn.commit()
                return True
            except PrivacyViolationError:
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
    def list_workspaces(self) -> list[Workspace***REMOVED***:
        """Returns all workspaces with their joined project_paths."""
        with self._connect() as conn:
            ws_rows = conn.execute(
                "SELECT slug, name, owner_chat_id, created_at, status, description"
                " FROM workspaces ORDER BY created_at"
            ).fetchall()
            proj_rows = conn.execute(
                "SELECT path, workspace_slug FROM workspace_projects ORDER BY created_at"
            ).fetchall()
        paths_by_slug: dict[str, list[str***REMOVED******REMOVED*** = {***REMOVED***
        for r in proj_rows:
            paths_by_slug.setdefault(r["workspace_slug"***REMOVED***, [***REMOVED***).append(r["path"***REMOVED***)
        return [
            Workspace(
                name=r["name"***REMOVED***,
                slug=r["slug"***REMOVED***,
                project_paths=paths_by_slug.get(r["slug"***REMOVED***, [***REMOVED***),
                created_at=r["created_at"***REMOVED***,
                status=r["status"***REMOVED***,
                description=r["description"***REMOVED***,
                owner_chat_id=r["owner_chat_id"***REMOVED***,
            )
            for r in ws_rows
        ***REMOVED***

    def list_projects(self, workspace_slug: str) -> list[str***REMOVED***:
        """Returns ONLY paths for the given workspace (isolation guarantee)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path FROM workspace_projects"
                " WHERE workspace_slug = ? ORDER BY created_at",
                (workspace_slug,),
            ).fetchall()
        return [r["path"***REMOVED*** for r in rows***REMOVED***

    def find_workspace_for_project(self, project_path: str) -> Workspace | None:
        """Returns the single owning Workspace for the path, or None if unregistered."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT workspace_slug FROM workspace_projects WHERE path = ?",
                (project_path,),
            ).fetchone()
        if not row:
            return None
        slug = row["workspace_slug"***REMOVED***
        for ws in self.list_workspaces():
            if ws.slug == slug:
                return ws
        return None

    def assert_path_privacy(
        self, project_path: str, expected_workspace_slug: str
    ) -> None:
        """CAN-14 fail-loud: raise PrivacyViolationError if path leaks across boundaries.

        Успешный no-op, если path принадлежит expected_workspace_slug.
        Path может быть НЕ зарегистрирован (NULL workspace) — это не violation.
        """
        ws = self.find_workspace_for_project(project_path)
        if ws is not None and ws.slug != expected_workspace_slug:
            raise PrivacyViolationError(
                path=project_path,
                expected_slug=expected_workspace_slug,
                actual_slug=ws.slug,
            )


# ── Module-level convenience ──


def get_default_registry() -> WorkspaceRegistry:
    """One-line accessor for the canonical DB at data_13/context.db."""
    return WorkspaceRegistry()


__all__ = [
    "DEFAULT_WORKSPACES",
    "PrivacyViolationError",
    "Project",
    "SyncReport",
    "Workspace",
    "WorkspaceRegistry",
    "_slugify_name",
    "get_default_registry",
***REMOVED***
