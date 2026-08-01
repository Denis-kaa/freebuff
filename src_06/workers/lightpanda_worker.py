#!/usr/bin/env python3
"""
Lightpanda Worker — headless browser automation for freebuff.

Wraps the Lightpanda binary running inside Termux + proot-distro Ubuntu.
Provides a Python API for:
  - Agent Mode tasks
  - Running PandaScript files
  - Dumping page content
  - Serving CDP server for Puppeteer/Playwright

Usage:
    from src_06.workers.lightpanda_worker import LightpandaWorker
    worker = LightpandaWorker()
    result = worker.dump_url("https://example.com", format="markdown")
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass
***REMOVED***
from typing import Any, Dict, List, Optional


@dataclass
class LightpandaResult:
    """Result of a Lightpanda worker operation."""
    success: bool
    data: str = ""
    error: Optional[str***REMOVED*** = None
    command: str = ""
    duration_ms: float = 0.0


class LightpandaWorker:
    """Python interface to the Lightpanda headless browser."""

    def __init__(
        self,
        binary_path: Optional[str***REMOVED*** = None,
        workspace_root: Optional[str***REMOVED*** = None,
    ) -> None:
        self._workspace_root = Path(workspace_root or str(Path(__file__).resolve().parent.parent.parent))
        self._binary_path = self._resolve_binary(binary_path)
        self._cdp_process: Optional[subprocess.Popen***REMOVED*** = None

    def _resolve_binary(self, override: Optional[str***REMOVED***) -> str:
        if override:
            return override

        # 1. Installed wrapper from scripts_01/install_lightpanda.sh
        wrapper = self._workspace_root / ".tools" / "lightpanda"
        if wrapper.exists():
            return str(wrapper)

        # 2. Direct binary if running inside proot/Ubuntu
        if shutil.which("lightpanda"):
            return "lightpanda"

        # 3. Fallback absolute path inside proot-distro
        return "/usr/local/bin/lightpanda"

    def _run(
        self,
        args: List[str***REMOVED***,
        timeout: int = 60,
        env: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
    ) -> LightpandaResult:
        """Run Lightpanda with the given arguments and return a LightpandaResult."""
        cmd = [self._binary_path, *args***REMOVED***
        cmd_str = " ".join(shlex.quote(str(x)) for x in cmd)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **(env or {***REMOVED***)***REMOVED***,
            )

            output = result.stdout or ""
            stderr = result.stderr or ""
            success = result.returncode == 0

            return LightpandaResult(
                success=success,
                data=output if success else stderr,
                error=None if success else f"Exit code {result.returncode***REMOVED***: {stderr[:500***REMOVED******REMOVED***",
                command=cmd_str,
            )
        except subprocess.TimeoutExpired:
            return LightpandaResult(
                success=False,
                data="",
                error=f"Lightpanda timed out after {timeout***REMOVED***s",
                command=cmd_str,
            )
        except FileNotFoundError:
            return LightpandaResult(
                success=False,
                data="",
                error=f"Lightpanda binary not found: {self._binary_path***REMOVED***. Run scripts_01/install_lightpanda.sh",
                command=cmd_str,
            )
        except Exception as e:
            return LightpandaResult(
                success=False,
                data="",
                error=str(e),
                command=cmd_str,
            )

    # ── Public API ─────────────────────────────────────────────

    def execute_agent_task(self, task: str, provider: str = "ollama", timeout: int = 120) -> LightpandaResult:
        """Run Lightpanda in Agent Mode for the given task.

        Args:
            task: natural-language task description
            provider: LLM provider (ollama, openai, anthropic, gemini)
            timeout: max seconds to wait
        """
        if not task:
            return LightpandaResult(success=False, error="Task cannot be empty")

        args = [
            "agent",
            "--provider", provider,
            "--task", task,
        ***REMOVED***
        return self._run(args, timeout=timeout)

    def run_script(self, script_path: str, timeout: int = 60) -> LightpandaResult:
        """Execute a saved PandaScript file.

        Args:
            script_path: path to the .js PandaScript
            timeout: max seconds to wait
        """
        if not os.path.isfile(script_path):
            return LightpandaResult(success=False, error=f"PandaScript not found: {script_path***REMOVED***")

        return self._run(["agent", script_path***REMOVED***, timeout=timeout)

    def dump_url(
        self,
        url: str,
        output_format: str = "markdown",
        timeout: int = 60,
    ) -> LightpandaResult:
        """Dump the content of a URL.

        Args:
            url: target URL
            output_format: output format (markdown, html, text)
            timeout: max seconds to wait
        """
        if not url:
            return LightpandaResult(success=False, error="URL cannot be empty")

        supported = {"markdown", "html", "text"***REMOVED***
        if output_format not in supported:
            return LightpandaResult(
                success=False,
                error=f"Unsupported output format '{output_format***REMOVED***'. Supported: {supported***REMOVED***",
            )

        # Lightpanda doesn't have a native 'dump' subcommand yet, so we fall back
        # to running a small inline PandaScript that loads the page and prints
        # the requested format. This keeps the worker functional even before
        # the command lands upstream.
        script = f"""
const url = {shlex.quote(url)***REMOVED***;
const format = {shlex.quote(output_format)***REMOVED***;
const res = await fetch(url);
const text = await res.text();
if (format === 'html') {{
    console.log(text);
***REMOVED******REMOVED*** else {{
    const body = text.replace(/<[^>***REMOVED***+>/g, ' ').replace(/\\s+/g, ' ').trim();
    console.log(body);
***REMOVED******REMOVED***
"""
        return self._run(["agent", "-e", script***REMOVED***, timeout=timeout)

    def serve_cdp(self, host: str = "127.0.0.1", port: int = 9222) -> LightpandaResult:
        """Start the Lightpanda CDP server.

        This launches a background process. Use stop_cdp() to terminate it.
        """
        if self._cdp_process is not None:
            return LightpandaResult(success=False, error="CDP server is already running")

        cmd = [self._binary_path, "serve", "--host", host, "--port", str(port)***REMOVED***
        try:
            self._cdp_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return LightpandaResult(
                success=True,
                data=f"CDP server started on {host***REMOVED***:{port***REMOVED***",
                command=" ".join(shlex.quote(str(x)) for x in cmd),
            )
        except FileNotFoundError:
            return LightpandaResult(
                success=False,
                error=f"Lightpanda binary not found: {self._binary_path***REMOVED***",
                command=" ".join(shlex.quote(str(x)) for x in cmd),
            )
        except Exception as e:
            return LightpandaResult(success=False, error=str(e), command=" ".join(shlex.quote(str(x)) for x in cmd))

    def stop_cdp(self) -> LightpandaResult:
        """Stop the background CDP server."""
        if self._cdp_process is None:
            return LightpandaResult(success=False, error="CDP server is not running")

        try:
            self._cdp_process.terminate()
            self._cdp_process.wait(timeout=5)
            self._cdp_process = None
            return LightpandaResult(success=True, data="CDP server stopped")
        except Exception as e:
            return LightpandaResult(success=False, error=str(e))
