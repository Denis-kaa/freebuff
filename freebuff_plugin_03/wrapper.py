"""
Freebuff Wrapper — phase-based запуск Codebuff CLI внутри proot-distro.

Phase-based (анти-OOM):
  Фаза 1: Python стартует сессию → PID-файл → завершается (память freed)
  Фаза 2: Codebuff работает один (единственный тяжёлый процесс)
  Фаза 3: monitor.sh (bash, <1MB) ждёт завершения → Python session_end → выход

Режимы:
  launch(prompt, cwd) — phase-based, Python завершается сразу
  synchronous_oneshot(prompt, cwd) — старый синхронный режим (для отладки)
"""

from __future__ import annotations

import os
***REMOVED***
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
***REMOVED***
from typing import Optional

from freebuff_plugin_03.config import (
    FREEBUFF_BINARY,
    FREEBUFF_ROOT,
    PROOT_DISTRO,
)

# ── OOM Protection ───────────────────────────────────────────

_OOM_SCRIPT = FREEBUFF_ROOT / "scripts_01" / "oom_protect.sh"


def _run_oom_protection() -> None:
    """Запускает OOM protection перед запуском Codebuff.
    Убивает старые freebuff, чистит tmux, проверяет память.
    """
    if _OOM_SCRIPT.exists():
        try:
            result = subprocess.run(
                ["bash", str(_OOM_SCRIPT), "--check"***REMOVED***,
                timeout=30,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"⚠️ OOM protection предупреждение: {result.stdout.strip()***REMOVED***", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("⚠️ OOM protection timeout (30s) — продолжаю без очистки", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ OOM protection error: {e***REMOVED***", file=sys.stderr)

# ── ANSI / управляющие последовательности ─────────────────────

_ANSI_STRIP = re.compile(r"\x1b\[[0-9;***REMOVED****[a-zA-Z***REMOVED***|\x1b\***REMOVED***.*?(\x1b\\|\x07)|\x1b[\[\***REMOVED***()#***REMOVED***")
_TERMINFO_STRIP = re.compile(r"\x1b[<>***REMOVED***|[\x00-\x08\x0b\x0c\x0e-\x1f***REMOVED***")
_ERASE_LINE = re.compile(r"\x1b\[[0-9***REMOVED****[JK***REMOVED***|\x1b\[[0-9;***REMOVED****[Hf***REMOVED***")
_SCREEN_ERASE = re.compile(r"\x1b\[2J\x1b\[H")
_CONTINUOUS_DOTS = re.compile(r"Connecting…+")
_PROGRESS_BARS = re.compile(r"█+[░***REMOVED****|●+[○***REMOVED****|[\d***REMOVED***+%")

def clean_tui_output(text: str) -> str:
    """Очищает вывод TUI от управляющих последовательностей."""
    text = _SCREEN_ERASE.sub("", text)
    text = _ERASE_LINE.sub("", text)
    text = _ANSI_STRIP.sub("", text)
    text = _TERMINFO_STRIP.sub("", text)
    text = _CONTINUOUS_DOTS.sub("", text)
    text = _PROGRESS_BARS.sub("", text)
    lines = [l for l in text.split("\n") if l.strip()***REMOVED***
    return "\n".join(lines)


# ── PID-файлы (сессия) ────────────────────────────────────────

_SESSION_DIR = Path(os.environ.get(
    "PREFIX", "/data/data/com.termux/files/usr"
)) / "tmp" / ".freebuff_plugin"


def _ensure_session_dir() -> None:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)


def save_pid_file(sid: str, pid: int, cwd: str) -> str:
    """
    Сохраняет информацию о запущенном процессе Codebuff.

    Returns: путь к PID-файлу.
    """
    _ensure_session_dir()
    pid_file = _SESSION_DIR / f"pid_{sid***REMOVED***"
    pid_file.write_text(
        f"{pid***REMOVED***\n{sid***REMOVED***\n{cwd***REMOVED***\n",
        encoding="utf-8",
    )
    return str(pid_file)


def read_pid_file(sid: str) -> dict | None:
    """Читает PID-файл сессии."""
    pid_file = _SESSION_DIR / f"pid_{sid***REMOVED***"
    if not pid_file.exists():
        return None
    lines = pid_file.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) < 3:
        return None
    return {
        "pid": int(lines[0***REMOVED***),
        "sid": lines[1***REMOVED***,
        "cwd": lines[2***REMOVED***,
    ***REMOVED***


def remove_pid_file(sid: str) -> None:
    """Удаляет PID-файл."""
    pid_file = _SESSION_DIR / f"pid_{sid***REMOVED***"
    if pid_file.exists():
        pid_file.unlink()


def list_active_pids() -> list[dict***REMOVED***:
    """Список всех активных PID-файлов."""
    _ensure_session_dir()
    results = [***REMOVED***
    for f in sorted(_SESSION_DIR.glob("pid_*")):
        lines = f.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) >= 3:
            results.append({
                "pid": int(lines[0***REMOVED***),
                "sid": lines[1***REMOVED***,
                "cwd": lines[2***REMOVED***,
            ***REMOVED***)
    return results


# ── AGENTS.md ─────────────────────────────────────────────────

def _make_agents_md(cwd: Path, prompt: str, session_id: str) -> Path:
    """Создаёт временный AGENTS.md с задачей."""
    content = f"""# Freebuff Plugin Session

Session ID: {session_id***REMOVED***
Created: {datetime.now(timezone.utc).isoformat()***REMOVED***

## Task

{prompt***REMOVED***

## Instructions

1. Выполни задачу выше.
2. После завершения задачи напиши результат в файл .freebuff_result
3. Не спрашивай подтверждения — просто делай.
4. Используй инструменты по необходимости.
5. Когда закончишь — сохрани результат и завершись.
"""
    agents_path = cwd / "AGENTS.md"
    agents_path.write_text(content, encoding="utf-8")
    return agents_path


def _wait_for_result(cwd: Path, timeout: int = 300, poll_interval: float = 2.0) -> str | None:
    """Ждёт появления .freebuff_result."""
    result_file = cwd / ".freebuff_result"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if result_file.exists():
            return result_file.read_text(encoding="utf-8")
        time.sleep(poll_interval)
    return None


# ═══════════════════════════════════════════════════════════════
# Phase-based launch (анти-OOM)
# ═══════════════════════════════════════════════════════════════

def launch(
    prompt: str,
    cwd: str | Path | None = None,
    timeout: int = 300,
    session_id: str | None = None,
) -> dict:
    """
    Phase-based запуск freebuff с передачей промпта через tmux.

    Фаза 1: Python — старт сессии → tmux с Codebuff → отправка промпта → Python exit
    Фаза 2: Codebuff обрабатывает задачу (один тяжёлый процесс)
    Фаза 3: monitor.sh ждёт → убивает tmux → Python session_end → Python exit

    Args:
        prompt: Текст задачи.
        cwd: Рабочая директория.
        timeout: Таймаут в секундах.
        session_id: ID сессии.

    Returns:
        dict: {success, session_id, pid, status***REMOVED***
    """
    from freebuff_plugin_03.bridge import session_start

    sid = session_id or uuid.uuid4().hex[:8***REMOVED***
    work_dir = Path(cwd) if cwd else Path.cwd()
    work_dir.mkdir(parents=True, exist_ok=True)

    # OOM Protection: убиваем старые freebuff перед запуском
    _run_oom_protection()

    # Фаза 1: Старт сессии
    try:
        sid = session_start(topic=prompt[:80***REMOVED***)
    except Exception as e:
        return {"success": False, "session_id": "", "pid": None,
                "status": f"session_start failed: {e***REMOVED***", "error": str(e)***REMOVED***

    # AGENTS.md для контекста
    _make_agents_md(work_dir, prompt, sid)

    # Выходной файл для захвата вывода
    out_file = work_dir / f".freebuff_output_{sid***REMOVED***.log"
    tmux_session = f"fb_{sid***REMOVED***"

    # Команда Codebuff внутри proot, с захватом через script
    proot_cmd = (
        f"proot-distro login {PROOT_DISTRO***REMOVED*** -- "
        f"{FREEBUFF_BINARY***REMOVED*** --cwd {work_dir***REMOVED***"
    )
    tmux_cmd = f"script -q {out_file***REMOVED*** -c '{proot_cmd***REMOVED***'"

    # Создаём tmux сессию с Codebuff
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, tmux_cmd***REMOVED***,
        capture_output=True, timeout=10,
    )

    # PID tmux процесса
    pid_result = subprocess.run(
        ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_pid***REMOVED***"***REMOVED***,
        capture_output=True, text=True, timeout=10,
    )
    tmux_pid = int(pid_result.stdout.strip()) if pid_result.stdout.strip() else 0

    # Сохраняем PID
    save_pid_file(sid, tmux_pid, str(work_dir))
    _ensure_session_dir()
    (_SESSION_DIR / f"tmux_{sid***REMOVED***").write_text(tmux_session, encoding="utf-8")

    # Monitor.sh — ждёт приглашения Codebuff, отправляет промпт,
    monitor_sh = FREEBUFF_ROOT / "freebuff_plugin_03" / "monitor.sh"
    subprocess.Popen(
        ["bash", str(monitor_sh), sid, prompt, str(timeout), str(work_dir)***REMOVED***,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    return {
        "success": True, "session_id": sid, "pid": tmux_pid,
        "status": "launched", "cwd": str(work_dir),
        "message": "Codebuff запущен через tmux, промпт передан в monitor.sh.",
    ***REMOVED***


def _wait_for_tmux_input(tmux_session: str, timeout: int = 30) -> bool:
    """Ждёт появления 'Enter a coding task' в tmux панели."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = subprocess.run(
                ["tmux", "capture-pane", "-t", tmux_session, "-p"***REMOVED***,
                capture_output=True, text=True, timeout=5,
            )
            text = r.stdout
            if "Enter a coding task" in text or "coding task" in text:
                time.sleep(1)
                return True
            if "Start coding" in text or "RECOMMENDED" in text:
                subprocess.run(
                    ["tmux", "send-keys", "-t", tmux_session, "Enter"***REMOVED***,
                    capture_output=True, timeout=5,
                )
        except Exception:
            pass
        time.sleep(1)
    return False


# ═══════════════════════════════════════════════════════════════
# Синхронный launch (только для отладки — может OOM)
# ═══════════════════════════════════════════════════════════════

def synchronous_oneshot(
    prompt: str,
    cwd: str | Path | None = None,
    timeout: int = 300,
    session_id: str | None = None,
) -> dict:
    """
    Синхронный запуск freebuff (для отладки).
    ВНИМАНИЕ: Держит Python + Codebuff в памяти — возможен OOM.
    """
    from freebuff_plugin_03.bridge import session_start, session_end

    sid = session_id or uuid.uuid4().hex[:8***REMOVED***
    start = time.time()

    work_dir: Path
    cleanup = False
    if cwd is None:
        work_dir = Path(tempfile.mkdtemp(prefix="freebuff_oneshot_"))
        cleanup = True
    else:
        work_dir = Path(cwd)

    original_agents = work_dir / "AGENTS.md"
    original_content = None
    if original_agents.exists():
        original_content = original_agents.read_text(encoding="utf-8")

    try:
        # OOM Protection: убиваем старые freebuff перед запуском
        _run_oom_protection()

        # Старт сессии
        sid = session_start(topic=prompt[:80***REMOVED***)

        # AGENTS.md
        _make_agents_md(work_dir, prompt, sid)

        out_file = work_dir / f".freebuff_output_{sid***REMOVED***.log"
        proot_cmd = (
            f"proot-distro login {PROOT_DISTRO***REMOVED*** -- "
            f"{FREEBUFF_BINARY***REMOVED*** --cwd {work_dir***REMOVED***"
        )
        cmd = ["script", "-q", str(out_file), "-c", proot_cmd***REMOVED***

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(work_dir),
        )

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        result_text = _wait_for_result(work_dir, timeout=3)
        raw_output = ""
        if out_file.exists():
            raw_output = out_file.read_text(encoding="utf-8", errors="replace")

        cleaned = clean_tui_output(raw_output)
        duration = time.time() - start

        # Завершаем сессию
        session_end(sid, summary=f"freebuff {'OK' if result_text else 'TIMEOUT'***REMOVED***")

        return {
            "success": result_text is not None,
            "output": cleaned,
            "result": result_text or "",
            "session_id": sid,
            "duration": round(duration, 1),
            "error": None,
            "returncode": proc.returncode,
        ***REMOVED***

    except Exception as e:
        duration = time.time() - start
        return {
            "success": False,
            "output": f"Error: {e***REMOVED***",
            "result": "",
            "session_id": sid,
            "duration": round(duration, 1),
            "error": str(e),
            "returncode": -1,
        ***REMOVED***
    finally:
        if original_content is not None:
            original_agents.write_text(original_content, encoding="utf-8")
        elif original_agents.exists():
            original_agents.unlink()
        out_file = work_dir / f".freebuff_output_{sid***REMOVED***.log"
        if out_file.exists():
            out_file.unlink()
        result_file = work_dir / ".freebuff_result"
        if result_file.exists():
            result_file.unlink()
        if cleanup:
            shutil.rmtree(str(work_dir), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Freebuff Wrapper CLI")
    sub = parser.add_subparsers(dest="command")

    # launch — phase-based (анти-OOM)
    p_launch = sub.add_parser("launch", help="Phase-based запуск (рекомендуется)")
    p_launch.add_argument("prompt", help="Задача")
    p_launch.add_argument("--cwd", default=None)
    p_launch.add_argument("--timeout", type=int, default=300)

    # run — старый синхронный (только для отладки)
    p_run = sub.add_parser("run", help="Синхронный запуск (только отладка)")
    p_run.add_argument("prompt", help="Задача")
    p_run.add_argument("--cwd", default=None)
    p_run.add_argument("--timeout", type=int, default=120)

    # status
    p_status = sub.add_parser("status", help="Статус активных сессий")

    args = parser.parse_args()

    if args.command == "launch":
        result = launch(
            prompt=args.prompt,
            cwd=args.cwd,
            timeout=args.timeout,
        )
        print(f"Session: {result.get('session_id', '?')***REMOVED***")
        print(f"PID:     {result.get('pid', '?')***REMOVED***")
        print(f"Status:  {result.get('status', '?')***REMOVED***")

    elif args.command == "run":
        result = synchronous_oneshot(
            prompt=args.prompt,
            cwd=args.cwd,
            timeout=args.timeout,
        )
        print(f"\n=== Результат (session={result['session_id'***REMOVED******REMOVED***) ===")
        print(f"Success: {result['success'***REMOVED******REMOVED***")
        print(f"Duration: {result['duration'***REMOVED******REMOVED***s")
        if result.get("error"):
            print(f"Error: {result['error'***REMOVED******REMOVED***")
        if result.get("output"):
            print(f"\nOutput ({len(result['output'***REMOVED***)***REMOVED*** chars):")
            print(result["output"***REMOVED***[:1000***REMOVED***)

    elif args.command == "status":
        pids = list_active_pids()
        if not pids:
            print("Нет активных сессий")
        else:
            print(f"Активных сессий: {len(pids)***REMOVED***")
            for p in pids:
                alive = _is_pid_alive(p["pid"***REMOVED***)
                print(f"  {p['sid'***REMOVED******REMOVED*** PID={p['pid'***REMOVED******REMOVED*** {'🟢' if alive else '⚫'***REMOVED*** {p['cwd'***REMOVED******REMOVED***")

    else:
        parser.print_help()


def _is_pid_alive(pid: int) -> bool:
    """Проверяет, жив ли процесс."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


if __name__ == "__main__":
    main()
