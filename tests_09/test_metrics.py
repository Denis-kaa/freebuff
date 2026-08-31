#!/usr/bin/env python3
"""
Tests for Metrics Engine (scripts_01/metrics.py).

Tests:
  - MetricResult / MetricsReport serialization
  - Metrics computed from seeded context.db and verifier.db:
    VCR, SRG, CpVO, RRR, TTD-false
  - compute_report with snapshots and trends
  - setup_databases / get_status
  - Graceful degradation without source DBs
  - CLI commands
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.metrics import (
    MetricsEngine,
    MetricResult,
    MetricsReport,
    METRIC_NAMES,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


def _seed_context_db(path: Path, rows: list[tuple]) -> None:
    """Создаёт context.db с таблицей action_verifications.

    Row: (claimed_status, verified_status, created_at, verified_at)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS action_verifications (
                id INTEGER PRIMARY KEY,
                claimed_status TEXT,
                verified_status TEXT,
                created_at TEXT,
                verified_at TEXT
            )
            """
        )
        for claimed, verified, created, verified_at in rows:
            conn.execute(
                "INSERT INTO action_verifications "
                "(claimed_status, verified_status, created_at, verified_at) "
                "VALUES (?, ?, ?, ?)",
                (claimed, verified, created, verified_at),
            )


def _seed_verifier_db(path: Path, rows: list[tuple]) -> None:
    """Создаёт verifier.db с таблицей verification_results.

    Row: (passed, duration_ms)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_results (
                id INTEGER PRIMARY KEY,
                passed INTEGER,
                duration_ms REAL
            )
            """
        )
        for passed, duration_ms in rows:
            conn.execute(
                "INSERT INTO verification_results (passed, duration_ms) VALUES (?, ?)",
                (passed, duration_ms),
            )


@pytest.fixture
def seeded(tmp_path) -> tuple[Path, Path]:
    """Создаёт context.db и verifier.db с детерминированными данными.

    5 задач action_verifications:
      - 3 verified_ok, 2 verified_fail
      - 4 claimed done (2 verified_ok, 2 verified_fail → SRG gap)
      - 1 claimed failed (rework)
      - TTD: verified_fail за 30 минут после created
    """
    now = datetime.now(timezone.utc)
    ctx_rows = [
        ("done", "verified_ok", (now - timedelta(hours=2)).isoformat(), (now - timedelta(hours=1)).isoformat()),
        ("done", "verified_ok", (now - timedelta(hours=3)).isoformat(), (now - timedelta(hours=2)).isoformat()),
        ("done", "verified_fail", (now - timedelta(hours=5)).isoformat(), (now - timedelta(hours=4, minutes=30)).isoformat()),
        ("done", "verified_fail", (now - timedelta(hours=7)).isoformat(), (now - timedelta(hours=6, minutes=30)).isoformat()),
        ("failed", "verified_ok", (now - timedelta(hours=9)).isoformat(), (now - timedelta(hours=8)).isoformat()),
    ]
    ctx_db = tmp_path / "data_13" / "context.db"
    vrf_db = tmp_path / "data_13" / "verifier.db"
    _seed_context_db(ctx_db, ctx_rows)
    _seed_verifier_db(vrf_db, [(1, 50.0), (1, 80.0), (0, 200.0)])
    return ctx_db, vrf_db


@pytest.fixture
def engine(seeded) -> MetricsEngine:
    ctx_db, vrf_db = seeded
    return MetricsEngine(
        context_db=ctx_db,
        verifier_db=vrf_db,
        metrics_db=ctx_db.parent / "metrics.db",
    )


# ═══════════════════════════════════════════════════════════════
# Dataclasses / constants
# ═══════════════════════════════════════════════════════════════


class TestDataclasses:
    def test_metric_names(self):
        assert "vcr" in METRIC_NAMES
        assert "srg" in METRIC_NAMES
        assert "cpvo" in METRIC_NAMES
        assert "rrr" in METRIC_NAMES
        assert "ttd" in METRIC_NAMES

    def test_metric_result_defaults(self):
        m = MetricResult()
        assert m.name != ""
        assert m.trend == "stable"
        assert m.value == 0.0

    def test_metric_result_rounds_value(self):
        m = MetricResult(name="vcr", value=0.66666)
        assert m.value == pytest.approx(0.6667, abs=1e-4)

    def test_metric_result_display_name(self):
        m = MetricResult(name="vcr")
        assert m.display_name == "Verified Completion Rate"

    def test_metrics_report_to_dict(self):
        report = MetricsReport(metrics={"vcr": MetricResult(name="vcr", value=0.8)}, total_tasks=5)
        d = report.to_dict()
        assert d["total_tasks"] == 5
        assert d["metrics"]["vcr"]["value"] == 0.8


# ═══════════════════════════════════════════════════════════════
# Individual metrics
# ═══════════════════════════════════════════════════════════════


class TestMetrics:
    def test_compute_vcr(self, engine: MetricsEngine):
        vcr = engine.compute_vcr()
        assert vcr.name == "vcr"
        # 3 verified_ok из 5 с результатом верификации.
        assert vcr.value == pytest.approx(0.6, abs=1e-6)
        assert vcr.sample_size == 5
        assert vcr.unit == "%"

    def test_compute_srg(self, engine: MetricsEngine):
        srg = engine.compute_srg()
        assert srg.name == "srg"
        # 4 claimed done, из них 2 verified_fail (не ok, не unverified) → gap.
        assert srg.value == pytest.approx(0.5, abs=1e-6)
        assert srg.sample_size == 4

    def test_compute_cpvo(self, engine: MetricsEngine):
        cpvo = engine.compute_cpvo()
        assert cpvo.name == "cpvo"
        # total_duration = 50+80+200 = 330; passed = 2 → 165.
        assert cpvo.value == pytest.approx(165.0, abs=1e-6)
        assert cpvo.unit == "ms/verification"

    def test_compute_rrr(self, engine: MetricsEngine):
        rrr = engine.compute_rrr()
        assert rrr.name == "rrr"
        # verified (ok|fail) = 5; среди них claimed failed = 1 → 0.2.
        assert rrr.value == pytest.approx(0.2, abs=1e-6)
        assert rrr.sample_size == 5

    def test_compute_ttd(self, engine: MetricsEngine):
        ttd = engine.compute_ttd()
        assert ttd.name == "ttd"
        # Два verified_fail: разница 30 минут в каждом.
        assert ttd.value == pytest.approx(30.0, abs=1e-3)
        assert ttd.sample_size == 2
        assert ttd.unit == "minutes"

    def test_confidence_scales_with_sample(self, engine: MetricsEngine):
        vcr = engine.compute_vcr()
        assert vcr.confidence == pytest.approx(0.5, abs=1e-6)  # min(1, 5/10)


# ═══════════════════════════════════════════════════════════════
# Report / snapshots / trends
# ═══════════════════════════════════════════════════════════════


class TestReport:
    def test_compute_report_has_all_metrics(self, engine: MetricsEngine):
        report = engine.compute_report(save=False)
        assert set(report.metrics.keys()) == {"vcr", "srg", "cpvo", "rrr", "ttd"}
        assert report.total_tasks == 5

    def test_compute_report_save_snapshot(self, engine: MetricsEngine):
        report = engine.compute_report(save=True)
        assert isinstance(report, MetricsReport)
        # compute_report сохранил снимок внутри → тренд доступен.
        trend = engine.get_trend("vcr")
        assert len(trend) >= 1
        assert "value" in trend[0]
        assert "snapshot_time" in trend[0]

    def test_save_snapshot_returns_id(self, engine: MetricsEngine):
        report = engine.compute_report(save=False)
        report_id = engine.save_snapshot(report)
        assert isinstance(report_id, str) and len(report_id) > 0

    def test_get_trend_limit(self, engine: MetricsEngine):
        for _ in range(3):
            engine.compute_report(save=True)
        trend = engine.get_trend("vcr", limit=2)
        assert len(trend) <= 2

    def test_get_trend_empty(self, engine: MetricsEngine):
        assert engine.get_trend("vcr") == []

    def test_setup_databases(self, engine: MetricsEngine):
        dbs = engine.setup_databases()
        assert dbs["context.db"] is True
        assert dbs["verifier.db"] is True
        assert dbs["metrics.db"] is True

    def test_get_status(self, engine: MetricsEngine):
        st = engine.get_status()
        assert st["status"] == "ok"
        assert st["databases"]["context.db"] is True
        assert st["eventbus_connected"] is False


# ═══════════════════════════════════════════════════════════════
# Graceful degradation
# ═══════════════════════════════════════════════════════════════


class TestDegradation:
    def test_no_context_db(self, tmp_path):
        engine = MetricsEngine(
            context_db=tmp_path / "missing" / "context.db",
            verifier_db=tmp_path / "missing" / "verifier.db",
            metrics_db=tmp_path / "m.db",
        )
        vcr = engine.compute_vcr()
        assert vcr.value == 0.0
        assert vcr.sample_size == 0
        srg = engine.compute_srg()
        assert srg.value == 0.0
        rrr = engine.compute_rrr()
        assert rrr.value == 0.0

    def test_no_verifier_db(self, tmp_path):
        ctx_db = tmp_path / "context.db"
        _seed_context_db(ctx_db, [("done", "verified_ok", "2026-01-01T00:00:00+00:00", "2026-01-01T00:10:00+00:00")])
        engine = MetricsEngine(
            context_db=ctx_db,
            verifier_db=tmp_path / "missing" / "verifier.db",
            metrics_db=tmp_path / "m.db",
        )
        cpvo = engine.compute_cpvo()
        assert cpvo.value == 0.0
        assert cpvo.sample_size == 0

    def test_report_without_sources(self, tmp_path):
        engine = MetricsEngine(
            context_db=tmp_path / "x" / "context.db",
            verifier_db=tmp_path / "x" / "verifier.db",
            metrics_db=tmp_path / "m.db",
        )
        report = engine.compute_report(save=False)
        assert report.total_tasks == 0
        assert report.metrics["vcr"].value == 0.0

    def test_ttd_no_failures(self, tmp_path):
        ctx_db = tmp_path / "context.db"
        _seed_context_db(ctx_db, [("done", "verified_ok", "2026-01-01T00:00:00+00:00", "2026-01-01T00:10:00+00:00")])
        engine = MetricsEngine(
            context_db=ctx_db,
            verifier_db=tmp_path / "v.db",
            metrics_db=tmp_path / "m.db",
        )
        ttd = engine.compute_ttd()
        assert ttd.value == 0.0
        assert ttd.sample_size == 0


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts_01.metrics import main

        monkeypatch.setattr(sys, "argv", ["metrics.py", "--help"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
