"""Tests for knowledge curator."""

from realtor_automation.curator import build_plan


def test_build_plan_contains_topic() -> None:
    plan = build_plan("холодные звонки")
    assert "холодные звонки" in plan.format()


def test_build_plan_has_sources() -> None:
    plan = build_plan("возражения")
    assert len(plan.fundamentals) > 0
    assert len(plan.strategies) > 0
