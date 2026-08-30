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
}
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
}
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
                ["bash", str(_OOM_SCRIPT), "--check"],
                timeout=30,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"⚠️ OOM protection предупреждение: {result.stdout.strip()}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("⚠️ OOM protection timeout (30s) — продолжаю без очистки", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ OOM protection error: {e}", file=sys.stderr)

# ── ANSI / управляющие последовательности ─────────────────────

_ANSI_STRIP = re.compile(r"\x1b\[[0-9;)*[a-zA-Z]|\x1b\*].*?(\x1b\\|\x07)|\x1b[\[\*]()#]")
_TERMINFO_STRIP = re.compile(r"\x1b[<>)|[\x00-\x08\x0b\x0c\x0e-\x1f]")
_ERASE_LINE = re.compile(r"\x1b\[[0-9)*[JK]|\x1b\[[0-9;]*[Hf]")
_SCREEN_ERASE = re.compile(r"\x1b\[2J\x1b\[H")
_CONTINUOUS_DOTS = re.compile(r"Connecting…+")
_PROGRESS_BARS = re.compile(r"█+[░)*|●+[○]*|[\d]+%")

def clean_tui_output(text: str) -> str:
    """Очищает вывод TUI от управляющих последовательностей."""
    text = _SCREEN_ERASE.sub("", text)
    text = _ERASE_LINE.sub("", text)
    text = _ANSI_STRIP.sub("", text)
    text = _TERMINFO_STRIP.sub("", text)
    text = _CONTINUOUS_DOTS.sub("", text)
    text = _PROGRESS_BARS.sub("", text)
    lines = [l for l in text.split("\n") if l.strip()]
    return "\n".join(lines)


# ── PID-файлы (сессия) ────────────────────────────────────────

# ── Proot autodetection (CON-31 / Phase 5.3-D-2) ────────────────

def _proot_distro_login_available() -> bool:
    """True если мы можем вызвать `proot-distro login` (т.е. Termux, не proot).

    Используется в паре с _is_inside_proot() для выбора пути запуска бинаря:
    - Termux (outer): `proot-distro login ubuntu -- {bin}`
    - inside-proot (Ubuntu / sandboxed env): direct exec `{bin}`
    См. §подробнее v5.73.0 CHANGELOG.
    """
    try:
        r = subprocess.run(
            ["proot-distro", "list"],
            capture_output=True, text=True, timeout=2,
        )
        # "should not be executed under PRoot" → returncode != 0
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _is_inside_proot() -> bool:
    """True если мы уже внутри proot-distro (Ubuntu) — бинарь можно exec'ить напрямую.

    Логика: если proot-distro НЕ доступен (т.е. мы внутри), И бинарь доступен
    и executable в нашей файловой системе → direct-exec путь безопасен.
    Это калька с lightpanda_worker.py: «ныряем» в proot-aware resolution,
    чтобы избежать вложенного `proot-distro login` из-под proot (запрещено).
    """
    if _proot_distro_login_available():
        return False  # мы в native Termux — wrapper path корректен
    # proot-distro недоступна → мы внутри. Проверяем, что бинарь доступен.
    try:
        return FREEBUFF_BINARY.exists() and os.access(FREEBUFF_BINARY, os.X_OK)
    except OSError:
        return False


# Single-instance blocker markers (v5.88.0): freebuff допускает только один
# живой инстанс. Когда он занят (живая интерактивная сессия), spawned-экземпляр
# печатает 'Freebuff is already running. Only one freebuff instance is allowed
# at a time.' и предлагает 'Take over'/'Exit' вместо старта TUI → monitor ждёт
# → timeout. Диспетчер должен отложить (deferral) задачу, а не фейлить её.
_SINGLE_INSTANCE_MARKERS = (
    "freebuff is already running",
    "only one freebuff instance is allowed",
    "take over",
)


# Ubuntu rootfs кандидаты для inside-proot загрузчика (v5.88.0 fix).
# Бинарь freebuff слинкован с glibc из Ubuntu rootfs; при direct-exec внутри
# sandbox загрузчик не находит libc.so (exit 127). Запуск через явный
# ld-linux-aarch64.so.1 --library-path решает проблему.
_ROOTFS_CANDIDATES = [
    Path("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs"),
    Path("/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu"),
]


