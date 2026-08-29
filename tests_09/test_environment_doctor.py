"""tests_09/test_environment_doctor.py — Unit tests for Environment Doctor.

Covers: _get_fs_type, _get_node_version, _get_available_memory_mb, _is_port_used,
_check_symlinks, and diagnose() integration.
"""

from __future__ import annotations

import os
import tempfile
***REMOVED***
from unittest.mock import patch, MagicMock, mock_open

import pytest

from core_02.environment_doctor import (
    _get_fs_type,
    _get_node_version,
    _get_available_memory_mb,
    _is_port_used,
    _check_symlinks,
    diagnose,
)


# ─── _get_fs_type ─────────────────────────────────────────────────────────

def test_get_fs_type_stat_success():
    """stat -f возвращает известный тип ФС."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ext4\n", stderr="")
        result = _get_fs_type(Path("/tmp"))
        assert result == "ext4"


def test_get_fs_type_stat_fallback_to_df():
    """stat -f падает → fallback на df -T."""
    with patch("subprocess.run") as mock_run:
        # Первый вызов — stat fails
        # Второй — df succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="stat: error"),
            MagicMock(
                returncode=0,
                stdout="Filesystem   Type  1K-blocks  Used Available Use% Mounted on\n/dev/sda1    ext4   100000  50000   50000   50% /\n",
                stderr="",
            ),
        ***REMOVED***
        result = _get_fs_type(Path("/tmp"))
        assert result == "ext4"


def test_get_fs_type_all_fail():
    """stat и df оба падают → 'unknown'."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("stat not found")
        result = _get_fs_type(Path("/tmp"))
        assert result == "unknown"


def test_get_fs_type_fat32():
    """FAT32 sdcard → 'fuseblk' или 'vfat'."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="fuseblk\n", stderr="")
        result = _get_fs_type(Path("/storage/emulated/0"))
        assert result == "fuseblk"


# ─── _get_node_version ────────────────────────────────────────────────────

def test_get_node_version_success():
    """node --version возвращает корректную строку."""
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/node"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="v26.4.0\n", stderr=""
        )
        result = _get_node_version()
        assert result == "26.4.0"


def test_get_node_version_not_found():
    """Node не установлен → None."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        result = _get_node_version()
        assert result is None


def test_get_node_version_command_fails():
    """node --version падает → None."""
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/node"
        mock_run.side_effect = FileNotFoundError("node not found")
        result = _get_node_version()
        assert result is None


def test_get_node_version_strips_v_prefix():
    """v26.4.0 → 26.4.0 (без v)."""
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/node"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="v20.11.0\n", stderr=""
        )
        result = _get_node_version()
        assert result == "20.11.0"
        assert not result.startswith("v")


# ─── _get_available_memory_mb ─────────────────────────────────────────────

def test_get_memory_success():
    """/proc/meminfo парсится корректно."""
    fake_meminfo = "MemTotal: 3851908 kB\nMemFree: 500000 kB\nMemAvailable: 1242656 kB\n"
    with patch("builtins.open", mock_open(read_data=fake_meminfo)):
        result = _get_available_memory_mb()
        assert result == 1213  # 1242656 / 1024 ≈ 1213


def test_get_memory_file_not_found():
    """/proc/meminfo отсутствует → -1."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = _get_available_memory_mb()
        assert result == -1


def test_get_memory_parse_failure():
    """/proc/meminfo без MemAvailable → -1."""
    fake_meminfo = "MemTotal: 3851908 kB\nMemFree: 500000 kB\n"
    with patch("builtins.open", mock_open(read_data=fake_meminfo)):
        result = _get_available_memory_mb()
        assert result == -1


# ─── _is_port_used ────────────────────────────────────────────────────────

def test_port_used_ss():
    """ss -tlnp показывает занятый порт."""
    fake_output = "LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:((\"node\",pid=1234))\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_output, stderr="")
        assert _is_port_used(8080) is True
        assert _is_port_used(3000) is False


def test_port_used_ss_fallback_netstat():
    """ss падает → fallback на netstat."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            FileNotFoundError("ss not found"),
            MagicMock(
                returncode=0,
                stdout="tcp 0 0 0.0.0.0:8080 0.0.0.0:* LISTEN 1234/node\n",
                stderr="",
            ),
        ***REMOVED***
        assert _is_port_used(8080) is True


def test_port_used_all_fail():
    """ss и netstat оба недоступны → False."""
    with patch("subprocess.run", side_effect=FileNotFoundError("nothing found")):
        assert _is_port_used(8080) is False


# ─── _check_symlinks ──────────────────────────────────────────────────────

