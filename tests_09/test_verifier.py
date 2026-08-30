#!/usr/bin/env python3
"""
Tests for scripts_01/verifier.py — LEVIATHAN Phase B Verification Framework.

Coverage:
  - VerificationRule dataclass (types, validation, defaults)
  - VerifierStorage CRUD (save, get, list, delete)
  - Verifier: seed_default_rules, list_rules, add_rule, remove_rule
  - Verifier: verify with all check_types
  - Verifier: get_summary, get_results, get_stats
  - Checkers: file_exists, file_contains, pytest, shell, sqlite, http
  - Template resolution
  - CLI integration
  - Edge cases (no rules, unknown check_type, empty context)
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
}
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.verifier import (
    CHECK_TYPES,
    CHECKER_REGISTRY,
    SEVERITY_LEVELS,
    VerificationRule,
    VerificationResult,
    VerificationSummary,
    VerifierStorage,
    Verifier,
    _check_file_exists,
    _check_file_contains,
    _check_sqlite,
    _check_http,
    _resolve_template,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_db() -> Path:
    """Создаёт временный SQLite файл для тестов."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def storage(tmp_db: Path) -> VerifierStorage:
    """VerifierStorage с временной БД."""
    return VerifierStorage(db_path=tmp_db)


@pytest.fixture
def verifier(tmp_db: Path) -> Verifier:
    """Verifier с временной БД."""
    return Verifier(storage=VerifierStorage(db_path=tmp_db))


@pytest.fixture
def sample_rule() -> VerificationRule:
    """Базовое правило для тестов."""
    return VerificationRule(
        name="Test rule",
        description="A test verification rule",
        task_type="test",
        check_type="file_exists",
        check_params={"path": "test_file.py"},
        expected="exists",
        severity="major",
    )


