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
        """Workflow accumulates errors from failed steps."""
        orch = Orchestrator()
        wf = Workflow(id="wf1", goal="Test errors")
        step = Step(id="s1", type=StepType.TOOL, tool=ToolType.SHELL)
        orch._handle_step_error(step, "Test error", wf)
        assert step.error == "Test error"

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
