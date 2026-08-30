"""Regression tests for phase-based launch (анти-OOM) — wrapper.launch_and_wait.

Covers: stale-.freebuff_result protection (mtime baseline), success result
read-back, launch failure, timeout. No real Buffy run (launch is monkeypatched).
"""
from __future__ import annotations

import time

import pytest

import freebuff_plugin_03.wrapper as wrapper


@pytest.fixture
def work_dir(tmp_path):
    return tmp_path


def _fake_launch_success(prompt, cwd, timeout, session_id=None, model="auto"):
    return {
        "success": True, "session_id": "test_sid", "pid": 1234,
        "status": "launched", "cwd": str(cwd),
    }


def _fake_launch_failure(prompt, cwd, timeout, session_id=None, model="auto"):
    return {"success": False, "session_id": "", "pid": None,
            "status": "session_start failed: boom", "error": "boom"}


def test_launch_and_wait_returns_result(monkeypatch, work_dir):
    """Успешный phase-based запуск: результат читается из .freebuff_result."""
    monkeypatch.setattr(wrapper, "launch", _fake_launch_success)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: "TASK DONE")

    result = wrapper.launch_and_wait(
        prompt="test", cwd=str(work_dir), timeout=5,
    )
    assert result["success"] is True
    assert result["result"] == "TASK DONE"
    assert result["session_id"] == "test_sid"
    assert result["error"] is None


def test_launch_and_wait_launch_failure(monkeypatch, work_dir):
    """Провал launch() → немедленный failed-результат без опроса."""
    monkeypatch.setattr(wrapper, "launch", _fake_launch_failure)
    called = {"poll": False}

    def _no_poll(*a, **k):
        called["poll"] = True
        return None

    monkeypatch.setattr(wrapper, "_wait_for_new_result", _no_poll)
    result = wrapper.launch_and_wait(prompt="test", cwd=str(work_dir), timeout=5)
    assert result["success"] is False
    assert "boom" in result["error"]
    assert called["poll"] is False


def test_launch_and_wait_timeout(monkeypatch, work_dir):
    """Таймаут опроса → failed с диагностикой (без исключения)."""
    monkeypatch.setattr(wrapper, "launch", _fake_launch_success)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: None)

    result = wrapper.launch_and_wait(prompt="test", cwd=str(work_dir), timeout=5)
    assert result["success"] is False
    assert "timeout" in result["error"].lower()
    assert result["returncode"] == -1


def test_launch_and_wait_detects_single_instance_blocker(monkeypatch, work_dir):
    """Single-instance blocker (v5.88.0): 'already running' маркер → blocked.

    freebuff допускает один инстанс: если живая сессия занимает его, spawned
    экземпляр печатает 'Freebuff is already running' + 'Take over'/'Exit' и не
    стартует → monitor ждёт → timeout. Wrapper должен пометить результат
    blocked_single_instance=True (для deferral), а не просто 'timeout'.
    """
    monkeypatch.setattr(wrapper, "launch", _fake_launch_success)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: None)

    out_file = work_dir / ".freebuff_output_test_sid.log"
    out_file.write_text(
        "Freebuff is already running. Only one freebuff instance is allowed at a time.\n"
        "Take over / Exit",
        encoding="utf-8",
    )

    result = wrapper.launch_and_wait(prompt="test", cwd=str(work_dir), timeout=5)
    assert result["success"] is False
    assert result["blocked_single_instance"] is True
    assert "single_instance_busy" in result["error"]
    assert result["returncode"] == -1


def test_launch_and_wait_blocked_only_when_no_result(monkeypatch, work_dir):
    """Маркер в выводе + результат ЕСТЬ → НЕ блокер (code-reviewer edge case).

    Если .freebuff_result появился — инстанс реально выполнил задачу (не мог
    быть заблокирован); маркер в выводе может быть просто процитирован в
    контексте задачи. blocked только на timeout-пути.
    """
    monkeypatch.setattr(wrapper, "launch", _fake_launch_success)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: "TASK DONE")

    out_file = work_dir / ".freebuff_output_test_sid.log"
    out_file.write_text(
        "Some task quoted: Freebuff is already running... but task completed",
        encoding="utf-8",
    )

    result = wrapper.launch_and_wait(prompt="test", cwd=str(work_dir), timeout=5)
    assert result["success"] is True
    assert result["result"] == "TASK DONE"
    assert result["blocked_single_instance"] is False
    assert result["error"] is None


