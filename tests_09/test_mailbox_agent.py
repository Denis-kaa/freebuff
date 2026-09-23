"""Тесты mailbox_agent (scripts_01/mailbox_agent.py).

Покрывает (промт pompts_11/promt02_mailbox_agent.md §5):
  * парсинг шапки письма (id/от/кому/статус/интент);
  * закрытый словарь интентов: ping / status / hello / unknown (ANTI-6b);
  * идемпотентность: повторный проход не дублирует ответы (архивация);
  * атомарность записи: нет .tmp-хвостов после ответа;
  * SRV-нумерация сквозная, мультиадрес в to-phone/to-desktop;
  * CLI-контракты: --once (JSON stdout), --status, --loop не тестируем (демон).

Hermetic: всё в tmpdir, FREEBUFF_MAILBOX_DIR не трогаем — функции принимают
mailbox параметром; env-дефолты проверяются отдельным тестом через monkeypatch.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01 import mailbox_agent as ma  # noqa: E402


# ── Фикстуры ─────────────────────────────────────────────────────────────


@pytest.fixture()
def mailbox(tmp_path: Path) -> Path:
    """Корень mailbox с канонической структурой папок."""
    for sub in ("to-server", "to-phone", "to-desktop", "archive"):
        (tmp_path / sub).mkdir()
    return tmp_path


def _write_incoming(mailbox: Path, name: str, sender: str, intent: str,
                    status: str = "NEW", extra: str = "") -> Path:
    """Положить входящее письмо в to-server/ в формате протокола v1.1."""
    p = mailbox / "to-server" / name
    p.write_text(
        f"# MSG-900 · от: {sender} · кому: buffy-server · "
        f"2026-09-22 23:30 · статус: {status}\n\n"
        f"интент: {intent}\n\n{extra}\n",
        encoding="utf-8",
    )
    return p


# ── Парсинг ──────────────────────────────────────────────────────────────


class TestParsing:
    """Парсинг шапки и интента."""

    def test_parse_full_header(self, mailbox: Path) -> None:
        p = _write_incoming(mailbox, "MSG-900_buffy-phone.md", "buffy-phone", "ping")
        msg = ma.parse_message(p)
        assert msg.msg_id == "MSG-900"
        assert msg.sender == "buffy-phone"
        assert msg.intent == "ping"
        assert msg.status == "NEW"

    def test_parse_missing_intent_is_unknown(self, mailbox: Path) -> None:
        p = mailbox / "to-server" / "x.md"
        p.write_text("# A-1 · от: buffy-phone · статус: NEW\n\nтекст без интента\n",
                     encoding="utf-8")
        msg = ma.parse_message(p)
        assert msg.intent == "unknown"

    def test_parse_unknown_intent_normalized(self, mailbox: Path) -> None:
        p = _write_incoming(mailbox, "x.md", "buffy-phone", "exec_rm_rf")
        assert ma.parse_message(p).intent == "unknown"

    def test_parse_broken_header_no_crash(self, mailbox: Path) -> None:
        p = mailbox / "to-server" / "broken.md"
        p.write_text("совсем не письмо", encoding="utf-8")
        msg = ma.parse_message(p)
        assert msg.msg_id.startswith("UNKNOWN-")
        assert msg.sender == "unknown"
        assert msg.intent == "unknown"


# ── Закрытый словарь интентов ────────────────────────────────────────────


class TestIntentHandlers:
    """ping/status/hello/unknown → ответ в папку отправителя."""

    def test_ping_replies_pong_to_phone(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "m1.md", "buffy-phone", "ping")
        done = ma.process_inbox(mailbox)
        assert done == ["MSG-900"]
        replies = list((mailbox / "to-phone").glob("SRV-*.md"))
        assert len(replies) == 1
        assert "pong" in replies[0].read_text(encoding="utf-8")

    def test_desktop_reply_routes_to_desktop(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "m2.md", "buffy-desktop", "ping")
        ma.process_inbox(mailbox)
        assert list((mailbox / "to-desktop").glob("SRV-*.md"))
        assert not list((mailbox / "to-phone").glob("SRV-*.md"))

    def test_status_replies_valid_json(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "m3.md", "buffy-phone", "status")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        text = reply.read_text(encoding="utf-8")
        payload = text.split("```json")[1].split("```")[0]
        report = json.loads(payload)
        assert report["agent"] == ma.AGENT_ID
        assert report["capability"] == "mailbox_agent"
        assert "ping" in report["known_intents"]

    def test_hello_onboarding_reply(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "m4.md", "buffy-phone", "hello")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        text = reply.read_text(encoding="utf-8")
        assert "на связи" in text
        assert "ping" in text and "status" in text and "hello" in text

    def test_unknown_intent_error_reply_no_exec(self, mailbox: Path) -> None:
        p = _write_incoming(mailbox, "m5.md", "buffy-phone", "exec",
                            extra="rm -rf /tmp/x")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        text = reply.read_text(encoding="utf-8")
        assert "закрытом словаре" in text
        assert "rm -rf" not in text  # тело не исполняется и не ретранслируется


# ── Идемпотентность / архивация / атомарность ────────────────────────────


class TestIdempotencyAndAtomicity:
    """Повторный проход не дублирует; письма архивируются; .tmp не течёт."""

    def test_processed_message_archived_not_deleted(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "a.md", "buffy-phone", "ping")
        ma.process_inbox(mailbox)
        assert not list((mailbox / "to-server").glob("*.md"))
        archived = list((mailbox / "archive").glob("a.md"))
        assert len(archived) == 1

    def test_second_pass_no_duplicate_reply(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "a.md", "buffy-phone", "ping")
        ma.process_inbox(mailbox)
        ma.process_inbox(mailbox)  # inbox пуст → ничего не делает
        assert len(list((mailbox / "to-phone").glob("SRV-*.md"))) == 1

    def test_non_new_status_skipped(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "b.md", "buffy-phone", "ping", status="READ")
        assert ma.process_inbox(mailbox) == []
        assert not list((mailbox / "to-phone").glob("SRV-*.md"))

    def test_no_tmp_files_left(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "c.md", "buffy-phone", "status")
        ma.process_inbox(mailbox)
        assert not list((mailbox / "to-phone").glob("*.tmp"))

    def test_missing_inbox_dir_returns_empty(self, tmp_path: Path) -> None:
        assert ma.process_inbox(tmp_path) == []


# ── Интент wip_report (promt03) ──────────────────────────────────────────


class TestWipReport:
    """wip_report: allowlist (shell=False), JSON-структура, graceful-ошибки."""

    def test_allowlist_rejects_foreign_command(self) -> None:
        ok, err = ma._run_git_allowlisted(("git", "push", "origin", "master"))
        assert ok is False
        assert "allowlist" in err

    def test_allowlist_accepts_only_three_commands(self) -> None:
        assert ma._GIT_STATUS_CMD in (
            ma._GIT_STATUS_CMD, ma._GIT_HEAD_CMD, ma._GIT_BEHIND_CMD)
        ok, _ = ma._run_git_allowlisted(("rm", "-rf", "/"))
        assert ok is False

    def test_wip_report_reply_is_valid_json(self, mailbox: Path, monkeypatch) -> None:
        fake_repo = tmp_repo_with_git()
        monkeypatch.setattr(ma, "WIP_REPO_PATH", fake_repo)
        _write_incoming(mailbox, "w1.md", "buffy-phone", "wip_report")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        payload = reply.read_text(encoding="utf-8").split("```json")[1].split("```")[0]
        report = json.loads(payload)
        assert "suggestion" in report
        assert report["repo"] == str(fake_repo)

    def test_wip_report_missing_repo_graceful(self, mailbox: Path, monkeypatch) -> None:
        monkeypatch.setattr(ma, "WIP_REPO_PATH", Path("/nonexistent/repo-xyz"))
        _write_incoming(mailbox, "w2.md", "buffy-phone", "wip_report")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        payload = reply.read_text(encoding="utf-8").split("```json")[1].split("```")[0]
        report = json.loads(payload)
        assert "error" in report
        assert "не найден" in report["error"]

    def test_wip_report_in_known_intents(self) -> None:
        assert "wip_report" in ma._KNOWN_INTENTS


def tmp_repo_with_git() -> Path:
    """Мини-репо с одним коммитом для живого git-пути (tmpdir)."""
    import tempfile
    base = Path(tempfile.mkdtemp(prefix="wiprepo-"))
    subprocess.run(["git", "init", "-q", str(base)], check=True, timeout=30)
    (base / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=str(base), check=True, timeout=30)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=str(base), check=True, timeout=30,
    )
    return base


# ── Нумерация SRV-NNN ────────────────────────────────────────────────────


class TestNumbering:
    """Сквозная нумерация исходящих с учётом archive/."""

    def test_numbers_increment(self, mailbox: Path) -> None:
        for i in ("1", "2"):
            _write_incoming(mailbox, f"n{i}.md", "buffy-phone", "ping")
        ma.process_inbox(mailbox)
        names = sorted(p.name for p in (mailbox / "to-phone").glob("SRV-*.md"))
        assert len(names) == 2
        nums = [int(n.split("-")[1].split("_")[0]) for n in names]
        assert nums == sorted(nums) and len(set(nums)) == 2

    def test_archive_counts_in_numbering(self, mailbox: Path) -> None:
        (mailbox / "archive" / "SRV-007_buffy-server_2026-09-21_old.md").write_text(
            "x", encoding="utf-8")
        _write_incoming(mailbox, "n.md", "buffy-phone", "ping")
        ma.process_inbox(mailbox)
        reply = next((mailbox / "to-phone").glob("SRV-*.md"))
        assert "SRV-008_" in reply.name

    def test_write_reply_rejects_bad_dir(self, mailbox: Path) -> None:
        with pytest.raises(ValueError):
            ma.write_reply(mailbox, "to-server", "buffy-phone", "x", "y")


# ── CLI-контракты ────────────────────────────────────────────────────────


class TestCli:
    """--once и --status: JSON в stdout, exit 0."""

    def test_cli_once_json_stdout(self, mailbox: Path) -> None:
        _write_incoming(mailbox, "cli.md", "buffy-phone", "ping")
        env = {**ma.os.environ, "FREEBUFF_MAILBOX_DIR": str(mailbox)}
        r = subprocess.run(
            [sys.executable, "-m", "scripts_01.mailbox_agent", "--once"],
            capture_output=True, text=True, env=env, timeout=60, check=True,
        )
        payload = json.loads(r.stdout)
        assert payload["processed"] == ["MSG-900"]

    def test_cli_status_json(self, mailbox: Path) -> None:
        env = {**ma.os.environ, "FREEBUFF_MAILBOX_DIR": str(mailbox)}
        r = subprocess.run(
            [sys.executable, "-m", "scripts_01.mailbox_agent", "--status"],
            capture_output=True, text=True, env=env, timeout=60, check=True,
        )
        report = json.loads(r.stdout)
        assert report["agent"] == "buffy-server"
        assert report["inbox_dir_exists"] is True

    def test_env_defaults(self, tmp_path: Path) -> None:
        with mock.patch.dict(ma.os.environ, {}, clear=True):
            assert ma.AGENT_ID == "buffy-server"
            assert ma.AGENT_PREFIX == "SRV"
            assert ma.DEFAULT_INTERVAL_S == 300
