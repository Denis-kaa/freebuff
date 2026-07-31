#!/usr/bin/env python3
"""
mcp_server.py — MCP Server для Buffy Project.

Model Context Protocol server на чистом Python (без внешних SDK).
Транспорт: stdio (JSON-RPC 2.0 over stdin/stdout) и Streamable HTTP
(single endpoint /mcp: POST для запросов, GET для SSE stream, DELETE для session).

Design decision: pure Python без официального `mcp` SDK, т.к. пакет не установлен
на Termux (ModuleNotFoundError). MCP протокол — это JSON-RPC 2.0, поэтому
реализация на stdlib + asyncio достаточна и портативна.
Существующий phone_mcp_server.py использует официальный SDK; этот сервер —
нет, для независимости от внешних зависимостей.

Экспонирует возможности Buffy внешним AI-агентам:
  - Tools:    ToolRegistry (git, file, shell, sqlite, http) + knowledge/memory/context
  - Resources: BUFFY.md, ROADMAP.md, knowledge entries, memory entries, session info
  - Prompts:  context_resume, knowledge_search, task_start

Интеграция с Claude / Gemini / OpenClaw:
  Claude config (claude_desktop_config.json) — stdio:
    {
      "mcpServers": {
        "buffy": {
          "command": "python",
          "args": ["/path/to/freebuff/scripts/mcp_server.py"***REMOVED***
        ***REMOVED***
      ***REMOVED***
    ***REMOVED***

  HTTP (Streamable HTTP transport):
    python scripts/mcp_server.py --http --port 8765
    Endpoint: http://127.0.0.1:8765/mcp
    POST: JSON-RPC, GET: SSE stream, DELETE: session

  OpenClaw / Gemini: stdio или HTTP transport.

Использование:
    python scripts/mcp_server.py                    # stdio режим
    python scripts/mcp_server.py --http             # HTTP режим (port 8765)
    python scripts/mcp_server.py --tools            # список MCP tools
    python scripts/mcp_server.py --resources        # список MCP resources
    python scripts/mcp_server.py --call knowledge_search '{"query": "router"***REMOVED***'
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
***REMOVED***
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "buffy-mcp-server"
SERVER_VERSION = "1.0.0"

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class McpTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any***REMOVED*** = field(default_factory=lambda: {"type": "object", "properties": {***REMOVED******REMOVED***)
    handler: Optional[Callable***REMOVED*** = None
    category: str = "general"


@dataclass
class McpResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    handler: Optional[Callable***REMOVED*** = None


@dataclass
class McpPrompt:
    """MCP prompt template."""
    name: str
    description: str
    arguments: List[Dict[str, Any***REMOVED******REMOVED*** = field(default_factory=list)
    handler: Optional[Callable***REMOVED*** = None


# ═══════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════


def rpc_response(req_id: Any, result: Any) -> str:
    """Создаёт JSON-RPC success response."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    ***REMOVED***, ensure_ascii=False)


