#!/usr/bin/env python3
"""
phone_control_mcp.py — Thin MCP tool-server wrapper for phone control.

Первый slicе pomt45_05 ([pompts_11/045_05_mcp_cloudflare_phone_control.md***REMOVED***(pompts_11/045_05_mcp_cloudflare_phone_control.md)):
MCP-сервер c тремя инструментами для локального API на телефоне
(`/send-sms`, `/get-contacts`, `/play-music`) + TunnelManager для
экспонирования API наружу через Cloudflare Tunnel (с fallback на
ngrok, если cloudflared недоступен).

Дизайн (валидирован thinker-with-files-gemini, пар. 2):
  - One file, тонкий wrapper, stdlib-only HTTP (urllib).
  - TunnelSpec dataclass + TunnelManager (`subprocess.Popen` argv-list,
    daemon thread читает stderr → regex URL → TunnelSpec).
  - BaseTool + 3 инструмента (send_sms / get_contacts / play_music).
    Каждый: JSON-схема (`required`+`isinstance`), handler, mocked payload.
  - PhoneControlMCP orchestrator: tools/list + tools/call, bearer gateway,
    origin allowlist. Env-driven config, безопасные defaults.
  - Грейсful degradation: cloudflared отсутствует → fallback на
    localhost-URL (без exit 1); exception в tool.execute() → safe envelope.

Безопасность:
  - argv subprocess (НЕ shell=True) — канарейки в test_subprocess_argv_no_shell.
  - Bearer-auth через hmac.compare_digest (constant-time, anti-timing-attack).
  - Origin check — comma-separated allowlist в env.
  - JSON-schema validation per tool (lightweight, без jsonschema-dep).

Эволюция (отложено):
  - Реальный Android-bridge (Tasker / Termux:API) — следующий slics.
  - Cloudflare Workers SSE-delivery — отдельный deploy-конфиг (Wrangler).

Использование:
    python scripts_01/phone_control_mcp.py serve --port 8765 --tunnel
    python scripts_01/phone_control_mcp.py tools-list
    python scripts_01/phone_control_mcp.py tools-call send_sms '{"to":"+1234","body":"hi"***REMOVED***'
"""
from __future__ import annotations

import argparse
import atexit
import hmac
import json
import os
***REMOVED***
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib ***REMOVED***quest as urlrequest
from urllib.error import HTTPError, URLError


# ═══════════════════════════════════════════════════════════════
# Конфигурация (env-driven, безопасные defaults)
# ═══════════════════════════════════════════════════════════════


def _env(name: str, default: str) -> str:
    """Читать env-переменную со значением по умолчанию."""
    return os.environ.get(name, default)


# Bearer token для MCP-уровня (НЕ путать с API-токеном локального телефона).
PHONE_MCP_TOKEN = _env("FREEBUFF_PHONE_MCP_TOKEN", "dev-token-change-me")
# Bearer token для локального API на телефоне (Tasker/Termux:API).
PHONE_API_TOKEN = _env("FREEBUFF_PHONE_API_TOKEN", "")
# Локальный API endpoint (host:port телефона, доступен через туннель).
PHONE_API_BASE = _env("FREEBUFF_PHONE_API_BASE", "http://127.0.0.1:8765")
# Cloudflared binary (для тестов подменяется через env на mock-скрипт).
PHONE_TUNNEL_BIN = _env("FREEBUFF_PHONE_TUNNEL_BIN", "cloudflared")
# Comma-separated Origin allowlist (или "*" — но это плохая практика).
PHONE_ORIGINS = tuple(s.strip() for s in _env("FREEBUFF_PHONE_ORIGINS", "*").split(",") if s.strip())
# Таймаут HTTP в секундах (короткий — это localhost API).
PHONE_HTTP_TIMEOUT_S = float(_env("FREEBUFF_PHONE_HTTP_TIMEOUT_S", "2.0"))
# URL ready timeout для tunnel (Cloudflare обычно <5s).
PHONE_TUNNEL_READY_S = float(_env("FREEBUFF_PHONE_TUNNEL_READY_S", "15.0"))


