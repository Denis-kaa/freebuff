"""Calibration package (P14) — feedback → thresholds.

Минимальная детерминированная калибровка: на основе `feedback` (relevant /
irrelevant) и сохранённых `MatchDecision.score` подбирается порог accept,
максимизирующий accuracy на накопленной выборке. Калибровка возвращает
рекомендацию + метрики; никаких авто-изменений профилей без явного apply.
"""

from .engine import CalibrationResult, ThresholdCalibrator, optimal_accept_threshold

__all__ = [
    "CalibrationResult",
    "ThresholdCalibrator",
    "optimal_accept_threshold",
***REMOVED***