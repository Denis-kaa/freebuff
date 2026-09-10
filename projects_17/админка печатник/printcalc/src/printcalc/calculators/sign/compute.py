"""Чистая функция расчёта Вывесок — порт 1:1 SignCalculator.calculate().

Источник: «Общий калькулятор печати/build_all/sign_calc.py», строки 782–930.
Порядок арифметических операций и float-семантика сохранены сознательно —
golden-тесты закрепляют паритет с legacy. GUI-ветки заменены CalcInputError;
материал «Авто» резолвится в дефолт детали (legacy get_price); настройка
«прайс за единицу» (PRICE_PER_CM > 0) переключает режим цены с
себестоимости на прайс — обе ветки перенесены.
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.calculators.sign.config import COMPLEXITY_FACTORS, SignConfig
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine


def compute(inputs: Mapping[str, Any], config: SignConfig | None = None) -> CalcResult:
    """Считает цену/себестоимость/прибыль вывески по входам и конфигу."""
    cfg = config if config is not None else SignConfig()

    product = _str_input(inputs, "product")
    if product not in cfg.product_model:
        raise CalcInputError("product", f"Неизвестное изделие: «{product}»")
    model = cfg.product_model[product]
    model_spec = cfg.base_models.get(model)
    if model_spec is None:
        raise CalcInputError("product", f"Неизвестная модель: «{model}»")
    unit = cfg.product_unit.get(product, "cm")
    qty = _num_input(inputs, "qty")
    if qty <= 0:
        raise CalcInputError("qty", "Количество должно быть больше 0")
    markup = _num_input(inputs, "markup_percent", default=cfg.markup_default) / 100.0

    complexity_name = _str_input(inputs, "complexity")
    complexity = COMPLEXITY_FACTORS.get(complexity_name, 1.0)

    # Геометрия (legacy 793–809).
    area: float
    per: float
    units: float
    if unit == "sqm":
        height_m = _num_input(inputs, "height")
        width_m = _num_input(inputs, "width")
        if width_m <= 0:
            raise CalcInputError("width", "Для короба нужна ширина, м")
        area = width_m * height_m * qty
        per = 2 * (width_m + height_m) * qty
        units = area
    else:
        height_cm = _num_input(inputs, "height")
        height_m = height_cm / 100.0
        width_m = height_m * cfg.letter_width_ratio
        area = width_m * height_m * qty
        per = 2 * (width_m + height_m) * qty
        units = height_cm * qty

    # Материалы (legacy 811–826): «Авто» → дефолт детали; отсутствующий
    # материал — fallback 200 ₽ (MATERIALS.get).
    spec = cfg.parts_for(product)
    material_cost = 0.0
    if spec.front is not None:
        front = _auto(_str_input(inputs, "front_material"), spec.front)
        material_cost += area * cfg.material_price(front, cfg.unknown_material_price)
    if spec.side is not None and spec.side_height:
        side = _auto(_str_input(inputs, "side_material"), spec.side)
        material_cost += (
            per * spec.side_height * cfg.material_price(side, cfg.unknown_material_price)
        )
    if spec.back is not None:
        back = _auto(_str_input(inputs, "back_material"), spec.back)
        material_cost += area * cfg.material_price(back, cfg.unknown_material_price)

    # Работа (legacy 829–830).
    work_cost = area * model_spec.work_rate * complexity

    # Подсветка (legacy 833–838).
    light_cost = 0.0
    if model_spec.light:
        if model == "Световой короб":
            light_cost = area * cfg.box_light_rate
        else:
            light_cost = per * cfg.letter_light_length * cfg.letter_light_rate

    # Изображение (legacy 841–842).
    image_name = _str_input(inputs, "image_type")
    image_cost = area * cfg.image_prices.get(image_name, 0.0)

    # Подложка (legacy 845–853): пара «площадь + материал» вместо чекбокса.
    substrate_area = _num_input(inputs, "substrate_area_m2", default=0.0)
    substrate_cost = 0.0
    if substrate_area > 0:
        substrate_material = _str_input(inputs, "substrate_material")
        substrate_cost = substrate_area * (
            cfg.material_price(substrate_material, cfg.default_substrate_price)
            + cfg.substrate_work_rate
        )

    # Каркас (legacy 856–862).
    frame_length = _num_input(inputs, "frame_length_m", default=0.0)
    frame_cost = 0.0
    if frame_length > 0:
        frame_material = _str_input(inputs, "frame_material")
        frame_cost = frame_length * (
            cfg.frame_prices.get(frame_material, cfg.default_frame_price)
            + cfg.frame_work_rate
        )

    # Монтаж по высоте (legacy 865–870).
    mounting = _str_input(inputs, "mounting")
    mount_cost = 0.0
    if mounting != "нет":
        if mounting not in cfg.mount_percents:
            raise CalcInputError("mounting", f"Неизвестный вариант монтажа: «{mounting}»")
        mount_cost = cfg.mount_base_cost * (1 + cfg.mount_percents[mounting] / 100.0)

    # Электрика/доставка/блоки (legacy 873–877).
    electric_cost = 0.0
    if _flag_input(inputs, "electric"):
        electric_cost = per * cfg.electric_per_meter + cfg.electric_base_cost
    delivery_km = _num_input(inputs, "delivery_distance_km", default=0.0)
    delivery_cost = delivery_km * cfg.delivery_per_km if delivery_km > 0 else 0.0
    ps_count = _num_input(inputs, "power_supply_count", default=0.0)
    ps_cost = ps_count * cfg.power_supply_cost

    extra = (
        mount_cost
        + electric_cost
        + delivery_cost
        + substrate_cost
        + frame_cost
        + image_cost
        + ps_cost
    )

    # Режим цены (legacy 880–891): прайс за единицу или себестоимость.
    price_per_unit = cfg.price_per_unit.get(product, 0.0)
    if price_per_unit > 0:
        base_total = price_per_unit * units
        full_cost = material_cost + work_cost + light_cost + extra
        price_no_tax = base_total + extra * (1 + markup)
    else:
        full_cost = material_cost + work_cost + light_cost + extra
        price_no_tax = full_cost * (1 + markup)

    price = price_no_tax / (1 - cfg.tax_rate)
    net_profit = price * (1 - cfg.tax_rate) - full_cost
    unit_price = price_no_tax / units if units else 0.0

    lines: list[CostLine] = [
        CostLine("Материалы", material_cost),
        CostLine("Работа", work_cost),
        CostLine("Подсветка", light_cost),
        CostLine("Монтаж", mount_cost),
        CostLine("Электрика", electric_cost),
        CostLine("Доставка", delivery_cost),
        CostLine("Подложка", substrate_cost),
        CostLine("Каркас", frame_cost),
        CostLine("Изображение", image_cost),
        CostLine(f"Блоки питания (x{ps_count:.0f})", ps_cost),
        CostLine("Себестоимость", full_cost),
        CostLine("Цена без налога", price_no_tax),
        CostLine(f"Налог ({cfg.tax_rate * 100:.0f}%)", price - price_no_tax),
        CostLine("ИТОГО ЦЕНА", price),
    ]

    details: dict[str, Any] = {
        "product": product,
        "model": model,
        "unit": unit,
        "qty": qty,
        "area_m2": area,
        "perimeter_m": per,
        "units": units,
        "complexity": complexity_name,
        "material_cost": material_cost,
        "work_cost": work_cost,
        "light_cost": light_cost,
        "extra": extra,
        "price_mode": "price_list" if price_per_unit > 0 else "cost_markup",
        "price_per_unit": price_per_unit,
        "markup_percent": markup * 100,
    }

    return CalcResult(
        calculator_id="sign",
        price=price,
        price_no_tax=price_no_tax,
        cost=full_cost,
        net_profit=net_profit,
        unit_price=unit_price,
        lines=tuple(lines),
        details=details,
    )


def _auto(chosen: str, default: str) -> str:
    """Материал «Авто» → дефолт детали (legacy get_price, строка 810)."""
    return default if chosen == "Авто" else chosen


def _num_input(
    inputs: Mapping[str, Any], name: str, default: float | None = None
) -> float:
    if name not in inputs:
        if default is not None:
            return default
        raise CalcInputError(name, "обязательное поле не задано")
    value = inputs[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcInputError(name, "ожидалось число")
    return float(value)


def _str_input(inputs: Mapping[str, Any], name: str) -> str:
    if name not in inputs:
        raise CalcInputError(name, "обязательное поле не задано")
    value = inputs[name]
    if not isinstance(value, str):
        raise CalcInputError(name, "ожидалась строка")
    return value


def _flag_input(inputs: Mapping[str, Any], name: str) -> bool:
    value = inputs.get(name, False)
    if not isinstance(value, bool):
        raise CalcInputError(name, "ожидался логический флаг (true/false)")
    return value
