"""Feedback-driven threshold calibration (P14).

Идея: пользователь помечает доставленные карточки `relevant`/`irrelevant`.
Для каждой такой публикации в storage лежит `MatchDecision` со score.
Калибратор собирает пары (score, label) и подбирает порог accept,
максимизирующий accuracy на выборке (детерминированно, O(n²) на списке
кандидатов — кандидаты сами score).

Порог НЕ применяется автоматически: требуется явное действие оператора
(обновить профиль/версию). Это сохраняет explainability и откат.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain import SearchProfile
from app.storage import SqliteStorage

SAMPLE_ACTIONS = frozenset({"relevant", "irrelevant"***REMOVED***)
DEFAULT_ACCEPT = 0.8
DEFAULT_PENDING = 0.5
DEFAULT_MIN_SAMPLES = 3


@dataclass(frozen=True, slots=True)
class _Sample:
    """Пара (score, метка «relevant») из накопленного feedback."""

    score: float
    relevant: bool


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Рекомендация по порогам на основе выборки (без авто-apply)."""

    profile_id: str
    owner_scope: str
    samples: int
    positive: int
    negative: int
    current_accept: float
    suggested_accept: float
    current_pending: float
    suggested_pending: float
    precision_at_suggested: float
    recall_at_suggested: float
    changed: bool

    def summary(self) -> str:
        """Краткое текстовое представление CLI/report."""
        status = "CHANGE" if self.changed else "KEEP"
        return (
            f"calibration[{status***REMOVED******REMOVED*** profile={self.profile_id***REMOVED*** samples={self.samples***REMOVED*** "
            f"pos={self.positive***REMOVED*** neg={self.negative***REMOVED*** "
            f"accept {self.current_accept:.2f***REMOVED***→{self.suggested_accept:.2f***REMOVED*** "
            f"pending {self.current_pending:.2f***REMOVED***→{self.suggested_pending:.2f***REMOVED*** "
            f"precision={self.precision_at_suggested:.2f***REMOVED*** recall={self.recall_at_suggested:.2f***REMOVED***"
        )


def optimal_accept_threshold(samples: list[_Sample***REMOVED***) -> float:
    """Порог, максимизирующий accuracy; при пустой выборке — default."""
    if not samples:
        return DEFAULT_ACCEPT
    candidates = sorted({round(sample.score, 6) for sample in samples***REMOVED***)
    best_threshold = candidates[0***REMOVED***
    best_accuracy = -1.0
    for threshold in candidates:
        accuracy = sum(
            1 for sample in samples if (sample.score >= threshold) == sample.relevant
        ) / len(samples)
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    return best_threshold


def _precision_recall(samples: list[_Sample***REMOVED***, threshold: float) -> tuple[float, float***REMOVED***:
    """Precision/recall для данного порога."""
    true_positive = sum(
        1 for sample in samples if sample.relevant and sample.score >= threshold
    )
    false_positive = sum(
        1 for sample in samples if not sample.relevant and sample.score >= threshold
    )
    false_negative = sum(
        1 for sample in samples if sample.relevant and sample.score < threshold
    )
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    return precision, recall


class ThresholdCalibrator:
    """Калибровка порогов профиля на накопленном feedback."""

    def __init__(
        self,
        storage: SqliteStorage,
        *,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> None:
        if min_samples < 1:
            raise ValueError("min_samples must be >= 1")
        self._storage = storage
        self._min_samples = min_samples

    def calibrate(self, profile: SearchProfile) -> CalibrationResult | None:
        """Собрать выборку по профилю и вернуть рекомендацию.

        Возвращает None при недостаточном количестве подтверждённых feedback
        записей (нет evidence — нет рекомендации).
        """
        feedback = self._storage.list_feedback(profile.owner_scope)
        samples: list[_Sample***REMOVED*** = [***REMOVED***
        for entry in feedback:
            action = str(entry["action"***REMOVED***)
            if action not in SAMPLE_ACTIONS:
                continue
            publication_key = str(entry["publication_key"***REMOVED***)
            decision = self._storage.get_decision(
                publication_key, profile.profile_id, profile.version
            )
            if decision is None:
                continue
            samples.append(
                _Sample(score=decision.score, relevant=(action == "relevant"))
            )

        if len(samples) < self._min_samples:
            return None

        positive = sum(1 for sample in samples if sample.relevant)
        negative = len(samples) - positive
        suggested_accept = optimal_accept_threshold(samples)
        # pending всегда ниже accept; детерминированный фиксированный шаг.
        suggested_pending = round(suggested_accept * 0.5, 2)
        if suggested_pending > profile.pending_threshold and not positive:
            suggested_pending = DEFAULT_PENDING

        precision, recall = _precision_recall(samples, suggested_accept)
        changed = (
            suggested_accept != profile.accept_threshold
            or suggested_pending != profile.pending_threshold
        )

        return CalibrationResult(
            profile_id=profile.profile_id,
            owner_scope=profile.owner_scope,
            samples=len(samples),
            positive=positive,
            negative=negative,
            current_accept=profile.accept_threshold,
            suggested_accept=suggested_accept,
            current_pending=profile.pending_threshold,
            suggested_pending=suggested_pending,
            precision_at_suggested=precision,
            recall_at_suggested=recall,
            changed=changed,
        )


__all__ = [
    "DEFAULT_ACCEPT",
    "DEFAULT_MIN_SAMPLES",
    "DEFAULT_PENDING",
    "CalibrationResult",
    "ThresholdCalibrator",
    "optimal_accept_threshold",
***REMOVED***