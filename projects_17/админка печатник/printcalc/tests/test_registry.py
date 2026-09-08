"""Тесты реестра и фасада calculate() (CALC-REGISTRY)."""

from __future__ import annotations

import pytest

from printcalc.calculators.riso import SPEC as RISO_SPEC, compute as riso_compute
from printcalc.engine import (
    CalcInputError,
    CalculatorRegistry,
    RegistryError,
    calculate,
)


@pytest.fixture()
def registry() -> CalculatorRegistry:
    reg = CalculatorRegistry()
    reg.register(RISO_SPEC, riso_compute)
    return reg


def test_register_and_ids(registry: CalculatorRegistry) -> None:
    assert registry.ids() == ("riso",)
    assert "riso" in registry


def test_duplicate_id_rejected() -> None:
    reg = CalculatorRegistry()
    reg.register(RISO_SPEC, riso_compute)
    with pytest.raises(RegistryError) as exc:
        reg.register(RISO_SPEC, riso_compute)
    assert "уже зарегистрирован" in str(exc.value)


def test_unknown_id_rejected(registry: CalculatorRegistry) -> None:
    with pytest.raises(RegistryError) as exc:
        registry.get("nope")
    assert "неизвестный калькулятор" in str(exc.value)


def test_calculate_end_to_end(registry: CalculatorRegistry) -> None:
    result = calculate(
        registry,
        "riso",
        {
            "format": "A4",
            "qty": 1000.0,
            "originals": 1.0,
            "color": "ч/б",
            "paper": "Офсетная 80 г/м²",
        },
    )
    assert result.price == pytest.approx(485.37234042553195)
    assert result.cost == pytest.approx(105.0)


def test_calculate_runs_validation_first(registry: CalculatorRegistry) -> None:
    # Неизвестное поле ловится схемой ещё до compute.
    with pytest.raises(CalcInputError) as exc:
        calculate(registry, "riso", {"qty": 1000.0, "zzz": 1})
    assert exc.value.field == "zzz"


def test_calculate_missing_required(registry: CalculatorRegistry) -> None:
    # format/paper/color имеют default; обязательные без default — qty и originals.
    with pytest.raises(CalcInputError) as exc:
        calculate(registry, "riso", {"originals": 1.0})
    assert exc.value.field == "qty"


def test_calculate_defaults_fill_missing_optional_fields(
    registry: CalculatorRegistry,
) -> None:
    result = calculate(
        registry,
        "riso",
        {
            "format": "A6",
            "qty": 10000.0,
            "originals": 1.0,
            "color": "2 краски",
            "paper": "Газетная",
            "markup_percent": 0.0,
        },
    )
    assert result.details["duplex"] is False
    assert result.price_no_tax == pytest.approx(1005.0)
