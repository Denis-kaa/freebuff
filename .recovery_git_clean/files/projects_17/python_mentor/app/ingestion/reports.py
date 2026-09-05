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
        f"{'competency':22s***REMOVED*** {'n':>3s***REMOVED*** {'concept':>7s***REMOVED*** {'practice':>8s***REMOVED*** {'diff':>6s***REMOVED***"
    ***REMOVED***
    total = 0
    for r in rows:
        total += r["n"***REMOVED***
        lines.append(
            f"{r['id'***REMOVED***:22s***REMOVED*** {r['n'***REMOVED***:3d***REMOVED*** {r['concepts'***REMOVED***:7d***REMOVED*** {r['practices'***REMOVED***:8d***REMOVED***"
            f" {r['min_d'***REMOVED******REMOVED***-{r['max_d'***REMOVED***:>3d***REMOVED***"
        )
    for c in cm.competencies:
        if not any(r["id"***REMOVED*** == c.id for r in rows):
            lines.append(f"{c.id:22s***REMOVED***   0       0       0     —")
    lines.append(f"{'TOTAL':22s***REMOVED*** {total:3d***REMOVED***")
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
    out = ["Gap-анализ (v0.1, данные не «ремонтируются» автоматически):"***REMOVED***
    gaps = [***REMOVED***
    for r in rows:
        if r["n"***REMOVED*** == 0:
            gaps.append(f"  - {r['cid'***REMOVED******REMOVED***: 0 упражнений (CONTENT GAP)")
        elif r["n"***REMOVED*** == 1:
            gaps.append(f"  - {r['cid'***REMOVED******REMOVED***: 1 упражнение (слабое покрытие)")
        elif r["rungs"***REMOVED*** < 2:
            gaps.append(f"  - {r['cid'***REMOVED******REMOVED***: только 1 rung ({r['rungs'***REMOVED******REMOVED***) — нет прогрессии")
    if not gaps:
        out.append("  пробелов нет")
    else:
        out.extend(gaps)
    out.append(f"\nВсего компетенций с пробелами: {len(gaps)***REMOVED***")
    return "\n".join(out)


def low_confidence_report(conn: sqlite3.Connection) -> list[dict***REMOVED***:
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
            "exercise_id": r["slug"***REMOVED***,
            "current_mapping": r["competency_id"***REMOVED***,
            "confidence": r["confidence"***REMOVED***,
            "source": r["source"***REMOVED***,
            "reason": "ручной override" if r["source"***REMOVED*** == "override" else "одно совпадение concepts / эвристика",
            "source_url": r["source_url"***REMOVED***,
        ***REMOVED***
        for r in rows
    ***REMOVED***


def license_report(conn: sqlite3.Connection) -> list[dict***REMOVED***:
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
            "source_id": r["id"***REMOVED***,
            "name": r["source_name"***REMOVED***,
            "license": r["license"***REMOVED***,
            "status": r["status"***REMOVED***,
            "redistribution_allowed": bool(r["redistribution_allowed"***REMOVED***),
            "modification_allowed": bool(r["modification_allowed"***REMOVED***),
            "attribution_required": bool(r["attribution_required"***REMOVED***),
        ***REMOVED***
        for r in rows
    ***REMOVED***