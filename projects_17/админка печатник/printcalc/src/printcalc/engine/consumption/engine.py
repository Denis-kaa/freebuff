"""Consumption Engine — единая точка расчёта расхода (ТЗ §25).

ConsumptionEngine.calculate(material, item, policy) маршрутизирует по
consumption_mode. Phase 1 реализует ROLL_NESTING (рулон) полноценно и
AREA/LINEAR/SHEET/PIECE/COUNT как прямые режимы (расход = затребованное
количество) — nesting для них появится в Phase 4 (§54).

Обязательные разделения:
- production (факт) ≠ billing (тарифицируемый) (§7, §18);
- nesting_length + setup + leader + trailer хранятся отдельно (§20-21);
- остаток классифицируется REMNANT/SCRAP, но НЕ используется автоматически (§22-23).
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from printcalc.engine.consumption.errors import ConsumptionError
from printcalc.engine.consumption.models import (
    Material,
    MaterialConsumptionPolicy,
    MaterialConsumptionResult,
    Remnant,
)
from printcalc.engine.consumption.normalize import effective_dimensions
from printcalc.engine.consumption.rounding import apply_rounding
from printcalc.engine.consumption.roll import choose_plan, plan_orientation, trace_steps
from printcalc.engine.consumption.units import area_to_m2, linear_to_m

#: Режимы, требующие рулона.
_ROLL_MODES = ("ROLL_NESTING",)


class ConsumptionEngine:
    """Единый интерфейс расчёта расхода (ТЗ §25)."""

    def calculate(
        self,
        material: Material,
        item: Mapping[str, Any],
        policy: MaterialConsumptionPolicy | None = None,
    ) -> MaterialConsumptionResult:
        """Считает расход материала для изделия item (width/height/quantity).

        Единицы входа — мм (нормализация с границы API — units.py).
        """
        pol = policy if policy is not None else MaterialConsumptionPolicy(
            material_id=material.id, mode=material.consumption_mode
        )
        if pol.material_id != material.id:
            raise ConsumptionError(
                "INVALID_POLICY",
                f"политика для «{pol.material_id}», а материал «{material.id}»",
            )

        width = _positive_number(item, "width")
        height = _positive_number(item, "height")
        quantity = _positive_number(item, "quantity")

        mode = pol.mode if pol.mode != material.consumption_mode else material.consumption_mode
        if mode in ("ROLL_NESTING",):
            return self._calculate_roll(material, pol, width, height, quantity)
        if mode in ("AREA", "LINEAR", "SHEET", "PIECE", "COUNT", "SHEET_NESTING", "CUSTOM"):
            return self._calculate_direct(material, pol, width, height, quantity)
        raise ConsumptionError("INVALID_MATERIAL_UNIT", f"неизвестный режим расхода: {mode}")

    # ---------- ROLL_NESTING (Phase 1 ядро) ----------

    def _calculate_roll(
        self,
        material: Material,
        pol: MaterialConsumptionPolicy,
        width: float,
        height: float,
        quantity: float,
    ) -> MaterialConsumptionResult:
        if material.roll_width is None or material.roll_width <= 0:
            raise ConsumptionError(
                "ROLL_WIDTH_TOO_SMALL",
                f"у материала «{material.name}» не задана ширина рулона",
            )

        eff = effective_dimensions(
            width=width,
            height=height,
            roll_width=material.roll_width,
            side_margin=pol.side_margin,
            top_margin=pol.top_margin,
            bottom_margin=pol.bottom_margin,
            bleed_left=pol.bleed_left,
            bleed_right=pol.bleed_right,
            bleed_top=pol.bleed_top,
            bleed_bottom=pol.bleed_bottom,
            trim_allowance=pol.trim_allowance,
            gap_x=pol.gap_x,
            gap_y=pol.gap_y,
        )

        plan, alternative, warnings = choose_plan(
            eff=eff,
            quantity=quantity,
            allow_rotation=pol.allow_rotation,
            orientation_policy=pol.orientation_policy,
            fixed_orientation=pol.fixed_orientation,
        )

        nesting_length = plan.layout.nesting_length
        setup = pol.setup_length
        leader = pol.leader_length
        trailer = pol.trailer_length
        total_length = nesting_length + setup + leader + trailer

        # Полная ширина рулона × total_length — фактический расход со всей ширины.
        production_area = material.roll_width * total_length
        product_area = plan.product_area
        waste = max(0.0, production_area - product_area)
        waste_pct = (waste / production_area * 100.0) if production_area > 0 else 0.0

        if pol.waste_percent > 0:
            extra = production_area * pol.waste_percent / 100.0
            production_area += extra
            waste += extra
            warnings.append(
                f"Применён дополнительный процент отхода: {pol.waste_percent:g}% "
                f"(+{extra / 1e6:.4g} м²). Правило владельца, не раскрой."
            )

        # Billing: min_consumption и min_billing_consumption (§18, §6).
        production_lm = linear_to_m(total_length)
        billing_qty, billing_unit, billing_warnings = _billing_quantity(
            production_lm=production_lm,
            min_consumption=pol.min_consumption,
            min_consumption_unit=pol.min_consumption_unit,
            min_billing=pol.min_billing_consumption,
            min_billing_unit=pol.min_billing_unit,
            rounding_mode=pol.rounding_mode,
            rounding_step=pol.rounding_step,
        )
        warnings.extend(billing_warnings)
        if pol.min_consumption > 0 and production_lm < pol.min_consumption:
            warnings.append(
                f"Применён минимальный расход: {pol.min_consumption:g} "
                f"{pol.min_consumption_unit} (производственный расход сохранён: "
                f"{production_lm:g} м)."
            )

        # Остаток: полоса по ширине рулона (§22-23) — классификация, не использование.
        # Полоса: unusable_width (мм) ПО шири́не × nesting_length (мм) ПО длине.
        remnant = _classify_remnant(
            pol=pol,
            remnant_width=plan.layout.unusable_width,
            remnant_length=nesting_length,
        )

        trace = trace_steps(
            eff=eff,
            plan=plan,
            quantity=quantity,
            roll_width=material.roll_width,
        )
        trace = trace + (
            {"step": "setup_length", "value_mm": setup},
            {"step": "leader_length", "value_mm": leader},
            {"step": "trailer_length", "value_mm": trailer},
            {"step": "total_production_length", "value_mm": total_length},
            {"step": "billing_quantity", "value": billing_qty, "unit": billing_unit},
        )

        layout_payload: dict[str, Any] = {
            "orientation": plan.layout.orientation,
            "piece_width_mm": plan.layout.piece_width,
            "piece_height_mm": plan.layout.piece_height,
            "pieces_across": plan.layout.pieces_across,
            "rows": plan.layout.rows,
            "nesting_length_mm": nesting_length,
            "total_length_mm": total_length,
            "usable_width_mm": plan.layout.usable_width,
            "unusable_strip_mm": plan.layout.unusable_width,
        }
        if alternative is not None:
            layout_payload["alternative"] = {
                "orientation": alternative.label,
                "production_area_m2": area_to_m2(alternative.production_area),
                "nesting_length_mm": alternative.layout.nesting_length,
            }

        return MaterialConsumptionResult(
            material_id=material.id,
            product_area=product_area,
            production_area=production_area,
            production_length=total_length,
            production_width=plan.layout.usable_width,
            billing_quantity=billing_qty,
            billing_unit=billing_unit,
            waste_area=waste,
            waste_percent=waste_pct,
            usable_width=plan.layout.usable_width,
            unusable_width=plan.layout.unusable_width,
            pieces_across=plan.layout.pieces_across,
            rows=plan.layout.rows,
            orientation=plan.label,
            alternative_orientation=alternative.label if alternative else None,
            setup_consumption=setup,
            trim_consumption=leader + trailer,
            remnant=remnant,
            warnings=tuple(warnings),
            calculation_trace=trace,
            layout=layout_payload,
        )

    # ---------- Прямые режимы (AREA/LINEAR/SHEET/PIECE/COUNT) ----------

    def _calculate_direct(
        self,
        material: Material,
        pol: MaterialConsumptionPolicy,
        width: float,
        height: float,
        quantity: float,
    ) -> MaterialConsumptionResult:
        """Прямой режим: расход = запрошенное количество в base_unit.

        AREA: м² = Ш×В×Q (мм→м²); LINEAR: пог.м = quantity; SHEET/PIECE/COUNT:
        количество листов/штук = quantity. Раскроя нет — это текущее поведение
        существующих калькуляторов (backward compat, §45).
        """
        warnings: list[str] = []
        if material.consumption_mode == "AREA":
            product_mm2 = width * height * quantity
            production_m2 = area_to_m2(product_mm2)
            billing = max(production_m2, pol.min_billing_consumption)
            if pol.min_billing_consumption > 0 and production_m2 < pol.min_billing_consumption:
                warnings.append(
                    f"Применён минимальный оплачиваемый расход: {pol.min_billing_consumption:g} м²."
                )
            if pol.waste_percent > 0:
                extra = production_m2 * pol.waste_percent / 100.0
                production_m2 += extra
                warnings.append(
                    f"Применён дополнительный процент отхода: {pol.waste_percent:g}%."
                )
            return MaterialConsumptionResult(
                material_id=material.id,
                product_area=product_mm2,
                production_area=production_m2 * 1_000_000.0,
                production_length=0.0,
                production_width=width,
                billing_quantity=billing,
                billing_unit="m2",
                waste_area=(production_m2 * 1_000_000.0) - product_mm2,
                waste_percent=(
                    (production_m2 * 1_000_000.0 - product_mm2)
                    / (production_m2 * 1_000_000.0)
                    * 100.0
                    if production_m2 > 0
                    else 0.0
                ),
                usable_width=width,
                unusable_width=0.0,
                pieces_across=1,
                rows=math.ceil(quantity),
                orientation=f"{width:g}x{height:g}",
                alternative_orientation=None,
                setup_consumption=0.0,
                trim_consumption=0.0,
                remnant=None,
                warnings=tuple(warnings),
                calculation_trace=(
                    {"step": "mode", "value": "AREA"},
                    {"step": "product_area", "value_m2": area_to_m2(product_mm2)},
                    {"step": "production_area", "value_m2": production_m2},
                    {"step": "billing_quantity", "value": billing, "unit": "m2"},
                ),
                layout={"mode": "AREA"},
            )
        # LINEAR/SHEET/PIECE/COUNT: количество = quantity в base_unit.
        unit = material.base_unit
        production_qty = quantity
        billing = max(production_qty, pol.min_billing_consumption)
        if pol.min_billing_consumption > 0 and production_qty < pol.min_billing_consumption:
            warnings.append(
                f"Применён минимальный оплачиваемый расход: "
                f"{pol.min_billing_consumption:g} {unit}."
            )
        return MaterialConsumptionResult(
            material_id=material.id,
            product_area=0.0,
            production_area=0.0,
            production_length=production_qty if unit == "lm" else 0.0,
            production_width=0.0,
            billing_quantity=billing,
            billing_unit=unit,
            waste_area=0.0,
            waste_percent=0.0,
            usable_width=0.0,
            unusable_width=0.0,
            pieces_across=1,
            rows=math.ceil(quantity),
            orientation="n/a",
            alternative_orientation=None,
            setup_consumption=0.0,
            trim_consumption=0.0,
            remnant=None,
            warnings=tuple(warnings),
            calculation_trace=(
                {"step": "mode", "value": material.consumption_mode},
                {"step": "quantity", "value": production_qty, "unit": unit},
                {"step": "billing_quantity", "value": billing, "unit": unit},
            ),
            layout={"mode": material.consumption_mode},
        )


def _billing_quantity(
    *,
    production_lm: float,
    min_consumption: float,
    min_consumption_unit: str,
    min_billing: float,
    min_billing_unit: str,
    rounding_mode: str,
    rounding_step: float,
) -> tuple[float, str, list[str]]:
    """Тарифицируемое количество: min_consumption → min_billing → округление (§18-19).

    Истинное production-значение НЕ подменяется (§18) — меняется только billing.
    """
    warnings: list[str] = []
    billing = production_lm
    unit = "lm"

    if min_consumption > 0 and billing < min_consumption:
        billing = min_consumption
        unit = min_consumption_unit
    if min_billing > 0 and billing < min_billing:
        billing = min_billing
        unit = min_billing_unit
        warnings.append(
            f"Применён минимальный оплачиваемый расход: {min_billing:g} {min_billing_unit}."
        )

    if rounding_mode != "NONE":
        rounded = apply_rounding(billing, mode=rounding_mode, step=rounding_step)
        if rounded != billing:
            warnings.append(
                f"Биллинг-количество округлено: {billing:g} → {rounded:g} ({rounding_mode})."
            )
        billing = rounded
    return billing, unit, warnings


def _classify_remnant(
    *, pol: MaterialConsumptionPolicy, remnant_width: float, remnant_length: float
) -> Remnant | None:
    """Классификация остаточной полосы (ТЗ §22): REMNANT или SCRAP по порогам."""
    if remnant_width <= 0 or remnant_length <= 0:
        return None
    area = remnant_width * remnant_length
    reasons: list[str] = []
    ok = True
    if pol.remnant_min_width > 0 and remnant_width < pol.remnant_min_width:
        ok = False
        reasons.append(f"ширина {remnant_width:g} < {pol.remnant_min_width:g} мм")
    if pol.remnant_min_length > 0 and remnant_length < pol.remnant_min_length:
        ok = False
        reasons.append(f"длина {remnant_length:g} < {pol.remnant_min_length:g} мм")
    if pol.remnant_min_area > 0 and area < pol.remnant_min_area:
        ok = False
        reasons.append(f"площадь {area:g} мм² < {pol.remnant_min_area:g} мм²")
    status = "REMNANT" if ok else "SCRAP"
    reason = (
        "полоса проходит порогам политики"
        if ok
        else "полоса ниже порогов политики: " + "; ".join(reasons)
    )
    return Remnant(
        status=status,
        width=remnant_width,
        length=remnant_length,
        area_mm2=area,
        reason=reason,
    )


def _positive_number(item: Mapping[str, Any], key: str) -> float:
    from printcalc.engine.errors import CalcInputError

    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcInputError(key, "ожидалось число")
    value = float(value)
    if value <= 0:
        raise CalcInputError(key, "значение должно быть > 0")
    return value


__all__ = ["ConsumptionEngine"]
