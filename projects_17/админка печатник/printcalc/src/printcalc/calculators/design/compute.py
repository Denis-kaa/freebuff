"""Чистая функция расчёта дизайна — порт 1:1 legacy updatePrice().

Источник: «Калькулятор макетов/design_calc.py» — JS updatePrice() (строка
в HTML: фильтр base/option/side) + export_pdf-поиск (строки 118–126).
Формулы НЕТ: цена = позиция прайса по тройке (услуга, сторона, уровень).
    price == 0            → «Цена по запросу», результат 0 (Вывеска)
    позиция не найдена    → «по договорённости», CalcInputError по услуге,
                            0 по варианту (parity: GUI скрывает вариант,
                            который не даёт цену — не ошибка ввода услуги)
Наценка/налог/тираж отсутствуют — parity сохранён (price == price_no_tax,
profit = 0, тираж на цену не влияет).
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.calculators.design.config import DesignConfig
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine


def compute(inputs: Mapping[str, Any], config: DesignConfig | None = None) -> CalcResult:
    """Считает цену работы дизайнера по входам и конфигу (паритет legacy)."""
    cfg = config if config is not None else DesignConfig()

    service = _str_input(inputs, "service")
    if not service:
        raise CalcInputError("service", "Услуга / вид работ не выбрана")
    if service not in cfg.services():
        raise CalcInputError("service", f"Неизвестная услуга: «{service}»")

    side = inputs.get("side", "") or ""
    if not isinstance(side, str):
        raise CalcInputError("side", "ожидалась строка")
    option = inputs.get("option", "") or ""
    if not isinstance(option, str):
        raise CalcInputError("option", "ожидалась строка")

    # Тираж/полосы на цену не влияют (прайс за работу) — только валидируем.
    pages = _num_optional(inputs, "pages", default=1.0)
    circulation = _num_optional(inputs, "circulation", default=500.0)
    if pages < 0 or circulation < 0:
        raise CalcInputError("pages", "Страницы/тираж не могут быть отрицательными")

    item = cfg.lookup(service, side, option)

    warnings: list[str] = []
    if item is None:
        # «по договорённости» — услуга известна, комбинация вариантов нет.
        warnings.append(
            f"Комбинация без цены — по договорённости: {service}"
            + (f" / {side}" if side else "")
            + (f" / {option}" if option else "")
        )
        price = 0.0
        found_name = ""
    else:
        found_name = item.name
        price = float(item.price)
        if price == 0:
            warnings.append("Цена по запросу")

    lines: list[CostLine] = [
        CostLine(found_name or service, price),
        CostLine("ИТОГО", price),
    ]

    details: dict[str, Any] = {
        "service": service,
        "side": side,
        "option": option,
        "category": item.category if item else None,
        "price_item": found_name,
        "price_found": item is not None,
        "price_on_request": item is not None and item.price == 0,
        "pages": pages,
        "circulation": circulation,
    }

    return CalcResult(
        calculator_id="design",
        price=price,
        price_no_tax=price,
        cost=price,
        net_profit=0.0,
        unit_price=price,  # прайс за работу, не за тираж
        lines=tuple(lines),
        warnings=tuple(warnings),
        details=details,
    )


def _num_optional(
    inputs: Mapping[str, Any], name: str, default: float
) -> float:
    value = inputs.get(name, default)
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


__all__ = ["compute"]
