#!/usr/bin/env python3
"""
orchestrator.py — FSM/DAG Orchestrator для Buffy Project.

Многошаговое выполнение задач: Goal → Plan → Execute → Validate → Result.

Архитектура:
  Orchestrator
  ├── Planner     — разбивает Goal на Step[***REMOVED*** (DAG)
  ├── Executor    — выполняет Step через Tool/Agent/Model
  ├── Validator   — проверяет результат Step
  └── FSM         — управляет состояниями Workflow + Step

Жизненный цикл Workflow:
  PENDING → PLANNING → RUNNING → COMPLETED
                              ↘ FAILED
                                ↘ CANCELLED

Жизненный цикл Step:
  PENDING → READY → RUNNING → SUCCESS
                           ↘ FAILED → PENDING (retry)
                           ↘ SKIPPED

Использование:
    from scripts.orchestrator import Orchestrator

    orch = Orchestrator()
    result = orch.run_workflow("Refactor router module")
    print(result.status)  # WorkflowStatus.COMPLETED
    for step in result.steps:
        print(f"  {step.id***REMOVED***: {step.status***REMOVED*** → {step.result[:50***REMOVED******REMOVED***")

События (EventBus):
  workflow.created   — workflow создан
  workflow.planning  — начато планирование
  workflow.started   — выполнение начато
  workflow.completed — выполнение завершено успешно
  workflow.failed    — выполнение провалено
  step.started       — шаг начат
  step.completed     — шаг завершён успешно
  step.failed        — шаг провален (последняя попытка)
  step.skipped       — шаг пропущен (зависимость не выполнена)
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
***REMOVED***
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


WORKSPACE = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"           # dependencies met, waiting to run
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    TOOL = "tool"             # shell, python, git, filesystem
    AGENT = "agent"           # IAgent contract
    MODEL = "model"           # LLM call via SmartRouter
    SUBTASK = "subtask"       # nested workflow
    VALIDATE = "validate"     # pure validation step


class ToolType(str, Enum):
    SHELL = "shell"
    PYTHON = "python"
    MEMORY = "memory"         # MemoryEngine
    KNOWLEDGE = "knowledge"   # KnowledgeEngine
    FILE = "file"             # filesystem read/write
    GIT = "git"


@dataclass
class Step:
    """Один шаг в Workflow."""
    id: str
    type: StepType
    name: str = ""
    description: str = ""
    input: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    depends_on: List[str***REMOVED*** = field(default_factory=list)
    tool: Optional[ToolType***REMOVED*** = None
    agent: Optional[str***REMOVED*** = None
    model_capabilities: Optional[List[str***REMOVED******REMOVED*** = None
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str***REMOVED*** = None
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: int = 60
    output_key: str = ""      # сохранить результат в context[key***REMOVED***


@dataclass
class Workflow:
    """Полный workflow — от goal до результата."""
    id: str
    goal: str
    steps: List[Step***REMOVED*** = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    errors: List[str***REMOVED*** = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict."""
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type.value,
                    "status": s.status.value,
                    "depends_on": s.depends_on,
                    "error": s.error,
                ***REMOVED***
                for s in self.steps
            ***REMOVED***,
            "status": self.status.value,
            "errors": self.errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Tool Executors
# ═══════════════════════════════════════════════════════════════


