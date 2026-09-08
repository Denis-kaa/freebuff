"""Нормализация входов перед nesting: effective dimensions (ТЗ §13).

Размер изделия не равен размеру печати/раскроя:
    effective_width  = product_width  + bleed_left + bleed_right + trim_allowance
    effective_height = product_height + bleed_top  + bleed_bottom + trim_allowance
gap_x/gap_y — между изделиями (влияет на раскладку, не на размер изделия);
side_margin — неснимаемые поля рулона (уменьшают полезную ширину).
"""

from __future__ import annotations

from dataclasses import dataclass

from printcalc.engine.consumption.errors import ConsumptionError


@dataclass(frozen=True)
class EffectiveDimensions:
    """Эффективные размеры изделия и полезная ширина (всё в мм)."""

    width: float
    height: float
    usable_roll_width: float
    gap_x: float
    gap_y: float


def effective_dimensions(
    *,
    width: float,
    height: float,
    roll_width: float,
    side_margin: float,
    top_margin: float,
    bottom_margin: float,
    bleed_left: float,
    bleed_right: float,
    bleed_top: float,
    bleed_bottom: float,
    trim_allowance: float,
    gap_x: float,
    gap_y: float,
) -> EffectiveDimensions:
    """Считает эффективные размеры и полезную ширину рулона (ТЗ §13).

    Отрицательные входы отсекаются политикой, но здесь — контроль осмысленности:
    effective размеры должны быть > 0, полезная ширина > 0.
    """
    if width <= 0 or height <= 0:
        raise ConsumptionError("INVALID_DIMENSION", "размеры изделия должны быть > 0")
    if roll_width <= 0:
        raise ConsumptionError("INVALID_DIMENSION", "ширина рулона должна быть > 0")

    usable = roll_width - side_margin - top_margin - bottom_margin
    if usable <= 0:
        raise ConsumptionError(
            "ROLL_WIDTH_TOO_SMALL",
            "боковые поля рулона съедают всю ширину: "
            f"{roll_width:g} − {side_margin + top_margin + bottom_margin:g} ≤ 0 мм",
        )

    eff_w = width + bleed_left + bleed_right + trim_allowance
    eff_h = height + bleed_top + bleed_bottom + trim_allowance
    if eff_w <= 0 or eff_h <= 0:
        raise ConsumptionError("INVALID_DIMENSION", "эффективные размеры должны быть > 0")

    return EffectiveDimensions(
        width=eff_w,
        height=eff_h,
        usable_roll_width=usable,
        gap_x=gap_x,
        gap_y=gap_y,
    )
