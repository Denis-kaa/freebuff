"""Реестр калькуляторов (CALC-REGISTRY).

Закрытый словарь в духе ANTI-6b: неизвестный id и дубликат id — ошибки,
никаких silent fallback. calculate() — фасад полного конвейера:
метаданные -> схемная валидация -> compute().
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.engine.errors import RegistryError
from printcalc.engine.result import CalcResult
from printcalc.engine.spec import CalculatorRegistration, CalculatorSpec
from printcalc.engine.validate import validate_inputs


class CalculatorRegistry:
    """Реестр «id -> (спека, compute)»."""

    def __init__(self) -> None:
        self._items: dict[str, CalculatorRegistration] = {}

    def register(self, spec: CalculatorSpec, compute: Any) -> None:
        """Регистрирует калькулятор. Raises RegistryError при дубликате id."""
        if spec.id in self._items:
            raise RegistryError(f"калькулятор '{spec.id}' уже зарегистрирован")
        self._items[spec.id] = CalculatorRegistration(spec=spec, compute=compute)

    def get(self, calculator_id: str) -> CalculatorRegistration:
        """Возвращает регистрацию. Raises RegistryError для неизвестного id."""
        try:
            return self._items[calculator_id]
        except KeyError:
            raise RegistryError(f"неизвестный калькулятор: '{calculator_id}'") from None

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    def __contains__(self, calculator_id: str) -> bool:
        return calculator_id in self._items


def calculate(
    registry: CalculatorRegistry,
    calculator_id: str,
    inputs: Mapping[str, Any],
) -> CalcResult:
    """Полный конвейер: валидация схемы -> чистая функция расчёта."""
    registration = registry.get(calculator_id)
    validate_inputs(registration.spec, inputs)
    return registration.compute(inputs)