def _rootfs_loader_prefix() -> Optional[str]:
    """Возвращает префикс запуска glibc-бинаря через загрузчик Ubuntu rootfs.

    Inside-proot direct-exec падает с 'libc.so: cannot open shared object file'
    (exit 127): sandbox не предоставляет glibc по стандартным путям. Явный вызов
    загрузчика rootfs решает:
        {ld-linux-aarch64.so.1} --library-path {libdir} {bin} --cwd {cwd}

    Returns:
        Строку-префикс (loader + --library-path) если загрузчик найден,
        иначе None (fallback на direct-exec, старое поведение).
    """
    for root in _ROOTFS_CANDIDATES:
        for rel in ("usr/lib/aarch64-linux-gnu", "lib/aarch64-linux-gnu"):
            loader = root / rel / "ld-linux-aarch64.so.1"
            libdir = root / rel
            if loader.exists() and libdir.is_dir():
                return f"{loader} --library-path {libdir}"
    return None


def _build_buffer_cmd(work_dir: Path) -> str:
    """Конструирует shell-команду для запуска freebuff binary.

    - В native Termux: `proot-distro login ubuntu -- {bin} --cwd {cwd}`
    - Внутри proot/Ubuntu: rootfs loader prefix (glibc) с fallback на direct exec:
        `{ld-linux-aarch64.so.1} --library-path {libdir} {bin} --cwd {cwd}`
    Возвращает shlex-safe строку (используется внутри `script -q ... -c '{cmd)'`).
    """
    if _is_inside_proot():
        loader_prefix = _rootfs_loader_prefix()
        if loader_prefix:
            print(
                f"[FreebuffWrapper] DETECTED inside-proot — rootfs loader: {loader_prefix}",
                file=sys.stderr,
            )
            # Termux LD_PRELOAD (libtermux-exec-ld-preload.so, bionic exec-shim)
            # ломает glibc-загрузчик: без снятия freebuff падает с
            # 'libc.so: cannot open shared object file' (exit 127) — проверено
            # в tmux (env -u LD_PRELOAD → TUI стартует, 'Connecting…').
            return f"env -u LD_PRELOAD {loader_prefix} {FREEBUFF_BINARY} --cwd {work_dir}"
        print(
            f"[FreebuffWrapper] DETECTED inside-proot — execing binary directly: {FREEBUFF_BINARY}",
            file=sys.stderr,
        )
        # Тот же glibc-бинарь — LD_PRELOAD (Termux bionic exec-shim) ломает и direct exec.
        return f"env -u LD_PRELOAD {FREEBUFF_BINARY} --cwd {work_dir}"
    return f"proot-distro login {PROOT_DISTRO} -- {FREEBUFF_BINARY} --cwd {work_dir}"


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
    pid_file = _SESSION_DIR / f"pid_{sid}"
    pid_file.write_text(
        f"{pid}\n{sid}\n{cwd}\n",
        encoding="utf-8",
    )
    return str(pid_file)


def read_pid_file(sid: str) -> dict | None:
    """Читает PID-файл сессии."""
    pid_file = _SESSION_DIR / f"pid_{sid}"
    if not pid_file.exists():
        return None
    lines = pid_file.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) < 3:
        return None
    return {
        "pid": int(lines[0]),
        "sid": lines[1],
        "cwd": lines[2],
    }


def remove_pid_file(sid: str) -> None:
    """Удаляет PID-файл."""
    pid_file = _SESSION_DIR / f"pid_{sid}"
    if pid_file.exists():
        pid_file.unlink()


def list_active_pids() -> list[dict]:
    """Список всех активных PID-файлов."""
    _ensure_session_dir()
    results = []
    for f in sorted(_SESSION_DIR.glob("pid_*")):
        lines = f.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) >= 3:
            results.append({
                "pid": int(lines[0]),
                "sid": lines[1],
                "cwd": lines[2],
            ])
    return results


# ── AGENTS.md ─────────────────────────────────────────────────

