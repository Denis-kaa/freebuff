"""Phase-based launch wrapper (анти-OOM) — wrapper.launch_and_wait.

Восстановлен v5.189.91 по контракту тестов tests_09/test_wrapper_phase.py.

Обёртка вокруг spawn freebuff CLI: launch() запускает процесс,
launch_and_wait() добавляет phase-based poll результата из .freebuff_result
с защитой от stale-файлов (mtime baseline) и single-instance blocker detection.

Proot autodetection (v5.73.0): _build_buffer_cmd определяет среду
(native Termux / inside-proot с rootfs loader / inside-proot без loader).
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from plugins_04.config import FREEBUFF_BINARY, PROOT_DISTRO

# ── Proot candidates ────────────────────────────────────────────
_ROOTFS_CANDIDATES = [
    Path("/rootfs"),
    Path("/data/data/com.termux/files/usr/var/lib/proot-distro/uuid-rootfs"),
]

_SINGLE_INSTANCE_MARKER = "Freebuff is already running"


# ═══════════════════════════════════════════════════════════════
# Proot detection
# ═══════════════════════════════════════════════════════════════

def _is_inside_proot() -> bool:
    """Check if we're running inside a proot environment."""
    # /proc/1/root is the classic proot indicator
    proc1 = Path("/proc/1/root")
    if proc1.exists():
        try:
            target = proc1.readlink()
            if target != "/":
                return True
        except OSError:
            pass
    # Alternative: check for PROOT env var
    if os.environ.get("PROOT_TMP_DIR"):
        return True
    return False


def _rootfs_loader_prefix() -> Optional[str]:
    """Find ld-linux loader in rootfs for direct glibc exec.

    Returns prefix string like:
        /rootfs/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1
        --library-path /rootfs/usr/lib/aarch64-linux-gnu
    or None if not found (fallback to direct exec).
    """
    for root in _ROOTFS_CANDIDATES:
        libdir = root / "usr" / "lib" / "aarch64-linux-gnu"
        loader = libdir / "ld-linux-aarch64.so.1"
        if loader.exists():
            return f"{loader} --library-path {libdir}"
    return None


def _proot_distro_login_available() -> bool:
    """Check if `proot-distro login` is available (native Termux)."""
    try:
        result = subprocess.run(
            ["proot-distro", "list"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _build_buffer_cmd(work_dir: Path) -> str:
    """Build the command string for launching freebuff in the right env.

    Priority:
      1. Inside proot with rootfs loader → ld-linux --library-path ...
      2. Inside proot without loader → direct exec (env -u LD_PRELOAD)
      3. Outside proot, proot-distro available → proot-distro login ubuntu
      4. Outside proot, no proot-distro → direct exec
    """
    bin_path = str(FREEBUFF_BINARY)
    cwd = str(work_dir)

    if _is_inside_proot():
        loader_prefix = _rootfs_loader_prefix()
        if loader_prefix:
            return f"env -u LD_PRELOAD {loader_prefix} {bin_path} --cwd {cwd}"
        else:
            return f"env -u LD_PRELOAD {bin_path} --cwd {cwd}"
    else:
        # Native Termux: always use proot-distro login
        return f"proot-distro login {PROOT_DISTRO} -- {bin_path} --cwd {cwd}"


# ═══════════════════════════════════════════════════════════════
# Result polling
# ═══════════════════════════════════════════════════════════════

def _wait_for_new_result(
    work_dir: Path,
    baseline_mtime: Optional[int],
    timeout: float = 300,
    poll_interval: float = 1.0,
) -> Optional[str]:
    """Poll .freebuff_result for a new result (mtime > baseline).

    Returns the result text, or None on timeout.
    """
    result_file = work_dir / ".freebuff_result"
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if result_file.exists():
            current_mtime = result_file.stat().st_mtime_ns
            if baseline_mtime is None or current_mtime > baseline_mtime:
                return result_file.read_text(encoding="utf-8")
        time.sleep(min(poll_interval, deadline - time.monotonic()))

    return None


# ═══════════════════════════════════════════════════════════════
# Launch
# ═══════════════════════════════════════════════════════════════

def launch(
    prompt: str,
    cwd: str,
    timeout: float,
    session_id: Optional[str] = None,
    model: str = "auto",
) -> Dict[str, Any]:
    """Spawn freebuff CLI process (non-blocking).

    Returns:
        {"success": bool, "session_id": str, "pid": int|None,
         "status": str, "cwd": str, "error": str|None}
    """
    work_dir = Path(cwd)
    session_id = session_id or f"sess_{int(time.time())}"

    cmd = _build_buffer_cmd(work_dir)

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "FREEBUFF_SESSION_ID": session_id, "FREEBUFF_MODEL": model},
        )
        return {
            "success": True,
            "session_id": session_id,
            "pid": proc.pid,
            "status": "launched",
            "cwd": str(work_dir),
        }
    except Exception as exc:
        return {
            "success": False,
            "session_id": session_id,
            "pid": None,
            "status": f"session_start failed: {exc}",
            "cwd": str(work_dir),
            "error": str(exc),
        }


def launch_and_wait(
    prompt: str,
    cwd: str,
    timeout: float,
    session_id: Optional[str] = None,
    model: str = "auto",
) -> Dict[str, Any]:
    """Phase-based launch with blocking wait for result.

    1. Snapshot .freebuff_result mtime (baseline) to detect stale files
    2. Spawn freebuff CLI
    3. If launch fails → immediate failed result (no polling)
    4. Poll .freebuff_result for new content (mtime > baseline)
    5. Check .freebuff_output_{session_id}.log for single-instance blocker
    """
    work_dir = Path(cwd)

    # Baseline mtime for stale detection
    result_file = work_dir / ".freebuff_result"
    baseline = result_file.stat().st_mtime_ns if result_file.exists() else None

    # Launch (uses session_id if provided, else generates one)
    info = launch(prompt, cwd, timeout, session_id=session_id, model=model)
    actual_sid = info["session_id"]

    if not info["success"]:
        return {
            "success": False,
            "result": None,
            "session_id": actual_sid,
            "error": info.get("error", info["status"]),
            "returncode": -1,
            "blocked_single_instance": False,
        }

    # Poll for result
    result = _wait_for_new_result(work_dir, baseline, timeout=timeout, poll_interval=0.5)

    if result is not None:
        return {
            "success": True,
            "result": result,
            "session_id": actual_sid,
            "error": None,
            "returncode": 0,
            "blocked_single_instance": False,
        }

    # Timeout — check for single-instance blocker in output log
    out_file = work_dir / f".freebuff_output_{actual_sid}.log"
    output_text = ""
    if out_file.exists():
        try:
            output_text = out_file.read_text(encoding="utf-8")
        except Exception:
            pass

    blocked = _SINGLE_INSTANCE_MARKER in output_text

    return {
        "success": False,
        "result": None,
        "session_id": actual_sid,
        "error": "single_instance_busy" if blocked else "timeout",
        "returncode": -1,
        "blocked_single_instance": blocked,
    }
