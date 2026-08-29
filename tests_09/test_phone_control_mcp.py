#!/usr/bin/env python3
"""
tests_09/test_phone_control_mcp.py — Тесты для [scripts_01/phone_control_mcp.py***REMOVED***(scripts_01/phone_control_mcp.py).

Покрытие:
  * Tool dispatch — happy path для каждого из 3 инструментов (send_sms/get_contacts/play_music)
  * Schema validation — missing required + wrong type → ToolError
  * Orchestrator — unknown tool / bearer-missing / bearer-invalid / origin-not-allowed
  * Orchestrator — tools/list возвращает все 3 схемы
  * Tunnel security — subprocess shell=False (канарейка на shell-injection)
  * Tunnel lifecycle — argv-list start, URL extraction, stop cleanup
  * Envelope contract — {success: bool, data|error***REMOVED*** для всех путей

Не использует реальный cloudflared (zero-dependency, tmp mock-script).
Без pytest fixtures — явные setUp/tearDown.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
***REMOVED***
from unittest.mock import MagicMock, patch

# Подключаем scripts_01 как importable (paths bootstrap)
sys.path.insert(0, str(Path(__file__).resolve().parents[1***REMOVED*** / "scripts_01"))

from phone_control_mcp import (  # noqa: E402
    BaseTool,
    GetContactsTool,
    PhoneAPIClient,
    PhoneControlMCP,
    PlayMusicTool,
    SendSmsTool,
    ToolError,
    TunnelManager,
    TunnelSpec,
    check_bearer,
    check_origin,
    default_tool_registry,
)


# ── Вспомогательные helpers ─────────────────────────────────


def _mock_api_client(payload: dict | None = None, status: int = 200) -> PhoneAPIClient:
    """Создаёт mocked PhoneAPIClient, где post()/get() возвращают заданный payload."""
    client = PhoneAPIClient(base_url="http://mock", token="mock-token", timeout=1.0)
    default = {"status": status, "body": payload or {***REMOVED******REMOVED***
    client.post = MagicMock(return_value=default)  # type: ignore[method-assign***REMOVED***
    client.get = MagicMock(return_value=default)  # type: ignore[method-assign***REMOVED***
    return client


# ═══════════════════════════════════════════════════════════════
# Tool dispatch — happy path для каждого из 3 инструментов
# ═══════════════════════════════════════════════════════════════


class TestSendSmsToolDispatch(unittest.TestCase):
    """send_sms: required = (to, body) — POST /send-sms."""

    def test_send_sms_with_valid_args_returns_delivered(self) -> None:
        # ARRANGE: mocked API возвращает 200 OK.
        api = _mock_api_client(status=200)
        tool = SendSmsTool()

        # ACT
        result = tool.execute(api, {"to": "+1234567890", "body": "Hello"***REMOVED***)

        # ASSERT: вернулся dict с delivered=True + payload прошёл через API.
        self.assertTrue(result["delivered"***REMOVED***)
        self.assertEqual(result["to"***REMOVED***, "+1234567890")
        api.post.assert_called_once_with("/send-sms", {"to": "+1234567890", "body": "Hello"***REMOVED***)


class TestGetContactsToolDispatch(unittest.TestCase):
    """get_contacts: optional limit — GET /get-contacts?limit=N."""

    def test_get_contacts_with_limit_returns_contacts_list(self) -> None:
        contacts = [{"name": "Alice", "phone": "+1"***REMOVED***, {"name": "Bob", "phone": "+2"***REMOVED******REMOVED***
        api = _mock_api_client(payload={"contacts": contacts***REMOVED***)
        tool = GetContactsTool()

        result = tool.execute(api, {"limit": 10***REMOVED***)

        self.assertEqual(result["count"***REMOVED***, 10)
        self.assertEqual(result["contacts"***REMOVED***, contacts)
        api.get.assert_called_once_with("/get-contacts?limit=10")

    def test_get_contacts_default_limit_uses_50(self) -> None:
        api = _mock_api_client(payload={"contacts": [***REMOVED******REMOVED***)
        tool = GetContactsTool()

        result = tool.execute(api, {***REMOVED***)

        self.assertEqual(result["count"***REMOVED***, 50)
        api.get.assert_called_once_with("/get-contacts?limit=50")


class TestPlayMusicToolDispatch(unittest.TestCase):
    """play_music: required = (artist, track) — POST /play-music."""

    def test_play_music_with_valid_args_returns_playing(self) -> None:
        api = _mock_api_client(status=200)
        tool = PlayMusicTool()

        result = tool.execute(api, {"artist": "Vulfpeck", "track": "Dean Town"***REMOVED***)

        self.assertTrue(result["playing"***REMOVED***)
        self.assertEqual(result["artist"***REMOVED***, "Vulfpeck")
        self.assertEqual(result["track"***REMOVED***, "Dean Town")
        api.post.assert_called_once_with("/play-music", {"artist": "Vulfpeck", "track": "Dean Town"***REMOVED***)


# ═══════════════════════════════════════════════════════════════
# Schema validation (lightweight guard)
# ═══════════════════════════════════════════════════════════════


class TestSchemaValidation(unittest.TestCase):
    """Lightweight schema validation — required + isinstance типов."""

    def test_send_sms_missing_body_raises_ToolError(self) -> None:
        tool = SendSmsTool()
        with self.assertRaises(ToolError) as ctx:
            tool.validate({"to": "+1234"***REMOVED***)
        self.assertIn("body", str(ctx.exception))

    def test_send_sms_missing_to_raises_ToolError(self) -> None:
        tool = SendSmsTool()
        with self.assertRaises(ToolError):
            tool.validate({"body": "hi"***REMOVED***)

    def test_send_sms_body_as_int_raises_ToolError(self) -> None:
        """body должен быть string, не integer."""
        tool = SendSmsTool()
        with self.assertRaises(ToolError) as ctx:
            tool.validate({"to": "+1234", "body": 12345***REMOVED***)  # type: ignore[arg-type***REMOVED***
        self.assertIn("string", str(ctx.exception))

    def test_get_contacts_limit_as_string_raises_ToolError(self) -> None:
        tool = GetContactsTool()
        with self.assertRaises(ToolError) as ctx:
            tool.validate({"limit": "abc"***REMOVED***)  # type: ignore[arg-type***REMOVED***
        self.assertIn("integer", str(ctx.exception))

    def test_schema_payload_is_dict_with_required_and_properties(self) -> None:
        """SMCP-схема — обязательно содержит type/required/properties."""
        tool = SendSmsTool()
        s = tool.input_schema()
        self.assertEqual(s["type"***REMOVED***, "object")
        self.assertIn("to", s["required"***REMOVED***)
        self.assertIn("body", s["required"***REMOVED***)
        self.assertIn("to", s["properties"***REMOVED***)
        self.assertIn("body", s["properties"***REMOVED***)

    def test_bool_rejected_as_integer_param_type(self) -> None:
        """bool is subclass of int, но семантически не integer для limit."""
        tool = GetContactsTool()
        with self.assertRaises(ToolError):
            tool.validate({"limit": True***REMOVED***)  # type: ignore[arg-type***REMOVED***

    def test_unknown_kwargs_rejected_ToolError(self) -> None:
        """Reviewer finding #2: reject unknown fields, не silent passthrough."""
        tool = SendSmsTool()
        with self.assertRaises(ToolError) as ctx:
            tool.validate({"to": "+1234", "body": "hi", "evil_field": "x"***REMOVED***)
        self.assertIn("unknown parameter", str(ctx.exception))
        self.assertIn("evil_field", str(ctx.exception))

    def test_radius_string_rejected_as_integer(self) -> None:
        """Sanity: string passed where integer expected."""
        tool = GetContactsTool()
        with self.assertRaises(ToolError) as ctx:
            tool.validate({"limit": "50"***REMOVED***)  # type: ignore[arg-type***REMOVED***
        self.assertIn("integer", str(ctx.exception))


# ═══════════════════════════════════════════════════════════════
# Orchestrator: dispatch + auth + origin + tools/list
# ═══════════════════════════════════════════════════════════════


class TestOrchestratorAuth(unittest.TestCase):
    """Bearer-token gate (HMAC constant-time compare)."""

    def test_bearer_missing_returns_401(self) -> None:
        mcp = PhoneControlMCP(
            token="correct-token",
            origins=("*",),
            api_client=_mock_api_client(),
            tools=default_tool_registry(),
        )
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer=None, origin="x")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 401)

    def test_bearer_invalid_returns_401(self) -> None:
        mcp = PhoneControlMCP(token="correct", origins=("*",), api_client=_mock_api_client(), tools=default_tool_registry())
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer="WRONG", origin="x")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 401)

    def test_bearer_too_long_returns_401(self) -> None:
        """DoS-guard: токены >4096 chars отклоняются даже если совпадают по prefix."""
        mcp = PhoneControlMCP(token="correct", origins=("*",), api_client=_mock_api_client(), tools=default_tool_registry())
        huge = "correct" + "A" * 5000
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer=huge, origin="x")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 401)