def _backup_agents_md(cwd: Path) -> None:
    """Бэкапит существующий канонический AGENTS.md в .freebuff_original_agents.

    Восстанавливается monitor.sh после сессии (W-13 fix: канон не теряется).
    Если бэкап уже есть — не перезаписываем (идемпотентность).
    """
    agents_path = cwd / "AGENTS.md"
    backup_path = cwd / ".freebuff_original_agents"
    if backup_path.exists():
        return
    if agents_path.exists():
        backup_path.write_text(agents_path.read_text(encoding="utf-8"), encoding="utf-8")


def _make_agents_md(cwd: Path, prompt: str, session_id: str) -> Path:
    """Создаёт временный AGENTS.md: session-заголовок + задача + канонические правила.

    Канонический AGENTS.md (правила платформы) сохраняется ниже заголовка сессии,
    чтобы запущенный агент видел и задачу, и правила (промт 70: AGENTS.md читается
    при старте любой сессии). Оригинал бэкапится в `.freebuff_original_agents`
    (launch) и восстанавливается monitor.sh после сессии.
    """
    agents_path = cwd / "AGENTS.md"
    backup_path = cwd / ".freebuff_original_agents"
    canonical = ""
    if backup_path.exists():
        canonical = backup_path.read_text(encoding="utf-8")
    elif agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8", errors="replace")
        # Guard двойного назначения: (1) повторный launch не дублирует session-контент;
        # (2) crash-tolerance — если AGENTS.md остался session-файлом после упавшей сессии,
        # канон не встраивается (пустой), restore сделает monitor.sh на следующей сессии.
        if "Freebuff Plugin Session" not in existing[:200]:
            canonical = existing
    content = f"""# Freebuff Plugin Session

Session ID: {session_id}
Created: {datetime.now(timezone.utc).isoformat()}

## Task

{prompt}

## Instructions

1. Выполни задачу выше.
2. После завершения задачи напиши результат в файл .freebuff_result
3. Не спрашивай подтверждения — просто делай.
4. Используй инструменты по необходимости.
5. Когда закончишь — сохрани результат и завершись.

---

## Канонические правила платформы (AGENTS.md)

{canonical}
"""
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


