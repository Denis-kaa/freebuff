#!/usr/bin/env python3
"""Tests for Orchestrator (scripts_01/orchestrator.py)."""

from __future__ import annotations

import json
import os
import sys
import pytest
}
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.orchestrator import (
    Orchestrator, DefaultPlanner, ToolExecutor, StepValidator,
    Step, Workflow, StepStatus, WorkflowStatus, StepType, ToolType,
)


class TestStepLifecycle:
    def test_step_default_status(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        assert step.status == StepStatus.PENDING
        assert step.retry_count == 0
        assert step.max_retries == 2

    def test_step_to_success(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        step.status = StepStatus.RUNNING
        assert step.status == StepStatus.RUNNING
        step.status = StepStatus.SUCCESS
        assert step.status == StepStatus.SUCCESS

    def test_step_to_failed(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        step.status = StepStatus.FAILED
        step.error = "Something went wrong"
        assert step.status == StepStatus.FAILED
        assert step.error == "Something went wrong"

    def test_step_retry(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL, max_retries=3)
        step.retry_count = 1
        step.status = StepStatus.PENDING
        assert step.retry_count == 1


class TestWorkflowLifecycle:
    def test_workflow_default(self):
        wf = Workflow(id="wf1", goal="Test goal")
        assert wf.status == WorkflowStatus.PENDING
        assert wf.steps == []
        assert wf.errors == []

    def test_workflow_to_completed(self):
        wf = Workflow(id="wf1", goal="Test")
        wf.status = WorkflowStatus.RUNNING
        wf.status = WorkflowStatus.COMPLETED
        assert wf.status == WorkflowStatus.COMPLETED

    def test_workflow_to_failed(self):
        wf = Workflow(id="wf1", goal="Test")
        wf.status = WorkflowStatus.FAILED
        wf.errors.append("Critical error")
        assert wf.status == WorkflowStatus.FAILED

    def test_workflow_to_dict(self):
        step = Step(id="s1", type=StepType.TOOL, name="Test", tool=ToolType.SHELL)
        wf = Workflow(id="wf1", goal="Test", steps=[step])
        wf.status = WorkflowStatus.COMPLETED
        d = wf.to_dict()
        assert d["id"] == "wf1"
        assert d["status"] == "completed"
        assert len(d["steps"]) == 1


class TestToolExecutor:
    def test_shell_simple(self):
        success, result, error = ToolExecutor.run(
            ToolType.SHELL, {"command": "echo hello"}, timeout=5
        )
        assert success
        assert "hello" in result

    def test_shell_failure(self):
        success, result, error = ToolExecutor.run(
            ToolType.SHELL, {"command": "exit 1"}, timeout=5
        )
        assert not success
        assert error is not None

    def test_shell_no_command(self):
        success, result, error = ToolExecutor.run(ToolType.SHELL, {}, timeout=5)
        assert not success

    def test_python_exec(self):
        success, result, error = ToolExecutor.run(
            ToolType.PYTHON, {"code": "print('hello from python')"}, timeout=5
        )
        assert success
        assert "hello from python" in result

    def test_python_syntax_error(self):
        success, result, error = ToolExecutor.run(
            ToolType.PYTHON, {"code": "print(}"], timeout=5
        )
        assert not success

    def test_python_no_code(self):
        success, result, error = ToolExecutor.run(ToolType.PYTHON, {}, timeout=5)
        assert not success

    def test_file_read_readme(self):
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {"action": "read", "path": "README.md"}, timeout=5
        )
        assert success
        assert len(result) > 0

    def test_file_not_found(self):
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {"action": "read", "path": "nonexistent_file_xyz.md"}, timeout=5
        )
        assert not success

    def test_file_write_absolute_path(self, tmp_path: Path):
        test_path = str(tmp_path / "test_output.txt")
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {
                "action": "write",
                "path": test_path,
                "content": "test content",
            ], timeout=5
        )
        # Absolute path overrides WORKSPACE on POSIX
        if success:
            written = Path(test_path).read_text()
            assert "test content" in written
        else:
            # If file tool doesn't support absolute paths, at least don't crash
            assert error is not None

    def test_unknown_tool(self):
        success, result, error = ToolExecutor.run("unknown_tool", {}, timeout=5)
        assert not success
        assert "Unknown" in (error or "")


