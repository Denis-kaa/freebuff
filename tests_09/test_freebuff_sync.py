from __future__ import annotations

import json
import sqlite3
}
from typing import Any

import pytest

from scripts_01.freebuff_sync import (
    EXIT_CONFIG,
    FileClassifier,
    FilterConfig,
    FreebuffSync,
    LocalLock,
    LockBusy,
    REMOTE_PROBE_SCRIPT,
    SyncConfig,
    CommandResult,
    load_config,
    main,
    parse_probe,
    sqlite_backup,
)


class FakeRunner:
    def __init__(self, outputs: dict[tuple[str, ...], CommandResult] | None = None):
        self.calls: list[tuple[str, ...]] = []
        self.outputs = outputs or {}

    def __call__(self, argv: Any, **kwargs: Any) -> CommandResult:
        key = tuple(str(item) for item in argv)
        self.calls.append(key)
        if key in self.outputs:
            return self.outputs[key]
        if key[:3] == ("git", "-C", str(self.root)) if hasattr(self, "root") else False:
            pass
        if "rev-parse" in key and "--show-toplevel" in key:
            return CommandResult(key, 0, str(self.root) + "\n", "")
        if "symbolic-ref" in key:
            return CommandResult(key, 0, "main\n", "")
        if "rev-parse" in key and key[-1] == "HEAD":
            return CommandResult(key, 0, "abc123\n", "")
        if "status" in key:
            return CommandResult(key, 0, "", "")
        if key[:2] == ("git", "-C") and key[-1] == "ls-files":
            return CommandResult(key, 0, "AGENTS.md\nBUFFY.md\ncore_02/app.py\n", "")
        return CommandResult(key, 0, "", "")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "freebuff"
    root.mkdir()
    (root / "AGENTS.md").write_text("rules", encoding="utf-8")
    (root / "BUFFY.md").write_text("manifest", encoding="utf-8")
    (root / "core_02").mkdir()
    (root / "core_02" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "scripts_01").mkdir()
    (root / "projects_17").mkdir()
    return root


def test_config_rejects_relative_remote_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absolute path"):
        SyncConfig.from_mapping({"remote": {"workspace_root": "relative"}})


def test_config_rejects_overlapping_remote_paths() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        SyncConfig.from_mapping(
            {
                "remote": {
                    "workspace_root": "/srv/freebuff",
                    "worktree": "/srv/freebuff",
                    "bare_repo": "/srv/freebuff/.sync.git",
                }
            }
        )