def _wait_for_new_result(
    cwd: Path,
    baseline: int | None,
    timeout: int = 300,
    poll_interval: float = 2.0,
) -> str | None:
    """Ждёт НОВЫЙ .freebuff_result (mtime новее baseline).

    Защита от стейл-файла: `.freebuff_result` может уже существовать
    (в т.ч. git-tracked в корне проекта) — без сравнения mtime мы бы
    мгновенно прочитали старый результат.
    """
    result_file = cwd / ".freebuff_result"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if result_file.exists():
            try:
                mtime = result_file.stat().st_mtime_ns
            except OSError:
                mtime = -1
            if baseline is None or mtime > baseline:
                try:
                    return result_file.read_text(encoding="utf-8")
                except OSError:
                    # Читатель мог застать файл в процессе записи — ретрай на след. полле
                    time.sleep(poll_interval)
                    continue
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
    model: str = "auto",
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
        model: Модель для стартового экрана выбора freebuff ("auto"/"0" = DeepSeek V4 Flash,
               "1".."5" = позиция в списке). Прокидывается в monitor.sh.

    Returns:
        dict: {success, session_id, pid, status}
    """
    from freebuff_plugin_03.bridge import session_start

    sid = session_id or uuid.uuid4().hex[:8]
    work_dir = Path(cwd) if cwd else Path.cwd()
    work_dir.mkdir(parents=True, exist_ok=True)

    # OOM Protection: убиваем старые freebuff перед запуском
    _run_oom_protection()

    # Фаза 1: Старт сессии
    try:
        sid = session_start(topic=prompt[:80])
    except Exception as e:
        return {"success": False, "session_id": "", "pid": None,
                "status": f"session_start failed: {e}", "error": str(e)]

    # AGENTS.md для контекста: бэкап канона → session-файл (restore делает monitor.sh)
    _backup_agents_md(work_dir)
    _make_agents_md(work_dir, prompt, sid)

    # Выходной файл для захвата вывода
    out_file = work_dir / f".freebuff_output_{sid}.log"
    tmux_session = f"fb_{sid}"

    # Команда Codebuff: внутри proot — direct exec, иначе proot-distro login (v5.73.0)
    proot_cmd = _build_buffer_cmd(work_dir)
    tmux_cmd = f"script -q {out_file} -c '{proot_cmd}'"

    # Создаём tmux сессию с Codebuff
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, tmux_cmd],
        capture_output=True, timeout=10,
    )

    # PID tmux процесса
    pid_result = subprocess.run(
        ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_pid]"],
        capture_output=True, text=True, timeout=10,
    )
    tmux_pid = int(pid_result.stdout.strip()) if pid_result.stdout.strip() else 0

    # Сохраняем PID
    save_pid_file(sid, tmux_pid, str(work_dir))
    _ensure_session_dir()
    (_SESSION_DIR / f"tmux_{sid}").write_text(tmux_session, encoding="utf-8")

    # Monitor.sh — ждёт приглашения Codebuff, отправляет промпт,
    monitor_sh = FREEBUFF_ROOT / "freebuff_plugin_03" / "monitor.sh"
    subprocess.Popen(
        ["bash", str(monitor_sh), sid, prompt, str(timeout), str(work_dir), model],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    return {
        "success": True, "session_id": sid, "pid": tmux_pid,
        "status": "launched", "cwd": str(work_dir),
        "message": "Codebuff запущен через tmux, промпт передан в monitor.sh.",
    }


def launch_and_wait(
    prompt: str,
    cwd: str | Path | None = None,
    timeout: int = 300,
    session_id: str | None = None,
    model: str = "auto",
) -> dict:
    """
    Phase-based запуск + ожидание результата (анти-OOM, для cron/диспетчера).

    В отличие от synchronous_oneshot (Python + Codebuff в памяти → OOM-риск),
    здесь launch() возвращается сразу (Python завершается, память freed),
    а результат забирается опросом `.freebuff_result` — тот же формат
    результата, что у synchronous_oneshot (success/output/result/duration).

    Args:
        prompt: Текст задачи.
        cwd: Рабочая директория.
        timeout: Таймаут ожидания результата (с).
        session_id: ID сессии.
        model: Модель для стартового экрана выбора freebuff ("auto"/"0" = DeepSeek V4 Flash,
               "1".."5" = позиция в списке). Прокидывается в launch() → monitor.sh.

    Returns:
        dict: {success, output, result, session_id, duration, error, returncode}
    """
    start = time.time()
    work_dir = Path(cwd) if cwd else Path.cwd()
    work_dir.mkdir(parents=True, exist_ok=True)

    # Снапшот существующего .freebuff_result (защита от стейл-файла)
    result_file = work_dir / ".freebuff_result"
    baseline: int | None = None
    if result_file.exists():
        try:
            baseline = result_file.stat().st_mtime_ns
        except OSError:
            baseline = None

    launched = launch(
        prompt=prompt,
        cwd=str(work_dir),
        timeout=timeout,
        session_id=session_id,
        model=model,
    )
    if not launched.get("success"):
        return {
            "success": False, "output": "", "result": "",
            "session_id": launched.get("session_id", ""),
            "duration": round(time.time() - start, 1),
            "error": launched.get("status", "launch failed"),
            "returncode": -1,
        }

    sid = launched.get("session_id", "")
    # Опрос нового результата (mtime > baseline)
    result_text = _wait_for_new_result(work_dir, baseline, timeout=timeout)
    duration = round(time.time() - start, 1)

    raw_output = ""
    out_file = work_dir / f".freebuff_output_{sid}.log"
    if out_file.exists():
        try:
            raw_output = out_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw_output = ""
        # Cleanup: не копим .freebuff_output_*.log в cwd при каждом cron-запуске
        try:
            out_file.unlink()
        except OSError:
            pass
    cleaned = clean_tui_output(raw_output)

    # Single-instance blocker (v5.88.0): если живая сессия уже занимает
    # единственный инстанс freebuff, spawned-экземпляр печатает
    # 'Freebuff is already running' + 'Take over'/'Exit' и НЕ стартует →
    # monitor ждёт → timeout. Это НЕ провал задачи: диспетчер должен
    # отложить её (deferral), а не фейлить как timeout.
    # Gate на result_text is None: если .freebuff_result появился — инстанс
    # реально выполнил задачу (не мог быть заблокирован), и маркер в выводе
    # может быть просто процитирован в контексте задачи (false positive).
    blocked_single_instance = result_text is None and any(
        m in raw_output.lower() for m in _SINGLE_INSTANCE_MARKERS
    )
    if blocked_single_instance:
        error = (
            "single_instance_busy: freebuff уже запущен — Only one freebuff "
            "instance is allowed. Задача должна быть отложена (deferral)."
        )
    elif result_text is None:
        error = f"timeout after {timeout}s (phase-based)"
    else:
        error = None

    return {
        "success": result_text is not None and not blocked_single_instance,
        "output": cleaned,
        "result": result_text or "",
        "session_id": sid,
        "duration": duration,
        "error": error,
        "returncode": 0 if (result_text is not None and not blocked_single_instance) else -1,
        "blocked_single_instance": blocked_single_instance,
    }


def _wait_for_tmux_input(tmux_session: str, timeout: int = 30) -> bool:
    """Ждёт появления 'Enter a coding task' в tmux панели."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = subprocess.run(
                ["tmux", "capture-pane", "-t", tmux_session, "-p"],
                capture_output=True, text=True, timeout=5,
            )
            text = r.stdout
            if "Enter a coding task" in text or "coding task" in text:
                time.sleep(1)
                return True
            if "Start coding" in text or "RECOMMENDED" in text:
                subprocess.run(
                    ["tmux", "send-keys", "-t", tmux_session, "Enter"],
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

    sid = session_id or uuid.uuid4().hex[:8]
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
        sid = session_start(topic=prompt[:80])

        # AGENTS.md
        _make_agents_md(work_dir, prompt, sid)

        out_file = work_dir / f".freebuff_output_{sid}.log"
        # Команда Codebuff: внутри proot — direct exec, иначе proot-distro login (v5.73.0)
        proot_cmd = _build_buffer_cmd(work_dir)
        cmd = ["script", "-q", str(out_file), "-c", proot_cmd]

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
        session_end(sid, summary=f"freebuff {'OK' if result_text else 'TIMEOUT'}")

        return {
            "success": result_text is not None,
            "output": cleaned,
            "result": result_text or "",
            "session_id": sid,
            "duration": round(duration, 1),
            "error": None,
            "returncode": proc.returncode,
        }

    except Exception as e:
        duration = time.time() - start
        return {
            "success": False,
            "output": f"Error: {e}",
            "result": "",
            "session_id": sid,
            "duration": round(duration, 1),
            "error": str(e),
            "returncode": -1,
        }
    finally:
        if original_content is not None:
            original_agents.write_text(original_content, encoding="utf-8")
        elif original_agents.exists():
            original_agents.unlink()
        out_file = work_dir / f".freebuff_output_{sid}.log"
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
        print(f"Session: {result.get('session_id', '?')}")
        print(f"PID:     {result.get('pid', '?')}")
        print(f"Status:  {result.get('status', '?')}")

    elif args.command == "run":
        result = synchronous_oneshot(
            prompt=args.prompt,
            cwd=args.cwd,
            timeout=args.timeout,
        )
        print(f"\n=== Результат (session={result['session_id']}) ===")
        print(f"Success: {result['success']}")
        print(f"Duration: {result['duration']}s")
        if result.get("error"):
            print(f"Error: {result['error']}")
        if result.get("output"):
            print(f"\nOutput ({len(result['output'])} chars):")
            print(result["output"][:1000])

    elif args.command == "status":
        pids = list_active_pids()
        if not pids:
            print("Нет активных сессий")
        else:
            print(f"Активных сессий: {len(pids)}")
            for p in pids:
                alive = _is_pid_alive(p["pid"])
                print(f"  {p['sid']} PID={p['pid']} {'🟢' if alive else '⚫'} {p['cwd']}")

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
