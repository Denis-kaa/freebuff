#!/usr/bin/env python3
"""
Sub-Agent Scanner — поиск инструментов и систем по паттернам.
Обходит /storage/emulated/0/PROJECTS/workstation/ и ~/.qwen,
классифицирует находки и генерирует structured JSON-отчёт.

Использование:
    python scripts/scanner.py                    # полный скан
    python scripts/scanner.py --category llm     # только LLM-инструменты
    python scripts/scanner.py --output report.json
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
***REMOVED***
from typing import Dict, List, Optional


# ── Конфигурация ──────────────────────────────────────────────

WORKSTATION = os.environ.get(
    "FREEBUFF_WORKSTATION",
    str(Path.home() / "storage" / "PROJECTS" / "workstation"),
)
QWEN_HOME = Path(os.environ.get("QWEN_HOME", str(Path.home() / ".qwen")))
TERMUX_HOME = os.environ.get("TERMUX_HOME", str(Path.home()))
OPENCLAW_HOME = Path(os.environ.get("OPENCLAW_HOME", str(Path.home() / ".openclaw")))

# Категории паттернов
PATTERNS: Dict[str, List[str***REMOVED******REMOVED*** = {
    "llm_model": [
        "*.gguf", "*.bin", "ollama", "llama.cpp", "llama-cli",
        "model*.json", "ggml", "mlc-chat", "qwen", "deepseek",
        "gemini", "groq", "openrouter",
    ***REMOVED***,
    "agent_framework": [
        "CLAUDE.md", "AGENTS.md", "SOUL.md", "BUFFY.md",
        "CODY.md", "openclaw", "aider", "codebuff",
        "freebuff", "agent", "worker",
    ***REMOVED***,
    "mcp_bridge": [
        "mcp", "mcp-bridge", "mcp_server", "mcp_client",
        "modelcontextprotocol", "phone_mcp", "phone-mcp",
    ***REMOVED***,
    "python_project": [
        "pyproject.toml", "setup.py", "setup.cfg", "main.py",
        "requirements.txt", "Pipfile", "uv.lock",
    ***REMOVED***,
    "node_project": [
        "package.json", "tsconfig.json", "next.config.*",
        "node_modules/.package-lock.json",
    ***REMOVED***,
    "database": [
        "*.db", "*.sqlite", "*.sqlite3", "migrations/",
        "alembic.ini", "schema.sql", "prisma/",
    ***REMOVED***,
    "api_gateway": [
        "openapi.json", "swagger.*", "fastapi", "flask",
        "express", "nginx.conf", "caddyfile",
    ***REMOVED***,
    "devops": [
        "Dockerfile", "docker-compose.yml", "Makefile",
        ".github/workflows/", "crontab", "systemd",
    ***REMOVED***,
    "telegram": [
        "tg_", "telegram", "telethon", "pyrogram",
        "bot.py", "tg_bot", "tg_terminal",
    ***REMOVED***,
    "voice_audio": [
        "whisper", "tts", "speech", "audio",
        "voice", "stt", "sound",
    ***REMOVED***,
    "config_secret": [
        ".env", ".env.*", ".keys", ".secrets",
        "credentials", "token", "vault",
    ***REMOVED***,
    "docs_knowledge": [
        "README.md", "SPEC.md", "ARCHITECTURE.md",
        "docs/", "wiki/", "knowledge/",
    ***REMOVED***,
***REMOVED***


@dataclass
class Finding:
    """Одна находка сканера."""
    path: str
    category: str
    pattern_matched: str
    file_type: str           # file | dir | symlink
    size_bytes: int = 0
    description: str = ""


@dataclass
class ScanReport:
    """Итоговый отчёт сканера."""
    scanned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scan_roots: List[str***REMOVED*** = field(default_factory=list)
    total_files_scanned: int = 0
    findings: List[Finding***REMOVED*** = field(default_factory=list)
    summary_by_category: Dict[str, int***REMOVED*** = field(default_factory=dict)
    recommendations: List[str***REMOVED*** = field(default_factory=list)


class Scanner:
    """Сканер инструментов и систем."""

    def __init__(self, roots: Optional[List[str***REMOVED******REMOVED*** = None):
        self.roots = roots or [WORKSTATION, QWEN_HOME, TERMUX_HOME, OPENCLAW_HOME***REMOVED***
        self.findings: List[Finding***REMOVED*** = [***REMOVED***
        self._file_count = 0
        self._max_files = 5000      # лимит, чтобы не зависнуть
        self._max_depth = 6
        self._skip_dirs = {
            "__pycache__", ".git", "node_modules", ".venv",
            "venv", ".aider", ".cache", "dist", "build",
            ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ***REMOVED***

    def scan(self) -> ScanReport:
        """Главный метод: обход корней и поиск по паттернам."""
        report = ScanReport(scan_roots=self.roots)

        for root in self.roots:
            if not os.path.exists(root):
                continue
            self._walk(Path(root), depth=0)

        report.findings = self.findings
        report.total_files_scanned = self._file_count

        # Сводка по категориям
        for f in self.findings:
            report.summary_by_category[f.category***REMOVED*** = (
                report.summary_by_category.get(f.category, 0) + 1
            )

        report.recommendations = self._generate_recommendations(report)
        return report

    def _walk(self, dirpath: Path, depth: int) -> None:
        if depth > self._max_depth or self._file_count > self._max_files:
            return

        try:
            entries = list(dirpath.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            if entry.name in self._skip_dirs:
                continue

            self._file_count += 1

            if entry.is_dir() and not entry.is_symlink():
                self._walk(entry, depth + 1)

            # Проверяем паттерны
            self._match_patterns(entry)

    def _match_patterns(self, entry: Path) -> None:
        """Сопоставляет файл/директорию с паттернами."""
        name_lower = entry.name.lower()

        for category, patterns in PATTERNS.items():
            for pattern in patterns:
                matched = False

                if pattern.startswith("*."):
                    # Глоб: по расширению
                    ext = pattern[1:***REMOVED***  # .gguf, .bin, .db
                    if name_lower.endswith(ext.lower()):
                        matched = True
                elif pattern.endswith("/"):
                    # Директория с именем
                    if entry.is_dir() and name_lower == pattern[:-1***REMOVED***.lower():
                        matched = True
                elif pattern.startswith("*"):
                    # Wildcard
                    substr = pattern[1:***REMOVED***
                    if substr.lower() in name_lower:
                        matched = True
                else:
                    # Точное совпадение
                    if name_lower == pattern.lower():
                        matched = True

                if matched:
                    ftype = "dir" if entry.is_dir() else "file"
                    if entry.is_symlink():
                        ftype = "symlink"

                    size = 0
                    try:
                        if entry.is_file():
                            size = entry.stat().st_size
                    except OSError:
                        pass

                    self.findings.append(Finding(
                        path=str(entry),
                        category=category,
                        pattern_matched=pattern,
                        file_type=ftype,
                        size_bytes=size,
                    ))
                    return  # одно совпадение — одна категория

    def _generate_recommendations(self, report: ScanReport) -> List[str***REMOVED***:
        recs = [***REMOVED***

        cats = report.summary_by_category

        if cats.get("voice_audio", 0) == 0:
            recs.append("🔴 whisper.cpp не найден — установи для голосового ввода: pkg install whisper-cpp")

        if cats.get("mcp_bridge", 0) == 0:
            recs.append("🟡 MCP-серверы не найдены — создай phone-mcp для доступа к Android API")

        if cats.get("database", 0) < 3:
            recs.append("🟡 Мало БД — рассмотри PostgreSQL/Redis через proot-distro")

        if cats.get("api_gateway", 0) == 0:
            recs.append("🟡 Нет API-шлюза — добавь FastAPI-гейтвей для объединения сервисов")

        llm_count = cats.get("llm_model", 0)
        agent_count = cats.get("agent_framework", 0)
        if llm_count > 0 and agent_count > 0:
            recs.append(f"✅ Найдено LLM-моделей: {llm_count***REMOVED***, агентских фреймворков: {agent_count***REMOVED***")
        elif agent_count == 0:
            recs.append("🔴 Нет агентских фреймворков — установи OpenClaw или Aider")

        return recs


# ── CLI ───────────────────────────────────────────────────────

def cmd_scan(args: List[str***REMOVED***) -> None:
    roots = None
    category_filter = None
    output_file = None

    i = 0
    while i < len(args):
        if args[i***REMOVED*** == "--category" and i + 1 < len(args):
            category_filter = args[i + 1***REMOVED***
            i += 2
        elif args[i***REMOVED*** == "--output" and i + 1 < len(args):
            output_file = args[i + 1***REMOVED***
            i += 2
        elif args[i***REMOVED*** == "--roots" and i + 1 < len(args):
            roots = args[i + 1***REMOVED***.split(",")
            i += 2
        else:
            i += 1

    scanner = Scanner(roots)
    report = scanner.scan()

    # Фильтр по категории
    if category_filter and category_filter in PATTERNS:
        report.findings = [f for f in report.findings if f.category == category_filter***REMOVED***
        report.summary_by_category = {category_filter: len(report.findings)***REMOVED***

    # Вывод
    if output_file:
        with open(output_file, "w") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        print(f"📄 Отчёт сохранён: {output_file***REMOVED***")
    else:
        _print_report(report)


def _print_report(report: ScanReport) -> None:
    """Красивый вывод в консоль."""
    print(f"\n{'='*60***REMOVED***")
    print(f"🔍 SCANNER REPORT — {report.scanned_at[:19***REMOVED******REMOVED***")
    print(f"{'='*60***REMOVED***")
    print(f"Отсканировано файлов: {report.total_files_scanned***REMOVED***")
    print(f"Найдено инструментов: {len(report.findings)***REMOVED***")
    print()

    if report.summary_by_category:
        print("📊 ПО КАТЕГОРИЯМ:")
        for cat, count in sorted(report.summary_by_category.items(), key=lambda x: -x[1***REMOVED***):
            emoji = _cat_emoji(cat)
            print(f"  {emoji***REMOVED*** {cat***REMOVED***: {count***REMOVED***")
        print()

    if report.findings:
        print("🔎 ТОП НАХОДОК:")
        for f in report.findings[:20***REMOVED***:
            print(f"  [{f.category***REMOVED******REMOVED*** {f.path***REMOVED***")

        if len(report.findings) > 20:
            print(f"  ... и ещё {len(report.findings) - 20***REMOVED***")

    if report.recommendations:
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        for r in report.recommendations:
            print(f"  {r***REMOVED***")

    print(f"\n{'='*60***REMOVED***\n")


def _cat_emoji(cat: str) -> str:
    return {
        "llm_model": "🧠",
        "agent_framework": "🤖",
        "mcp_bridge": "🔌",
        "python_project": "🐍",
        "node_project": "🟢",
        "database": "🗄️",
        "api_gateway": "🌐",
        "devops": "🐳",
        "telegram": "✈️",
        "voice_audio": "🎤",
        "config_secret": "🔑",
        "docs_knowledge": "📚",
    ***REMOVED***.get(cat, "📦")


if __name__ == "__main__":
    cmd_scan(sys.argv[1:***REMOVED***)