def test_launch_and_wait_not_blocked_on_clean_output(monkeypatch, work_dir):
    """Обычный timeout БЕЗ single-instance маркера → blocked=False."""
    monkeypatch.setattr(wrapper, "launch", _fake_launch_success)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: None)

    out_file = work_dir / ".freebuff_output_test_sid.log"
    out_file.write_text("Connecting...\n\x1b[2J no marker here", encoding="utf-8")

    result = wrapper.launch_and_wait(prompt="test", cwd=str(work_dir), timeout=5)
    assert result["success"] is False
    assert result["blocked_single_instance"] is False
    assert "timeout" in result["error"].lower()


def test_launch_and_wait_forwards_model_to_launch(monkeypatch, work_dir):
    """model из launch_and_wait пробрасывается в launch (→ monitor.sh) (v5.88.0)."""
    seen: dict = {}

    def _fake_launch(prompt, cwd, timeout, session_id=None, model="auto"):
        seen.update(prompt=prompt, model=model)
        return {"success": True, "session_id": "sid", "pid": 1, "status": "launched"}

    monkeypatch.setattr(wrapper, "launch", _fake_launch)
    monkeypatch.setattr(wrapper, "_wait_for_new_result", lambda *a, **k: "OK")

    result = wrapper.launch_and_wait(
        prompt="p", cwd=str(work_dir), timeout=5, model="3",
    )
    assert result["success"] is True
    assert seen.get("model") == "3"
    assert seen.get("prompt") == "p"


def test_wait_for_new_result_ignores_stale_file(work_dir):
    """Стейл .freebuff_result (существующий ДО запуска) не считается результатом."""
    result_file = work_dir / ".freebuff_result"
    result_file.write_text("OLD RESULT", encoding="utf-8")
    baseline = result_file.stat().st_mtime_ns

    # Нового результата нет → после короткого таймаута None
    assert wrapper._wait_for_new_result(
        work_dir, baseline, timeout=1, poll_interval=0.1,
    ) is None

    # Пишем новый результат (mtime новее) → читается
    time.sleep(0.02)
    result_file.write_text("NEW RESULT", encoding="utf-8")
    got = wrapper._wait_for_new_result(
        work_dir, baseline, timeout=2, poll_interval=0.05,
    )
    assert got == "NEW RESULT"


def test_wait_for_new_result_no_baseline_accepts_existing(work_dir):
    """Без baseline (файла не было до запуска) существующий файл — результат."""
    result_file = work_dir / ".freebuff_result"
    result_file.write_text("RESULT", encoding="utf-8")
    got = wrapper._wait_for_new_result(
        work_dir, None, timeout=2, poll_interval=0.05,
    )
    assert got == "RESULT"


# ── Proot autodetection (v5.73.0) ──────────────────────────────

def test_build_buffer_cmd_uses_direct_exec_when_inside_proot(monkeypatch, work_dir):
    """Inside-proot БЕЗ rootfs loader: proot_cmd = `{bin] --cwd {cwd]` (fallback)."""
    from freebuff_plugin_03.config import FREEBUFF_BINARY
    monkeypatch.setattr(wrapper, "_is_inside_proot", lambda: True)
    monkeypatch.setattr(wrapper, "_rootfs_loader_prefix", lambda: None)
    cmd = wrapper._build_buffer_cmd(work_dir)
    # direct-exec fallback: тот же glibc-бинарь → тоже снимаем LD_PRELOAD,
    # иначе Termux bionic exec-shim ломает загрузку (libc.so exit 127)
    assert cmd.startswith("env -u LD_PRELOAD "), f"got: {cmd!r}"
    assert str(FREEBUFF_BINARY) in cmd
    assert "proot-distro login" not in cmd
    assert str(work_dir) in cmd


