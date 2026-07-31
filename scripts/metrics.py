"""
metrics.py — Metrics Engine (LEVIATHAN Phase C).

5 метрик качества разработки на основе данных верификации:

  1. VCR  (Verified Completion Rate) — доля verified_status='verified_ok'
  2. SRG  (Self-Report Gap) — разница между заявленным и проверенным
  3. CpVO (Cost per Verified Outcome) — стоимость на единицу результата
  4. RRR  (Rework/Rollback Rate) — доля с последующими фиксами
  5. TTD-false (Time-To-Detect false) — время до обнаружения ошибки

Источники данных:
  - context.db → action_verifications таблица (claimed_status, verified_status)
  - verifier.db → verification_results таблица (pass/fail, duration_ms)

Использование:
    python scripts/metrics.py vcr           # VCR метрика
    python scripts/metrics.py srg           # SRG метрика
    python scripts/metrics.py cpvo          # CpVO метрика
    python scripts/metrics.py rrr           # RRR метрика
    python scripts/metrics.py ttd           # TTD-false метрика
    python scripts/metrics.py report        # полный отчёт
    python scripts/metrics.py report --json  # JSON отчёт
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
***REMOVED***
from typing import Any, Dict, List

WORKSPACE = Path(__file__).resolve().parent.parent

CONTEXT_DB = WORKSPACE / "data" / "context.db"
VERIFIER_DB = WORKSPACE / "data" / "verifier.db"
METRICS_DB = WORKSPACE / "data" / "metrics.db"

METRIC_NAMES = {
    "vcr": "Verified Completion Rate",
    "srg": "Self-Report Gap",
    "cpvo": "Cost per Verified Outcome",
    "rrr": "Rework/Rollback Rate",
    "ttd": "Time-To-Detect (false)",
***REMOVED***


@dataclass
class MetricResult:
    """Результат вычисления одной метрики.

    Attributes:
        name: машинное имя метрики (vcr, srg, cpvo, rrr, ttd)
        display_name: человекочитаемое имя
        value: числовое значение
        unit: единица измерения (%, ms, count)
        interpretation: текстовое описание что означает значение
        trend: направление тренда (up/down/stable)
        sample_size: количество записей, на основе которых вычислено
        timestamp: время вычисления
    """

    name: str = ""
    display_name: str = ""
    value: float = 0.0
    unit: str = ""
    interpretation: str = ""
    trend: str = "stable"
    sample_size: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            self.name = str(uuid.uuid4().hex[:12***REMOVED***)
        if not self.display_name:
            self.display_name = METRIC_NAMES.get(self.name, self.name)
        self.value = round(self.value, 4)


@dataclass
class MetricsReport:
    """Полный отчёт со всеми 5 метриками.

    Attributes:
        metrics: словарь {name: MetricResult***REMOVED***
        total_tasks: общее количество задач
        period_start: начало периода
        period_end: конец периода
        duration_ms: время вычисления отчёта
        timestamp: время создания отчёта
    """

    metrics: Dict[str, MetricResult***REMOVED*** = field(default_factory=dict)
    total_tasks: int = 0
    period_start: str = ""
    period_end: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict."""
        return {
            "metrics": {name: asdict(m) for name, m in self.metrics.items()***REMOVED***,
            "total_tasks": self.total_tasks,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        ***REMOVED***


class MetricsEngine:
    """Metrics Engine — вычисление метрик качества разработки.

    Использование:
        engine = MetricsEngine()
        engine.setup_databases()  # проверить что БД существуют
        report = engine.compute_report()
        print(f"VCR: {report.metrics['vcr'***REMOVED***.value:.1%***REMOVED***")
    """

    _context_db: Path | str | None = None
    _verifier_db: Path | str | None = None
    _metrics_db: Path | str | None = None
    _event_bus: Any = None

    def __init__(
        self,
        context_db: Path | str | None = None,
        verifier_db: Path | str | None = None,
        metrics_db: Path | str | None = None,
        event_bus: Any = None,
    ) -> None:
        self._context_db = Path(context_db) if context_db else CONTEXT_DB
        self._verifier_db = Path(verifier_db) if verifier_db else VERIFIER_DB
        self._metrics_db = Path(metrics_db) if metrics_db else METRICS_DB
        self._event_bus = event_bus

    def _connect_ctx(self) -> sqlite3.Connection | None:
        """Connect to context.db (action_verifications table)."""
        if not self._context_db.exists():
            return None
        conn = sqlite3.connect(str(self._context_db))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    def _connect_vrf(self) -> sqlite3.Connection | None:
        """Connect to verifier.db (verification_results table)."""
        if not self._verifier_db.exists():
            return None
        conn = sqlite3.connect(str(self._verifier_db))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    def _init_metrics_db(self) -> None:
        """Инициализирует metrics.db для кэширования результатов."""
        self._metrics_db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self._metrics_db)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metric_snapshots (
                    id TEXT PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT DEFAULT '',
                    sample_size INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    interpretation TEXT DEFAULT '',
                    snapshot_time TEXT NOT NULL,
                    report_id TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    total_tasks INTEGER DEFAULT 0,
                    duration_ms REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ms_metric
                    ON metric_snapshots(metric_name, snapshot_time);
                CREATE INDEX IF NOT EXISTS idx_ms_report
                    ON metric_snapshots(report_id);
            """)
            conn.commit()

    def save_snapshot(self, report: MetricsReport) -> str:
        """Сохраняет сниппет отчёта в metrics.db для отслеживания трендов.

        Returns:
            ID сохранённого отчёта.
        """
        self._init_metrics_db()
        report_id = uuid.uuid4().hex[:12***REMOVED***
        with sqlite3.connect(str(self._metrics_db)) as conn:
            conn.execute(
                "INSERT INTO reports (id, total_tasks, duration_ms, created_at) VALUES (?, ?, ?, ?)",
                (report_id, report.total_tasks, report.duration_ms, report.timestamp),
            )
            for name, metric in report.metrics.items():
                conn.execute(
                    "INSERT INTO metric_snapshots\n"
                    "                       (id, metric_name, value, unit, sample_size, confidence,\n"
                    "                        interpretation, snapshot_time, report_id)\n"
                    "                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex[:12***REMOVED***,
                        name,
                        metric.value,
                        metric.unit,
                        metric.sample_size,
                        metric.confidence,
                        metric.interpretation,
                        metric.timestamp,
                        report_id,
                    ),
                )
            conn.commit()
        return report_id

    def get_trend(self, metric_name: str, limit: int = 10) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Получает историю значений метрики для отслеживания тренда.

        Args:
            metric_name: имя метрики (vcr, srg, cpvo, rrr, ttd)
            limit: количество последних замеров

        Returns:
            Список {value, unit, snapshot_time***REMOVED*** отсортированный по времени.
        """
        self._init_metrics_db()
        with sqlite3.connect(str(self._metrics_db)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT value, unit, sample_size, confidence, snapshot_time\n"
                "                   FROM metric_snapshots\n"
                "                   WHERE metric_name = ?\n"
                "                   ORDER BY snapshot_time DESC\n"
                "                   LIMIT ?",
                (metric_name, limit),
            ).fetchall()
            return [dict(r) for r in rows***REMOVED***

    def compute_vcr(self) -> MetricResult:
        """VCR: доля verified_status='verified_ok'.

        VCR = tasks_with_verified_ok / tasks_with_verification_result

        Высокий VCR (>80%) = здоровый процесс верификации.
        """
        conn = self._connect_ctx()
        if conn is None:
            return MetricResult(
                name="vcr",
                value=0.0,
                unit="%",
                interpretation="No context.db available",
                sample_size=0,
                confidence=0.0,
            )
        try:
            row = conn.execute(
                "SELECT\n"
                "                       COUNT(*) as total,\n"
                "                       SUM(CASE WHEN verified_status = 'verified_ok' THEN 1 ELSE 0 END) as ok_count\n"
                "                   FROM action_verifications\n"
                "                   WHERE verified_status IN ('verified_ok', 'verified_fail')"
            ).fetchone()
            conn.close()
            total = row["total"***REMOVED*** if row and row["total"***REMOVED*** else 0
            ok_count = row["ok_count"***REMOVED*** if row and row["ok_count"***REMOVED*** else 0
            value = ok_count / total if total > 0 else 0.0
            confidence = min(1.0, total / 10)
            if value >= 0.8:
                interpretation = "Высокий уровень верификации (>80%)"
            elif value >= 0.5:
                interpretation = f"Средний уровень ({value:.0%***REMOVED***) — есть задачи без верификации"
            else:
                interpretation = f"Низкий уровень ({value:.0%***REMOVED***) — большинство задач не верифицированы"
            if value >= 0.7:
                trend = "up"
            elif value < 0.3:
                trend = "down"
            else:
                trend = "stable"
            return MetricResult(
                name="vcr",
                value=value,
                unit="%",
                interpretation=interpretation,
                sample_size=total,
                confidence=confidence,
                trend=trend,
            )
        except Exception as e:
            conn.close()
            return MetricResult(
                name="vcr",
                value=0.0,
                unit="%",
                interpretation=f"Error: {e***REMOVED***",
                sample_size=0,
                confidence=0.0,
            )

    def compute_srg(self) -> MetricResult:
        """SRG: разница между заявленным и проверенным.

        SRG = tasks_with_claimed_done_but_not_verified / total_claimed_done

        Высокий SRG = агенты отмечают задачи как done, но верификация не проходит.
        Низкий SRG (<20%) = заявленное соответствует проверенному.
        """
        conn = self._connect_ctx()
        if conn is None:
            return MetricResult(
                name="srg",
                value=0.0,
                unit="%",
                interpretation="No context.db available",
                sample_size=0,
                confidence=0.0,
            )
        try:
            row = conn.execute(
                "SELECT\n"
                "                       COUNT(*) as total_claimed,\n"
                "                       SUM(CASE\n"
                "                           WHEN claimed_status = 'done'\n"
                "                           AND verified_status NOT IN ('verified_ok', 'unverified')\n"
                "                           THEN 1 ELSE 0\n"
                "                       END) as gap_count,\n"
                "                       SUM(CASE WHEN claimed_status = 'done' THEN 1 ELSE 0 END) as done_count\n"
                "                   FROM action_verifications"
            ).fetchone()
            conn.close()
            done_count = row["done_count"***REMOVED*** if row and row["done_count"***REMOVED*** else 0
            gap_count = row["gap_count"***REMOVED*** if row and row["gap_count"***REMOVED*** else 0
            total = row["total_claimed"***REMOVED*** if row and row["total_claimed"***REMOVED*** else 0
            value = gap_count / done_count if done_count > 0 else 0.0
            confidence = min(1.0, total / 10)
            if value <= 0.2:
                interpretation = "Низкий разрыв — заявленное соответствует проверенному"
            elif value <= 0.5:
                interpretation = f"Средний разрыв ({value:.0%***REMOVED***) — часть задач требует доработки"
            else:
                interpretation = f"Высокий разрыв ({value:.0%***REMOVED***) — заявленное часто расходится с проверенным"
            if value <= 0.2:
                trend = "down"
            elif value > 0.5:
                trend = "up"
            else:
                trend = "stable"
            return MetricResult(
                name="srg",
                value=value,
                unit="%",
                interpretation=interpretation,
                sample_size=done_count,
                confidence=confidence,
                trend=trend,
            )
        except Exception as e:
            conn.close()
            return MetricResult(
                name="srg",
                value=0.0,
                unit="%",
                interpretation=f"Error: {e***REMOVED***",
                sample_size=0,
                confidence=0.0,
            )

    def compute_cpvo(self) -> MetricResult:
        """CpVO: средняя длительность верификации на единицу результата.

        CpVO = total_duration_ms / verified_ok_count

        Низкий CpVO = эффективная верификация.
        """
        conn = self._connect_vrf()
        if conn is None:
            return MetricResult(
                name="cpvo",
                value=0.0,
                unit="ms/verification",
                interpretation="No verifier.db available",
                sample_size=0,
                confidence=0.0,
            )
        try:
            row = conn.execute(
                "SELECT\n"
                "                       COUNT(*) as total,\n"
                "                       SUM(duration_ms) as total_duration,\n"
                "                       SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_count\n"
                "                   FROM verification_results"
            ).fetchone()
            conn.close()
            total = row["total"***REMOVED*** if row and row["total"***REMOVED*** else 0
            total_duration = row["total_duration"***REMOVED*** if row and row["total_duration"***REMOVED*** else 0.0
            passed_count = row["passed_count"***REMOVED*** if row and row["passed_count"***REMOVED*** else 0
            value = total_duration / passed_count if passed_count > 0 else 0.0
            confidence = min(1.0, total / 10)
            if value <= 100:
                interpretation = "Низкая стоимость верификации (<100ms/check)"
            elif value <= 1000:
                interpretation = f"Средняя стоимость ({value:.0f***REMOVED***ms/check)"
            else:
                interpretation = f"Высокая стоимость ({value:.0f***REMOVED***ms/check) — возможно, есть медленные проверки"
            if value <= 100:
                trend = "down"
            elif value > 1000:
                trend = "up"
            else:
                trend = "stable"
            return MetricResult(
                name="cpvo",
                value=value,
                unit="ms/verification",
                interpretation=interpretation,
                sample_size=passed_count,
                confidence=confidence,
                trend=trend,
            )
        except Exception as e:
            conn.close()
            return MetricResult(
                name="cpvo",
                value=0.0,
                unit="ms/verification",
                interpretation=f"Error: {e***REMOVED***",
                sample_size=0,
                confidence=0.0,
            )

    def compute_rrr(self) -> MetricResult:
        """RRR: доля задач с последующими фиксами.

        RRR = tasks_claimed_failed_after_verified / total_verified

        Высокий RRR = низкое качество первой реализации.
        """
        conn = self._connect_ctx()
        if conn is None:
            return MetricResult(
                name="rrr",
                value=0.0,
                unit="%",
                interpretation="No context.db available",
                sample_size=0,
                confidence=0.0,
            )
        try:
            row = conn.execute(
                "SELECT\n"
                "                       COUNT(*) as total_verified,\n"
                "                       SUM(CASE\n"
                "                           WHEN verified_status IN ('verified_ok', 'verified_fail')\n"
                "                           AND claimed_status = 'failed'\n"
                "                           THEN 1 ELSE 0\n"
                "                       END) as rework_count,\n"
                "                       SUM(CASE\n"
                "                           WHEN verified_status IN ('verified_ok', 'verified_fail')\n"
                "                           THEN 1 ELSE 0\n"
                "                       END) as verified_count\n"
                "                   FROM action_verifications"
            ).fetchone()
            conn.close()
            verified_count = row["verified_count"***REMOVED*** if row and row["verified_count"***REMOVED*** else 0
            rework_count = row["rework_count"***REMOVED*** if row and row["rework_count"***REMOVED*** else 0
            total = row["total_verified"***REMOVED*** if row and row["total_verified"***REMOVED*** else 0
            value = rework_count / verified_count if verified_count > 0 else 0.0
            confidence = min(1.0, total / 10)
            if value <= 0.1:
                interpretation = "Низкий уровень доработок — качество первой реализации высокое"
            elif value <= 0.3:
                interpretation = f"Средний уровень доработок ({value:.0%***REMOVED***)"
            else:
                interpretation = f"Высокий уровень доработок ({value:.0%***REMOVED***) — требуются улучшения в первой реализации"
            if value <= 0.1:
                trend = "down"
            elif value > 0.3:
                trend = "up"
            else:
                trend = "stable"
            return MetricResult(
                name="rrr",
                value=value,
                unit="%",
                interpretation=interpretation,
                sample_size=verified_count,
                confidence=confidence,
                trend=trend,
            )
        except Exception as e:
            conn.close()
            return MetricResult(
                name="rrr",
                value=0.0,
                unit="%",
                interpretation=f"Error: {e***REMOVED***",
                sample_size=0,
                confidence=0.0,
            )

    def compute_ttd(self) -> MetricResult:
        """TTD-false: среднее время до обнаружения ошибки.

        TTD = avg(verified_at - claimed_at) for verified_fail tasks

        Низкий TTD (<1h) = быстрое обнаружение ошибок.
        """
        conn = self._connect_ctx()
        if conn is None:
            return MetricResult(
                name="ttd",
                value=0.0,
                unit="minutes",
                interpretation="No context.db available",
                sample_size=0,
                confidence=0.0,
            )
        try:
            rows = conn.execute(
                "SELECT created_at, verified_at\n"
                "                   FROM action_verifications\n"
                "                   WHERE verified_status = 'verified_fail'\n"
                "                     AND verified_at != ''\n"
                "                     AND created_at != ''\n"
                "                   ORDER BY created_at DESC\n"
                "                   LIMIT 50"
            ).fetchall()
            conn.close()
            if not rows:
                return MetricResult(
                    name="ttd",
                    value=0.0,
                    unit="minutes",
                    interpretation="Нет данных о проваленных верификациях",
                    sample_size=0,
                    confidence=0.0,
                )
            total_minutes = 0.0
            count = 0
            for row in rows:
                try:
                    created = datetime.fromisoformat(row["created_at"***REMOVED***)
                    verified = datetime.fromisoformat(row["verified_at"***REMOVED***)
                    diff = (verified - created).total_seconds() / 60.0
                    if diff >= 0:
                        total_minutes += diff
                        count += 1
                except (ValueError, TypeError):
                    continue
            value = total_minutes / count if count > 0 else 0.0
            confidence = min(1.0, count / 10)
            if value <= 60:
                interpretation = f"Быстрое обнаружение (~{value:.0f***REMOVED*** мин)"
            elif value <= 1440:
                interpretation = f"Среднее время обнаружения (~{value:.0f***REMOVED*** мин ≈ {value / 60:.1f***REMOVED*** ч)"
            else:
                interpretation = f"Долгое обнаружение (~{value:.0f***REMOVED*** мин ≈ {value / 1440:.1f***REMOVED*** д)"
            if value <= 60:
                trend = "down"
            elif value > 1440:
                trend = "up"
            else:
                trend = "stable"
            return MetricResult(
                name="ttd",
                value=value,
                unit="minutes",
                interpretation=interpretation,
                sample_size=count,
                confidence=confidence,
                trend=trend,
            )
        except Exception as e:
            conn.close()
            return MetricResult(
                name="ttd",
                value=0.0,
                unit="minutes",
                interpretation=f"Error: {e***REMOVED***",
                sample_size=0,
                confidence=0.0,
            )

    def setup_databases(self) -> Dict[str, bool***REMOVED***:
        """Проверяет доступность БД-источников.

        Returns:
            Словарь {db_name: is_available***REMOVED***
        """
        return {
            "context.db": self._context_db.exists(),
            "verifier.db": self._verifier_db.exists(),
            "metrics.db": True,
        ***REMOVED***

    def compute_report(self, save: bool = True) -> MetricsReport:
        """Вычисляет все 5 метрик и возвращает отчёт.

        Args:
            save: сохранить снимок в metrics.db

        Returns:
            MetricsReport со всеми метриками.
        """
        start = time.time()
        vcr = self.compute_vcr()
        srg = self.compute_srg()
        cpvo = self.compute_cpvo()
        rrr = self.compute_rrr()
        ttd = self.compute_ttd()

        conn = self._connect_ctx()
        total_tasks = 0
        if conn is not None:
            try:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM action_verifications"
                ).fetchone()
                if row:
                    total_tasks = row["cnt"***REMOVED***
                conn.close()
            except Exception:
                pass
        duration_ms = (time.time() - start) * 1000

        report = MetricsReport(
            metrics={
                "vcr": vcr,
                "srg": srg,
                "cpvo": cpvo,
                "rrr": rrr,
                "ttd": ttd,
            ***REMOVED***,
            total_tasks=total_tasks,
            duration_ms=duration_ms,
        )
        if save:
            try:
                report_id = self.save_snapshot(report)
                if self._event_bus:
                    from scripts.event_bus import Event

                    self._event_bus.publish(
                        Event(
                            type="metrics.report",
                            source="metrics",
                            data={
                                "report_id": report_id,
                                "total_tasks": total_tasks,
                                "vcr": vcr.value,
                                "srg": srg.value,
                                "cpvo": cpvo.value,
                                "rrr": rrr.value,
                                "ttd": ttd.value,
                                "duration_ms": duration_ms,
                            ***REMOVED***,
                        )
                    )
            except Exception:
                pass
        return report

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Диагностика Metrics Engine.

        Returns:
            Словарь с состоянием всех источников данных.
        """
        dbs = self.setup_databases()
        return {
            "status": "ok",
            "databases": dbs,
            "context_db_path": str(self._context_db),
            "verifier_db_path": str(self._verifier_db),
            "metrics_db_path": str(self._metrics_db),
            "eventbus_connected": self._event_bus is not None,
        ***REMOVED***


class Colors:
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    BLUE = "\x1b[34m"
    CYAN = "\x1b[36m"
    BOLD = "\x1b[1m"
    RESET = "\x1b[0m"


def _print_header(text: str) -> None:
    """Печатает заголовок с рамкой."""
    print(f"\n{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***============================================================{Colors.RESET***REMOVED***")
    print(f"{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***  {text***REMOVED***{Colors.RESET***REMOVED***")
    print(f"{Colors.BOLD***REMOVED***{Colors.CYAN***REMOVED***============================================================{Colors.RESET***REMOVED***")


def _format_metric(metric: MetricResult) -> None:
    """Форматирует вывод одной метрики."""
    if metric.unit == "%":
        value_str = f"{metric.value:.1%***REMOVED***"
    elif metric.unit == "minutes" and metric.value >= 1440:
        value_str = f"{metric.value:.0f***REMOVED*** min ({metric.value / 1440:.1f***REMOVED*** days)"
    elif metric.unit == "minutes":
        value_str = f"{metric.value:.0f***REMOVED*** min ({metric.value / 60:.1f***REMOVED*** h)"
    else:
        value_str = f"{metric.value:.2f***REMOVED*** {metric.unit***REMOVED***"

    trend_icons = {"up": "↑", "down": "↓", "stable": "→"***REMOVED***
    trend_icon = trend_icons.get(metric.trend, "→")

    trend_colors = {
        "vcr": Colors.GREEN if metric.trend == "up" else Colors.RED if metric.trend == "down" else Colors.YELLOW,
        "srg": Colors.GREEN if metric.trend == "down" else Colors.RED if metric.trend == "up" else Colors.YELLOW,
        "cpvo": Colors.GREEN if metric.trend == "down" else Colors.RED if metric.trend == "up" else Colors.YELLOW,
        "rrr": Colors.GREEN if metric.trend == "down" else Colors.RED if metric.trend == "up" else Colors.YELLOW,
        "ttd": Colors.GREEN if metric.trend == "down" else Colors.RED if metric.trend == "up" else Colors.YELLOW,
    ***REMOVED***
    trend_color = trend_colors.get(metric.name, Colors.YELLOW)

    print(f"\n  {Colors.BOLD***REMOVED***{metric.display_name***REMOVED***{Colors.RESET***REMOVED***")
    print(f"    Value:       {Colors.BOLD***REMOVED***{value_str***REMOVED***{Colors.RESET***REMOVED***")
    print(f"    Trend:       {trend_color***REMOVED***{trend_icon***REMOVED*** {metric.trend***REMOVED***{Colors.RESET***REMOVED***")
    print(f"    Samples:     {metric.sample_size***REMOVED***")
    print(f"    Confidence:  {metric.confidence:.0%***REMOVED***")
    print(f"    {metric.interpretation***REMOVED***")


def _cmd_report(args: argparse.Namespace, engine: MetricsEngine) -> None:
    """Команда: report — полный отчёт."""
    start = time.time()
    report = engine.compute_report(save=True)
    duration_ms = (time.time() - start) * 1000

    if args.json:
        data = report.to_dict()
        data["execution_ms"***REMOVED*** = round(duration_ms)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    _print_header(
        f"Metrics Report — {report.total_tasks***REMOVED*** tasks (computed in {duration_ms:.0f***REMOVED***ms)"
    )
    for name in ("vcr", "srg", "cpvo", "rrr", "ttd"):
        if name in report.metrics:
            _format_metric(report.metrics[name***REMOVED***)
    print()

    score = _compute_health_score(report)
    score_color = (
        Colors.GREEN
        if score >= 7
        else Colors.YELLOW
        if score >= 4
        else Colors.RED
    )
    print(f"  {Colors.BOLD***REMOVED***Health Score: {score_color***REMOVED***{score***REMOVED***/10{Colors.RESET***REMOVED***")
    print("  (based on VCR↑, SRG↓, CpVO↓, RRR↓, TTD↓)")
    print()


def _cmd_single(args: argparse.Namespace, engine: MetricsEngine) -> None:
    """Команда: vcr/srg/cpvo/rrr/ttd — одна метрика."""
    metric_name = args.command
    compute_fn = getattr(engine, f"compute_{metric_name***REMOVED***", None)
    if compute_fn is None:
        print(f"{Colors.RED***REMOVED***Unknown metric: {metric_name***REMOVED***{Colors.RESET***REMOVED***")
        sys.exit(1)
    metric = compute_fn()
    if args.json:
        print(json.dumps(asdict(metric), ensure_ascii=False, indent=2))
        return
    _format_metric(metric)
    print()


def _cmd_trend(args: argparse.Namespace, engine: MetricsEngine) -> None:
    """Команда: trend — история метрики."""
    metric_name = args.metric
    if metric_name not in METRIC_NAMES:
        print(
            f"{Colors.RED***REMOVED***Unknown metric: {metric_name***REMOVED***. Available: "
            f"{', '.join(METRIC_NAMES.keys())***REMOVED***{Colors.RESET***REMOVED***"
        )
        sys.exit(1)
    history = engine.get_trend(metric_name, limit=args.limit)
    if args.json:
        print(json.dumps(history, ensure_ascii=False, indent=2))
        return

    _print_header(f"Trend: {METRIC_NAMES[metric_name***REMOVED******REMOVED*** (last {len(history)***REMOVED***)")
    if not history:
        print(f"  {Colors.YELLOW***REMOVED***No history available{Colors.RESET***REMOVED***")
        return
    for entry in reversed(history):
        value = entry["value"***REMOVED***
        if metric_name in ("vcr", "srg", "rrr"):
            value_str = f"{value:.1%***REMOVED***"
        elif metric_name == "cpvo":
            value_str = f"{value:.0f***REMOVED*** ms"
        elif metric_name == "ttd":
            value_str = f"{value:.0f***REMOVED*** min"
        else:
            value_str = f"{value:.2f***REMOVED***"
        ts = entry.get("snapshot_time", "")
        if ts:
            ts = ts[:16***REMOVED***
        print(f"  {ts***REMOVED***  {value_str***REMOVED***  (n={entry['sample_size'***REMOVED******REMOVED***)")
    print()


def _cmd_status(args: argparse.Namespace, engine: MetricsEngine) -> None:
    """Команда: status — диагностика Metrics Engine."""
    status = engine.get_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    _print_header("Metrics Engine Status")
    dbs = status["databases"***REMOVED***
    for name, available in dbs.items():
        icon = f"{Colors.GREEN***REMOVED***✓{Colors.RESET***REMOVED***" if available else f"{Colors.RED***REMOVED***✗{Colors.RESET***REMOVED***"
        print(f"  {icon***REMOVED*** {name***REMOVED***")
    print(f"  EventBus:  {'✅' if status['eventbus_connected'***REMOVED*** else '❌'***REMOVED***")
    print(f"  Status:    {Colors.GREEN***REMOVED***{status['status'***REMOVED******REMOVED***{Colors.RESET***REMOVED***")
    print()


def _compute_health_score(report: MetricsReport) -> int:
    """Вычисляет общий Health Score (0-10) на основе 5 метрик."""
    score = 5
    m = report.metrics
    if "vcr" in m and m["vcr"***REMOVED***.value >= 0.8:
        score += 2
    elif "vcr" in m and m["vcr"***REMOVED***.value >= 0.5:
        score += 1
    if "srg" in m and m["srg"***REMOVED***.value <= 0.2:
        score += 2
    elif "srg" in m and m["srg"***REMOVED***.value <= 0.5:
        score += 1
    if "cpvo" in m and m["cpvo"***REMOVED***.value <= 100:
        score += 1
    if "rrr" in m and m["rrr"***REMOVED***.value <= 0.1:
        score += 1
    elif "rrr" in m and m["rrr"***REMOVED***.value <= 0.3:
        score += 0
    if "ttd" in m and m["ttd"***REMOVED***.value <= 60:
        score += 1
    elif "ttd" in m and m["ttd"***REMOVED***.value <= 1440:
        score += 0.5
    return min(10, max(0, round(score)))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Metrics Engine — 5 метрик качества разработки (LEVIATHAN Phase C)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/metrics.py report           # полный отчёт
  python scripts/metrics.py report --json    # JSON отчёт
  python scripts/metrics.py vcr              # VCR метрика
  python scripts/metrics.py srg              # SRG метрика
  python scripts/metrics.py cpvo             # CpVO метрика
  python scripts/metrics.py rrr              # RRR метрика
  python scripts/metrics.py ttd              # TTD-false метрика
  python scripts/metrics.py trend vcr        # история VCR
  python scripts/metrics.py status           # статус Metrics Engine
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="report",
        choices=["report", "vcr", "srg", "cpvo", "rrr", "ttd", "trend", "status"***REMOVED***,
        help="Команда: report (по умолчанию) или имя метрики",
    )
    parser.add_argument("--json", action="store_true", help="Вывод в JSON")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Лимит для trend (по умолчанию 10)",
    )
    parser.add_argument("--metric", help="Имя метрики для trend")
    args = parser.parse_args()
    engine = MetricsEngine()

    if args.command == "report":
        _cmd_report(args, engine)
        return
    if args.command in ("vcr", "srg", "cpvo", "rrr", "ttd"):
        _cmd_single(args, engine)
        return
    if args.command == "trend":
        if not args.metric:
            print(f"{Colors.RED***REMOVED***Error: --metric is required for trend command{Colors.RESET***REMOVED***")
            print("Usage: python scripts/metrics.py trend --metric vcr")
            sys.exit(1)
        _cmd_trend(args, engine)
        return
    if args.command == "status":
        _cmd_status(args, engine)
        return


if __name__ == "__main__":
    main()
