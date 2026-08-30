"""Tests for src_06/workers/lightpanda_worker.py."""
from __future__ import annotations

import os
import subprocess
import sys
from unittest import mock

import pytest

FREEBUFF_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FREEBUFF_ROOT)

from src_06.workers.lightpanda_worker import LightpandaWorker


class _CompletedProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_resolve_binary_prefers_wrapper(tmp_path) -> None:
    workspace = tmp_path / "freebuff"
    tools = workspace / ".tools"
    tools.mkdir(parents=True)
    wrapper = tools / "lightpanda"
    wrapper.write_text("#!/bin/bash\necho lightpanda")
    wrapper.chmod(0o755)

    worker = LightpandaWorker(workspace_root=str(workspace))
    assert worker._binary_path == str(wrapper)


def test_resolve_binary_fallback() -> None:
    worker = LightpandaWorker(workspace_root="/nonexistent")
    assert worker._binary_path == "/usr/local/bin/lightpanda"


@mock.patch("subprocess.run")
def test_execute_agent_task(mock_run: mock.MagicMock) -> None:
    mock_run.return_value = _CompletedProcess(stdout="done", returncode=0)
    worker = LightpandaWorker(workspace_root="/tmp")
    result = worker.execute_agent_task("search github")

    assert result.success is True
    assert result.data == "done"
    assert result.error is None
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "agent" in args
    assert "--task" in args
    assert "search github" in args


@mock.patch("subprocess.run")
def test_run_script_missing_file(mock_run: mock.MagicMock) -> None:
    worker = LightpandaWorker(workspace_root="/tmp")
    result = worker.run_script("/missing/script.js")
    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.lower()
    mock_run.assert_not_called()


@mock.patch("subprocess.run")
def test_dump_url_invalid_format(mock_run: mock.MagicMock) -> None:
    worker = LightpandaWorker(workspace_root="/tmp")
    result = worker.dump_url("https://example.com", output_format="invalid")
    assert result.success is False
    assert result.error is not None
    assert "Unsupported output format" in result.error
    mock_run.assert_not_called()


@mock.patch("subprocess.run")
def test_binary_not_found(mock_run: mock.MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError("No such file")
    worker = LightpandaWorker(binary_path="/missing/lightpanda")
    result = worker.execute_agent_task("x")
    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.lower()


@mock.patch("subprocess.run")
def test_timeout(mock_run: mock.MagicMock) -> None:
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["lightpanda"], timeout=1)
    worker = LightpandaWorker(binary_path="/usr/local/bin/lightpanda")
    result = worker.execute_agent_task("x", timeout=1)
    assert result.success is False
    assert result.error is not None
    assert "timed out" in result.error.lower()


@mock.patch("subprocess.Popen")
def test_cdp_server_lifecycle(mock_popen: mock.MagicMock) -> None:
    proc = mock.MagicMock()
    mock_popen.return_value = proc
    worker = LightpandaWorker(workspace_root="/tmp")

    start = worker.serve_cdp()
    assert start.success is True
    assert "9222" in start.data
    mock_popen.assert_called_once()

    worker.stop_cdp()
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once()
