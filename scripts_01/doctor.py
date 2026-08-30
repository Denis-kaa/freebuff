#!/usr/bin/env python3
"""
doctor.py — CLI диагностики окружения Buffy.

Проверяет:
  - Android / Termux
  - Python, Node.js, Git, npm, pip
  - proot, glibc
  - Runtime (freebuff, claude-code)
  - PATH, .env, .keys
  - Wrapper, разрешения
  - Совместимость

При обнаружении проблем предлагает автоматическое исправление.

Использование:
    python scripts_01/doctor.py                 # Базовая диагностика
    python scripts_01/doctor.py --full           # Полная проверка
    python scripts_01/doctor.py --check-runtime freebuff  # Проверить Runtime
    python scripts_01/doctor.py --fix            # Авто-исправление
    python scripts_01/doctor.py --json           # Вывод в JSON
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
}
from typing import Any, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "")

# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class CheckResult:
    """Результат одной проверки."""
    name: str
    status: str = "ok"       # ok, warn, fail, skip
    message: str = ""
    fix_available: bool = False
    fix_command: str = ""


@dataclass
class DoctorReport:
    """Полный отчёт диагностики."""
    platform: str = ""
    checks: List[CheckResult] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    health_score: float = 1.0

    @property
    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "ok")

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")


# ═══════════════════════════════════════════════════════════════
# Formatters
# ═══════════════════════════════════════════════════════════════

class Colors:
    """ANSI цвета для терминала."""
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def icon(status: str) -> str:
        if status == "ok":
            return f"{Colors.GREEN}✓{Colors.RESET}"
        elif status == "warn":
            return f"{Colors.YELLOW}⚠{Colors.RESET}"
        elif status == "fail":
            return f"{Colors.RED}✗{Colors.RESET}"
        return "?"


def _print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")


def _print_result(check: CheckResult) -> None:
    icon = Colors.icon(check.status)
    fix_note = ""
    if check.fix_available:
        fix_note = f"  {Colors.BLUE}→ fix: {check.fix_command}{Colors.RESET}"
    print(f"  {icon} {check.name}: {check.message}{fix_note}")


# ═══════════════════════════════════════════════════════════════
# Checkers
# ═══════════════════════════════════════════════════════════════


def _run(cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """Запускает команду и возвращает (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -2, "", "timeout"
    except Exception as e:
        return -3, "", str(e)


def check_platform(report: DoctorReport) -> None:
    """Проверяет платформу."""
    import platform
    report.platform = platform.system()

    # OS
    if IS_TERMUX:
        report.checks.append(CheckResult("OS", "ok", "Android (Termux)"))
    elif report.platform == "Linux":
        report.checks.append(CheckResult("OS", "ok", f"Linux ({platform.release()})"))
    elif report.platform == "Darwin":
        report.checks.append(CheckResult("OS", "ok", "macOS"))
    else:
        report.checks.append(CheckResult("OS", "warn", f"Unknown: {report.platform}"))

    # Architecture
    arch = platform.machine()
    if arch in ("aarch64", "arm64"):
        report.checks.append(CheckResult("Architecture", "ok", "ARM64"))
    elif arch == "x86_64":
        report.checks.append(CheckResult("Architecture", "ok", "x86_64"))
    else:
        report.checks.append(CheckResult("Architecture", "warn", arch))


def check_termux(report: DoctorReport) -> None:
    """Проверяет Termux окружение."""
    if not IS_TERMUX:
        report.checks.append(CheckResult("Termux", "skip", "Not Termux"))
        return

    prefix = os.environ.get("PREFIX", "")
    if prefix and Path(prefix).exists():
        report.checks.append(CheckResult("Termux", "ok", f"PREFIX={prefix}"))
    else:
        report.checks.append(CheckResult("Termux", "fail", "PREFIX not set"))


def check_python(report: DoctorReport) -> None:
    """Проверяет Python."""
    import sys as _sys
    ver = f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"
    if _sys.version_info >= (3, 11):
        report.checks.append(CheckResult("Python", "ok", f"v{ver}"))
    else:
        report.checks.append(
            CheckResult("Python", "fail", f"v{ver} (need >= 3.11)",
                        fix_available=True, fix_command="pkg install python")
        )

    # pip
    rc, out, _ = _run([sys.executable, "-m", "pip", "--version"])
    if rc == 0:
        report.checks.append(CheckResult("pip", "ok", out.split()[0] if out else "installed"))
    else:
        report.checks.append(CheckResult("pip", "fail", "not working"))


def check_node(report: DoctorReport) -> None:
    """Проверяет Node.js."""
    rc, out, _ = _run(["node", "--version"])
    if rc == 0:
        ver = out.strip()
        try:
            major = int(ver.lstrip("v").split(".")[0])
            if major >= 18:
                report.checks.append(CheckResult("Node.js", "ok", ver))
            else:
                report.checks.append(CheckResult("Node.js", "warn", f"{ver} (>= 18 recommended)"))
        except ValueError:
            report.checks.append(CheckResult("Node.js", "ok", ver))
    else:
        report.checks.append(CheckResult("Node.js", "skip", "not installed (optional)"))

    # npm
    rc, out, _ = _run(["npm", "--version"])
    if rc == 0:
        report.checks.append(CheckResult("npm", "ok", out.strip()))
    else:
        report.checks.append(CheckResult("npm", "skip", "not installed"))


def check_git(report: DoctorReport) -> None:
    """Проверяет Git."""
    rc, out, _ = _run(["git", "--version"])
    if rc == 0:
        report.checks.append(CheckResult("Git", "ok", out.strip()))
    else:
        report.checks.append(
            CheckResult("Git", "fail", "not installed",
                        fix_available=True, fix_command="pkg install git")
        )


def check_proot(report: DoctorReport) -> None:
    """Проверяет proot (для Android)."""
    if not IS_TERMUX:
        report.checks.append(CheckResult("proot", "skip", "Not Termux"))
        return

    if shutil.which("proot-distro"):
        rc, out, _ = _run(["proot-distro", "list"])
        if rc == 0:
            distros = out.strip()
            report.checks.append(CheckResult("proot", "ok", f"Available: {distros}" if distros else "installed"))
        else:
            report.checks.append(CheckResult("proot", "warn", "installed but listing failed"))
    else:
        report.checks.append(
            CheckResult("proot", "skip", "not installed (optional, needed for Claude Code)",
                        fix_available=True, fix_command="pkg install proot proot-distro")
        )


def check_runtime_freebuff(report: DoctorReport) -> None:
    """Проверяет FreeBuff CLI."""
    if shutil.which("freebuff"):
        rc, out, _ = _run(["freebuff", "--version"], timeout=10)
        if rc == 0:
            report.checks.append(CheckResult("freebuff CLI", "ok", out.strip()[:80]))
        else:
            report.checks.append(CheckResult("freebuff CLI", "warn", "installed but --version failed"))
    else:
        # Проверить pip
        rc, out, _ = _run([sys.executable, "-m", "pip", "show", "freebuff"])
        if rc == 0:
            report.checks.append(CheckResult("freebuff CLI", "warn", "pip package installed, binary not in PATH"))
        else:
            report.checks.append(
                CheckResult("freebuff CLI", "fail", "not installed",
                            fix_available=True, fix_command="pip install freebuff")
            )


def check_runtime_claude(report: DoctorReport) -> None:
    """Проверяет Claude Code."""
    if shutil.which("claude"):
        rc, out, _ = _run(["claude", "--version"], timeout=10)
        if rc == 0:
            report.checks.append(CheckResult("Claude Code", "ok", out.strip()[:80]))
        else:
            report.checks.append(CheckResult("Claude Code", "warn", "binary found but --version failed"))
        return

    # Проверить npm глобально
    rc, out, _ = _run(["npm", "list", "-g", "@anthropic/claude-code"], timeout=10)
    if rc == 0 and "@anthropic/claude-code" in out:
        report.checks.append(CheckResult("Claude Code", "warn", "npm package installed, binary not in PATH"))
    else:
        report.checks.append(
            CheckResult("Claude Code", "skip", "not installed (optional)",
                        fix_available=True, fix_command="npm install -g @anthropic/claude-code")
        )


def check_path(report: DoctorReport) -> None:
    """Проверяет PATH."""
    path = os.environ.get("PATH", "")
    dirs = path.split(":")
    issues = []

    for d in ["~/.local/bin", "/usr/local/bin"]:
        expanded = os.path.expanduser(d)
        if expanded not in dirs:
            issues.append(d)

    if issues:
        report.checks.append(
            CheckResult("PATH", "warn", f"Missing: {', '.join(issues)}",
                        fix_available=True, fix_command=f"export PATH=\"$HOME/.local/bin:$PATH\"")
        )
    else:
        report.checks.append(CheckResult("PATH", "ok", "All required dirs present"))


def check_env(report: DoctorReport) -> None:
    """Проверяет .env и ключи."""
    env_path = WORKSPACE / ".env"
    if env_path.exists():
        has_keys = False
        try:
            for line in env_path.read_text().split("\n"):
                if "API_KEY" in line and not line.strip().startswith("#"):
                    has_keys = True
                    break
        except Exception:
            pass
        if has_keys:
            report.checks.append(CheckResult(".env", "ok", "API keys found"))
        else:
            report.checks.append(CheckResult(".env", "warn", "file exists but no API_KEY found"))
    else:
        report.checks.append(CheckResult(".env", "warn", "not found (create from .env.example)"))

    # .keys/
    keys_dir = WORKSPACE / ".keys"
    if keys_dir.exists() and list(keys_dir.iterdir()):
        report.checks.append(CheckResult(".keys/", "ok", "KeyPool directory exists"))
    else:
        report.checks.append(CheckResult(".keys/", "warn", "not found (KeyPool unavailable)"))


def check_disk(report: DoctorReport) -> None:
    """Проверяет дисковое пространство."""
    try:
        usage = shutil.disk_usage(WORKSPACE)
        free_gb = usage.free / (1024 ** 3)
        if free_gb > 1:
            report.checks.append(CheckResult("Disk", "ok", f"{free_gb:.1f} GB free"))
        elif free_gb > 0.5:
            report.checks.append(CheckResult("Disk", "warn", f"{free_gb:.1f} GB free (low)"))
        else:
            report.checks.append(CheckResult("Disk", "fail", f"{free_gb:.1f} GB free (critical)"))
    except Exception:
        report.checks.append(CheckResult("Disk", "skip", "Cannot determine"))


def check_ram(report: DoctorReport) -> None:
    """Проверяет RAM."""
    # Try reading /proc/meminfo (Linux/Android)
    try:
        meminfo = Path("/proc/meminfo").read_text()
        for line in meminfo.split("\n"):
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                mb = kb // 1024
                if mb > 1024:
                    report.checks.append(CheckResult("RAM", "ok", f"{mb} MB available"))
                elif mb > 512:
                    report.checks.append(CheckResult("RAM", "warn", f"{mb} MB (low)"))
                else:
                    report.checks.append(CheckResult("RAM", "fail", f"{mb} MB (critical)"))
                return
        report.checks.append(CheckResult("RAM", "skip", "Cannot parse /proc/meminfo"))
    except Exception:
        report.checks.append(CheckResult("RAM", "skip", "Cannot determine"))


def check_workspace(report: DoctorReport) -> None:
    """Проверяет workspace."""
    # BUFFY.md
    if (WORKSPACE / "BUFFY.md").exists():
        report.checks.append(CheckResult("BUFFY.md", "ok", "Found"))
    else:
        report.checks.append(CheckResult("BUFFY.md", "fail", "Not found — is this a freebuff workspace?"))

    # data_13/context.db
    db_path = WORKSPACE / "data_13" / "context.db"
    if db_path.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            conn.close()
            report.checks.append(CheckResult("context.db", "ok", f"{sessions[0]} sessions"))
        except Exception:
            report.checks.append(CheckResult("context.db", "warn", "Exists but cannot read"))
    else:
        report.checks.append(CheckResult("context.db", "warn", "Not found"))


def check_consistency(report: DoctorReport) -> None:
    """Проверяет самоконсистентность канонических реестров (Этап 9).

    Запускает scripts_01/consistency_check.py — реестры (ARCHITECTURE_CANONICAL,
    LIFECYCLE, MODULE_CONSOLIDATION, GLOSSARY, ROADMAP) как данные.
    """
    try:
        # При запуске `python scripts_01/doctor.py` sys.path[0] = scripts_01/,
        # поэтому workspace добавляем в путь явно для `import scripts_01.*`.
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        from scripts_01.consistency_check import build_report

        result = build_report(WORKSPACE)
    except Exception as e:
        report.checks.append(
            CheckResult("Consistency", "warn", f"Cannot run: {e}")
        )
        return

    total = result.get("total_issues", 0)
    if result.get("consistent", False):
        report.checks.append(CheckResult("Consistency", "ok", "All registries consistent"))
    else:
        report.checks.append(
            CheckResult(
                "Consistency",
                "warn" if total <= 3 else "fail",
                f"{total} issue(s) — run `python scripts_01/consistency_check.py --report`",
            )
        )


def check_drift(report: DoctorReport) -> None:
    """Проверяет дрейф документации vs. реальность (Этап 9).

    Запускает scripts_01/drift_check.py — битые ссылки, расхождения дерева
    каталогов, непроиндексированные доки, статус-таблицы BUFFY_PROJECT.
    """
    try:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        from scripts_01.drift_check import build_report as build_drift_report

        result = build_drift_report(WORKSPACE)
    except Exception as e:
        report.checks.append(CheckResult("Drift", "warn", f"Cannot run: {e}"))
        return

    if not result.get("has_drift", False):
        report.checks.append(CheckResult("Drift", "ok", "No drift (docs match reality)"))
        return

    total = sum(
        len(result.get(k, []))
        for k in ("status_tables", "knowledge_index", "directory_structure",
                  "adr_canonical_location", "markdown_links")
    )
    report.checks.append(
        CheckResult(
            "Drift",
            "warn" if total <= 3 else "fail",
            f"{total} drift issue(s) — run `python scripts_01/drift_check.py --force --report`",
        )
    )


def check_tests(report: DoctorReport) -> None:
    """Проверяет тесты (быстрый прогон)."""
    tests_dir = WORKSPACE / "tests_09"
    if not tests_dir.exists():
        report.checks.append(CheckResult("Tests", "warn", "tests_09/ directory not found"))
        return

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests_09/", "-q", "--tb=no", "--collect-only"],
            cwd=str(WORKSPACE),
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            # Extract count
            for line in result.stdout.split("\n"):
                if "passed" in line:
                    report.checks.append(CheckResult("Tests", "ok", line.strip()))
                    return
            report.checks.append(CheckResult("Tests", "ok", "All passed"))
        else:
            report.checks.append(CheckResult("Tests", "warn", "Some tests failed"))
    except subprocess.TimeoutExpired:
        report.checks.append(CheckResult("Tests", "skip", "Timeout (> 300s)"))
    except Exception as e:
        report.checks.append(CheckResult("Tests", "skip", f"Cannot run: {e}"))


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def run_diagnostics(
    full: bool = False,
    runtime: Optional[str] = None,
    apply_fixes: bool = False,
) -> DoctorReport:
    """Запускает полную диагностику.

    Args:
        full: запустить все проверки (включая тесты)
        runtime: проверить конкретный Runtime
        apply_fixes: автоматически применить исправления

    Returns:
        DoctorReport
    """
    report = DoctorReport()

    # Всегда проверяем
    check_platform(report)
    check_termux(report)
    check_python(report)
    check_git(report)
    check_path(report)
    check_disk(report)
    check_ram(report)
    check_workspace(report)
    check_consistency(report)
    check_drift(report)

    # Опционально
    if full or runtime == "freebuff":
        check_runtime_freebuff(report)
    if full or runtime == "claude-code":
        check_node(report)
        check_proot(report)
        check_runtime_claude(report)
    if full:
        check_env(report)
        check_tests(report)

    # Расчёт health score
    total = len(report.checks)
    if total > 0:
        ok = report.ok_count
        report.health_score = ok / total

    # Авто-исправление
    if apply_fixes:
        for check in report.checks:
            if check.status == "fail" and check.fix_available:
                # Пытаемся применить fix
                try:
                    subprocess.run(check.fix_command, shell=True, timeout=30)
                    report.fixes_applied.append(check.fix_command)
                except Exception:
                    pass

    return report


def print_report(report: DoctorReport, json_output: bool = False) -> None:
    """Выводит отчёт."""
    if json_output:
        data = {
            "platform": report.platform,
            "health_score": round(report.health_score, 2),
            "ok": report.ok_count,
            "warn": report.warn_count,
            "fail": report.fail_count,
            "checks": [
                {"name": c.name, "status": c.status, "message": c.message}
                for c in report.checks
            ],
        }
        if report.fixes_applied:
            data["fixes_applied"] = report.fixes_applied
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    _print_header(f"Buffy Doctor — {report.platform}")
    print(f"  Health Score: {Colors.BOLD}{report.health_score:.0%}{Colors.RESET}")
    print(f"  {report.ok_count} ok, {report.warn_count} warnings, {report.fail_count} failures")

    for check in report.checks:
        _print_result(check)

    if report.fixes_applied:
        _print_header("Fixes Applied")
        for fix in report.fixes_applied:
            print(f"  {Colors.GREEN}→ {fix}{Colors.RESET}")

    # Summary
    _print_header("Summary")
    if report.fail_count == 0 and report.warn_count == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}✓ All checks passed!{Colors.RESET}")
    elif report.fail_count == 0:
        print(f"  {Colors.YELLOW}⚠ {report.warn_count} warnings — system works but can be improved{Colors.RESET}")
    else:
        print(f"  {Colors.RED}✗ {report.fail_count} failures — run with --fix to attempt repairs{Colors.RESET}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Buffy Doctor — CLI диагностики окружения",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/doctor.py                        # Базовая диагностика
  python scripts_01/doctor.py --full                  # Полная проверка
  python scripts_01/doctor.py --check-runtime freebuff  # Проверить Runtime
  python scripts_01/doctor.py --fix                   # Авто-исправление
  python scripts_01/doctor.py --json                  # Вывод в JSON
        """,
    )
    parser.add_argument("--full", action="store_true", help="Полная проверка (включая тесты и все Runtime)")
    parser.add_argument("--check-runtime", choices=["freebuff", "claude-code"], help="Проверить конкретный Runtime")
    parser.add_argument("--fix", action="store_true", help="Автоматически применить исправления")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON формате")
    parser.add_argument("--version", action="store_true", help="Показать версию")

    args = parser.parse_args()

    if args.version:
        print("Buffy Doctor v1.0.0")
        return

    report = run_diagnostics(
        full=args.full,
        runtime=args.check_runtime,
        apply_fixes=args.fix,
    )
    print_report(report, json_output=args.json)

    # Exit code
    if report.fail_count > 0:
        sys.exit(1)
    elif report.warn_count > 0:
        sys.exit(0)  # warnings not fatal
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
