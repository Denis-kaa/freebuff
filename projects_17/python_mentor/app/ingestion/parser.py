"""Discovery и parsing Exercism-корпуса (Phase B+C, Шаг 6; prompt1 §14–§17).

Читает локальный клон data/exercism_src (структура — docs/exercism_research.md §2).
Оффлайн, без сети. Поля упражнения нормализуются из track config.json
и .meta/config.json.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
***REMOVED***
from typing import Any

TRACK_CONFIG_JSON = "config.json"
CONCEPT_DIR = "concept"
PRACTICE_DIR = "practice"
SKIP_FOREGONE = {"lens-person", "nucleotide-count", "parallel-letter-frequency"***REMOVED***


@dataclass(frozen=True)
class ExerciseRecord:
    slug: str
    exercise_type: str  # concept | practice
    name: str
    blurb: str
    source_difficulty: int
    source_concepts: tuple[str, ...***REMOVED***
    statement_relpath: str
    tests_relpath: str
    stub_relpath: str
    reference_solution_ref: str
    source_url: str
    content_hash: str


def load_track_config(source_root: str | Path) -> dict[str, Any***REMOVED***:
    """config.json трека: {exercises: {concept: [...***REMOVED***, practice: [...***REMOVED******REMOVED***, concepts: [...***REMOVED******REMOVED***."""
    with open(Path(source_root) / TRACK_CONFIG_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {***REMOVED***

def _track_meta_entry(entry: dict[str, Any***REMOVED***) -> dict[str, Any***REMOVED***:
    """Нормализация записи упражнения из config.json."""
    return {
        "name": entry.get("name", entry.get("slug", "")),
        "difficulty": int(entry.get("difficulty", 1)),
        "type": entry.get("type", ""),
        "practices": list(entry.get("practices", [***REMOVED***)),
        "prerequisites": list(entry.get("prerequisites", [***REMOVED***)),
        "blurb": entry.get("blurb", ""),
    ***REMOVED***


def track_exercise_meta(track: dict[str, Any***REMOVED***) -> dict[str, dict[str, Any***REMOVED******REMOVED***:
    """slug -> {name, difficulty, practices, prerequisites, blurb***REMOVED*** из config.json."""
    out: dict[str, dict[str, Any***REMOVED******REMOVED*** = {***REMOVED***
    for ex_type in (CONCEPT_DIR, PRACTICE_DIR):
        for entry in track.get("exercises", {***REMOVED***).get(ex_type, [***REMOVED***):
            if not isinstance(entry, dict):
                continue
            slug = entry.get("slug", "")
            out[slug***REMOVED*** = _track_meta_entry(entry)
    return out
    return out


def _rel_to_root(root: Path, path: Path) -> str:
    """Относительный путь от корня клона (exercises/..) либо '' если файла нет."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return ""


def parse_exercise(
    exercise_dir: Path, root: Path, track_by_slug: dict[str, dict***REMOVED***
) -> ExerciseRecord | None:
    """Разобрать одно упражнение из локального клона."""
    if not exercise_dir.is_dir():
        return None
    slug = exercise_dir.name
    if slug in SKIP_FOREGONE:
        return None
    ex_type = exercise_dir.parent.name
    if ex_type not in (CONCEPT_DIR, PRACTICE_DIR):
        return None

    meta: dict = {***REMOVED***
    meta_path = exercise_dir / ".meta" / "config.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    track = track_by_slug.get(slug, {***REMOVED***)

    # Statement: .docs/instructions.md (у части practice — README.md)
    statement = exercise_dir / ".docs" / "instructions.md"
    if not statement.exists():
        statement = exercise_dir / "README.md"

    # Stub: из .meta files.solution, иначе slug.py, иначе первый *.py без _test
    stub = exercise_dir / f"{slug.replace('-', '_')***REMOVED***.py"
    if not stub.exists():
        sol_rel = (meta.get("files") or {***REMOVED***).get("solution") or [***REMOVED***
        stub = exercise_dir / sol_rel[0***REMOVED*** if sol_rel else stub
        if not stub.exists():
            candidates = sorted(p for p in exercise_dir.glob("*.py") if "_test" not in p.name)
            if candidates:
                stub = candidates[0***REMOVED***

    # Tests
    tests = exercise_dir / f"{slug.replace('-', '_')***REMOVED***_test.py"
    if not tests.exists():
        tst_rel = (meta.get("files") or {***REMOVED***).get("test") or [***REMOVED***
        tests = exercise_dir / tst_rel[0***REMOVED*** if tst_rel else tests

    # Reference solution
    ref = exercise_dir / ".meta" / ("exemplar.py" if ex_type == CONCEPT_DIR else "example.py")
    if not ref.exists():
        ref = exercise_dir / ".meta" / "example.py"
    if not ref.exists():
        ref = exercise_dir / ".meta" / "exemplar.py"

    return ExerciseRecord(
        slug=slug,
        exercise_type=ex_type,
        name=str(track.get("name") or meta.get("name") or slug),
        blurb=str(meta.get("blurb") or track.get("blurb") or ""),
        source_difficulty=int(track.get("difficulty", 1)),
        source_concepts=tuple(track.get("practices", [***REMOVED***)) + tuple(track.get("prerequisites", [***REMOVED***)),
        statement_relpath=_rel_to_root(root, statement) if statement.exists() else "",
        tests_relpath=_rel_to_root(root, tests) if tests.exists() else "",
        stub_relpath=_rel_to_root(root, stub) if stub.exists() else "",
        reference_solution_ref=_rel_to_root(root, ref) if ref.exists() else "",
        source_url=str(meta.get("source_url", "")),
        content_hash=_sha256_file_tree(exercise_dir),
    )


def _sha256_file_tree(exercise_dir: Path) -> str:
    h = hashlib.sha256()
    files = sorted(p for p in exercise_dir.rglob("*") if p.is_file())
    for p in files:
        rel = str(p.relative_to(exercise_dir))
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(p.read_bytes())
        h.update(b"\x00")
    return h.hexdigest()


def discover_exercises(source_root: str | Path) -> list[Path***REMOVED***:
    """Все каталоги упражнений (concept + practice) в локальном клоне."""
    root = Path(source_root)
    out: list[Path***REMOVED*** = [***REMOVED***
    for group in (CONCEPT_DIR, PRACTICE_DIR):
        for p in sorted((root / "exercises" / group).iterdir()) if (root / "exercises" / group).is_dir() else [***REMOVED***:
            if p.is_dir() and p.name not in SKIP_FOREGONE:
                out.append(p)
    return out