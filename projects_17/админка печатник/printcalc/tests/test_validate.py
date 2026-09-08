"""Тесты схемной валидации движка (CALC-VALIDATE)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec
from printcalc.engine.validate import validate_inputs


def _square(inputs: Mapping[str, Any]) -> CalcResult:
    return CalcResult(
        calculator_id="square",
        price=float(inputs["x"]) ** 2,
        price_no_tax=float(inputs["x"]) ** 2,
        cost=0.0,
        net_profit=0.0,
        unit_price=0.0,
    )


SQ = CalculatorSpec(
    id="square",
    title="Square",
    version="0.1.0",
    fields=(FieldSpec(name="x", kind=FieldKind.NUMBER, title="X"),),
)


def test_unknown_field_rejected() -> None:
    with pytest.raises(CalcInputError) as exc:
        validate_inputs(SQ, {"x": 2.0, "zzz": 1})
    assert exc.value.field == "zzz"


def test_missing_required_rejected() -> None:
    with pytest.raises(CalcInputError) as exc:
        validate_inputs(SQ, {})
    assert exc.value.field == "x"


def test_bool_is_not_number() -> None:
    with pytest.raises(CalcInputError) as exc:
        validate_inputs(SQ, {"x": True})
    assert exc.value.field == "x"


def test_string_number_accepted() -> None:
    validate_inputs(SQ, {"x": "12.5"})


def test_exclusive_min_zero_rejected() -> None:
    spec = CalculatorSpec(
        id="t",
        title="T",
        version="0.1.0",
        fields=(
            FieldSpec(
                name="n", kind=FieldKind.NUMBER, title="N",
                min_value=0, exclusive_min=True,
            ),
        ),
    )
    with pytest.raises(CalcInputError):
        validate_inputs(spec, {"n": 0})
    validate_inputs(spec, {"n": 0.001})


def test_integer_rejects_fraction() -> None:
    spec = CalculatorSpec(
        id="t",
        title="T",
        version="0.1.0",
        fields=(FieldSpec(name="n", kind=FieldKind.INTEGER, title="N"),),
    )
    with pytest.raises(CalcInputError) as exc:
        validate_inputs(spec, {"n": 1.5})
    assert "целое" in exc.value.message


def test_enum_membership() -> None:
    spec = CalculatorSpec(
        id="t",
        title="T",
        version="0.1.0",
        fields=(
            FieldSpec(
                name="c", kind=FieldKind.ENUM, title="C",
                options=("a", "b"), default="a",
            ),
        ),
    )
    validate_inputs(spec, {})
    validate_inputs(spec, {"c": "b"})
    with pytest.raises(CalcInputError) as exc:
        validate_inputs(spec, {"c": "z"})
    assert "допустимые значения" in exc.value.message


def test_optional_with_default_missing_ok() -> None:
    spec = CalculatorSpec(
        id="t",
        title="T",
        version="0.1.0",
        fields=(
            FieldSpec(
                name="m", kind=FieldKind.NUMBER, title="M",
                default=25.0, required=False,
            ),
        ),
    )
    validate_inputs(spec, {})
