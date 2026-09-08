"""Правила округления движка расхода (ТЗ §19, §40).

Округление применяется ТОЛЬКО в специально указанной точке расчёта
(биллинг-количество и/или итоговая длина по политике). Внутренние
расчёты — с полной точностью; запрещено 0.833 → 0.8 с последующим
использованием «0.8» в следующем расчёте.

Режимы: NONE | CEIL | FLOOR | ROUND | CEIL_TO_STEP (§19).
"""

from __future__ import annotations

import math

from printcalc.engine.consumption.errors import ConsumptionError

ROUNDING_MODES: tuple[str, ...] = ("NONE", "CEIL", "FLOOR", "ROUND", "CEIL_TO_STEP")


def apply_rounding(
    value: float, *, mode: str, step: float
) -> float:
    """Округляет value согласно режиму; step > 0 обязателен для CEIL_TO_STEP."""
    if mode not in ROUNDING_MODES:
        raise ConsumptionError("INVALID_ROUNDING", f"неизвестный режим округления: {mode}")
    if mode == "NONE" or value <= 0:
        return value
    if mode == "CEIL":
        return math.ceil(value)
    if mode == "FLOOR":
        return math.floor(value)
    if mode == "ROUND":
        return round(value)
    # CEIL_TO_STEP: 0.83 м при шаге 0.1 → 0.9 (пример ТЗ §19)
    if step <= 0:
        raise ConsumptionError(
            "INVALID_ROUNDING", "CEIL_TO_STEP требует положительный rounding_step"
        )
    return math.ceil(value / step) * step


__all__ = ["ROUNDING_MODES", "apply_rounding"]
