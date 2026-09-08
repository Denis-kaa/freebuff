"""Ошибки движка калькуляторов.

Паритет с legacy: оригинальный GUI (tkinter) показывал ровно одну ошибку
за раз и прерывал расчёт (messagebox.showerror + return). Движок сохраняет
это поведение — первое же нарушение прерывает валидацию/расчёт.
"""

from __future__ import annotations

from dataclasses import dataclass


class CalcError(Exception):
    """Базовая ошибка движка калькуляторов."""


@dataclass(frozen=True)
class ValidationIssue:
    """Структурированное описание одной проблемы входа."""

    field: str
    message: str


class CalcInputError(CalcError):
    """Ошибка входных данных (аналог messagebox.showerror в legacy).

    Attributes:
        field: имя поля, к которому относится ошибка.
        message: человекочитаемое сообщение (тексты legacy сохранены).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message

    def to_issue(self) -> ValidationIssue:
        return ValidationIssue(field=self.field, message=self.message)


class RegistryError(CalcError):
    """Ошибка реестра: дубликат или неизвестный id калькулятора.

    Паритет с ANTI-6b: закрытый словарь — никаких silent fallback.
    """
