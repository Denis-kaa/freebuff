"""RuntimeRegistry + RuntimeCapabilityRegistry (восстановлено v5.189.88).

Контракт: tests_09/test_runtime_abstraction.py. Персистентность — JSON,
провайдеры — YAML-манифесты из providers-директории с builtin-fallback.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from plugins_04.runtime import (
    AdapterType,
    RuntimeConfig,
    RuntimeDefinition,
    RuntimeStatus,
)

# Директория провайдеров по умолчанию (Marketplace-ready)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROVIDERS_DIR = _REPO_ROOT / "runtime_05" / "providers"

# Builtin-fallback: минимум 3 известных runtime (если providers/ пуст/отсутствует)
_BUILTIN_PROVIDERS: List[Dict[str, Any]] = [
    {
        "name": "freebuff",
        "display_name": "Freebuff CLI",
        "adapter_type": "stdio_mcp",
        "bin_names": ["freebuff"],
        "args": ["mcp"],
        "capabilities": {"coding": 0.85, "planning": 0.80, "research": 0.75},
        "platforms": ["linux", "macos", "windows"],
    },
    {
        "name": "claude-code",
        "display_name": "Claude Code",
        "adapter_type": "stdio_mcp",
        "bin_names": ["claude"],
        "args": ["mcp"],
        "capabilities": {"coding": 0.95, "review": 0.95, "documentation": 0.90, "testing": 0.85},
        "platforms": ["linux", "macos", "windows"],
    },
    {
        "name": "openclaw",
        "display_name": "OpenClaw",
        "adapter_type": "stdio_mcp",
        "bin_names": ["openclaw"],
        "args": ["mcp"],
        "capabilities": {"testing": 0.70, "automation": 0.75},
        "platforms": ["linux", "macos"],
    },
]


def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


class RuntimeRegistry:
    """Реестр runtime с JSON-персистентностью и provider-манифестами."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        providers_dir: Optional[str] = None,
    ) -> None:
        self.storage_path = storage_path
        self.providers_dir = providers_dir or str(DEFAULT_PROVIDERS_DIR)
        self._runtimes: Dict[str, RuntimeDefinition] = {}
        self.active_name: Optional[str] = None
        self._known_runtimes: Dict[str, Dict[str, Any]] = {}
        self._providers_loaded = False
        self._adapters: Dict[str, Any] = {}
        self.load()

    # -- persistence -------------------------------------------------

    def _save(self) -> None:
        if self.storage_path is None:
            return
        data = {
            "runtimes": [rt.to_dict() for rt in self._runtimes.values()],
            "active": self.active_name,
        }
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def load(self) -> None:
        """Загрузка состояния из JSON (при наличии файла)."""
        if self.storage_path is None or not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for raw in data.get("runtimes", []):
            if isinstance(raw, dict):
                rt = RuntimeDefinition.from_dict(raw)
                if rt.name:
                    self._runtimes[rt.name] = rt
        active = data.get("active")
        self.active_name = active if isinstance(active, str) else None

    # -- CRUD ----------------------------------------------------------

    def register(self, definition: RuntimeDefinition) -> None:
        self._runtimes[definition.name] = definition
        self._save()

    def get(self, name: str) -> Optional[RuntimeDefinition]:
        return self._runtimes.get(name)

    def unregister(self, name: str) -> bool:
        if name not in self._runtimes:
            return False
        del self._runtimes[name]
        if self.active_name == name:
            self.active_name = None
        self._save()
        return True

    def list(self, status: Optional[RuntimeStatus] = None) -> List[RuntimeDefinition]:
        runtimes = list(self._runtimes.values())
        if status is not None:
            runtimes = [rt for rt in runtimes if rt.status == status]
        return runtimes

    def set_active(self, name: str) -> bool:
        if name not in self._runtimes:
            return False
        self.active_name = name
        self._save()
        return True

    def get_active(self) -> Optional[RuntimeDefinition]:
        if self.active_name is None:
            return None
        return self._runtimes.get(self.active_name)

    # -- providers / known runtimes -------------------------------------

    @property
    def marketplace_ready(self) -> bool:
        return self._providers_loaded

    @property
    def providers_count(self) -> int:
        return len(self._known_runtimes)

    def load_providers_from_dir(self) -> int:
        """Загрузка YAML-манифестов; при нуле файлов — builtin fallback."""
        count = 0
        providers = Path(self.providers_dir)
        if providers.is_dir():
            for yaml_file in sorted(providers.glob("*.yaml")) + sorted(providers.glob("*.yml")):
                manifest = _load_yaml(yaml_file)
                if manifest and self.register_provider(manifest):
                    count += 1
        self._providers_loaded = True
        if count == 0:
            # Fallback: встроенные известные runtime
            for manifest in _BUILTIN_PROVIDERS:
                self.register_provider(manifest)
        return count

    def register_provider(self, manifest: Dict[str, Any]) -> bool:
        name = manifest.get("name") or ""
        if not isinstance(name, str) or not name.strip():
            return False
        caps_raw = manifest.get("capabilities", {})
        if isinstance(caps_raw, dict):
            capabilities: Dict[str, Any] = dict(caps_raw)
            cap_list = list(caps_raw.keys())
        elif isinstance(caps_raw, list):
            capabilities = {}  # legacy-формат: список без scores
            cap_list = [str(c) for c in caps_raw]
        else:
            capabilities = {}
            cap_list = []
        self._known_runtimes[name] = {
            "name": name,
            "display_name": manifest.get("display_name", name),
            "adapter_type": manifest.get("adapter_type", AdapterType.STDIO_MCP.value),
            "bin_names": list(manifest.get("bin_names", [])),
            "args": list(manifest.get("args", [])),
            "capabilities": capabilities,
            "_capability_list": cap_list,
            "platforms": list(manifest.get("platforms", [])),
        }
        return True

    def discover(self) -> List[str]:
        """Поиск установленных runtime по bin_names из манифестов."""
        self.list_known()
        discovered: List[str] = []
        for name, info in self._known_runtimes.items():
            for bin_name in info.get("bin_names", []):
                if shutil.which(bin_name):
                    if name not in self._runtimes:
                        self.register(RuntimeDefinition(
                            name=name,
                            display_name=info.get("display_name", name),
                            status=RuntimeStatus.INSTALLED,
                            capabilities=list(info.get("_capability_list", [])),
                        ))
                    discovered.append(name)
                    break
        return discovered

    def list_known(self) -> List[Dict[str, Any]]:
        """Все известные runtime (лениво загружает провайдеров)."""
        if not self._providers_loaded:
            self.load_providers_from_dir()
        return [dict(info) for info in self._known_runtimes.values()]

    # -- lifecycle / status ---------------------------------------------

    def connect(self, name: str) -> Tuple[bool, str]:
        rt = self._runtimes.get(name)
        if rt is None:
            return False, f"Unknown runtime: {name}"
        command = rt.config.command
        args = list(rt.config.args)
        if command:
            resolved = shutil.which(command)
            if resolved is None and not Path(command).exists():
                return False, f"Command not found: {command}"
        else:
            info = self._known_runtimes.get(name) or {}
            bin_names = info.get("bin_names", [])
            resolved = next((shutil.which(b) for b in bin_names if shutil.which(b)), None)
            if resolved is None:
                return False, f"Binary not found for {name}: {bin_names}"
            command = resolved
            args = list(info.get("args", []))
        from plugins_04.runtime.adapter import default_adapter_registry

        adapter_cls = default_adapter_registry.get(rt.adapter_type or AdapterType.STDIO_MCP.value)
        if adapter_cls is None:
            return False, f"Unknown adapter type: {rt.adapter_type}"
        try:
            adapter = adapter_cls(rt.config, command=command, args=args, name=name, display_name=rt.display_name)  # type: ignore[call-arg,misc]
        except TypeError as exc:
            # Адаптер с другой сигнатурой конструктора (напр. HTTPMCPAdapter)
            try:
                adapter = adapter_cls(rt.config, url=rt.config.url, name=name, display_name=rt.display_name)  # type: ignore[call-arg,misc]
            except Exception:
                return False, f"Adapter init failed: {exc}"
        try:
            ok = bool(adapter.connect())
        except Exception as exc:
            return False, f"Connect failed: {exc}"
        if ok:
            rt.status = RuntimeStatus.CONNECTED
            self._save()
            return True, f"Connected to {name}"
        return False, f"Failed to connect to {name}"

    def disconnect(self, name: str) -> bool:
        rt = self._runtimes.get(name)
        if rt is None:
            return False
        adapter = self._adapters.pop(name, None)
        if adapter is not None:
            try:
                adapter.disconnect()
            except Exception:
                pass
        rt.status = RuntimeStatus.INSTALLED
        self._save()
        return True

    def get_adapter(self, name: str) -> Optional[Any]:
        """Живой адаптер runtime (кэшируется; None для неизвестного имени)."""
        if name in self._adapters:
            return self._adapters[name]
        rt = self._runtimes.get(name)
        if rt is None:
            return None
        from plugins_04.runtime.adapter import default_adapter_registry

        adapter_cls = default_adapter_registry.get(rt.adapter_type or AdapterType.STDIO_MCP.value)
        if adapter_cls is None:
            return None
        try:
            adapter = default_adapter_registry.create(
                rt.adapter_type or AdapterType.STDIO_MCP.value,
                rt.config,
                command=rt.config.command or name,
                args=list(rt.config.args),
                runtime_name=name,
                display_name=rt.display_name or name,
                url=rt.config.url,
            )
        except Exception:
            return None
        if adapter is not None:
            self._adapters[name] = adapter
        return adapter

    def get_status(self) -> Dict[str, Any]:
        runtimes = self.list()
        connected = [rt.name for rt in runtimes if rt.status == RuntimeStatus.CONNECTED]
        return {
            "active": self.active_name,
            "total": len(runtimes),
            "connected": connected,
            "runtimes": [
                {"name": rt.name, "status": rt.status.value, "capabilities": list(rt.capabilities)}
                for rt in runtimes
            ],
            "known": self.list_known(),
        }