@pytest.fixture
def tmp_dir() -> Path:
    """Временная директория с тестовыми файлами."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        # Создаём тестовый файл
        (path / "test_file.py").write_text("# test content")
        (path / "output.md").write_text("x" * 200)  # > 100 chars
        yield path


# ═══════════════════════════════════════════════════════════════
# Test: VerificationRule
# ═══════════════════════════════════════════════════════════════


class TestVerificationRule:
    """Проверка dataclass VerificationRule."""

    def test_default_rule_id(self):
        """rule_id генерируется автоматически."""
        rule = VerificationRule(name="test", check_type="file_exists")
        assert len(rule.rule_id) == 12

    def test_severity_validation(self):
        """severity валидируется (невалидное → major)."""
        rule = VerificationRule(name="test", check_type="file_exists", severity="invalid")
        assert rule.severity == "major"

    def test_severity_valid_values(self):
        """Все валидные severity проходят."""
        for sev in SEVERITY_LEVELS:
            rule = VerificationRule(name="test", check_type="file_exists", severity=sev)
            assert rule.severity == sev

    def test_weight_clamped(self):
        """weight зажимается в [0, 1]."""
        rule = VerificationRule(name="test", check_type="file_exists", weight=5.0)
        assert rule.weight == 1.0
        rule2 = VerificationRule(name="test", check_type="file_exists", weight=-1.0)
        assert rule2.weight == 0.0

    def test_default_enabled(self):
        """Правило по умолчанию активно."""
        rule = VerificationRule(name="test", check_type="file_exists")
        assert rule.enabled is True

    def test_default_task_type(self):
        """task_type по умолчанию 'any'."""
        rule = VerificationRule(name="test", check_type="file_exists")
        assert rule.task_type == "any"


# ═══════════════════════════════════════════════════════════════
# Test: VerificationResult
# ═══════════════════════════════════════════════════════════════


class TestVerificationResult:
    """Проверка dataclass VerificationResult."""

    def test_default_result_id(self):
        """result_id генерируется автоматически."""
        result = VerificationResult(rule_id="r1", task_id="t1")
        assert len(result.result_id) == 12

    def test_default_verified_by(self):
        """verified_by по умолчанию 'verifier'."""
        result = VerificationResult(rule_id="r1", task_id="t1")
        assert result.verified_by == "verifier"


# ═══════════════════════════════════════════════════════════════
# Test: VerifierStorage CRUD
# ═══════════════════════════════════════════════════════════════


class TestVerifierStorage:
    """Проверка SQLite-хранилища."""

    def test_init_creates_tables(self, tmp_db: Path):
        """При инициализации создаются таблицы."""
        VerifierStorage(db_path=tmp_db)
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "verification_rules" in table_names
        assert "verification_results" in table_names
        conn.close()

    def test_save_and_get_rule(self, storage: VerifierStorage, sample_rule: VerificationRule):
        """Сохранение и получение правила."""
        storage.save_rule(sample_rule)
        retrieved = storage.get_rule(sample_rule.rule_id)
        assert retrieved is not None
        assert retrieved.name == sample_rule.name
        assert retrieved.check_type == sample_rule.check_type
        assert retrieved.check_params == sample_rule.check_params

    def test_delete_rule(self, storage: VerifierStorage, sample_rule: VerificationRule):
        """Удаление правила."""
        storage.save_rule(sample_rule)
        assert storage.delete_rule(sample_rule.rule_id) is True
        assert storage.get_rule(sample_rule.rule_id) is None

    def test_delete_nonexistent_rule(self, storage: VerifierStorage):
        """Удаление несуществующего правила."""
        assert storage.delete_rule("nonexistent") is False

    def test_list_rules(self, storage: VerifierStorage):
        """Список правил."""
        r1 = VerificationRule(name="Rule 1", check_type="file_exists", task_type="test")
        r2 = VerificationRule(name="Rule 2", check_type="pytest", task_type="refactor")
        storage.save_rule(r1)
        storage.save_rule(r2)

        all_rules = storage.list_rules()
        assert len(all_rules) == 2

        filtered = storage.list_rules(task_type="test")
        assert len(filtered) == 1
        assert filtered[0].name == "Rule 1"

    def test_list_rules_enabled_only(self, storage: VerifierStorage):
        """Фильтр только активных правил."""
        r1 = VerificationRule(name="Active", check_type="file_exists", enabled=True)
        r2 = VerificationRule(name="Disabled", check_type="pytest", enabled=False)
        storage.save_rule(r1)
        storage.save_rule(r2)

        enabled = storage.list_rules(enabled_only=True)
        assert len(enabled) == 1
        assert enabled[0].name == "Active"

    def test_save_and_get_result(self, storage: VerifierStorage):
        """Сохранение и получение результатов."""
        result = VerificationResult(rule_id="r1", task_id="task1", passed=True)
        storage.save_result(result)

        results = storage.get_results("task1")
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].rule_id == "r1"

    def test_get_summary(self, storage: VerifierStorage):
        """Сводка по результатам."""
        for i in range(3):
            storage.save_result(VerificationResult(
                rule_id=f"r{i}", task_id="task1", task_type="test", passed=True,
            ))
        storage.save_result(VerificationResult(
            rule_id="r3", task_id="task1", task_type="test", passed=False,
        ))

        summary = storage.get_summary("task1")
        assert summary is not None
        assert summary.total_rules == 4
        assert summary.passed == 3
        assert summary.failed == 1
        assert summary.score == 0.75
        assert summary.status == "verified"  # 0.75 >= 0.7

    def test_get_summary_no_results(self, storage: VerifierStorage):
        """Сводка для задачи без результатов."""
        assert storage.get_summary("nonexistent") is None

    def test_get_stats(self, storage: VerifierStorage):
        """Статистика."""
        storage.save_result(VerificationResult(rule_id="r1", task_id="t1", passed=True))
        storage.save_result(VerificationResult(rule_id="r2", task_id="t1", passed=False))
        storage.save_result(VerificationResult(rule_id="r3", task_id="t2", passed=True))

        stats = storage.get_stats()
        assert stats["total_results"] == 3
        assert stats["total_passed"] == 2
        assert stats["total_failed"] == 1
        assert stats["unique_tasks"] == 2

    def test_count_rules(self, storage: VerifierStorage):
        """Количество правил."""
        assert storage.count_rules() == 0
        storage.save_rule(VerificationRule(name="R1", check_type="file_exists"))
        assert storage.count_rules() == 1


# ═══════════════════════════════════════════════════════════════
# Test: Template resolution
# ═══════════════════════════════════════════════════════════════


class TestTemplateResolution:
    """Проверка _resolve_template."""

    def test_simple_variable(self):
        """Замена {{variable]]."""
        result = _resolve_template("{{path)]/test.py", {"path": "src_06"})
        assert result == "src_06/test.py"

    def test_multiple_variables(self):
        """Несколько переменных."""
        result = _resolve_template("{{dir)]/{{file]].py", {"dir": "src_06", "file": "main"})
        assert result == "src_06/main.py"

    def test_unknown_variable(self):
        """Неизвестная переменная остаётся как есть."""
        result = _resolve_template("{{unknown)]/test.py", {})
        assert result == "{{unknown]]/test.py"

    def test_no_variables(self):
        """Без переменных — без изменений."""
        result = _resolve_template("src_06/main.py", {"foo": "bar"})
        assert result == "src_06/main.py"

    def test_empty_template(self):
        """Пустой шаблон."""
        result = _resolve_template("", {"key": "val"})
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# Test: Verifier
# ═══════════════════════════════════════════════════════════════


class TestVerifier:
    """Проверка Verifier."""

    def test_seed_default_rules(self, verifier: Verifier):
        """Загрузка встроенных правил."""
        count = verifier.seed_default_rules()
        assert count > 0
        rules = verifier.list_rules()
        assert len(rules) == count

    def test_seed_default_rules_idempotent(self, verifier: Verifier):
        """Повторная загрузка не дублирует правила."""
        verifier.seed_default_rules()
        count1 = verifier.seed_default_rules()
        assert count1 == 0  # ничего не добавлено

    def test_seed_default_rules_force(self, verifier: Verifier):
        """Принудительная перезапись."""
        verifier.seed_default_rules()
        count = verifier.seed_default_rules(force=True)
        assert count > 0  # перезаписаны

    def test_add_rule(self, verifier: Verifier):
        """Добавление правила."""
        rule_id = verifier.add_rule(VerificationRule(
            name="Custom", check_type="file_exists",
            check_params={"path": "any.txt"},
        ))
        assert len(rule_id) == 12
        rule = verifier.get_rule(rule_id)
        assert rule is not None
        assert rule.name == "Custom"

    def test_remove_rule(self, verifier: Verifier):
        """Удаление правила."""
        rule_id = verifier.add_rule(VerificationRule(
            name="To remove", check_type="file_exists",
        ))
        assert verifier.remove_rule(rule_id) is True
        assert verifier.get_rule(rule_id) is None

    def test_list_rules_by_type(self, verifier: Verifier):
        """Фильтрация правил по типу задачи."""
        verifier.add_rule(VerificationRule(name="R1", check_type="file_exists", task_type="test"))
        verifier.add_rule(VerificationRule(name="R2", check_type="pytest", task_type="refactor"))

        test_rules = verifier.list_rules(task_type="test")
        assert len(test_rules) == 1
        assert test_rules[0].name == "R1"

    def test_verify_no_rules(self, verifier: Verifier):
        """Если нет подходящих правил — пустой результат."""
        results = verifier.verify(task_id="task1", task_type="unknown_type")
        assert results == []

    def test_verify_with_default_rules(self, verifier: Verifier):
        """Верификация с дефолтными правилами."""
        verifier.seed_default_rules()
        # Имплементация с проверкой файла
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            test_path = f.name
            f.write(b"print('hello')")
        import os
        try:
            results = verifier.verify(
                task_id="task-impl-1",
                task_type="implement",
                context={"output_path": test_path},
            )
            # Должны найти хотя бы одно правило (Check file exists after implementation)
            assert len(results) >= 1
            # Правило file_exists должно пройти
            file_rule = next((r for r in results if r.rule_id and "file" in r.rule_id), None)
        finally:
            os.unlink(test_path)

    def test_verify_unknown_check_type(self, verifier: Verifier):
        """Неизвестный check_type → fail с ошибкой."""
        verifier.add_rule(VerificationRule(
            name="Bad checker", check_type="nonexistent",
        ))
        results = verifier.verify(task_id="task1", task_type="any")
        assert len(results) == 1
        assert results[0].passed is False
        assert "unknown check_type" in results[0].actual.lower()

    def test_get_summary(self, verifier: Verifier):
        """Сводка после верификации."""
        verifier.seed_default_rules()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            test_path = f.name
            f.write(b"print('test')")
        import os
        try:
            verifier.verify(
                task_id="task-summary",
                task_type="implement",
                context={"output_path": test_path},
            )
            summary = verifier.get_summary("task-summary")
            assert summary is not None
            assert summary.task_id == "task-summary"
            assert summary.total_rules > 0
        finally:
            os.unlink(test_path)

    def test_get_results(self, verifier: Verifier, tmp_dir: Path):
        """Результаты после верификации."""
        verifier.add_rule(VerificationRule(
            name="Test result", check_type="file_exists",
            check_params={"path": str(tmp_dir / "test_file.py")},
        ))
        verifier.verify(task_id="task-results", task_type="any")
        results = verifier.get_results("task-results")
        assert len(results) >= 1

    def test_get_stats(self, verifier: Verifier):
        """Статистика Verifier."""
        stats = verifier.get_stats()
        assert "total_rules" in stats
        assert "total_results" in stats

    def test_diagnose(self, verifier: Verifier):
        """Диагностика."""
        diag = verifier.diagnose()
        assert diag["status"] == "ok"
        assert "check_types_available" in diag
        assert len(diag["check_types_available"]) > 0

    def test_eventbus_auto_verification(self, verifier: Verifier):
        """Авто-верификация через EventBus."""
        mock_bus = MagicMock()
        verifier._event_bus = mock_bus
        verifier.start_auto_verification()
        assert len(verifier._subscribers) > 0
        verifier.stop_auto_verification()
        assert len(verifier._subscribers) == 0


# ═══════════════════════════════════════════════════════════════
# Test: Checkers
# ═══════════════════════════════════════════════════════════════


class TestCheckers:
    """Проверка отдельных чекеров."""

    def test_file_exists_found(self, tmp_dir: Path):
        """file_exists находит существующий файл."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_exists({"path": str(tmp_dir / "test_file.py")}, context)
        assert result.passed is True
        assert result.actual == "exists"

    def test_file_exists_not_found(self, tmp_dir: Path):
        """file_exists не находит отсутствующий файл."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_exists({"path": str(tmp_dir / "nonexistent.py")}, context)
        assert result.passed is False
        assert result.actual == "not found"

    def test_file_contains_found(self, tmp_dir: Path):
        """file_contains находит паттерн в файле."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_contains(
            {"path": str(tmp_dir / "test_file.py"), "pattern": "test content"},
            context,
        )
        assert result.passed is True
        assert result.actual == "found"

    def test_file_contains_not_found(self, tmp_dir: Path):
        """file_contains не находит паттерн."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_contains(
            {"path": str(tmp_dir / "test_file.py"), "pattern": "nonexistent pattern"},
            context,
        )
        assert result.passed is False
        assert result.actual == "not found"

    def test_file_contains_min_length(self, tmp_dir: Path):
        """file_contains с паттерном {100,] проверяет длину."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_contains(
            {"path": str(tmp_dir / "output.md"), "pattern": ".{100,}"],
            context,
        )
        assert result.passed is True
        assert "chars" in result.actual

    def test_file_contains_file_not_found(self, tmp_dir: Path):
        """file_contains с несуществующим файлом."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_file_contains(
            {"path": str(tmp_dir / "missing.txt"), "pattern": "test"},
            context,
        )
        assert result.passed is False
        assert "file not found" in result.actual.lower()

    def test_sqlite_query_success(self, tmp_db: Path):
        """sqlite с существующей БД и запросом."""
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1), (2), (3)")
        conn.commit()
        conn.close()

        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_sqlite(
            {"db_path": str(tmp_db), "query": "SELECT COUNT(*) FROM test", "min_rows": 1},
            context,
        )
        assert result.passed is True
        assert "3 rows" in result.actual

    def test_sqlite_query_few_rows(self, tmp_db: Path):
        """sqlite с недостаточным количеством строк."""
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_sqlite(
            {"db_path": str(tmp_db), "query": "SELECT COUNT(*) FROM test", "min_rows": 5},
            context,
        )
        assert result.passed is False
        assert "only" in result.actual

    def test_sqlite_db_not_found(self):
        """sqlite с несуществующей БД."""
        context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
        result = _check_sqlite(
            {"db_path": "/nonexistent/db.sqlite", "query": "SELECT 1"},
            context,
        )
        assert result.passed is False
        assert "db not found" in result.actual.lower()

    def test_http_success(self):
        """http запрос — успешный ответ (мок)."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value = mock_response

            context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
            result = _check_http(
                {"url": "https://example.com/health", "timeout": 5},
                context,
            )
            assert result.passed is True
            assert "HTTP 200" in result.actual

    def test_http_failure(self):
        """http запрос — ошибка (мок)."""
        from urllib.error import HTTPError
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                url="https://example.com/404", code=404, msg="Not Found",
                hdrs={}, fp=None,
            )
            context = {"_rule_id": "r1", "task_id": "t1", "task_type": "test"}
            result = _check_http(
                {"url": "https://example.com/404", "timeout": 5},
                context,
            )
            assert result.passed is False
            assert "HTTP 404" in result.actual

    def test_checker_registry_has_all_types(self):
        """CHECKER_REGISTRY содержит все заявленные типы."""
        for check_type in CHECK_TYPES:
            assert check_type in CHECKER_REGISTRY, f"Missing checker: {check_type}"


