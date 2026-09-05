"""
Unit тесты для Runtime Abstraction Layer.

Покрытие:
- Типы и data classes (RuntimeDefinition, RuntimeResult, RuntimeCapability, etc.)
- RuntimeAdapter base class (connect/disconnect/ping/health)
- StdioMCPAdapter (mocked MCP Client)
- HTTPMCPAdapter (mocked HTTP Client)
- FreebuffAdapter (search binary, connect)
- ClaudeCodeAdapter (search binary, connect)
- RuntimeRegistry (register/get/list/discover/unregister/save/load)
- RuntimeCapabilityRegistry (list, get_runtime_for_capability, score)
- AdapterRegistry
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
***REMOVED***
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from freebuff_plugin_03.runtime import (
    RuntimeStatus,
    SessionStatus,
    AdapterType,
    RuntimeConfig,
    RuntimeDefinition,
    RuntimeResult,
    RuntimeCapability,
    RuntimeSession,
    RuntimeHealth,
)
from freebuff_plugin_03.runtime.adapter import (
    RuntimeAdapter,
    StdioMCPAdapter,
    HTTPMCPAdapter,
    AdapterRegistry,
    default_adapter_registry,
)
from freebuff_plugin_03.runtime.registry import (
    RuntimeRegistry,
    RuntimeCapabilityRegistry,
)
from freebuff_plugin_03.runtime.adapters import (
    FreebuffAdapter,
    ClaudeCodeAdapter,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_storage():
    """Временный файл для runtime registry."""
    tmp = Path(tempfile.mktemp(suffix=".json"))
    yield tmp
    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture
def mock_mcp_client():
    """Mock StdioMCPClient."""
    client = Mock()
    # is_connected как PropertyMock — возвращает True после connect
    is_connected_prop = PropertyMock(return_value=True)
    type(client).is_connected = is_connected_prop
    client.connect.return_value = True
    client.ping.return_value = True
    client.disconnect.return_value = None
    client.list_tools.return_value = [***REMOVED***
    client.call_tool.return_value = Mock(
        success=True,
        content=[{"type": "text", "text": "Hello from mock"***REMOVED******REMOVED***,
        error=None,
    )
    client.server_info = {"serverInfo": {"version": "1.0.0"***REMOVED******REMOVED***
    return client


# ═══════════════════════════════════════════════════════════════
# 1. Types
# ═══════════════════════════════════════════════════════════════


class TestTypes:
    """Runtime types - 8 tests."""

    def test_runtime_config_defaults(self):
        cfg = RuntimeConfig()
        assert cfg.max_concurrent == 1
        assert cfg.timeout_seconds == 300
        assert cfg.max_retries == 3
        assert cfg.auto_reconnect is True

    def test_runtime_definition_defaults(self):
        rt = RuntimeDefinition()
        assert rt.name == ""
        assert rt.status == RuntimeStatus.UNKNOWN
        assert rt.version == "0.0.0"

    def test_runtime_definition_with_values(self):
        rt = RuntimeDefinition(
            name="freebuff",
            display_name="Freebuff CLI",
            version="1.0.0",
            status=RuntimeStatus.ACTIVE,
            capabilities=["coding", "planning"***REMOVED***,
        )
        assert rt.name == "freebuff"
        assert rt.status == RuntimeStatus.ACTIVE
        assert "coding" in rt.capabilities

    def test_runtime_result_defaults(self):
        result = RuntimeResult()
        assert result.content == ""
        assert result.finish_reason == "stop"
        assert result.latency_ms == 0
        assert result.cached is False

    def test_runtime_result_with_content(self):
        result = RuntimeResult(
            content="Hello",
            runtime="freebuff",
            latency_ms=150,
            model_used="deepseek-v4",
        )
        assert result.content == "Hello"
        assert result.latency_ms == 150
        assert result.model_used == "deepseek-v4"

    def test_runtime_capability(self):
        cap = RuntimeCapability(
            name="coding",
            description="Code generation",
            confidence=0.95,
            models=["deepseek-v4", "claude-3.5"***REMOVED***,
        )
        assert cap.name == "coding"
        assert cap.confidence == 0.95
        assert len(cap.models) == 2

    def test_runtime_session(self):
        session = RuntimeSession(
            runtime="freebuff",
            session_id="sess_001",
            message_count=5,
            status=SessionStatus.ACTIVE,
        )
        assert session.runtime == "freebuff"
        assert session.message_count == 5
        assert session.status == SessionStatus.ACTIVE

    def test_runtime_health(self):
        health = RuntimeHealth(alive=True, version="1.0", latency_ms=42, connected=True, tools_count=5)
        assert health.alive is True
        assert health.version == "1.0"
        assert health.tools_count == 5


# ═══════════════════════════════════════════════════════════════
# 2. RuntimeAdapter (base + implementations)
# ═══════════════════════════════════════════════════════════════


class TestRuntimeAdapter:
    """RuntimeAdapter ABC - 4 tests."""

    def test_adapter_abstract_class(self):
        """RuntimeAdapter нельзя инстанциировать напрямую."""
        with pytest.raises(TypeError):
            RuntimeAdapter(RuntimeConfig())  # type: ignore

    def test_concrete_adapter_implements_abstract(self):
        """StdioMCPAdapter реализует все абстрактные методы."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "echo", ["hello"***REMOVED***, "test", "Test Runtime")
        # Должен быть инстанциирован без ошибок
        assert adapter.name == "test"
        assert adapter.display_name == "Test Runtime"

    def test_adapter_lifecycle(self, monkeypatch: pytest.MonkeyPatch):
        """StdioMCPAdapter: connect → generate → disconnect."""
        # DEFERRED-7: короткий handshake-timeout — иначе connect() спавнит
        # реальный `echo` и ждёт полный MCP_REQUEST_TIMEOUT (30s), пока тот
        # не ответит валидным JSON-RPC initialize (чего не случится).
        from freebuff_plugin_03 import mcp_client

        monkeypatch.setattr(mcp_client, "MCP_REQUEST_TIMEOUT", 0.5)
        adapter = StdioMCPAdapter(RuntimeConfig(), "echo", ["hello"***REMOVED***, "test", "Test")
        assert adapter.is_connected() is False
        # connect должен вернуть False (echo не MCP сервер)
        ok = adapter.connect()
        assert ok is False
        assert adapter.is_connected() is False

    def test_adapter_reset_session(self):
        """reset_session создаёт новую сессию."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "echo", [***REMOVED***, "test", "Test")
        adapter._session = RuntimeSession(runtime="test", message_count=10)
        adapter.reset_session()
        assert adapter._session is not None
        assert adapter._session.message_count == 0


class TestStdioMCPAdapter:
    """StdioMCPAdapter - 6 tests with mocked client."""

    def test_connect_with_mock(self, mock_mcp_client):
        """connect через mock MCP клиента."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", ["-c", "print(1)"***REMOVED***, "test", "Test")
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient", return_value=mock_mcp_client):
            ok = adapter.connect()
            assert ok is True
            assert adapter.is_connected() is True

    def test_disconnect(self, mock_mcp_client):
        """disconnect вызывает disconnect клиента."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", [***REMOVED***, "test", "Test")
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient", return_value=mock_mcp_client):
            adapter.connect()
            ok = adapter.disconnect()
            assert ok is True

    def test_ping(self, mock_mcp_client):
        """ping возвращает True при успехе."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", [***REMOVED***, "test", "Test")
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient", return_value=mock_mcp_client):
            adapter.connect()
            assert adapter.ping() is True

    def test_health(self, mock_mcp_client):
        """health возвращает RuntimeHealth."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", [***REMOVED***, "test", "Test")
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient", return_value=mock_mcp_client):
            adapter.connect()
            health = adapter.health()
            assert isinstance(health, RuntimeHealth)
            assert health.alive is True

    def test_generate_selects_tool(self, mock_mcp_client):
        """generate выбирает подходящий инструмент."""
        mock_tool = Mock()
        mock_tool.name = "generate"
        mock_tool.description = "Generate"
        mock_tool.input_schema = {
            "type": "object",
            "properties": {"messages": {"type": "array"***REMOVED******REMOVED***,
        ***REMOVED***
        mock_mcp_client.list_tools.return_value = [mock_tool***REMOVED***
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", [***REMOVED***, "test", "Test")
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient", return_value=mock_mcp_client):
            adapter.connect()
            result = adapter.generate([{"role": "user", "content": "hi"***REMOVED******REMOVED***)
            assert isinstance(result, RuntimeResult)
            assert result.runtime == "test"

    def test_generate_not_connected(self):
        """generate без подключения возвращает ошибку."""
        adapter = StdioMCPAdapter(RuntimeConfig(), "python", [***REMOVED***, "test", "Test")
        result = adapter.generate([{"role": "user", "content": "hi"***REMOVED******REMOVED***)
        assert result.error is not None
        assert "Not connected" in result.error


class TestHTTPMCPAdapter:
    """HTTPMCPAdapter - 4 tests."""

    def test_init(self):
        adapter = HTTPMCPAdapter(RuntimeConfig(), "http://localhost:8765/mcp", "http-test", "HTTP Test")
        assert adapter.name == "http-test"
        assert adapter.adapter_type == AdapterType.HTTP_MCP.value

    def test_connect_fails_without_server(self):
        """connect не может подключиться без сервера."""
        adapter = HTTPMCPAdapter(RuntimeConfig(), "http://localhost:1/mcp", "http-test", "HTTP Test")
        ok = adapter.connect()
        assert ok is False  # Сервер не отвечает

    def test_disconnect_not_connected(self):
        """disconnect без подключения возвращает True."""
        adapter = HTTPMCPAdapter(RuntimeConfig(), "http://localhost:1/mcp", "http-test", "HTTP Test")
        ok = adapter.disconnect()
        assert ok is True

    def test_generate_not_connected(self):
        """generate без подключения возвращает ошибку."""
        adapter = HTTPMCPAdapter(RuntimeConfig(), "http://localhost:1/mcp", "http-test", "HTTP Test")
        result = adapter.generate([{"role": "user", "content": "hi"***REMOVED******REMOVED***)
        assert result.error is not None
        assert "Not connected" in result.error


# ═══════════════════════════════════════════════════════════════
# 3. Adapter Registry
# ═══════════════════════════════════════════════════════════════


class TestAdapterRegistry:
    """AdapterRegistry - 5 tests."""

    def test_default_registry_has_adapters(self):
        """default_adapter_registry имеет stdio_mcp и http_mcp."""
        assert default_adapter_registry.get(AdapterType.STDIO_MCP.value) is StdioMCPAdapter
        assert default_adapter_registry.get(AdapterType.HTTP_MCP.value) is HTTPMCPAdapter

    def test_register_custom_adapter(self):
        """Можно зарегистрировать кастомный адаптер."""
        registry = AdapterRegistry()
        registry.register("custom", StdioMCPAdapter)
        assert registry.get("custom") is StdioMCPAdapter

    def test_get_unknown_returns_none(self):
        """Неизвестный тип адаптера возвращает None."""
        registry = AdapterRegistry()
        assert registry.get("unknown_type") is None

    def test_list_types(self):
        """list_types возвращает зарегистрированные типы."""
        registry = AdapterRegistry()
        registry.register("a", StdioMCPAdapter)
        registry.register("b", HTTPMCPAdapter)
        types = registry.list_types()
        assert "a" in types
        assert "b" in types

    def test_create_adapter(self):
        """create создаёт экземпляр адаптера."""
        registry = AdapterRegistry()
        registry.register("test_type", StdioMCPAdapter)
        adapter = registry.create("test_type", RuntimeConfig(), command="echo", args=[***REMOVED***, runtime_name="test")
        assert adapter is not None
        assert adapter.name == "test"


# ═══════════════════════════════════════════════════════════════
# 4. Runtime Registry
# ═══════════════════════════════════════════════════════════════


class TestRuntimeRegistry:
    """RuntimeRegistry - 12 tests."""

    def test_init_empty(self, tmp_storage: Path):
        """Пустой реестр."""
        registry = RuntimeRegistry(tmp_storage)
        assert len(registry.list()) == 0
        assert registry.get_active() is None

    def test_register(self, tmp_storage: Path):
        """Регистрация Runtime."""
        registry = RuntimeRegistry(tmp_storage)
        rt = RuntimeDefinition(name="freebuff", display_name="Freebuff", status=RuntimeStatus.INSTALLED)
        registry.register(rt)
        assert len(registry.list()) == 1
        assert registry.get("freebuff") is rt

    def test_register_persists(self, tmp_storage: Path):
        """Регистрация сохраняется в JSON."""
        registry = RuntimeRegistry(tmp_storage)
        rt = RuntimeDefinition(name="freebuff", display_name="Freebuff", status=RuntimeStatus.INSTALLED)
        registry.register(rt)

        # Проверяем что файл создан
        assert tmp_storage.exists()
        data = json.loads(tmp_storage.read_text())
        assert len(data["runtimes"***REMOVED***) == 1

    def test_load_persisted(self, tmp_storage: Path):
        """Загрузка из сохранённого файла."""
        registry1 = RuntimeRegistry(tmp_storage)
        registry1.register(RuntimeDefinition(
            name="freebuff", display_name="Freebuff", status=RuntimeStatus.CONNECTED,
        ))
        registry1.set_active("freebuff")

        # Новая инстанция — загружаем
        registry2 = RuntimeRegistry(tmp_storage)
        registry2.load()
        assert len(registry2.list()) == 1
        assert registry2.get_active() is not None
        assert registry2.active_name == "freebuff"

    def test_unregister(self, tmp_storage: Path):
        """Удаление Runtime."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(name="test", display_name="Test"))
        assert registry.unregister("test") is True
        assert len(registry.list()) == 0

    def test_unregister_unknown(self, tmp_storage: Path):
        """Удаление несуществующего."""
        registry = RuntimeRegistry(tmp_storage)
        assert registry.unregister("nonexistent") is False

    def test_list_by_status(self, tmp_storage: Path):
        """Фильтрация по статусу."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(name="a", status=RuntimeStatus.INSTALLED))
        registry.register(RuntimeDefinition(name="b", status=RuntimeStatus.CONNECTED))
        registry.register(RuntimeDefinition(name="c", status=RuntimeStatus.CONNECTED))
        connected = registry.list(RuntimeStatus.CONNECTED)
        assert len(connected) == 2
        assert all(rt.status == RuntimeStatus.CONNECTED for rt in connected)

    def test_set_active(self, tmp_storage: Path):
        """set_active устанавливает активный Runtime."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(name="freebuff", display_name="Freebuff"))
        assert registry.set_active("freebuff") is True
        assert registry.active_name == "freebuff"
        assert registry.get_active() is not None

    def test_set_active_unknown(self, tmp_storage: Path):
        """set_active с неизвестным именем возвращает False."""
        registry = RuntimeRegistry(tmp_storage)
        assert registry.set_active("nonexistent") is False

    @pytest.mark.slow  # v5.189.10: discover по FS (~5.7s)
    def test_discover_runtimes(self, tmp_storage: Path):
        """discover находит установленные Runtime."""
        registry = RuntimeRegistry(tmp_storage)
        discovered = registry.discover()
        # В списке known runtimes должны быть freebuff и claude-code
        known = registry.list_known()
        names = [k["name"***REMOVED*** for k in known***REMOVED***
        assert "freebuff" in names
        assert "claude-code" in names

    def test_list_known(self, tmp_storage: Path):
        """list_known возвращает все известные Runtime."""
        registry = RuntimeRegistry(tmp_storage)
        known = registry.list_known()
        assert len(known) >= 3  # freebuff, claude-code, openclaw
        assert any(k["name"***REMOVED*** == "freebuff" for k in known)

    def test_get_status_structure(self, tmp_storage: Path):
        """get_status возвращает корректную структуру."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(name="freebuff", status=RuntimeStatus.INSTALLED))
        status = registry.get_status()
        assert "active" in status
        assert "total" in status
        assert "connected" in status
        assert "runtimes" in status
        assert "known" in status
        assert status["total"***REMOVED*** == 1

    def test_connect_disconnect(self, tmp_storage: Path):
        """connect/disconnect lifecycle."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(
            name="freebuff",
            display_name="Freebuff",
            status=RuntimeStatus.INSTALLED,
            config=RuntimeConfig(command="echo"),
        ))

        # DEFERRED-7: mock StdioMCPClient — иначе registry.connect() спавнит
        # реальный `python -m freebuff_cli` (subprocess.Popen) и ждёт 30s
        # MCP-инициализацию, которую тот не завершит.
        with patch("freebuff_plugin_03.runtime.adapter.StdioMCPClient") as mock_cls:
            mock_cls.return_value.connect.return_value = False
            # connect (создаст адаптер через mock'нутый клиент)
            with patch("freebuff_plugin_03.runtime.registry.shutil.which", return_value=None):
                with patch("freebuff_plugin_03.runtime.registry.Path.exists", return_value=False):
                    ok, msg = registry.connect("freebuff")
                    # Не подключается (mocked client), но не падает
                    assert isinstance(ok, bool)
                    assert isinstance(msg, str)

        # disconnect
        ok = registry.disconnect("freebuff")
        assert isinstance(ok, bool)


# ═══════════════════════════════════════════════════════════════
# 5. Runtime Capability Registry
# ═══════════════════════════════════════════════════════════════


class TestRuntimeCapabilityRegistry:
    """RuntimeCapabilityRegistry - 8 tests."""

    def test_list_capabilities_empty_registry(self, tmp_storage: Path):
        """Пустой реестр — пустой список capability."""
        registry = RuntimeRegistry(tmp_storage)
        cap_reg = RuntimeCapabilityRegistry(registry)
        caps = cap_reg.list_capabilities()
        assert caps == {***REMOVED***

    def test_list_capabilities_with_runtimes(self, tmp_storage: Path):
        """Реестр с Runtime возвращает capability."""
        runtime_reg = RuntimeRegistry(tmp_storage)
        runtime_reg.register(RuntimeDefinition(
            name="freebuff", display_name="Freebuff",
            capabilities=["coding", "planning"***REMOVED***,
            status=RuntimeStatus.CONNECTED,
        ))
        cap_reg = RuntimeCapabilityRegistry(runtime_reg)
        caps = cap_reg.list_capabilities()
        assert "coding" in caps
        assert "planning" in caps
        assert len(caps["coding"***REMOVED***) == 1

    def test_get_runtime_for_capability(self, tmp_storage: Path):
        """get_runtime_for_capability возвращает лучший Runtime."""
        runtime_reg = RuntimeRegistry(tmp_storage)
        runtime_reg.register(RuntimeDefinition(
            name="freebuff", display_name="Freebuff",
            capabilities=["coding", "planning"***REMOVED***,
            status=RuntimeStatus.CONNECTED,
        ))
        runtime_reg.register(RuntimeDefinition(
            name="claude-code", display_name="Claude Code",
            capabilities=["coding", "review"***REMOVED***,
            status=RuntimeStatus.CONNECTED,
        ))
        cap_reg = RuntimeCapabilityRegistry(runtime_reg)
        best = cap_reg.get_runtime_for_capability("coding")
        assert best is not None
        assert best["runtime"***REMOVED*** == "claude-code"  # Выше confidence

    def test_get_runtime_with_preference(self, tmp_storage: Path):
        """Предпочитаемый Runtime учитывается."""
        runtime_reg = RuntimeRegistry(tmp_storage)
        runtime_reg.register(RuntimeDefinition(
            name="freebuff", display_name="Freebuff",
            capabilities=["coding"***REMOVED***, status=RuntimeStatus.CONNECTED,
        ))
        runtime_reg.register(RuntimeDefinition(
            name="claude-code", display_name="Claude Code",
            capabilities=["coding"***REMOVED***, status=RuntimeStatus.CONNECTED,
        ))
        cap_reg = RuntimeCapabilityRegistry(runtime_reg)
        best = cap_reg.get_runtime_for_capability("coding", preferred_runtime="freebuff")
        assert best is not None
        assert best["runtime"***REMOVED*** == "freebuff"

    def test_get_runtime_unknown_capability(self, tmp_storage: Path):
        """Неизвестная capability возвращает None."""
        cap_reg = RuntimeCapabilityRegistry(RuntimeRegistry(tmp_storage))
        result = cap_reg.get_runtime_for_capability("nonexistent")
        assert result is None

    def test_score_runtime(self, tmp_storage: Path):
        """score_runtime возвращает корректные оценки."""
        cap_reg = RuntimeCapabilityRegistry(RuntimeRegistry(tmp_storage))
        assert cap_reg.score_runtime("freebuff", "coding") == 0.85
        assert cap_reg.score_runtime("claude-code", "review") == 0.95
        assert cap_reg.score_runtime("unknown", "unknown") == 0.3  # По умолчанию

    def test_set_score(self, tmp_storage: Path):
        """set_score переопределяет оценку."""
        cap_reg = RuntimeCapabilityRegistry(RuntimeRegistry(tmp_storage))
        cap_reg.set_score("freebuff", "coding", 0.99)
        assert cap_reg.score_runtime("freebuff", "coding") == 0.99

    def test_all_capability_names(self, tmp_storage: Path):
        """all_capability_names возвращает все известные названия."""
        cap_reg = RuntimeCapabilityRegistry(RuntimeRegistry(tmp_storage))
        names = cap_reg.all_capability_names()
        assert "coding" in names
        assert "review" in names
        assert "planning" in names

    def test_set_score_clamps(self, tmp_storage: Path):
        """set_score ограничивает значение 0.0-1.0."""
        cap_reg = RuntimeCapabilityRegistry(RuntimeRegistry(tmp_storage))
        cap_reg.set_score("freebuff", "coding", 2.0)
        assert cap_reg.score_runtime("freebuff", "coding") == 1.0
        cap_reg.set_score("freebuff", "coding", -1.0)
        assert cap_reg.score_runtime("freebuff", "coding") == 0.0


# ═══════════════════════════════════════════════════════════════
# 6. FreebuffAdapter
# ═══════════════════════════════════════════════════════════════


class TestFreebuffAdapter:
    """FreebuffAdapter - 4 tests."""

    def test_adapter_name(self):
        """FreebuffAdapter имеет правильное имя."""
        adapter = FreebuffAdapter()
        assert adapter.name == "freebuff"
        assert "Freebuff" in adapter.display_name

    def test_capabilities(self):
        """FreebuffAdapter возвращает capability."""
        adapter = FreebuffAdapter()
        caps = adapter.list_capabilities()
        assert len(caps) >= 3
        names = [c.name for c in caps***REMOVED***
        assert "coding" in names
        assert "planning" in names

    def test_find_freebuff_in_path(self):
        """_find_freebuff находит через which."""
        with patch("shutil.which", return_value="/usr/local/bin/freebuff"):
            command, args = FreebuffAdapter._find_freebuff()
            assert command == "/usr/local/bin/freebuff"
            assert "mcp" in args

    def test_find_freebuff_fallback(self):
        """_find_freebuff падает на python -m freebuff_cli."""
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                command, args = FreebuffAdapter._find_freebuff()
                assert "python" in command or "python3" in command


# ═══════════════════════════════════════════════════════════════
# 7. ClaudeCodeAdapter
# ═══════════════════════════════════════════════════════════════


class TestClaudeCodeAdapter:
    """ClaudeCodeAdapter - 4 tests."""

    def test_adapter_name(self):
        """ClaudeCodeAdapter имеет правильное имя."""
        adapter = ClaudeCodeAdapter()
        assert adapter.name == "claude-code"
        assert "Claude" in adapter.display_name

    def test_capabilities(self):
        """ClaudeCodeAdapter возвращает capability."""
        adapter = ClaudeCodeAdapter()
        caps = adapter.list_capabilities()
        assert len(caps) >= 4
        names = [c.name for c in caps***REMOVED***
        assert "review" in names
        assert "documentation" in names

    def test_find_claude_in_path(self):
        """_find_claude находит через which."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            command, args = ClaudeCodeAdapter._find_claude()
            assert command == "/usr/local/bin/claude"
            assert "mcp" in args

    def test_find_claude_fallback(self):
        """_find_claude падает на 'claude' как default."""
        with patch("shutil.which", return_value=None):
            with patch("freebuff_plugin_03.runtime.adapters.claude.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                command, args = ClaudeCodeAdapter._find_claude()
                assert command == "claude"
                assert "mcp" in args


# ═══════════════════════════════════════════════════════════════
# 8. Integration
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 8. Integration
# ═══════════════════════════════════════════════════════════════


class TestProviderLoading:
    """Provider YAML loading (Marketplace-ready) - 6 tests."""

    def test_providers_dir_autodiscovery(self, tmp_storage: Path):
        """RuntimeRegistry загружает провайдеров из YAML при discover()."""
        registry = RuntimeRegistry(tmp_storage)
        # discover() должен вызвать load_providers_from_dir()
        registry.discover()
        assert registry._providers_loaded is True
        assert registry.marketplace_ready is True

    def test_list_known_loads_providers(self, tmp_storage: Path):
        """list_known() лениво загружает провайдеров."""
        registry = RuntimeRegistry(tmp_storage)
        # До вызова — providers не загружены
        assert registry._providers_loaded is False
        known = registry.list_known()
        # После вызова — providers загружены
        assert registry._providers_loaded is True
        assert len(known) >= 3  # freebuff, claude-code, openclaw

    def test_providers_count(self, tmp_storage: Path):
        """providers_count возвращает количество загруженных провайдеров."""
        registry = RuntimeRegistry(tmp_storage)
        registry.load_providers_from_dir()
        assert registry.providers_count >= 3

    def test_register_provider_programmatic(self, tmp_storage: Path):
        """register_provider() добавляет провайдера без YAML-файла."""
        registry = RuntimeRegistry(tmp_storage)
        manifest = {
            "name": "test-runtime",
            "display_name": "Test Runtime",
            "adapter_type": "stdio_mcp",
            "bin_names": ["test-rt"***REMOVED***,
            "args": ["mcp"***REMOVED***,
            "capabilities": {"coding": 0.80, "testing": 0.90***REMOVED***,
            "platforms": ["linux"***REMOVED***,
        ***REMOVED***
        ok = registry.register_provider(manifest)
        assert ok is True
        assert registry.providers_count >= 1
        assert "test-runtime" in registry._known_runtimes

    def test_register_provider_invalid(self, tmp_storage: Path):
        """register_provider() с пустым именем возвращает False."""
        registry = RuntimeRegistry(tmp_storage)
        ok = registry.register_provider({"name": "", "display_name": "Bad"***REMOVED***)
        assert ok is False

    def test_custom_providers_dir(self, tmp_storage: Path):
        """RuntimeRegistry принимает кастомную директорию providers."""
        pytest.importorskip("yaml")  # Требует PyYAML для создания тестового манифеста
        import tempfile, yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            providers_path = Path(tmpdir) / "my_providers"
            providers_path.mkdir()
            # Создаём тестовый манифест
            manifest = {
                "name": "custom-rt",
                "display_name": "Custom Runtime",
                "adapter_type": "http_mcp",
                "bin_names": ["custom"***REMOVED***,
                "args": [***REMOVED***,
                "capabilities": {"coding": 0.75***REMOVED***,
                "platforms": ["linux", "android"***REMOVED***,
            ***REMOVED***
            yaml_file = providers_path / "custom.yaml"
            yaml_file.write_text(yaml.dump(manifest))

            registry = RuntimeRegistry(tmp_storage, providers_dir=str(providers_path))
            count = registry.load_providers_from_dir()
            assert count == 1
            assert "custom-rt" in registry._known_runtimes
            assert registry._known_runtimes["custom-rt"***REMOVED***["capabilities"***REMOVED***["coding"***REMOVED*** == 0.75

    def test_marketplace_ready_property(self, tmp_storage: Path):
        """marketplace_ready — True после загрузки провайдеров."""
        registry = RuntimeRegistry(tmp_storage)
        assert registry.marketplace_ready is False  # Ещё не загружены
        registry.load_providers_from_dir()
        assert registry.marketplace_ready is True

    def test_providers_dir_missing_fallback(self, tmp_storage: Path):
        """Если providers/ не существует — использует hardcoded fallback."""
        registry = RuntimeRegistry(tmp_storage, providers_dir="/nonexistent/path")
        count = registry.load_providers_from_dir()
        # Должен загрузить fallback (встроенные 3 провайдера)
        assert count == 0
        assert registry._providers_loaded is True
        # list_known должен работать через fallback
        known = registry.list_known()
        assert len(known) >= 3


class TestProviderIntegration:
    """Provider + Capability integration — 2 tests."""

    def test_capability_scores_from_provider_manifest(self, tmp_storage: Path):
        """RuntimeCapabilityRegistry загружает scores из provider manifests."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register_provider({
            "name": "test",
            "display_name": "Test",
            "capabilities": {"coding": 0.99, "review": 0.88***REMOVED***,
        ***REMOVED***)
        cap_reg = RuntimeCapabilityRegistry(registry)
        # score должен прийти из манифеста
        score = cap_reg.score_runtime("test", "coding")
        assert score == 0.99
        score = cap_reg.score_runtime("test", "review")
        assert score == 0.88

    def test_legacy_list_format_capabilities(self, tmp_storage: Path):
        """Совместимость со старым форматом capabilities: список вместо словаря."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register_provider({
            "name": "legacy-rt",
            "display_name": "Legacy",
            "capabilities": ["coding", "planning"***REMOVED***,  # Старый формат
        ***REMOVED***)
        cap_reg = RuntimeCapabilityRegistry(registry)
        score = cap_reg.score_runtime("legacy-rt", "coding")
        assert score == 0.5  # По умолчанию для старого формата


class TestIntegration:
    """Integration tests - 3 tests."""

    def test_registry_with_freebuff_adapter(self, tmp_storage: Path):
        """RuntimeRegistry + FreebuffAdapter интеграция."""
        registry = RuntimeRegistry(tmp_storage)
        rt = RuntimeDefinition(
            name="freebuff",
            display_name="Freebuff CLI",
            capabilities=["coding", "planning"***REMOVED***,
            status=RuntimeStatus.INSTALLED,
        )
        registry.register(rt)
        registry.set_active("freebuff")

        assert registry.active_name == "freebuff"
        assert registry.get("freebuff") is rt

        # Capability registry
        cap_reg = RuntimeCapabilityRegistry(registry)
        best = cap_reg.get_runtime_for_capability("coding")
        assert best is not None
        assert best["runtime"***REMOVED*** == "freebuff"

    def test_multiple_runtimes_capability_selection(self, tmp_storage: Path):
        """Выбор между multiple Runtime по capability."""
        registry = RuntimeRegistry(tmp_storage)
        registry.register(RuntimeDefinition(
            name="freebuff", display_name="Freebuff",
            capabilities=["coding", "planning"***REMOVED***,
            status=RuntimeStatus.CONNECTED,
        ))
        registry.register(RuntimeDefinition(
            name="claude-code", display_name="Claude Code",
            capabilities=["coding", "review", "documentation"***REMOVED***,
            status=RuntimeStatus.CONNECTED,
        ))

        cap_reg = RuntimeCapabilityRegistry(registry)

        # Для review — лучший claude-code
        review_rt = cap_reg.get_runtime_for_capability("review")
        assert review_rt["runtime"***REMOVED*** == "claude-code"

        # Для coding — лучший claude-code (0.95 > 0.85)
        coding_rt = cap_reg.get_runtime_for_capability("coding")
        assert coding_rt["runtime"***REMOVED*** == "claude-code"

    def test_registry_save_load_cycle(self, tmp_storage: Path):
        """Цикл save/load сохраняет состояние."""
        # Save
        reg1 = RuntimeRegistry(tmp_storage)
        reg1.register(RuntimeDefinition(name="freebuff", display_name="Freebuff", status=RuntimeStatus.INSTALLED))
        reg1.set_active("freebuff")

        # Load
        reg2 = RuntimeRegistry(tmp_storage)
        reg2.load()
        assert reg2.active_name == "freebuff"
        rt = reg2.get("freebuff")
        assert rt is not None
        assert rt.status == RuntimeStatus.INSTALLED
