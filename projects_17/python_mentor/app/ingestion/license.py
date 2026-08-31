"""License gate и provenance (Phase B+C, Шаг 5; prompt1 §11–§13).

Правило (ADR-004): `can_be_live(source) <=> source.status == "approved"`.
Никаких «unknown → live». Approval — ручной шаг (реестр YAML, не автоматика).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

VALID_STATUSES = ("pending", "approved", "rejected")


@dataclass(frozen=True)
class ExerciseSource:
    id: str
    source_name: str
    repository: str
    source_url: str
    license: str
    license_evidence: str
    redistribution_allowed: bool
    modification_allowed: bool
    attribution_required: bool
    status: str

    @classmethod
    def from_dict(cls, raw: dict) -> "ExerciseSource":
        status = str(raw["status"]).lower()
        if status not in VALID_STATUSES:
            raise ValueError(f"{raw.get('id')}: bad status {status!r}")
        evidence = str(raw["license_evidence"]).strip()
        if status == "approved" and not evidence:
            raise ValueError(f"{raw.get('id')}: approved без license_evidence — запрещено")
        return cls(
            id=str(raw["id"]),
            source_name=str(raw["source_name"]),
            repository=str(raw["repository"]),
            source_url=str(raw.get("source_url", "")),
            license=str(raw["license"]),
            license_evidence=evidence,
            redistribution_allowed=bool(raw.get("redistribution_allowed", False)),
            modification_allowed=bool(raw.get("modification_allowed", False)),
            attribution_required=bool(raw.get("attribution_required", True)),
            status=status,
        )


def load_sources(path: str | Path) -> list[ExerciseSource]:
    """Загрузить реестр источников из sources.yaml."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    out: list[ExerciseSource] = []
    for s in raw.get("sources", []):
        src = ExerciseSource.from_dict(s)
        if src.status == "approved" and not src.license_evidence:
            raise ValueError(f"{src.id}: approved без license_evidence — запрещено")
        out.append(src)
    return out


def can_be_live(status: str) -> bool:
    """Гейт: только approved."""
    return status == "approved"


def register_sources(conn: sqlite3.Connection, sources: list[ExerciseSource]) -> int:
    """Upsert реестра в exercise_sources. Возвращает число записей."""
    n = 0
    for s in sources:
        conn.execute(
            """
            INSERT INTO exercise_sources (
                id, source_name, repository, source_url, license,
                license_evidence, redistribution_allowed, modification_allowed,
                attribution_required, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                license=excluded.license,
                license_evidence=excluded.license_evidence,
                status=excluded.status
            """,
            (
                s.id, s.source_name, s.repository, s.source_url, s.license,
                s.license_evidence, int(s.redistribution_allowed),
                int(s.modification_allowed), int(s.attribution_required), s.status,
            ),
        )
        n += 1
    conn.commit()
    return n