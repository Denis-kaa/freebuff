"""Ошибки движка расхода материала (ТЗ §38) — все наследуют CalcInputError.

Коды ошибок — стабильные машинные токены (закрытый набор, дух ANTI-6b):
клиент получает code + человекочитаемое сообщение; приблизительный результат
вместо ошибки ЗАПРЕЩЁН (§38: «не выдавать приблизительный результат»).
"""

from __future__ import annotations

from printcalc.engine.errors import CalcInputError

#: Закрытый набор кодов ошибок движка расхода (ТЗ §38).
CONSUMPTION_ERROR_CODES: tuple[str, ...] = (
    "ROLL_WIDTH_TOO_SMALL",
    "PRODUCT_DOES_NOT_FIT",
    "INVALID_DIMENSION",
    "INVALID_QUANTITY",
    "INVALID_MATERIAL_UNIT",
    "INVALID_ROUNDING",
    "NEGATIVE_ALLOWANCE",
    "INVALID_POLICY",
)


class ConsumptionError(CalcInputError):
    """Ошибка расчёта расхода с машинным кодом (ТЗ §38)."""

    def __init__(self, code: str, message: str) -> None:
        if code not in CONSUMPTION_ERROR_CODES:
            raise ValueError(f"неизвестный код ошибки расхода: {code}")
        super().__init__(code, message)
        self.code = code


__all__ = ["CONSUMPTION_ERROR_CODES", "ConsumptionError"]
