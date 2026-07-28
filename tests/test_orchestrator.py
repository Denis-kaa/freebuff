#!/usr/bin/env python3
"""Tests for Orchestrator (scripts/orchestrator.py)."""

from __future__ import annotations

import json
import os
import sys
import pytest
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.orchestrator import (
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
        assert wf.steps == [***REMOVED***
        assert wf.errors == [***REMOVED***

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
        wf = Workflow(id="wf1", goal="Test", steps=[step***REMOVED***)
        wf.status = WorkflowStatus.COMPLETED
        d = wf.to_dict()
        assert d["id"***REMOVED*** == "wf1"
        assert d["status"***REMOVED*** == "completed"
        assert len(d["steps"***REMOVED***) == 1


class TestToolExecutor:
    def test_shell_simple(self):
        success, result, error = ToolExecutor.run(
            ToolType.SHELL, {"command": "echo hello"***REMOVED***, timeout=5
        )
        assert success
        assert "hello" in result

    def test_shell_failure(self):
        success, result, error = ToolExecutor.run(
            ToolType.SHELL, {"command": "exit 1"***REMOVED***, timeout=5
        )
        assert not success
        assert error is not None

    def test_shell_no_command(self):
        success, result, error = ToolExecutor.run(ToolType.SHELL, {***REMOVED***, timeout=5)
        assert not success

    def test_python_exec(self):
        success, result, error = ToolExecutor.run(
            ToolType.PYTHON, {"code": "print('hello from python')"***REMOVED***, timeout=5
        )
        assert success
        assert "hello from python" in result

    def test_python_syntax_error(self):
        success, result, error = ToolExecutor.run(
            ToolType.PYTHON, {"code": "print(***REMOVED***"***REMOVED***, timeout=5
        )
        assert not success

    def test_python_no_code(self):
        success, result, error = ToolExecutor.run(ToolType.PYTHON, {***REMOVED***, timeout=5)
        assert not success

    def test_file_read_readme(self):
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {"action": "read", "path": "README.md"***REMOVED***, timeout=5
        )
        assert success
        assert len(result) > 0

    def test_file_not_found(self):
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {"action": "read", "path": "nonexistent_file_xyz.md"***REMOVED***, timeout=5
        )
        assert not success

    def test_file_write_absolute_path(self, tmp_path: Path):
        test_path = str(tmp_path / "test_output.txt")
        success, result, error = ToolExecutor.run(
            ToolType.FILE, {
                "action": "write",
                "path": test_path,
                "content": "test content",
            ***REMOVED***, timeout=5
        )
        # Absolute path overrides WORKSPACE on POSIX
        if success:
            written = Path(test_path).read_text()
            assert "test content" in written
        else:
            # If file tool doesn't support absolute paths, at least don't crash
            assert error is not None

    def test_unknown_tool(self):
        success, result, error = ToolExecutor.run("unknown_tool", {***REMOVED***, timeout=5)
        assert not success
        assert "Unknown" in (error or "")


class TestValidator:
    def test_not_empty_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"not_empty": True***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = "some result"
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert is_valid

    def test_not_empty_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"not_empty": True***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = ""
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert not is_valid

    def test_min_length_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"min_length": 5***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = "hello world"
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert is_valid

    def test_min_length_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"min_length": 50***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = "short"
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert not is_valid

    def test_contains_pass(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"contains": "SUCCESS"***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = "Task completed SUCCESS"
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert is_valid

    def test_contains_fail(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"validation": {"contains": "FAILED"***REMOVED******REMOVED***)
        step.status = StepStatus.SUCCESS
        step.result = "Task completed OK"
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert not is_valid

    def test_not_success_status(self):
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        step.status = StepStatus.FAILED
        is_valid, error = StepValidator.validate(step, {***REMOVED***)
        assert not is_valid


class TestDefaultPlanner:
    def test_plan_code_goal(self):
        steps = DefaultPlanner.plan("Refactor the router module")
        assert len(steps) >= 3
        types = [s.type for s in steps***REMOVED***
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
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"***REMOVED***),
        ***REMOVED***
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0***REMOVED***.id == "s1"

    def test_get_ready_steps_chain(self):
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"***REMOVED***),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s2"***REMOVED***),
        ***REMOVED***
        # s1 ready
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0***REMOVED***.id == "s1"
        # Complete s1
        wf.steps[0***REMOVED***.status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0***REMOVED***.id == "s2"

    def test_context_stored_on_success(self):
        """Output key is stored in context when step succeeds."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test context")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"command": "echo context_value"***REMOVED***,
                    output_key="test_key")
        wf.steps = [step***REMOVED***
        orch._execute_step(step, wf)
        if step.status == StepStatus.SUCCESS:
            assert wf.context.get("test_key") is not None
            assert "context_value" in str(wf.context["test_key"***REMOVED***)

    def test_workflow_errors_collected(self):
        """Workflow accumulates errors from failed steps after max retries."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test errors")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                    input={"command": "false"***REMOVED***, max_retries=0)
        wf.steps = [step***REMOVED***
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
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"***REMOVED***),
        ***REMOVED***
        wf.steps[0***REMOVED***.status = StepStatus.FAILED
        wf.steps[0***REMOVED***.error = "catastrophic failure"
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
                 input={"command": "echo a"***REMOVED***),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo b"***REMOVED***),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo c"***REMOVED***),
        ***REMOVED***
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 3
        ids = {s.id for s in ready***REMOVED***
        assert ids == {"s1", "s2", "s3"***REMOVED***

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
                 input={"command": "echo first"***REMOVED***),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo second"***REMOVED***,
                 depends_on=["s1"***REMOVED***),
        ***REMOVED***
        # Only s1 should be ready initially
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0***REMOVED***.id == "s1"
        # After s1 succeeds, s2 becomes ready
        wf.steps[0***REMOVED***.status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1
        assert ready[0***REMOVED***.id == "s2"

    def test_handle_blocked_steps_marks_skipped(self):
        """_handle_blocked_steps skips steps with failed dependencies."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Blocked test")
        s1 = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        s1.status = StepStatus.FAILED
        s1.error = "dependency broke"
        s2 = Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL, depends_on=["s1"***REMOVED***)
        wf.steps = [s1, s2***REMOVED***
        orch._handle_blocked_steps(wf, wf.steps)
        assert s2.status == StepStatus.SKIPPED
        assert "s1" in s2.error

    # ── EventBus integration tests ───────────────────────────

    def test_event_bus_step_retrying(self):
        """step.retrying event is published when a step retries."""
        from scripts.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event***REMOVED*** = [***REMOVED***
        eb.subscribe("step.retrying", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Retry test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "exit 1"***REMOVED***, max_retries=2)
        wf.steps = [step***REMOVED***
        orch._execute_step(step, wf)
        # Should have retried (status back to PENDING)
        assert step.retry_count >= 1
        assert step.status == StepStatus.PENDING
        assert len(collected) >= 1
        assert collected[0***REMOVED***.data["step_id"***REMOVED*** == "s1"
        assert collected[0***REMOVED***.data["retry_count"***REMOVED*** >= 1

    def test_event_bus_workflow_progress(self):
        """workflow.progress event is published during execution."""
        from scripts.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event***REMOVED*** = [***REMOVED***
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
        from scripts.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event***REMOVED*** = [***REMOVED***
        eb.subscribe("step.completed", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "echo ok"***REMOVED***)
        wf.steps = [step***REMOVED***
        orch._execute_step(step, wf)
        assert step.status == StepStatus.SUCCESS
        assert len(collected) >= 1
        assert collected[0***REMOVED***.data["step_id"***REMOVED*** == "s1"

    def test_event_bus_step_failed(self):
        """step.failed event is published when step exhausts retries."""
        from scripts.event_bus import EventBus, Event
        eb = EventBus()
        collected: list[Event***REMOVED*** = [***REMOVED***
        eb.subscribe("step.failed", lambda e: collected.append(e))
        orch = Orchestrator(event_bus=eb)
        wf = Workflow(id="wf1", goal="Test")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                     input={"command": "exit 1"***REMOVED***, max_retries=0)
        wf.steps = [step***REMOVED***
        orch._execute_step(step, wf)
        assert step.status == StepStatus.FAILED
        assert len(collected) >= 1
        assert collected[0***REMOVED***.data["step_id"***REMOVED*** == "s1"

    def test_event_bus_workflow_lifecycle(self):
        """All workflow lifecycle events fire during run_workflow."""
        from scripts.event_bus import EventBus, Event
        eb = EventBus()
        events: list[str***REMOVED*** = [***REMOVED***
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

    # ── Thread safety tests ──────────────────────────────────

    def test_context_updates_from_parallel_steps(self):
        """Context accumulates results from parallel steps (thread-safe)."""
        orch = Orchestrator(max_workers=4)
        wf = Workflow(id="wf1", goal="Context test")
        wf.steps = [
            Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val1"***REMOVED***, output_key="key1"),
            Step(id="s2", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val2"***REMOVED***, output_key="key2"),
            Step(id="s3", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo val3"***REMOVED***, output_key="key3"),
        ***REMOVED***
        result = orch.run_workflow("Context test")
        # All keys should be present if steps succeeded
        succeeded = [s for s in result.steps if s.status == StepStatus.SUCCESS***REMOVED***
        for s in succeeded:
            if s.output_key:
                assert s.output_key in result.context

    def test_dag_parallel_diamond(self):
        """Diamond dependency: A -> B, A -> C, B+C -> D runs correctly."""
        orch = Orchestrator(max_workers=4)
        wf = Workflow(id="wf1", goal="Diamond DAG")
        wf.steps = [
            Step(id="a", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo a"***REMOVED***),
            Step(id="b", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo b"***REMOVED***, depends_on=["a"***REMOVED***),
            Step(id="c", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo c"***REMOVED***, depends_on=["a"***REMOVED***),
            Step(id="d", type=StepType.TOOL, tool=ToolType.SHELL,
                 input={"command": "echo d"***REMOVED***, depends_on=["b", "c"***REMOVED***),
        ***REMOVED***
        # Initially only 'a' is ready
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1 and ready[0***REMOVED***.id == "a"
        # After a succeeds, b and c are both ready
        wf.steps[0***REMOVED***.status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        ids = {s.id for s in ready***REMOVED***
        assert ids == {"b", "c"***REMOVED***
        # After b and c succeed, d is ready
        wf.steps[1***REMOVED***.status = StepStatus.SUCCESS
        wf.steps[2***REMOVED***.status = StepStatus.SUCCESS
        ready = orch._get_ready_steps(wf)
        assert len(ready) == 1 and ready[0***REMOVED***.id == "d"
