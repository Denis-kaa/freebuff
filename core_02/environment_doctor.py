"""core_02/environment_doctor.py — Environment Doctor для blueprint_v3.

Диагностирует окружение перед запуском любого проекта.
Проверяет: файловую систему, Node.js, память, порты, артефакты проекта.
Основание: PROJECT_REQUIREMENTS.md §5, CON-41/42/43, PB-15.

Usage:
    from core_02.environment_doctor import diagnose
    result = diagnose(Path("/path/to/project"))
    if not result["ok"***REMOVED***:
        for b in result["blockers"***REMOVED***:
            print(f"BLOCKER: {b***REMOVED***")
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
***REMOVED***
from typing import Optional


@dataclass
class EnvDiagnosis:
    """Результат диагностики окружения."""
    ok: bool
    project_root: str
    blockers: list[str***REMOVED*** = field(default_factory=list)
    warnings: list[str***REMOVED*** = field(default_factory=list)
    info: dict = field(default_factory=dict)  # {node_version, fs_type, avail_mb, ...***REMOVED***


# ─── Platform-specific helpers ────────────────────────────────────────────

def _get_fs_type(path: Path) -> str:
    """Возвращает тип файловой системы для пути."""
    try:
        # Linux / Termux: stat -f -c '%T'
        result = subprocess.run(
            ["stat", "-f", "-c", "%T", str(path)***REMOVED***,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: df -T
    try:
        result = subprocess.run(
            ["df", "-T", str(path)***REMOVED***,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1***REMOVED***.split()
                if len(parts) > 1:
                    return parts[1***REMOVED***
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "unknown"


def _get_node_version() -> Optional[str***REMOVED***:
    """Возвращает строку версии Node.js или None."""
    node = shutil.which("node")
    if not node:
        return None
    try:
        result = subprocess.run(
            [node, "--version"***REMOVED***,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_available_memory_mb() -> int:
    """Возвращает доступную память в МБ."""
    # Linux / Termux: /proc/meminfo
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1***REMOVED***) // 1024  # kB → MB
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    return -1


def _is_port_used(port: int) -> bool:
    """Проверяет, занят ли порт."""
    try:
        # ss (предпочтительнее на Linux/Termux)
        result = subprocess.run(
            ["ss", "-tlnp"***REMOVED***,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f":{port***REMOVED***" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: netstat
    try:
        result = subprocess.run(
            ["netstat", "-tlnp"***REMOVED***,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f":{port***REMOVED***" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False


def _check_symlinks() -> bool:
    """Проверяет, поддерживает ли ФС symlinks."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            link_path = str(tmp.name) + ".link_test"
            try:
                os.symlink(tmp.name, link_path)
                os.unlink(link_path)
                return True
            except OSError:
                return False
            finally:
                if os.path.exists(link_path):
                    os.unlink(link_path)
                os.unlink(tmp.name)
    except Exception:
        return False


# ─── Main diagnostic ──────────────────────────────────────────────────────

