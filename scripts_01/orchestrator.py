#!/usr/bin/env python3
"""
orchestrator.py — FSM/DAG Orchestrator для Buffy Project.

Многошаговое выполнение задач: Goal → Plan → Execute → Validate → Result.

Архитектура:
  Orchestrator
  ├── Planner     — разбивает Goal на Step[] (DAG)
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
    from scripts_01.orchestrator import Orchestrator

    orch = Orchestrator()
    result = orch.run_workflow("Refactor router module")
    print(result.status)  # WorkflowStatus.COMPLETED
    for step in result.steps:
        print(f"  {step.id}: {step.status} → {step.result[:50]}")

События (EventBus):
  workflow.created   — workflow создан
  workflow.planning  — начато планирование
  workflow.started   — выполнение начато (step_count)
  workflow.progress  — прогресс (completed_steps / total_steps)
  workflow.completed — выполнение завершено успешно
  workflow.failed    — выполнение провалено
  step.started       — шаг начат
  step.completed     — шаг завершён успешно
  step.failed        — шаг провален (последняя попытка)
  step.retrying      — повторная попытка (retry_count / max_retries)
  step.skipped       — шаг пропущен (зависимость не выполнена)
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shlex
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
}
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
    input: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    tool: Optional[ToolType] = None
    agent: Optional[str] = None
    model_capabilities: Optional[List[str]] = None
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: int = 60
    output_key: str = ""      # сохранить результат в context[key]


@dataclass
class Workflow:
    """Полный workflow — от goal до результата."""
    id: str
    goal: str
    steps: List[Step] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "errors": self.errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════
# Tool Executors
# ═══════════════════════════════════════════════════════════════


class ToolExecutor:
    """Выполняет инструменты (shell, python, memory, etc.).

    Все методы статические — полная обратная совместимость.
    ToolRuntime интеграция выполняется на уровне Orchestrator._execute_step().
    """

    @staticmethod
    def run(tool: ToolType, input_data: Dict[str, Any],
            timeout: int = 60) -> Tuple[bool, Any, Optional[str]]:
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
            return False, None, f"Unknown tool: {tool}"

    @staticmethod
    def _run_shell(data: Dict[str, Any], timeout: int) -> Tuple[bool, Any, Optional[str]]:
        command = data.get("command", "")
        if not command:
            return False, None, "No command specified"
        cwd = data.get("cwd", str(WORKSPACE))
        try:
            result = subprocess.run(
                ["sh", "-c", command], capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout}s)"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _run_python(data: Dict[str, Any], timeout: int) -> Tuple[bool, Any, Optional[str]]:
        """Execute Python code in an isolated subprocess (no exec())."""
        code = data.get("code", "")
        if not code:
            return False, None, "No code specified"
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True,
                timeout=timeout, cwd=str(WORKSPACE),
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout}s)"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _run_memory(data: Dict[str, Any]) -> Tuple[bool, Any, Optional[str]]:
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel
        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        action = data.get("action", "search")
        query = data.get("query", "")
        level = data.get("level", None)

        if action == "search":
            results = engine.search(query, level=MemoryLevel(level) if level else None)
            return True, [
                {"key": r.key, "summary": r.summary, "level": r.level.value}
                for r in results[:5]
            ], None
        elif action == "get":
            entry = engine.retrieve(
                level=MemoryLevel(data.get("level")),
                key=data.get("key"),
            ) if data.get("level") and data.get("key") else None
            return True, entry.content[:500] if entry else None, None
        elif action == "list":
            entries = engine.list_entries(
                level=MemoryLevel(level) if level else None
            )
            return True, [(e.key, e.level.value, len(e.content)) for e in entries], None
        return False, None, f"Unknown action: {action}"

    @staticmethod
    def _run_knowledge(data: Dict[str, Any]) -> Tuple[bool, Any, Optional[str]]:
        from scripts_01.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=str(WORKSPACE))
        query = data.get("query", "")
        mode = data.get("mode", "hybrid")
        if not query:
            return False, None, "No query specified"
        results = ke.search(query, top_k=5, mode=mode)
        return True, [
            {"doc_id": r.doc_id, "score": r.score, "snippet": r.snippet[:200]}
            for r in results
        ], None

    @staticmethod
    def _run_file(data: Dict[str, Any]) -> Tuple[bool, Any, Optional[str]]:
        action = data.get("action", "read")
        path = data.get("path", "")
        if not path:
            return False, None, "No path specified"
        full_path = WORKSPACE / path
        try:
            if action == "read":
                if not full_path.exists():
                    return False, None, f"File not found: {path}"
                content = full_path.read_text(encoding="utf-8")
                return True, content, None
            elif action == "write":
                content = data.get("content", "")
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                return True, f"Written {len(content)} chars", None
            elif action == "list":
                if not full_path.exists():
                    return False, None, f"Directory not found: {path}"
                files = [str(f.relative_to(WORKSPACE)) for f in sorted(full_path.rglob("*"))]
                return True, files[:50], None
        except Exception as e:
            return False, None, str(e)
        return False, None, f"Unknown action: {action}"

    @staticmethod
    def _run_git(data: Dict[str, Any], timeout: int) -> Tuple[bool, Any, Optional[str]]:
        command = data.get("command", "status")
        cwd = data.get("cwd", str(WORKSPACE))
        cmd_parts = ["git"] + shlex.split(command)
        try:
            result = subprocess.run(
                cmd_parts, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output, None if success else f"Exit code: {result.returncode}"
        except Exception as e:
            return False, "", str(e)


# ═══════════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════════


class StepValidator:
    """Валидатор результатов шагов."""

    @staticmethod
    def validate(step: Step, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Проверяет результат шага.

        Returns:
            (is_valid, error_message)
        """
        if step.status != StepStatus.SUCCESS:
            return False, f"Step status is {step.status.value}, not SUCCESS"

        # Проверка по типу шага
        validation_rules = step.input.get("validation", {})

        # not_empty — результат не должен быть пустым
        if validation_rules.get("not_empty", False):
            if not step.result:
                return False, "Result is empty"

        # min_length — минимальная длина результата
        min_len = validation_rules.get("min_length", 0)
        if isinstance(step.result, str) and len(step.result) < min_len:
            return False, f"Result too short: {len(step.result)} < {min_len}"

        # contains — результат должен содержать строку
        contains = validation_rules.get("contains", "")
        if contains and isinstance(step.result, str):
            if contains not in step.result:
                return False, f"Result doesn't contain '{contains}'"

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
    def plan(goal: str) -> List[Step]:
        """Создаёт список шагов на основе goal."""
        goal_lower = goal.lower()
        steps: List[Step] = []
        step_id = 0

        def _sid(prefix: str = "step") -> str:
            nonlocal step_id
            step_id += 1
            return f"{prefix}_{step_id}"

        # Всегда: поиск релевантных знаний
        steps.append(Step(
            id=_sid("knowledge"),
            type=StepType.TOOL,
            name="Search Knowledge",
            description="Search relevant knowledge for the goal",
            tool=ToolType.KNOWLEDGE,
            input={"query": goal, "mode": "hybrid"},
            output_key="knowledge_results",
        ))

        # Если запрос на код/рефакторинг
        if any(w in goal_lower for w in ["refactor", "implement", "create", "code",
                                           "write", "add", "fix", "update", "change"]):
            steps.append(Step(
                id=_sid("read"),
                type=StepType.TOOL,
                name="Read Context",
                description="Read relevant files",
                tool=ToolType.SHELL,
                input={
                    # v5.189.9: -maxdepth 3 ограничивает обход — полное древо
                    # на Android FUSE (sdcard) занимает >60s → TimeoutExpired ×3 retries.
                    "command": "find . -maxdepth 3 -name '*.py' | head -20",
                    "validation": {"not_empty": False},
                },
                depends_on=[steps[-1].id] if steps else [],
                output_key="file_list",
            ))
            steps.append(Step(
                id=_sid("execute"),
                type=StepType.TOOL,
                name="Execute",
                description="Execute the task",
                tool=ToolType.SHELL,
                input={
                    "command": f"echo 'TODO: implement for: {goal}'",
                    "validation": {"min_length": 10},
                },
                depends_on=[steps[-1].id] if steps else [],
                output_key="execution_result",
            ))

        # Если запрос на исследование/анализ
        elif any(w in goal_lower for w in ["research", "analyze", "search", "find",
                                             "explain", "what", "how", "compare"]):
            steps.append(Step(
                id=_sid("analyze"),
                type=StepType.TOOL,
                name="Analyze",
                description="Deep analysis",
                tool=ToolType.KNOWLEDGE,
                input={"query": goal, "mode": "semantic_ml"},
                depends_on=[steps[-1].id] if steps else [],
                output_key="analysis_results",
            ))

        # Если запрос на архитектуру/проектирование
        elif any(w in goal_lower for w in ["architecture", "design", "plan", "propose"]):
            steps.append(Step(
                id=_sid("memory"),
                type=StepType.TOOL,
                name="Check Memory",
                description="Check existing context in memory",
                tool=ToolType.MEMORY,
                input={"action": "search", "query": goal},
                depends_on=[steps[-1].id] if steps else [],
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
                    "validation": {"not_empty": True, "min_length": 10},
                    "validate_step_id": steps[-1].id,
                },
                depends_on=[steps[-1].id],
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
        → planner.plan(goal) → steps[]
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
        planner: Optional[DefaultPlanner] = None,
        executor: Optional[ToolExecutor] = None,
        validator: Optional[StepValidator] = None,
        event_bus: Optional[Any] = None,  # EventBus instance
        tool_registry: Optional[Any] = None,  # ToolRegistry instance
        policy_engine: Optional[Any] = None,  # PolicyEngine (правило 11) — опционально
        max_workers: int = 4,  # max parallel steps (1 = sequential)
    ):
        self._planner = planner or DefaultPlanner()
        self._executor = executor or ToolExecutor()
        self._validator = validator or StepValidator()
        self._event_bus = event_bus
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self.max_workers = max_workers
        self._lock = threading.Lock()

    def _get_policy_engine(self) -> Optional[Any]:
        """Ленивый PolicyEngine (правило 11 User-Choice Override), graceful degradation.

        Возвращает None, если policy-движок недоступен — workflow не блокируется,
        и маршрутизация MODEL-шагов выполняется через SmartRouter.
        """
        if self._policy_engine is None:
            try:
                from freebuff_plugin_03.policy import PolicyEngine
                from freebuff_plugin_03.runtime.registry import (
                    RuntimeCapabilityRegistry,
                    RuntimeRegistry,
                )
                registry = RuntimeRegistry(
                    storage_path=WORKSPACE / "data_13" / "runtime_registry.json"
                )
                registry.load()
                self._policy_engine = PolicyEngine(registry, RuntimeCapabilityRegistry(registry))
            except Exception:
                self._policy_engine = False  # sentinel: не повторяем инициализацию
        return self._policy_engine if self._policy_engine else None

    def run_workflow(self, goal: str) -> Workflow:
        """Полный цикл: Plan → Execute → Validate.

        Синхронная версия (для CLI/скриптов).
        """
        workflow = Workflow(
            id=uuid.uuid4().hex[:12],
            goal=goal,
        )

        # Publish: workflow created
        self._publish_event("workflow.created", {
            "workflow_id": workflow.id,
            "goal": goal,
        ])

        # Правило 8 (Context-Aware Routing): перед созданием задачи проверяем
        # Knowledge/Graph на существующие похожие работы — не создаём дубли.
        # Результат сохраняется в workflow.metadata и публикуется событием.
        context_matches = self.check_existing_context(goal)
        workflow.metadata["context_matches"] = context_matches
        self._publish_event("workflow.context_check", {
            "workflow_id": workflow.id,
            "goal": goal,
            "matches": len(context_matches),
        ])

        # Phase 1: Plan
        workflow.status = WorkflowStatus.PLANNING
        self._publish_event("workflow.planning", {
            "workflow_id": workflow.id,
            "goal": goal,
        ])

        steps = self._planner.plan(goal)
        workflow.steps = steps

        if not steps:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors.append("Planner returned no steps")
            self._publish_event("workflow.failed", {
                "workflow_id": workflow.id,
                "goal": goal,
                "error": "Planner returned no steps",
            ])
            return workflow

        # Phase 2: Execute (parallel DAG execution)
        workflow.status = WorkflowStatus.RUNNING
        self._publish_event("workflow.started", {
            "workflow_id": workflow.id,
            "goal": goal,
            "step_count": len(steps),
        ])

        active_futures: Dict[concurrent.futures.Future, Step] = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as pool:
            while True:
                # Get steps whose dependencies are met
                with self._lock:
                    ready_steps = self._get_ready_steps(workflow)

                # Submit ready steps to thread pool
                for step in ready_steps:
                    future = pool.submit(self._execute_step, step, workflow)
                    active_futures[future] = step

                if not active_futures:
                    # No active work — check if we're done or blocked
                    with self._lock:
                        remaining = [
                            s for s in steps
                            if s.status in (StepStatus.PENDING, StepStatus.READY)
                        ]
                    if not remaining:
                        break  # All done
                    # Blocked steps — skip those with failed/skipped deps
                    skipped_now = self._handle_blocked_steps(workflow, steps)
                    if not skipped_now:
                        # v5.189.9 deadlock guard: нет активной работы, скипать нечего,
                        # а шаги остались (несуществующий dep / цикл в DAG) → иначе
                        # while True крутился бы вечно. Терминируем: оставшиеся шаги
                        # получают терминальный SKIPPED (чистое финальное состояние),
                        # workflow — FAILED с описательной ошибкой.
                        with self._lock:
                            deadlocked: List[Step] = []
                            for s in remaining:
                                if s.status in (
                                    StepStatus.PENDING, StepStatus.READY,
                                ):
                                    s.status = StepStatus.SKIPPED
                                    s.error = (
                                        "Deadlock: dependencies can never "
                                        "be satisfied"
                                    )
                                    deadlocked.append(s)
                        # Обсервабилити: те же step.skipped события, что и в
                        # _handle_blocked_steps (публикация вне лока).
                        for s in deadlocked:
                            self._publish_step_event(s, workflow)
                        workflow.status = WorkflowStatus.FAILED
                        workflow.errors.append(
                            "Deadlock: steps can never become ready "
                            f"({', '.join(s.id for s in remaining)})"
                        )
                        break
                    continue

                # Wait for at least one step to finish
                done, _ = concurrent.futures.wait(
                    active_futures.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                for future in done:
                    try:
                        future.result()  # re-raise thread exceptions
                    except Exception:
                        pass  # errors already handled in _execute_step
                    del active_futures[future]

                # Publish progress
                self._publish_workflow_progress(workflow)

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
        ])

        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        return workflow

    def check_existing_context(
        self, goal: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Правило 8: Context-Aware Routing — поиск существующего контекста.

        Перед созданием задачи проверяет Knowledge Engine (FTS + TF-IDF + graph)
        на похожие работы, чтобы не создавать дубли. Возвращает список совпадений
        (doc_id, score, title, snippet). Не блокирует выполнение: при
        недоступности индекса или ошибке возвращает пустой список.

        Args:
            goal: цель/задача workflow
            top_k: количество результатов

        Returns:
            Список dict-совпадений из Knowledge Engine.
        """
        matches: List[Dict[str, Any]] = []
        try:
            from scripts_01.knowledge_engine import (
                DEFAULT_DB_PATH,
                KnowledgeEngine,
            )
            index_db = WORKSPACE / DEFAULT_DB_PATH
            if not index_db.exists():
                return matches  # индекс ещё не построен — нет контекста
            ke = KnowledgeEngine(workspace_root=str(WORKSPACE))
            results = ke.search(goal, top_k=top_k, mode="hybrid")
            for r in results:
                meta = r.metadata or {}
                matches.append({
                    "doc_id": r.doc_id,
                    "score": round(float(r.score), 4),
                    "title": meta.get("title", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "snippet": r.snippet[:160],
                ])
        except Exception:
            pass  # Knowledge недоступен — workflow не блокируем
        return matches

    def _get_ready_steps(self, workflow: Workflow) -> List[Step]:
        """Находит шаги, готовые к выполнению (DAG resolution)."""
        ready: List[Step] = []
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

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Публикует событие через EventBus, если он подключён."""
        if self._event_bus is not None:
            from scripts_01.event_bus import Event
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
            ])
        elif status == StepStatus.FAILED:
            self._publish_event("step.failed", {
                "step_id": step.id,
                "workflow_id": workflow.id,
                "step_name": step.name or step.id,
                "error": step.error,
            ])
        elif status == StepStatus.SKIPPED:
            self._publish_event("step.skipped", {
                "step_id": step.id,
                "workflow_id": workflow.id,
                "step_name": step.name or step.id,
                "error": step.error,
            ])

    def _execute_step(self, step: Step, workflow: Workflow) -> None:
        """Выполняет один шаг. Thread-safe — вызывается из ThreadPoolExecutor."""
        with self._lock:
            step.status = StepStatus.RUNNING

        # Publish: step started
        self._publish_event("step.started", {
            "step_id": step.id,
            "workflow_id": workflow.id,
            "step_name": step.name or step.id,
            "step_type": step.type.value,
            "tool": step.tool.value if step.tool else None,
        ])

        success = False
        result = None
        error: Optional[str] = None

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

        elif step.type == StepType.VALIDATE:
            target_id = step.input.get("validate_step_id", "")
            with self._lock:
                target = next((s for s in workflow.steps if s.id == target_id), None)
            if target:
                with self._lock:
                    is_valid, validation_err = self._validator.validate(target, workflow.context)
                if is_valid:
                    success = True
                    result = "Validation passed"
                else:
                    error = f"Validation failed for {target_id}: {validation_err}"
            else:
                error = f"Target step not found: {target_id}"

        elif step.type == StepType.MODEL:
            try:
                caps = step.model_capabilities or ["code"]
                model = None
                routed_via = "router"

                # Правило 11 (User-Choice Override): policy resolve имеет приоритет
                policy_engine = self._get_policy_engine()
                if policy_engine is not None:
                    from freebuff_plugin_03.policy import is_policy_override
                    resolved = policy_engine.resolve(caps[0])
                    runtime = resolved.get("runtime") if isinstance(resolved, dict) else None
                    is_override = is_policy_override(resolved)
                    if runtime and is_override:
                        from scripts_01.model_gateway import RUNTIME_MODELS
                        model = RUNTIME_MODELS.get(runtime)
                        if model:
                            routed_via = f"policy:{runtime}"

                # Fallback: авто-маршрутизация SmartRouter
                if model is None:
                    from core_02.router import SmartRouter, ModelCatalog
                    router = SmartRouter(ModelCatalog.default())
                    decision = router.route(
                        required_capabilities=caps,
                        max_tokens_needed=step.input.get("max_tokens", 2000),
                    )
                    model = decision.model  # RouteDecision.model (не model_id)

                result = f"Routed to: {model} ({routed_via})"
                success = True
            except Exception as e:
                error = str(e)

        else:
            error = f"Unsupported step type: {step.type}"

        # Thread-safe status update
        with self._lock:
            if success:
                step.status = StepStatus.SUCCESS
                step.result = result
            else:
                step.error = error or "Tool execution failed"
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    step.status = StepStatus.PENDING
                    self._publish_event("step.retrying", {
                        "step_id": step.id,
                        "workflow_id": workflow.id,
                        "retry_count": step.retry_count,
                        "max_retries": step.max_retries,
                        "error": error,
                    ])
                else:
                    step.status = StepStatus.FAILED
                    workflow.errors.append(
                        f"Step {step.id} failed after {step.max_retries} retries: {error}"
                    )

        # Publish step event after execution
        self._publish_step_event(step, workflow)

        # Thread-safe context update
        with self._lock:
            if step.status == StepStatus.SUCCESS and step.output_key:
                workflow.context[step.output_key] = step.result

    def _run_via_tool_registry(self, step: Step) -> Tuple[bool, Any, Optional[str]]:
        """Делегирует выполнение шага в ToolRegistry."""
        try:
            tool_name = step.tool.value if step.tool else ""
            params = {}
            if step.tool == ToolType.SHELL:
                params = {
                    "command": step.input.get("command", ""),
                    "cwd": step.input.get("cwd", str(WORKSPACE)),
                    "timeout": step.timeout_seconds,
                }
            elif step.tool == ToolType.FILE:
                params = {
                    "action": step.input.get("action", "read"),
                    "path": step.input.get("path", ""),
                    "content": step.input.get("content", ""),
                }
            elif step.tool == ToolType.GIT:
                params = {
                    "command": step.input.get("command", "status"),
                    "args": step.input.get("args", ""),
                    "cwd": step.input.get("cwd", str(WORKSPACE)),
                    "timeout": step.timeout_seconds,
                }
            result = self._tool_registry.execute(tool_name, params)
            return result.success, result.data, result.error
        except Exception as e:
            return False, None, f"ToolRuntime error: {e}"

    def _handle_blocked_steps(
        self, workflow: Workflow, steps: List[Step]
    ) -> List[Step]:
        """Skip steps whose dependencies failed or were skipped.

        v5.189.9: транзитивно блокированные шаги (dep SKIPPED) тоже скипаются —
        иначе шаг, зависящий от SKIPPED, навсегда остаётся PENDING и
        run_workflow попадает в бесконечный цикл. Возвращает список скипнутых
        (пустой список ⇒ run_workflow может применить deadlock-guard).
        """
        skipped: List[Step] = []
        with self._lock:
            for s in steps:
                if s.status not in (StepStatus.PENDING, StepStatus.READY):
                    continue
                dead_deps = [
                    d for d in s.depends_on
                    if any(ss.id == d and ss.status in (
                        StepStatus.FAILED, StepStatus.SKIPPED,
                    ) for ss in steps)
                ]
                if dead_deps:
                    s.status = StepStatus.SKIPPED
                    # Формулировка точная: деп может быть FAILED или SKIPPED
                    # (речь про блокировку, а не только про фейл). Контракт
                    # «id депа присутствует в error» сохранён.
                    s.error = f"Dependency blocked: {', '.join(dead_deps)}"
                    skipped.append(s)
        # Publish outside lock to avoid holding it during EventBus I/O
        for s in skipped:
            self._publish_step_event(s, workflow)
        return skipped

    def _publish_workflow_progress(self, workflow: Workflow) -> None:
        """Publish workflow.progress event with step completion counts."""
        with self._lock:
            completed = sum(
                1 for s in workflow.steps
                if s.status in (StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED)
            )
            total = len(workflow.steps)
        self._publish_event("workflow.progress", {
            "workflow_id": workflow.id,
            "completed_steps": completed,
            "total_steps": total,
        ])

    def save_workflow(self, workflow: Workflow) -> None:
        """Сохраняет workflow в Memory Engine."""
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType

        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        engine.store(
            level=MemoryLevel.WORKING,
            key=f"workflow_{workflow.id}",
            content=json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2),
            content_type=ContentType.JSON,
            summary=f"Workflow: {workflow.goal[:80]}",
            metadata={
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "step_count": len(workflow.steps),
            },
        )

    def list_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Список сохранённых workflows."""
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel

        engine = MemoryEngine(workspace_root=str(WORKSPACE))
        entries = engine.list_entries(level=MemoryLevel.WORKING)
        workflows = []
        for e in entries:
            if e.key.startswith("workflow_"):
                try:
                    data = json.loads(e.content)
                    workflows.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue
        workflows.sort(key=lambda w: w.get("created_at", ""), reverse=True)
        return workflows[:limit]


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
  python scripts_01/orchestrator.py run "Рефакторинг модуля роутинга"
  python scripts_01/orchestrator.py run "Найди документацию по Memory Engine" --steps 3
  python scripts_01/orchestrator.py list
  python scripts_01/orchestrator.py get <workflow_id>
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
        print(f"🚀 Starting workflow: {args.goal}")
        print()
        result = orch.run_workflow(args.goal)
        print(f"📊 Status: {result.status.value}")
        print(f"   Steps: {len(result.steps)}")
        print(f"   Errors: {len(result.errors)}")
        print()
        for i, step in enumerate(result.steps, 1):
            icon = {
                StepStatus.SUCCESS: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.RUNNING: "🔄",
                StepStatus.PENDING: "⏳",
                StepStatus.READY: "📋",
                StepStatus.SKIPPED: "⏭️",
            ].get(step.status, "❓")
            print(f"  {icon} {i}. {step.name or step.id}")
            if step.error:
                print(f"     Error: {step.error[:100]}")
            if step.result:
                result_str = str(step.result)[:100]
                print(f"     Result: {result_str}...")
        print()
        if result.status == WorkflowStatus.COMPLETED:
            print("✅ Workflow completed successfully!")
        else:
            print(f"❌ Workflow failed: {', '.join(result.errors[:3])}")

        # Save
        orch.save_workflow(result)

    elif args.command == "list":
        workflows = orch.list_workflows()
        if not workflows:
            print("📭 No workflows")
            return
        print(f"📋 Workflows ({len(workflows)}):")
        for w in workflows:
            icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
            ].get(w.get("status", ""), "❓")
            print(f"  {icon} {w['id']} | {w['goal'][:60]} | {w['status']} | {len(w['steps'])} steps")

    elif args.command == "get":
        workflows = orch.list_workflows(limit=100)
        found = [w for w in workflows if w["id"].startswith(args.workflow_id)]
        if not found:
            print(f"❌ Workflow not found: {args.workflow_id}")
            return
        w = found[0]
        print(f"📋 Workflow: {w['id']}")
        print(f"   Goal:   {w['goal']}")
        print(f"   Status: {w['status']}")
        print(f"   Steps:  {len(w['steps'])}")
        print(f"   Errors: {len(w.get('errors', []))}")
        print()
        for s in w["steps"]:
            print(f"  [{s['status']}] {s['name']} ({s['type']})")
            if s.get("error"):
                print(f"    Error: {s['error'][:80]}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