def test_symlinks_supported():
    """os.symlink работает → True."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        link_path = tmp_path + ".test_link"
        os.symlink(tmp_path, link_path)
        result = _check_symlinks()
        assert result is True
    finally:
        for p in (tmp_path, tmp_path + ".test_link"):
            if os.path.exists(p):
                os.unlink(p)


def test_symlinks_unsupported():
    """os.symlink падает с OSError на FAT32."""
    with patch("os.symlink", side_effect=OSError(38, "Function not implemented")):
        result = _check_symlinks()
        assert result is False


# ─── diagnose() integration ───────────────────────────────────────────────

def test_diagnose_returns_dict():
    """diagnose() возвращает dict с обязательными ключами."""
    with patch("core_02.environment_doctor._get_fs_type", return_value="ext4"), \
         patch("core_02.environment_doctor._get_node_version", return_value="20.11.0"), \
         patch("core_02.environment_doctor._get_available_memory_mb", return_value=4096), \
         patch("core_02.environment_doctor._is_port_used", return_value=False), \
         patch("core_02.environment_doctor._check_symlinks", return_value=True):
        result = diagnose(Path("/tmp/test_project"))
        assert isinstance(result, dict)
        assert "ok" in result
        assert "blockers" in result
        assert "warnings" in result
        assert "info" in result


def test_diagnose_perfect_environment():
    """Идеальное окружение → ok=True, 0 blockers."""
    with patch("core_02.environment_doctor._get_fs_type", return_value="ext4"), \
         patch("core_02.environment_doctor._get_node_version", return_value="20.11.0"), \
         patch("core_02.environment_doctor._get_available_memory_mb", return_value=8192), \
         patch("core_02.environment_doctor._is_port_used", return_value=False), \
         patch("core_02.environment_doctor._check_symlinks", return_value=True):
        tmp = tempfile.mkdtemp()
        try:
            # Создаём артефакты
            for f in ("RUNNABLE.md", "CHECKLIST.md", "README.md"):
                (Path(tmp) / f).write_text("# test")
            result = diagnose(Path(tmp))
            assert result["ok"***REMOVED*** is True
            assert len(result["blockers"***REMOVED***) == 0
            assert len(result["warnings"***REMOVED***) == 0
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def test_diagnose_fat32_without_runcheck():
    """FAT32 без RUNNABLE.md/CHECKLIST.md → ok=False, blockers."""
    with patch("core_02.environment_doctor._get_fs_type", return_value="fuseblk"), \
         patch("core_02.environment_doctor._get_node_version", return_value="26.4.0"), \
         patch("core_02.environment_doctor._get_available_memory_mb", return_value=512), \
         patch("core_02.environment_doctor._is_port_used", return_value=False), \
         patch("core_02.environment_doctor._check_symlinks", return_value=False):
        tmp = tempfile.mkdtemp()
        try:
            result = diagnose(Path(tmp))
            assert result["ok"***REMOVED*** is False
            assert any("RUNNABLE.md" in b for b in result["blockers"***REMOVED***)
            assert any("CHECKLIST.md" in b for b in result["blockers"***REMOVED***)
            assert any("symlinks" in b.lower() for b in result["blockers"***REMOVED***)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def test_diagnose_low_memory_warning():
    """<1GB память → warning (не blocker)."""
    with patch("core_02.environment_doctor._get_fs_type", return_value="ext4"), \
         patch("core_02.environment_doctor._get_node_version", return_value="20.11.0"), \
         patch("core_02.environment_doctor._get_available_memory_mb", return_value=768), \
         patch("core_02.environment_doctor._is_port_used", return_value=False), \
         patch("core_02.environment_doctor._check_symlinks", return_value=True):
        tmp = tempfile.mkdtemp()
        try:
            for f in ("RUNNABLE.md", "CHECKLIST.md", "README.md"):
                (Path(tmp) / f).write_text("# test")
            result = diagnose(Path(tmp))
            assert result["ok"***REMOVED*** is True  # warning, not blocker
            assert any("памят" in w.lower() or "mb" in w.lower() for w in result["warnings"***REMOVED***)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def test_diagnose_node_too_old():
    """Node < 20 → blocker."""
    with patch("core_02.environment_doctor._get_fs_type", return_value="ext4"), \
         patch("core_02.environment_doctor._get_node_version", return_value="18.7.0"), \
         patch("core_02.environment_doctor._get_available_memory_mb", return_value=4096), \
         patch("core_02.environment_doctor._is_port_used", return_value=False), \
         patch("core_02.environment_doctor._check_symlinks", return_value=True):
        tmp = tempfile.mkdtemp()
        try:
            for f in ("RUNNABLE.md", "CHECKLIST.md", "README.md"):
                (Path(tmp) / f).write_text("# test")
            result = diagnose(Path(tmp))
            assert result["ok"***REMOVED*** is False
            assert any("20" in b for b in result["blockers"***REMOVED***)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