class TestOrchestratorOrigin(unittest.TestCase):
    """Origin allowlist (Comma-separated env, default * для dev)."""

    def test_origin_not_in_allowlist_returns_403(self) -> None:
        mcp = PhoneControlMCP(
            token="t",
            origins=("https://allowed.example.com",),
            api_client=_mock_api_client(),
            tools=default_tool_registry(),
        )
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer="t", origin="https://evil.example.com")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 403)

    def test_origin_wildcard_allows_anything(self) -> None:
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=_mock_api_client(), tools=default_tool_registry())
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer="t", origin="https://anywhere.example.com")
        self.assertTrue(out["success"***REMOVED***)


class TestOrchestratorToolDispatch(unittest.TestCase):
    """Envelope contract: {success: bool, ...***REMOVED*** и unknown tool → 404."""

    def test_unknown_tool_returns_404_with_available_list(self) -> None:
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=_mock_api_client(), tools=default_tool_registry())
        out = mcp.call_tool("nuke_phone", {***REMOVED***, bearer="t", origin="x")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 404)
        self.assertIn("send_sms", out["available"***REMOVED***)
        self.assertIn("get_contacts", out["available"***REMOVED***)
        self.assertIn("play_music", out["available"***REMOVED***)

    def test_tool_execution_error_returns_safe_envelope(self) -> None:
        """Если API возвращает ошибку — caller получает friendly ToolError в envelope."""
        client = _mock_api_client(status=500)
        client.post = MagicMock(return_value={"status": 500, "error": "phone dead"***REMOVED***)  # type: ignore[method-assign***REMOVED***
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=client, tools=default_tool_registry())
        out = mcp.call_tool("send_sms", {"to": "+1", "body": "hi"***REMOVED***, bearer="t", origin="x")
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 400)
        self.assertIn("phone dead", out["error"***REMOVED***)


class TestOrchestratorToolsList(unittest.TestCase):
    """tools/list возвращает все 3 инструмента со схемами."""

    def test_tools_list_returns_3_tools_with_schemas(self) -> None:
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=_mock_api_client(), tools=default_tool_registry())
        out = mcp.list_tools(bearer="t", origin="x")
        self.assertTrue(out["success"***REMOVED***)
        names = sorted(t["name"***REMOVED*** for t in out["data"***REMOVED***["tools"***REMOVED***)
        self.assertEqual(names, ["get_contacts", "play_music", "send_sms"***REMOVED***)
        for tool in out["data"***REMOVED***["tools"***REMOVED***:
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"***REMOVED***["type"***REMOVED***, "object")


# ═══════════════════════════════════════════════════════════════
# TunnelManager: argv subprocess (security) + lifecycle
# ═══════════════════════════════════════════════════════════════


class TestTunnelSecurity(unittest.TestCase):
    """Tunnel-инвариант: shell=False, argv-list (канарейка от shell-injection)."""

    def test_subprocess_argv_is_list_no_shell(self) -> None:
        """Mock subprocess.Popen — убеждаемся, что вызывается с shell=False и argv-списком."""
        captured_kwargs: dict = {***REMOVED***

        class FakeProc:
            stderr = None
            def poll(self) -> int | None: return None  # живой
            def terminate(self) -> None: pass
            def wait(self, timeout: float = 3.0) -> int: return 0
            def kill(self) -> None: pass

        def fake_popen(argv, **kwargs):
            captured_kwargs["argv"***REMOVED*** = argv
            captured_kwargs.update(kwargs)
            return FakeProc()

        # Подменяем subprocess.Popen в namespace-у модуля + заранее registers atexit (чтобы start не упал)
        with patch("phone_control_mcp.subprocess.Popen", side_effect=fake_popen) as mock_popen:
            with patch("phone_control_mcp.time.sleep"):  # чтобы ready-loop не задерживал
                with patch("phone_control_mcp.threading.Thread"):  # заглушим reader-thread
                    mgr = TunnelManager(tunnel_bin="cloudflared", ready_timeout=0.05)
                    # Подменим URL capture: ручной инжект через captured_url dict-патч.
                    with patch.object(mgr, "_reader_thread", create=True):
                        # Форсируем captured_url в _spawn через monkeypatch на URL PASS.
                        # Проще: модифицируем captured через прямое присваивание в _spawn-локальной dict.
                        # Здесь просто проверяем что Popen получает верные аргументы (URL — побочный эффект).
                        with self.assertRaises((RuntimeError, TimeoutError)):
                            # URL никогда не придёт (нет реального cloudflared), но Popen всё равно дёрнут.
                            mgr.start(8765)

        # Главное: shell=False и argv=list.
        mock_popen.assert_called_once()
        self.assertFalse(captured_kwargs["shell"***REMOVED***, "shell=True WOULD allow shell injection!")
        argv = captured_kwargs["argv"***REMOVED***
        self.assertIsInstance(argv, list)
        self.assertEqual(argv[0***REMOVED***, "cloudflared")
        self.assertEqual(argv[1:***REMOVED***, ["tunnel", "--url", "http://localhost:8765"***REMOVED***)

    def test_popen_uses_start_new_session(self) -> None:
        """Hardening #2: Popen получает start_new_session=True → detach от process group родителя.

        Если parent убит SIGKILL → subprocess переживёт в своей сессии (нет
        cascading kill). Канарейка против regression: при удалении флага в Popen
        тест падает.
        """
        captured_kwargs: dict = {***REMOVED***

        class FakeProc:
            stderr = None
            def poll(self) -> int | None: return None
            def terminate(self) -> None: pass
            def wait(self, timeout: float = 3.0) -> int: return 0
            def kill(self) -> None: pass

        def fake_popen(argv, **kwargs):
            captured_kwargs["argv"***REMOVED*** = argv
            captured_kwargs.update(kwargs)
            return FakeProc()

        with patch("phone_control_mcp.subprocess.Popen", side_effect=fake_popen) as mock_popen:
            with patch("phone_control_mcp.time.sleep"):
                with patch("phone_control_mcp.threading.Thread"):
                    mgr = TunnelManager(tunnel_bin="cloudflared", ready_timeout=0.05)
                    with patch.object(mgr, "_reader_thread", create=True):
                        with self.assertRaises((RuntimeError, TimeoutError)):
                            mgr.start(8765)

        # Главная assertion: start_new_session=True был передан в Popen.
        mock_popen.assert_called_once()
        self.assertTrue(
            captured_kwargs.get("start_new_session", False),
            "Popen должен получить start_new_session=True для SIGKILL-detach (reviewer hardening #2)",
        )


class TestTunnelLifecycle(unittest.TestCase):
    """Tunnel lifecycle с mock-скриптом (НЕ реальным cloudflared)."""

    def _write_mock_cloudflared(self, tmpdir: Path, url: str) -> Path:
        """Создаёт bash-скрипт, который печатает URL в stderr и затем 'спит'."""
        script = tmpdir / "mock_cloudflared.sh"
        # Bash с stderr → эмулирует cloudflared.
        script.write_text(
            "#!/usr/bin/env bash\n"
            "sleep 0.1\n"
            f'echo "{url***REMOVED***" >&2\n'
            "sleep 60\n",  # test must terminate us
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    def test_tunnel_start_extracts_url_and_stop_terminates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_s:
            tmpdir = Path(tmpdir_s)
            mock_url = "https://abc-def-ghi.trycloudflare.com/"
            mock_bin = self._write_mock_cloudflared(tmpdir, mock_url)
            mgr = TunnelManager(tunnel_bin=str(mock_bin), ready_timeout=5.0)
            # ACT: start with port 9876 (mock script ignores port number, gets argv)
            spec = mgr.start(9876)
            # ASSERT: URL extracted, spec populated.
            self.assertIsInstance(spec, TunnelSpec)
            self.assertEqual(spec.url, mock_url.rstrip("/"))
            self.assertEqual(spec.port, 9876)
            self.assertEqual(spec.kind, "cloudflared")
            # ACT: stop — terminate + wait.
            mgr.stop(timeout=2.0)
            # ASSERT: spec cleared + proc terminated.
            self.assertIsNone(mgr.spec)
            self.assertFalse(mgr.is_active)

    def test_tunnel_already_active_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_s:
            tmpdir = Path(tmpdir_s)
            mock_bin = self._write_mock_cloudflared(tmpdir, "https://first.trycloudflare.com")
            mgr = TunnelManager(tunnel_bin=str(mock_bin), ready_timeout=5.0)
            mgr.start(8888)
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    mgr.start(8889)
                self.assertIn("already active", str(ctx.exception))
            finally:
                mgr.stop()

    def test_concurrent_start_serializes_via_lock(self) -> None:
        """Hardening #1: threading.Lock в start() закрывает race между concurrent tunnel_up.

        СЦЕНАРИЙ: два потока входят в start() «одновременно». Без lock оба
        увидят is_active=False → создаются 2 Popen-процесса, второй leaked.
        С lock: один успевает, второй сразу видит is_active=True → RuntimeError.

        Mock-скрипт эмулирует cloudflared (URL в stderr, потом sleep 60s);
        тест terminate'ит активные процессы в finally.
        """
        import threading as _threading

        with tempfile.TemporaryDirectory() as tmpdir_s:
            tmpdir = Path(tmpdir_s)
            # Один и тот же mock-bin обслуживает оба thread'a (быстрый URL-print, slow sleep).
            mock_bin = self._write_mock_cloudflared(tmpdir, "https://race-condition.trycloudflare.com")
            mgr = TunnelManager(tunnel_bin=str(mock_bin), ready_timeout=5.0)

            results: dict[str, object***REMOVED*** = {"first_spec": None, "second_error": None, "started_at": [***REMOVED******REMOVED***

            def attempt_start(port: int) -> None:
                try:
                    spec = mgr.start(port)
                    results["first_spec"***REMOVED*** = spec  # один из потоков заполнит
                except RuntimeError as e:
                    results["second_error"***REMOVED*** = str(e)

            # Запускаем 2 потока одновременно.
            t1 = _threading.Thread(target=attempt_start, args=(9001,))
            t2 = _threading.Thread(target=attempt_start, args=(9002,))
            t1.start(); t2.start()
            t1.join(timeout=10.0); t2.join(timeout=10.0)

            try:
                # ASSERT: один из потоков успешно создал spec, другой получил RuntimeError("already active").
                spec = results["first_spec"***REMOVED***
                self.assertIsInstance(spec, TunnelSpec)
                self.assertIn("already active", str(results["second_error"***REMOVED***))
                # ASSERT: только ОДИН процесс создан (а не два leaked Popen).
                # TunnelManager._spec хранит ровно один spec.
                self.assertIs(mgr.spec, spec)
                # ASSERT: оба потока завершились, а не deadlocked.
                self.assertFalse(t1.is_alive())
                self.assertFalse(t2.is_alive())
            finally:
                mgr.stop(timeout=2.0)


# ═══════════════════════════════════════════════════════════════
# Tunnel orchestrator (PhoneControlMCP.tunnel_up/down/status)
# ═══════════════════════════════════════════════════════════════


class TestTunnelOrchestrator(unittest.TestCase):
    """PhoneControlMCP.tunnel_up/down/status не блокирует test (через прямое управление)."""

    def test_tunnel_status_when_inactive_returns_active_false(self) -> None:
        mgr = TunnelManager(tunnel_bin="/nonexistent", ready_timeout=0.01)
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=_mock_api_client(), tunnel_manager=mgr)
        out = mcp.tunnel_status()
        self.assertTrue(out["success"***REMOVED***)
        self.assertFalse(out["data"***REMOVED***["active"***REMOVED***)

    def test_tunnel_up_when_cloudflared_missing_returns_503(self) -> None:
        mgr = TunnelManager(tunnel_bin="/definitely/not/a/real/binary", ready_timeout=0.01)
        mcp = PhoneControlMCP(token="t", origins=("*",), api_client=_mock_api_client(), tunnel_manager=mgr)
        out = mcp.tunnel_up(8765)
        self.assertFalse(out["success"***REMOVED***)
        self.assertEqual(out["status"***REMOVED***, 503)


if __name__ == "__main__":
    unittest.main()
