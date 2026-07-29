"""
Runtime Abstraction Layer — Runtime Registry и Capability Registry.

Спецификация: docs/core/RUNTIME_ABSTRACTION_SPECIFICATION.md §6, §3.3
Основание: VISION_3.0.md §3.5
Marketplace: runtime/MARKETPLACE.md, runtime/providers/README.md
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
***REMOVED***
from typing import Any, Dict, List, Optional, Set, Tuple

from freebuff_plugin.runtime import (
    AdapterType,
    RuntimeCapability,
    RuntimeConfig,
    RuntimeDefinition,
    RuntimeStatus,
)
from freebuff_plugin.runtime.adapter import (
    RuntimeAdapter,
    StdioMCPAdapter,
    default_adapter_registry,
)

# YAML support: try PyYAML, fallback to built-in JSON (for simple manifests)
try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
    _yaml = None  # type: ignore[assignment***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Runtime Registry
# ═══════════════════════════════════════════════════════════════


class RuntimeRegistry:
    """Реестр всех Runtime — установленных, доступных, активных.

    Управляет жизненным циклом Runtime:
      INSTALLED → DISCOVERED → CONNECTED → ACTIVE → DISCONNECTED

    Сохраняет состояние в JSON файл для идемпотентности между сессиями.
    """

    # Default providers directory relative to project root
    DEFAULT_PROVIDERS_DIR = "runtime/providers"

    def __init__(
        self,
        storage_path: Optional[Path***REMOVED*** = None,
        providers_dir: Optional[str***REMOVED*** = None,
    ):
        self._runtimes: Dict[str, RuntimeDefinition***REMOVED*** = {***REMOVED***
        self._adapters: Dict[str, RuntimeAdapter***REMOVED*** = {***REMOVED***
        self._active_name: Optional[str***REMOVED*** = None
        self._storage = storage_path or Path("data/runtime_registry.json")
        self._providers_dir = providers_dir or self.DEFAULT_PROVIDERS_DIR

        # Реестр известных Runtime — загружается из YAML-манифестов
        # при первом вызове load_providers_from_dir() или discover().
        # Hardcoded fallback — только если директория providers/ не найдена.
        self._known_runtimes: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = {***REMOVED***
        self._providers_loaded = False

    # ── Load / Save ──────────────────────────────────────────

    def load(self) -> None:
        """Загружает реестр из storage."""
        if not self._storage.exists():
            return
        try:
            data = json.loads(self._storage.read_text(encoding="utf-8"))
            for item in data.get("runtimes", [***REMOVED***):
                rt = RuntimeDefinition(
                    name=item.get("name", ""),
                    display_name=item.get("display_name", ""),
                    version=item.get("version", "0.0.0"),
                    adapter_type=item.get("adapter_type", AdapterType.STDIO_MCP.value),
                    status=RuntimeStatus(item.get("status", "unknown")),
                    capabilities=item.get("capabilities", [***REMOVED***),
                    bin_path=item.get("bin_path"),
                    error=item.get("error"),
                )
                self._runtimes[rt.name***REMOVED*** = rt
            self._active_name = data.get("active")
        except (json.JSONDecodeError, OSError, ValueError):
            pass  # Повреждённый файл — игнорируем

    def save(self) -> None:
        """Сохраняет реестр в storage."""
        self._storage.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "active": self._active_name,
            "runtimes": [
                {
                    "name": rt.name,
                    "display_name": rt.display_name,
                    "version": rt.version,
                    "adapter_type": rt.adapter_type,
                    "status": rt.status.value,
                    "capabilities": rt.capabilities,
                    "bin_path": rt.bin_path,
                    "error": rt.error,
                ***REMOVED***
                for rt in self._runtimes.values()
            ***REMOVED***,
        ***REMOVED***
        self._storage.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Register / Unregister ────────────────────────────────

    def register(self, runtime: RuntimeDefinition) -> None:
        """Зарегистрировать Runtime."""
        self._runtimes[runtime.name***REMOVED*** = runtime
        self.save()

    def unregister(self, name: str) -> bool:
        """Удалить Runtime из реестра."""
        if name in self._runtimes:
            del self._runtimes[name***REMOVED***
            if self._active_name == name:
                self._active_name = None
            self.save()
            return True
        return False

    # ── Query ────────────────────────────────────────────────

    def get(self, name: str) -> Optional[RuntimeDefinition***REMOVED***:
        """Получить Runtime по имени."""
        return self._runtimes.get(name)

    def list(self, status: Optional[RuntimeStatus***REMOVED*** = None) -> List[RuntimeDefinition***REMOVED***:
        """Список Runtime, опционально фильтр по статусу."""
        if status is None:
            return list(self._runtimes.values())
        return [rt for rt in self._runtimes.values() if rt.status == status***REMOVED***

    def list_known(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список известных Runtime (включая не установленные)."""
        # Lazy-load providers если ещё не загружены
        if not self._providers_loaded:
            self.load_providers_from_dir()

        result = [***REMOVED***
        for name, info in self._known_runtimes.items():
            existing = self._runtimes.get(name)
            result.append({
                "name": name,
                "display_name": info["display_name"***REMOVED***,
                "installed": existing is not None,
                "status": existing.status.value if existing else RuntimeStatus.UNKNOWN.value,
                "capabilities": info.get("capabilities", [***REMOVED***),
                "platforms": info.get("platforms", [***REMOVED***),
                "requires_api_key": info.get("requires_api_key", False),
            ***REMOVED***)
        return result

    # ── Active Runtime ───────────────────────────────────────

    def set_active(self, name: str) -> bool:
        """Установить Runtime как активный по умолчанию."""
        if name not in self._runtimes:
            return False
        self._active_name = name
        self.save()
        return True

    def get_active(self) -> Optional[RuntimeDefinition***REMOVED***:
        """Получить активный Runtime."""
        if self._active_name:
            return self._runtimes.get(self._active_name)
        return None

    @property
    def active_name(self) -> Optional[str***REMOVED***:
        return self._active_name

    # ── Discover ─────────────────────────────────────────────

    # ── Provider Loading (Marketplace-ready) ───────────────

    def load_providers_from_dir(self, directory: Optional[str***REMOVED*** = None) -> int:
        """Загружает все YAML-манифесты из директории providers.

        Marketplace-ready: новый Runtime добавляется YAML-файлом,
        без изменения кода ядра.

        Args:
            directory: путь к директории с YAML (по умолчанию self._providers_dir)

        Returns:
            количество загруженных манифестов
        """
        target = Path(directory or self._providers_dir)
        if not target.exists() or not target.is_dir():
            self._providers_loaded = True
            self._load_builtin_fallback()
            return 0

        count = 0
        for yaml_file in sorted(target.glob("*.yaml")):
            manifest = self._parse_provider_yaml(yaml_file)
            if manifest:
                name = manifest.get("name", "")
                if name:
                    self._known_runtimes[name***REMOVED*** = manifest
                    count += 1

        # Загружаем также .yml файлы
        for yml_file in sorted(target.glob("*.yml")):
            manifest = self._parse_provider_yaml(yml_file)
            if manifest:
                name = manifest.get("name", "")
                if name:
                    self._known_runtimes[name***REMOVED*** = manifest
                    count += 1

        if count == 0:
            self._load_builtin_fallback()

        self._providers_loaded = True
        return count

    def register_provider(self, manifest: Dict[str, Any***REMOVED***) -> bool:
        """Зарегистрировать провайдера программно (без YAML-файла).

        Args:
            manifest: словарь в формате provider manifest

        Returns:
            True если провайдер зарегистрирован успешно
        """
        name = manifest.get("name", "")
        if not name:
            return False
        self._known_runtimes[name***REMOVED*** = manifest
        if not self._providers_loaded:
            self._providers_loaded = True
        return True

    def _parse_provider_yaml(self, path: Path) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Парсит YAML-манифест провайдера.

        Поддерживает PyYAML и fallback на ручной парсинг ключ-значение.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        if _HAS_YAML:
            try:
                return _yaml.safe_load(content)  # type: ignore[union-attr***REMOVED***
            except Exception:
                return None

        # Fallback: ручной парсинг простого YAML (ключ: значение)
        return self._parse_simple_yaml(content)

    @staticmethod
    def _parse_simple_yaml(content: str) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Ручной парсинг простого YAML без зависимостей.

        Обрабатывает:
        - Плоские ключ-значение (name: freebuff)
        - Индентированные секции (capabilities, bin_names, platforms, args)
        - Индентированные key: value пары внутри секций (coding: 0.85)
        - Списковые элементы с '- ' (bin_names, platforms, args)
        Не поддерживает многострочные строки (>, |) —
        для полной поддержки установите PyYAML.
        """
        result: Dict[str, Any***REMOVED*** = {***REMOVED***
        capabilities: Dict[str, float***REMOVED*** = {***REMOVED***
        bin_names: List[str***REMOVED*** = [***REMOVED***
        platforms: List[str***REMOVED*** = [***REMOVED***
        args: List[str***REMOVED*** = [***REMOVED***
        current_section: Optional[str***REMOVED*** = None

        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                current_section = None
                continue

            # Проверяем: внутри секции или нет?
            if ":" in stripped and not stripped.startswith("-"):
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if value:
                    # Есть значение справа от ':'
                    if current_section == "capabilities":
                        # Индентированный ключ внутри секции capabilities
                        # Формат: coding: 0.85
                        try:
                            capabilities[key***REMOVED*** = float(value)
                        except ValueError:
                            capabilities[key***REMOVED*** = 0.5
                        continue  # Не сбрасываем current_section

                    elif current_section == "install":
                        # Индентированный ключ внутри install
                        # Пропускаем — install не парсим
                        continue

                    elif current_section == "requirements":
                        # Индентированный ключ внутри requirements
                        continue

                    else:
                        # Топ-уровень ключ-значение
                        current_section = None
                        if key == "name":
                            result["name"***REMOVED*** = value
                        elif key == "display_name":
                            result["display_name"***REMOVED*** = value
                        elif key == "adapter_type":
                            result["adapter_type"***REMOVED*** = value
                        elif key == "requires_api_key":
                            result["requires_api_key"***REMOVED*** = value.lower() == "true"
                        elif key == "api_key_env":
                            result["api_key_env"***REMOVED*** = value
                        elif key == "docs_url":
                            result["docs_url"***REMOVED*** = value
                        elif key == "recipe":
                            result["recipe"***REMOVED*** = value
                        elif key == "maintainer":
                            result["maintainer"***REMOVED*** = value
                        elif key == "version":
                            pass  # version: auto — игнорируем
                else:
                    # Нет значения — это заголовок секции
                    current_section = key

            elif current_section == "capabilities" and stripped.startswith("- "):
                # Формат: - coding: 0.85 (списковый формат capabilities)
                item = stripped[2:***REMOVED***
                if ":" in item:
                    cap_name, _, cap_val = item.partition(":")
                    cap_name = cap_name.strip()
                    try:
                        capabilities[cap_name***REMOVED*** = float(cap_val.strip())
                    except ValueError:
                        capabilities[cap_name***REMOVED*** = 0.5
                else:
                    capabilities[item.strip()***REMOVED*** = 0.5

            elif current_section == "bin_names" and stripped.startswith("- "):
                bin_names.append(stripped[2:***REMOVED***.strip())

            elif current_section == "platforms" and stripped.startswith("- "):
                platforms.append(stripped[2:***REMOVED***.strip())

            elif current_section == "args" and stripped.startswith("- "):
                args.append(stripped[2:***REMOVED***.strip())

        if "name" not in result:
            return None

        # Присваиваем собранные значения
        result["capabilities"***REMOVED*** = capabilities
        result["bin_names"***REMOVED*** = bin_names if bin_names else [result["name"***REMOVED******REMOVED***
        result["platforms"***REMOVED*** = platforms if platforms else ["linux"***REMOVED***
        result["args"***REMOVED*** = args

        # Defaults для отсутствующих полей
        result.setdefault("display_name", result["name"***REMOVED***)
        result.setdefault("adapter_type", AdapterType.STDIO_MCP.value)
        result.setdefault("requires_api_key", False)

        return result

    def _load_builtin_fallback(self) -> None:
        """Загружает hardcoded fallback, если providers/ не найдена.

        Мержит builtin runtimes с уже зарегистрированными провайдерами.
        Не перезаписывает существующие записи.
        """

        builtins = {
            "freebuff": {
                "display_name": "Freebuff CLI (Codebuff)",
                "adapter_type": AdapterType.STDIO_MCP.value,
                "capabilities": {
                    "coding": 0.85, "planning": 0.85, "architecture": 0.80,
                    "testing": 0.80, "research": 0.70,
                ***REMOVED***,
                "bin_names": ["freebuff", "codebuff"***REMOVED***,
                "args": ["mcp"***REMOVED***,
                "platforms": ["linux", "macos", "android"***REMOVED***,
            ***REMOVED***,
            "claude-code": {
                "display_name": "Claude Code",
                "adapter_type": AdapterType.STDIO_MCP.value,
                "capabilities": {
                    "coding": 0.95, "review": 0.95, "architecture": 0.85,
                    "documentation": 0.90, "planning": 0.80,
                ***REMOVED***,
                "bin_names": ["claude"***REMOVED***,
                "args": ["mcp"***REMOVED***,
                "platforms": ["linux", "macos"***REMOVED***,
            ***REMOVED***,
            "openclaw": {
                "display_name": "OpenClaw",
                "adapter_type": AdapterType.STDIO_MCP.value,
                "capabilities": {"coding": 0.70, "research": 0.85***REMOVED***,
                "bin_names": [***REMOVED***,
                "args": [***REMOVED***,
                "platforms": ["linux", "macos", "android"***REMOVED***,
            ***REMOVED***,
        ***REMOVED***

        # Мержим: builtin не перезаписывает уже зарегистрированные
        for name, info in builtins.items():
            if name not in self._known_runtimes:
                self._known_runtimes[name***REMOVED*** = info

    def discover(self) -> List[RuntimeDefinition***REMOVED***:
        """Авто-обнаружение установленных Runtime.

        Загружает YAML-манифесты из runtime/providers/,
        затем ищет бинарники (which, ~/.local/bin/).

        Marketplace-ready: новый Runtime добавляется YAML-файлом
        без изменения этого метода.
        """
        # Lazy-load providers из YAML
        if not self._providers_loaded:
            self.load_providers_from_dir()

        discovered: List[RuntimeDefinition***REMOVED*** = [***REMOVED***

        for name, info in self._known_runtimes.items():
            bin_path = self._find_binary(info.get("bin_names", [***REMOVED***))
            if bin_path:
                version = self._detect_version(bin_path, name)
                # Конвертируем capabilities: dict → list для RuntimeDefinition
                caps_raw = info.get("capabilities", [***REMOVED***)
                if isinstance(caps_raw, dict):
                    caps_list = list(caps_raw.keys())
                else:
                    caps_list = list(caps_raw) if caps_raw else [***REMOVED***
                rt = RuntimeDefinition(
                    name=name,
                    display_name=info["display_name"***REMOVED***,
                    version=version,
                    adapter_type=info["adapter_type"***REMOVED***,
                    status=RuntimeStatus.DISCOVERED,
                    capabilities=caps_list,
                    bin_path=str(bin_path),
                    config=RuntimeConfig(
                        command=str(bin_path),
                        args=info.get("args", [***REMOVED***),
                    ),
                )
                self._runtimes[name***REMOVED*** = rt
                discovered.append(rt)

        if discovered:
            self.save()
        return discovered

    def _find_binary(self, bin_names: List[str***REMOVED***) -> Optional[Path***REMOVED***:
        """Ищет бинарник Runtime в PATH."""
        for name in bin_names:
            path = shutil.which(name)
            if path:
                return Path(path)

        # Дополнительные пути
        extra_paths = [
            Path.home() / ".local" / "bin",
            Path("/usr/local/bin"),
            Path("/data/data/com.termux/files/usr/bin"),
        ***REMOVED***
        for name in bin_names:
            for extra in extra_paths:
                candidate = extra / name
                if candidate.exists():
                    return candidate
        return None

    def _detect_version(self, bin_path: Path, name: str) -> str:
        """Определяет версию Runtime."""
        try:
            result = subprocess.run(
                [str(bin_path), "--version"***REMOVED***,
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:20***REMOVED***
        except Exception:
            pass
        return "unknown"

    @property
    def providers_dir(self) -> str:
        """Путь к директории провайдеров."""
        return self._providers_dir

    @property
    def providers_count(self) -> int:
        """Количество загруженных провайдеров."""
        return len(self._known_runtimes)

    @property
    def marketplace_ready(self) -> bool:
        """Проверяет, загружены ли провайдеры из YAML (а не hardcoded fallback)."""
        return self._providers_loaded and bool(self._known_runtimes)

    # ── Adapter Management ───────────────────────────────────

    def get_adapter(self, name: str) -> Optional[RuntimeAdapter***REMOVED***:
        """Получить адаптер для Runtime."""
        return self._adapters.get(name)

    def register_adapter(self, name: str, adapter: RuntimeAdapter) -> None:
        """Зарегистрировать экземпляр адаптера."""
        self._adapters[name***REMOVED*** = adapter

    def remove_adapter(self, name: str) -> None:
        """Удалить адаптер."""
        self._adapters.pop(name, None)

    def connect(self, name: str) -> Tuple[bool, str***REMOVED***:
        """Подключиться к Runtime: найти бинарник, создать адаптер, выполнить handshake."""
        # Lazy-load providers если ещё не загружены
        if not self._providers_loaded:
            self.load_providers_from_dir()

        rt = self._runtimes.get(name)
        if rt is None:
            # Пробуем обнаружить
            discovered = self.discover()
            rt = self._runtimes.get(name)
            if rt is None:
                return False, f"Runtime not found: {name***REMOVED***"

        if name in self._adapters:
            adapter = self._adapters[name***REMOVED***
            if adapter.is_connected():
                return True, f"Already connected: {name***REMOVED***"

        # Создаём адаптер
        known = self._known_runtimes.get(name, {***REMOVED***)
        bin_path = rt.bin_path or self._find_binary(known.get("bin_names", [***REMOVED***))
        if not bin_path and name == "freebuff":
            # Fallback: текущий Python
            bin_path = Path(sys.executable)
            args = ["-m", "freebuff_cli"***REMOVED***
        else:
            args = known.get("args", [***REMOVED***)

        if not bin_path:
            return False, f"Binary not found for: {name***REMOVED***"

        config = RuntimeConfig(
            command=str(bin_path),
            args=args,
            work_dir=str(Path.cwd()),
            timeout_seconds=rt.config.timeout_seconds if rt.config else 300,
        )

        adapter = StdioMCPAdapter(
            config=config,
            command=str(bin_path),
            args=args,
            runtime_name=name,
            display_name=rt.display_name,
        )

        ok = adapter.connect()
        if ok:
            self._adapters[name***REMOVED*** = adapter
            rt.status = RuntimeStatus.CONNECTED
            rt.error = None
            self.save()
            return True, f"Connected to {name***REMOVED***"
        else:
            rt.status = RuntimeStatus.ERROR
            rt.error = "handshake failed"
            self.save()
            return False, f"Failed to connect to {name***REMOVED***"

    def disconnect(self, name: str) -> bool:
        """Отключиться от Runtime."""
        adapter = self._adapters.pop(name, None)
        if adapter:
            try:
                adapter.disconnect()
            except Exception:
                pass
            rt = self._runtimes.get(name)
            if rt:
                rt.status = RuntimeStatus.DISCONNECTED
                self.save()
            return True
        return False

    def is_connected(self, name: str) -> bool:
        """Проверить, активно ли подключение Runtime."""
        adapter = self._adapters.get(name)
        if adapter is None:
            return False
        try:
            return adapter.is_connected()
        except Exception:
            return False

    # ── Status ───────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Полный статус реестра Runtime."""
        runtimes = [***REMOVED***
        for name, rt in self._runtimes.items():
            adapter = self._adapters.get(name)
            runtimes.append({
                "name": name,
                "display_name": rt.display_name,
                "version": rt.version,
                "status": rt.status.value,
                "connected": adapter is not None and adapter.is_connected(),
                "active": name == self._active_name,
                "bin_path": rt.bin_path,
                "error": rt.error,
            ***REMOVED***)

        return {
            "active": self._active_name,
            "total": len(self._runtimes),
            "connected": sum(1 for a in self._adapters.values() if a.is_connected()),
            "runtimes": runtimes,
            "known": self.list_known(),
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Runtime Capability Registry
# ═══════════════════════════════════════════════════════════════


class RuntimeCapabilityRegistry:
    """Реестр capability для всех Runtime.

    Позволяет выбрать Runtime по capability:
      capability("coding") → RuntimeDefinition(claude-code, confidence=0.95)
    """

    def __init__(self, runtime_registry: RuntimeRegistry):
        self._registry = runtime_registry

        # Confidence scores — загружаются из provider manifests при первом обращении.
        # Hardcoded здесь ТОЛЬКО если providers/ не найдена (fallback).
        self._default_scores: Dict[str, Dict[str, float***REMOVED******REMOVED*** = {***REMOVED***
        self._scores_loaded = False

    def _ensure_scores_loaded(self) -> None:
        """Lazy-load capability scores из provider manifests."""
        if self._scores_loaded:
            return

        # Загружаем scores из known_runtimes (populated из YAML или fallback)
        # Используем list_known() для ленивой загрузки providers
        if not self._registry._providers_loaded:
            self._registry.list_known()  # Триггерит load_providers_from_dir()

        for name, info in self._registry._known_runtimes.items():
            caps = info.get("capabilities", {***REMOVED***)
            if name not in self._default_scores:
                self._default_scores[name***REMOVED*** = {***REMOVED***
            if isinstance(caps, list):
                # Старый формат: ["coding", "planning"***REMOVED*** — default score 0.5
                for cap in caps:
                    if cap not in self._default_scores[name***REMOVED***:
                        self._default_scores[name***REMOVED***[cap***REMOVED*** = 0.5
            elif isinstance(caps, dict):
                # Новый формат: {"coding": 0.85, "planning": 0.85***REMOVED***
                # Мержим: не перезаписываем пользовательские оценки (set_score)
                for cap_name, cap_score in caps.items():
                    if cap_name not in self._default_scores[name***REMOVED***:
                        self._default_scores[name***REMOVED***[cap_name***REMOVED*** = cap_score

        self._scores_loaded = True

    def list_capabilities(self) -> Dict[str, List[Dict[str, Any***REMOVED******REMOVED******REMOVED***:
        """Все доступные capability: capability_name → [Runtime, ...***REMOVED***."""
        result: Dict[str, List[Dict[str, Any***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        for rt in self._registry.list():
            for cap_name in rt.capabilities:
                if cap_name not in result:
                    result[cap_name***REMOVED*** = [***REMOVED***
                score = self.score_runtime(rt.name, cap_name)
                result[cap_name***REMOVED***.append({
                    "runtime": rt.name,
                    "status": rt.status.value,
                    "confidence": score,
                    "connected": self._registry.is_connected(rt.name),
                ***REMOVED***)
        # Сортируем по confidence (лучшие первые)
        for cap_name in result:
            result[cap_name***REMOVED***.sort(key=lambda x: x["confidence"***REMOVED***, reverse=True)
        return result

    def get_runtime_for_capability(
        self,
        capability: str,
        preferred_runtime: Optional[str***REMOVED*** = None,
    ) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Какой Runtime лучше всего подходит для capability.

        Args:
            capability: название capability (coding, review, ...)
            preferred_runtime: предпочитаемый Runtime (если None — лучший по confidence)

        Returns:
            {runtime, confidence, connected***REMOVED*** или None
        """
        caps = self.list_capabilities()
        if capability not in caps:
            return None

        available = caps[capability***REMOVED***

        if preferred_runtime:
            for item in available:
                if item["runtime"***REMOVED*** == preferred_runtime:
                    return item
            # Предпочитаемый не найден — берём лучший
            return available[0***REMOVED*** if available else None

        # Берём лучший (уже отсортировано по confidence)
        return available[0***REMOVED*** if available else None

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        """Оценка Runtime для capability (0.0 - 1.0).

        Определяется комбинацией:
        - Provider manifest (из YAML capabilities)
        - User override через set_score()
        """
        self._ensure_scores_loaded()
        rt_scores = self._default_scores.get(runtime_name, {***REMOVED***)
        return rt_scores.get(capability, 0.3)  # По умолчанию низкая уверенность

    def set_score(self, runtime_name: str, capability: str, score: float) -> None:
        """Установить пользовательскую оценку (override)."""
        if runtime_name not in self._default_scores:
            self._default_scores[runtime_name***REMOVED*** = {***REMOVED***
        self._default_scores[runtime_name***REMOVED***[capability***REMOVED*** = max(0.0, min(1.0, score))

    def all_capability_names(self) -> List[str***REMOVED***:
        """Список всех известных названий capability."""
        self._ensure_scores_loaded()
        names: Set[str***REMOVED*** = set()
        for rt_name, scores in self._default_scores.items():
            names.update(scores.keys())
        for rt in self._registry.list():
            names.update(rt.capabilities)
        return sorted(names)