# ═══════════════════════════════════════════════════════════════
# Test: Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Краевые случаи."""

    def test_verify_with_empty_context(self, verifier: Verifier):
        """Верификация с пустым контекстом не падает."""
        verifier.seed_default_rules()
        # Используем тип 'research' — там есть правило с file_contains
        results = verifier.verify(task_id="edge-empty", task_type="research", context={})
        # Не должно упасть, даже если нет подходящих файлов
        assert isinstance(results, list)

    def test_verify_same_task_twice(self, verifier: Verifier, tmp_dir: Path):
        """Повторная верификация той же задачи."""
        verifier.add_rule(VerificationRule(
            name="Marker", check_type="file_exists",
            check_params={"path": str(tmp_dir / "test_file.py")},
        ))
        r1 = verifier.verify(task_id="dup-task", task_type="any")
        r2 = verifier.verify(task_id="dup-task", task_type="any")
        assert any(x.passed for x in r1)
        assert any(x.passed for x in r2)
        # Все результаты сохраняются
        all_results = verifier.get_results("dup-task")
        assert len(all_results) == 2

    def test_checker_registry_integrity(self):
        """CHECKER_REGISTRY функции принимают правильные аргументы."""
        for name, checker in CHECKER_REGISTRY.items():
            import inspect
            sig = inspect.signature(checker)
            params = list(sig.parameters.keys())
            assert "params" in params, f"{name}: missing 'params' parameter"
            assert "context" in params, f"{name}: missing 'context' parameter"