def diagnose(project_root: Path) -> dict:
    """Диагностирует окружение для проекта.

    Args:
        project_root: Путь к корню проекта.

    Returns:
        dict с ключами:
        - ok: bool — можно ли запускать проект
        - blockers: list[str***REMOVED*** — критические проблемы
        - warnings: list[str***REMOVED*** — предупреждения
        - info: dict — детальная информация о среде
    """
    blockers: list[str***REMOVED*** = [***REMOVED***
    warnings: list[str***REMOVED*** = [***REMOVED***
    info: dict = {***REMOVED***

    # 1. Файловая система
    fs_type = _get_fs_type(project_root)
    info["fs_type"***REMOVED*** = fs_type

    NO_SYMLINK_FS = {"fuseblk", "exfat", "fat32", "vfat", "msdos"***REMOVED***
    if fs_type.lower() in NO_SYMLINK_FS:
        symlinks_ok = _check_symlinks()
        info["symlinks"***REMOVED*** = symlinks_ok
        if not symlinks_ok:
            blockers.append(
                f"Файловая система {fs_type***REMOVED*** не поддерживает symlinks. "
                "Используйте --no-bin-links для npm и полные пути к CLI. "
                "Рекомендуется web-фолбэк (esbuild-wasm). "
                "См. PROJECT_REQUIREMENTS.md §4."
            )
        else:
            warnings.append(f"ФС {fs_type***REMOVED*** — symlinks работают, но нестабильно.")
    else:
        info["symlinks"***REMOVED*** = True

    # 2. Node.js
    node_ver = _get_node_version()
    info["node_version"***REMOVED*** = node_ver or "not found"

    if node_ver is None:
        blockers.append("Node.js не найден. Установите Node.js >= 20 LTS.")
    else:
        try:
            major = int(node_ver.split(".")[0***REMOVED***)
            if major < 20:
                blockers.append(
                    f"Node.js v{node_ver***REMOVED*** < 20 LTS. "
                    "Рекомендуется v20 или v22 LTS."
                )
            elif major >= 26:
                warnings.append(
                    f"Node.js v{node_ver***REMOVED*** — возможна несовместимость "
                    "с нативными модулями. На Termux — штатная версия."
                )
        except ValueError:
            warnings.append(f"Не удалось определить версию Node.js: {node_ver***REMOVED***")

    # 3. Память
    avail_mb = _get_available_memory_mb()
    info["available_memory_mb"***REMOVED*** = avail_mb

    if avail_mb == -1:
        warnings.append("Не удалось определить объём доступной памяти.")
    elif avail_mb < 512:
        blockers.append(
            f"Доступно {avail_mb***REMOVED*** MB памяти (< 512 MB). "
            "Возможны OOM-падения при сборке."
        )
    elif avail_mb < 1024:
        warnings.append(
            f"Доступно {avail_mb***REMOVED*** MB памяти (< 1 GB). "
            "Рекомендуется закрыть фоновые приложения."
        )

    # 4. Артефакты проекта
    for artifact in ("RUNNABLE.md", "CHECKLIST.md", "README.md"):
        path = project_root / artifact
        info[f"has_{artifact.lower().replace('.', '_')***REMOVED***"***REMOVED*** = path.exists()
        if not path.exists():
            if artifact in ("RUNNABLE.md", "CHECKLIST.md"):
                blockers.append(
                    f"Отсутствует {artifact***REMOVED*** в {project_root***REMOVED***. "
                    "См. PROJECT_REQUIREMENTS.md §2-3."
                )
            else:
                warnings.append(f"Отсутствует {artifact***REMOVED*** (рекомендуется).")

    # 5. Порты (проверяем стандартные)
    for port in (8080, 3000, 19000, 19006):
        if _is_port_used(port):
            warnings.append(f"Порт {port***REMOVED*** уже занят.")
    info["ports_checked"***REMOVED*** = [8080, 3000, 19000, 19006***REMOVED***

    # 6. Python (для Python-проектов)
    if (project_root / "requirements.txt").exists() or list(project_root.glob("*.py")):
        try:
            import yaml  # noqa: F401
            info["pyyaml_available"***REMOVED*** = True
        except ImportError:
            warnings.append("PyYAML не установлен (pip install pyyaml).")

    return EnvDiagnosis(
        ok=len(blockers) == 0,
        project_root=str(project_root),
        blockers=blockers,
        warnings=warnings,
        info=info,
    ).__dict__


# ─── Quick CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    root = Path(sys.argv[1***REMOVED***) if len(sys.argv) > 1 else Path.cwd()
    result = diagnose(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["blockers"***REMOVED***:
        print(f"\n❌ BLOCKERS ({len(result['blockers'***REMOVED***)***REMOVED***):")
        for b in result["blockers"***REMOVED***:
            print(f"  • {b***REMOVED***")
    if result["warnings"***REMOVED***:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'***REMOVED***)***REMOVED***):")
        for w in result["warnings"***REMOVED***:
            print(f"  • {w***REMOVED***")
    if not result["blockers"***REMOVED*** and not result["warnings"***REMOVED***:
        print("\n✅ Среда готова к запуску.")
