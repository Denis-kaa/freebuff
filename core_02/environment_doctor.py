"""core_02/environment_doctor.py — Environment Doctor для blueprint_v3.

Диагностирует окружение перед запуском любого проекта.
Проверяет: файловую систему, Node.js, память, порты, артефакты проекта.
Основание: PROJECT_REQUIREMENTS.md §5, CON-41/42/43, PB-15.

Usage:
    from core_02.environment_doctor import diagnose
    result = diagnose(Path("/path/to/project"))
    if not result["ok"]:
        for b in result["blockers"]:
            print(f"BLOCKER: {b}")
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EnvDiagnosis:
    """Результат диагностики окружения."""
    ok: bool
    project_root: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)  # {node_version, fs_type, avail_mb, ...}


# ─── Platform-specific helpers ────────────────────────────────────────────

def _get_fs_type(path: Path) -> str:
    """Возвращает тип файловой системы для пути."""
    try:
        # Linux / Termux: stat -f -c '%T'
        result = subprocess.run(
            ["stat", "-f", "-c", "%T", str(path)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: df -T
    try:
        result = subprocess.run(
            ["df", "-T", str(path)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 1:
                    return parts[1]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "unknown"


def _get_node_version() -> Optional[str]:
    """Возвращает строку версии Node.js или None."""
    node = shutil.which("node")
    if not node:
        return None
    try:
        result = subprocess.run(
            [node, "--version"],
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
                        return int(parts[1]) // 1024  # kB → MB
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    return -1


def _is_port_used(port: int) -> bool:
    """Проверяет, занят ли порт."""
    try:
        # ss (предпочтительнее на Linux/Termux)
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f":{port}" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: netstat
    try:
        result = subprocess.run(
            ["netstat", "-tlnp"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f":{port}" in result.stdout
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
        - blockers: list[str] — критические проблемы
        - warnings: list[str] — предупреждения
        - info: dict — детальная информация о среде
    """
    blockers: list[str] = []
    warnings: list[str] = []
    info: dict = {}

    # 1. Файловая система
    fs_type = _get_fs_type(project_root)
    info["fs_type"] = fs_type

    NO_SYMLINK_FS = {"fuseblk", "exfat", "fat32", "vfat", "msdos"}
    if fs_type.lower() in NO_SYMLINK_FS:
        symlinks_ok = _check_symlinks()
        info["symlinks"] = symlinks_ok
        if not symlinks_ok:
            blockers.append(
                f"Файловая система {fs_type} не поддерживает symlinks. "
                "Используйте --no-bin-links для npm и полные пути к CLI. "
                "Рекомендуется web-фолбэк (esbuild-wasm). "
                "См. PROJECT_REQUIREMENTS.md §4."
            )
        else:
            warnings.append(f"ФС {fs_type} — symlinks работают, но нестабильно.")
    else:
        info["symlinks"] = True

    # 2. Node.js
    node_ver = _get_node_version()
    info["node_version"] = node_ver or "not found"

    if node_ver is None:
        blockers.append("Node.js не найден. Установите Node.js >= 20 LTS.")
    else:
        try:
            major = int(node_ver.split(".")[0])
            if major < 20:
                blockers.append(
                    f"Node.js v{node_ver} < 20 LTS. "
                    "Рекомендуется v20 или v22 LTS."
                )
            elif major >= 26:
                warnings.append(
                    f"Node.js v{node_ver} — возможна несовместимость "
                    "с нативными модулями. На Termux — штатная версия."
                )
        except ValueError:
            warnings.append(f"Не удалось определить версию Node.js: {node_ver}")

    # 3. Память
    avail_mb = _get_available_memory_mb()
    info["available_memory_mb"] = avail_mb

    if avail_mb == -1:
        warnings.append("Не удалось определить объём доступной памяти.")
    elif avail_mb < 512:
        blockers.append(
            f"Доступно {avail_mb} MB памяти (< 512 MB). "
            "Возможны OOM-падения при сборке."
        )
    elif avail_mb < 1024:
        warnings.append(
            f"Доступно {avail_mb} MB памяти (< 1 GB). "
            "Рекомендуется закрыть фоновые приложения."
        )

    # 4. Артефакты проекта
    for artifact in ("RUNNABLE.md", "CHECKLIST.md", "README.md"):
        path = project_root / artifact
        info[f"has_{artifact.lower().replace('.', '_')}"] = path.exists()
        if not path.exists():
            if artifact in ("RUNNABLE.md", "CHECKLIST.md"):
                blockers.append(
                    f"Отсутствует {artifact} в {project_root}. "
                    "См. PROJECT_REQUIREMENTS.md §2-3."
                )
            else:
                warnings.append(f"Отсутствует {artifact} (рекомендуется).")

    # 5. Порты (проверяем стандартные)
    for port in (8080, 3000, 19000, 19006):
        if _is_port_used(port):
            warnings.append(f"Порт {port} уже занят.")
    info["ports_checked"] = [8080, 3000, 19000, 19006]

    # 6. Python (для Python-проектов)
    if (project_root / "requirements.txt").exists() or list(project_root.glob("*.py")):
        try:
            import yaml  # noqa: F401
            info["pyyaml_available"] = True
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

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    result = diagnose(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["blockers"]:
        print(f"\n❌ BLOCKERS ({len(result['blockers'])}):")
        for b in result["blockers"]:
            print(f"  • {b}")
    if result["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  • {w}")
    if not result["blockers"] and not result["warnings"]:
        print("\n✅ Среда готова к запуску.")
