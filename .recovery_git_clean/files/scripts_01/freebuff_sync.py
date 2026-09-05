#!/usr/bin/env python3
"""Freebuff workspace synchronisation over Git/SSH.

The module deliberately keeps the mutating surface small:

* discovery and ``bootstrap --dry-run`` are the default safe path;
* Git and SSH commands are argv-based and never use ``shell=True``;
* hard-denied files are excluded before Git operations;
* remote mutation requires an explicit ``bootstrap --apply``.

The implementation is intentionally independent from Freebuff's runtime/API
servers. It only owns the workspace mirror contract described in
``freebuff-sync-spec.md``.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
***REMOVED***
import shutil
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    import yaml
except ImportError:  # pragma: no cover - requirements.txt already includes PyYAML
    yaml = None  # type: ignore[assignment***REMOVED***

MODULE_VERSION = "1.0.0"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFLICT = 2
EXIT_SUSPICIOUS = 3
EXIT_CONFIG = 4
EXIT_LOCK = 5

CANONICAL_DIRS = (
    ".freebuff",
    ".github",
    "buffy-playground_19",
    "cli_07",
    "core_02",
    "docs_10",
    "freebuff_plugin",
    "freebuff_plugin_03",
    "frontend_18",
    "infa_20",
    "plugins_04",
    "pompts_11",
    "projects_17",
    "prototype_22",
    "runtime_05",
    "scripts_01",
    "services_08",
    "src_06",
    "tests_09",
)

ROOT_ALLOWLIST = {
    ".cursorrules",
    ".freebuff",
    ".gitignore",
    "AGENTS.md",
    "BUFFY.md",
    "BUFFY_PROJECT.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODY.md",
    "README.md",
    "SPEC.md",
    "TASK.md",
    "__init__.py",
    "freebuff_cli.py",
    "freebuff-sync-spec.md",
    "freebuff_sync.py",
    "generate_project_dump.sh",
    "mypy.ini",
    "pytest.ini",
    "requirements.txt",
    "run_checks.py",
    "run_tests.sh",
    "run_tests_fast.sh",
    "setup_canonical.sh",
    "smart_test_runner.sh",
    "smart_test_runner_fixed.sh",
    "status_report.sh",
    "verify_archive.sh",
***REMOVED***

HARD_DENY_DIRS = {
    ".git",
    ".keys",
    ".freezer",
    ".mypy_cache",
    ".pytest_cache",
    ".test_logs",
    ".test_temp",
    "node_modules",
    "dist",
    "build",
    ".vite",
    "books_out_23",
    "trash_21",
    "screenshots_16",
    "architecture_forensics_v2",
    "intelligence_forensics_25",
    "phase4_evaluation_24",
    "phase5_intelligence_loop_26",
    "phase6_code_contract_forensics_27",
    "phase7_evaluation_28",
    "phase8_evaluation_29",
    "phase9_evaluation_30",
    "phase9_implementation_continuation_31",
    "platform_architectural_inventory_34",
    "repository_organization_forensics_32",
    "system_model_forensics_33",
    "FORENSICS_104_105_106_107",
***REMOVED***

HARD_DENY_PATTERNS = (
    ".env",
    ".env.*",
    "*.session",
    "*.session-journal",
    "*.pem",
    "*.key",
    "*.crt",
    "*.log",
    "*.pid",
    "*.lock",
    "*.tmp",
    "*.bak",
    "*.bak-*",
    "*.orig",
    "*~",
    "*.pyc",
    "*.pyo",
    "*.db-wal",
    "*.db-shm",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.zip",
    "*.7z",
    "*.rar",
    "*.sha256",
    "*.md5",
)

SUSPICIOUS_NAME_PARTS = ("token", "secret", "credential", "private_key")

RUNTIME_DECLARATIVE = (
    "data_13/forge_registry.yaml",
    "data_13/missing_registry.yaml",
    "data_13/opportunities.yaml",
    "data_13/whims.yaml",
    "data_13/scenario_decisions.yaml",
    "data_13/lisa_calibration.yaml",
    "data_13/hypothesis_ledger/**",
    "context_12/unified_context.md",
    "context_12/session_todos.md",
    "context_12/checkpoints/**",
    "context_12/summaries/**",
    "context_12/memory/**",
    "context_12/knowledge/**",
    "context_12/exports/**",
    "sessions_15/README.md",
    "sessions_15/.gitkeep",
)

RUNTIME_SQLITE = (
    "data_13/context.db",
    "data_13/metrics.db",
    "data_13/presence.db",
    "data_13/project_pulse.db",
    "data_13/roles.db",
    "data_13/collaboration.db",
    "data_13/verifier.db",
    "context_12/events.db",
    "projects_17/diet_platform/diet_platform.db",
    "projects_17/tg_terminal_messenger/tg_cache.db",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__***REMOVED***")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name***REMOVED***.{os.getpid()***REMOVED***.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path, limit: int | None = None) -> str | None:
    if limit is not None and path.stat().st_size > limit:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_dict(value: Any) -> dict[str, Any***REMOVED***:
    return dict(value) if isinstance(value, Mapping) else {***REMOVED***


def _expand_local_path(value: str | Path, base: Path) -> Path:
    path = Path(os.path.expanduser(str(value)))
    return path if path.is_absolute() else (base / path).resolve()


def validate_remote_path(value: str, field_name: str) -> str:
    path = Path(os.path.expanduser(value))
    if not path.is_absolute():
        raise ValueError(f"{field_name***REMOVED*** must be an absolute path: {value!r***REMOVED***")
    if any(char in str(path) for char in ("\x00", "\n", "\r")):
        raise ValueError(f"{field_name***REMOVED*** contains control characters")
    return str(path)


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class LocalConfig:
    workspace_root: str = "."
    branch: str = "auto"


@dataclass(frozen=True)
class RemoteConfig:
    ssh_alias: str = "wimp"
    workspace_root: str | None = None
    bare_repo: str | None = None
    worktree: str | None = None
    branch: str = "auto"
    lock_path: str | None = None
    log_dir: str | None = None


@dataclass(frozen=True)
class SyncOptions:
    lock_timeout_sec: int = 30
    watch_interval_sec: int = 10
    watch_debounce_sec: int = 3
    delete_mode: str = "mirror-after-merge"
    conflict_mode: str = "stop-and-report"
    non_interactive: bool = False
    require_clean_success: bool = True


@dataclass(frozen=True)
class WatchOptions:
    enabled: bool = True
    backend: str = "hybrid"
    auto_commit: bool = True
    auto_push: bool = True
    check_command: tuple[str, ...***REMOVED*** | None = None
    commit_prefix: str = "chore(sync):"


@dataclass(frozen=True)
class FilterConfig:
    include: tuple[str, ...***REMOVED*** = CANONICAL_DIRS
    root_allowlist: tuple[str, ...***REMOVED*** = tuple(sorted(ROOT_ALLOWLIST))
    exclude: tuple[str, ...***REMOVED*** = ()
    runtime_data: bool = False
    runtime_allowlist: tuple[str, ...***REMOVED*** = RUNTIME_DECLARATIVE
    sqlite_allowlist: tuple[str, ...***REMOVED*** = ()
    large_file_limit_mib: int = 25
    large_file_allowlist: tuple[str, ...***REMOVED*** = ()
    unknown_policy: str = "exclude-and-report"


@dataclass(frozen=True)
class LoggingConfig:
    external_log_dir: str = "~/.cache/freebuff-sync"
    tracked_report_dir: str = ".freebuff/sync-reports"
    include_diff: bool = True


@dataclass(frozen=True)
class SyncConfig:
    version: int = 1
    local: LocalConfig = field(default_factory=LocalConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)
    sync: SyncOptions = field(default_factory=SyncOptions)
    watch: WatchOptions = field(default_factory=WatchOptions)
    filters: FilterConfig = field(default_factory=FilterConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    config_path: Path | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any***REMOVED***, config_path: Path | None = None) -> "SyncConfig":
        version = int(raw.get("version", 1))
        if version != 1:
            raise ValueError(f"unsupported sync config version: {version***REMOVED***")
        local_raw = _as_dict(raw.get("local"))
        remote_raw = _as_dict(raw.get("remote"))
        sync_raw = _as_dict(raw.get("sync"))
        watch_raw = _as_dict(raw.get("watch"))
        filter_raw = _as_dict(raw.get("filters"))
        logging_raw = _as_dict(raw.get("logging"))
        check = watch_raw.get("check_command")
        if isinstance(check, str):
            check_value: tuple[str, ...***REMOVED*** | None = (check,)
        elif isinstance(check, (list, tuple)):
            check_value = tuple(str(item) for item in check)
        else:
            check_value = None

        def tuple_value(key: str, default: Iterable[str***REMOVED***) -> tuple[str, ...***REMOVED***:
            value = filter_raw.get(key, default)
            if isinstance(value, str):
                return (value,)
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"filters.{key***REMOVED*** must be a list")
            return tuple(str(item) for item in value)

        config = cls(
            version=version,
            local=LocalConfig(
                workspace_root=str(local_raw.get("workspace_root", ".")),
                branch=str(local_raw.get("branch", "auto")),
            ),
            remote=RemoteConfig(
                ssh_alias=str(remote_raw.get("ssh_alias", "wimp")),
                workspace_root=(str(remote_raw["workspace_root"***REMOVED***) if remote_raw.get("workspace_root") else None),
                bare_repo=(str(remote_raw["bare_repo"***REMOVED***) if remote_raw.get("bare_repo") else None),
                worktree=(str(remote_raw["worktree"***REMOVED***) if remote_raw.get("worktree") else None),
                branch=str(remote_raw.get("branch", "auto")),
                lock_path=(str(remote_raw["lock_path"***REMOVED***) if remote_raw.get("lock_path") else None),
                log_dir=(str(remote_raw["log_dir"***REMOVED***) if remote_raw.get("log_dir") else None),
            ),
            sync=SyncOptions(
                lock_timeout_sec=int(sync_raw.get("lock_timeout_sec", 30)),
                watch_interval_sec=int(sync_raw.get("watch_interval_sec", 10)),
                watch_debounce_sec=int(sync_raw.get("watch_debounce_sec", 3)),
                delete_mode=str(sync_raw.get("delete_mode", "mirror-after-merge")),
                conflict_mode=str(sync_raw.get("conflict_mode", "stop-and-report")),
                non_interactive=bool(sync_raw.get("non_interactive", False)),
                require_clean_success=bool(sync_raw.get("require_clean_success", True)),
            ),
            watch=WatchOptions(
                enabled=bool(watch_raw.get("enabled", True)),
                backend=str(watch_raw.get("backend", "hybrid")),
                auto_commit=bool(watch_raw.get("auto_commit", True)),
                auto_push=bool(watch_raw.get("auto_push", True)),
                check_command=check_value,
                commit_prefix=str(watch_raw.get("commit_prefix", "chore(sync):")),
            ),
            filters=FilterConfig(
                include=tuple_value("include", CANONICAL_DIRS),
                root_allowlist=tuple_value("root_allowlist", sorted(ROOT_ALLOWLIST)),
                exclude=tuple_value("exclude", ()),
                runtime_data=bool(filter_raw.get("runtime_data", False)),
                runtime_allowlist=tuple_value("runtime_allowlist", RUNTIME_DECLARATIVE),
                sqlite_allowlist=tuple_value("sqlite_allowlist", ()),
                large_file_limit_mib=int(filter_raw.get("large_file_limit_mib", 25)),
                large_file_allowlist=tuple_value("large_file_allowlist", ()),
                unknown_policy=str(filter_raw.get("unknown_policy", "exclude-and-report")),
            ),
            logging=LoggingConfig(
                external_log_dir=str(logging_raw.get("external_log_dir", "~/.cache/freebuff-sync")),
                tracked_report_dir=str(logging_raw.get("tracked_report_dir", ".freebuff/sync-reports")),
                include_diff=bool(logging_raw.get("include_diff", True)),
            ),
            config_path=config_path,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.sync.lock_timeout_sec <= 0:
            raise ValueError("sync.lock_timeout_sec must be positive")
        if self.sync.watch_interval_sec <= 0 or self.sync.watch_debounce_sec < 0:
            raise ValueError("watch intervals are invalid")
        if self.filters.large_file_limit_mib <= 0:
            raise ValueError("filters.large_file_limit_mib must be positive")
        if self.filters.unknown_policy not in {"exclude-and-report", "fail"***REMOVED***:
            raise ValueError("filters.unknown_policy must be exclude-and-report or fail")
        if not self.remote.ssh_alias or any(char.isspace() for char in self.remote.ssh_alias):
            raise ValueError("remote.ssh_alias must be a non-empty SSH alias")
        values = {
            "remote.workspace_root": self.remote.workspace_root,
            "remote.bare_repo": self.remote.bare_repo,
            "remote.worktree": self.remote.worktree,
            "remote.lock_path": self.remote.lock_path,
            "remote.log_dir": self.remote.log_dir,
        ***REMOVED***
        for name, value in values.items():
            if value:
                validate_remote_path(value, name)
        if self.remote.bare_repo and self.remote.worktree:
            bare = Path(self.remote.bare_repo).resolve()
            worktree = Path(self.remote.worktree).resolve()
            if bare == worktree or _is_relative_to(bare, worktree) or _is_relative_to(worktree, bare):
                raise ValueError("remote.bare_repo and remote.worktree must not overlap")

    def resolved_local_root(self, cwd: Path | None = None) -> Path:
        base = (self.config_path.parent if self.config_path else (cwd or Path.cwd())).resolve()
        return _expand_local_path(self.local.workspace_root, base)

    def external_log_dir(self, local_root: Path) -> Path:
        return _expand_local_path(self.logging.external_log_dir, local_root)


def load_config(path: Path) -> SyncConfig:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read sync configuration")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {***REMOVED***
    if not isinstance(raw, Mapping):
        raise ValueError("sync config root must be a mapping")
    return SyncConfig.from_mapping(raw, path.resolve())


@dataclass(frozen=True)
class FileClassification:
    path: str
    category: str
    reason: str
    size_bytes: int
    git_tracked: bool
    sha256: str | None = None


class FileClassifier:
    """Classify workspace paths according to the spec's ordered rules."""

    def __init__(self, root: Path, config: FilterConfig):
        self.root = root.resolve()
        self.config = config
        self.large_limit = config.large_file_limit_mib * 1024 * 1024

    @staticmethod
    def _matches(path: str, patterns: Iterable[str***REMOVED***) -> bool:
        normalized = path.strip("/")
        for pattern in patterns:
            pattern = pattern.strip("/")
            if fnmatch.fnmatchcase(normalized, pattern) or fnmatch.fnmatchcase(normalized, pattern.lstrip("**/")):
                return True
            if pattern.endswith("/**") and (normalized == pattern[:-3***REMOVED*** or normalized.startswith(pattern[:-2***REMOVED***)):
                return True
        return False

    def _hard_denied(self, relative: str) -> str | None:
        parts = relative.split("/")
        if relative == "core" or relative.startswith("core/"):
            return "hard-deny legacy core directory"
        if any(part in HARD_DENY_DIRS for part in parts[:-1***REMOVED***):
            return "hard-deny directory"
        if relative in {".freebuff_result", ".freebuff_original_agents", "data_13/.drift_last_run", "data_13/.pulse_snapshot.json", "docs_10/DRIFT_REPORT.md", "status_report_20260801_205122.txt", "verify_archive_marker.txt"***REMOVED***:
            return "hard-deny generated artifact"
        basename = parts[-1***REMOVED***
        if basename == ".env" or basename.startswith(".env."):
            return "hard-deny secret environment file"
        lower_name = basename.lower()
        if any(part in lower_name for part in SUSPICIOUS_NAME_PARTS):
            return "suspicious secret-like filename"
        if self._matches(relative, HARD_DENY_PATTERNS):
            return "hard-deny filename pattern"
        return None

    def _runtime_allowed(self, relative: str) -> bool:
        return self.config.runtime_data and self._matches(relative, self.config.runtime_allowlist)

    def _sqlite_allowed(self, relative: str) -> bool:
        return self.config.runtime_data and relative in set(self.config.sqlite_allowlist)

    def classify(self, path: Path, git_tracked: bool = False) -> FileClassification:
        relative = path.resolve().relative_to(self.root).as_posix()
        size = path.stat().st_size if path.is_file() else 0
        denied = self._hard_denied(relative)
        if denied:
            return FileClassification(relative, "ignored", denied, size, git_tracked)
        if path.is_file() and path.suffix.lower() == ".db" and not self._sqlite_allowed(relative):
            return FileClassification(relative, "ignored", "SQLite requires explicit sqlite_allowlist", size, git_tracked)
        if relative.startswith(("data_13/", "context_12/", "logs_14/", "sessions_15/")) and not self._runtime_allowed(relative):
            return FileClassification(relative, "unknown", "runtime data is opt-in", size, git_tracked)
        top = relative.split("/", 1)[0***REMOVED***
        allowed = top in self.config.include or relative in set(self.config.root_allowlist)
        if self._matches(relative, self.config.exclude):
            return FileClassification(relative, "ignored", "explicit YAML exclude", size, git_tracked)
        if not allowed and not self._runtime_allowed(relative):
            return FileClassification(relative, "unknown", "outside canonical workspace allowlist", size, git_tracked)
        if path.is_file() and size > self.large_limit and not self._matches(relative, self.config.large_file_allowlist):
            return FileClassification(relative, "suspicious", f"file exceeds {self.config.large_file_limit_mib***REMOVED*** MiB", size, git_tracked)
        digest = sha256_file(path, limit=self.large_limit)
        return FileClassification(relative, "included", "canonical workspace allowlist", size, git_tracked, digest)

    def scan(self, tracked_paths: set[str***REMOVED*** | None = None) -> list[FileClassification***REMOVED***:
        tracked_paths = tracked_paths or set()
        result: list[FileClassification***REMOVED*** = [***REMOVED***
        if not self.root.exists():
            raise FileNotFoundError(self.root)
        for current, directories, filenames in os.walk(self.root):
            directories[:***REMOVED*** = sorted(
                name for name in directories
                if name not in HARD_DENY_DIRS and name != "__pycache__"
            )
            current_path = Path(current)
            for filename in sorted(filenames):
                path = current_path / filename
                try:
                    relative = path.resolve().relative_to(self.root).as_posix()
                except ValueError:
                    continue
                result.append(self.classify(path, relative in tracked_paths))
        return result


def discover_local(root: Path, runner: Callable[..., CommandResult***REMOVED*** | None = None) -> dict[str, Any***REMOVED***:
    root = root.resolve()
    runner = runner or run_command
    markers = [name for name in ("AGENTS.md", "BUFFY.md", "core_02", "scripts_01", "projects_17") if (root / name).exists()***REMOVED***
    if len(markers) < 2:
        raise ValueError(f"not a Freebuff workspace: {root***REMOVED***")
    git_root: str | None = None
    branch: str | None = None
    head: str | None = None
    clean = False
    git_present = shutil.which("git") is not None
    if git_present:
        try:
            git_root = runner(["git", "-C", str(root), "rev-parse", "--show-toplevel"***REMOVED***).stdout.strip()
            branch = runner(["git", "-C", str(root), "symbolic-ref", "--short", "-q", "HEAD"***REMOVED***, check=False).stdout.strip() or None
            head = runner(["git", "-C", str(root), "rev-parse", "HEAD"***REMOVED***, check=False).stdout.strip() or None
            tracked_diff = runner(["git", "-C", str(root), "diff", "--quiet"***REMOVED***, check=False, timeout=15)
            staged_diff = runner(["git", "-C", str(root), "diff", "--cached", "--quiet"***REMOVED***, check=False, timeout=15)
            untracked = runner(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "--directory"***REMOVED***, check=False, timeout=15)
            clean = tracked_diff.returncode == 0 and staged_diff.returncode == 0 and not untracked.stdout.strip()
        except OSError:
            pass
    return {"workspace_root": str(root), "git_root": git_root, "git_present": git_present, "branch": branch, "head": head, "clean": clean, "markers": markers***REMOVED***


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...***REMOVED***
    returncode: int
    stdout: str = ""
    stderr: str = ""


def run_command(argv: Sequence[str***REMOVED***, *, input_text: str | None = None, check: bool = True, cwd: Path | None = None, timeout: int = 30) -> CommandResult:
    completed = subprocess.run(
        list(argv),
        input=input_text,
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        check=False,
    )
    result = CommandResult(tuple(str(item) for item in argv), completed.returncode, completed.stdout, completed.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode***REMOVED***): {' '.join(result.argv)***REMOVED***\n{result.stderr.strip()***REMOVED***")
    return result


REMOTE_PROBE_SCRIPT = """set -eu
printf 'protocol=1\\n'
printf 'host=%s\\n' \"$(hostname 2>/dev/null || printf unknown)\"
printf 'user=%s\\n' \"$(id -un 2>/dev/null || printf unknown)\"
printf 'home=%s\\n' \"${HOME:-unknown***REMOVED***\"
printf 'os=%s\\n' \"$(uname -s 2>/dev/null || printf unknown)\"
printf 'arch=%s\\n' \"$(uname -m 2>/dev/null || printf unknown)\"
printf 'git=%s\\n' \"$(command -v git 2>/dev/null || printf missing)\"
printf 'python3=%s\\n' \"$(command -v python3 2>/dev/null || printf missing)\"
printf 'inotifywait=%s\\n' \"$(command -v inotifywait 2>/dev/null || printf missing)\"
"""

REMOTE_BOOTSTRAP_SCRIPT = r"""set -eu
bare=$1
worktree=$2
lock=$3
backup=$4
mkdir -p "$(dirname "$bare")" "$(dirname "$worktree")" "$(dirname "$lock")" "$(dirname "$backup")"
mkdir "$lock" 2>/dev/null || { printf 'remote sync lock is busy\\n' >&2; exit 43; ***REMOVED***
trap 'rmdir "$lock" 2>/dev/null || true' EXIT
if [ -e "$bare" ***REMOVED***; then
  git --git-dir="$bare" rev-parse --is-bare-repository >/dev/null
else
  git init --bare "$bare" >/dev/null
fi
if [ -e "$worktree" ***REMOVED***; then
  if [ -z "$(find "$worktree" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ***REMOVED***; then
    rmdir "$worktree"
  else
    mkdir -p "$backup"
    mv "$worktree" "$backup/worktree"
  fi
fi
"""

REMOTE_HOOK_INSTALL_SCRIPT = r"""set -eu
bare=$1
log_dir=$2
pre_b64=$3
post_b64=$4
mkdir -p "$bare/hooks" "$log_dir"
printf '%s' "$pre_b64" | base64 -d > "$bare/hooks/pre-receive"
printf '%s' "$post_b64" | base64 -d > "$bare/hooks/post-receive"
chmod 700 "$bare/hooks/pre-receive" "$bare/hooks/post-receive"
"""

REMOTE_CANDIDATE_SCRIPT = r"""set -eu
home=${HOME:?***REMOVED***
for root in "$home" "$home/work" "$home/workspace" "$home/projects" "$home/src" "$home/PROJECTS" /srv /opt; do
  [ -d "$root" ***REMOVED*** || continue
  find "$root" -maxdepth 4 -xdev -type d -name .git -prune -print 2>/dev/null | while IFS= read -r gitdir; do
    candidate=${gitdir%/.git***REMOVED***
    markers=0
    [ -f "$candidate/AGENTS.md" ***REMOVED*** && markers=$((markers + 1))
    [ -f "$candidate/BUFFY.md" ***REMOVED*** && markers=$((markers + 1))
    [ -d "$candidate/core_02" ***REMOVED*** && markers=$((markers + 1))
    [ -d "$candidate/scripts_01" ***REMOVED*** && markers=$((markers + 1))
    [ -d "$candidate/projects_17" ***REMOVED*** && markers=$((markers + 1))
    [ "$markers" -ge 2 ***REMOVED*** || continue
    printf '%s\\t%s\\t%s\\n' "$candidate" "$markers" "worktree"
  done
  find "$root" -maxdepth 4 -xdev -type d -name '*.git' -prune -print 2>/dev/null | while IFS= read -r bare; do
    printf '%s\\t0\\tbare\\n' "$bare"
  done
done
"""


def parse_candidates(output: str) -> list[dict[str, Any***REMOVED******REMOVED***:
    candidates: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    seen: set[str***REMOVED*** = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\\t")
        if len(fields) != 3:
            raise ValueError(f"invalid candidate probe line: {line!r***REMOVED***")
        path, marker_count, kind = fields
        if not path.startswith("/") or kind not in {"worktree", "bare"***REMOVED***:
            raise ValueError(f"invalid candidate probe values: {line!r***REMOVED***")
        if path in seen:
            continue
        seen.add(path)
        candidates.append({"path": path, "markers": int(marker_count), "git_kind": kind***REMOVED***)
    return candidates


def ssh_candidates(alias: str, runner: Callable[..., CommandResult***REMOVED*** = run_command) -> list[dict[str, Any***REMOVED******REMOVED***:
    result = runner(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", alias, "sh", "-s", "--"***REMOVED***,
        input_text=REMOTE_CANDIDATE_SCRIPT,
        timeout=30,
    )
    return parse_candidates(result.stdout)


def parse_probe(output: str) -> dict[str, str***REMOVED***:
    parsed: dict[str, str***REMOVED*** = {***REMOVED***
    allowed = {"protocol", "host", "user", "home", "os", "arch", "git", "python3", "inotifywait"***REMOVED***
    for line in output.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in allowed or key in parsed:
            raise ValueError(f"invalid remote probe line: {line!r***REMOVED***")
        parsed[key***REMOVED*** = value
    if parsed.get("protocol") != "1":
        raise ValueError("remote probe protocol must be 1")
    if not parsed.get("home", "").startswith("/"):
        raise ValueError("remote probe home must be absolute")
    return parsed


def ssh_probe(alias: str, runner: Callable[..., CommandResult***REMOVED*** = run_command) -> dict[str, str***REMOVED***:
    result = runner(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", alias, "sh", "-s", "--"***REMOVED***,
        input_text=REMOTE_PROBE_SCRIPT,
        timeout=15,
    )
    return parse_probe(result.stdout)


class LockBusy(RuntimeError):
    pass


class LocalLock:
    def __init__(self, path: Path, mode: str, timeout_sec: int = 30):
        self.path = path
        self.mode = mode
        self.timeout_sec = timeout_sec
        self.acquired = False

    def __enter__(self) -> "LocalLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise LockBusy(f"sync lock is busy: {self.path***REMOVED***") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "hostname": os.uname().nodename, "mode": self.mode, "timestamp": utc_stamp()***REMOVED***))
        self.acquired = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


@dataclass
class BootstrapPlan:
    local: dict[str, Any***REMOVED***
    remote_probe: dict[str, str***REMOVED*** | None
    candidates: list[dict[str, Any***REMOVED******REMOVED***
    paths: dict[str, str | None***REMOVED***
    classifications: list[FileClassification***REMOVED***
    actions: list[str***REMOVED***
    blocked: list[str***REMOVED***
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any***REMOVED***:
        data = asdict(self)
        data["classifications"***REMOVED*** = [asdict(item) for item in self.classifications***REMOVED***
        return data


class FreebuffSync:
    """Orchestrate discovery and Git synchronisation for one workspace."""

    def __init__(self, config: SyncConfig, runner: Callable[..., CommandResult***REMOVED*** = run_command):
        self.config = config
        self.runner = runner
        self.root = config.resolved_local_root()
        self.local_lock_path = self.config.external_log_dir(self.root) / "sync.lock"

    def tracked_paths(self) -> set[str***REMOVED***:
        if not shutil.which("git"):
            return set()
        result = self.runner(["git", "-C", str(self.root), "ls-files"***REMOVED***, check=False)
        return {line.strip() for line in result.stdout.splitlines() if line.strip()***REMOVED***

    def classify(self) -> list[FileClassification***REMOVED***:
        return FileClassifier(self.root, self.config.filters).scan(self.tracked_paths())

    def _remote_paths(self) -> dict[str, str | None***REMOVED***:
        remote = self.config.remote
        return {"workspace_root": remote.workspace_root, "bare_repo": remote.bare_repo, "worktree": remote.worktree, "lock_path": remote.lock_path, "log_dir": remote.log_dir***REMOVED***

    def plan_bootstrap(self, dry_run: bool = True, probe: dict[str, str***REMOVED*** | None = None) -> BootstrapPlan:
        local = discover_local(self.root, self.runner)
        candidates: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        if probe is None and self.config.remote.ssh_alias:
            try:
                probe = ssh_probe(self.config.remote.ssh_alias, self.runner)
                if not self.config.remote.workspace_root:
                    candidates = ssh_candidates(self.config.remote.ssh_alias, self.runner)
            except Exception as exc:
                probe = {"protocol": "error", "error": str(exc)***REMOVED***
        classifications = self.classify()
        blocked: list[str***REMOVED*** = [***REMOVED***
        suspicious = [item.path for item in classifications if item.category == "suspicious"***REMOVED***
        unknown = [item.path for item in classifications if item.category == "unknown"***REMOVED***
        if suspicious:
            blocked.append(f"suspicious files require review: {len(suspicious)***REMOVED***")
        if unknown and self.config.filters.unknown_policy == "fail":
            blocked.append(f"unknown files require review: {len(unknown)***REMOVED***")
        if local.get("branch") is None:
            blocked.append("local repository is detached or has no branch")
        paths = self._remote_paths()
        if probe and probe.get("protocol") == "error":
            blocked.append(f"SSH discovery failed: {probe.get('error', 'unknown error')***REMOVED***")
        if probe and probe.get("git") == "missing":
            blocked.append("remote git is unavailable")
        if not all(paths.get(key) for key in ("workspace_root", "bare_repo", "worktree")):
            blocked.append("remote.workspace_root, bare_repo and worktree must be configured after discovery")
        actions = [
            "run bounded SSH capability probe",
            "write sync-discovery.json to external log directory",
            "create/verify remote bare repository",
            "capture existing server worktree seed before merge",
            "publish local branch without force push",
            "create/reuse clean server worktree",
            "install versioned pre-receive and post-receive hooks",
            "verify local HEAD == bare ref == server worktree HEAD",
        ***REMOVED***
        if not paths.get("workspace_root") and not candidates:
            blocked.append("no unambiguous remote Freebuff candidate was discovered")
        return BootstrapPlan(local, probe, candidates, paths, classifications, actions, blocked, dry_run)

    def bootstrap(self, *, apply: bool = False, yes: bool = False, probe: dict[str, str***REMOVED*** | None = None) -> BootstrapPlan:
        plan = self.plan_bootstrap(dry_run=not apply, probe=probe)
        if not apply:
            self._write_report("bootstrap-dry-run", plan.to_dict())
            return plan
        if plan.blocked:
            raise RuntimeError("bootstrap blocked: " + "; ".join(plan.blocked))
        if not yes and self.config.sync.non_interactive:
            raise RuntimeError("mutating bootstrap requires --yes in non-interactive mode")
        with LocalLock(self.local_lock_path, "bootstrap", self.config.sync.lock_timeout_sec):
            self._apply_bootstrap(plan)
        plan.dry_run = False
        self._write_report("bootstrap", plan.to_dict())
        return plan

    def _write_report(self, mode: str, payload: dict[str, Any***REMOVED***) -> Path:
        report_dir = self.config.external_log_dir(self.root) / "runs"
        report = report_dir / f"{utc_stamp()***REMOVED***-{mode***REMOVED***.json"
        write_json(report, payload)
        return report

    def _apply_bootstrap(self, plan: BootstrapPlan) -> None:
        remote = self.config.remote
        assert remote.bare_repo and remote.worktree and remote.workspace_root
        if not plan.local.get("clean"):
            raise RuntimeError("local worktree must be clean before apply bootstrap")
        probe = plan.remote_probe or ssh_probe(remote.ssh_alias, self.runner)
        if probe.get("git") == "missing":
            raise RuntimeError("remote git is unavailable")
        # Remote commands use argv; paths have already passed absolute-path validation.
        lock_path = remote.lock_path or f"{remote.bare_repo***REMOVED***.lock"
        log_dir = remote.log_dir or f"{remote.bare_repo***REMOVED***.logs"
        backup = f"{remote.worktree***REMOVED***.freebuff-sync-backups/bootstrap-{utc_stamp()***REMOVED***"
        self.runner(
            [
                "ssh", remote.ssh_alias, "sh", "-s", "--",
                shlex.quote(remote.bare_repo), shlex.quote(remote.worktree),
                shlex.quote(lock_path), shlex.quote(backup),
            ***REMOVED***,
            input_text=REMOTE_BOOTSTRAP_SCRIPT,
            timeout=120,
        )
        remote_url = f"{remote.ssh_alias***REMOVED***:{remote.bare_repo***REMOVED***"
        remotes = self.runner(["git", "-C", str(self.root), "remote"***REMOVED***, check=False).stdout.splitlines()
        if "freebuff-sync" not in remotes:
            self.runner(["git", "-C", str(self.root), "remote", "add", "freebuff-sync", remote_url***REMOVED***)
        branch = plan.local["branch"***REMOVED***
        self.runner(["git", "-C", str(self.root), "push", "freebuff-sync", f"{branch***REMOVED***:refs/heads/{branch***REMOVED***"***REMOVED***, timeout=120)
        self.runner(
            ["ssh", remote.ssh_alias, "git", "clone", shlex.quote(remote.bare_repo), shlex.quote(remote.worktree)***REMOVED***,
            timeout=120,
        )
        self.runner(["ssh", remote.ssh_alias, "mkdir", "-p", shlex.quote(str(Path(lock_path).parent)), shlex.quote(log_dir)***REMOVED***, timeout=30)
        import base64
        import shlex
        branch_literal = shlex.quote(branch)
        bare_literal = shlex.quote(remote.bare_repo)
        worktree_literal = shlex.quote(remote.worktree)
        lock_literal = shlex.quote(lock_path)
        log_literal = shlex.quote(log_dir)
        pre_hook = f"""#!/bin/sh
set -eu
branch={branch_literal***REMOVED***
while IFS=' ' read -r old new ref; do
  [ \"$ref\" = \"refs/heads/$branch\" ***REMOVED*** || {{ printf 'only configured branch may be pushed\\n' >&2; exit 1; ***REMOVED******REMOVED***
done
"""
        post_hook = f"""#!/bin/sh
set -eu
bare={bare_literal***REMOVED***
worktree={worktree_literal***REMOVED***
lock={lock_literal***REMOVED***
log_dir={log_literal***REMOVED***
branch={branch_literal***REMOVED***
mkdir \"$lock\" 2>/dev/null || {{ printf 'sync hook lock is busy\\n' >&2; exit 1; ***REMOVED******REMOVED***
trap 'rmdir \"$lock\" 2>/dev/null || true' EXIT
mkdir -p \"$log_dir\"
if [ -n \"$(git -C \"$worktree\" status --porcelain --untracked-files=all)\" ***REMOVED***; then
  printf '%s dirty worktree\\n' \"$(date -u +%FT%TZ)\" >> \"$log_dir/hook.log\"
  exit 1
fi
git -C \"$worktree\" fetch \"$bare\" \"$branch\"
git -C \"$worktree\" merge --ff-only FETCH_HEAD
"""
        self.runner(
            [
                "ssh", remote.ssh_alias, "sh", "-s", "--", shlex.quote(remote.bare_repo),
                shlex.quote(log_dir), base64.b64encode(pre_hook.encode()).decode(),
                base64.b64encode(post_hook.encode()).decode(),
            ***REMOVED***,
            input_text=REMOTE_HOOK_INSTALL_SCRIPT,
            timeout=30,
        )

    def _git(self, *args: str, check: bool = True, timeout: int = 120) -> CommandResult:
        return self.runner(["git", "-C", str(self.root), *args***REMOVED***, check=check, timeout=timeout)

    def _branch(self) -> str:
        branch = discover_local(self.root, self.runner).get("branch")
        if not branch:
            raise RuntimeError("local repository is detached or has no branch")
        return str(branch)

    def _ensure_clean(self) -> None:
        tracked_diff = self._git("diff", "--quiet", check=False, timeout=15)
        staged_diff = self._git("diff", "--cached", "--quiet", check=False, timeout=15)
        untracked = self._git("ls-files", "--others", "--exclude-standard", "--directory", check=False, timeout=15)
        if tracked_diff.returncode != 0 or staged_diff.returncode != 0 or untracked.stdout.strip():
            raise RuntimeError("local worktree is dirty; commit or stash changes first")

    def _remote_name(self) -> str:
        return "freebuff-sync"

    def _ensure_no_denied_tracked_files(self) -> None:
        denied = [item.path for item in self.classify() if item.git_tracked and item.category in {"ignored", "suspicious"***REMOVED******REMOVED***
        if denied:
            raise RuntimeError("tracked files are blocked by sync filters: " + ", ".join(denied[:20***REMOVED***))

    def push(self) -> dict[str, Any***REMOVED***:
        """Push the current branch without force and verify the remote ref."""
        branch = self._branch()
        self._ensure_clean()
        self._ensure_no_denied_tracked_files()
        remote = self.config.remote
        if not remote.bare_repo:
            raise ValueError("remote.bare_repo is required for push")
        with LocalLock(self.local_lock_path, "push", self.config.sync.lock_timeout_sec):
            result = self._git("push", self._remote_name(), f"{branch***REMOVED***:refs/heads/{branch***REMOVED***", timeout=120)
        return {"mode": "push", "branch": branch, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr***REMOVED***

    def pull(self) -> dict[str, Any***REMOVED***:
        """Fetch and fast-forward/merge remote changes without destructive reset."""
        branch = self._branch()
        self._ensure_clean()
        with LocalLock(self.local_lock_path, "pull", self.config.sync.lock_timeout_sec):
            self._git("fetch", self._remote_name(), branch, timeout=120)
            remote_ref = f"{self._remote_name()***REMOVED***/{branch***REMOVED***"
            merge = self._git("merge", "--ff-only", remote_ref, check=False, timeout=120)
            if merge.returncode != 0:
                raise RuntimeError(f"pull requires manual merge or has a conflict:\n{merge.stderr or merge.stdout***REMOVED***")
        return {"mode": "pull", "branch": branch, "head": self._git("rev-parse", "HEAD").stdout.strip()***REMOVED***

    def sync(self) -> dict[str, Any***REMOVED***:
        """Fetch, merge, push and verify a clean equal state."""
        branch = self._branch()
        self._ensure_clean()
        with LocalLock(self.local_lock_path, "sync", self.config.sync.lock_timeout_sec):
            self._git("fetch", self._remote_name(), branch, timeout=120)
            remote_ref = f"{self._remote_name()***REMOVED***/{branch***REMOVED***"
            merge = self._git("merge", remote_ref, check=False, timeout=120)
            if merge.returncode != 0:
                raise RuntimeError(f"sync conflict; resolve manually:\n{merge.stderr or merge.stdout***REMOVED***")
            self._git("push", self._remote_name(), f"{branch***REMOVED***:refs/heads/{branch***REMOVED***", timeout=120)
            head = self._git("rev-parse", "HEAD").stdout.strip()
        return {"mode": "sync", "branch": branch, "head": head, "clean": True***REMOVED***

    def status(self) -> dict[str, Any***REMOVED***:
        local = discover_local(self.root, self.runner)
        data: dict[str, Any***REMOVED*** = {"version": MODULE_VERSION, "local": local, "remote": self._remote_paths(), "config_path": str(self.config.config_path) if self.config.config_path else None***REMOVED***
        try:
            data["classifications"***REMOVED*** = {category: count for category, count in _counts(self.classify()).items()***REMOVED***
        except (FileNotFoundError, ValueError) as exc:
            data["classification_error"***REMOVED*** = str(exc)
        remote = self.config.remote
        if remote.ssh_alias:
            try:
                data["remote_probe"***REMOVED*** = ssh_probe(remote.ssh_alias, self.runner)
                if not remote.workspace_root:
                    data["remote_candidates"***REMOVED*** = ssh_candidates(remote.ssh_alias, self.runner)
            except Exception as exc:
                data["remote_error"***REMOVED*** = str(exc)
        return data

    def watch_once(self) -> dict[str, Any***REMOVED***:
        before = self.runner(["git", "-C", str(self.root), "status", "--porcelain", "--untracked-files=normal"***REMOVED***, check=False, timeout=15).stdout
        time.sleep(self.config.sync.watch_debounce_sec)
        after = self.runner(["git", "-C", str(self.root), "status", "--porcelain", "--untracked-files=normal"***REMOVED***, check=False, timeout=15).stdout
        result: dict[str, Any***REMOVED*** = {"changed": before != after, "before": before.splitlines(), "after": after.splitlines()***REMOVED***
        if before == after or not self.config.watch.auto_commit:
            return result
        self._ensure_no_denied_tracked_files()
        classifications = self.classify()
        blocked = [item.path for item in classifications if item.category in {"suspicious", "unknown"***REMOVED*** and item.path in after***REMOVED***
        if blocked:
            raise RuntimeError("watch blocked by unclassified files: " + ", ".join(blocked[:20***REMOVED***))
        self._git("add", "--all")
        staged = self._git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            return result
        self._git("commit", "-m", f"{self.config.watch.commit_prefix***REMOVED*** update workspace from Termux", timeout=120)
        result["committed"***REMOVED*** = True
        if self.config.watch.auto_push:
            result["push"***REMOVED*** = self.push()
        return result


def _counts(items: Iterable[FileClassification***REMOVED***) -> dict[str, int***REMOVED***:
    result: dict[str, int***REMOVED*** = {***REMOVED***
    for item in items:
        result[item.category***REMOVED*** = result.get(item.category, 0) + 1
    return result


def sqlite_backup(source: Path, destination: Path) -> None:
    """Create an integrity-checked SQLite backup atomically."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name***REMOVED***.{os.getpid()***REMOVED***.tmp")
    try:
        with sqlite3.connect(source) as source_db, sqlite3.connect(temporary) as destination_db:
            source_db.backup(destination_db)
            result = destination_db.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0***REMOVED*** != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {result!r***REMOVED***")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freebuff Git/SSH workspace synchronisation")
    parser.add_argument("mode", choices=("bootstrap", "push", "pull", "sync", "status", "watch"))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="allow bootstrap mutation")
    parser.add_argument("--yes", action="store_true", help="confirm non-interactive mutation")
    parser.add_argument("--dry-run", action="store_true", help="show bootstrap plan without mutation")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--once", action="store_true", help="run watch polling once")
    return parser


def _default_config_path(root: Path) -> Path:
    return root / ".freebuff" / "sync.yaml"


def main(argv: Sequence[str***REMOVED*** | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_path = args.config.resolve() if args.config else _default_config_path(Path.cwd().resolve())
        if not config_path.exists():
            raise ValueError(f"sync config not found: {config_path***REMOVED***; create .freebuff/sync.yaml")
        config = load_config(config_path)
        if args.non_interactive:
            from dataclasses ***REMOVED***place
            config = replace(config, sync=replace(config.sync, non_interactive=True))
        sync = FreebuffSync(config)
        if args.mode == "bootstrap":
            plan = sync.bootstrap(apply=args.apply and not args.dry_run, yes=args.yes)
            output = plan.to_dict()
        elif args.mode == "push":
            output = sync.push()
        elif args.mode == "pull":
            output = sync.pull()
        elif args.mode == "sync":
            output = sync.sync()
        elif args.mode == "status":
            output = sync.status()
        else:
            if args.once:
                output = sync.watch_once()
            else:
                print("freebuff-sync watch started; press Ctrl+C to stop", file=sys.stderr)
                while True:
                    sync.watch_once()
                    time.sleep(config.sync.watch_interval_sec)
        if args.mode != "watch" or args.once or args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2, default=_json_default))
        return EXIT_OK
    except LockBusy as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_LOCK
    except ValueError as exc:
        print(f"configuration error: {exc***REMOVED***", file=sys.stderr)
        return EXIT_CONFIG
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR
    except (OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
