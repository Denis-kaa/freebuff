"""Отчёты по corpus (Phase B+C, Шаг 8; prompt1 §24–§26).

coverage / gaps / low-confidence / license. Все читают SQLite (только SELECT),
ничего не пишут.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from app.curriculum.map import load_competency_map


def _load_cm():
    return load_competency_map("configs/competency_map.yaml")


def ingest_chart(conn: sqlite3.Connection) -> str:
    """Покрытие по компетенциям: exercise_count, concept/practice split, difficulty."""
    cm = _load_cm()
    rows = conn.execute(
        """
        SELECT c.id, COUNT(e.id) AS n,
               SUM(CASE WHEN e.exercise_type='concept' THEN 1 ELSE 0 END) AS concepts,
               SUM(CASE WHEN e.exercise_type='practice' THEN 1 ELSE 0 END) AS practices,
               MIN(e.source_difficulty) AS min_d, MAX(e.source_difficulty) AS max_d
        FROM exercise_competencies ec
        JOIN exercises e ON e.id = ec.exercise_id
        JOIN competencies c ON c.id = ec.competency_id
        GROUP BY c.id ORDER BY c.id
        """
    ).fetchall()
    lines = [
        f"{'competency':22s} {'n':>3s} {'concept':>7s} {'practice':>8s} {'diff':>6s}"
    ]
    total = 0
    for r in rows:
        total += r["n"]
        lines.append(
            f"{r['id']:22s} {r['n']:3d} {r['concepts']:7d} {r['practices']:8d}"
            f" {r['min_d']}-{r['max_d']:>3d}"
        )
    for c in cm.competencies:
        if not any(r["id"] == c.id for r in rows):
            lines.append(f"{c.id:22s}   0       0       0     —")
    lines.append(f"{'TOTAL':22s} {total:3d}")
    return "\n".join(lines)


def gap_report(conn: sqlite3.Connection) -> str:
    """Gap-анализ (без «ремонта»): компетенции с 0/1 упражнением, rung-пробелы."""
    rows = conn.execute(
        """
        SELECT c.id AS cid, COUNT(ec.exercise_id) AS n,
               COUNT(DISTINCT e.pedagogical_rung) AS rungs
        FROM competencies c
        LEFT JOIN exercise_competencies ec ON ec.competency_id = c.id
        LEFT JOIN exercises e ON e.id = ec.exercise_id
        GROUP BY c.id ORDER BY c.id
        """
    ).fetchall()
    out = ["Gap-анализ (v0.1, данные не «ремонтируются» автоматически):"]
    gaps = []
    for r in rows:
        if r["n"] == 0:
            gaps.append(f"  - {r['cid']}: 0 упражнений (CONTENT GAP)")
        elif r["n"] == 1:
            gaps.append(f"  - {r['cid']}: 1 упражнение (слабое покрытие)")
        elif r["rungs"] < 2:
            gaps.append(f"  - {r['cid']}: только 1 rung ({r['rungs']}) — нет прогрессии")
    if not gaps:
        out.append("  пробелов нет")
    else:
        out.extend(gaps)
    out.append(f"\nВсего компетенций с пробелами: {len(gaps)}")
    return "\n".join(out)


def low_confidence_report(conn: sqlite3.Connection) -> list[dict]:
    """Упражнения с low/medium confidence маппинга (для ручного ревью)."""
    rows = conn.execute(
        """
        SELECT e.slug, ec.competency_id, ec.confidence, ec.source, e.source_url
        FROM exercise_competencies ec
        JOIN exercises e ON e.id = ec.exercise_id
        WHERE ec.confidence IN ('low', 'medium')
        ORDER BY ec.confidence DESC, e.slug
        """
    ).fetchall()
    return [
        {
            "exercise_id": r["slug"],
            "current_mapping": r["competency_id"],
            "confidence": r["confidence"],
            "source": r["source"],
            "reason": "ручной override" if r["source"] == "override" else "одно совпадение concepts / эвристика",
            "source_url": r["source_url"],
        }
        for r in rows
    ]


def license_report(conn: sqlite3.Connection) -> list[dict]:
    """Статус источников и ограничения (из exercise_sources)."""
    rows = conn.execute(
        """
        SELECT id, source_name, license, status,
               redistribution_allowed, modification_allowed, attribution_required
        FROM exercise_sources
        """
    ).fetchall()
    return [
        {
            "source_id": r["id"],
            "name": r["source_name"],
            "license": r["license"],
            "status": r["status"],
            "redistribution_allowed": bool(r["redistribution_allowed"]),
            "modification_allowed": bool(r["modification_allowed"]),
            "attribution_required": bool(r["attribution_required"]),
        }
        for r in rows
    ]