# Базовые scores для capability-выбора (до provider-манифестов)
_BASE_SCORES: Dict[Tuple[str, str], float] = {
    ("freebuff", "coding"): 0.85,
    ("claude-code", "coding"): 0.95,
    ("claude-code", "review"): 0.95,
}

_DEFAULT_CAPABILITY_NAMES = [
    "coding", "planning", "review", "documentation", "testing",
    "research", "automation", "communication",
]


class RuntimeCapabilityRegistry:
    """Capability-индекс над RuntimeRegistry: кто лучший для задачи."""

    def __init__(self, registry: RuntimeRegistry) -> None:
        self._registry = registry
        self._score_overrides: Dict[Tuple[str, str], float] = {}

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        # 1) Явные overrides
        key = (runtime_name, capability)
        if key in self._score_overrides:
            return self._score_overrides[key]
        # 2) Provider-манифест (dict-формат со scores)
        known = self._registry._known_runtimes.get(runtime_name)
        if known is not None:
            caps = known.get("capabilities")
            if isinstance(caps, dict) and capability in caps:
                try:
                    return float(caps[capability])
                except (TypeError, ValueError):
                    pass
        # 3) Базовая таблица известных пар
        if key in _BASE_SCORES:
            return _BASE_SCORES[key]
        if known is not None and capability in known.get("_capability_list", []):
            return 0.5  # legacy list-формат
        # 4) Зарегистрированный runtime со списком capabilities
        rt = self._registry.get(runtime_name)
        if rt is not None and capability in rt.capabilities:
            return 0.5
        return 0.3

    def set_score(self, runtime_name: str, capability: str, score: float) -> None:
        clamped = max(0.0, min(1.0, float(score)))
        self._score_overrides[(runtime_name, capability)] = clamped

    def all_capability_names(self) -> List[str]:
        names = set(_DEFAULT_CAPABILITY_NAMES)
        names.update(k[1] for k in _BASE_SCORES)
        for known in self._registry._known_runtimes.values():
            caps = known.get("capabilities")
            if isinstance(caps, dict):
                names.update(caps.keys())
            names.update(known.get("_capability_list", []))
        return sorted(names)

    def list_capabilities(self) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for rt in self._registry.list():
            for cap in rt.capabilities:
                result.setdefault(cap, []).append(rt.name)
        return result

    def get_runtime_for_capability(
        self,
        capability: str,
        preferred_runtime: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        candidates = self.list_capabilities().get(capability, [])
        if not candidates:
            return None
        scored = [(self.score_runtime(name, capability), name) for name in candidates]
        if preferred_runtime is not None and preferred_runtime in candidates:
            best = preferred_runtime
            best_score = self.score_runtime(preferred_runtime, capability)
        else:
            best_score, best = max(scored, key=lambda pair: (pair[0], pair[1]))
        return {
            "runtime": best,
            "capability": capability,
            "score": best_score,
            "candidates": [{"runtime": n, "score": s} for s, n in sorted(scored, reverse=True)],
        }