class ToolExecutor:
    """Выполняет инструменты (shell, python, memory, etc.).

    Все методы статические — полная обратная совместимость.
    ToolRuntime интеграция выполняется на уровне Orchestrator._execute_step().
    """

    @staticmethod
    def run(tool: ToolType, input_data: Dict[str, Any***REMOVED***,
            timeout: int = 60) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        """Запускает инструмент.

        Returns:
            (success, result, error_message)
        """
        if tool == ToolType.SHELL:
            return ToolExecutor._run_shell(input_data, timeout)
        elif tool == ToolType.PYTHON:
            return ToolExecutor._run_python(input_data, timeout)
        elif tool == ToolType.MEMORY:
            return ToolExecutor._run_memory(input_data)
        elif tool == ToolType.KNOWLEDGE:
            return ToolExecutor._run_knowledge(input_data)
        elif tool == ToolType.FILE:
            return ToolExecutor._run_file(input_data)
        elif tool == ToolType.GIT:
            return ToolExecutor._run_git(input_data, timeout)
        else:
            return False, None, f"Unknown tool: {tool***REMOVED***"

    @staticmethod
    def _run_shell(data: Dict[str, Any***REMOVED***, timeout: int) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        command = data.get("command", "")
        if not command:
            return False, None, "No command specified"
        cwd = data.get("cwd", str(WORKSPACE))
        try:
            result = subprocess.run(
                ["sh", "-c", command***REMOVED***, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode***REMOVED***"
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout***REMOVED***s)"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _run_python(data: Dict[str, Any***REMOVED***, timeout: int) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        """Execute Python code in an isolated subprocess (no exec())."""
        code = data.get("code", "")
        if not code:
            return False, None, "No code specified"
        try:
            result = subprocess.run(
                [sys.executable, "-c", code***REMOVED***,
                capture_output=True, text=True,
                timeout=timeout, cwd=str(WORKSPACE),
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode***REMOVED***"
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout***REMOVED***s)"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _run_memory(data: Dict[str, Any***REMOVED***) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        from scripts.memory_engine import MemoryEngine, MemoryLevel
        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        action = data.get("action", "search")
        query = data.get("query", "")
        level = data.get("level", None)

        if action == "search":
            results = engine.search(query, level=MemoryLevel(level) if level else None)
            return True, [
                {"key": r.key, "summary": r.summary, "level": r.level.value***REMOVED***
                for r in results[:5***REMOVED***
            ***REMOVED***, None
        elif action == "get":
            entry = engine.retrieve(
                level=MemoryLevel(data.get("level")),
                key=data.get("key"),
            ) if data.get("level") and data.get("key") else None
            return True, entry.content[:500***REMOVED*** if entry else None, None
        elif action == "list":
            entries = engine.list_entries(
                level=MemoryLevel(level) if level else None
            )
            return True, [(e.key, e.level.value, len(e.content)) for e in entries***REMOVED***, None
        return False, None, f"Unknown action: {action***REMOVED***"

    @staticmethod
    def _run_knowledge(data: Dict[str, Any***REMOVED***) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=str(WORKSPACE))
        query = data.get("query", "")
        mode = data.get("mode", "hybrid")
        if not query:
            return False, None, "No query specified"
        results = ke.search(query, top_k=5, mode=mode)
        return True, [
            {"doc_id": r.doc_id, "score": r.score, "snippet": r.snippet[:200***REMOVED******REMOVED***
            for r in results
        ***REMOVED***, None

    @staticmethod
    def _run_file(data: Dict[str, Any***REMOVED***) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        action = data.get("action", "read")
        path = data.get("path", "")
        if not path:
            return False, None, "No path specified"
        full_path = WORKSPACE / path
        try:
            if action == "read":
                if not full_path.exists():
                    return False, None, f"File not found: {path***REMOVED***"
                content = full_path.read_text(encoding="utf-8")
                return True, content, None
            elif action == "write":
                content = data.get("content", "")
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                return True, f"Written {len(content)***REMOVED*** chars", None
            elif action == "list":
                if not full_path.exists():
                    return False, None, f"Directory not found: {path***REMOVED***"
                files = [str(f.relative_to(WORKSPACE)) for f in sorted(full_path.rglob("*"))***REMOVED***
                return True, files[:50***REMOVED***, None
        except Exception as e:
            return False, None, str(e)
        return False, None, f"Unknown action: {action***REMOVED***"

    @staticmethod
    def _run_git(data: Dict[str, Any***REMOVED***, timeout: int) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        command = data.get("command", "status")
        cwd = data.get("cwd", str(WORKSPACE))
        cmd_parts = ["git"***REMOVED*** + shlex.split(command)
        try:
            result = subprocess.run(
                cmd_parts, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode***REMOVED***"
        except Exception as e:
            return False, "", str(e)


# ═══════════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════════


class StepValidator:
    """Валидатор результатов шагов."""

    @staticmethod
    def validate(step: Step, context: Dict[str, Any***REMOVED***) -> Tuple[bool, Optional[str***REMOVED******REMOVED***:
        """Проверяет результат шага.

        Returns:
            (is_valid, error_message)
        """
        if step.status != StepStatus.SUCCESS:
            return False, f"Step status is {step.status.value***REMOVED***, not SUCCESS"

        # Проверка по типу шага
        validation_rules = step.input.get("validation", {***REMOVED***)

        # not_empty — результат не должен быть пустым
        if validation_rules.get("not_empty", False):
            if not step.result:
                return False, "Result is empty"

        # min_length — минимальная длина результата
        min_len = validation_rules.get("min_length", 0)
        if isinstance(step.result, str) and len(step.result) < min_len:
            return False, f"Result too short: {len(step.result)***REMOVED*** < {min_len***REMOVED***"

        # contains — результат должен содержать строку
        contains = validation_rules.get("contains", "")
        if contains and isinstance(step.result, str):
            if contains not in step.result:
                return False, f"Result doesn't contain '{contains***REMOVED***'"

        # error_free — без ошибок (уже проверено статусом)
        if step.error:
            return False, step.error

        return True, None


# ═══════════════════════════════════════════════════════════════
# Default Planner
# ═══════════════════════════════════════════════════════════════


class DefaultPlanner:
    """Планировщик по умолчанию — разбивает goal на шаги.

    Анализирует goal и создаёт шаги для типовых сценариев:
      - Код/рефакторинг → поиск знаний → shell → validate
      - Исследование → knowledge search → memory store
      - Архитектура → knowledge search → file read → validate
    """

    @staticmethod
    def plan(goal: str) -> List[Step***REMOVED***:
        """Создаёт список шагов на основе goal."""
        goal_lower = goal.lower()
        steps: List[Step***REMOVED*** = [***REMOVED***
        step_id = 0

        def _sid(prefix: str = "step") -> str:
            nonlocal step_id
            step_id += 1
            return f"{prefix***REMOVED***_{step_id***REMOVED***"

        # Всегда: поиск релевантных знаний
        steps.append(Step(
            id=_sid("knowledge"),
            type=StepType.TOOL,
            name="Search Knowledge",
            description="Search relevant knowledge for the goal",
            tool=ToolType.KNOWLEDGE,
            input={"query": goal, "mode": "hybrid"***REMOVED***,
            output_key="knowledge_results",
        ))

        # Если запрос на код/рефакторинг
        if any(w in goal_lower for w in ["refactor", "implement", "create", "code",
                                           "write", "add", "fix", "update", "change"***REMOVED***):
            steps.append(Step(
                id=_sid("read"),
                type=StepType.TOOL,
                name="Read Context",
                description="Read relevant files",
                tool=ToolType.SHELL,
                input={
                    "command": f"find . -name '*.py' | head -20",
                    "validation": {"not_empty": False***REMOVED***,
                ***REMOVED***,
                depends_on=[steps[-1***REMOVED***.id***REMOVED*** if steps else [***REMOVED***,
                output_key="file_list",
            ))
            steps.append(Step(
                id=_sid("execute"),
                type=StepType.TOOL,
                name="Execute",
                description="Execute the task",
                tool=ToolType.SHELL,
                input={
                    "command": f"echo 'TODO: implement for: {goal***REMOVED***'",
                    "validation": {"min_length": 10***REMOVED***,
                ***REMOVED***,
                depends_on=[steps[-1***REMOVED***.id***REMOVED*** if steps else [***REMOVED***,
                output_key="execution_result",
            ))

        # Если запрос на исследование/анализ
        elif any(w in goal_lower for w in ["research", "analyze", "search", "find",
                                             "explain", "what", "how", "compare"***REMOVED***):
            steps.append(Step(
                id=_sid("analyze"),
                type=StepType.TOOL,
                name="Analyze",
                description="Deep analysis",
                tool=ToolType.KNOWLEDGE,
                input={"query": goal, "mode": "semantic_ml"***REMOVED***,
                depends_on=[steps[-1***REMOVED***.id***REMOVED*** if steps else [***REMOVED***,
                output_key="analysis_results",
            ))

        # Если запрос на архитектуру/проектирование
        elif any(w in goal_lower for w in ["architecture", "design", "plan", "propose"***REMOVED***):
            steps.append(Step(
                id=_sid("memory"),
                type=StepType.TOOL,
                name="Check Memory",
                description="Check existing context in memory",
                tool=ToolType.MEMORY,
                input={"action": "search", "query": goal***REMOVED***,
                depends_on=[steps[-1***REMOVED***.id***REMOVED*** if steps else [***REMOVED***,
                output_key="memory_context",
            ))

        # Validate последнего шага
        if len(steps) > 1:
            steps.append(Step(
                id=_sid("validate"),
                type=StepType.VALIDATE,
                name="Validate Result",
                description="Validate the final result",
                input={
                    "validation": {"not_empty": True, "min_length": 10***REMOVED***,
                    "validate_step_id": steps[-1***REMOVED***.id,
                ***REMOVED***,
                depends_on=[steps[-1***REMOVED***.id***REMOVED***,
            ))

        return steps


# ═══════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════


class Orchestrator:
    """FSM/DAG Orchestrator для многошаговых задач.

    Жизненный цикл:
      run_workflow(goal)
        → workflow.status = PLANNING
        → planner.plan(goal) → steps[***REMOVED***
        → workflow.status = RUNNING
        → while steps remain:
            ready = get_ready_steps()  # DAG resolution
            for step in ready:
                execute_step(step)
                validate_step(step)
                save_to_context(step)
        → workflow.status = COMPLETED | FAILED

    Интеграция с ToolRuntime:
      - Если передан tool_registry, ToolExecutor делегирует SHELL/FILE/GIT туда
      - Если tool_registry не передан — используется старый ToolExecutor (полная совместимость)
      - EventBus проксируется в ToolRegistry для tool.executed/tool.failed событий
    """

    def __init__(
        self,
        planner: Optional[DefaultPlanner***REMOVED*** = None,
        executor: Optional[ToolExecutor***REMOVED*** = None,
        validator: Optional[StepValidator***REMOVED*** = None,
        event_bus: Optional[Any***REMOVED*** = None,  # EventBus instance
        tool_registry: Optional[Any***REMOVED*** = None,  # ToolRegistry instance
    ):
        self._planner = planner or DefaultPlanner()
        self._executor = executor or ToolExecutor()
        self._validator = validator or StepValidator()
        self._event_bus = event_bus
        self._tool_registry = tool_registry
        self._lock = threading.Lock()

    def run_workflow(self, goal: str) -> Workflow:
        """Полный цикл: Plan → Execute → Validate.

        Синхронная версия (для CLI/скриптов).
        """
        workflow = Workflow(
            id=uuid.uuid4().hex[:12***REMOVED***,
            goal=goal,
        )

        # Publish: workflow created
        self._publish_event("workflow.created", {
            "workflow_id": workflow.id,
            "goal": goal,
        ***REMOVED***)

        # Phase 1: Plan
        workflow.status = WorkflowStatus.PLANNING
        self._publish_event("workflow.planning", {
            "workflow_id": workflow.id,
            "goal": goal,
        ***REMOVED***)

        steps = self._planner.plan(goal)
        workflow.steps = steps

        if not steps:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors.append("Planner returned no steps")
            self._publish_event("workflow.failed", {
                "workflow_id": workflow.id,
                "goal": goal,
                "error": "Planner returned no steps",
            ***REMOVED***)
            return workflow

        # Phase 2: Execute (DAG execution)
        workflow.status = WorkflowStatus.RUNNING
        self._publish_event("workflow.started", {
            "workflow_id": workflow.id,
            "goal": goal,
            "step_count": len(steps),
        ***REMOVED***)
        completed = False

        while not completed:
            ready_steps = self._get_ready_steps(workflow)
            if not ready_steps:
                # Все шаги завершены или все оставшиеся заблокированы
                remaining = [s for s in steps if s.status in
                             (StepStatus.PENDING, StepStatus.READY)***REMOVED***
                if not remaining:
                    completed = True
                else:
                    # Заблокированы — смотрим ошибки в зависимостях
                    for s in remaining:
                        failed_deps = [
                            d for d in s.depends_on
                            if any(ss.id == d and ss.status == StepStatus.FAILED
                                   for ss in steps)
                        ***REMOVED***
                        if failed_deps:
                            s.status = StepStatus.SKIPPED
                            s.error = f"Dependency failed: {', '.join(failed_deps)***REMOVED***"
                            self._publish_step_event(s, workflow)
                        else:
                            s.status = StepStatus.READY
                    continue

            for step in ready_steps:
                self._execute_step(step, workflow)

            # Проверяем: все FAILED?
            all_failed = all(
                s.status in (StepStatus.FAILED, StepStatus.SKIPPED)
                for s in steps if s.status != StepStatus.SUCCESS
            )
            if all_failed and not ready_steps:
                workflow.status = WorkflowStatus.FAILED
                break

        if workflow.status != WorkflowStatus.FAILED:
            workflow.status = WorkflowStatus.COMPLETED

        # Publish: workflow result
        status_key = "workflow.completed" if workflow.status == WorkflowStatus.COMPLETED else "workflow.failed"
        self._publish_event(status_key, {
            "workflow_id": workflow.id,
            "goal": goal,
            "status": workflow.status.value,
            "step_count": len(workflow.steps),
            "error_count": len(workflow.errors),
        ***REMOVED***)

        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        return workflow

    def _get_ready_steps(self, workflow: Workflow) -> List[Step***REMOVED***:
        """Находит шаги, готовые к выполнению (DAG resolution)."""
        ready: List[Step***REMOVED*** = [***REMOVED***
        for step in workflow.steps:
            if step.status != StepStatus.PENDING:
                continue

            # Проверяем зависимости
            deps_met = all(
                any(s.id == dep and s.status == StepStatus.SUCCESS
                    for s in workflow.steps)
                for dep in step.depends_on
            )
            if deps_met:
                step.status = StepStatus.READY
                ready.append(step)

        return ready

    def _publish_event(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие через EventBus, если он подключён."""
        if self._event_bus is not None:
            from scripts.event_bus import Event
            self._event_bus.publish(Event(
                type=event_type,
                data=data,
                source="orchestrator",
            ))

    def _publish_step_event(self, step: Step, workflow: Workflow) -> None:
        """Публикует событие о статусе шага."""
        status = step.status
        if status == StepStatus.SUCCESS:
            self._publish_event("step.completed", {
                "step_id": step.id,
                "workflow_id": workflow.id,
                "step_name": step.name or step.id,
            ***REMOVED***)
        elif status == StepStatus.FAILED:
            self._publish_event("step.failed", {
                "step_id": step.id,
                "workflow_id": workflow.id,
                "step_name": step.name or step.id,
                "error": step.error,
            ***REMOVED***)
        elif status == StepStatus.SKIPPED:
            self._publish_event("step.skipped", {
                "step_id": step.id,
                "workflow_id": workflow.id,
                "step_name": step.name or step.id,
                "error": step.error,
            ***REMOVED***)

    def _execute_step(self, step: Step, workflow: Workflow) -> None:
        """Выполняет один шаг."""
        step.status = StepStatus.RUNNING

        # Publish: step started
        self._publish_event("step.started", {
            "step_id": step.id,
            "workflow_id": workflow.id,
            "step_name": step.name or step.id,
            "step_type": step.type.value,
            "tool": step.tool.value if step.tool else None,
        ***REMOVED***)

        if step.type == StepType.TOOL:
            # ToolRuntime delegation (если подключён)
            if self._tool_registry is not None and step.tool in (
                ToolType.SHELL, ToolType.FILE, ToolType.GIT
            ):
                success, result, error = self._run_via_tool_registry(step)
            else:
                success, result, error = self._executor.run(
                    step.tool, step.input, step.timeout_seconds
                )
            if success:
                step.status = StepStatus.SUCCESS
                step.result = result
            else:
                self._handle_step_error(step, error or "Tool execution failed", workflow)

        elif step.type == StepType.VALIDATE:
            # Находим целевой шаг для валидации
            target_id = step.input.get("validate_step_id", "")
            target = next((s for s in workflow.steps if s.id == target_id), None)
            if target:
                is_valid, error = self._validator.validate(target, workflow.context)
                if is_valid:
                    step.status = StepStatus.SUCCESS
                    step.result = "Validation passed"
                else:
                    step.status = StepStatus.FAILED
                    step.error = error
                    workflow.errors.append(f"Validation failed for {target_id***REMOVED***: {error***REMOVED***")
            else:
                step.status = StepStatus.FAILED
                step.error = f"Target step not found: {target_id***REMOVED***"

        elif step.type == StepType.MODEL:
            # Через SmartRouter
            try:
                from core.router import SmartRouter, ModelCatalog
                router = SmartRouter(ModelCatalog.default())
                caps = step.model_capabilities or ["code"***REMOVED***
                decision = router.route(
                    required_capabilities=caps,
                    max_tokens_needed=step.input.get("max_tokens", 2000),
                )
                step.result = f"Routed to: {decision.model_id***REMOVED***"
                step.status = StepStatus.SUCCESS
            except Exception as e:
                self._handle_step_error(step, str(e), workflow)

        else:
            step.status = StepStatus.FAILED
            step.error = f"Unsupported step type: {step.type***REMOVED***"

        # Publish step event after execution
        self._publish_step_event(step, workflow)

        # Сохраняем результат в контекст
        if step.status == StepStatus.SUCCESS and step.output_key:
            workflow.context[step.output_key***REMOVED*** = step.result

    def _run_via_tool_registry(self, step: Step) -> Tuple[bool, Any, Optional[str***REMOVED******REMOVED***:
        """Делегирует выполнение шага в ToolRegistry."""
        try:
            tool_name = step.tool.value if step.tool else ""
            params = {***REMOVED***
            if step.tool == ToolType.SHELL:
                params = {
                    "command": step.input.get("command", ""),
                    "cwd": step.input.get("cwd", str(WORKSPACE)),
                    "timeout": step.timeout_seconds,
                ***REMOVED***
            elif step.tool == ToolType.FILE:
                params = {
                    "action": step.input.get("action", "read"),
                    "path": step.input.get("path", ""),
                    "content": step.input.get("content", ""),
                ***REMOVED***
            elif step.tool == ToolType.GIT:
                params = {
                    "command": step.input.get("command", "status"),
                    "args": step.input.get("args", ""),
                    "cwd": step.input.get("cwd", str(WORKSPACE)),
                    "timeout": step.timeout_seconds,
                ***REMOVED***
            result = self._tool_registry.execute(tool_name, params)
            return result.success, result.data, result.error
        except Exception as e:
            return False, None, f"ToolRuntime error: {e***REMOVED***"

    def _handle_step_error(self, step: Step, error: str, workflow: Workflow) -> None:
        """Обрабатывает ошибку шага с ретраем."""
        step.error = error
        if step.retry_count < step.max_retries:
            step.retry_count += 1
            step.status = StepStatus.PENDING
        else:
            step.status = StepStatus.FAILED
            workflow.errors.append(f"Step {step.id***REMOVED*** failed after {step.max_retries***REMOVED*** retries: {error***REMOVED***")

    def save_workflow(self, workflow: Workflow) -> None:
        """Сохраняет workflow в Memory Engine."""
        from scripts.memory_engine import MemoryEngine, MemoryLevel, ContentType

        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        engine.store(
            level=MemoryLevel.WORKING,
            key=f"workflow_{workflow.id***REMOVED***",
            content=json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2),
            content_type=ContentType.JSON,
            summary=f"Workflow: {workflow.goal[:80***REMOVED******REMOVED***",
            metadata={
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "step_count": len(workflow.steps),
            ***REMOVED***,
        )

    def list_workflows(self, limit: int = 10) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список сохранённых workflows."""
        from scripts.memory_engine import MemoryEngine, MemoryLevel

        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        entries = engine.list_entries(level=MemoryLevel.WORKING)
        workflows = [***REMOVED***
        for e in entries:
            if e.key.startswith("workflow_"):
                try:
                    data = json.loads(e.content)
                    workflows.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue
        workflows.sort(key=lambda w: w.get("created_at", ""), reverse=True)
        return workflows[:limit***REMOVED***


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Orchestrator — многошаговые задачи Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/orchestrator.py run "Рефакторинг модуля роутинга"
  python scripts/orchestrator.py run "Найди документацию по Memory Engine" --steps 3
  python scripts/orchestrator.py list
  python scripts/orchestrator.py get <workflow_id>
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="Запустить workflow")
    p_run.add_argument("goal", help="Цель/задача")
    p_run.add_argument("--steps", type=int, default=0, help="Макс. шагов (0 = все)")

    # list
    sub.add_parser("list", help="Список workflow")

    # get
    p_get = sub.add_parser("get", help="Детали workflow")
    p_get.add_argument("workflow_id", help="ID workflow")

    args = parser.parse_args()
    orch = Orchestrator()

    if args.command == "run":
        print(f"🚀 Starting workflow: {args.goal***REMOVED***")
        print()
        result = orch.run_workflow(args.goal)
        print(f"📊 Status: {result.status.value***REMOVED***")
        print(f"   Steps: {len(result.steps)***REMOVED***")
        print(f"   Errors: {len(result.errors)***REMOVED***")
        print()
        for i, step in enumerate(result.steps, 1):
            icon = {
                StepStatus.SUCCESS: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.RUNNING: "🔄",
                StepStatus.PENDING: "⏳",
                StepStatus.READY: "📋",
                StepStatus.SKIPPED: "⏭️",
            ***REMOVED***.get(step.status, "❓")
            print(f"  {icon***REMOVED*** {i***REMOVED***. {step.name or step.id***REMOVED***")
            if step.error:
                print(f"     Error: {step.error[:100***REMOVED******REMOVED***")
            if step.result:
                result_str = str(step.result)[:100***REMOVED***
                print(f"     Result: {result_str***REMOVED***...")
        print()
        if result.status == WorkflowStatus.COMPLETED:
            print("✅ Workflow completed successfully!")
        else:
            print(f"❌ Workflow failed: {', '.join(result.errors[:3***REMOVED***)***REMOVED***")

        # Save
        orch.save_workflow(result)

    elif args.command == "list":
        workflows = orch.list_workflows()
        if not workflows:
            print("📭 No workflows")
            return
        print(f"📋 Workflows ({len(workflows)***REMOVED***):")
        for w in workflows:
            icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
            ***REMOVED***.get(w.get("status", ""), "❓")
            print(f"  {icon***REMOVED*** {w['id'***REMOVED******REMOVED*** | {w['goal'***REMOVED***[:60***REMOVED******REMOVED*** | {w['status'***REMOVED******REMOVED*** | {len(w['steps'***REMOVED***)***REMOVED*** steps")

    elif args.command == "get":
        workflows = orch.list_workflows(limit=100)
        found = [w for w in workflows if w["id"***REMOVED***.startswith(args.workflow_id)***REMOVED***
        if not found:
            print(f"❌ Workflow not found: {args.workflow_id***REMOVED***")
            return
        w = found[0***REMOVED***
        print(f"📋 Workflow: {w['id'***REMOVED******REMOVED***")
        print(f"   Goal:   {w['goal'***REMOVED******REMOVED***")
        print(f"   Status: {w['status'***REMOVED******REMOVED***")
        print(f"   Steps:  {len(w['steps'***REMOVED***)***REMOVED***")
        print(f"   Errors: {len(w.get('errors', [***REMOVED***))***REMOVED***")
        print()
        for s in w["steps"***REMOVED***:
            print(f"  [{s['status'***REMOVED******REMOVED******REMOVED*** {s['name'***REMOVED******REMOVED*** ({s['type'***REMOVED******REMOVED***)")
            if s.get("error"):
                print(f"    Error: {s['error'***REMOVED***[:80***REMOVED******REMOVED***")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
