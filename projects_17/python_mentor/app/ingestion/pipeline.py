"""Ingestion pipeline (Phase B+C, Шаг 6; prompt1 §14–§17, §28, §30).

Порядок: discovery → parse → license gate (approved source) →
competency mapping (Шаг 7) → SQLite (INSERT/UPDATE по content_hash).
Идемпотентность: повторный прогон без изменений = 0 новых/обновлений;
изменение файлов упражнения → UPDATE (не INSERT). Dry-run: ничего не пишет.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
}
from typing import Callable

from app.curriculum.map import CompetencyMap
from app.ingestion.license import can_be_live, load_sources, register_sources
from app.ingestion.parser import (
    ExerciseRecord,
    discover_exercises,
    load_track_config,
    parse_exercise,
    track_exercise_meta,
)
from app.storage import open_corpus

SOURCE_ID = "exercism-python"

# Mapping: callable(record) -> list[(competency_id, confidence, source)]
Mapper = Callable[[ExerciseRecord], list[tuple[str, str, str]]]


def rung_from_difficulty(source_difficulty: int) -> str:
    """Детерминированный маппинг difficulty → pedagogical_rung (prompt1 §19)."""
    if source_difficulty <= 1:
        return "repetition"
    if source_difficulty == 2:
        return "analogy"
    if source_difficulty == 3:
        return "new"
    if 4 <= source_difficulty <= 5:
        return "unfamiliar_context"
    if 6 <= source_difficulty <= 7:
        return "combination"
    return "independent"


@dataclass
class IngestReport:
    discovered: int = 0
    parsed: int = 0
    approved_live: int = 0
    pending: int = 0
    skipped: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    concept_count: int = 0
    practice_count: int = 0
    mapped_exercises: int = 0
    low_confidence: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        return {
            "discovered": self.discovered,
            "parsed": self.parsed,
            "approved_live": self.approved_live,
            "pending": self.pending,
            "skipped": self.skipped,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "concept": self.concept_count,
            "practice": self.practice_count,
            "mapped_exercises": self.mapped_exercises,
            "low_confidence": len(self.low_confidence),
            "errors": len(self.errors),
        }


def sync_competencies(conn, cm: CompetencyMap) -> None:
    """Идемпотентная синхронизация карты компетенций в SQLite (двухфазно)."""
    # Фаза 1: все компетенции (чтобы prerequisites могли ссылаться на любые id)
    for c in cm.competencies:
        conn.execute(
            """
            INSERT OR IGNORE INTO competencies (
                id, name, description, category, understand_criteria,
                can_do_criteria, typical_errors_json, verification_exercise,
                project_marker
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                c.id, c.name, c.description, c.category,
                c.understand_criteria, c.can_do_criteria,
                json.dumps(list(c.typical_errors)), c.verification_exercise,
                c.project_marker,
            ),
        )
    # Фаза 2: связи prereq → компетенция
    for c in cm.competencies:
        for p in c.prerequisites:
            conn.execute(
                "INSERT OR IGNORE INTO competency_prerequisites"
                " (competency_id, prerequisite_id) VALUES (?,?)",
                (c.id, p),
            )
    conn.commit()


def ingest(
    source_root: str | Path,
    db_path: str | Path,
    sources_yaml: str | Path,
    *,
    dry_run: bool = False,
    with_refs: bool = False,
    mapper: Mapper | None = None,
    competency_map: CompetencyMap | None = None,
) -> IngestReport:
    """Главная функция: корпус → SQLite (idempotent, license-gated)."""
    report = IngestReport()
    root = Path(source_root)
    if not root.is_dir():
        raise FileNotFoundError(f"source не найден: {root}")

    sources = load_sources(sources_yaml)
    source_status = sources[0].status if sources else "rejected"
    source_approved = can_be_live(source_status)

    conn = None
    if not dry_run:
        conn = open_corpus(db_path)
        register_sources(conn, sources)
        if competency_map is not None:
            sync_competencies(conn, competency_map)

    track = load_track_config(root)
    meta_by_slug = track_exercise_meta(track)

    dirs = discover_exercises(root)
    report.discovered = len(dirs)

    for d in dirs:
        rec = parse_exercise(d, root, meta_by_slug)
        if rec is None:
            report.skipped += 1
            continue
        report.parsed += 1
        if rec.exercise_type == "concept":
            report.concept_count += 1
        else:
            report.practice_count += 1

        if not source_approved:
            report.pending += 1
            continue
        report.approved_live += 1

        if dry_run:
            if mapper is not None:
                matches = mapper(rec)
                if matches:
                    report.mapped_exercises += 1
                    if any(conf == "low" for _, conf, _ in matches):
                        report.low_confidence.append(rec.slug)
            continue

        assert conn is not None  # не dry_run: соединение открыто
        ex_id = f"{SOURCE_ID}:{rec.slug}"
        rung = rung_from_difficulty(rec.source_difficulty)
        ref = rec.reference_solution_ref if with_refs else None

        existing = conn.execute(
            "SELECT content_hash FROM exercises WHERE id=?", (ex_id,)
        ).fetchone()
        if existing is not None and existing["content_hash"] == rec.content_hash:
            report.unchanged += 1
        else:
            conn.execute(
                """
                INSERT INTO exercises (
                    id, source_id, exercise_type, slug, name, blurb,
                    source_difficulty, pedagogical_rung, statement_relpath,
                    tests_relpath, stub_relpath, reference_solution_ref,
                    source_url, content_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, blurb=excluded.blurb,
                    source_difficulty=excluded.source_difficulty,
                    pedagogical_rung=excluded.pedagogical_rung,
                    statement_relpath=excluded.statement_relpath,
                    tests_relpath=excluded.tests_relpath,
                    stub_relpath=excluded.stub_relpath,
                    reference_solution_ref=excluded.reference_solution_ref,
                    source_url=excluded.source_url,
                    content_hash=excluded.content_hash
                """,
                (
                    ex_id, SOURCE_ID, rec.exercise_type, rec.slug, rec.name,
                    rec.blurb, rec.source_difficulty, rung, rec.statement_relpath,
                    rec.tests_relpath, rec.stub_relpath, ref, rec.source_url,
                    rec.content_hash,
                ),
            )
            if existing is None:
                report.inserted += 1
            else:
                report.updated += 1

        if mapper is not None:
            matches = mapper(rec)
            if matches:
                report.mapped_exercises += 1
                conn.execute(
                    "DELETE FROM exercise_competencies WHERE exercise_id=?", (ex_id,)
                )
                for comp_id, conf, src in matches:
                    conn.execute(
                        "INSERT OR REPLACE INTO exercise_competencies"
                        " (exercise_id, competency_id, confidence, source)"
                        " VALUES (?,?,?,?)",
                        (ex_id, comp_id, conf, src),
                    )
                if any(conf == "low" for _, conf, _ in matches):
                    report.low_confidence.append(rec.slug)

    if conn is not None:
        conn.commit()
        conn.close()
    return report