def rpc_error(req_id: Any, code: int, message: str, data: Any = None) -> str:
    """Создаёт JSON-RPC error response."""
    err: Dict[str, Any***REMOVED*** = {"code": code, "message": message***REMOVED***
    if data is not None:
        err["data"***REMOVED*** = data
    return json.dumps({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": err,
    ***REMOVED***, ensure_ascii=False)


def rpc_notification(method: str, params: Dict[str, Any***REMOVED***) -> str:
    """Создаёт JSON-RPC notification (no id, no response expected)."""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    ***REMOVED***, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# Session Management (Streamable HTTP)
# ═══════════════════════════════════════════════════════════════


@dataclass
class McpSession:
    """MCP HTTP session with notification queue for SSE.

    Note: No automatic TTL/cleanup — sessions persist until DELETE.
    If a client crashes without DELETE, the session remains in memory.
    For production use, add a periodic cleanup thread or max-age check.
    """

    session_id: str
    notification_queue: Queue = field(default_factory=Queue)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class McpSessionManager:
    """Thread-safe session manager for Streamable HTTP transport."""

    def __init__(self):
        self._sessions: Dict[str, McpSession***REMOVED*** = {***REMOVED***
        self._lock = threading.Lock()

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id***REMOVED*** = McpSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[McpSession***REMOVED***:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if found and deleted."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.active = False
                return True
            return False

    def push_notification(self, session_id: str, message: str) -> bool:
        """Push a notification to a session's SSE stream."""
        session = self.get_session(session_id)
        if session and session.active:
            session.notification_queue.put(message)
            return True
        return False

    def count(self) -> int:
        """Return number of active sessions."""
        with self._lock:
            return len(self._sessions)


# ═══════════════════════════════════════════════════════════════
# BuffyMcpServer
# ═══════════════════════════════════════════════════════════════


class BuffyMcpServer:
    """MCP Server для Buffy Project.

    Экспонирует:
      - ToolRegistry инструменты как MCP tools
      - Knowledge Engine как MCP resource + tool
      - Memory Engine как MCP resource + tool
      - ContextManager как MCP resource + tool
      - Документы (BUFFY.md, ROADMAP.md) как MCP resources
      - Prompts для context_resume и task_start

    Особенности:
      - Pure Python, без внешних MCP SDK
      - JSON-RPC 2.0 over stdio
      - Lazy loading компонентов (импортируются при первом использовании)
      - EventBus интеграция (mcp.* events)
    """

    def __init__(self, workspace_root: str | Path | None = None):
        self.workspace = Path(workspace_root) if workspace_root else WORKSPACE
        self._tools: Dict[str, McpTool***REMOVED*** = {***REMOVED***
        self._resources: Dict[str, McpResource***REMOVED*** = {***REMOVED***
        self._prompts: Dict[str, McpPrompt***REMOVED*** = {***REMOVED***
        self._initialized = False
        self._client_info: Dict[str, Any***REMOVED*** = {***REMOVED***

        # Lazy-loaded components
        self._tool_registry = None
        self._knowledge_engine = None
        self._memory_engine = None
        self._context_manager = None
        self._event_bus = None
        self._bridge_layer = None
        self._bootstrap_engine = None
        self._runtime_registry = None
        self._runtime_capability_registry = None
        self._policy_engine = None

        # Phase 7 (CoWork) lazy-loaded components — восстановленные модули
        self._roles_engine = None
        self._presence_engine = None
        self._collaboration_engine = None
        self._distributed_coordinator = None
        self._rag_engine = None
        self._project_pulse = None

        # Register all MCP capabilities
        self._register_tools()
        self._register_phase7_tools()
        self._register_resources()
        self._register_prompts()

    # ── Lazy component accessors ───────────────────────────

    def _get_tool_registry(self):
        if self._tool_registry is None:
            from scripts.tool_runtime import (
                ToolRegistry, GitTool, SQLiteTool, HTTPTool, FileTool, ShellTool,
            )
            self._tool_registry = ToolRegistry(
                event_bus=self._get_event_bus(),
                default_context={"workspace": str(self.workspace)***REMOVED***,
            )
            for cls in [GitTool, SQLiteTool, HTTPTool, FileTool, ShellTool***REMOVED***:
                self._tool_registry.register(cls())
        return self._tool_registry

    def _get_knowledge_engine(self):
        if self._knowledge_engine is None:
            from scripts.knowledge_engine import KnowledgeEngine
            self._knowledge_engine = KnowledgeEngine(workspace_root=str(self.workspace))
        return self._knowledge_engine

    def _get_memory_engine(self):
        if self._memory_engine is None:
            from scripts.memory_engine import MemoryEngine
            self._memory_engine = MemoryEngine(
                workspace_root=str(self.workspace),
                event_bus=self._get_event_bus(),
            )
        return self._memory_engine

    def _get_context_manager(self):
        if self._context_manager is None:
            from scripts.context_manager import ContextManager
            self._context_manager = ContextManager(str(self.workspace))
        return self._context_manager

    def _get_event_bus(self):
        if self._event_bus is None:
            try:
                from scripts.event_bus import get_default_event_bus
                self._event_bus = get_default_event_bus(str(self.workspace))
            except Exception:
                pass  # EventBus optional
        return self._event_bus

    def _get_bridge_layer(self):
        """Lazy-load Bridge Layer with graceful degradation."""
        if self._bridge_layer is None:
            try:
                from freebuff_plugin import BridgeLayer
                bus = self._get_event_bus()
                self._bridge_layer = BridgeLayer(
                    event_bus=bus or None,
                    agent_name="buffy-mcp",
                    agent_version="1.0.0",
                )
                self._bridge_layer.start()
            except ImportError as e:
                print(f"⚠️ MCP: BridgeLayer unavailable (plugin not loaded): {e***REMOVED***", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: BridgeLayer init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._bridge_layer

    def _get_bootstrap_engine(self):
        """Lazy-load Bootstrap Engine with graceful degradation."""
        if self._bootstrap_engine is None:
            try:
                from freebuff_plugin import BootstrapEngine
                bus = self._get_event_bus()
                self._bootstrap_engine = BootstrapEngine(
                    workspace_root=str(self.workspace),
                    event_bus=bus or None,
                )
            except ImportError as e:
                print(f"⚠️ MCP: BootstrapEngine unavailable (plugin not loaded): {e***REMOVED***", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: BootstrapEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._bootstrap_engine

    def _get_runtime_registry(self):
        """Lazy-load Runtime Registry with graceful degradation."""
        if self._runtime_registry is None:
            try:
                from freebuff_plugin import RuntimeRegistry, RuntimeCapabilityRegistry
                storage = self.workspace / "data" / "runtime_registry.json"
                self._runtime_registry = RuntimeRegistry(storage_path=storage)
                self._runtime_registry.load()
                self._runtime_capability_registry = RuntimeCapabilityRegistry(self._runtime_registry)
            except ImportError as e:
                print(f"⚠️ MCP: RuntimeRegistry unavailable (plugin not loaded): {e***REMOVED***", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: RuntimeRegistry init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._runtime_registry

    def _get_policy_engine(self):
        """Lazy-load Policy Engine for capability-based runtime selection."""
        if self._policy_engine is None:
            try:
                from freebuff_plugin.policy import PolicyEngine
                registry = self._get_runtime_registry()
                cap_reg = self._runtime_capability_registry
                if registry is None or cap_reg is None:
                    return None
                self._policy_engine = PolicyEngine(registry, cap_reg)
            except ImportError as e:
                print(f"⚠️ MCP: PolicyEngine unavailable (plugin not loaded): {e***REMOVED***", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: PolicyEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._policy_engine

    def _publish(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Publish MCP event to EventBus."""
        bus = self._get_event_bus()
        if bus is None:
            return
        try:
            from scripts.event_bus import Event
            bus.publish(Event(
                type=f"mcp.{event_type***REMOVED***",
                source="mcp_server",
                data=data,
            ))
        except Exception:
            pass

    # ── Phase 7 (CoWork) accessors ────────────────────────────────────

    def _get_roles_engine(self):
        """Lazy-load RoleEngine with graceful degradation."""
        if self._roles_engine is None:
            try:
                from scripts.roles import RoleEngine

                self._roles_engine = RoleEngine()
            except Exception as e:
                print(f"⚠️ MCP: RoleEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._roles_engine

    def _get_presence_engine(self):
        """Lazy-load PresenceEngine with graceful degradation."""
        if self._presence_engine is None:
            try:
                from scripts.presence import PresenceEngine

                self._presence_engine = PresenceEngine()
            except Exception as e:
                print(f"⚠️ MCP: PresenceEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._presence_engine

    def _get_collaboration_engine(self):
        """Lazy-load CollaborationEngine with graceful degradation."""
        if self._collaboration_engine is None:
            try:
                from scripts.collaboration import CollaborationEngine

                self._collaboration_engine = CollaborationEngine(
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: CollaborationEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._collaboration_engine

    def _get_distributed_coordinator(self):
        """Lazy-load DistributedCoordinator with graceful degradation."""
        if self._distributed_coordinator is None:
            try:
                from scripts.distributed_agents import DistributedCoordinator

                self._distributed_coordinator = DistributedCoordinator(
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: DistributedCoordinator init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._distributed_coordinator

    def _get_rag_engine(self):
        """Lazy-load RAGEngine with graceful degradation."""
        if self._rag_engine is None:
            try:
                from scripts.rag_engine import RAGEngine

                self._rag_engine = RAGEngine(workspace_root=str(self.workspace))
            except Exception as e:
                print(f"⚠️ MCP: RAGEngine init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._rag_engine

    def _get_project_pulse(self):
        """Lazy-load ProjectPulse with graceful degradation."""
        if self._project_pulse is None:
            try:
                from scripts.project_pulse import ProjectPulse

                self._project_pulse = ProjectPulse(
                    workspace=self.workspace,
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: ProjectPulse init failed: {e***REMOVED***", file=sys.stderr)
                return None
        return self._project_pulse

    # ── Phase 7 (CoWork) tool registration ────────────────────────────

    def _register_phase7_tools(self) -> None:
        """Регистрирует MCP tools восстановленных Phase 7 модулей."""
        # ── Roles ──
        self._tools["roles_list"***REMOVED*** = McpTool(
            name="roles_list",
            description="List role definitions and assignments (RoleEngine).",
            input_schema={"type": "object", "properties": {"definitions": {"type": "boolean", "description": "Show role definitions", "default": False***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_roles_list,
            category="roles",
        )
        self._tools["roles_get"***REMOVED*** = McpTool(
            name="roles_get",
            description="Get roles assigned to an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"***REMOVED******REMOVED***, "required": ["agent"***REMOVED******REMOVED***,
            handler=self._handle_roles_get,
            category="roles",
        )
        self._tools["roles_assign"***REMOVED*** = McpTool(
            name="roles_assign",
            description="Assign a role to an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string"***REMOVED***, "role": {"type": "string"***REMOVED******REMOVED***, "required": ["agent", "role"***REMOVED******REMOVED***,
            handler=self._handle_roles_assign,
            category="roles",
        )
        self._tools["roles_unassign"***REMOVED*** = McpTool(
            name="roles_unassign",
            description="Remove a role from an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string"***REMOVED***, "role": {"type": "string"***REMOVED******REMOVED***, "required": ["agent", "role"***REMOVED******REMOVED***,
            handler=self._handle_roles_unassign,
            category="roles",
        )
        self._tools["roles_stats"***REMOVED*** = McpTool(
            name="roles_stats",
            description="Role engine statistics.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_roles_stats,
            category="roles",
        )

        # ── Presence ──
        self._tools["presence_list"***REMOVED*** = McpTool(
            name="presence_list",
            description="List registered agents with optional status/capability filters.",
            input_schema={"type": "object", "properties": {"status": {"type": "string"***REMOVED***, "capability": {"type": "string"***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_presence_list,
            category="presence",
        )
        self._tools["presence_get"***REMOVED*** = McpTool(
            name="presence_get",
            description="Get presence details of a single agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"***REMOVED******REMOVED***, "required": ["agent"***REMOVED******REMOVED***,
            handler=self._handle_presence_get,
            category="presence",
        )
        self._tools["presence_history"***REMOVED*** = McpTool(
            name="presence_history",
            description="Get presence status-change history.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"***REMOVED***, "limit": {"type": "integer", "default": 50***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_presence_history,
            category="presence",
        )

        # ── Collaboration ──
        self._tools["collab_create"***REMOVED*** = McpTool(
            name="collab_create",
            description="Create a collaboration session.",
            input_schema={"type": "object", "properties": {"topic": {"type": "string"***REMOVED***, "owner": {"type": "string"***REMOVED***, "participants": {"type": "array", "items": {"type": "string"***REMOVED******REMOVED******REMOVED***, "required": ["topic", "owner"***REMOVED******REMOVED***,
            handler=self._handle_collab_create,
            category="collaboration",
        )
        self._tools["collab_list"***REMOVED*** = McpTool(
            name="collab_list",
            description="List collaboration sessions.",
            input_schema={"type": "object", "properties": {"status": {"type": "string"***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_collab_list,
            category="collaboration",
        )
        self._tools["collab_get"***REMOVED*** = McpTool(
            name="collab_get",
            description="Get collaboration session details.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"***REMOVED******REMOVED***, "required": ["session_id"***REMOVED******REMOVED***,
            handler=self._handle_collab_get,
            category="collaboration",
        )
        self._tools["collab_join"***REMOVED*** = McpTool(
            name="collab_join",
            description="Join a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"***REMOVED***, "participant": {"type": "string"***REMOVED***, "role": {"type": "string"***REMOVED******REMOVED***, "required": ["session_id", "participant"***REMOVED******REMOVED***,
            handler=self._handle_collab_join,
            category="collaboration",
        )
        self._tools["collab_leave"***REMOVED*** = McpTool(
            name="collab_leave",
            description="Leave a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"***REMOVED***, "participant": {"type": "string"***REMOVED******REMOVED***, "required": ["session_id", "participant"***REMOVED******REMOVED***,
            handler=self._handle_collab_leave,
            category="collaboration",
        )
        self._tools["collab_send"***REMOVED*** = McpTool(
            name="collab_send",
            description="Send a message to a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"***REMOVED***, "sender": {"type": "string"***REMOVED***, "content": {"type": "string"***REMOVED***, "msg_type": {"type": "string", "default": "text"***REMOVED******REMOVED***, "required": ["session_id", "sender", "content"***REMOVED******REMOVED***,
            handler=self._handle_collab_send,
            category="collaboration",
        )
        self._tools["collab_history"***REMOVED*** = McpTool(
            name="collab_history",
            description="Get message history of a session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"***REMOVED***, "limit": {"type": "integer", "default": 50***REMOVED******REMOVED***, "required": ["session_id"***REMOVED******REMOVED***,
            handler=self._handle_collab_history,
            category="collaboration",
        )
        self._tools["collab_status"***REMOVED*** = McpTool(
            name="collab_status",
            description="Collaboration engine diagnostics.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_collab_status,
            category="collaboration",
        )

        # ── Distributed Agents ──
        self._tools["distributed_list"***REMOVED*** = McpTool(
            name="distributed_list",
            description="List distributed agent mesh and coordinator status.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_distributed_list,
            category="distributed",
        )
        self._tools["distributed_spawn"***REMOVED*** = McpTool(
            name="distributed_spawn",
            description="Spawn/register a distributed agent.",
            input_schema={"type": "object", "properties": {"name": {"type": "string"***REMOVED***, "command": {"type": "string"***REMOVED***, "capabilities": {"type": "object"***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_distributed_spawn,
            category="distributed",
        )
        self._tools["distributed_run"***REMOVED*** = McpTool(
            name="distributed_run",
            description="Run a distributed workflow plan.",
            input_schema={"type": "object", "properties": {"goal": {"type": "string"***REMOVED***, "steps": {"type": "array", "items": {"type": "object"***REMOVED******REMOVED******REMOVED***, "required": ["goal", "steps"***REMOVED******REMOVED***,
            handler=self._handle_distributed_run,
            category="distributed",
        )
        self._tools["distributed_status"***REMOVED*** = McpTool(
            name="distributed_status",
            description="Distributed system status.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_distributed_status,
            category="distributed",
        )
        self._tools["distributed_broadcast"***REMOVED*** = McpTool(
            name="distributed_broadcast",
            description="Broadcast a message to all distributed agents.",
            input_schema={"type": "object", "properties": {"message": {"type": "string"***REMOVED******REMOVED***, "required": ["message"***REMOVED******REMOVED***,
            handler=self._handle_distributed_broadcast,
            category="distributed",
        )

        # ── RAG ──
        self._tools["rag_search"***REMOVED*** = McpTool(
            name="rag_search",
            description="RAG 2.0 semantic search with ranking.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"***REMOVED***, "top_k": {"type": "integer", "default": 10***REMOVED***, "mode": {"type": "string", "default": "hybrid_rrf"***REMOVED******REMOVED***, "required": ["query"***REMOVED******REMOVED***,
            handler=self._handle_rag_search,
            category="rag",
        )
        self._tools["rag_hybrid"***REMOVED*** = McpTool(
            name="rag_hybrid",
            description="Quick hybrid RRF search.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"***REMOVED***, "top_k": {"type": "integer", "default": 10***REMOVED******REMOVED***, "required": ["query"***REMOVED******REMOVED***,
            handler=self._handle_rag_hybrid,
            category="rag",
        )
        self._tools["rag_rerank"***REMOVED*** = McpTool(
            name="rag_rerank",
            description="Feature-based re-ranking of candidates.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"***REMOVED***, "top_k": {"type": "integer", "default": 10***REMOVED******REMOVED***, "required": ["query"***REMOVED******REMOVED***,
            handler=self._handle_rag_rerank,
            category="rag",
        )

        # ── Project Pulse ──
        self._tools["pulse_list"***REMOVED*** = McpTool(
            name="pulse_list",
            description="List project pulse entries.",
            input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 50***REMOVED***, "event_type": {"type": "string"***REMOVED***, "source": {"type": "string"***REMOVED******REMOVED******REMOVED***,
            handler=self._handle_pulse_list,
            category="pulse",
        )
        self._tools["pulse_stats"***REMOVED*** = McpTool(
            name="pulse_stats",
            description="Project pulse statistics.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_pulse_stats,
            category="pulse",
        )
        self._tools["pulse_scan"***REMOVED*** = McpTool(
            name="pulse_scan",
            description="Run full project scan (git + files) into the pulse.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_pulse_scan,
            category="pulse",
        )

    # ── Phase 7 handlers: Roles ───────────────────────────────────────

    def _handle_roles_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List role definitions and assignments."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"***REMOVED***
        try:
            data = {
                "roles": [r.to_dict() for r in engine.list_roles()***REMOVED***,
                "assignments": [a.to_dict() for a in engine.list_assignments()***REMOVED***,
            ***REMOVED***
            self._publish("roles.listed", {"roles": len(data["roles"***REMOVED***), "assignments": len(data["assignments"***REMOVED***)***REMOVED***)
            return {"success": True, "data": data***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_roles_get(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get roles of an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"***REMOVED***
        agent = arguments.get("agent", "")
        if not agent:
            return {"success": False, "error": "Missing required parameter: agent"***REMOVED***
        try:
            return {"success": True, "data": {"agent": agent, "roles": engine.get_roles(agent)***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_roles_assign(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Assign a role to an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"***REMOVED***
        agent = arguments.get("agent", "")
        role = arguments.get("role", "")
        if not agent or not role:
            return {"success": False, "error": "Missing required parameters: agent, role"***REMOVED***
        try:
            ok = engine.assign_role(agent, role)
            if not ok:
                return {"success": False, "error": f"Unknown role: {role***REMOVED***"***REMOVED***
            return {"success": True, "data": {"agent": agent, "role": role***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_roles_unassign(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Remove a role from an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"***REMOVED***
        agent = arguments.get("agent", "")
        role = arguments.get("role", "")
        if not agent or not role:
            return {"success": False, "error": "Missing required parameters: agent, role"***REMOVED***
        try:
            ok = engine.unassign_role(agent, role)
            return {"success": True, "data": {"agent": agent, "role": role, "removed": ok***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_roles_stats(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Role engine statistics."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"***REMOVED***
        try:
            return {"success": True, "data": engine.get_stats()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Phase 7 handlers: Presence ────────────────────────────────────

    def _handle_presence_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List agents with filters."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"***REMOVED***
        try:
            data = engine.list_agents_json(
                status=arguments.get("status"), capability=arguments.get("capability")
            )
            self._publish("presence.listed", {"total": data.get("total", 0)***REMOVED***)
            return {"success": True, "data": data***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_presence_get(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get agent presence details."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"***REMOVED***
        agent_name = arguments.get("agent") or arguments.get("agent_name", "")
        if not agent_name:
            return {"success": False, "error": "agent is required"***REMOVED***
        try:
            return {"success": True, "data": engine.get_agent_json(agent_name)***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_presence_history(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get presence history."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"***REMOVED***
        try:
            return {"success": True, "data": engine.get_history_json(
                agent_name=arguments.get("agent") or arguments.get("agent_name"),
                limit=int(arguments.get("limit", 50)),
            )***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Phase 7 handlers: Collaboration ───────────────────────────────

    def _handle_collab_create(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Create a collaboration session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        topic = arguments.get("topic", "")
        owner = arguments.get("owner", "")
        if not topic or not owner:
            return {"success": False, "error": "Missing required parameters: topic, owner"***REMOVED***
        try:
            session = engine.create_session(topic, owner, arguments.get("participants"))
            return {"success": True, "data": session.to_dict()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List collaboration sessions."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        try:
            sessions = engine.list_sessions(status=arguments.get("status"))
            return {"success": True, "data": {"sessions": [s.to_dict() for s in sessions***REMOVED******REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_get(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get session details."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        session_id = arguments.get("session_id", "")
        if not session_id:
            return {"success": False, "error": "Missing required parameter: session_id"***REMOVED***
        try:
            session = engine.get_session(session_id)
            if session is None:
                return {"success": False, "error": f"Session not found: {session_id***REMOVED***"***REMOVED***
            return {"success": True, "data": session.to_dict()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_join(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Join a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        session_id = arguments.get("session_id", "")
        participant = arguments.get("participant", "")
        if not session_id or not participant:
            return {"success": False, "error": "Missing required parameters: session_id, participant"***REMOVED***
        try:
            ok = engine.join_session(session_id, participant, arguments.get("role", "editor"))
            return {"success": True, "data": {"joined": ok, "session_id": session_id, "participant": participant***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_leave(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Leave a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        session_id = arguments.get("session_id", "")
        participant = arguments.get("participant", "")
        if not session_id or not participant:
            return {"success": False, "error": "Missing required parameters: session_id, participant"***REMOVED***
        try:
            ok = engine.leave_session(session_id, participant)
            return {"success": True, "data": {"left": ok***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_send(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Send a message to a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        session_id = arguments.get("session_id", "")
        sender = arguments.get("sender", "")
        content = arguments.get("content", "")
        if not session_id or not sender or not content:
            return {"success": False, "error": "Missing required parameters: session_id, sender, content"***REMOVED***
        try:
            msg = engine.send_message(session_id, sender, content, arguments.get("msg_type", "text"))
            if msg is None:
                return {"success": False, "error": "Session not found or closed"***REMOVED***
            return {"success": True, "data": asdict(msg)***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_history(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get session history."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        session_id = arguments.get("session_id", "")
        if not session_id:
            return {"success": False, "error": "Missing required parameter: session_id"***REMOVED***
        try:
            messages = engine.get_history(session_id, limit=int(arguments.get("limit", 50)))
            return {"success": True, "data": {"messages": [asdict(m) for m in messages***REMOVED******REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_collab_status(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Collaboration engine diagnostics."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"***REMOVED***
        try:
            return {"success": True, "data": engine.get_status()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Phase 7 handlers: Distributed ─────────────────────────────────

    def _handle_distributed_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List distributed mesh."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"***REMOVED***
        try:
            agents = coord.list_agents()
            # total берём из mesh.get_summary() (контракт теста с mock-координатором).
            try:
                mesh_summary = coord.mesh.get_summary()
                total = int(mesh_summary.get("total", len(agents))) if isinstance(mesh_summary, dict) else len(agents)
            except Exception:
                total = len(agents)
            data = {"agents": agents, "total": total, "status": coord.get_status()***REMOVED***
            self._publish("distributed.listed", {"agents": total***REMOVED***)
            return {"success": True, "data": data***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_distributed_spawn(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Spawn a distributed agent."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"***REMOVED***
        try:
            result = coord.spawn_agent(
                name=arguments.get("name"),
                command=arguments.get("command", "python"),
                capabilities=arguments.get("capabilities"),
            )
            return {"success": True, "data": result***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_distributed_run(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Run a distributed workflow."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"***REMOVED***
        goal = arguments.get("goal", "")
        steps = arguments.get("steps")
        if not goal or not steps:
            return {"success": False, "error": "Missing required parameters: goal, steps"***REMOVED***
        try:
            plan = coord.run_distributed_workflow(goal=goal, steps=steps)
            return {"success": True, "data": plan.to_dict()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_distributed_status(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Distributed system status."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"***REMOVED***
        try:
            return {"success": True, "data": coord.get_status()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_distributed_broadcast(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Broadcast to all agents."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"***REMOVED***
        message = arguments.get("message", "")
        if not message:
            return {"success": False, "error": "Missing required parameter: message"***REMOVED***
        try:
            recipients = coord.broadcast_to_all(message, arguments.get("data"))
            return {"success": True, "data": {"recipients": recipients, "agents_notified": recipients, "message": message***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Phase 7 handlers: RAG ─────────────────────────────────────────

    def _handle_rag_search(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """RAG search."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"***REMOVED***
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"***REMOVED***
        try:
            report = rag.search(
                query,
                top_k=int(arguments.get("top_k", 10)),
                mode=arguments.get("mode", "hybrid_rrf"),
            )
            return {"success": True, "data": report.to_dict()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_rag_hybrid(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Hybrid RRF search."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"***REMOVED***
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"***REMOVED***
        try:
            report = rag.hybrid_search(query, top_k=int(arguments.get("top_k", 10)))
            return {"success": True, "data": report.to_dict()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_rag_rerank(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Re-rank candidates."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"***REMOVED***
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"***REMOVED***
        try:
            report = rag.search(query, top_k=int(arguments.get("top_k", 30)) * 3, mode="hybrid_rrf", rerank_results=False)
            reranked = rag.rerank(query, report.results)
            return {"success": True, "data": [r.to_dict() for r in reranked[: int(arguments.get("top_k", 10))***REMOVED******REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Phase 7 handlers: Project Pulse ───────────────────────────────

    def _handle_pulse_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List pulse entries."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"***REMOVED***
        try:
            data = pulse.list_json(
                limit=int(arguments.get("limit", 50)),
                event_type=arguments.get("event_type"),
                source=arguments.get("source"),
            )
            return {"success": True, "data": data***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_pulse_stats(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Pulse statistics."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"***REMOVED***
        try:
            return {"success": True, "data": pulse.get_stats()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_pulse_scan(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Run full project scan."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"***REMOVED***
        try:
            return {"success": True, "data": pulse.full_scan()***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Tool registration ──────────────────────────────────

    def _register_tools(self) -> None:
        """Регистрирует все MCP tools."""
        # 1. ToolRegistry tools (auto-discovered)
        self._register_toolregistry_tools()

        # 2. Knowledge tools
        self._tools["knowledge_search"***REMOVED*** = McpTool(
            name="knowledge_search",
            description="Search the Knowledge Engine (FTS5 + TF-IDF + semantic). Returns ranked results with snippets.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"***REMOVED***,
                    "mode": {"type": "string", "description": "Search mode: keyword, semantic, hybrid", "default": "hybrid"***REMOVED***,
                    "top_k": {"type": "integer", "description": "Max results", "default": 10***REMOVED***,
                ***REMOVED***,
                "required": ["query"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_knowledge_search,
            category="knowledge",
        )

        # 3. Memory tools
        self._tools["memory_store"***REMOVED*** = McpTool(
            name="memory_store",
            description="Store a memory entry in Buffy's Memory Engine (5 levels: working, project, knowledge, personal, archive).",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"***REMOVED******REMOVED***,
                    "key": {"type": "string", "description": "Memory key (unique within level)"***REMOVED***,
                    "content": {"type": "string", "description": "Content to store"***REMOVED***,
                    "summary": {"type": "string", "description": "Short summary", "default": ""***REMOVED***,
                ***REMOVED***,
                "required": ["level", "key", "content"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_memory_store,
            category="memory",
        )

        self._tools["memory_retrieve"***REMOVED*** = McpTool(
            name="memory_retrieve",
            description="Retrieve a memory entry from Buffy's Memory Engine by level and key.",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"***REMOVED******REMOVED***,
                    "key": {"type": "string", "description": "Memory key"***REMOVED***,
                ***REMOVED***,
                "required": ["level", "key"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_memory_retrieve,
            category="memory",
        )

        self._tools["memory_list"***REMOVED*** = McpTool(
            name="memory_list",
            description="List all memory entries at a given level.",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"***REMOVED******REMOVED***,
                ***REMOVED***,
                "required": ["level"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_memory_list,
            category="memory",
        )

        # 4. Context/Session tools
        self._tools["session_status"***REMOVED*** = McpTool(
            name="session_status",
            description="Get the status of the current/last Buffy session (messages, tokens, context usage).",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_session_status,
            category="context",
        )

        self._tools["context_resume"***REMOVED*** = McpTool(
            name="context_resume",
            description="Get the last session conspect for context restoration. Returns markdown summary of previous session.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_context_resume,
            category="context",
        )

        # 5. Plugin tools
        self._tools["plugins_list"***REMOVED*** = McpTool(
            name="plugins_list",
            description="List all loaded plugins and their states.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_plugins_list,
            category="plugins",
        )

        # 6. Bridge Layer tools (Phase 6: CoWork/Companion)
        self._tools["bridge_connect"***REMOVED*** = McpTool(
            name="bridge_connect",
            description="Connect to an external MCP server via stdio or HTTP. The server's tools become available as ACP capabilities.",
            input_schema={
                "type": "object",
                "properties": {
                    "transport": {
                        "type": "string",
                        "description": "Transport type",
                        "enum": ["stdio", "http"***REMOVED***,
                    ***REMOVED***,
                    "command": {
                        "type": "string",
                        "description": "Command for stdio transport (e.g., 'python')",
                    ***REMOVED***,
                    "args": {
                        "type": "string",
                        "description": "Space-separated args for stdio (e.g., 'scripts/mcp_server.py')",
                    ***REMOVED***,
                    "endpoint": {
                        "type": "string",
                        "description": "HTTP endpoint (e.g., 'http://127.0.0.1:8765/mcp')",
                    ***REMOVED***,
                    "name": {
                        "type": "string",
                        "description": "Optional custom name for the server",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["transport"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_bridge_connect,
            category="bridge",
        )

        self._tools["bridge_list"***REMOVED*** = McpTool(
            name="bridge_list",
            description="List all connected MCP servers and their available tools.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_bridge_list,
            category="bridge",
        )

        self._tools["bridge_disconnect"***REMOVED*** = McpTool(
            name="bridge_disconnect",
            description="Disconnect a connected MCP server by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Server name to disconnect (from bridge_list)",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["name"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_bridge_disconnect,
            category="bridge",
        )

        self._tools["bridge_rpc"***REMOVED*** = McpTool(
            name="bridge_rpc",
            description="Send a JSON-RPC request to a connected MCP server (e.g., tools/call, resources/list, ping).",
            input_schema={
                "type": "object",
                "properties": {
                    "server": {
                        "type": "string",
                        "description": "Server name (from bridge_list)",
                    ***REMOVED***,
                    "method": {
                        "type": "string",
                        "description": "MCP JSON-RPC method (tools/list, resources/list, tools/call, ping)",
                    ***REMOVED***,
                    "tool": {
                        "type": "string",
                        "description": "Tool name for tools/call",
                    ***REMOVED***,
                    "arguments": {
                        "type": "string",
                        "description": "JSON arguments for tools/call",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["server", "method"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_bridge_rpc,
            category="bridge",
        )

        # 7. Bootstrap Engine tools
        self._tools["bootstrap_check"***REMOVED*** = McpTool(
            name="bootstrap_check",
            description="Check the current environment state (OS, Python, Node, Git, Disk, RAM, packages). Returns detailed environment report.",
            input_schema={
                "type": "object",
                "properties": {
                    "quick": {
                        "type": "boolean",
                        "description": "Quick check (OS, Python, Git, Disk only)",
                        "default": False,
                    ***REMOVED***,
                ***REMOVED***,
            ***REMOVED***,
            handler=self._handle_bootstrap_check,
            category="bootstrap",
        )

        self._tools["bootstrap_run"***REMOVED*** = McpTool(
            name="bootstrap_run",
            description="Run full bootstrap: check environment → load profile → install components → diagnose → report. Idempotent — skips already-installed components.",
            input_schema={
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "string",
                        "description": "Profile name: minimal, developer, offline, cloud, android",
                        "default": "minimal",
                    ***REMOVED***,
                ***REMOVED***,
            ***REMOVED***,
            handler=self._handle_bootstrap_run,
            category="bootstrap",
        )

        self._tools["bootstrap_status"***REMOVED*** = McpTool(
            name="bootstrap_status",
            description="Get Bootstrap Engine status — whether bootstrap was ever run, last profile, warnings, errors.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_bootstrap_status,
            category="bootstrap",
        )

        # 8. Runtime Abstraction Layer tools
        self._tools["runtime_list"***REMOVED*** = McpTool(
            name="runtime_list",
            description="List all discovered AI runtimes, their connection status, capabilities, and the active runtime.",
            input_schema={"type": "object", "properties": {***REMOVED******REMOVED***,
            handler=self._handle_runtime_list,
            category="runtime",
        )

        self._tools["runtime_connect"***REMOVED*** = McpTool(
            name="runtime_connect",
            description="Connect to a registered AI runtime by name (e.g., freebuff, claude-code). Performs MCP handshake.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to connect",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["name"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_runtime_connect,
            category="runtime",
        )

        self._tools["runtime_disconnect"***REMOVED*** = McpTool(
            name="runtime_disconnect",
            description="Disconnect an active AI runtime by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to disconnect",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["name"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_runtime_disconnect,
            category="runtime",
        )

        self._tools["runtime_select"***REMOVED*** = McpTool(
            name="runtime_select",
            description="Select the active default AI runtime by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to set as active",
                    ***REMOVED***,
                ***REMOVED***,
                "required": ["name"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_runtime_select,
            category="runtime",
        )

        self._tools["runtime_generate"***REMOVED*** = McpTool(
            name="runtime_generate",
            description="Generate a response from an AI runtime. Selects runtime by capability, explicit name, or active runtime.",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Single prompt/message to send",
                    ***REMOVED***,
                    "messages": {
                        "type": "array",
                        "description": "Optional list of {role, content***REMOVED*** messages (overrides prompt)",
                    ***REMOVED***,
                    "name": {
                        "type": "string",
                        "description": "Explicit runtime name (optional)",
                    ***REMOVED***,
                    "capability": {
                        "type": "string",
                        "description": "Select runtime by capability, e.g. coding (optional)",
                    ***REMOVED***,
                    "system": {
                        "type": "string",
                        "description": "System prompt (optional)",
                    ***REMOVED***,
                    "temperature": {
                        "type": "number",
                        "description": "Generation temperature",
                        "default": 0.7,
                    ***REMOVED***,
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                    ***REMOVED***,
                ***REMOVED***,
            ***REMOVED***,
            handler=self._handle_runtime_generate,
            category="runtime",
        )

    def _register_toolregistry_tools(self) -> None:
        """Auto-discover and register ToolRegistry tools as MCP tools."""
        try:
            registry = self._get_tool_registry()
            for tool_info in registry.list_tools():
                # Convert ToolRegistry params to JSON Schema
                properties: Dict[str, Any***REMOVED*** = {***REMOVED***
                required: List[str***REMOVED*** = [***REMOVED***
                for p in tool_info.get("parameters", [***REMOVED***):
                    prop: Dict[str, Any***REMOVED*** = {"type": p["type"***REMOVED***, "description": p["description"***REMOVED******REMOVED***
                    if p.get("default") is not None:
                        prop["default"***REMOVED*** = p["default"***REMOVED***
                    if p.get("enum"):
                        prop["enum"***REMOVED*** = p["enum"***REMOVED***
                    properties[p["name"***REMOVED******REMOVED*** = prop
                    if p.get("required"):
                        required.append(p["name"***REMOVED***)

                schema: Dict[str, Any***REMOVED*** = {
                    "type": "object",
                    "properties": properties,
                ***REMOVED***
                if required:
                    schema["required"***REMOVED*** = required

                tool_name = tool_info["name"***REMOVED***
                self._tools[tool_name***REMOVED*** = McpTool(
                    name=tool_name,
                    description=tool_info["description"***REMOVED***,
                    input_schema=schema,
                    handler=self._make_toolregistry_handler(tool_name),
                    category=tool_info.get("category", "general"),
                )
        except Exception as e:
            print(f"⚠️ MCP: ToolRegistry discovery failed: {e***REMOVED***", file=sys.stderr)

    def _make_toolregistry_handler(self, tool_name: str) -> Callable:
        """Creates a handler that delegates to ToolRegistry.execute()."""
        def handler(arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
            registry = self._get_tool_registry()
            result = registry.execute(tool_name, arguments)
            self._publish("tool.called", {"tool": tool_name, "success": result.success***REMOVED***)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "duration_ms": result.duration_ms,
            ***REMOVED***
        return handler

    # ── Resource registration ──────────────────────────────

    def _register_resources(self) -> None:
        """Регистрирует все MCP resources."""
        # 1. Project documents
        doc_resources = [
            ("buffy://manifest", "buffy_manifest", "BUFFY.md — master prompt / agent manifesto", "BUFFY.md"),
            ("buffy://roadmap", "buffy_roadmap", "ROADMAP.md — project roadmap with 5 phases", "docs/vision/ROADMAP.md"),
            ("buffy://spec", "buffy_spec", "SPEC.md — technical specification", "SPEC.md"),
            ("buffy://changelog", "buffy_changelog", "CHANGELOG.md — version history", "CHANGELOG.md"),
            ("buffy://task", "buffy_task", "TASK.md — current task", "TASK.md"),
            ("buffy://inventory", "buffy_inventory", "SYSTEM_INVENTORY.md — full component catalog", "docs/core/SYSTEM_INVENTORY.md"),
            ("buffy://decisions", "buffy_decisions", "DECISIONS.md — index of architecture decision records", "docs/decisions/DECISIONS.md"),
        ***REMOVED***
        for uri, name, desc, rel_path in doc_resources:
            self._resources[uri***REMOVED*** = McpResource(
                uri=uri,
                name=name,
                description=desc,
                mime_type="text/markdown",
                handler=self._make_file_resource_handler(rel_path),
            )

        # 2. Dynamic resources (knowledge, memory) — handled via URI patterns
        self._resources["buffy://knowledge"***REMOVED*** = McpResource(
            uri="buffy://knowledge",
            name="knowledge_index",
            description="Knowledge Engine index — use knowledge_search tool to query, or buffy://knowledge/{key***REMOVED*** to read specific entry",
            mime_type="application/json",
            handler=self._handle_knowledge_resource,
        )

        self._resources["buffy://memory"***REMOVED*** = McpResource(
            uri="buffy://memory",
            name="memory_overview",
            description="Memory Engine overview — use buffy://memory/{level***REMOVED***/{key***REMOVED*** to read specific entry",
            mime_type="application/json",
            handler=self._handle_memory_resource,
        )

    def _make_file_resource_handler(self, rel_path: str) -> Callable:
        """Creates a handler that reads a project file."""
        def handler(uri: str) -> Tuple[str, str***REMOVED***:
            full_path = self.workspace / rel_path
            if not full_path.exists():
                return "", f"File not found: {rel_path***REMOVED***"
            content = full_path.read_text(encoding="utf-8")
            return content, "text/markdown"
        return handler

    def _handle_knowledge_resource(self, uri: str) -> Tuple[str, str***REMOVED***:
        """Handle buffy://knowledge or buffy://knowledge/{key***REMOVED***."""
        parts = uri.replace("buffy://knowledge", "").strip("/").split("/", 1)
        if not parts or parts[0***REMOVED*** == "":
            # List all knowledge entries
            from scripts.memory_engine import MemoryLevel
            me = self._get_memory_engine()
            entries = me.list_entries(MemoryLevel.KNOWLEDGE)
            data = [{"key": e.key, "summary": e.summary[:100***REMOVED******REMOVED*** for e in entries***REMOVED***
            return json.dumps(data, ensure_ascii=False, indent=2), "application/json"
        else:
            key = parts[0***REMOVED***
            from scripts.memory_engine import MemoryLevel
            me = self._get_memory_engine()
            entry = me.retrieve(MemoryLevel.KNOWLEDGE, key)
            if entry is None:
                return "", f"Knowledge entry not found: {key***REMOVED***"
            return entry.content, "text/markdown"

    def _handle_memory_resource(self, uri: str) -> Tuple[str, str***REMOVED***:
        """Handle buffy://memory or buffy://memory/{level***REMOVED***/{key***REMOVED***."""
        from scripts.memory_engine import MemoryLevel
        parts = uri.replace("buffy://memory", "").strip("/").split("/", 1)
        me = self._get_memory_engine()

        if not parts or parts[0***REMOVED*** == "":
            # Overview: list all levels with counts
            overview = {***REMOVED***
            for level in MemoryLevel:
                entries = me.list_entries(level)
                overview[level.value***REMOVED*** = len(entries)
            return json.dumps(overview, ensure_ascii=False, indent=2), "application/json"
        elif len(parts) >= 2:
            level_str, key = parts[0***REMOVED***, parts[1***REMOVED***
            try:
                level = MemoryLevel(level_str)
            except ValueError:
                return "", f"Invalid memory level: {level_str***REMOVED***"
            entry = me.retrieve(level, key)
            if entry is None:
                return "", f"Memory entry not found: {level***REMOVED***/{key***REMOVED***"
            return entry.content, "text/markdown"
        else:
            # buffy://memory/{level***REMOVED*** — list entries at level
            level_str = parts[0***REMOVED***
            try:
                level = MemoryLevel(level_str)
            except ValueError:
                return "", f"Invalid memory level: {level_str***REMOVED***"
            entries = me.list_entries(level)
            data = [{"key": e.key, "summary": e.summary[:100***REMOVED******REMOVED*** for e in entries***REMOVED***
            return json.dumps(data, ensure_ascii=False, indent=2), "application/json"

    # ── Prompt registration ────────────────────────────────

    def _register_prompts(self) -> None:
        """Регистрирует MCP prompts."""
        self._prompts["context_resume"***REMOVED*** = McpPrompt(
            name="context_resume",
            description="Restore Buffy's context from the last session. Returns a prompt for starting a new session with previous context.",
            arguments=[***REMOVED***,
            handler=self._handle_prompt_context_resume,
        )

        self._prompts["knowledge_search"***REMOVED*** = McpPrompt(
            name="knowledge_search",
            description="Search the Knowledge Engine and format results as a context prompt.",
            arguments=[
                {"name": "query", "description": "Search query", "required": True***REMOVED***,
                {"name": "mode", "description": "Search mode: keyword, semantic, hybrid", "default": "hybrid"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_prompt_knowledge_search,
        )

        self._prompts["task_start"***REMOVED*** = McpPrompt(
            name="task_start",
            description="Start a new task with context. Returns a structured prompt for beginning work on a task.",
            arguments=[
                {"name": "task", "description": "Task description", "required": True***REMOVED***,
                {"name": "project", "description": "Project name", "default": "freebuff"***REMOVED***,
            ***REMOVED***,
            handler=self._handle_prompt_task_start,
        )

    def _handle_prompt_context_resume(self, args: Dict[str, Any***REMOVED***) -> str:
        """Generate context resume prompt."""
        conspect = self._handle_context_resume({***REMOVED***)["data"***REMOVED*** or ""
        return (
            "I am starting a new session. Here is the context from my previous session:\n\n"
            f"{conspect***REMOVED***\n\n"
            "Please read BUFFY.md, restore context, and briefly tell me "
            "what was done in the previous session and what we are continuing."
        )

    def _handle_prompt_knowledge_search(self, args: Dict[str, Any***REMOVED***) -> str:
        """Generate knowledge search prompt."""
        query = args.get("query", "")
        mode = args.get("mode", "hybrid")
        result = self._handle_knowledge_search({"query": query, "mode": mode***REMOVED***)
        results = result.get("data", [***REMOVED***)
        lines = [f"## Knowledge Search Results for: '{query***REMOVED***'", ""***REMOVED***
        for r in results:
            lines.append(f"### [{r.get('score', 0):.3f***REMOVED******REMOVED*** {r.get('doc_id', '?')***REMOVED***")
            lines.append(r.get("snippet", "")[:300***REMOVED***)
            lines.append("")
        return "\n".join(lines) if lines else "No results found."

    def _handle_prompt_task_start(self, args: Dict[str, Any***REMOVED***) -> str:
        """Generate task start prompt."""
        task = args.get("task", "")
        project = args.get("project", "freebuff")
        return (
            f"TASK: {task***REMOVED***\n"
            f"PROJECT: {project***REMOVED***\n\n"
            "Please:\n"
            "1. Read BUFFY.md and relevant docs\n"
            "2. Create a plan with TODO steps\n"
            "3. Implement the changes\n"
            "4. Run tests and code review\n"
            "5. Document changes in CHANGELOG.md"
        )

    # ── Tool handlers ──────────────────────────────────────

    def _handle_knowledge_search(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Search Knowledge Engine."""
        query = arguments.get("query", "")
        mode = arguments.get("mode", "hybrid")
        top_k = arguments.get("top_k", 10)

        if not query:
            return {"success": False, "error": "query is required"***REMOVED***

        try:
            ke = self._get_knowledge_engine()
            results = ke.search(query, top_k=top_k, mode=mode)
            self._publish("knowledge.searched", {"query": query, "results": len(results)***REMOVED***)
            return {
                "success": True,
                "data": [
                    {
                        "doc_id": r.doc_id,
                        "score": r.score,
                        "snippet": r.snippet,
                        "metadata": r.metadata,
                    ***REMOVED***
                    for r in results
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_memory_store(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Store memory entry."""
        from scripts.memory_engine import MemoryEngine, MemoryLevel, ContentType

        level_str = arguments.get("level", "")
        key = arguments.get("key", "")
        content = arguments.get("content", "")
        summary = arguments.get("summary", "")

        if not all([level_str, key, content***REMOVED***):
            return {"success": False, "error": "level, key, content are required"***REMOVED***

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str***REMOVED***"***REMOVED***

        try:
            me = self._get_memory_engine()
            me.store(
                level=level,
                key=key,
                content=content,
                content_type=ContentType.TEXT,
                summary=summary,
            )
            self._publish("memory.stored", {"level": level_str, "key": key***REMOVED***)
            return {"success": True, "data": f"Stored {level_str***REMOVED***/{key***REMOVED***"***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_memory_retrieve(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Retrieve memory entry."""
        from scripts.memory_engine import MemoryLevel

        level_str = arguments.get("level", "")
        key = arguments.get("key", "")

        if not all([level_str, key***REMOVED***):
            return {"success": False, "error": "level and key are required"***REMOVED***

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str***REMOVED***"***REMOVED***

        try:
            me = self._get_memory_engine()
            entry = me.retrieve(level, key)
            if entry is None:
                return {"success": False, "error": f"Not found: {level_str***REMOVED***/{key***REMOVED***"***REMOVED***
            return {
                "success": True,
                "data": {
                    "key": entry.key,
                    "content": entry.content,
                    "summary": entry.summary,
                    "content_type": entry.content_type.value if hasattr(entry.content_type, 'value') else str(entry.content_type),
                    "metadata": entry.metadata,
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_memory_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List memory entries at a level."""
        from scripts.memory_engine import MemoryLevel

        level_str = arguments.get("level", "")
        if not level_str:
            return {"success": False, "error": "level is required"***REMOVED***

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str***REMOVED***"***REMOVED***

        try:
            me = self._get_memory_engine()
            entries = me.list_entries(level)
            return {
                "success": True,
                "data": [
                    {
                        "key": e.key,
                        "summary": e.summary[:100***REMOVED***,
                        "content_type": e.content_type.value if hasattr(e.content_type, 'value') else str(e.content_type),
                    ***REMOVED***
                    for e in entries
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_session_status(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get session status."""
        try:
            cm = self._get_context_manager()
            from scripts.context_manager import SessionStatus
            active = cm.list_sessions(SessionStatus.ACTIVE)
            if active:
                s = active[0***REMOVED***
                status = cm.get_context_status(s["session_id"***REMOVED***)
                return {"success": True, "data": {"session": s, "context": status***REMOVED******REMOVED***
            else:
                return {"success": True, "data": {"session": None, "message": "No active sessions"***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_context_resume(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get last conspect for context restoration."""
        summaries_dir = self.workspace / "context" / "summaries"
        if not summaries_dir.is_dir():
            return {"success": True, "data": ""***REMOVED***

        files = sorted(
            [f for f in summaries_dir.iterdir() if f.name.endswith(".md")***REMOVED***,
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return {"success": True, "data": ""***REMOVED***

        try:
            content = files[0***REMOVED***.read_text(encoding="utf-8")
            return {"success": True, "data": content, "metadata": {"file": files[0***REMOVED***.name***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_plugins_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List loaded plugins."""
        try:
            from scripts.plugin_api import PluginRegistry, PluginLoader
            registry = PluginRegistry()
            loader = PluginLoader(registry)
            loader.load_all()
            state = registry.get_state()
            return {"success": True, "data": state***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Bridge Layer handlers ──────────────────────────────

    def _handle_bridge_connect(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Connect to an external MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"***REMOVED***

        transport = arguments.get("transport", "")
        name = arguments.get("name")

        try:
            if transport == "stdio":
                command = arguments.get("command", "")
                args_str = arguments.get("args", "")
                args_list = args_str.split() if args_str else [***REMOVED***

                if not command:
                    return {"success": False, "error": "command is required for stdio transport"***REMOVED***

                result = bridge.connect_mcp_stdio(
                    command=command,
                    args=args_list,
                    cwd=str(self.workspace),
                    name=name,
                )
                self._publish("bridge.connected", {"transport": "stdio", "server": result.get("server", command), "tools": result.get("tools", 0)***REMOVED***)
                return result

            elif transport == "http":
                endpoint = arguments.get("endpoint", "")
                if not endpoint:
                    return {"success": False, "error": "endpoint is required for http transport"***REMOVED***

                result = bridge.connect_mcp_http(
                    endpoint=endpoint,
                    name=name,
                )
                self._publish("bridge.connected", {"transport": "http", "server": result.get("server", endpoint), "tools": result.get("tools", 0)***REMOVED***)
                return result

            else:
                return {"success": False, "error": f"Unknown transport: {transport***REMOVED***. Use 'stdio' or 'http'."***REMOVED***

        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_bridge_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List connected MCP servers."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"***REMOVED***

        servers = bridge.list_mcp_servers()
        return {
            "success": True,
            "data": {
                "servers": servers,
                "total": len(servers),
            ***REMOVED***,
        ***REMOVED***

    def _handle_bridge_disconnect(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Disconnect an MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"***REMOVED***

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"***REMOVED***

        ok = bridge.disconnect_mcp(name)
        self._publish("bridge.disconnected", {"server": name, "success": ok***REMOVED***)
        return {
            "success": ok,
            "data": {"disconnected": ok, "server": name***REMOVED***,
            "error": None if ok else f"Server not found: {name***REMOVED***",
        ***REMOVED***

    def _handle_bridge_rpc(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Send JSON-RPC to a connected MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"***REMOVED***

        server_name = arguments.get("server", "")
        method = arguments.get("method", "")

        if not server_name:
            return {"success": False, "error": "server is required"***REMOVED***
        if not method:
            return {"success": False, "error": "method is required"***REMOVED***

        # Build params based on method
        if method == "tools/call":
            tool = arguments.get("tool", "")
            args_str = arguments.get("arguments", "{***REMOVED***")
            try:
                args_dict = json.loads(args_str)
            except json.JSONDecodeError:
                args_dict = {***REMOVED***

            params = {"name": tool, "arguments": args_dict***REMOVED***
        else:
            params = {***REMOVED***

        result = bridge._rpc_to_server(server_name, method, params)
        self._publish("bridge.rpc", {"server": server_name, "method": method, "success": result.get("success", False)***REMOVED***)
        return result

    # ── Bootstrap Engine handlers ──────────────────────────

    def _handle_bootstrap_check(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Check environment state via Bootstrap Engine."""
        engine = self._get_bootstrap_engine()
        if engine is None:
            return {"success": False, "error": "BootstrapEngine not available"***REMOVED***

        try:
            quick = arguments.get("quick", False)
            if quick:
                env = engine._checker.check_quick()
            else:
                env = engine.check()

            self._publish("bootstrap.checked", {"quick": quick, "os": env.os_type***REMOVED***)

            return {
                "success": True,
                "data": {
                    "os": env.os_type,
                    "is_termux": env.is_termux,
                    "python_version": env.python_version,
                    "node_version": env.node_version,
                    "git_available": env.git_available,
                    "disk_free_gb": env.disk_free_gb,
                    "ram_total_mb": env.ram_total_mb,
                    "ram_available_mb": env.ram_available_mb,
                    "pip_packages": len(env.pip_packages),
                    "has_git": env.has_git,
                    "has_env_file": env.has_env_file,
                    "workspace": env.workspace,
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_bootstrap_run(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Run full bootstrap cycle."""
        profile = arguments.get("profile", "minimal")

        try:
            from freebuff_plugin import BootstrapEngine
            bus = self._get_event_bus()
            engine = BootstrapEngine(
                workspace_root=str(self.workspace),
                profile=profile,
                event_bus=bus or None,
            )
            report = engine.run()

            self._publish("bootstrap.ran", {
                "profile": profile,
                "success": report.success,
                "duration_ms": report.duration_ms,
                "steps": len(report.steps),
            ***REMOVED***)

            return {
                "success": report.success,
                "data": {
                    "profile": report.profile,
                    "duration_ms": report.duration_ms,
                    "steps": [
                        {
                            "name": s.name,
                            "status": s.status,
                            "duration_ms": s.duration_ms,
                            "error": s.error,
                        ***REMOVED***
                        for s in report.steps
                    ***REMOVED***,
                    "warnings": report.warnings[:10***REMOVED***,
                    "errors": report.errors[:10***REMOVED***,
                    "diagnosis": {
                        "health_score": report.diagnosis.health_score if report.diagnosis else None,
                        "path_issues": report.diagnosis.path_issues if report.diagnosis else [***REMOVED***,
                        "runtime_issues": report.diagnosis.runtime_issues if report.diagnosis else [***REMOVED***,
                        "dependency_issues": report.diagnosis.dependency_issues if report.diagnosis else [***REMOVED***,
                        "key_issues": report.diagnosis.key_issues if report.diagnosis else [***REMOVED***,
                    ***REMOVED*** if report.diagnosis else None,
                    "environment": {
                        "os": report.environment.os_type if report.environment else "unknown",
                        "python": report.environment.python_version if report.environment else "",
                        "git": report.environment.git_available if report.environment else False,
                    ***REMOVED*** if report.environment else None,
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_bootstrap_status(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Get bootstrap status."""
        engine = self._get_bootstrap_engine()
        if engine is None:
            return {"success": False, "error": "BootstrapEngine not available"***REMOVED***

        try:
            status = engine.get_status()
            return {
                "success": True,
                "data": status,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    # ── Runtime Abstraction Layer handlers ─────────────────

    def _handle_runtime_list(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """List discovered runtimes and active runtime."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"***REMOVED***

        try:
            status = registry.get_status()
            self._publish("runtime.listed", {"total": status.get("total", 0), "active": status.get("active")***REMOVED***)
            return {"success": True, "data": status***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_runtime_connect(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Connect to a runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"***REMOVED***

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"***REMOVED***

        try:
            ok, msg = registry.connect(name)
            self._publish("runtime.connected", {"runtime": name, "success": ok, "message": msg***REMOVED***)
            return {"success": ok, "data": {"runtime": name, "connected": ok, "message": msg***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_runtime_disconnect(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Disconnect a runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"***REMOVED***

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"***REMOVED***

        try:
            ok = registry.disconnect(name)
            self._publish("runtime.disconnected", {"runtime": name, "success": ok***REMOVED***)
            return {"success": ok, "data": {"runtime": name, "disconnected": ok***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_runtime_select(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Set active runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"***REMOVED***

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"***REMOVED***

        try:
            ok = registry.set_active(name)
            if not ok:
                return {"success": False, "error": f"Runtime not registered: {name***REMOVED***"***REMOVED***
            self._publish("runtime.selected", {"runtime": name***REMOVED***)
            return {"success": True, "data": {"runtime": name, "active": True***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_runtime_generate(self, arguments: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Generate a response from a runtime."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"***REMOVED***

        capability = arguments.get("capability")
        explicit_name = arguments.get("name")
        prompt = arguments.get("prompt", "")
        messages = arguments.get("messages")
        system = arguments.get("system")
        try:
            temperature = float(arguments.get("temperature", 0.7))
        except (TypeError, ValueError):
            return {"success": False, "error": "temperature must be a number"***REMOVED***
        max_tokens = arguments.get("max_tokens")
        if max_tokens is not None:
            try:
                max_tokens = int(max_tokens)
                if max_tokens <= 0:
                    return {"success": False, "error": "max_tokens must be positive"***REMOVED***
            except (TypeError, ValueError):
                return {"success": False, "error": "max_tokens must be an integer"***REMOVED***

        # Build and validate messages list
        if messages is None:
            if not prompt:
                return {"success": False, "error": "prompt or messages is required"***REMOVED***
            messages = [{"role": "user", "content": prompt***REMOVED******REMOVED***
        elif not isinstance(messages, list) or not all(
            isinstance(m, dict) and "role" in m and "content" in m for m in messages
        ):
            return {"success": False, "error": "messages must be a list of dicts with role and content"***REMOVED***

        # Determine target runtime
        runtime_name = None
        if explicit_name:
            runtime_name = explicit_name
        elif capability:
            policy_engine = self._get_policy_engine()
            if policy_engine is not None:
                runtime_name = policy_engine.select_runtime(capability)
            if runtime_name is None:
                cap_reg = self._runtime_capability_registry
                if cap_reg is None:
                    return {"success": False, "error": "RuntimeCapabilityRegistry not available"***REMOVED***
                best = cap_reg.get_runtime_for_capability(capability)
                if best is None:
                    return {"success": False, "error": f"No runtime available for capability: {capability***REMOVED***"***REMOVED***
                runtime_name = best["runtime"***REMOVED***
            if registry.get(runtime_name) is None:
                return {"success": False, "error": f"Runtime selected for capability is not registered: {runtime_name***REMOVED***"***REMOVED***
        else:
            active = registry.get_active()
            if active is None:
                return {"success": False, "error": "No active runtime. Use runtime_select or provide name/capability."***REMOVED***
            runtime_name = active.name

        if not runtime_name or not isinstance(runtime_name, str):
            return {"success": False, "error": "Could not determine target runtime"***REMOVED***

        # Ensure connected
        adapter = registry.get_adapter(runtime_name)
        if adapter is None or not adapter.is_connected():
            ok, msg = registry.connect(runtime_name)
            if not ok:
                return {"success": False, "error": f"Could not connect to runtime {runtime_name***REMOVED***: {msg***REMOVED***"***REMOVED***
            adapter = registry.get_adapter(runtime_name)
            if adapter is None:
                return {"success": False, "error": f"Runtime adapter unavailable after connect: {runtime_name***REMOVED***"***REMOVED***

        try:
            result = adapter.generate(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._publish("runtime.generated", {
                "runtime": runtime_name,
                "success": result.error is None,
                "model_used": result.model_used,
            ***REMOVED***)
            if result.error:
                return {"success": False, "error": result.error, "data": {"runtime": runtime_name***REMOVED******REMOVED***
            return {
                "success": True,
                "data": {
                    "runtime": runtime_name,
                    "content": result.content,
                    "model_used": result.model_used,
                    "provider_used": result.provider_used,
                    "latency_ms": result.latency_ms,
                    "usage": result.usage,
                    "finish_reason": result.finish_reason,
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e), "data": {"runtime": runtime_name***REMOVED******REMOVED***

    # ── MCP protocol handlers ──────────────────────────────

    def handle_initialize(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle initialize request."""
        self._client_info = params.get("clientInfo", {***REMOVED***)
        self._initialized = True

        self._publish("server.initialized", {
            "client": self._client_info.get("name", "unknown"),
            "protocol_version": PROTOCOL_VERSION,
        ***REMOVED***)

        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            ***REMOVED***,
            "capabilities": {
                "tools": {"listChanged": True***REMOVED***,
                "resources": {"listChanged": True, "subscribe": False***REMOVED***,
                "prompts": {"listChanged": True***REMOVED***,
            ***REMOVED***,
        ***REMOVED***

    def handle_tools_list(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle tools/list request."""
        tools = [***REMOVED***
        for name, tool in sorted(self._tools.items()):
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            ***REMOVED***)
        return {"tools": tools***REMOVED***

    def handle_tools_call(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle tools/call request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {***REMOVED***)

        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name***REMOVED***")

        if tool.handler is None:
            raise ValueError(f"Tool has no handler: {name***REMOVED***")

        try:
            result = tool.handler(arguments)
        except Exception as e:
            # Tool handler raised — return MCP tool error (not protocol error)
            return {
                "content": [{"type": "text", "text": json.dumps(
                    {"success": False, "error": str(e)***REMOVED***, ensure_ascii=False,
                )***REMOVED******REMOVED***,
                "isError": True,
            ***REMOVED***

        # MCP expects content array with TextContent
        if isinstance(result, dict):
            content_text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            content_text = str(result)

        return {
            "content": [{"type": "text", "text": content_text***REMOVED******REMOVED***,
            "isError": isinstance(result, dict) and not result.get("success", True),
        ***REMOVED***

    def handle_resources_list(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle resources/list request."""
        resources = [***REMOVED***
        for uri, res in sorted(self._resources.items()):
            resources.append({
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "mimeType": res.mime_type,
            ***REMOVED***)
        return {"resources": resources***REMOVED***

    def handle_resources_read(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle resources/read request."""
        uri = params.get("uri", "")
        res = self._resources.get(uri)

        if res is None:
            # Try pattern matching for dynamic URIs
            if uri.startswith("buffy://knowledge/"):
                res = self._resources.get("buffy://knowledge")
            elif uri.startswith("buffy://memory/"):
                res = self._resources.get("buffy://memory")

        if res is None or res.handler is None:
            raise ValueError(f"Unknown resource: {uri***REMOVED***")

        content, mime_type = res.handler(uri)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": mime_type,
                    "text": content,
                ***REMOVED***
            ***REMOVED***
        ***REMOVED***

    def handle_prompts_list(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle prompts/list request."""
        prompts = [***REMOVED***
        for name, p in sorted(self._prompts.items()):
            prompts.append({
                "name": p.name,
                "description": p.description,
                "arguments": p.arguments,
            ***REMOVED***)
        return {"prompts": prompts***REMOVED***

    def handle_prompts_get(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Handle prompts/get request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {***REMOVED***)

        prompt = self._prompts.get(name)
        if prompt is None:
            raise ValueError(f"Unknown prompt: {name***REMOVED***")

        if prompt.handler:
            text = prompt.handler(arguments)
        else:
            text = prompt.description

        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": text***REMOVED***,
                ***REMOVED***
            ***REMOVED***,
        ***REMOVED***

    # ── JSON-RPC message dispatch ──────────────────────────

    def dispatch(self, message: Dict[str, Any***REMOVED***) -> Optional[str***REMOVED***:
        """Dispatch a JSON-RPC message and return response (or None for notifications).

        Args:
            message: parsed JSON-RPC message

        Returns:
            JSON response string, or None for notifications
        """
        req_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {***REMOVED***)

        # Notifications (no id) — don't send response
        is_notification = req_id is None

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "notifications/initialized":
                # Client signals readiness — no response needed
                return None

            elif method == "ping":
                return rpc_response(req_id, {***REMOVED***) if not is_notification else None

            elif method == "tools/list":
                result = self.handle_tools_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "tools/call":
                result = self.handle_tools_call(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/list":
                result = self.handle_resources_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/read":
                result = self.handle_resources_read(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/templates/list":
                # Return empty list (no URI templates for now)
                return rpc_response(req_id, {"resourceTemplates": [***REMOVED******REMOVED***) if not is_notification else None

            elif method == "prompts/list":
                result = self.handle_prompts_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "prompts/get":
                result = self.handle_prompts_get(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "logging/setLevel":
                # Accept any log level, no response data needed
                return rpc_response(req_id, {***REMOVED***) if not is_notification else None

            elif method == "shutdown":
                # MCP shutdown — signal readiness to stop (no actual exit here)
                self._publish("server.shutdown", {***REMOVED***)
                return rpc_response(req_id, {***REMOVED***) if not is_notification else None

            else:
                if is_notification:
                    return None
                return rpc_error(req_id, METHOD_NOT_FOUND, f"Method not found: {method***REMOVED***")

        except ValueError as e:
            if is_notification:
                return None
            return rpc_error(req_id, INVALID_PARAMS, str(e))
        except Exception as e:
            if is_notification:
                return None
            trace = traceback.format_exc()[:500***REMOVED***
            return rpc_error(req_id, INTERNAL_ERROR, str(e), {"trace": trace***REMOVED***)

    # ── stdio transport ─────────────────────────────────────

    async def run_stdio(self) -> None:
        """Run MCP server over stdio transport.

        Reads JSON-RPC messages from stdin (one per line),
        writes responses to stdout.
        """
        # Ensure stdout is line-buffered
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break  # EOF

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                # Parse JSON-RPC message
                try:
                    message = json.loads(line_str)
                except json.JSONDecodeError as e:
                    # Send parse error
                    sys.stdout.write(rpc_error(None, PARSE_ERROR, f"Parse error: {e***REMOVED***") + "\n")
                    sys.stdout.flush()
                    continue

                # Handle batch requests
                if isinstance(message, list):
                    responses = [***REMOVED***
                    for msg in message:
                        resp = self.dispatch(msg)
                        if resp:
                            responses.append(json.loads(resp))
                    if responses:
                        sys.stdout.write(json.dumps(responses, ensure_ascii=False) + "\n")
                        sys.stdout.flush()
                    continue

                # Single request
                response = self.dispatch(message)
                if response:
                    sys.stdout.write(response + "\n")
                    sys.stdout.flush()

            except Exception as e:
                print(f"⚠️ MCP server error: {e***REMOVED***", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def run_sync(self) -> None:
        """Run MCP server synchronously (blocking, line-by-line stdin)."""
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                sys.stdout.write(rpc_error(None, PARSE_ERROR, f"Parse error: {e***REMOVED***") + "\n")
                sys.stdout.flush()
                continue

            # Batch request
            if isinstance(message, list):
                responses = [***REMOVED***
                for msg in message:
                    resp = self.dispatch(msg)
                    if resp:
                        responses.append(json.loads(resp))
                if responses:
                    sys.stdout.write(json.dumps(responses, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                continue

            response = self.dispatch(message)
            if response:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()

    # ── Status / introspection ─────────────────────────────

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Return server status for CLI."""
        return {
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "protocol": PROTOCOL_VERSION,
            "workspace": str(self.workspace),
            "initialized": self._initialized,
            "tools": len(self._tools),
            "resources": len(self._resources),
            "prompts": len(self._prompts),
            "tool_names": sorted(self._tools.keys()),
            "resource_uris": sorted(self._resources.keys()),
            "prompt_names": sorted(self._prompts.keys()),
        ***REMOVED***

    def list_tools_info(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """List all tools with full info (for CLI)."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "input_schema": t.input_schema,
            ***REMOVED***
            for t in sorted(self._tools.values(), key=lambda x: x.name)
        ***REMOVED***

    def list_resources_info(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """List all resources with full info (for CLI)."""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mime_type": r.mime_type,
            ***REMOVED***
            for r in sorted(self._resources.values(), key=lambda x: x.uri)
        ***REMOVED***

    # ── Streamable HTTP transport ──────────────────────────

    def run_http(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Run MCP server over Streamable HTTP transport.

        Single endpoint /mcp:
        - POST: JSON-RPC requests (application/json response)
        - GET: SSE notification stream (text/event-stream)
        - DELETE: session termination (204 No Content)

        Session management via Mcp-Session-Id header.
        Spec: MCP 2025-03-26 Streamable HTTP transport.
        """
        session_manager = McpSessionManager()
        httpd = McpHttpServer(
            (host, port),
            McpHTTPRequestHandler,
            self,
            session_manager,
        )
        print(f"🌐 MCP HTTP Server: http://{host***REMOVED***:{port***REMOVED***/mcp", file=sys.stderr)
        print(f"   Protocol: {PROTOCOL_VERSION***REMOVED***", file=sys.stderr)
        print(f"   Tools: {len(self._tools)***REMOVED*** | Resources: {len(self._resources)***REMOVED*** | Prompts: {len(self._prompts)***REMOVED***", file=sys.stderr)
        print(f"   Press Ctrl+C to stop", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...", file=sys.stderr)
        finally:
            httpd.shutdown()


# ═══════════════════════════════════════════════════════════════
# Streamable HTTP Transport (MCP 2025-03-26)
# ═══════════════════════════════════════════════════════════════


class McpHttpServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with BuffyMcpServer and session manager."""

    daemon_threads = True

    def __init__(self, server_addr, handler_class,
                 mcp_server: "BuffyMcpServer",
                 session_manager: McpSessionManager):
        super().__init__(server_addr, handler_class)
        self.mcp_server = mcp_server
        self.session_manager = session_manager


class McpHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP Streamable HTTP transport.

    Single endpoint /mcp:
    - POST: JSON-RPC requests → application/json, or 202 for notifications
    - GET: SSE stream (text/event-stream) for server-to-client notifications
    - DELETE: session termination (204 No Content)

    Session management via Mcp-Session-Id header (assigned on initialize).
    Mcp-Protocol-Version header included in all responses.
    """

    server_version = "BuffyMCP/1.0"
    protocol_version = "HTTP/1.1"  # needed for keep-alive / SSE

    @property
    def _mcp(self) -> "BuffyMcpServer":
        return self.server.mcp_server

    @property
    def _sessions(self) -> McpSessionManager:
        return self.server.session_manager

    # ── Response helpers ───────────────────────────────────

    def _send_json(self, status: int, body: str,
                   extra_headers: Optional[Dict[str, str***REMOVED******REMOVED*** = None) -> None:
        """Send a JSON HTTP response."""
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _send_status(self, status: int,
                     extra_headers: Optional[Dict[str, str***REMOVED******REMOVED*** = None) -> None:
        """Send a status-only response (no body).

        Per RFC 7230 §3.3.2, 204 responses MUST NOT include Content-Length.
        """
        self.send_response(status)
        if status != 204:
            self.send_header("Content-Length", "0")
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()

    def _send_error_json(self, status: int, code: int, message: str) -> None:
        """Send an HTTP error with JSON-RPC error body."""
        self._send_json(status, rpc_error(None, code, message))

    def _validate_origin(self) -> bool:
        """Validate Origin header to prevent DNS rebinding attacks.

        Per MCP 2025-03-26 spec, servers MUST validate the Origin header.
        Allows: no Origin (non-browser clients), localhost, 127.0.0.1.
        Uses urlparse to prevent bypass via e.g. http://localhost.evil.com.
        """
        from urllib.parse import urlparse

        origin = self.headers.get("Origin")
        if origin is None:
            return True  # Non-browser clients (curl, CLI) don't send Origin
        try:
            parsed = urlparse(origin)
            return parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")
        except Exception:
            return False

    # ── POST: JSON-RPC requests ────────────────────────────

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path***REMOVED***")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            message = json.loads(raw_body)
        except json.JSONDecodeError as e:
            self._send_error_json(400, PARSE_ERROR, f"Parse error: {e***REMOVED***")
            return

        # initialize → create new session, return Mcp-Session-Id
        if isinstance(message, dict) and message.get("method") == "initialize":
            session_id = self._sessions.create_session()
            response = self._mcp.dispatch(message)
            if response:
                self._send_json(200, response, {"Mcp-Session-Id": session_id***REMOVED***)
            else:
                self._send_status(202, {"Mcp-Session-Id": session_id***REMOVED***)
            return

        # Non-initialize POSTs require valid Mcp-Session-Id
        session_id = self.headers.get("Mcp-Session-Id")
        if session_id and not self._sessions.get_session(session_id):
            self._send_error_json(404, INVALID_REQUEST, "Session not found")
            return

        # Batch request
        if isinstance(message, list):
            responses = [***REMOVED***
            for msg in message:
                resp = self._mcp.dispatch(msg)
                if resp:
                    responses.append(json.loads(resp))
            if responses:
                self._send_json(200, json.dumps(responses, ensure_ascii=False))
            else:
                self._send_status(202)
            return

        # Single message
        is_notification = message.get("id") is None
        response = self._mcp.dispatch(message)

        if is_notification or response is None:
            self._send_status(202)
        else:
            self._send_json(200, response)

    # ── GET: SSE notification stream ────────────────────────

    def do_GET(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path***REMOVED***")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id:
            self._send_error_json(400, INVALID_REQUEST, "Mcp-Session-Id required for GET")
            return

        session = self._sessions.get_session(session_id)
        if not session:
            self._send_error_json(404, INVALID_REQUEST, "Session not found")
            return

        # Open SSE stream
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        self.end_headers()

        try:
            while session.active:
                try:
                    msg = session.notification_queue.get(timeout=30)
                    self.wfile.write(f"data: {msg***REMOVED***\n\n".encode("utf-8"))
                    self.wfile.flush()
                except Empty:
                    # Heartbeat to keep connection alive
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Client disconnected

    # ── DELETE: session termination ─────────────────────────

    def do_DELETE(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path***REMOVED***")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id:
            self._send_error_json(400, INVALID_REQUEST, "Mcp-Session-Id required")
            return

        if self._sessions.delete_session(session_id):
            self._send_status(204)
        else:
            self._send_error_json(404, INVALID_REQUEST, "Session not found")

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Server для Buffy Project — Model Context Protocol (stdio + Streamable HTTP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Claude integration (claude_desktop_config.json) — stdio:
  {
    "mcpServers": {
      "buffy": {
        "command": "python",
        "args": ["scripts/mcp_server.py"***REMOVED***
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***

HTTP integration (Streamable HTTP transport):
  python scripts/mcp_server.py --http --port 8765
  Endpoint: http://127.0.0.1:8765/mcp
  POST: JSON-RPC, GET: SSE stream, DELETE: session

Examples:
  python scripts/mcp_server.py                  # stdio MCP server
  python scripts/mcp_server.py --http           # HTTP MCP server (port 8765)
  python scripts/mcp_server.py --status         # server status
  python scripts/mcp_server.py --tools          # list MCP tools
  python scripts/mcp_server.py --resources      # list MCP resources
  python scripts/mcp_server.py --call knowledge_search '{"query": "router"***REMOVED***'
        """,
    )
    parser.add_argument("--status", action="store_true", help="Show server status")
    parser.add_argument("--tools", action="store_true", help="List all MCP tools")
    parser.add_argument("--resources", action="store_true", help="List all MCP resources")
    parser.add_argument("--prompts", action="store_true", help="List all MCP prompts")
    parser.add_argument("--call", nargs=2, metavar=("TOOL", "ARGS"), help="Call a tool directly")
    parser.add_argument("--read", metavar="URI", help="Read a resource directly")
    parser.add_argument("--async-mode", dest="async_mode", action="store_true", help="Use async stdio transport")
    parser.add_argument("--http", action="store_true", help="Run Streamable HTTP server (POST/GET/DELETE at /mcp)")
    parser.add_argument("--fastapi", action="store_true", help="Run FastAPI server (requires fastapi+uvicorn)")
    parser.add_argument("--tunnel", action="store_true", help="Start Cloudflare Tunnel (requires --fastapi)")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP server port (default: 8765)")

    args = parser.parse_args()

    server = BuffyMcpServer()

    if args.status:
        status = server.get_status()
        print(f"📊 MCP SERVER STATUS")
        print(f"   Server:     {status['server'***REMOVED******REMOVED*** v{status['version'***REMOVED******REMOVED***")
        print(f"   Protocol:   {status['protocol'***REMOVED******REMOVED***")
        print(f"   Workspace:  {status['workspace'***REMOVED******REMOVED***")
        print(f"   Tools:      {status['tools'***REMOVED******REMOVED***")
        print(f"   Resources:  {status['resources'***REMOVED******REMOVED***")
        print(f"   Prompts:    {status['prompts'***REMOVED******REMOVED***")
        print(f"\n   Tool names: {', '.join(status['tool_names'***REMOVED***)***REMOVED***")
        print(f"   Resources:  {', '.join(status['resource_uris'***REMOVED***)***REMOVED***")
        print(f"   Prompts:    {', '.join(status['prompt_names'***REMOVED***)***REMOVED***")

    elif args.tools:
        tools = server.list_tools_info()
        print(f"🔧 MCP TOOLS ({len(tools)***REMOVED***):")
        for t in tools:
            print(f"\n  {t['name'***REMOVED******REMOVED*** [{t['category'***REMOVED******REMOVED******REMOVED***")
            print(f"    {t['description'***REMOVED***[:100***REMOVED******REMOVED***")
            props = t['input_schema'***REMOVED***.get('properties', {***REMOVED***)
            required = t['input_schema'***REMOVED***.get('required', [***REMOVED***)
            for pname, pschema in props.items():
                req = "*" if pname in required else ""
                ptype = pschema.get('type', 'any')
                desc = pschema.get('description', '')[:60***REMOVED***
                print(f"    - {pname***REMOVED***{req***REMOVED*** ({ptype***REMOVED***): {desc***REMOVED***")

    elif args.resources:
        resources = server.list_resources_info()
        print(f"📄 MCP RESOURCES ({len(resources)***REMOVED***):")
        for r in resources:
            print(f"\n  {r['uri'***REMOVED******REMOVED***")
            print(f"    {r['name'***REMOVED******REMOVED***: {r['description'***REMOVED***[:100***REMOVED******REMOVED***")
            print(f"    mime: {r['mime_type'***REMOVED******REMOVED***")

    elif args.prompts:
        print(f"💬 MCP PROMPTS ({len(server._prompts)***REMOVED***):")
        for name, p in sorted(server._prompts.items()):
            print(f"\n  {p.name***REMOVED***")
            print(f"    {p.description[:100***REMOVED******REMOVED***")
            for arg in p.arguments:
                req = "*" if arg.get("required") else ""
                print(f"    - {arg['name'***REMOVED******REMOVED***{req***REMOVED***: {arg.get('description', '')[:60***REMOVED******REMOVED***")

    elif args.call:
        tool_name, args_str = args.call
        try:
            arguments = json.loads(args_str)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON args: {e***REMOVED***")
            return
        result = server.handle_tools_call({"name": tool_name, "arguments": arguments***REMOVED***)
        if result.get("isError"):
            print(f"❌ Tool error")
        else:
            print(f"✅ Tool result")
        for content in result.get("content", [***REMOVED***):
            print(content.get("text", ""))

    elif args.read:
        try:
            result = server.handle_resources_read({"uri": args.read***REMOVED***)
            for content in result.get("contents", [***REMOVED***):
                print(content.get("text", ""))
        except ValueError as e:
            print(f"❌ {e***REMOVED***")

    else:
        # Default: run MCP server
        if args.tunnel and not args.fastapi:
            print("⚠️  --tunnel requires --fastapi", file=sys.stderr)
            sys.exit(1)
        if args.fastapi:
            try:
                from scripts.mcp_fastapi import main as fastapi_main
                sys.argv = [sys.argv[0***REMOVED***, "--host", args.host, "--port", str(args.port)***REMOVED***
                if args.tunnel:
                    sys.argv.append("--tunnel")
                fastapi_main()
            except ImportError:
                print("❌ FastAPI not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
                sys.exit(1)
        elif args.http:
            server.run_http(host=args.host, port=args.port)
        elif args.async_mode:
            asyncio.run(server.run_stdio())
        else:
            server.run_sync()


if __name__ == "__main__":
    main()
