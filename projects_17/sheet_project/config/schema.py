"""Доменная модель CONFIG — `config/schema.py` (этап 1, sheet_project D2).

Роль: CONFIG contract §1 (`contracts.yaml`) + `architecture.md` §2.1.
Чистые данные: `dataclass(frozen=True)` + закрытые множества (`Enum`),
БЕЗ исполняемого кода и БЕЗ openpyxl.

L1-валидация (audit G2): невалидный CONFIG → `ConfigValidationError` с именем
поля ДО генерации. Владелец L1 — этот модуль (L2/L3 — validator, L4 — LibreOffice).

Сериализация: `to_dict` / `from_dict` (правило «CONFIG сериализуем в YAML/JSON»).

Примечание: frozen даёт поверхностную иммутабельность (вложенные list/dict не
замораживаются — по конвенции не мутируются); hash() на экземплярах не используем.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConfigValidationError(ValueError):
    """L1: невалидный CONFIG (fail-fast, до генерации)."""


# ─────────────────────────────────────────────────────────────────────────────
# Закрытые множества (contracts.yaml: type: enum)
# ─────────────────────────────────────────────────────────────────────────────

class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    FORMULA = "formula"
    CURRENCY = "currency"
    PERCENT = "percent"


class ReferenceKind(str, Enum):
    HYPERLINK = "hyperlink"
    CROSS_SHEET_REF = "cross_sheet_ref"


class ValidationKind(str, Enum):
    LIST = "list"
    RANGE = "range"
    TYPE = "type"
    CUSTOM = "custom"


class DisplayKind(str, Enum):
    CONDITIONAL_FORMAT = "conditional_format"
    HIDE_COLUMN = "hide_column"
    FREEZE = "freeze"


class AnchorRow(str, Enum):
    HEADER = "header"
    FIRST_DATA = "first_data"
    LAST_DATA = "last_data"


class AnchorRange(str, Enum):
    CELL = "cell"
    COLUMN = "column"
    DATA_RANGE = "data_range"


class ArtifactStatus(str, Enum):
    CREATING = "CREATING"
    GENERATED = "GENERATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    INVALID = "INVALID"
    FAILED = "FAILED"


# ─────────────────────────────────────────────────────────────────────────────
# Доменные сущности (dataclass, frozen = Value Objects)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationRule:
    """Правило data validation (список/диапазон/тип)."""
    kind: ValidationKind
    values: list[str***REMOVED*** | None = None
    min: float | None = None
    max: float | None = None

    def __post_init__(self) -> None:
        _require_enum("ValidationRule.kind", self.kind, ValidationKind)


@dataclass(frozen=True)
class Field:
    """Колонка листа: имя, тип, обязательность, формат, правила валидации."""
    name: str
    type: FieldType
    required: bool = False
    format: str | None = None
    validation: list[ValidationRule***REMOVED*** | None = None

    def __post_init__(self) -> None:
        _require_nonempty("Field.name", self.name)
        _require_enum("Field.type", self.type, FieldType)


@dataclass(frozen=True)
class DataSource:
    """Привязка листа к коллекции данных (audit H2)."""
    source: str
    field_map: dict[str, str***REMOVED***

    def __post_init__(self) -> None:
        _require_nonempty("DataSource.source", self.source)
        if not self.field_map:
            raise ConfigValidationError("DataSource.field_map: пустой")


@dataclass(frozen=True)
class KPI:
    label: str
    source: str
    format: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty("KPI.label", self.label)


@dataclass(frozen=True)
class Card:
    template: str
    fields: list[str***REMOVED*** | None = None

    def __post_init__(self) -> None:
        _require_nonempty("Card.template", self.template)


@dataclass(frozen=True)
class LookupTable:
    name: str
    values: list[str***REMOVED***

    def __post_init__(self) -> None:
        _require_nonempty("LookupTable.name", self.name)


@dataclass(frozen=True)
class DashboardBlock:
    title: str
    kpis: list[KPI***REMOVED*** | None = None
    cards: list[Card***REMOVED*** | None = None

    def __post_init__(self) -> None:
        _require_nonempty("DashboardBlock.title", self.title)


@dataclass(frozen=True)
class DisplayRule:
    kind: DisplayKind
    condition: str | None = None

    def __post_init__(self) -> None:
        _require_enum("DisplayRule.kind", self.kind, DisplayKind)


@dataclass(frozen=True)
class Anchor:
    """Якорь цели формулы/ссылки (audit H1): логический, НЕ координаты."""
    column: str
    row: AnchorRow = AnchorRow.FIRST_DATA
    offset: int = 0
    range: AnchorRange = AnchorRange.CELL

    def __post_init__(self) -> None:
        _require_nonempty("Anchor.column", self.column)
        _require_enum("Anchor.row", self.row, AnchorRow)
        _require_enum("Anchor.range", self.range, AnchorRange)


@dataclass(frozen=True)
class Formula:
    expression: str
    anchor: Anchor
    note: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty("Formula.expression", self.expression)


@dataclass(frozen=True)
class Reference:
    target_sheet: str
    kind: ReferenceKind = ReferenceKind.HYPERLINK
    anchor: Anchor | None = None
    display: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty("Reference.target_sheet", self.target_sheet)
        _require_enum("Reference.kind", self.kind, ReferenceKind)


@dataclass(frozen=True)
class Sheet:
    name: str
    columns: list[Field***REMOVED***
    data_source: DataSource | None = None
    formulas: list[Formula***REMOVED*** | None = None
    blocks: list[DashboardBlock***REMOVED*** | None = None
    lookup_tables: list[LookupTable***REMOVED*** | None = None
    references: list[Reference***REMOVED*** | None = None

    def __post_init__(self) -> None:
        _require_nonempty("Sheet.name", self.name)


@dataclass(frozen=True)
class Workbook:
    name: str
    template_id: str
    template_version: str
    sheets: list[Sheet***REMOVED***

    def __post_init__(self) -> None:
        _require_nonempty("Workbook.name", self.name)
        _require_nonempty("Workbook.template_id", self.template_id)
        _require_nonempty("Workbook.template_version", self.template_version)


@dataclass(frozen=True)
class GenerationArtifact:
    """Метаданные результата генерации (audit G3; владелец GENERATOR/Orchestrator)."""
    path: str
    generation_id: str
    template_id: str
    template_version: str
    status: ArtifactStatus
    temp_path: str | None = None
    created_at: str | None = None  # ISO-8601
    validated_at: str | None = None  # ISO-8601

    def __post_init__(self) -> None:
        for attr in ("path", "generation_id", "template_id", "template_version"):
            _require_nonempty(f"GenerationArtifact.{attr***REMOVED***", getattr(self, attr))
        _require_enum("GenerationArtifact.status", self.status, ArtifactStatus)


def _require_nonempty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{field_name***REMOVED***: пустое значение")


def _require_enum(field_name: str, value: Any, enum_cls: type[Enum***REMOVED***) -> None:
    if not isinstance(value, enum_cls):
        raise ConfigValidationError(
            f"{field_name***REMOVED***: ожидается {enum_cls.__name__***REMOVED***, получено {type(value).__name__***REMOVED***"
        )


# ─────────────────────────────────────────────────────────────────────────────
# L1-валидация (fail-fast, кросс-сущностные инварианты)
# ─────────────────────────────────────────────────────────────────────────────

def validate_workbook(workbook: Workbook) -> None:
    """L1: структурная валидация CONFIG (fail-fast, с именем поля).

    Проверяет инварианты, которые не видны из одного поля:
    - листы непусты, имена уникальны;
    - имена колонок уникальны в пределах листа;
    - DataSource.field_map: колонки существуют в листе;
    - Formula.anchor.column: колонка существует в листе;
    - Reference.target_sheet: ссылается на существующий лист;
    - Reference(cross_sheet_ref): имеет anchor, а его колонка есть в целевом листе.

    Raise ConfigValidationError при первом нарушении.
    """
    if not workbook.sheets:
        raise ConfigValidationError("Workbook.sheets: пустой (min_items: 1)")

    sheet_by_name: dict[str, Sheet***REMOVED*** = {***REMOVED***
    for sheet in workbook.sheets:
        if sheet.name in sheet_by_name:
            raise ConfigValidationError(f"Workbook.sheets: дубль имени листа '{sheet.name***REMOVED***'")
        sheet_by_name[sheet.name***REMOVED*** = sheet

    for sheet in workbook.sheets:
        _validate_sheet(sheet, sheet_by_name)


def _validate_sheet(sheet: Sheet, sheet_by_name: dict[str, Sheet***REMOVED***) -> None:
    if not sheet.columns:
        raise ConfigValidationError(f"Sheet.{sheet.name***REMOVED***.columns: пустой (min_items: 1)")
    col_names = [c.name for c in sheet.columns***REMOVED***
    if len(col_names) != len(set(col_names)):
        raise ConfigValidationError(f"Sheet.{sheet.name***REMOVED***.columns: дублирующиеся имена колонок")

    if sheet.data_source is not None:
        for col in sheet.data_source.field_map:
            if col not in col_names:
                raise ConfigValidationError(
                    f"Sheet.{sheet.name***REMOVED***.data_source.field_map: колонка '{col***REMOVED***' отсутствует в columns"
                )

    for formula in (sheet.formulas or [***REMOVED***):
        if formula.anchor.column not in col_names:
            raise ConfigValidationError(
                f"Sheet.{sheet.name***REMOVED***.formulas: anchor.column '{formula.anchor.column***REMOVED***' отсутствует в columns"
            )

    for ref in (sheet.references or [***REMOVED***):
        target = sheet_by_name.get(ref.target_sheet)
        if target is None:
            raise ConfigValidationError(
                f"Sheet.{sheet.name***REMOVED***.references: битая ссылка на лист '{ref.target_sheet***REMOVED***'"
            )
        if ref.kind is ReferenceKind.CROSS_SHEET_REF:
            if ref.anchor is None:
                raise ConfigValidationError(
                    f"Sheet.{sheet.name***REMOVED***.references: cross_sheet_ref '{ref.target_sheet***REMOVED***' требует anchor"
                )
            if ref.anchor.column not in [c.name for c in target.columns***REMOVED***:
                raise ConfigValidationError(
                    f"Sheet.{sheet.name***REMOVED***.references: anchor.column '{ref.anchor.column***REMOVED***' отсутствует в листе '{target.name***REMOVED***'"
                )


# ─────────────────────────────────────────────────────────────────────────────
# Сериализация (YAML/JSON-ready)
# ─────────────────────────────────────────────────────────────────────────────

def to_dict(obj: Any) -> Any:
    """Сериализовать CONFIG-граф в plain dict (Enum → value)."""
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        return {f.name: to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)***REMOVED***
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj***REMOVED***
    if isinstance(obj, dict):
        return {key: to_dict(value) for key, value in obj.items()***REMOVED***
    return obj


def from_dict(cls: type, data: Any) -> Any:
    """Реконструировать объект из plain dict по типу cls (обратно to_dict)."""
    origin = typing.get_origin(cls)
    if origin is typing.Union or origin is types.UnionType:
        args = typing.get_args(cls)
        if data is None and type(None) in args:
            return None
        non_none = [a for a in args if a is not type(None)***REMOVED***
        if len(non_none) != 1:
            raise ConfigValidationError(f"from_dict: неоднозначный Union {cls!r***REMOVED***")
        return from_dict(non_none[0***REMOVED***, data)
    if origin is list:
        (item_type,) = typing.get_args(cls)
        return [from_dict(item_type, item) for item in data***REMOVED***
    if origin is dict:
        key_type, value_type = typing.get_args(cls)
        return {from_dict(key_type, k): from_dict(value_type, v) for k, v in data.items()***REMOVED***
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(data)
    if dataclasses.is_dataclass(cls):
        hints = typing.get_type_hints(cls)
        kwargs = {
            f.name: from_dict(hints[f.name***REMOVED***, data[f.name***REMOVED***)
            for f in dataclasses.fields(cls)
            if f.name in data
        ***REMOVED***
        return cls(**kwargs)
    return data


__all__ = [
    "Anchor",
    "AnchorRange",
    "AnchorRow",
    "ArtifactStatus",
    "Card",
    "ConfigValidationError",
    "DashboardBlock",
    "DataSource",
    "DisplayKind",
    "DisplayRule",
    "Field",
    "FieldType",
    "Formula",
    "GenerationArtifact",
    "KPI",
    "LookupTable",
    "Reference",
    "ReferenceKind",
    "Sheet",
    "ValidationKind",
    "ValidationRule",
    "Workbook",
    "from_dict",
    "to_dict",
    "validate_workbook",
***REMOVED***
