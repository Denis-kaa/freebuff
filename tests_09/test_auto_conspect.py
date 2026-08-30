"""Tests for scripts_01/auto_conspect.py CLI behavior."""
import os
import subprocess
import sys
}

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts_01.context_manager import ContextManager


class TestAutoConspectCLI:
    """Интеграционные тесты auto_conspect CLI."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def _run_auto_conspect(self, project_root: Path, workspace: Path, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["FREEBUFF_ROOT"] = str(workspace)
        return subprocess.run(
            [sys.executable, str(project_root / "scripts_01" / "auto_conspect.py"), *args],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
        )

    def test_no_active_sessions_exits_cleanly(self, project_root, tmp_path):
        result = self._run_auto_conspect(project_root, tmp_path)
        assert result.returncode == 0, result.stderr
        assert "No active sessions" in result.stdout

    def test_processes_active_session(self, project_root, tmp_path):
        # Create necessary directories and start a session in-process
        for sub in ["data", "sessions_15", "context_12/checkpoints", "context_12/summaries"]:
            (tmp_path / sub).mkdir(parents=True, exist_ok=True)

        cm = ContextManager(str(tmp_path))
        snap = cm.start_session(project="test", topic="auto-conspect test")
        cm.add_message(snap.session_id, "user", "hello", token_count=2)

        result = self._run_auto_conspect(project_root, tmp_path, snap.session_id)
        assert result.returncode == 0, result.stderr
        assert "Conspecting session" in result.stdout

        summaries = list((tmp_path / "context_12" / "summaries").glob("*.md"))
        assert len(summaries) >= 1

    def test_demo_flag_runs_demo(self, project_root, tmp_path):
        env = os.environ.copy()
        env["FREEBUFF_ROOT"] = str(tmp_path)
        result = subprocess.run(
            [sys.executable, str(project_root / "scripts_01" / "demo_auto_conspect.py")],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert "Conspect saved to" in result.stdout