def test_classifier_hard_denies_secret_cache_archive_and_legacy(tmp_path: Path) -> None:
    root = tmp_path / "freebuff"
    root.mkdir()
    (root / "AGENTS.md").write_text("x", encoding="utf-8")
    files = {
        ".env": "SECRET=1",
        "notes.log": "log",
        "bundle.tar.gz": "archive",
        "core" + "/legacy.py": "legacy",
        ".freebuff_result": "{]",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    classifier = FileClassifier(root, FilterConfig())
    result = {item.path: item for item in classifier.scan()}
    assert result[".env"].category == "ignored"
    assert result["notes.log"].category == "ignored"
    assert result["bundle.tar.gz"].category == "ignored"
    assert result["core/legacy.py"].category == "ignored"
    assert result[".freebuff_result"].category == "ignored"


def test_classifier_runtime_is_opt_in(tmp_path: Path) -> None:
    root = tmp_path / "freebuff"
    root.mkdir()
    runtime = root / "data_13"
    runtime.mkdir()
    (runtime / "forge_registry.yaml").write_text("projects: {)\n", encoding="utf-8")
    (runtime / "context.db").write_bytes(b"not sqlite")
    result = {item.path: item for item in FileClassifier(root, FilterConfig()).scan()}
    assert result["data_13/forge_registry.yaml"].category == "unknown"
    assert result["data_13/context.db"].category == "ignored"


def test_classifier_explicit_runtime_allowlist(tmp_path: Path) -> None:
    root = tmp_path / "freebuff"
    root.mkdir()
    runtime = root / "data_13"
    runtime.mkdir()
    (runtime / "forge_registry.yaml").write_text("projects: {)\n", encoding="utf-8")
    config = FilterConfig(runtime_data=True)
    result = {item.path: item for item in FileClassifier(root, config).scan()}
    assert result["data_13/forge_registry.yaml"].category == "included"


def test_parse_probe_rejects_duplicates_and_bad_protocol() -> None:
    with pytest.raises(ValueError, match="protocol"):
        parse_probe("protocol=2\nhome=/home/u\n")
    with pytest.raises(ValueError, match="invalid"):
        parse_probe("protocol=1\nhome=/home/u\nprotocol=1\n")


def test_parse_probe_accepts_versioned_contract() -> None:
    result = parse_probe("protocol=1\nhome=/home/u\ngit=/usr/bin/git\n")
    assert result["protocol"] == "1"
    assert result["home"] == "/home/u"


def test_ssh_probe_uses_argv_and_fixed_probe_script() -> None:
    calls: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def runner(argv: Any, **kwargs: Any) -> CommandResult:
        calls.append((tuple(argv), kwargs))
        return CommandResult(tuple(argv), 0, "protocol=1\nhome=/home/u\ngit=/usr/bin/git\n", "")

    from scripts_01.freebuff_sync import ssh_probe

    assert ssh_probe("wimp", runner)["protocol"] == "1"
    argv, kwargs = calls[0]
    assert argv[:5] == ("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10")
    assert argv[-3:] == ("sh", "-s", "--")
    assert kwargs["input_text"] == REMOTE_PROBE_SCRIPT


def test_dry_run_bootstrap_is_non_mutating(workspace: Path, tmp_path: Path) -> None:
    config = SyncConfig.from_mapping(
        {
            "local": {"workspace_root": str(workspace)},
            "remote": {
                "ssh_alias": "wimp",
                "workspace_root": "/srv/freebuff",
                "bare_repo": "/srv/.freebuff-sync.git",
                "worktree": "/srv/freebuff",
            },
            "filters": {"unknown_policy": "exclude-and-report"},
            "logging": {"external_log_dir": str(tmp_path / "logs")},
        },
        tmp_path / "sync.yaml",
    )
    runner = FakeRunner()
    runner.root = workspace
    sync = FreebuffSync(config, runner)
    plan = sync.bootstrap(probe={"protocol": "1", "home": "/home/u", "git": "/usr/bin/git"})
    assert plan.dry_run is True
    assert plan.paths["bare_repo"] == "/srv/.freebuff-sync.git"
    assert any("create/verify remote bare repository" in item for item in plan.actions)
    assert not any(call[0] == "ssh" and "init" in call for call in runner.calls)
    reports = list((tmp_path / "logs" / "runs").glob("*.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["dry_run"] is True


def test_local_lock_is_exclusive(tmp_path: Path) -> None:
    path = tmp_path / "sync.lock"
    with LocalLock(path, "test"):
        with pytest.raises(LockBusy):
            with LocalLock(path, "second"):
                pass
    assert not path.exists()


def test_sqlite_backup_is_integrity_checked(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"
    with sqlite3.connect(source) as db:
        db.execute("create table items (id integer primary key, value text)")
        db.execute("insert into items(value) values ('ok')")
        db.commit()
    sqlite_backup(source, destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("select value from items").fetchone() == ("ok",)


def test_cli_missing_config_returns_config_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["bootstrap", "--dry-run"]) == EXIT_CONFIG
    assert "sync config not found" in capsys.readouterr().err


def test_config_yaml_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "sync.yaml"
    config_path.write_text(
        "version: 1\nremote:\n  ssh_alias: wimp\n  workspace_root: /srv/freebuff\n  bare_repo: /srv/.sync.git\n  worktree: /srv/freebuff\nfilters:\n  runtime_data: true\n  sqlite_allowlist:\n    - data_13/context.db\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.remote.ssh_alias == "wimp"
    assert config.filters.runtime_data is True
    assert config.filters.sqlite_allowlist == ("data_13/context.db",)