def test_build_buffer_cmd_uses_rootfs_loader_when_inside_proot(monkeypatch, work_dir):
    """Inside-proot С rootfs loader (v5.88.0 fix): cmd = loader-prefix + bin + --cwd.

    Регрессия на live-баг: direct-exec glibc-бинаря падал с
    'libc.so: cannot open shared object file' (exit 127); через
    `ld-linux-aarch64.so.1 --library-path {libdir}` бинарь линкуется.
    """
    from freebuff_plugin_03.config import FREEBUFF_BINARY
    monkeypatch.setattr(wrapper, "_is_inside_proot", lambda: True)
    monkeypatch.setattr(
        wrapper,
        "_rootfs_loader_prefix",
        lambda: "/rootfs/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 --library-path /rootfs/usr/lib/aarch64-linux-gnu",
    )
    cmd = wrapper._build_buffer_cmd(work_dir)
    # Termux LD_PRELOAD (libtermux-exec-ld-preload.so) ломает glibc loader → снимаем
    assert cmd.startswith("env -u LD_PRELOAD "), f"got: {cmd!r}"
    assert "ld-linux-aarch64.so.1 --library-path" in cmd, f"got: {cmd!r}"
    assert str(FREEBUFF_BINARY) in cmd
    assert "proot-distro login" not in cmd
    assert str(work_dir) in cmd


def test_rootfs_loader_prefix_found_when_loader_exists(monkeypatch, tmp_path):
    """_rootfs_loader_prefix: loader найден в usr/lib/aarch64-linux-gnu → префикс."""
    root = tmp_path / "rootfs"
    libdir = root / "usr/lib/aarch64-linux-gnu"
    libdir.mkdir(parents=True)
    loader = libdir / "ld-linux-aarch64.so.1"
    loader.write_text("# fake loader", encoding="utf-8")
    monkeypatch.setattr(wrapper, "_ROOTFS_CANDIDATES", [root])

    prefix = wrapper._rootfs_loader_prefix()
    assert prefix is not None
    assert str(loader) in prefix
    assert f"--library-path {libdir}" in prefix


def test_rootfs_loader_prefix_none_when_missing(monkeypatch, tmp_path):
    """_rootfs_loader_prefix: loader нигде не найден → None (fallback direct-exec)."""
    empty_root = tmp_path / "empty"
    empty_root.mkdir(parents=True)
    monkeypatch.setattr(wrapper, "_ROOTFS_CANDIDATES", [empty_root])
    assert wrapper._rootfs_loader_prefix() is None


def test_build_buffer_cmd_uses_proot_login_when_outside(monkeypatch, work_dir):
    """Native Termux: proot_cmd = `proot-distro login ubuntu -- {bin] --cwd {cwd]`."""
    monkeypatch.setattr(wrapper, "_is_inside_proot", lambda: False)
    cmd = wrapper._build_buffer_cmd(work_dir)
    assert "proot-distro login" in cmd
    assert "ubuntu" in cmd  # PROOT_DISTRO default
    assert " -- " in cmd


def test_proot_distro_login_available_false_on_filenotfound(monkeypatch):
    """`proot-distro` бинарь отсутствует → False (мы внутри proot)."""
    import subprocess as sp

    def _raise(*a, **k):
        raise FileNotFoundError("proot-distro")

    monkeypatch.setattr(sp, "run", _raise)
    assert wrapper._proot_distro_login_available() is False


def test_proot_distro_login_available_true_when_list_succeeds(monkeypatch):
    """`proot-distro list` возвращает 0 → True (native Termux)."""
    class _Proc:
        returncode = 0
        stdout = "ubuntu installed\n"
        stderr = ""

    import subprocess as sp
    monkeypatch.setattr(sp, "run", lambda *a, **k: _Proc())
    assert wrapper._proot_distro_login_available() is True
