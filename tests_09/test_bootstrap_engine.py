"""
Unit тесты для Bootstrap Engine.

Покрытие: Checker, State, Profiles, Installer, Engine, Doctor
~55 тестов
"""

from __future__ import annotations

import json
import os
import tempfile
***REMOVED***
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, Mock, patch

import pytest
import shutil

WORKSPACE = Path(__file__).resolve().parent.parent
os.chdir(str(WORKSPACE))

from freebuff_plugin_03.bootstrap import (
    BootstrapProfile,
    BootstrapReport,
    DiagnosticReport,
    EnvironmentState,
    InstallResult,
    InstallStep,
    RuntimeDefinition,
)
from freebuff_plugin_03.bootstrap.checker import EnvironmentChecker
from freebuff_plugin_03.bootstrap.state import BootstrapState
from freebuff_plugin_03.bootstrap.installer import IdempotentInstaller
from freebuff_plugin_03.bootstrap.doctor import RuntimeDoctor
from freebuff_plugin_03.bootstrap.engine import BootstrapEngine


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_ws() -> Generator[Path, None, None***REMOVED***:
    """Временная рабочая директория."""
    tmp = Path(tempfile.mkdtemp(prefix="bootstrap_test_"))
    yield tmp
    import shutil
    shutil.rmtree(str(tmp), ignore_errors=True)


@pytest.fixture
def env_state() -> EnvironmentState:
    """Базовое состояние окружения."""
    return EnvironmentState(
        os_type="android",
        is_termux=True,
        python_version="3.14.1",
        node_version="v22.0.0",
        git_available=True,
        disk_free_gb=10.0,
        ram_total_mb=4096,
        ram_available_mb=2048,
        pip_packages={"requests": "2.31.0", "pyyaml": "6.0"***REMOVED***,
        system_packages=["curl", "git"***REMOVED***,
        path_dirs=["/usr/bin", "/data/data/com.termux/files/usr/bin"***REMOVED***,
    )


# ═══════════════════════════════════════════════════════════════
# 1. Types
# ═══════════════════════════════════════════════════════════════


class TestTypes:
    """Tests for bootstrap types - 4 tests"""

    def test_environment_state_defaults(self):
        state = EnvironmentState()
        assert state.os_type == "unknown"
        assert state.is_termux is False
        assert state.disk_free_gb == 0.0

    def test_bootstrap_report_summary(self):
        report = BootstrapReport(
            success=True,
            profile="minimal",
            duration_ms=1500.0,
            steps=[InstallStep(name="check", status="passed")***REMOVED***,
        )
        summary = report.summary()
        assert "✅" in summary
        assert "minimal" in summary
        assert "1500" in summary

    def test_report_has_warnings(self):
        report = BootstrapReport(warnings=["low disk"***REMOVED***)
        assert report.has_warnings() is True
        assert report.has_errors() is False

    def test_runtime_definition_defaults(self):
        rt = RuntimeDefinition(name="freebuff")
        assert rt.version == "latest"
        assert rt.install_type == "pip"


# ═══════════════════════════════════════════════════════════════
# 2. Environment Checker
# ═══════════════════════════════════════════════════════════════


class TestEnvironmentChecker:
    """EnvironmentChecker - 8 tests"""

    def test_check_os_linux(self):
        """Определяет Linux."""
        with patch("platform.system", return_value="linux"):
            with patch("os.environ.get", return_value=None):
                checker = EnvironmentChecker("/tmp")
                state = checker.check_quick()
                assert state.os_type == "linux"

    def test_check_os_termux(self):
        """Определяет Termux (Android)."""
        with patch("platform.system", return_value="linux"):
            with patch.dict(os.environ, {"TERMUX_VERSION": "0.118.0"***REMOVED***):
                checker = EnvironmentChecker("/tmp")
                state = checker.check_quick()
                assert state.os_type == "android"
                assert state.is_termux is True

    def test_check_os_mac(self):
        """Определяет macOS."""
        with patch("platform.system", return_value="darwin"):
            checker = EnvironmentChecker("/tmp")
            state = checker.check_quick()
            assert state.os_type == "mac"

    def test_check_python_version(self):
        """Проверяет версию Python."""
        checker = EnvironmentChecker("/tmp")
        state = checker.check_quick()
        assert state.python_version != ""
        assert "." in state.python_version

    def test_check_git_available(self):
        """Проверяет Git."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            checker = EnvironmentChecker("/tmp")
            state = checker.check_quick()
            assert state.git_available is True

    def test_check_git_not_available(self):
        """Git не найден."""
        with patch("shutil.which", return_value=None):
            checker = EnvironmentChecker("/tmp")
            state = checker.check_quick()
            assert state.git_available is False

    def test_check_disk_space(self, tmp_ws: Path):
        """Проверяет свободное место."""
        checker = EnvironmentChecker(str(tmp_ws))
        state = checker.check_quick()
        assert state.disk_free_gb > 0  # Хотя бы немного места есть

    def test_check_workspace_git(self, tmp_ws: Path):
        """Проверяет git-репозиторий в workspace (через check(), не check_quick())."""
        (tmp_ws / ".git").mkdir()
        checker = EnvironmentChecker(str(tmp_ws))
        state = checker.check()
        assert state.has_git is True


# ═══════════════════════════════════════════════════════════════
# 3. State Management
# ═══════════════════════════════════════════════════════════════


class TestBootstrapState:
    """BootstrapState - 8 tests"""

    def test_load_empty(self, tmp_ws: Path):
        """Загрузка из несуществующего файла."""
        state = BootstrapState(tmp_ws)
        assert state.load() is None

    def test_save_and_load(self, tmp_ws: Path):
        """Сохранение и загрузка."""
        state = BootstrapState(tmp_ws)
        state.save({"profile": "minimal", "status": "complete"***REMOVED***)
        assert (tmp_ws / "bootstrap_state.json").exists()
        data = state.load()
        assert data is not None
        assert data["profile"***REMOVED*** == "minimal"
        assert data["status"***REMOVED*** == "complete"
        assert "timestamp" in data

    def test_is_complete_true(self, tmp_ws: Path):
        """is_complete после успешного сохранения."""
        state = BootstrapState(tmp_ws)
        state.save({"profile": "test", "status": "complete"***REMOVED***)
        assert state.is_complete() is True

    def test_is_complete_false(self, tmp_ws: Path):
        """is_complete без файла."""
        state = BootstrapState(tmp_ws)
        assert state.is_complete() is False

    def test_is_incomplete(self, tmp_ws: Path):
        """is_incomplete после mark_incomplete."""
        state = BootstrapState(tmp_ws)
        state.mark_incomplete()
        assert state.is_incomplete() is True
        assert state.is_complete() is False

    def test_clear(self, tmp_ws: Path):
        """clear удаляет файл."""
        state = BootstrapState(tmp_ws)
        state.save({"test": True***REMOVED***)
        assert (tmp_ws / "bootstrap_state.json").exists()
        state.clear()
        assert not (tmp_ws / "bootstrap_state.json").exists()

    def test_get_component_version(self, tmp_ws: Path):
        """get_component_version."""
        state = BootstrapState(tmp_ws)
        data = {
            "environment": {"python": "3.14.1"***REMOVED***,
            "runtimes": {
                "freebuff": {"installed": True, "version": "1.0.0"***REMOVED***
            ***REMOVED***,
        ***REMOVED***
        state.save(data)
        assert state.get_component_version("python") == "3.14.1"
        assert state.get_component_version("freebuff") == "1.0.0"
        assert state.get_component_version("nonexistent") is None

    def test_to_report_dict(self, tmp_ws: Path, env_state: EnvironmentState):
        """to_report_dict формирует правильную структуру."""
        state = BootstrapState(tmp_ws)
        steps = [InstallStep(name="check_env", status="passed")***REMOVED***
        data = state.to_report_dict(env_state, steps, [***REMOVED***, [***REMOVED***, "minimal")
        assert data["profile"***REMOVED*** == "minimal"
        assert data["environment"***REMOVED***["python"***REMOVED*** == "3.14.1"
        assert data["environment"***REMOVED***["os"***REMOVED*** == "android"
        assert data["steps"***REMOVED***[0***REMOVED***["name"***REMOVED*** == "check_env"


# ═══════════════════════════════════════════════════════════════
# 4. Profiles
# ═══════════════════════════════════════════════════════════════


class TestProfiles:
    """Bootstrap profiles - 5 tests"""

    def test_default_profiles_exist(self):
        """profiles.yaml существует и содержит профили."""
        yaml_path = Path(WORKSPACE) / "freebuff_plugin_03" / "bootstrap" / "profiles.yaml"
        assert yaml_path.exists()

    def test_minimal_profile(self):
        """Профиль minimal."""
        engine = BootstrapEngine(profile="minimal")
        profile = engine._load_profile()
        assert profile is not None
        assert profile.name == "minimal"

    def test_developer_profile(self):
        """Профиль developer."""
        engine = BootstrapEngine(profile="developer")
        profile = engine._load_profile()
        assert profile is not None
        assert profile.name == "developer"
        assert "freebuff" in profile.runtimes

    def test_list_profiles(self):
        """list_profiles возвращает список."""
        engine = BootstrapEngine()
        profiles = engine.list_profiles()
        assert len(profiles) >= 3
        names = [p["name"***REMOVED*** for p in profiles***REMOVED***
        assert "minimal" in names
        assert "developer" in names

    def test_profile_offline_mode(self):
        """Профиль offline имеет offline_mode=True."""
        engine = BootstrapEngine(profile="offline")
        profile = engine._load_profile()
        assert profile is not None
        assert profile.offline_mode is True


# ═══════════════════════════════════════════════════════════════
# 5. Installer
# ═══════════════════════════════════════════════════════════════


class TestInstaller:
    """IdempotentInstaller - 14 tests (4 new: retry logic)"""

    def test_init(self, tmp_ws: Path, env_state: EnvironmentState):
        """Инициализация."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        assert installer.steps == [***REMOVED***

    def test_install_pip_requests(self, tmp_ws: Path, env_state: EnvironmentState):
        """Install pip (mocked)."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = installer._install_pip("requests")
            assert isinstance(result, InstallResult)

    def test_install_system_existing(self, tmp_ws: Path, env_state: EnvironmentState):
        """Установка уже существующего системного пакета."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("shutil.which", return_value="/usr/bin/curl"):
            result = installer._install_system("curl")
            assert result.skip_reason == "already in PATH"

    def test_install_system_new(self, tmp_ws: Path, env_state: EnvironmentState):
        """Установка нового системного пакета."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                result = installer._install_system("nonexistent-pkg")
                assert result.installed is True

    def test_install_system_fails(self, tmp_ws: Path, env_state: EnvironmentState):
        """Ошибка установки системного пакета."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                result = installer._install_system("broken-pkg")
                assert result.installed is False

    def test_install_git_already_cloned(self, tmp_ws: Path, env_state: EnvironmentState):
        """Git clone уже существующего репозитория.

        repo.git → repo name: 'repo'
        dest: workspace/runtimes/repo
        """
        installer = IdempotentInstaller(tmp_ws, env_state)
        dest = tmp_ws / "runtimes" / "repo"
        dest.mkdir(parents=True)
        result = installer._install_git("https://github.com/test/repo.git")
        assert result.skip_reason == "already cloned"

    def test_install_git_new(self, tmp_ws: Path, env_state: EnvironmentState):
        """Git clone нового репозитория."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = installer._install_git(
                "https://github.com/test/repo.git",
                dest_path=str(tmp_ws / "custom_path"),
            )
            assert result.installed is True

    def test_install_git_fails(self, tmp_ws: Path, env_state: EnvironmentState):
        """Ошибка git clone."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("auth error")
            result = installer._install_git("https://github.com/test/repo.git")
            assert result.installed is False

    def test_install_runtime_already_installed(self, tmp_ws: Path, env_state: EnvironmentState):
        """Runtime уже установлен."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        rt = RuntimeDefinition(name="python3", install_type="pip", bin_name="python3")
        with patch("shutil.which", return_value="/usr/bin/python3"):
            result = installer.install_runtime(rt)
            assert result.skip_reason == "already installed"

    def test_install_runtime_unknown_type(self, tmp_ws: Path, env_state: EnvironmentState):
        """Неизвестный тип установки."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        rt = RuntimeDefinition(name="test", install_type="unknown_type", bin_name="test")
        with patch("shutil.which", return_value=None):
            result = installer.install_runtime(rt)
            assert result.installed is False

    # ── Retry logic tests ───────────────────────────────────

    def test_run_with_retry_success_first_try(self, tmp_ws: Path, env_state: EnvironmentState):
        """_run_with_retry: успех с первой попытки."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            success, error, duration, step = installer._run_with_retry(
                ["echo", "ok"***REMOVED***, step_name="test",
            )
            assert success is True
            assert error == ""
            assert step.status == "passed"

    def test_run_with_retry_eventual_success(self, tmp_ws: Path, env_state: EnvironmentState):
        """_run_with_retry: 2 неудачи → успех на 3-й."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                # Первые 2 вызова возвращают returncode=1, третий — 0
                mock_run.side_effect = [
                    type("Result", (), {"returncode": 1, "stderr": "fail1"***REMOVED***)(),
                    type("Result", (), {"returncode": 1, "stderr": "fail2"***REMOVED***)(),
                    type("Result", (), {"returncode": 0, "stderr": ""***REMOVED***)(),
                ***REMOVED***
                success, error, duration, step = installer._run_with_retry(
                    ["cmd"***REMOVED***, max_retries=3, step_name="test_retry",
                )
                assert success is True
                assert mock_run.call_count == 3
                assert mock_sleep.call_count == 2  # 2 sleeps before 3rd try
                assert step.status == "passed"

    def test_run_with_retry_all_fail(self, tmp_ws: Path, env_state: EnvironmentState):
        """_run_with_retry: все 3 попытки неудачны."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "network error"
                success, error, duration, step = installer._run_with_retry(
                    ["cmd"***REMOVED***, max_retries=3, step_name="test_fail",
                )
                assert success is False
                assert "network error" in error
                assert step.status == "failed"
                assert mock_run.call_count == 3
                assert mock_sleep.call_count == 2  # 2 sleeps before 3rd try

    def test_install_pip_uses_retry(self, tmp_ws: Path, env_state: EnvironmentState):
        """_install_pip использует retry: все 3 попытки при неудаче."""
        installer = IdempotentInstaller(tmp_ws, env_state)
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "timeout"
                result = installer._install_pip("broken-pkg")
                assert result.installed is False
                assert mock_run.call_count == 3  # 3 retries
                assert mock_sleep.call_count == 2  # 2 sleeps


# ═══════════════════════════════════════════════════════════════
# 6. Doctor
# ═══════════════════════════════════════════════════════════════


class TestRuntimeDoctor:
    """RuntimeDoctor - 6 tests"""

    def test_diagnose_empty_env(self, tmp_ws: Path):
        """Диагностика пустого окружения."""
        env = EnvironmentState(os_type="linux")
        doctor = RuntimeDoctor(env, tmp_ws)
        report = doctor.diagnose()
        assert isinstance(report, DiagnosticReport)

    def test_diagnose_healthy(self, tmp_ws: Path, env_state: EnvironmentState):
        """Здоровое окружение."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                doctor = RuntimeDoctor(env_state, tmp_ws)
                report = doctor.diagnose()
                assert report.health_score >= 0.5

    def test_diagnose_missing_python(self, tmp_ws: Path):
        """Старая версия Python."""
        env = EnvironmentState(
            os_type="linux",
            python_version="3.9.0",
            path_dirs=["/usr/bin"***REMOVED***,
        )
        doctor = RuntimeDoctor(env, tmp_ws)
        report = doctor.diagnose()
        assert len(report.runtime_issues) >= 1
        assert any("3.9" in i for i in report.runtime_issues)

    def test_diagnose_missing_keys(self, tmp_ws: Path):
        """Отсутствуют ключи."""
        env = EnvironmentState(os_type="linux", path_dirs=["/usr/bin"***REMOVED***)
        doctor = RuntimeDoctor(env, tmp_ws)
        report = doctor.diagnose()
        assert len(report.key_issues) >= 1

    def test_diagnose_missing_deps(self, tmp_ws: Path):
        """Отсутствуют зависимости."""
        env = EnvironmentState(
            os_type="linux",
            pip_packages={***REMOVED***,
            path_dirs=["/usr/bin"***REMOVED***,
        )
        doctor = RuntimeDoctor(env, tmp_ws)
        report = doctor.diagnose()
        assert len(report.dependency_issues) >= 1

    def test_health_score_calculation(self, tmp_ws: Path):
        """Health score calculation."""
        env = EnvironmentState(os_type="linux", path_dirs=[***REMOVED***)
        doctor = RuntimeDoctor(env, tmp_ws)
        report = doctor.diagnose()
        assert 0.0 <= report.health_score <= 1.0


# ═══════════════════════════════════════════════════════════════
# 7. Engine
# ═══════════════════════════════════════════════════════════════


class TestBootstrapEngine:
    """BootstrapEngine - 8 tests"""

    def test_init_defaults(self):
        """Инициализация с дефолтами."""
        engine = BootstrapEngine()
        assert engine._profile_name == "minimal"

    def test_init_with_profile(self):
        """Инициализация с профилем."""
        engine = BootstrapEngine(profile="developer")
        assert engine._profile_name == "developer"

    def test_check(self, tmp_ws: Path):
        """Проверка окружения (mocked subprocess)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws))
            state = engine.check()
            assert isinstance(state, EnvironmentState)
            assert state.python_version != ""

    def test_load_profile_minimal(self, tmp_ws: Path):
        """Загрузка профиля minimal."""
        engine = BootstrapEngine(str(tmp_ws), profile="minimal")
        profile = engine._load_profile()
        assert profile is not None
        assert profile.name == "minimal"

    def test_load_profile_fallback(self, tmp_ws: Path):
        """Fallback при отсутствии profiles.yaml."""
        with patch("freebuff_plugin_03.bootstrap.engine.DEFAULT_PROFILES_PATH",
                   tmp_ws / "nonexistent.yaml"):
            engine = BootstrapEngine(str(tmp_ws), profile="custom")
            profile = engine._load_profile()
            assert profile is not None
            assert profile.name == "minimal"

    def test_get_status_never_run(self, tmp_ws: Path):
        """Статус когда bootstrap никогда не запускался."""
        engine = BootstrapEngine(str(tmp_ws))
        status = engine.get_status()
        assert status["status"***REMOVED*** == "never_run"

    def test_get_status_after_run(self, tmp_ws: Path):
        """Статус после запуска."""
        state_mgr = BootstrapState(tmp_ws)
        state_mgr.save({"profile": "minimal", "status": "complete"***REMOVED***)
        engine = BootstrapEngine(str(tmp_ws))
        status = engine.get_status()
        assert status["status"***REMOVED*** == "complete"
        assert status["profile"***REMOVED*** == "minimal"

    def test_run_completes(self, tmp_ws: Path):
        """Полный цикл bootstrap."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal")
            report = engine.run()
            assert isinstance(report, BootstrapReport)
            assert report.profile == "minimal"
            assert report.environment is not None
            assert report.environment.python_version != ""

    def test_event_bus_emit_started(self, tmp_ws: Path):
        """EventBus: эмитит bootstrap.started при старте."""
        mock_bus = Mock()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal", event_bus=mock_bus)
            engine.run()
            # Проверяем что publish был вызван с bootstrap.started
            calls = [c for c in mock_bus.publish.call_args_list***REMOVED***
            types = [c[0***REMOVED***[0***REMOVED***.type for c in calls***REMOVED***
            assert "bootstrap.started" in types
            assert "bootstrap.checked" in types
            assert "bootstrap.profile_loaded" in types
            assert "bootstrap.completed" in types

    def test_event_bus_emit_failed(self, tmp_ws: Path):
        """EventBus: эмитит bootstrap.failed при ошибке установки."""
        mock_bus = Mock()
        # Mock shutil.which only for freebuff (не мешать curl/git которые реально есть)
        real_which = shutil.which
        def which_only_freebuff(name):
            return None if name == "freebuff" else real_which(name)

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                with patch("shutil.which", side_effect=which_only_freebuff):
                    mock_run.return_value.returncode = 1
                    mock_run.return_value.stderr = "network error"
                    engine = BootstrapEngine(str(tmp_ws), profile="minimal", event_bus=mock_bus)
                    report = engine.run()
                    assert report.success is False
                    calls = [c for c in mock_bus.publish.call_args_list***REMOVED***
                    types = [c[0***REMOVED***[0***REMOVED***.type for c in calls***REMOVED***
                    assert "bootstrap.failed" in types
                    # Verify event data contains the error
                    failed_events = [c for c in mock_bus.publish.call_args_list
                                    if c[0***REMOVED***[0***REMOVED***.type == "bootstrap.failed"***REMOVED***
                    assert len(failed_events) > 0
                    event_data = failed_events[0***REMOVED***[0***REMOVED***[0***REMOVED***.data
                    assert "network error" in str(event_data.get("error", ""))

    def test_event_bus_silent_when_not_configured(self, tmp_ws: Path):
        """EventBus: без event_bus — никаких ошибок."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal")
            report = engine.run()
            assert report.success is True

    def test_event_bus_failure_does_not_break(self, tmp_ws: Path):
        """EventBus: ошибка EventBus не ломает bootstrap."""
        mock_bus = Mock()
        mock_bus.publish.side_effect = Exception("bus error")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal", event_bus=mock_bus)
            report = engine.run()
            assert report.success is True  # Bootstrap работает даже без EventBus


# ═══════════════════════════════════════════════════════════════
# 8. Integration
# ═══════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests - 4 tests"""

    def test_full_bootstrap_cycle(self, tmp_ws: Path):
        """Полный цикл: check → load → install → diagnose → report."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal")
            report = engine.run()
            assert report.environment is not None
            assert report.success is True

    def test_bootstrap_idempotent(self, tmp_ws: Path):
        """Повторный bootstrap — идемпотентность."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine1 = BootstrapEngine(str(tmp_ws), profile="minimal")
            report1 = engine1.run()

            engine2 = BootstrapEngine(str(tmp_ws), profile="minimal")
            report2 = engine2.run()

            assert report1.success is True
            assert report2.success is True

    def test_bootstrap_state_preserved(self, tmp_ws: Path):
        """Состояние сохраняется между запусками."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal")
            engine.run()

            status = engine.get_status()
            assert status["status"***REMOVED*** == "complete"
            assert status["profile"***REMOVED*** == "minimal"

    def test_bootstrap_diagnosis(self, tmp_ws: Path):
        """Bootstrap включает диагностику."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            engine = BootstrapEngine(str(tmp_ws), profile="minimal")
            report = engine.run()
            assert report.diagnosis is not None
