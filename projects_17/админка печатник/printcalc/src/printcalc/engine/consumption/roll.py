"""Roll Nesting Engine (ТЗ §10-12, §16): раскладка изделий поперёк рулона.

Формула (§11, без припусков):
    pieces_across = floor(W_usable / w_eff)
    rows = ceil(Q / pieces_across)
    length = rows × h_eff (+ gaps между рядами)
    production_area = W × length

Обязательная проверка двух ориентаций (§12): A = w×h, B = h×w; выбор по
политике (MIN_WASTE | MIN_LENGTH | FIXED_ORIENTATION). Nesting отвечает
только на вопрос «как физически разместить» (§33); расход и деньги —
вышестоящие слои.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from printcalc.engine.consumption.errors import ConsumptionError
from printcalc.engine.consumption.models import Layout
from printcalc.engine.consumption.normalize import EffectiveDimensions


@dataclass(frozen=True)
class OrientationPlan:
    """План раскладки для одной ориентации."""

    label: str  # "700x800"
    swapped: bool  # True — изделие повернуто (h×w)
    layout: Layout
    product_area: float  # мм², площадь изделий (не зависит от ориентации)
    production_area: float  # мм², W_usable × total_length
    waste_area: float  # мм²
    waste_percent: float


def plan_orientation(
    *,
    eff: EffectiveDimensions,
    quantity: float,
    swapped: bool,
) -> OrientationPlan:
    """Считает раскладку для одной ориентации (ТЗ §11).

    gapped piece width = eff.width + gap_x (зазор перед каждым изделием,
    кроме первого — учитывается упрощённо через (n−1)·gap при расчёте,
    но для строк по ширине применяем conservative: floor(W / (w+gap))).
    """
    pw = eff.height if swapped else eff.width
    ph = eff.width if swapped else eff.height
    label = f"{pw:g}x{ph:g}"

    step_w = pw + eff.gap_x
    if step_w > eff.usable_roll_width:
        raise ConsumptionError(
            "PRODUCT_DOES_NOT_FIT",
            f"изделие {pw:g} мм (+зазор {eff.gap_x:g}) не помещается "
            f"на полезную ширину рулона {eff.usable_roll_width:g} мм",
        )
    pieces_across = int(math.floor(eff.usable_roll_width / step_w))
    if pieces_across < 1:
        raise ConsumptionError(
            "PRODUCT_DOES_NOT_FIT",
            f"изделие {pw:g} мм не помещается на рулон {eff.usable_roll_width:g} мм",
        )

    rows = int(math.ceil(quantity / pieces_across))
    if quantity <= 0:
        raise ConsumptionError("INVALID_QUANTITY", "количество должно быть > 0")

    row_pitch = ph + eff.gap_y
    nesting_length = (rows - 1) * row_pitch + ph if rows > 0 else 0.0

    layout = Layout(
        orientation=label,
        piece_width=pw,
        piece_height=ph,
        pieces_across=pieces_across,
        rows=rows,
        nesting_length=nesting_length,
        usable_width=eff.usable_roll_width,
        unusable_width=eff.usable_roll_width - pieces_across * step_w + eff.gap_x,
    )
    product_area = pw * ph * quantity
    production_area = eff.usable_roll_width * nesting_length
    waste = max(0.0, production_area - product_area)
    waste_pct = (waste / production_area * 100.0) if production_area > 0 else 0.0

    return OrientationPlan(
        label=label,
        swapped=swapped,
        layout=layout,
        product_area=product_area,
        production_area=production_area,
        waste_area=waste,
        waste_percent=waste_pct,
    )


def choose_plan(
    *,
    eff: EffectiveDimensions,
    quantity: float,
    allow_rotation: bool,
    orientation_policy: str,
    fixed_orientation: str = "portrait",
) -> tuple[OrientationPlan, OrientationPlan | None, list[str]]:
    """Выбирает план согласно политике (ТЗ §12, §16).

    Возвращает (рекомендованный, альтернативный, warnings).
    POLICY: MIN_WASTE (дефолт) | MIN_LENGTH | FIXED_ORIENTATION.
    """
    if orientation_policy not in ("MIN_WASTE", "MIN_LENGTH", "FIXED_ORIENTATION"):
        raise ConsumptionError("INVALID_POLICY", f"неизвестная политика ориентации: {orientation_policy}")

    plan_a: OrientationPlan | None = None
    plan_b: OrientationPlan | None = None
    warnings: list[str] = []

    try:
        plan_a = plan_orientation(eff=eff, quantity=quantity, swapped=False)
    except ConsumptionError:
        plan_a = None  # «как введено» не влезает — возможно, влезет поворотом

    if allow_rotation:
        try:
            plan_b = plan_orientation(eff=eff, quantity=quantity, swapped=True)
        except ConsumptionError:
            plan_b = None  # поворот не помещается — не ошибка, просто нет варианта

    if plan_a is None and plan_b is None:
        raise ConsumptionError(
            "PRODUCT_DOES_NOT_FIT",
            f"изделие {eff.width:g}×{eff.height:g} мм не помещается на полезную "
            f"ширину рулона {eff.usable_roll_width:g} мм ни прямо, ни поворотом",
        )

    if plan_a is None:
        # Правило владельца (2026-09-09): если изделие не влезает по ширине рулона,
        # разворачиваем изображение (ширина↔высота) и считаем повёрнутым.
        chosen = plan_b
        warnings.append(
            f"Изделие {eff.width:g}×{eff.height:g} мм не помещается на рулон прямо — "
            f"рассчитано повёрнутым ('{plan_b.label if plan_b else ''}')."
        )
    elif plan_b is None:
        chosen = plan_a
    elif orientation_policy == "FIXED_ORIENTATION":
        chosen = plan_b if fixed_orientation == "landscape" else plan_a
    else:
        # MIN_WASTE: минимальный production_area (== минимальный waste при равной product_area)
        # MIN_LENGTH: минимальная длина раскладки
        if orientation_policy == "MIN_LENGTH":
            chosen = (
                plan_b
                if plan_b.layout.nesting_length < plan_a.layout.nesting_length
                else plan_a
            )
        else:  # MIN_WASTE
            chosen = (
                plan_b if plan_b.production_area < plan_a.production_area else plan_a
            )

    if chosen is None:  # недостижимо (plan_a/plan_b хотя бы один есть), но сужает тип для mypy
        raise ConsumptionError("PRODUCT_DOES_NOT_FIT", "нет допустимого плана раскладки")

    alt: OrientationPlan | None = None
    if plan_a is not None and plan_b is not None:
        alt = plan_b if chosen is plan_a else plan_a

    if alt is not None:
        saved = abs(chosen.production_area - alt.production_area)
        if saved > 1e-9:
            warnings.append(
                f"Поворот изделия {'уменьшает' if chosen.production_area < alt.production_area else 'не изменяет'} "
                f"расход; альтернатива «{alt.label}»: {alt.production_area / 1e6:.4g} м²."
            )
    return chosen, alt, warnings


def trace_steps(
    *,
    eff: EffectiveDimensions,
    plan: OrientationPlan,
    quantity: float,
    roll_width: float,
) -> tuple[dict[str, Any], ...]:
    """Человекочитаемый след расчёта (ТЗ §9, §53) — «почему посчитано 0,8 м²»."""
    lo = plan.layout
    return (
        {"step": "roll_width", "value_mm": roll_width},
        {"step": "usable_width", "value_mm": eff.usable_roll_width, "note": "рулон − боковые поля"},
        {
            "step": "effective_piece",
            "value": f"{lo.piece_width:g}x{lo.piece_height:g}",
            "note": "изделие + bleed + trim",
        },
        {
            "step": "pieces_across",
            "formula": f"floor({lo.usable_width:g} / ({lo.piece_width:g}+gap {eff.gap_x:g}))",
            "value": lo.pieces_across,
        },
        {
            "step": "rows",
            "formula": f"ceil({quantity:g} / {lo.pieces_across})",
            "value": lo.rows,
        },
        {
            "step": "nesting_length",
            "formula": f"{lo.rows} × ({lo.piece_height:g}+gap {eff.gap_y:g})",
            "value_mm": lo.nesting_length,
        },
        {
            "step": "production_area",
            "formula": f"{lo.usable_width:g} × {lo.nesting_length:g} мм",
            "value_m2": plan.production_area / 1_000_000.0,
        },
        {"step": "product_area", "value_m2": plan.product_area / 1_000_000.0},
        {"step": "waste_area", "value_m2": plan.waste_area / 1_000_000.0},
        {"step": "waste_percent", "value": plan.waste_percent},
    )


__all__ = ["OrientationPlan", "choose_plan", "plan_orientation", "trace_steps"]
