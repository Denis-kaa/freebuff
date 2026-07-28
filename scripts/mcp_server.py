#!/usr/bin/env python3
"""
mcp_server.py — MCP Server для Buffy Project.

Model Context Protocol server на чистом Python (без внешних SDK).
Транспорт: stdio (JSON-RPC 2.0 over stdin/stdout).

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
  Claude config (claude_desktop_config.json):
    {
      "mcpServers": {
        "buffy": {
          "command": "python",
          "args": ["/path/to/freebuff/scripts/mcp_server.py"***REMOVED***
        ***REMOVED***
      ***REMOVED***
    ***REMOVED***

  OpenClaw / Gemini: аналогично через stdio transport.

Использование:
    python scripts/mcp_server.py                    # stdio режим
    python scripts/mcp_server.py --tools            # список MCP tools
    python scripts/mcp_server.py --resources        # список MCP resources
    python scripts/mcp_server.py --call knowledge_search '{"query": "router"***REMOVED***'
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Callable, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

PROTOCOL_VERSION = "2024-11-05"
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

        # Register all MCP capabilities
        self._register_tools()
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
            ("buffy://roadmap", "buffy_roadmap", "ROADMAP.md — project roadmap with 5 phases", "docs/ROADMAP.md"),
            ("buffy://spec", "buffy_spec", "SPEC.md — technical specification", "SPEC.md"),
            ("buffy://changelog", "buffy_changelog", "CHANGELOG.md — version history", "CHANGELOG.md"),
            ("buffy://task", "buffy_task", "TASK.md — current task", "TASK.md"),
            ("buffy://inventory", "buffy_inventory", "SYSTEM_INVENTORY.md — full component catalog", "docs/SYSTEM_INVENTORY.md"),
            ("buffy://decisions", "buffy_decisions", "DECISIONS.md — architecture decision records", "docs/DECISIONS.md"),
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


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Server для Buffy Project — Model Context Protocol over stdio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Claude integration (claude_desktop_config.json):
  {
    "mcpServers": {
      "buffy": {
        "command": "python",
        "args": ["scripts/mcp_server.py"***REMOVED***
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***

Examples:
  python scripts/mcp_server.py                  # stdio MCP server
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
        # Default: run stdio MCP server
        if args.async_mode:
            asyncio.run(server.run_stdio())
        else:
            server.run_sync()


if __name__ == "__main__":
    main()
