"""core_02/tool_acl.py — Sandbox/Tool-ACL слой (ADR-022).

Fail-closed policy-слой поверх ToolRegistry: принципал (роль) → инструмент →
операция → разрещение. Аддитивный, не трогает существующие инструменты:
работает как gate, подключённый к ``ToolRegistry`` через ``attach_acl``.

Границы (по умолчанию для ВСЕХ ролей, fail-closed):
  B1. path-guard  — параметры ``path/cwd/db_path/destination`` обязаны
      резолвиться внутри workspace root (relative → root; absolute → под root).
  B2. shell-denylist — опасные команды запрещены на уровне сырого текста
      (``rm -rf /``, ``mkfs``, ``dd if=``, fork bomb, ``sudo``, ``curl|sh``).
  B3. network-guard — для ограниченных ролей запрещены private/loopback
      адреса (anti-SSRF); admin-уровень имеет доступ к локальным сервисам.
  B4. deny-wins — явный deny всегда сильнее allow (без пробелов).

Роли по умолчанию (default_policy()):
  - read_only: чтение (file read/exists/list, git status/diff/log, sqlite
    SELECT) — всё остальное DENY; B1–B3 включены.
  - standard: + file write/copy/move/mkdir (внутри root), git add/commit,
    sqlite write, http GET; deny-shell only через B2/B3; deny git push/pull.
  - agent: полный доступ (shell/http/sqlite), deny — только B1/B2 (hard)
    и явный deny git push (платформа не пушит сама, AGENTS.md).
  - admin: то же, что agent + право задавать собственные явные deny-правила
    через ``add_rule``; push по-прежнему DENY по умолчанию.

Правила реестра (MissingRegistry, ADR-022): контракт зафиксирован как
``tool_acl`` (kind=module, factory=security).

Безопасность termux: это политический слой, НЕ OS-sandbox (seccomp/namespaces
недоступны без root на Android). Намеренно fail-closed: отсутствие роли или
правила → DENY с причиной.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

__all__ = [
    "AccessDecision",
    "AclRule",
    "ToolACL",
    "default_policy",
]

# Эффекты
ALLOW = "allow"
DENY = "deny"

# Роли по умолчанию
ROLE_READ_ONLY = "read_only"
ROLE_STANDARD = "standard"
ROLE_AGENT = "agent"

# Инструменты (glob-паттерны), которые захватывает политика
_TOOL_FILE = "file"
_TOOL_GIT = "git"
_TOOL_HTTP = "http"
_TOOL_SHELL = "shell"
_TOOL_SQLITE = "sqlite"

# Параметры, которые содержат операции инструмента
_ACTION_PARAM = {
    "file": "action",
    "git": "command",
    "http": "method",
    "sqlite": "query",
}

# Путевые параметры всех инструментов
_PATH_PARAMS = ("path", "cwd", "db_path", "destination")


@dataclass(frozen=True)
class AccessDecision:
    """Итог проверки ACL для одного вызова инструмента."""

    allowed: bool
    reason: str
    principal: str = "default"
    matched_rules: Tuple[str, ...] = ()
    tool: str = ""


@dataclass(frozen=True)
class AclRule:
    """Одно точечное правило: роль × инструмент(glob) × операция(glob).

    ``op=None`` — правило на инструмент целиком (любая операция).
    ``op`` — значение параметра-операции инструмента (например, ``read``
    для file, ``status`` для git, ``SELECT`` для sqlite, ``GET`` для http).
    """

    role: str
    tool: str
    effect: str  # ALLOW | DENY
    op: Optional[str] = None
    note: str = ""

    def matches(self, role: str, tool: str, operation: Optional[str]) -> bool:
        if role != self.role and self.role != "*":
            return False
        if not fnmatch.fnmatch(tool, self.tool_glob):
            return False
        if self.op is not None:
            if operation is None:
                return False
            if not fnmatch.fnmatch(str(operation).lower(), self.op.lower()):
                return False
        return True


class ToolACL:
    """Fail-closed policy-слой для инструментов ToolRegistry.

    Модель разрешений:
      - ``define_role(name, default_effect=DENY)`` — создать роль;
      - ``allow_tool(role, tool_glob)`` / ``deny_tool(...)`` — базовые
        grant/deny по инструментам;
      - ``add_rule(...)`` — точечные правила (инструмент + операция);
      - ``check(principal, tool, params)`` — решение для вызова.

    Порядок вычисления (fail-closed):
      1. роль неизвестна → DENY;
      2. hard-boundary B1/B2/B3 → DENY (всегда, для всех ролей);
      3. deny-rule точечная или deny_tool → DENY (deny-wins);
      4. grant-rule или allow_tool → ALLOW;
      5. иначе → default-эффект роли (по умолчанию DENY).
    """

    def __init__(self, root: Optional[Path | str] = None) -> None:
        self._root = (Path(root) if root else Path.cwd()).resolve()
        self._default_effects: Dict[str, str] = {}
        self._allow_tools: Dict[str, Set[str]] = {}
        self._deny_tools: Dict[str, Set[str]] = {}
        self._rules: List[AclRule] = []
        # роль × инструмент → разрешённые операции (опциональные restrict-списки)
        self._op_restrict: Dict[Tuple[str, str], Set[str]] = {}
        # deny-списки shell-паттернов (B2) — расширяемые
        self._shell_patterns: List[re.Pattern[str]] = [
            re.compile(r"\brm\s+(-[a-z)*[rf])+\s+(/|~|/[\w.-]+|\.\s*/\s*)$|rm\s+-rf\s*/$", re.IGNORECASE),
            re.compile(r"\bmkfs\b"), re.compile(r"\bdd\s+if=", re.IGNORECASE),
            re.compile(r"\b:\(\)\s*\{\s*:\|:&\s*\*);:"),
            re.compile(r"\bsudo\b", re.IGNORECASE),
            re.compile(r">\s*/dev/(sd|hd|xvd)", re.IGNORECASE),
            re.compile(r"\b(chmod|chown)\b.*(-R\s*)?\s*7[0-7){2]\s+/", re.IGNORECASE),
            re.compile(r"\b(wget|curl)\b.*\|\s*(ba)?sh\b", re.IGNORECASE),
            re.compile(r"\bbash\s+-c\s+['\").*curl", re.IGNORECASE),
            re.compile(r"\bpoweroff\b|\breboot\b|\bshutdown\b", re.IGNORECASE),
            re.compile(r"\b>+\s*/dev/\w+\s*(;|&&|\||$)"),
        ]

    # ── конфигурация ─────────────────────────────────────────────────

    def define_role(self, role: str, default_effect: str = DENY) -> "ToolACL":
        """Создать роль с fallback-эффектом (по умолчанию DENY = fail-closed)."""
        if default_effect not in (ALLOW, DENY):
            raise ValueError(f"Невалидный default_effect: {default_effect!r}")
        self._default_effects[role] = default_effect
        self._allow_tools.setdefault(role, set())
        self._deny_tools.setdefault(role, set())
        return self

    def allow_tool(self, role: str, tool_glob: str) -> "ToolACL":
        """Разрешить role вызывать инструменты, попадающие под glob."""
        self.define_role(role)
        self._allow_tools[role].add(tool_glob)
        return self

    def deny_tool(self, role: str, tool_glob: str) -> "ToolACL":
        """Запретить role инструменты, попадающие под glob (deny-wins)."""
        self.define_role(role)
        self._deny_tools[role].add(tool_glob)
        return self

    def add_rule(self, rule: AclRule) -> "ToolACL":
        """Точечное правило (жёсткий deny-wins для правил effect=DENY)."""
        self._rules.append(rule)
        return self

    def restrict_ops(self, role: str, tool: str, ops: Sequence[str]) -> "ToolACL":
        """Разрешить role у инструмента только перечисленные операции (glob).

        Если restrict-список задан — любая операция вне списка → DENY:
        это fail-closed-эквивалент «разрешено только …» для конкретного
        инструмента роли (например, read_only: sqlite только SELECT).
        """
        self.define_role(role)
        patterns = set(ops)
        # "*" в списке означает «без ограничений» — сбрасываем restrict
        if "*" in patterns:
            patterns.clear()
        self._op_restrict[(role, tool)] = patterns
        return self

    def add_shell_pattern(self, pattern: str) -> "ToolACL":
        """Добавить пользовательский deny-паттерн shell (B2, raw regex)."""
        self._shell_patterns.append(re.compile(pattern, re.IGNORECASE))
        return self

    # ── проверка ────────────────────────────────────────────────────

    def check(
        self,
        principal: str,
        tool: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> AccessDecision:
        params = params or {}
        if principal not in self._default_effects:
            return AccessDecision(
                allowed=False,
                reason=f"ACL: неизвестный principal {principal!r} (fail-closed)",
                principal=principal,
                tool=tool,
            )

        # B1–B3 общие границы (никому не обходимы)
        d_boundary = self._check_boundaries(tool, params)
        if not d_boundary.allowed:
            return d_boundary

        operation = self._operation(tool, params)

        # 1) точечные deny-правила (deny-wins)
        for rule in self._rules:
            if rule.effect == DENY and rule.matches(principal, tool, operation):
                return AccessDecision(
                    allowed=False,
                    reason=f"ACL deny-rule: {rule.note or rule!r}",
                    principal=principal,
                    matched_rules=(str(rule),),
                    tool=tool,
                )

        # 2) deny по tool-glob
        if any(fnmatch.fnmatch(tool, g) for g in self._deny_tools.get(principal, ())):
            return AccessDecision(
                allowed=False,
                reason=f"ACL deny_tool({principal}, {tool})",
                principal=principal,
                matched_rules=tuple(sorted(self._deny_tools[principal])),
                tool=tool,
            )

        # 3) точечные allow-правила (только для отчёта —— грант решает tool-glob)
        allow_matched: List[str] = []
        for rule in self._rules:
            if rule.effect == ALLOW and rule.matches(principal, tool, operation):
                allow_matched.append(str(rule))

        # 3.5) restrict-список операций: не в списке → DENY (fail-closed)
        restrict = self._op_restrict.get((principal, tool))
        if restrict is not None:
            if operation is None or not any(
                fnmatch.fnmatch(operation, p) for p in restrict
            ):
                return AccessDecision(
                    allowed=False,
                    reason=(
                        f"ACL restrict_ops({principal}, {tool}): операция "
                        f"{operation!r} не входит в {sorted(restrict)}"
                    ),
                    principal=principal,
                    matched_rules=tuple(allow_matched),
                    tool=tool,
                )

        # 4) grant по tool-glob (где бы ни было deny)
        if not any(fnmatch.fnmatch(tool, g) for g in self._allow_tools.get(principal, ())):
            # 5) fallback-эффект роли
            effect = self._default_effects.get(principal, DENY)
            if effect == DENY:
                return AccessDecision(
                    allowed=False,
                    reason=(
                        f"ACL: инструмент {tool!r} не разрешён для роли "
                        f"{principal!r} (fallback {effect})"
                    ),
                    principal=principal,
                    matched_rules=tuple(allow_matched),
                    tool=tool,
                )
            # default ALLOW — но только если нет deny; deny уже обработан выше.
            return AccessDecision(
                allowed=True,
                reason="ACL: fallback ALLOW",
                principal=principal,
                matched_rules=tuple(allow_matched),
                tool=tool,
            )

        return AccessDecision(
            allowed=True,
            reason=f"ACL: инструмент {tool!r} разрешён для роли {principal!r}",
            principal=principal,
            matched_rules=tuple(allow_matched),
            tool=tool,
        )

    # ── внутреннее ───────────────────────────────────────────────────

    def _operation(self, tool: str, params: Dict[str, Any]) -> Optional[str]:
        """Извлечь «операцию» вызова (action/command/method) для сопоставления с правилами."""
        tool_norm = tool.split(".")[0]
        key = _ACTION_PARAM.get(tool_norm)
        if key is None:
            return None
        val = params.get(key)
        if val is None:
            return None
        text = str(val).strip()
        if not text:
            return None
        # sqlite — первый ключевое слово запроса ("SELECT …" → select)
        if tool_norm == "sqlite":
            m = re.match(r"^[\s()*([a-z]+)", text, re.IGNORECASE)
            return m.group(1).lower() if m else text.lower()
        # git — первое слово команды ("status --short" → status); http — метод
        if tool_norm in ("git", "http"):
            return text.split()[0].lower()
        # file — полное значение action
        return text.lower()

    def _check_boundary(self, tool: str, params: Dict[str, Any]) -> Optional[AccessDecision]:
        """B1–B3: проверки, которые не обходятся ни одной ролью. None = ок."""
        # B1 — пути внутри root
        for key in _PATH_PARAMS:
            val = params.get(key)
            if not val or not isinstance(val, str) or not val.strip():
                continue
            p = Path(val)
            if not p.is_absolute():
                p = self._root / p
            try:
                resolved = p.resolve()
            except OSError as exc:
                return AccessDecision(
                    allowed=False,
                    reason=f"ACL B1: ошибка резолва пути {val!r}: {exc}",
                    principal="*",
                    tool=tool,
                )
            root_resolved = self._root.resolve()
            if resolved != root_resolved and not str(resolved).startswith(str(root_resolved) + "/"):
                return AccessDecision(
                    allowed=False,
                    reason=f"ACL B1: путь {val!r} вне workspace {root_resolved}",
                    principal="*",
                    tool=tool,
                )

        # B2 shell-паттерны
        if tool.split(".")[0] == _TOOL_SHELL:
            command = params.get("command", "")
            if isinstance(command, str):
                for rx in self._shell_patterns:
                    if rx.search(command):
                        return AccessDecision(
                            allowed=False,
                            reason=f"ACL B2: shell-паттерн {rx.pattern!r} запрещён",
                            principal="*",
                            tool=tool,
                        )

        # B3 network/SSRF — только если у роли нет сетевого grant
        if tool.split(".")[0] == _TOOL_HTTP:
            url = params.get("url", "")
            if isinstance(url, str) and url:
                decision = self._check_url(url)
                if not decision.allowed:
                    return decision
        return None  # type: ignore[return-value]

    def _check_url(self, url: str) -> Optional[AccessDecision]:
        """B3: запретить loopback/private для HTTP (anti-SSRF)."""
        host = self._extract_host(url)
        if host is None:
            return None
        try:
            ip = ipaddress.ip_address(host.strip("[)"))
        except ValueError:
            # hostname: локальные имена
            low = host.lower()
            if low in ("localhost",) or low.endswith(".local"):
                return AccessDecision(
                    allowed=False,
                    reason=f"ACL B3: локальный хост {host!r} запрещён",
                    principal="*",
                    tool="http",
                )
            return None
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
            return AccessDecision(
                allowed=False,
                reason=f"ACL B3: непубличный адрес {ip} запрещён (anti-SSRF)",
                principal="*",
                tool="http",
            )
        return None

    @staticmethod
    def _extract_host(url: str) -> Optional[str]:
        """Извлечь host из URL (без парсинга полных URI — лёгкий regex)."""
        m = re.match(r"^(?:https?|ftp)://([^/?#:)+)", url, re.IGNORECASE)
        return m.group(1) if m else None


def default_policy(root: Optional[Path | str] = None) -> ToolACL:
    """Политика по умолчанию (три роли; см. docstring модуля)."""
    acl = ToolACL(root=root)

    # ── read_only: чтение только ────────────────────────────────
    acl.define_role(ROLE_READ_ONLY)
    acl.allow_tool(ROLE_READ_ONLY, "file")
    acl.restrict_ops(ROLE_READ_ONLY, "file", ("read", "exists", "list"))
    acl.allow_tool(ROLE_READ_ONLY, "git")
    acl.restrict_ops(ROLE_READ_ONLY, "git", ("status", "log", "diff"))
    acl.allow_tool(ROLE_READ_ONLY, "sqlite")
    acl.restrict_ops(ROLE_READ_ONLY, "sqlite", ("select",))

    # ── standard: + write/run, минус сеть к loc и git push───────────
    acl.define_role(ROLE_STANDARD)
    acl.allow_tool(ROLE_STANDARD, "file")
    acl.restrict_ops(ROLE_STANDARD, "file", (
        "read", "write", "list", "exists", "mkdir", "copy", "move",
    ))
    acl.allow_tool(ROLE_STANDARD, "git")
    acl.restrict_ops(ROLE_STANDARD, "git", (
        "status", "log", "diff", "add", "commit", "branch", "tag", "checkout",
    ))
    acl.add_rule(AclRule(ROLE_STANDARD, "git", DENY, op="push", note="стандарт: без push"))
    acl.add_rule(AclRule(ROLE_STANDARD, "git", DENY, op="pull", note="стандарт: без pull"))
    acl.allow_tool(ROLE_STANDARD, "sqlite")
    acl.allow_tool(ROLE_STANDARD, "http")
    acl.restrict_ops(ROLE_STANDARD, "http", ("get", "post"))
    acl.allow_tool(ROLE_STANDARD, "shell")

    # ── agent: полный доступ, deny-wins на особом ───────────────────
    acl.define_role(ROLE_AGENT)
    for t in (_TOOL_FILE, _TOOL_GIT, _TOOL_HTTP, _TOOL_SHELL, _TOOL_SQLITE):
        acl.allow_tool(ROLE_AGENT, t)
    acl.add_rule(AclRule(ROLE_AGENT, "git", DENY, op="push", note="agent: git push запрещён"))
    acl.add_rule(AclRule(ROLE_AGENT, "git", DENY, op="pull", note="agent: pull как side-эффект"))
    return acl