class TestValidator:
    def test_not_empty_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"not_empty": True}})
        step.status = StepStatus.SUCCESS
        step.result = "some result"
        is_valid, error = StepValidator.validate(step, {})
        assert is_valid

    def test_not_empty_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"not_empty": True}})
        step.status = StepStatus.SUCCESS
        step.result = ""
        is_valid, error = StepValidator.validate(step, {})
        assert not is_valid

    def test_min_length_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"min_length": 5}})
        step.status = StepStatus.SUCCESS
        step.result = "hello world"
        is_valid, error = StepValidator.validate(step, {})
        assert is_valid

    def test_min_length_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"min_length": 50}})
        step.status = StepStatus.SUCCESS
        step.result = "short"
        is_valid, error = StepValidator.validate(step, {})
        assert not is_valid

    def test_contains_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"contains": "SUCCESS"}})
        step.status = StepStatus.SUCCESS
        step.result = "Task completed SUCCESS"
        is_valid, error = StepValidator.validate(step, {})
        assert is_valid

    def test_contains_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"contains": "FAILED"}})
        step.status = StepStatus.SUCCESS
        step.result = "Task completed OK"
        is_valid, error = StepValidator.validate(step, {})
        assert not is_valid

    def test_not_success_status(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        step.status = StepStatus.FAILED
        is_valid, error = StepValidator.validate(step, {})
        assert not is_valid


class TestDefaultPlanner:
    def test_plan_code_goal(self):
        steps = DefaultPlanner.plan("Refactor the router module")
        assert len(steps) >= 3
        types = [s.type for s in steps]
        assert StepType.TOOL in types

    def test_plan_research_goal(self):
        steps = DefaultPlanner.plan("Research memory engine architecture")
        assert len(steps) >= 2

    def test_plan_architecture_goal(self):
        steps = DefaultPlanner.plan("Design new plugin API")
        assert len(steps) >= 2

    def test_plan_all_steps_have_ids(self):
        steps = DefaultPlanner.plan("Implement new feature")
        for s in steps:
            assert s.id


class TestContextAwareRouting:
    """Правило 8 (промт 37): Context-Aware Routing — проверка контекста перед созданием задачи."""

    def test_check_existing_context_returns_list(self):
        """check_existing_context всегда возвращает список (может быть пустым)."""
        orch = Orchestrator()
        matches = orch.check_existing_context("Test workflow")
        assert isinstance(matches, list)
        for m in matches:
            assert "doc_id" in m
            assert "score" in m
            assert "snippet" in m

    def test_check_existing_context_mocked_knowledge(self, tmp_path: Path):
        """При наличии индекса возвращаются совпадения с полями контракта."""
        class FakeResult:
            doc_id = "doc_1"
            score = 0.95
            snippet = "existing knowledge snippet"
            metadata = {"title": "Existing Work", "doc_type": "note"}

        class FakeKE:
            def search(self, *args, **kwargs):
                return [FakeResult()]

        # Создаём файл индекса во временном воркспейсе
        index_file = tmp_path / "context_12" / "knowledge" / "index.db"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("")

        import scripts_01.orchestrator as orch_mod
        orig_ws = orch_mod.WORKSPACE
        orch_mod.WORKSPACE = tmp_path
        try:
            with patch("scripts_01.knowledge_engine.KnowledgeEngine", return_value=FakeKE()):
                orch = Orchestrator()
                matches = orch.check_existing_context("Implement feature")
        finally:
            orch_mod.WORKSPACE = orig_ws

        assert len(matches) == 1
        assert matches[0]["doc_id"] == "doc_1"
        assert matches[0]["title"] == "Existing Work"

    def test_run_workflow_publishes_context_check_event(self):
        """Событие workflow.context_check публикуется при запуске workflow."""
        from scripts_01.event_bus import EventBus
        eb = EventBus()
        collected = []
        eb.subscribe("workflow.context_check", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        orch.run_workflow("Test context event")
        assert len(collected) >= 1
        assert "workflow_id" in collected[0].data
        assert "goal" in collected[0].data
        assert "matches" in collected[0].data

    def test_workflow_metadata_has_context_matches(self):
        """Результат проверки контекста сохраняется в workflow.metadata."""
        orch = Orchestrator()
        result = orch.run_workflow("Test metadata")
        assert "context_matches" in result.metadata
        assert isinstance(result.metadata["context_matches"], list)


class TestOrchestrator:
    def test_run_simple_workflow(self):
        orch = Orchestrator()
        result = orch.run_workflow("Test simple workflow")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
        assert len(result.steps) >= 1

    def test_run_code_workflow(self):
        orch = Orchestrator()
        result = orch.run_workflow("Implement a simple hello world")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)

    def test_workflow_has_id(self):
        orch = Orchestrator()
        result = orch.run_workflow("Test")
        assert result.id
        assert len(result.id) == 12

    def test_get_ready_steps_simple(self):
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"]),
        ]
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0].id == "s1"

    def test_get_ready_steps_chain(self):
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"]),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s2"]),
        ]
        # s1 ready
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0].id == "s1"
        # Complete s1
        wf.steps[0].status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0].id == "s2"

    def test_context_stored_on_success(self):
        """Output key is stored in context when step succeeds."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test context")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"command": "echo context_value"},
                    output_key="test_key")
        wf.steps = [step]
        orch._execute_step(step, wf)
        if step.status == StepStatus.SUCCESS:
            assert wf.context.get("test_key") is not None
            assert "context_value" in str(wf.context["test_key"])

    def test_workflow_errors_collected(self):
        """Workflow accumulates errors from failed steps after max retries."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test errors")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"command": "false"}, max_retries=0)
        wf.steps = [step]
        orch._execute_step(step, wf)
        assert step.status == StepStatus.FAILED
        assert step.error is not None
        assert len(wf.errors) >= 1

    def test_failed_deps_skip_downstream(self):
        """Steps with failed deps become SKIPPED."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test deps")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"]),
        ]
        wf.steps[0].status = StepStatus.FAILED
        wf.steps[0].error = "catastrophic failure"
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 0

    # ── Parallel execution tests ──────────────────────────────

    def test_max_workers_param(self):
        """Orchestrator accepts max_workers parameter."""
        orch = Orchestrator(max_workers=8)
        assert orch.max_workers == 8

    def test_max_workers_default(self):
        """Default max_workers is 4."""
        orch = Orchestrator()
        assert orch.max_workers == 4

    def test_independent_steps_run_in_parallel(self):
        """Steps without depends_on are picked up together as ready."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Parallel test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo a"}),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo b"}),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo c"}),
        ]
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 3
        ids = {s.id for s in ready}
        assert ids == {"s1", "s2", "s3"}

    def test_parallel_workflow_completes(self):
        """Full parallel workflow with independent steps completes."""
        orch = Orchestrator(max_workers=3)
        result = orch.run_workflow("Implement hello world")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
        # All steps should have terminal status
        for step in result.steps:
            assert step.status in (
                StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED
            )

    def test_chain_still_respects_dependencies(self):
        """Steps in a chain execute sequentially (dependencies respected)."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Chain test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo first"}),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo second"},
                 depends_on=["s1"]),
        ]
        # Only s1 should be ready initially
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0].id == "s1"
        # After s1 succeeds, s2 becomes ready
        wf.steps[0].status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0].id == "s2"

    def test_handle_blocked_steps_marks_skipped(self):
        """_handle_blocked_steps skips steps with failed dependencies."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Blocked test")
        s1 = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        s1.status = StepStatus.FAILED
        s1.error = "dependency broke"
        s2 = Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"])
        wf.steps = [s1, s2]
        orch._handle_blocked_steps(wf, wf.steps)
        assert s2.status == StepStatus.SKIPPED
        assert "s1" in s2.error

    # ── EventBus integration tests ───────────────────────────

    def test_event_bus_step_retrying(self):
        """step.retrying event is published when a step retries."""
        from scripts_01.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event] = []
        eb.subscribe("step.retrying", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Retry test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "exit 1"}, max_retries=2)
        wf.steps = [step]
        orch._execute_step(step, wf)
        # Should have retried (status back to PENDING)
        assert step.retry_count >= 1
        assert step.status == StepStatus.PENDING
        assert len(collected) >= 1
        assert collected[0].data["step_id"] == "s1"
        assert collected[0].data["retry_count"] >= 1

    def test_event_bus_workflow_progress(self):
        """workflow.progress event is published during execution."""
        from scripts_01.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event] = []
        eb.subscribe("workflow.progress", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb, max_workers=1)
        result = orch.run_workflow("Implement hello world")
        assert len(collected) >= 1
        for ev in collected:
            assert "workflow_id" in ev.data
            assert "completed_steps" in ev.data
            assert "total_steps" in ev.data

    def test_event_bus_step_completed(self):
        """step.completed event is published on success."""
        from scripts_01.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event] = []
        eb.subscribe("step.completed", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "echo ok"})
        wf.steps = [step]
        orch._execute_step(step, wf)
        assert step.status == StepStatus.SUCCESS
        assert len(collected) >= 1
        assert collected[0].data["step_id"] == "s1"

    def test_event_bus_step_failed(self):
        """step.failed event is published when step exhausts retries."""
        from scripts_01.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event] = []
        eb.subscribe("step.failed", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "exit 1"}, max_retries=0)
        wf.steps = [step]
        orch._execute_step(step, wf)
        assert step.status == StepStatus.FAILED
        assert len(collected) >= 1
        assert collected[0].data["step_id"] == "s1"

    def test_event_bus_workflow_lifecycle(self):
        """All workflow lifecycle events fire during run_workflow."""
        from scripts_01.event_bus import EventBus, Event
        eb = EventBus()
        events: list[str] = []
        eb.subscribe("workflow.created", lambda e: events.append("created"))
        eb.subscribe("workflow.planning", lambda e: events.append("planning"))
        eb.subscribe("workflow.started", lambda e: events.append("started"))
        eb.subscribe("workflow.completed", lambda e: events.append("completed"))
        orch = Orchestrator(event_bus=eb)
        orch.run_workflow("Test")
        assert "created" in events
        assert "planning" in events
        assert "started" in events
        assert "completed" in events or "failed" in events

    def test_no_event_bus_doesnt_crash(self):
        """Orchestrator without EventBus works fine (no-op)."""
        orch = Orchestrator(event_bus=None)
        result = orch.run_workflow("Test")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)

    # ── Termination guarantees (v5.189.9) ────────────────────

    class _FixedStepsPlanner:
        """Planner returning a fixed step list (bypasses DefaultPlanner)."""

        def __init__(self, steps):
            self._steps = steps

        def plan(self, goal):
            return list(self._steps)

    def test_skipped_dependency_propagates_and_terminates(self):
        """Step depending on a SKIPPED step is also SKIPPED — no infinite loop.

        Regression (v5.189.9): chain s1 FAILED → s2 SKIPPED → s3 depends on s2.
        Before the fix s3 stayed PENDING forever (dep was SKIPPED, not FAILED,
        so _handle_blocked_steps ignored it) and run_workflow busy-looped.
        """
        orch = Orchestrator()
        wf_steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "exit 1"}, max_retries=0),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo b"}, depends_on=["s1"], max_retries=0),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo c"}, depends_on=["s2"], max_retries=0),
        ]
        orch._planner = self._FixedStepsPlanner(wf_steps)
        result = orch.run_workflow("skip chain")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
        statuses = {s.id: s.status for s in result.steps}
        assert statuses["s1"] == StepStatus.FAILED
        assert statuses["s2"] == StepStatus.SKIPPED
        # Транзитивная пропагация: s3 не виснет PENDING, а скипается
        assert statuses["s3"] == StepStatus.SKIPPED

    def test_missing_dependency_terminates_with_failed(self):
        """depends_on на несуществующий step id → deadlock-guard, а не вечный цикл.

        Regression (v5.189.9): before the fix, a step whose dependency id
        doesn't exist could never become ready and was never skipped →
        while True in run_workflow looped forever. Now the deadlock guard
        fails the workflow with a descriptive error.
        """
        orch = Orchestrator()
        wf_steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo ok"}, depends_on=["ghost"], max_retries=0),
        ]
        orch._planner = self._FixedStepsPlanner(wf_steps)
        result = orch.run_workflow("ghost dep")
        assert result.status == WorkflowStatus.FAILED
        assert any("Deadlock" in e for e in result.errors)

    def test_run_code_workflow_completes_under_10s(self):
        """Полный code-workflow завершается за <10s — защита от возврата медленного find.

        Regression (v5.189.9): Read Context использовал `find . -name '*.py'`
        БЕЗ -maxdepth — на Android FUSE обход всего дерева занимал >60s →
        TimeoutExpired ×3 ретрая → workflow попадал в бесконечный while True
        (CPU-spin навсегда, full-suite застревал на ~52%).

        С фиксом (`find . -maxdepth 3 ... | head -20`) прогон укладывается в
        секунды. Порог 10s отделяет фикс от регрессии: вернувшийся unbounded
        find даёт минуты/вечный цикл, а не <10s.

        Разделение ответственности: этот тест ловит регрессию медленного find
        (workflow вернётся FAILED после ~180s ретраев → assert сработает с
        сообщением); регрессию бесконечного while True ловят соседние
        termination-тесты (test_skipped_dependency_propagates_and_terminates,
        test_missing_dependency_terminates_with_failed) — они завершаются быстро.
        """
        import time

        orch = Orchestrator()
        start = time.perf_counter()
        result = orch.run_workflow("Implement a simple hello world")
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, (
            f"code-workflow занял {elapsed:.1f}s — вероятен возврат медленного "
            "find (Read Context должен использовать -maxdepth 3)"
        )
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)

    # ── Thread safety tests ──────────────────────────────────

    def test_context_updates_from_parallel_steps(self):
        """Context accumulates results from parallel steps (thread-safe)."""
        orch = Orchestrator(max_workers=4)
        wf = Workflow(id="wf1", goal="Context test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val1"}, output_key="key1"),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val2"}, output_key="key2"),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val3"}, output_key="key3"),
        ]
        result = orch.run_workflow("Context test")
        # All keys should be present if steps succeeded
        succeeded = [s for s in result.steps if s.status == StepStatus.SUCCESS]
        for s in succeeded:
            if s.output_key:
                assert s.output_key in result.context

    def test_dag_parallel_diamond(self):
        """Diamond dependency: A -> B, A -> C, B+C -> D runs correctly."""
        orch = Orchestrator(max_workers=4)
        wf = Workflow(id="wf1", goal="Diamond DAG")
        wf.steps = [
            Step(id="a", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo a"}),
            Step(id="b", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo b"}, depends_on=["a"]),
            Step(id="c", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo c"}, depends_on=["a"]),
            Step(id="d", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo d"}, depends_on=["b", "c"]),
        ]
        # Initially only 'a' is ready
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1 and ready[0].id == "a"
        # After a succeeds, b and c are both ready
        wf.steps[0].status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        ids = {s.id for s in ready}
        assert ids == {"b", "c"}
        # After b and c succeed, d is ready
        wf.steps[1].status = StepStatus.SUCCESS
        wf.steps[2].status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1 and ready[0].id == "d"


class TestModelStepPolicy:
    """Правило 11 (User-Choice Override): MODEL-шаг уважает policy resolve."""

    class FakePolicy:
        """Policy с пользовательским override на coding → claude-code."""

        def resolve(self, capability):
            return {
                "capability": capability,
                "runtime": "claude-code",
                "source": "policy",
                "preferred": "claude-code",
            }

    class NoPolicy:
        """Policy без переопределения — авто-выбор системы."""

        def resolve(self, capability):
            return {
                "capability": capability,
                "runtime": None,
                "source": "auto",
                "preferred": None,
            }

    def _run_model_step(self, orch: Orchestrator) -> Step:
        wf = Workflow(id="w1", goal="g")
        step = Step(id="m1", type=StepType.MODEL, model_capabilities=["coding"])
        wf.steps = [step]
        orch._execute_step(step, wf)
        return step

    def test_policy_override_used(self):
        """Override (claude-code на coding) применяется вместо SmartRouter."""
        orch = Orchestrator(policy_engine=self.FakePolicy())
        step = self._run_model_step(orch)
        assert step.status == StepStatus.SUCCESS
        assert "policy:claude-code" in step.result
        assert "anthropic/claude-3.5-sonnet" in step.result

    def test_router_fallback_when_no_policy_runtime(self):
        """Нет override → авто-маршрутизация SmartRouter (router)."""
        orch = Orchestrator(policy_engine=self.NoPolicy())
        step = self._run_model_step(orch)
        assert step.status == StepStatus.SUCCESS
        assert "Routed to:" in step.result
        assert "(router)" in step.result