# ═══════════════════════════════════════════════════════════════
# Test: Security / Injection Prevention
# ═══════════════════════════════════════════════════════════════


class TestInjectionPrevention:
    """Verify that the verifier cannot be coerced into shell execution
    via templated parameters (Шаг 1, pompts_11/TASK_SECURE_MCP_ACCESS.md)."""

    @pytest.mark.slow  # v5.189.10: тяжеловесный verifier subprocess (~5.3s)
    def test_pytest_injection_via_test_path(self, verifier: Verifier, tmp_path: Path):
        """Метасимволы в test_path не должны выполнять отдельную команду."""
        canary = tmp_path / "pwned_pytest_injection"
        payload = f"tests_09/nonexistent_for_module.py; touch {canary}"
        verifier.add_rule(VerificationRule(
            name="Pytest injection probe",
            check_type="pytest",
            check_params={"test_path": payload, "timeout": 30},
        ))
        verifier.verify(task_id="inj-pytest", task_type="any", context={})
        assert not canary.exists(), (
            "VULNERABILITY: pytest check executed shell-injected payload"
        )

    def test_legacy_shell_rule_rejected(self, verifier: Verifier, tmp_path: Path):
        """Правило с check_type='shell' (больше нет в реестре) не должно
        выполняться; реестр возвращает unknown_check_type."""
        canary = tmp_path / "pwned_legacy_shell"
        verifier.add_rule(VerificationRule(
            name="Legacy shell probe",
            check_type="shell",  # намеренно: удалён из CHECKER_REGISTRY
            check_params={"command": f"touch {canary}"},
        ))
        results = verifier.verify(task_id="inj-shell", task_type="any", context={})
        assert results, "Should still get a result row for unknown check_type"
        assert any("unknown check_type" in r.actual.lower() for r in results), (
            "Legacy shell rule must be rejected by the registry"
        )
        assert not canary.exists(), (
            "VULNERABILITY: shell check_type still executes arbitrary commands"
        )

    def test_seeded_defaults_no_shell(self, verifier: Verifier):
        """После seed DEFAULT_RULES не должно быть правил с check_type='shell'."""
        verifier.seed_default_rules()
        rules = verifier.list_rules()
        assert all(r.check_type != "shell" for r in rules), (
            "DEFAULT_RULES не должны содержать shell check_type после фикса"
        )
