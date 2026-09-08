"""Доменные модели движка расхода (ТЗ §5-8, §22).

Ключевое разделение (§7, обязательное):
- Product Area — площадь готового изделия;
- Production Consumption — фактически зарезервированный/использованный материал;
- Billing Consumption — количество, идущее в расчёт стоимости.

Это принципиально разные значения; движок никогда не подменяет production
billing'ом (истинное значение сохраняется, §18).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

#: Режимы расхода материала (ТЗ §5.1). Закрытый набор; TIME/WEIGHT — будущее.
CONSUMPTION_MODES: tuple[str, ...] = (
    "AREA",
    "LINEAR",
    "SHEET",
    "PIECE",
    "ROLL_NESTING",
    "SHEET_NESTING",
    "COUNT",
    "CUSTOM",
)

#: Единицы расхода (ТЗ §41 + MATERIAL_MODEL §4).
CONSUMPTION_UNITS: tuple[str, ...] = ("m2", "lm", "mm", "шт", "лист")


@dataclass(frozen=True)
class Material:
    """Материал (ТЗ §5.1). roll_width/roll_length — мм; sheet_* — мм."""

    id: str
    name: str
    category: str = "general"
    consumption_mode: str = "AREA"
    base_unit: str = "m2"
    purchase_unit: str = "m2"
    roll_width: float | None = None
    roll_length: float | None = None
    sheet_width: float | None = None
    sheet_height: float | None = None
    purchase_price: float = 0.0  # ₽ за purchase_unit (Cost Engine применяет сам)
    price_unit: str = "m2"
    active: bool = True


@dataclass(frozen=True)
class MaterialConsumptionPolicy:
    """Политика расхода (ТЗ §6). Все параметры конфигурируемые; длины — мм.

    orientation_policy: MIN_WASTE | MIN_LENGTH | FIXED_ORIENTATION (§12)
    rounding_mode: NONE | CEIL | FLOOR | ROUND | CEIL_TO_STEP (§19)
    """

    material_id: str
    mode: str = "AREA"

    min_consumption: float = 0.0
    min_consumption_unit: str = "lm"

    min_billing_consumption: float = 0.0
    min_billing_unit: str = "lm"

    side_margin: float = 0.0
    top_margin: float = 0.0
    bottom_margin: float = 0.0

    bleed_left: float = 0.0
    bleed_right: float = 0.0
    bleed_top: float = 0.0
    bleed_bottom: float = 0.0

    gap_x: float = 0.0
    gap_y: float = 0.0

    trim_allowance: float = 0.0
    setup_length: float = 0.0
    leader_length: float = 0.0
    trailer_length: float = 0.0

    allow_rotation: bool = True
    allow_nesting: bool = False
    allow_job_ganging: bool = False

    orientation_policy: str = "FIXED_ORIENTATION"  # дефолт ТЗ: примеры §14/§15 считают ориентацию «как введено»; авто-выбор — MIN_WASTE/MIN_LENGTH явной политикой
    fixed_orientation: str = "portrait"  # для FIXED_ORIENTATION: portrait = Ш×В как введено

    rounding_mode: str = "NONE"
    rounding_step: float = 0.0

    waste_percent: float = 0.0  # дополнительное правило, НЕ заменяет раскрой (§4)

    remnant_min_width: float = 0.0  # мм (§22)
    remnant_min_length: float = 0.0
    remnant_min_area: float = 0.0  # мм²

    notes: str = ""

    def __post_init__(self) -> None:
        if self.mode not in CONSUMPTION_MODES:
            raise ValueError(f"неизвестный режим расхода: {self.mode}")
        negatives = {
            "bleed_left": self.bleed_left,
            "bleed_right": self.bleed_right,
            "bleed_top": self.bleed_top,
            "bleed_bottom": self.bleed_bottom,
            "gap_x": self.gap_x,
            "gap_y": self.gap_y,
            "side_margin": self.side_margin,
            "top_margin": self.top_margin,
            "bottom_margin": self.bottom_margin,
            "trim_allowance": self.trim_allowance,
            "setup_length": self.setup_length,
            "leader_length": self.leader_length,
            "trailer_length": self.trailer_length,
        }
        bad = [k for k, v in negatives.items() if v < 0]
        if bad:
            # ТЗ §38: NEGATIVE_ALLOWANCE.
            raise ValueError(f"отрицательные припуски запрещены: {', '.join(bad)}")


@dataclass(frozen=True)
class Layout:
    """Раскладка одного варианта ориентации (ТЗ §11-12, §16)."""

    orientation: str  # "700x800" — строка «ширина×высота» эффективных размеров
    piece_width: float  # мм (эффективные, с bleed/trim)
    piece_height: float
    pieces_across: int
    rows: int
    nesting_length: float  # мм, чистая длина раскладки без setup/leader/trailer
    usable_width: float  # мм, ширина рулона минус боковые поля
    unusable_width: float  # мм, неиспользуемая полоса по ширине


@dataclass(frozen=True)
class Remnant:
    """Классификация остатка (ТЗ §22): REMNANT пригоден, SCRAP — нет."""

    status: str  # REMNANT | SCRAP
    width: float  # мм
    length: float  # мм
    area_mm2: float
    reason: str = ""


@dataclass(frozen=True)
class MaterialConsumptionResult:
    """Результат движка расхода (ТЗ §8). Длины — мм; площади — мм² и м²."""

    material_id: str

    product_area: float  # мм², площадь готовых изделий
    production_area: float  # мм², фактический расход материала

    production_length: float  # мм, total = nesting + setup + leader + trailer
    production_width: float  # мм (используемая ширина рулона)

    billing_quantity: float  # количество в billing-единице
    billing_unit: str

    waste_area: float  # мм² = production_area − product_area (≥ 0)
    waste_percent: float  # 0..100

    usable_width: float  # мм
    unusable_width: float  # мм

    pieces_across: int
    rows: int

    orientation: str  # рекомендованная ориентация
    alternative_orientation: str | None  # §16

    setup_consumption: float  # мм, отдельно от nesting (§20)
    trim_consumption: float  # мм (leader + trailer, §21)

    remnant: Remnant | None  # §22-23: рассчитан и классифицирован, НЕ используется

    warnings: tuple[str, ...] = ()
    calculation_trace: tuple[Mapping[str, Any], ...] = ()
    layout: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def to_dict(self) -> dict[str, Any]:
        """Сериализация для API/CalcResult.details (мм² → м² на границе, §40)."""
        from printcalc.engine.consumption.units import area_to_m2, linear_to_m

        return {
            "material_id": self.material_id,
            "product_area_m2": area_to_m2(self.product_area),
            "production_area_m2": area_to_m2(self.production_area),
            "production_length_m": linear_to_m(self.production_length),
            "production_width_m": linear_to_m(self.production_width),
            "billing_quantity": self.billing_quantity,
            "billing_unit": self.billing_unit,
            "waste_area_m2": area_to_m2(self.waste_area),
            "waste_percent": self.waste_percent,
            "usable_width_m": linear_to_m(self.usable_width),
            "unusable_width_m": linear_to_m(self.unusable_width),
            "pieces_across": self.pieces_across,
            "rows": self.rows,
            "orientation": self.orientation,
            "alternative_orientation": self.alternative_orientation,
            "setup_length_m": linear_to_m(self.setup_consumption),
            "leader_trailer_length_m": linear_to_m(self.trim_consumption),
            "remnant": (
                {
                    "status": self.remnant.status,
                    "width_m": linear_to_m(self.remnant.width),
                    "length_m": linear_to_m(self.remnant.length),
                    "area_m2": area_to_m2(self.remnant.area_mm2),
                    "reason": self.remnant.reason,
                }
                if self.remnant is not None
                else None
            ),
            "warnings": list(self.warnings),
            "calculation_trace": [dict(step) for step in self.calculation_trace],
            "layout": dict(self.layout),
        }
