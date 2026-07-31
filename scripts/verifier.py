#!/usr/bin/env python3
"""
verifier.py — Verification Framework (LEVIATHAN Phase B).

Независимая верификация заявленных результатов. Проверяет, что
задача действительно выполнена, а не просто отмечена как "done".

Система правил (verification_rules):
  - Каждое правило определяет, как проверить результат определённого типа задачи
  - Типы проверок: file_exists, content_match, pytest, shell, sqlite, http
  - Правила сгруппированы по task_type (refactor, test, implement, research)

Жизненный цикл верификации:
  1. Агент завершает задачу → claimed_status='done'
  2. EventBus: task.claimed → Verifier подбирает правила по task_type
  3. Verifier запускает check_command (exists/pytest/shell/sqlite/...)
  4. Verifier пишет verified_status и verified_by
  5. EventBus: task.verified

Использование:
    python scripts/verifier.py verify --task-id xxx --task-type refactor
    python scripts/verifier.py rules list
    python scripts/verifier.py rules add --name "Check file" --task-type refactor ...
    python scripts/verifier.py status --task-id xxx
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
***REMOVED***
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Callable, Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent.parent
VERIFIER_DB = WORKSPACE / "data" / "verifier.db"

# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

CHECK_TYPES = {
    "file_exists": "Проверка существования файла",
    "file_contains": "Проверка содержимого файла (substring/regex)",
    "pytest": "Запуск pytest теста",
    "sqlite": "SQL-запрос к SQLite (check rows/values)",
    "http": "HTTP запрос (check status/body)",
***REMOVED***

SEVERITY_LEVELS = ["critical", "major", "minor"***REMOVED***


@dataclass
class VerificationRule:
    """Одно правило верификации.

    Attributes:
        rule_id: уникальный ID правила
        name: человекочитаемое имя
        description: описание что проверяет
        task_type: тип задачи ("refactor", "test", "implement", "research", "any")
        check_type: тип проверки (file_exists, pytest, shell, ...)
        check_params: параметры проверки (зависят от check_type)
        expected: ожидаемый результат (строка для сравнения)
        severity: критичность (critical/major/minor)
        enabled: активно ли правило
        weight: вес вклада в общий score (0.0-1.0)
        created_at: дата создания
    """
    rule_id: str = ""
    name: str = ""
    description: str = ""
    task_type: str = "any"
    check_type: str = "file_exists"
    check_params: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    expected: str = ""
    severity: str = "major"
    enabled: bool = True
    weight: float = 1.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = uuid.uuid4().hex[:12***REMOVED***
        if self.severity not in SEVERITY_LEVELS:
            self.severity = "major"
        self.weight = max(0.0, min(1.0, self.weight))


@dataclass
class VerificationResult:
    """Результат одной проверки.

    Attributes:
        result_id: уникальный ID результата
        rule_id: ID правила, по которому выполнена проверка
        task_id: ID проверяемой задачи
        task_type: тип задачи
        passed: прошла ли проверка
        actual: фактический результат
        expected: ожидаемый результат
        duration_ms: время выполнения проверки (мс)
        timestamp: время проверки
        verified_by: кто проверил ("verifier", "cli", "auto")
        error: сообщение об ошибке (если была)
    """
    result_id: str = ""
    rule_id: str = ""
    task_id: str = ""
    task_type: str = ""
    passed: bool = False
    actual: str = ""
    expected: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    verified_by: str = "verifier"
    error: str = ""

    def __post_init__(self):
        if not self.result_id:
            self.result_id = uuid.uuid4().hex[:12***REMOVED***


@dataclass
class VerificationSummary:
    """Сводка верификации задачи.

    Attributes:
        task_id: ID задачи
        task_type: тип задачи
        total_rules: сколько правил применено
        passed: сколько проверок прошло
        failed: сколько проверок провалилось
        score: доля успешных проверок (0.0-1.0)
        status: "verified" если score >= threshold, иначе "failed"
        threshold: порог прохождения (0.7 по умолчанию)
        duration_ms: общее время верификации
        timestamp: время проверки
    """
    task_id: str = ""
    task_type: str = ""
    total_rules: int = 0
    passed: int = 0
    failed: int = 0
    score: float = 0.0
    status: str = "pending"
    threshold: float = 0.7
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ═══════════════════════════════════════════════════════════════
# Storage (SQLite persistence for rules and results)
# ═══════════════════════════════════════════════════════════════


class VerifierStorage:
    """SQLite-хранилище для правил и результатов верификации."""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = Path(db_path) if db_path else VERIFIER_DB
        self._init_db()

    def _init_db(self) -> None:
        """Создаёт таблицы verification_rules и verification_results."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS verification_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    task_type TEXT DEFAULT 'any',
                    check_type TEXT NOT NULL,
                    check_params TEXT DEFAULT '{***REMOVED***',
                    expected TEXT DEFAULT '',
                    severity TEXT DEFAULT 'major',
                    enabled INTEGER DEFAULT 1,
                    weight REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS verification_results (
                    result_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_type TEXT DEFAULT '',
                    passed INTEGER NOT NULL,
                    actual TEXT DEFAULT '',
                    expected TEXT DEFAULT '',
                    duration_ms REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL,
                    verified_by TEXT DEFAULT 'verifier',
                    error TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_vr_task_id
                    ON verification_results(task_id);
                CREATE INDEX IF NOT EXISTS idx_vr_rule_id
                    ON verification_results(rule_id);
                CREATE INDEX IF NOT EXISTS idx_vr_task_type
                    ON verification_results(task_type);
                CREATE INDEX IF NOT EXISTS idx_vr_timestamp
                    ON verification_results(timestamp);
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    # ── Rules CRUD ─────────────────────────────────────────

    def save_rule(self, rule: VerificationRule) -> None:
        """Сохраняет правило (upsert)."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO verification_rules
                   (rule_id, name, description, task_type, check_type,
                    check_params, expected, severity, enabled, weight, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule.rule_id, rule.name, rule.description, rule.task_type,
                    rule.check_type, json.dumps(rule.check_params, ensure_ascii=False),
                    rule.expected, rule.severity, int(rule.enabled),
                    rule.weight, rule.created_at,
                ),
            )
            conn.commit()

    def delete_rule(self, rule_id: str) -> bool:
        """Удаляет правило. True если удалено."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM verification_rules WHERE rule_id = ?",
                (rule_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_rule(self, rule_id: str) -> VerificationRule | None:
        """Получает правило по ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM verification_rules WHERE rule_id = ?",
                (rule_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_rule(row)

    def list_rules(self, task_type: str | None = None,
                   enabled_only: bool = False) -> List[VerificationRule***REMOVED***:
        """Список правил с опциональной фильтрацией."""
        query = "SELECT * FROM verification_rules"
        conditions: List[str***REMOVED*** = [***REMOVED***
        params: List[Any***REMOVED*** = [***REMOVED***

        if task_type and task_type != "any":
            conditions.append("(task_type = ? OR task_type = 'any')")
            params.append(task_type)

        if enabled_only:
            conditions.append("enabled = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY severity, weight DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_rule(r) for r in rows***REMOVED***

    def count_rules(self) -> int:
        """Количество правил в БД."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM verification_rules"
            ).fetchone()[0***REMOVED***

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> VerificationRule:
        """Конвертирует строку SQLite в VerificationRule."""
        data = dict(row)
        return VerificationRule(
            rule_id=data["rule_id"***REMOVED***,
            name=data["name"***REMOVED***,
            description=data["description"***REMOVED***,
            task_type=data["task_type"***REMOVED***,
            check_type=data["check_type"***REMOVED***,
            check_params=json.loads(data["check_params"***REMOVED***) if isinstance(data["check_params"***REMOVED***, str) else {***REMOVED***,
            expected=data["expected"***REMOVED***,
            severity=data["severity"***REMOVED***,
            enabled=bool(data["enabled"***REMOVED***),
            weight=float(data["weight"***REMOVED***),
            created_at=data["created_at"***REMOVED***,
        )

    # ── Results CRUD ───────────────────────────────────────

    def save_result(self, result: VerificationResult) -> None:
        """Сохраняет результат проверки."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO verification_results
                   (result_id, rule_id, task_id, task_type, passed,
                    actual, expected, duration_ms, timestamp, verified_by, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.result_id, result.rule_id, result.task_id,
                    result.task_type, int(result.passed), result.actual,
                    result.expected, result.duration_ms, result.timestamp,
                    result.verified_by, result.error,
                ),
            )
            conn.commit()

    def get_results(self, task_id: str) -> List[VerificationResult***REMOVED***:
        """Получает все результаты для задачи."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM verification_results WHERE task_id = ? ORDER BY timestamp",
                (task_id,),
            ).fetchall()
            return [self._row_to_result(r) for r in rows***REMOVED***

    def get_summary(self, task_id: str) -> VerificationSummary | None:
        """Собирает сводку по результатам для задачи."""
        results = self.get_results(task_id)
        if not results:
            return None

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total = len(results)
        score = passed / total if total > 0 else 0.0

        return VerificationSummary(
            task_id=task_id,
            task_type=results[0***REMOVED***.task_type if results else "",
            total_rules=total,
            passed=passed,
            failed=failed,
            score=score,
            status="verified" if score >= 0.7 else "failed",
            threshold=0.7,
        )

    def get_stats(self) -> Dict[str, Any***REMOVED***:
        """Статистика верификации."""
        with self._connect() as conn:
            total_results = conn.execute(
                "SELECT COUNT(*) FROM verification_results"
            ).fetchone()[0***REMOVED***
            total_passed = conn.execute(
                "SELECT COUNT(*) FROM verification_results WHERE passed = 1"
            ).fetchone()[0***REMOVED***
            total_failed = conn.execute(
                "SELECT COUNT(*) FROM verification_results WHERE passed = 0"
            ).fetchone()[0***REMOVED***
            unique_tasks = conn.execute(
                "SELECT COUNT(DISTINCT task_id) FROM verification_results"
            ).fetchone()[0***REMOVED***
            return {
                "total_rules": self.count_rules(),
                "total_results": total_results,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "unique_tasks": unique_tasks,
                "pass_rate": total_passed / total_results if total_results > 0 else 0.0,
            ***REMOVED***

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> VerificationResult:
        """Конвертирует строку SQLite в VerificationResult."""
        data = dict(row)
        return VerificationResult(
            result_id=data["result_id"***REMOVED***,
            rule_id=data["rule_id"***REMOVED***,
            task_id=data["task_id"***REMOVED***,
            task_type=data["task_type"***REMOVED***,
            passed=bool(data["passed"***REMOVED***),
            actual=data["actual"***REMOVED***,
            expected=data["expected"***REMOVED***,
            duration_ms=float(data["duration_ms"***REMOVED***),
            timestamp=data["timestamp"***REMOVED***,
            verified_by=data["verified_by"***REMOVED***,
            error=data["error"***REMOVED***,
        )


# ═══════════════════════════════════════════════════════════════
# Built-in verification rules
# ═══════════════════════════════════════════════════════════════

DEFAULT_RULES: List[VerificationRule***REMOVED*** = [
    VerificationRule(
        name="Check file exists after implementation",
        description="Проверяет, что файл был создан после задачи",
        task_type="implement",
        check_type="file_exists",
        check_params={"path": "{{output_path***REMOVED******REMOVED***"***REMOVED***,
        expected="exists",
        severity="critical",
        weight=1.0,
    ),
    VerificationRule(
        name="Check pytest tests pass",
        description="Запускает тесты и проверяет exit code",
        task_type="test",
        check_type="pytest",
        check_params={"test_path": "{{test_path***REMOVED******REMOVED***", "timeout": 60***REMOVED***,
        expected="0 failures",
        severity="critical",
        weight=1.0,
    ),
    VerificationRule(
        name="Check file contains expected content",
        description="Проверяет, что файл содержит ожидаемый текст",
        task_type="refactor",
        check_type="file_contains",
        check_params={"path": "{{file_path***REMOVED******REMOVED***", "pattern": "{{expected_pattern***REMOVED******REMOVED***"***REMOVED***,
        expected="found",
        severity="major",
        weight=0.8,
    ),
    VerificationRule(
        name="Check SQLite query returns expected rows",
        description="Проверяет результат SQL-запроса",
        task_type="implement",
        check_type="sqlite",
        check_params={
            "db_path": "{{db_path***REMOVED******REMOVED***",
            "query": "{{query***REMOVED******REMOVED***",
            "min_rows": 1,
        ***REMOVED***,
        expected="rows > 0",
        severity="major",
        weight=0.6,
    ),
    VerificationRule(
        name="Check research output has content",
        description="Проверяет, что результат исследования не пустой",
        task_type="research",
        check_type="file_contains",
        check_params={"path": "{{output_path***REMOVED******REMOVED***", "pattern": ".{100,***REMOVED***"***REMOVED***,
        expected="non-empty",
        severity="minor",
        weight=0.5,
    ),
    VerificationRule(
        name="Check HTTP endpoint returns 200",
        description="Проверяет доступность HTTP эндпоинта",
        task_type="implement",
        check_type="http",
        check_params={"url": "{{url***REMOVED******REMOVED***", "timeout": 10***REMOVED***,
        expected="200",
        severity="major",
        weight=0.7,
    ),
***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Checkers (executors for each check_type)
# ═══════════════════════════════════════════════════════════════


def _check_file_exists(params: Dict[str, Any***REMOVED***,
                       context: Dict[str, Any***REMOVED***) -> VerificationResult:
    """Проверяет, существует ли файл."""
    path_template = params.get("path", "")
    path_str = _resolve_template(path_template, context)
    path = Path(path_str)
    if not path.is_absolute():
        path = WORKSPACE / path

    exists = path.exists()
    return VerificationResult(
        rule_id=context.get("_rule_id", ""),
        task_id=context.get("task_id", ""),
        task_type=context.get("task_type", ""),
        passed=exists,
        actual="exists" if exists else "not found",
        expected="exists",
        verified_by="verifier",
    )


def _check_file_contains(params: Dict[str, Any***REMOVED***,
                         context: Dict[str, Any***REMOVED***) -> VerificationResult:
    """Проверяет, что файл содержит ожидаемый паттерн."""
    path_template = params.get("path", "")
    pattern = params.get("pattern", "")
    path_str = _resolve_template(path_template, context)
    pattern = _resolve_template(pattern, context)
    path = Path(path_str)
    if not path.is_absolute():
        path = WORKSPACE / path

    if not path.exists():
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=False,
            actual="file not found",
            expected=pattern,
            error=f"File not found: {path***REMOVED***",
            verified_by="verifier",
        )

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=False,
            actual=f"error: {e***REMOVED***",
            expected=pattern,
            error=str(e),
            verified_by="verifier",
        )

    if pattern == ".{100,***REMOVED***":
        found = len(content) >= 100
        actual = f"{len(content)***REMOVED*** chars" if found else f"too short ({len(content)***REMOVED*** chars)"
    else:
        ***REMOVED***
        try:
            found = bool(re.search(pattern, content, re.DOTALL))
        except re.error:
            found = pattern in content
        actual = "found" if found else "not found"

    return VerificationResult(
        rule_id=context.get("_rule_id", ""),
        task_id=context.get("task_id", ""),
        task_type=context.get("task_type", ""),
        passed=found,
        actual=actual,
        expected=pattern,
        verified_by="verifier",
    )


def _check_pytest(params: Dict[str, Any***REMOVED***,
                  context: Dict[str, Any***REMOVED***) -> VerificationResult:
    """Запускает pytest через argv-список (без shell=True)."""
    test_path_template = params.get("test_path", "")
    timeout = params.get("timeout", 60)
    test_path = _resolve_template(test_path_template, context)

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-q", "--tb=no"***REMOVED***,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKSPACE),
        )
        rc, out, err = result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        rc, out, err = -1, "", "timeout"
    except Exception as e:
        rc, out, err = -2, "", str(e)
    duration_ms = (time.time() - start) * 1000

    passed = rc == 0
    actual = "0 failures" if passed else f"exit code {rc***REMOVED***"

    # Считаем failures из вывода
    if not passed:
        for line in out.split("\n"):
            if "failed" in line:
                actual = line.strip()
                break

    return VerificationResult(
        rule_id=context.get("_rule_id", ""),
        task_id=context.get("task_id", ""),
        task_type=context.get("task_type", ""),
        passed=passed,
        actual=actual,
        expected="0 failures",
        duration_ms=duration_ms,
        error=err if not passed else "",
        verified_by="verifier",
    )


def _check_sqlite(params: Dict[str, Any***REMOVED***,
                  context: Dict[str, Any***REMOVED***) -> VerificationResult:
    """Выполняет SQL-запрос и проверяет результат."""
    db_path_template = params.get("db_path", "")
    query = params.get("query", "")
    min_rows = params.get("min_rows", 1)
    db_path = _resolve_template(db_path_template, context)
    query = _resolve_template(query, context)

    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = WORKSPACE / db_path_obj

    if not db_path_obj.exists():
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=False,
            actual="db not found",
            expected=f"rows >= {min_rows***REMOVED***",
            error=f"DB not found: {db_path_obj***REMOVED***",
            verified_by="verifier",
        )

    start = time.time()
    try:
        conn = sqlite3.connect(str(db_path_obj))
        rows = conn.execute(query).fetchall()
        conn.close()
        duration_ms = (time.time() - start) * 1000
        # Берём значение из первой колонки первой строки (например COUNT(*))
        row_count = rows[0***REMOVED***[0***REMOVED*** if rows else 0
        passed = row_count >= min_rows
        actual = f"{row_count***REMOVED*** rows" if passed else f"only {row_count***REMOVED*** rows (min {min_rows***REMOVED***)"
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=passed,
            actual=actual,
            expected=f"rows >= {min_rows***REMOVED***",
            duration_ms=duration_ms,
            verified_by="verifier",
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=False,
            actual=f"error: {e***REMOVED***",
            expected=f"rows >= {min_rows***REMOVED***",
            duration_ms=duration_ms,
            error=str(e),
            verified_by="verifier",
        )


def _check_http(params: Dict[str, Any***REMOVED***,
                context: Dict[str, Any***REMOVED***) -> VerificationResult:
    """Выполняет HTTP-запрос и проверяет status code."""
    import urllib.request
    import urllib.error

    url_template = params.get("url", "")
    timeout = params.get("timeout", 10)
    expected_status = params.get("expected_status", 200)
    url = _resolve_template(url_template, context)

    start = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.status
        resp.close()
        duration_ms = (time.time() - start) * 1000
        passed = status == expected_status
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=passed,
            actual=f"HTTP {status***REMOVED***",
            expected=f"HTTP {expected_status***REMOVED***",
            duration_ms=duration_ms,
            verified_by="verifier",
        )
    except urllib.error.HTTPError as e:
        duration_ms = (time.time() - start) * 1000
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=e.code == expected_status,
            actual=f"HTTP {e.code***REMOVED***",
            expected=f"HTTP {expected_status***REMOVED***",
            duration_ms=duration_ms,
            error=str(e),
            verified_by="verifier",
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return VerificationResult(
            rule_id=context.get("_rule_id", ""),
            task_id=context.get("task_id", ""),
            task_type=context.get("task_type", ""),
            passed=False,
            actual=f"error: {e***REMOVED***",
            expected=f"HTTP {expected_status***REMOVED***",
            duration_ms=duration_ms,
            error=str(e),
            verified_by="verifier",
        )


# Registry of checkers
CHECKER_REGISTRY: Dict[str, Callable***REMOVED*** = {
    "file_exists": _check_file_exists,
    "file_contains": _check_file_contains,
    "pytest": _check_pytest,
    "sqlite": _check_sqlite,
    "http": _check_http,
***REMOVED***


def _resolve_template(template: str, context: Dict[str, Any***REMOVED***) -> str:
    """Заменяет {{variable***REMOVED******REMOVED*** в шаблоне на значения из context."""
    def replacer(match):
        key = match.group(1)
        return str(context.get(key, match.group(0)))
    return re.sub(r"\{\{(\w+)\***REMOVED***\***REMOVED***", replacer, template)


# ═══════════════════════════════════════════════════════════════
# Verifier
# ═══════════════════════════════════════════════════════════════


class Verifier:
    """Verification Framework — независимая верификация результатов.

    Использование:
        verifier = Verifier()
        verifier.seed_default_rules()

        # Проверить задачу
        results = verifier.verify(
            task_id="wf-123",
            task_type="refactor",
            context={"file_path": "src/router.py", "expected_pattern": "class Router"***REMOVED***,
        )

        # Просмотр сводки
        summary = verifier.get_summary("wf-123")
        print(f"Status: {summary.status***REMOVED***, Score: {summary.score:.0%***REMOVED***")
    """

    def __init__(self, storage: VerifierStorage | None = None,
                 event_bus: Any = None):
        self._storage = storage or VerifierStorage()
        self._event_bus = event_bus  # Optional EventBus
        self._subscribers: List[Any***REMOVED*** = [***REMOVED***  # EventBus subscriptions

    # ── Rule management ────────────────────────────────────

    def seed_default_rules(self, force: bool = False) -> int:
        """Загружает встроенные правила в БД, если их там нет.

        Args:
            force: перезаписать существующие правила

        Returns:
            Количество добавленных правил.
        """
        count = 0
        for rule in DEFAULT_RULES:
            existing = self._storage.get_rule(rule.rule_id)
            if existing and not force:
                continue
            self._storage.save_rule(rule)
            count += 1
        return count

    def add_rule(self, rule: VerificationRule) -> str:
        """Добавляет правило. Возвращает rule_id."""
        self._storage.save_rule(rule)
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="verifier.rule_added",
                    source="verifier",
                    data={
                        "rule_id": rule.rule_id,
                        "name": rule.name,
                        "task_type": rule.task_type,
                        "check_type": rule.check_type,
                    ***REMOVED***,
                ))
            except Exception:
                pass
        return rule.rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """Удаляет правило. Возвращает True если удалено."""
        return self._storage.delete_rule(rule_id)

    def list_rules(self, task_type: str | None = None,
                   enabled_only: bool = False) -> List[VerificationRule***REMOVED***:
        """Список правил."""
        return self._storage.list_rules(task_type=task_type, enabled_only=enabled_only)

    def get_rule(self, rule_id: str) -> VerificationRule | None:
        """Получает правило по ID."""
        return self._storage.get_rule(rule_id)

    # ── Verification ───────────────────────────────────────

    def verify(self, task_id: str, task_type: str = "any",
               context: Dict[str, Any***REMOVED*** | None = None) -> List[VerificationResult***REMOVED***:
        """Запускает верификацию задачи.

        Args:
            task_id: ID задачи
            task_type: тип задачи (refactor, test, implement, research)
            context: контекст с переменными для шаблонов ({{path***REMOVED******REMOVED***, {{file_path***REMOVED******REMOVED***, etc.)

        Returns:
            Список VerificationResult по каждому правилу.
        """
        ctx = dict(context or {***REMOVED***)
        ctx["task_id"***REMOVED*** = task_id
        ctx["task_type"***REMOVED*** = task_type

        # Подбираем правила
        rules = self._storage.list_rules(task_type=task_type, enabled_only=True)
        if not rules:
            # Пробуем без фильтрации по типу
            rules = self._storage.list_rules(enabled_only=True)
            # Фильтруем только 'any'
            rules = [r for r in rules if r.task_type in ("any", task_type)***REMOVED***

        if not rules:
            if self._event_bus is not None:
                try:
                    from scripts.event_bus import Event
                    self._event_bus.publish(Event(
                        type="verifier.no_rules",
                        source="verifier",
                        data={"task_id": task_id, "task_type": task_type***REMOVED***,
                    ))
                except Exception:
                    pass
            return [***REMOVED***

        results: List[VerificationResult***REMOVED*** = [***REMOVED***

        for rule in rules:
            ctx["_rule_id"***REMOVED*** = rule.rule_id
            checker = CHECKER_REGISTRY.get(rule.check_type)
            if checker is None:
                results.append(VerificationResult(
                    rule_id=rule.rule_id,
                    task_id=task_id,
                    task_type=task_type,
                    passed=False,
                    actual="unknown check_type",
                    expected=rule.expected,
                    error=f"No checker for: {rule.check_type***REMOVED***",
                    verified_by="verifier",
                ))
                continue

            try:
                start = time.time()
                result = checker(rule.check_params, ctx)
                result.duration_ms = (time.time() - start) * 1000
                result.rule_id = rule.rule_id
                result.task_id = task_id
                result.task_type = task_type
                result.expected = rule.expected
                results.append(result)
            except Exception as e:
                results.append(VerificationResult(
                    rule_id=rule.rule_id,
                    task_id=task_id,
                    task_type=task_type,
                    passed=False,
                    actual="checker error",
                    expected=rule.expected,
                    error=str(e),
                    verified_by="verifier",
                ))

        # Сохраняем результаты
        for result in results:
            self._storage.save_result(result)

        # Публикуем EventBus
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                summary = self._storage.get_summary(task_id)
                status = summary.status if summary else "unknown"
                self._event_bus.publish(Event(
                    type="task.verified",
                    source="verifier",
                    data={
                        "task_id": task_id,
                        "task_type": task_type,
                        "status": status,
                        "passed": sum(1 for r in results if r.passed),
                        "failed": sum(1 for r in results if not r.passed),
                        "total": len(results),
                    ***REMOVED***,
                ))
            except Exception:
                pass

        return results

    def get_summary(self, task_id: str) -> VerificationSummary | None:
        """Сводка по результатам верификации задачи."""
        return self._storage.get_summary(task_id)

    def get_results(self, task_id: str) -> List[VerificationResult***REMOVED***:
        """Все результаты верификации для задачи."""
        return self._storage.get_results(task_id)

    def get_stats(self) -> Dict[str, Any***REMOVED***:
        """Статистика верификации."""
        return self._storage.get_stats()

    # ── EventBus integration ───────────────────────────────

    def start_auto_verification(self) -> None:
        """Подписывается на task.claimed для авто-верификации."""
        if self._event_bus is None:
            return

        from scripts.event_bus import Event

        def on_task_claimed(event: Event) -> None:
            """Авто-верификация при поступлении task.claimed."""
            task_id = event.data.get("task_id", "")
            task_type = event.data.get("task_type", "any")
            context = event.data.get("context", {***REMOVED***)

            if not task_id:
                return

            results = self.verify(task_id, task_type=task_type, context=context)

        sub = self._event_bus.subscribe("task.claimed", on_task_claimed)
        self._subscribers.append(sub)

    def stop_auto_verification(self) -> None:
        """Отписывается от событий."""
        if self._event_bus is None:
            return
        for sub in self._subscribers:
            self._event_bus.unsubscribe(sub)
        self._subscribers.clear()

    # ── Diagnosis / status ─────────────────────────────────

    def diagnose(self) -> Dict[str, Any***REMOVED***:
        """Диагностика Verifier."""
        stats = self.get_stats()
        rules = self.list_rules()
        return {
            "status": "ok",
            "rules_count": len(rules),
            "rules_enabled": sum(1 for r in rules if r.enabled),
            "check_types_available": list(CHECKER_REGISTRY.keys()),
            "eventbus_connected": self._event_bus is not None,
            "storage": str(self._storage._db_path),
            **stats,
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Colors (CLI)
# ═══════════════════════════════════════════════════════════════

class Colors:
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def status_icon(passed: bool) -> str:
        return f"{Colors.GREEN***REMOVED***✓{Colors.RESET***REMOVED***" if passed else f"{Colors.RED***REMOVED***✗{Colors.RESET***REMOVED***"

    @staticmethod
    def severity_color(severity: str) -> str:
        return {"critical": Colors.RED, "major": Colors.YELLOW, "minor": Colors.BLUE***REMOVED***.get(severity, Colors.RESET)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def _print_header(text: str) -> None:
    print(f"\n{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***{'=' * 60***REMOVED***{Colors.RESET***REMOVED***")
    print(f"{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***  {text***REMOVED***{Colors.RESET***REMOVED***")
    print(f"{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***{'=' * 60***REMOVED***{Colors.RESET***REMOVED***")


def _cmd_verify(args: argparse.Namespace, verifier: Verifier) -> None:
    """Команда: verify — запустить верификацию."""
    context: Dict[str, Any***REMOVED*** = {***REMOVED***
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            print(f"{Colors.RED***REMOVED***Error: invalid JSON in --context{Colors.RESET***REMOVED***")
            sys.exit(1)

    _print_header(f"Verifying task: {args.task_id***REMOVED*** ({args.task_type***REMOVED***)")
    results = verifier.verify(
        task_id=args.task_id,
        task_type=args.task_type,
        context=context,
    )

    if not results:
        print(f"  {Colors.YELLOW***REMOVED***⚠ No rules matched for task_type '{args.task_type***REMOVED***'{Colors.RESET***REMOVED***")
        print(f"  Run 'python scripts/verifier.py rules list' to see available rules")
        return

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for result in results:
        icon = Colors.status_icon(result.passed)
        rule = verifier.get_rule(result.rule_id)
        rule_name = rule.name if rule else result.rule_id[:8***REMOVED***
        print(f"  {icon***REMOVED*** {rule_name***REMOVED***")
        print(f"     Expected: {result.expected***REMOVED***")
        print(f"     Actual:   {result.actual***REMOVED***")
        if result.error:
            print(f"     Error:    {Colors.RED***REMOVED***{result.error***REMOVED***{Colors.RESET***REMOVED***")
        if result.duration_ms > 0:
            print(f"     Duration: {result.duration_ms:.0f***REMOVED***ms")

    score = passed / len(results) if results else 0.0
    summary = verifier.get_summary(args.task_id)

    _print_header("Summary")
    print(f"  {passed***REMOVED***/{len(results)***REMOVED*** passed ({score:.0%***REMOVED***)")
    if summary:
        print(f"  Status: {Colors.GREEN if summary.status == 'verified' else Colors.RED***REMOVED***{summary.status***REMOVED***{Colors.RESET***REMOVED***")
        print(f"  Threshold: {summary.threshold:.0%***REMOVED***")


def _cmd_rules(args: argparse.Namespace, verifier: Verifier) -> None:
    """Команда: rules — управление правилами."""
    if args.action == "list":
        rules = verifier.list_rules(task_type=args.task_type, enabled_only=args.enabled_only)
        _print_header(f"Verification Rules ({len(rules)***REMOVED*** total)")
        if not rules:
            print("  (no rules)")
            return

        for rule in rules:
            sev_color = Colors.severity_color(rule.severity)
            enabled = f"{Colors.GREEN***REMOVED***active{Colors.RESET***REMOVED***" if rule.enabled else f"{Colors.RED***REMOVED***disabled{Colors.RESET***REMOVED***"
            print(f"  {Colors.BOLD***REMOVED***{rule.name***REMOVED***{Colors.RESET***REMOVED*** [{sev_color***REMOVED***{rule.severity***REMOVED***{Colors.RESET***REMOVED******REMOVED*** ({enabled***REMOVED***)")
            print(f"     ID:        {rule.rule_id***REMOVED***")
            print(f"     Type:      {rule.check_type***REMOVED*** | Task: {rule.task_type***REMOVED***")
            print(f"     Desc:      {rule.description***REMOVED***")
            print(f"     Params:    {json.dumps(rule.check_params, ensure_ascii=False)***REMOVED***")
            print()

    elif args.action == "add":
        check_params: Dict[str, Any***REMOVED*** = {***REMOVED***
        if args.params:
            try:
                check_params = json.loads(args.params)
            except json.JSONDecodeError:
                print(f"{Colors.RED***REMOVED***Error: invalid JSON in --params{Colors.RESET***REMOVED***")
                sys.exit(1)

        rule = VerificationRule(
            name=args.name,
            description=args.description or "",
            task_type=args.task_type or "any",
            check_type=args.check_type,
            check_params=check_params,
            expected=args.expected or "",
            severity=args.severity or "major",
            enabled=not args.disabled,
        )
        rule_id = verifier.add_rule(rule)
        print(f"{Colors.GREEN***REMOVED***✓{Colors.RESET***REMOVED*** Rule added: {rule_id***REMOVED***")
        print(f"  Name: {rule.name***REMOVED***")

    elif args.action == "remove":
        if verifier.remove_rule(args.rule_id):
            print(f"{Colors.GREEN***REMOVED***✓{Colors.RESET***REMOVED*** Rule removed: {args.rule_id***REMOVED***")
        else:
            print(f"{Colors.RED***REMOVED***✗{Colors.RESET***REMOVED*** Rule not found: {args.rule_id***REMOVED***")
            sys.exit(1)

    elif args.action == "seed":
        count = verifier.seed_default_rules(force=args.force)
        print(f"{Colors.GREEN***REMOVED***✓{Colors.RESET***REMOVED*** Seeded {count***REMOVED*** default rules")


def _cmd_status(args: argparse.Namespace, verifier: Verifier) -> None:
    """Команда: status — статус верификации задачи."""
    results = verifier.get_results(args.task_id)
    summary = verifier.get_summary(args.task_id)

    if not results and not summary:
        print(f"{Colors.YELLOW***REMOVED***⚠ No verification results for task: {args.task_id***REMOVED***{Colors.RESET***REMOVED***")
        return

    _print_header(f"Verification Status: {args.task_id***REMOVED***")

    if summary:
        status_color = Colors.GREEN if summary.status == "verified" else Colors.RED
        print(f"  Status:   {status_color***REMOVED***{summary.status***REMOVED***{Colors.RESET***REMOVED***")
        print(f"  Score:    {summary.score:.0%***REMOVED*** (threshold: {summary.threshold:.0%***REMOVED***)")
        print(f"  Passed:   {summary.passed***REMOVED***/{summary.total_rules***REMOVED***")
        print(f"  Failed:   {summary.failed***REMOVED***")

    if results:
        print()
        for r in results:
            icon = Colors.status_icon(r.passed)
            rule = verifier.get_rule(r.rule_id)
            rule_name = rule.name if rule else r.rule_id[:8***REMOVED***
            print(f"  {icon***REMOVED*** {rule_name***REMOVED***: {r.actual***REMOVED***")
            if r.error:
                print(f"     Error: {r.error***REMOVED***")


def _cmd_diagnose(args: argparse.Namespace, verifier: Verifier) -> None:
    """Команда: diagnose — диагностика Verifier."""
    diag = verifier.diagnose()
    if args.json:
        print(json.dumps(diag, ensure_ascii=False, indent=2))
        return

    _print_header("Verifier Diagnosis")
    print(f"  Status:            {Colors.GREEN if diag['status'***REMOVED*** == 'ok' else Colors.RED***REMOVED***{diag['status'***REMOVED******REMOVED***{Colors.RESET***REMOVED***")
    print(f"  Rules:             {diag['rules_count'***REMOVED******REMOVED*** ({diag['rules_enabled'***REMOVED******REMOVED*** enabled)")
    print(f"  Check types:       {', '.join(diag['check_types_available'***REMOVED***)***REMOVED***")
    print(f"  EventBus:          {'✅' if diag['eventbus_connected'***REMOVED*** else '❌'***REMOVED***")
    print(f"  Storage:           {diag['storage'***REMOVED******REMOVED***")
    print(f"  Total results:     {diag['total_results'***REMOVED******REMOVED***")
    print(f"  Unique tasks:      {diag['unique_tasks'***REMOVED******REMOVED***")
    print(f"  Pass rate:         {diag['pass_rate'***REMOVED***:.0%***REMOVED***")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifier — Verification Framework (LEVIATHAN Phase B)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/verifier.py verify --task-id wf-123 --task-type refactor --context '{"file_path":"src/main.py","expected_pattern":"def main"***REMOVED***'
  python scripts/verifier.py rules list
  python scripts/verifier.py rules add --name "Check CSS" --check-type file_exists --params '{"path":"src/style.css"***REMOVED***'
  python scripts/verifier.py rules seed
  python scripts/verifier.py status --task-id wf-123
  python scripts/verifier.py diagnose
  python scripts/verifier.py diagnose --json
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # verify
    p_verify = sub.add_parser("verify", help="Запустить верификацию задачи")
    p_verify.add_argument("--task-id", required=True, help="ID задачи")
    p_verify.add_argument("--task-type", default="any", help="Тип задачи (refactor/test/implement/research)")
    p_verify.add_argument("--context", default="{***REMOVED***", help="JSON контекст для шаблонов")

    # rules
    p_rules = sub.add_parser("rules", help="Управление правилами")
    p_rules.add_argument("action", choices=["list", "add", "remove", "seed"***REMOVED***)
    p_rules.add_argument("--name", help="Имя правила (для add)")
    p_rules.add_argument("--description", help="Описание правила")
    p_rules.add_argument("--task-type", help="Тип задачи")
    p_rules.add_argument("--check-type", choices=list(CHECK_TYPES.keys()), help="Тип проверки (для add)")
    p_rules.add_argument("--params", default="{***REMOVED***", help="JSON параметры проверки")
    p_rules.add_argument("--expected", help="Ожидаемый результат")
    p_rules.add_argument("--severity", choices=SEVERITY_LEVELS, default="major", help="Критичность")
    p_rules.add_argument("--disabled", action="store_true", help="Создать неактивное правило")
    p_rules.add_argument("--rule-id", help="ID правила (для remove)")
    p_rules.add_argument("--force", action="store_true", help="Перезаписать существующие (для seed)")
    p_rules.add_argument("--enabled-only", action="store_true", help="Только активные правила (для list)")

    # status
    p_status = sub.add_parser("status", help="Статус верификации задачи")
    p_status.add_argument("--task-id", required=True, help="ID задачи")

    # diagnose
    p_diag = sub.add_parser("diagnose", help="Диагностика Verifier")
    p_diag.add_argument("--json", action="store_true", help="Вывод в JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Init
    verifier = Verifier()
    verifier.seed_default_rules()

    if args.command == "verify":
        _cmd_verify(args, verifier)
    elif args.command == "rules":
        _cmd_rules(args, verifier)
    elif args.command == "status":
        _cmd_status(args, verifier)
    elif args.command == "diagnose":
        _cmd_diagnose(args, verifier)


if __name__ == "__main__":
    main()