_CLOUDFLARE_URL_RE = re.compile(r"https?://[a-z0-9-***REMOVED***+\.trycloudflare\.com/?", re.IGNORECASE)
_NGROK_URL_RE = re.compile(r"https?://[a-z0-9-***REMOVED***+\.ngrok(?:-free)?\.app/?", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════
# TunnelSpec + TunnelManager
# ═══════════════════════════════════════════════════════════════


@dataclass
class TunnelSpec:
    """Спецификация живой туннель-сессии."""
    url: str                       # Публичный URL (https://*.trycloudflare.com или *.ngrok.app).
    port: int                      # Локальный порт, который пробрасывается.
    binary: str                    # Бинарь (cloudflared / ngrok / mock).
    process: subprocess.Popen      # Живой subprocess (для .terminate()).
    kind: str = "cloudflared"      # "cloudflared" | "ngrok" | "mock"
    started_at: float = field(default_factory=time.monotonic)


class TunnelManager:
    """Лайфцикл одного tunnel-subprocess.

    start_cloudflared() / start_ngrok() / start() — выбирают binary по типу;
    stop() — terminate() + wait(timeout).
    """

    def __init__(self, tunnel_bin: Optional[str***REMOVED*** = None, ready_timeout: Optional[float***REMOVED*** = None) -> None:
        self._bin = tunnel_bin or PHONE_TUNNEL_BIN
        self._ready_timeout = ready_timeout if ready_timeout is not None else PHONE_TUNNEL_READY_S
        self._spec: Optional[TunnelSpec***REMOVED*** = None
        self._reader_thread: Optional[threading.Thread***REMOVED*** = None
        # threading.Lock сериализует start()/stop() — закрывает race между
        # concurrent tunnel_up callers (reviewer hardening #1).
        self._lock = threading.Lock()

    @property
    def spec(self) -> Optional[TunnelSpec***REMOVED***:
        return self._spec

    @property
    def is_active(self) -> bool:
        return self._spec is not None and self._spec.process.poll() is None

    def start(self, port: int) -> TunnelSpec:
        """Запустить cloudflared; ngrok fallback если cloudflared отсутствует.

        Защищён self._lock: между check (is_active) и _spawn() — атомарный блок.
        Concurrent tunnel_up callers сериализуются; второй получает README-processed
        либо RuntimeError("already active") если первый уже дошёл до _spec.
        """
        with self._lock:
            if self.is_active:
                raise RuntimeError("tunnel already active — call stop() first")
            # Пробуем cloudflared argv-list.
            try:
                return self._spawn(self._bin, ["tunnel", "--url", f"http://localhost:{port***REMOVED***"***REMOVED***, port, "cloudflared")
            except FileNotFoundError:
                # Fallback на ngrok (только если явно указан PHONE_NGROK_BIN).
                ngrok_bin = _env("FREEBUFF_PHONE_NGROK_BIN", "")
                if not ngrok_bin:
                    raise
                return self._spawn(ngrok_bin, ["http", str(port)***REMOVED***, port, "ngrok")

    def _spawn(self, binary: str, argv: list[str***REMOVED***, port: int, kind: str) -> TunnelSpec:
        """Безопасный subprocess-старт (argv-list, NO shell=True).

        Также `start_new_session=True` (Linux: создаёт новый session via os.setsid)
        → cloudflared НЕ принадлежит process group родителя. Если родитель убит
        SIGKILL — subprocess переживёт (нужен отдельный cleanup-hook на уровне
        обёртки, например через mcp_fastapi lifecycle). hardening #2.
        """
        full_argv = [binary***REMOVED*** + argv
        # Subprocess с stdout=None / stderr=PIPE → читатель stderr в daemon-thread.
        # NB: shell=False — единственный безопасный путь; см. test_subprocess_argv_no_shell.
        # NB: start_new_session=True → см. test_popen_uses_start_new_session (regression).
        proc = subprocess.Popen(
            full_argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            shell=False,                # КРИТИЧНО: без shell-injection
            start_new_session=True,     # hardening #2: detach от process group родителя
            text=True,
            bufsize=1,
        )
        captured_url: dict[str, Optional[str***REMOVED******REMOVED*** = {"url": None***REMOVED***
        url_re = _NGROK_URL_RE if kind == "ngrok" else _CLOUDFLARE_URL_RE

        def _reader() -> None:
            """Daemon-reader: captures URL из stderr, затем terminate subprocess.

            Без post-URL drain (reviewer finding #4): жёстко terminate на parentе
            после URL captured → subprocess.Popen.stderr автоматически закрывается,
            pipe не buffer-block'ится. На mock-сценариях URL часто в первой строке;
            на реальном cloudflared — обычно в первых 5-10 строках.
            """
            assert proc.stderr is not None
            for line in proc.stderr:
                m = url_re.search(line)
                if m and captured_url["url"***REMOVED*** is None:
                    captured_url["url"***REMOVED*** = m.group(0).rstrip("/")
                    # Закрываем stderr-reader; parent main-loop увидит URL.
                    return
            # Если URL never matched — просто выходим, parent main-loop увидит timeout/poll().

        self._reader_thread = threading.Thread(target=_reader, name=f"tunnel-reader-{kind***REMOVED***", daemon=True)
        self._reader_thread.start()

        # Ждём готовности URL с таймаутом.
        deadline = time.monotonic() + self._ready_timeout
        while time.monotonic() < deadline:
            if captured_url["url"***REMOVED*** is not None:
                break
            if proc.poll() is not None:
                # Процесс умер до того как успели поймать URL.
                raise RuntimeError(f"tunnel process {binary***REMOVED*** exited prematurely (code={proc.returncode***REMOVED***)")
            time.sleep(0.1)

        if captured_url["url"***REMOVED*** is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise TimeoutError(f"tunnel URL not captured within {self._ready_timeout***REMOVED***s")

        spec = TunnelSpec(url=captured_url["url"***REMOVED***, port=port, binary=binary, process=proc, kind=kind)
        self._spec = spec
        atexit.register(self._atexit_cleanup)
        return spec

    def stop(self, timeout: float = 3.0) -> None:
        """Terminate subprocess + дренаж потоков.

        Защищён self._lock: если кто-то в середине start(), stop ждёт
        (lock held). Двойная защита от доступа к мёртвому self._spec.
        """
        with self._lock:
            if self._spec is None:
                return
            proc = self._spec.process
            try:
                proc.terminate()
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=timeout)
            finally:
                self._spec = None
                self._reader_thread = None

    def _atexit_cleanup(self) -> None:
        """Гарантированная очистка при exit interpreter."""
        try:
            self.stop(timeout=2.0)
        except Exception:
            # atexit должен тихо глотать всё — иначе exit 1 при завершении.
            pass


# ═══════════════════════════════════════════════════════════════
# PhoneAPIClient (urllib-based, тонкая обёртка)
# ═══════════════════════════════════════════════════════════════


class PhoneAPIClient:
    """HTTP-клиент для локального API на телефоне.

    Plugins-friendly: один Bearer token, JSON request/response,
    короткий таймаут (localhost). Не делает ретраев — fail-fast,
    чтобы caller мог быстро вернуть meaningful error в MCP envelope.
    """

    def __init__(
        self,
        base_url: Optional[str***REMOVED*** = None,
        token: Optional[str***REMOVED*** = None,
        timeout: Optional[float***REMOVED*** = None,
    ) -> None:
        self.base_url = (base_url or PHONE_API_BASE).rstrip("/")
        self.token = token if token is not None else PHONE_API_TOKEN
        self.timeout = timeout if timeout is not None else PHONE_HTTP_TIMEOUT_S

    def _request(
        self, method: str, path: str, payload: Optional[dict[str, Any***REMOVED******REMOVED*** = None
    ) -> dict[str, Any***REMOVED***:
        url = f"{self.base_url***REMOVED***{path***REMOVED***"
        data: Optional[bytes***REMOVED*** = None
        headers = {"Accept": "application/json"***REMOVED***
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"***REMOVED*** = "application/json"
        if self.token:
            headers["Authorization"***REMOVED*** = f"Bearer {self.token***REMOVED***"
        req = urlrequest.Request(url, data=data, method=method, headers=headers)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return {"status": resp.status, "body": json.loads(body) if body else {***REMOVED******REMOVED***
        except HTTPError as e:
            return {"status": e.code, "error": f"HTTP {e.code***REMOVED*** from phone API: {e.reason***REMOVED***"***REMOVED***
        except URLError as e:
            return {"status": 0, "error": f"phone API unreachable: {e.reason***REMOVED***"***REMOVED***
        except json.JSONDecodeError as e:
            return {"status": 0, "error": f"phone API returned invalid JSON: {e***REMOVED***"***REMOVED***

    def get(self, path: str) -> dict[str, Any***REMOVED***:
        return self._request("GET", path)

    def post(self, path: str, payload: dict[str, Any***REMOVED***) -> dict[str, Any***REMOVED***:
        return self._request("POST", path, payload)


# ═══════════════════════════════════════════════════════════════
# Tools (BaseTool + send_sms/get_contacts/play_music)
# ═══════════════════════════════════════════════════════════════


class ToolError(Exception):
    """Schema validation / tool execution error (превращается в MCP error envelope)."""


class BaseTool:
    """Базовый MCP-инструмент.

    Подклассы определяют:
      - name (str), description (str)
      - input_schema() → dict с 'required' и 'properties'
      - _call(api_client, **kwargs) → dict (raw response body, no envelope)

    NOTE: ``input_schema()`` — КАСТОМНЫЙ метод (НЕ pydantic API). Класс не
    наследует ``pydantic.BaseModel``; метод возвращает plain dict для ключа
    ``inputSchema`` MCP ``tools/list``. Имя выбрано без коллизии с pydantic
    v1 ``BaseModel.schema()`` (deprecated в pydantic 2.x).
    """

    name: str = ""
    description: str = ""
    _required: tuple[str, ...***REMOVED*** = ()
    _properties: dict[str, str***REMOVED*** = {***REMOVED***  # param_name → "string" | "integer"

    def input_schema(self) -> dict[str, Any***REMOVED***:
        return {
            "type": "object",
            "required": list(self._required),
            "properties": {
                k: {"type": v, "description": f"Parameter `{k***REMOVED***` of type {v***REMOVED***"***REMOVED***
                for k, v in self._properties.items()
            ***REMOVED***,
        ***REMOVED***

    def validate(self, kwargs: dict[str, Any***REMOVED***) -> None:
        """Lightweight schema validation — required fields + isinstance types + reject extras.

        Блокирует silent passthrough of unexpected kwargs (reviewer finding #2):
        если в запросе есть поля, которых нет в схеме, это ToolError (НЕ
        forwarding to upstream API). SSRF / data-leak vector защищён.
        """
        # 1. Required fields.
        for required in self._required:
            if required not in kwargs:
                raise ToolError(f"missing required parameter: {required!r***REMOVED***")
        # 2. Type checks for declared fields (single truth-check, no double logic).
        for param_name, expected_type in self._properties.items():
            if param_name not in kwargs:
                continue
            value = kwargs[param_name***REMOVED***
            if expected_type == "string":
                if not isinstance(value, str):
                    raise ToolError(
                        f"parameter {param_name!r***REMOVED*** must be string, got {type(value).__name__***REMOVED***"
                    )
            elif expected_type == "integer":
                # bool is a subclass of int в Python, поэтому нужжно отделять явно.
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ToolError(
                        f"parameter {param_name!r***REMOVED*** must be integer, got {type(value).__name__***REMOVED***"
                    )
        # 3. Reject unknown fields (no silent passthrough).
        allowed = set(self._required) | set(self._properties.keys())
        extras = set(kwargs.keys()) - allowed
        if extras:
            raise ToolError(
                f"unknown parameter(s): {sorted(extras)***REMOVED***. "
                f"allowed: {sorted(allowed)***REMOVED***"
            )

    def execute(self, api_client: PhoneAPIClient, kwargs: dict[str, Any***REMOVED***) -> dict[str, Any***REMOVED***:
        """MCP-facing entrypoint: validate → call → return raw body."""
        self.validate(kwargs)
        try:
            return self._call(api_client, **kwargs)
        except Exception as e:
            # Безопасный envelope: caller получает explicit error в MCP result.
            raise ToolError(f"tool {self.name***REMOVED*** failed: {e***REMOVED***") from e

    def _call(self, api_client: PhoneAPIClient, **kwargs: Any) -> dict[str, Any***REMOVED***:
        raise NotImplementedError


class SendSmsTool(BaseTool):
    """POST /send-sms — отправить SMS через локальный API на телефоне."""

    name = "send_sms"
    description = "Send an SMS message via the local phone API. Returns delivery confirmation."
    _required = ("to", "body")
    _properties = {"to": "string", "body": "string"***REMOVED***

    def _call(self, api_client: PhoneAPIClient, **kwargs: Any) -> dict[str, Any***REMOVED***:
        resp = api_client.post("/send-sms", kwargs)
        if resp.get("status", 0) != 200:
            raise ToolError(resp.get("error", "send-sms failed"))
        return {"delivered": True, "to": kwargs["to"***REMOVED***, "status": resp.get("status")***REMOVED***


class GetContactsTool(BaseTool):
    """GET /get-contacts?limit=N — список контактов из телефонной книги."""

    name = "get_contacts"
    description = "Fetch the contact list from the phone's address book."
    _required = ()                # все параметры опциональны
    _properties = {"limit": "integer"***REMOVED***

    def _call(self, api_client: PhoneAPIClient, **kwargs: Any) -> dict[str, Any***REMOVED***:
        limit = kwargs.get("limit", 50)
        resp = api_client.get(f"/get-contacts?limit={limit***REMOVED***")
        if resp.get("status", 0) != 200:
            raise ToolError(resp.get("error", "get-contacts failed"))
        return {"contacts": resp.get("body", {***REMOVED***).get("contacts", [***REMOVED***), "count": limit***REMOVED***


class PlayMusicTool(BaseTool):
    """POST /play-music — воспроизвести трек (artist + track) на телефоне."""

    name = "play_music"
    description = "Play a music track identified by artist and track name on the phone."
    _required = ("artist", "track")
    _properties = {"artist": "string", "track": "string"***REMOVED***

    def _call(self, api_client: PhoneAPIClient, **kwargs: Any) -> dict[str, Any***REMOVED***:
        resp = api_client.post("/play-music", kwargs)
        if resp.get("status", 0) != 200:
            raise ToolError(resp.get("error", "play-music failed"))
        return {"playing": True, "track": kwargs["track"***REMOVED***, "artist": kwargs["artist"***REMOVED******REMOVED***


def default_tool_registry() -> dict[str, BaseTool***REMOVED***:
    """Реестр инструментов по умолчанию (все 3)."""
    return {
        t.name: t() for t in (SendSmsTool, GetContactsTool, PlayMusicTool)
    ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# PhoneControlMCP orchestrator
# ═══════════════════════════════════════════════════════════════


def check_bearer(provided: Optional[str***REMOVED***, expected: str) -> bool:
    """Bearer-token gate с constant-time compare (anti-timing-attack)."""
    if not provided:
        return False
    if len(provided) > 4096:           # DoS-guard (RFC 6750 sanity)
        return False
    return hmac.compare_digest(provided, expected)


def check_origin(origin: Optional[str***REMOVED***, allowlist: tuple[str, ...***REMOVED***) -> bool:
    """Origin allowlist; '*' = allow all (для local dev)."""
    if not allowlist:
        return False
    if "*" in allowlist:
        return True
    if not origin:
        return False
    return origin in allowlist


class PhoneControlMCP:
    """MCP-оркстратор: tools/list + tools/call + auth/origin gate."""

    def __init__(
        self,
        token: Optional[str***REMOVED*** = None,
        origins: Optional[tuple[str, ...***REMOVED******REMOVED*** = None,
        tools: Optional[dict[str, BaseTool***REMOVED******REMOVED*** = None,
        api_client: Optional[PhoneAPIClient***REMOVED*** = None,
        tunnel_manager: Optional[TunnelManager***REMOVED*** = None,
    ) -> None:
        self.token = token if token is not None else PHONE_MCP_TOKEN
        self.origins = origins if origins is not None else PHONE_ORIGINS
        self.tools = tools if tools is not None else default_tool_registry()
        self.api_client = api_client or PhoneAPIClient()
        self.tunnel = tunnel_manager or TunnelManager()

    # ── Tools/list ─────────────────────────────────────────
    def list_tools(self, *, bearer: Optional[str***REMOVED*** = None, origin: Optional[str***REMOVED*** = None) -> dict[str, Any***REMOVED***:
        if not check_bearer(bearer, self.token):
            return {"success": False, "error": "unauthorized", "status": 401***REMOVED***
        if not check_origin(origin, self.origins):
            return {"success": False, "error": "origin not allowed", "status": 403***REMOVED***
        return {
            "success": True,
            "data": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema(),
                    ***REMOVED***
                    for tool in self.tools.values()
                ***REMOVED***
            ***REMOVED***,
        ***REMOVED***

    # ── Tools/call ─────────────────────────────────────────
    def call_tool(
        self,
        tool_name: str,
        kwargs: dict[str, Any***REMOVED***,
        *,
        bearer: Optional[str***REMOVED*** = None,
        origin: Optional[str***REMOVED*** = None,
    ) -> dict[str, Any***REMOVED***:
        if not check_bearer(bearer, self.token):
            return {"success": False, "error": "unauthorized", "status": 401***REMOVED***
        if not check_origin(origin, self.origins):
            return {"success": False, "error": "origin not allowed", "status": 403***REMOVED***
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"unknown tool: {tool_name!r***REMOVED***",
                "available": sorted(self.tools.keys()),
                "status": 404,
            ***REMOVED***
        tool = self.tools[tool_name***REMOVED***
        try:
            raw = tool.execute(self.api_client, kwargs)
            return {"success": True, "data": raw***REMOVED***
        except ToolError as e:
            return {"success": False, "error": str(e), "status": 400***REMOVED***

    # ── Tunnel API ─────────────────────────────────────────
    def tunnel_up(self, port: int) -> dict[str, Any***REMOVED***:
        try:
            spec = self.tunnel.start(port)
            return {"success": True, "data": {"url": spec.url, "kind": spec.kind, "port": spec.port***REMOVED******REMOVED***
        except (FileNotFoundError, RuntimeError, TimeoutError) as e:
            return {"success": False, "error": str(e), "status": 503***REMOVED***

    def tunnel_down(self) -> dict[str, Any***REMOVED***:
        try:
            self.tunnel.stop()
            return {"success": True, "data": {"stopped": True***REMOVED******REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e), "status": 500***REMOVED***

    def tunnel_status(self) -> dict[str, Any***REMOVED***:
        if not self.tunnel.is_active:
            return {"success": True, "data": {"active": False***REMOVED******REMOVED***
        spec = self.tunnel.spec
        assert spec is not None
        return {
            "success": True,
            "data": {
                "active": True,
                "url": spec.url,
                "kind": spec.kind,
                "port": spec.port,
                "uptime_s": round(time.monotonic() - spec.started_at, 1),
            ***REMOVED***,
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phone-control MCP tool server wrapper (pomt45_05 first slice)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tools_list = sub.add_parser("tools-list", help="List available tools")
    p_tools_list.add_argument("--bearer", default=None, help="Bearer token override")
    p_tools_list.add_argument("--origin", default=None, help="Origin header override")

    p_tools_call = sub.add_parser("tools-call", help="Call a tool")
    p_tools_call.add_argument("tool", help="Tool name (send_sms | get_contacts | play_music)")
    p_tools_call.add_argument("args", help="Tool arguments as JSON string")
    p_tools_call.add_argument("--bearer", default=None)
    p_tools_call.add_argument("--origin", default=None)

    p_tunnel = sub.add_parser("tunnel", help="Manage Cloudflare tunnel")
    p_tunnel.add_argument("action", choices=["up", "down", "status"***REMOVED***)
    p_tunnel.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    mcp = PhoneControlMCP()

    if args.cmd == "tools-list":
        out = mcp.list_tools(bearer=args.bearer, origin=args.origin)
    elif args.cmd == "tools-call":
        try:
            parsed_kwargs = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"INVALID JSON: {e***REMOVED***", file=sys.stderr)
            return 2
        out = mcp.call_tool(args.tool, parsed_kwargs, bearer=args.bearer, origin=args.origin)
    elif args.cmd == "tunnel":
        if args.action == "up":
            out = mcp.tunnel_up(args.port)
        elif args.action == "down":
            out = mcp.tunnel_down()
        else:
            out = mcp.tunnel_status()
    else:
        parser.print_help()
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
