"""Тесты доменной модели `config/schema.py` (этап 1)."""

from dataclasses import FrozenInstanceError

import pytest

from config.schema import (
    Anchor,
    AnchorRange,
    AnchorRow,
    ArtifactStatus,
    ConfigValidationError,
    DataSource,
    Field,
    FieldType,
    Formula,
    GenerationArtifact,
    Reference,
    ReferenceKind,
    Sheet,
    Workbook,
    from_dict,
    to_dict,
    validate_workbook,
)


def _field(name: str, ftype: FieldType = FieldType.TEXT) -> Field:
    return Field(name=name, type=ftype)


def _minimal_workbook() -> Workbook:
    sheet = Sheet(
        name="Projects",
        columns=[_field("name"), _field("status")],
        data_source=DataSource(source="projects", field_map={"name": "name", "status": "status"}),
    )
    return Workbook(
        name="dashboard",
        template_id="project_management",
        template_version="1.0",
        sheets=[sheet],
    )


def _full_workbook() -> Workbook:
    projects = Sheet(
        name="Projects",
        columns=[_field("name"), _field("status")],
        data_source=DataSource(source="projects", field_map={"name": "name", "status": "status"}),
        formulas=[Formula(expression="=COUNTA({status))", anchor=Anchor(column="status"))],
        references=[
            Reference(
                target_sheet="Tasks",
                kind=ReferenceKind.CROSS_SHEET_REF,
                anchor=Anchor(column="project_id"),
            )
        ],
    )
    tasks = Sheet(
        name="Tasks",
        columns=[_field("project_id"), _field("title")],
        data_source=DataSource(source="tasks", field_map={"project_id": "project_id", "title": "title"}),
    )
    return Workbook(
        name="dashboard",
        template_id="project_management",
        template_version="1.0",
        sheets=[projects, tasks],
    )


# ── enums ──

def test_enum_values():
    assert FieldType.TEXT.value == "text"
    assert FieldType.CURRENCY.value == "currency"
    assert ReferenceKind.CROSS_SHEET_REF.value == "cross_sheet_ref"
    assert AnchorRow.FIRST_DATA.value == "first_data"
    assert AnchorRange.DATA_RANGE.value == "data_range"
    assert ArtifactStatus.READY.value == "READY"


# ── construction + L1 validation ──

def test_minimal_workbook_is_valid():
    validate_workbook(_minimal_workbook())  # не raises


def test_full_workbook_is_valid():
    validate_workbook(_full_workbook())


def test_empty_sheets_rejected():
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[])
    with pytest.raises(ConfigValidationError):
        validate_workbook(wb)


def test_duplicate_sheet_names_rejected():
    s = Sheet(name="A", columns=[_field("x")])
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[s, s])
    with pytest.raises(ConfigValidationError):
        validate_workbook(wb)


def test_duplicate_column_names_rejected():
    s = Sheet(name="A", columns=[_field("x"), _field("x")])
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[s])
    with pytest.raises(ConfigValidationError):
        validate_workbook(wb)


def test_field_map_unknown_column_rejected():
    s = Sheet(
        name="A",
        columns=[_field("name")],
        data_source=DataSource(source="projects", field_map={"ghost": "ghost"}),
    )
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[s])
    with pytest.raises(ConfigValidationError, match="ghost"):
        validate_workbook(wb)


def test_broken_reference_target_sheet_rejected():
    s = Sheet(name="A", columns=[_field("x")], references=[Reference(target_sheet="Nope")])
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[s])
    with pytest.raises(ConfigValidationError, match="Nope"):
        validate_workbook(wb)


def test_cross_sheet_ref_requires_anchor():
    a = Sheet(name="A", columns=[_field("x")])
    b = Sheet(
        name="B",
        columns=[_field("y")],
        references=[Reference(target_sheet="A", kind=ReferenceKind.CROSS_SHEET_REF)],
    )
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[a, b])
    with pytest.raises(ConfigValidationError, match="anchor"):
        validate_workbook(wb)


def test_formula_anchor_column_must_exist():
    s = Sheet(
        name="A",
        columns=[_field("x")],
        formulas=[Formula(expression="=1", anchor=Anchor(column="ghost"))],
    )
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[s])
    with pytest.raises(ConfigValidationError, match="ghost"):
        validate_workbook(wb)


def test_empty_required_string_rejected():
    with pytest.raises(ConfigValidationError):
        Workbook(
            name="",
            template_id="t",
            template_version="1",
            sheets=[Sheet(name="A", columns=[_field("x")])],
        )


def test_empty_columns_rejected():
    wb = Workbook(name="x", template_id="t", template_version="1", sheets=[Sheet(name="A", columns=[])])
    with pytest.raises(ConfigValidationError):
        validate_workbook(wb)


def test_enum_field_rejects_raw_string():
    with pytest.raises(ConfigValidationError):
        Field(name="x", type="text")  # type: ignore[arg-type]


# ── immutability + defaults ──

def test_frozen_immutability():
    f = _field("x")
    with pytest.raises(FrozenInstanceError):
        f.name = "y"  # type: ignore[misc]


def test_anchor_defaults():
    a = Anchor(column="col")
    assert a.row is AnchorRow.FIRST_DATA
    assert a.offset == 0
    assert a.range is AnchorRange.CELL


# ── serialization ──

def test_to_dict_from_dict_roundtrip():
    wb = _full_workbook()
    assert from_dict(Workbook, to_dict(wb)) == wb


def test_to_dict_uses_enum_values():
    d = to_dict(_minimal_workbook())
    assert d["sheets"][0]["columns"][0]["type"] == "text"


def test_generation_artifact_roundtrip():
    artifact = GenerationArtifact(
        path="output/x.xlsx",
        generation_id="g1",
        template_id="project_management",
        template_version="1.0",
        status=ArtifactStatus.GENERATED,
    )
    assert artifact.status is ArtifactStatus.GENERATED
    assert from_dict(GenerationArtifact, to_dict(artifact)) == artifact
