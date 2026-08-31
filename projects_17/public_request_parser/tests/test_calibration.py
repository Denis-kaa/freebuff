"""Hermetic tests P14 feedback→threshold calibration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.calibration import ThresholdCalibrator, optimal_accept_threshold
from app.calibration.engine import _Sample
from app.domain import MatchDecision, MatchOutcome, Publication, SearchProfile
from app.storage import SqliteStorage

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_profile(version: int = 1, *, pending_threshold: float = 0.5) -> SearchProfile:
    return SearchProfile(
        profile_id="profile-1",
        owner_scope="operator",
        version=version,
        service_name="Python",
        required_terms=("python",),
        accept_threshold=0.8,
        pending_threshold=pending_threshold,
    )


def add_sample(
    storage: SqliteStorage,
    *,
    key: str,
    score: float,
    action: str,
) -> None:
    """Треугольник: публикация + decision + feedback для одного ключа."""
    publication = Publication(
        source_id="src",
        item_id=key,
        canonical_url=f"https://x.test/{key}",
        title=f"title {key}",
        fetched_at=NOW,
    )
    storage.save_publication(publication)
    storage.save_decision(
        MatchDecision(
            publication_key=publication.item_key,
            profile_id="profile-1",
            profile_version=1,
            outcome=MatchOutcome.REJECT if score < 0.5 else MatchOutcome.ACCEPT,
            score=score,
            reasons=("required term matched: python",),
            rules_snapshot={"required_terms": ("python",)},
            decided_at=NOW,
        )
    )
    storage.record_feedback(
        owner_scope="operator",
        delivery_key=f"operator:{publication.item_key}:p1",
        publication_key=publication.item_key,
        action=action,
        created_at=NOW,
    )


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage]:
    db = SqliteStorage(tmp_path / "calib.db")
    yield db
    db.close()


def test_optimal_threshold_maximizes_accuracy() -> None:
    """На простой выборке порог разделяет relevant/irrelevant."""
    samples = [
        _Sample(score=0.95, relevant=True),
        _Sample(score=0.90, relevant=True),
        _Sample(score=0.45, relevant=False),
        _Sample(score=0.30, relevant=False),
    ]
    threshold = optimal_accept_threshold(samples)

    assert 0.45 < threshold <= 0.90
    assert threshold in {0.9, 0.95}


def test_calibrator_returns_none_without_enough_samples(storage: SqliteStorage) -> None:
    """Меньше min_samples → None (нет evidence)."""
    add_sample(storage, key="a", score=0.95, action="relevant")
    add_sample(storage, key="b", score=0.4, action="irrelevant")

    result = ThresholdCalibrator(storage, min_samples=3).calibrate(make_profile())

    assert result is None


def test_calibrator_recommends_lowering_accept_when_missed_relevant(
    storage: SqliteStorage,
) -> None:
    """Feedback «relevant» для score < 0.8 → рекомендация снизить порог."""
    add_sample(storage, key="h1", score=0.95, action="relevant")
    add_sample(storage, key="h2", score=0.90, action="relevant")
    add_sample(storage, key="l1", score=0.55, action="relevant")  # false negative
    add_sample(storage, key="x1", score=0.30, action="irrelevant")

    result = ThresholdCalibrator(storage).calibrate(make_profile())

    assert result is not None
    assert result.samples == 4
    assert result.positive == 3
    assert result.negative == 1
    assert result.changed is True
    assert result.suggested_accept < 0.8
    assert result.suggested_pending < result.suggested_accept
    assert result.summary().startswith("calibration[CHANGE)")


def test_calibrator_keeps_thresholds_when_already_optimal(
    storage: SqliteStorage,
) -> None:
    """Порог 0.8 уже оптимален (есть sample с score 0.8) → KEEP."""
    add_sample(storage, key="a1", score=0.95, action="relevant")
    add_sample(storage, key="a2", score=0.80, action="relevant")
    add_sample(storage, key="b1", score=0.40, action="irrelevant")

    result = ThresholdCalibrator(storage).calibrate(
        make_profile(pending_threshold=0.4)  # совпадает с suggested_pending=0.4
    )

    assert result is not None
    assert result.suggested_accept == 0.8
    assert result.changed is False
    assert result.summary().startswith("calibration[KEEP)")


def test_calibration_ignores_feedback_without_decision(
    storage: SqliteStorage,
) -> None:
    """Feedback без сохранённого decision не попадает в выборку."""
    storage.record_feedback(
        owner_scope="operator",
        delivery_key="operator:src:ghost:p1",
        publication_key="src:ghost",
        action="relevant",
        created_at=NOW,
    )
    add_sample(storage, key="a1", score=0.95, action="relevant")
    add_sample(storage, key="b1", score=0.30, action="irrelevant")
    add_sample(storage, key="c1", score=0.10, action="irrelevant")

    result = ThresholdCalibrator(storage).calibrate(make_profile())

    assert result is not None
    assert result.samples == 3  # ghost-запись без decision исключена