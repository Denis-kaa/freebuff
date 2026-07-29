"""
Freebuff Plugin — конфигурация.
"""
from __future__ import annotations

import os
***REMOVED***

# ── Пути ──────────────────────────────────────────────────────

FREEBUFF_ROOT = Path(os.environ.get(
    "FREEBUFF_ROOT",
    str(Path(__file__).resolve().parent.parent),
))

FREEBUFF_BINARY = Path(os.environ.get(
    "FREEBUFF_BINARY",
    str(Path.home() / ".config" / "manicode" / "freebuff"),
))

FREEBUFF_WRAPPER = Path(os.environ.get(
    "FREEBUFF_WRAPPER",
    str(Path.home() / ".local" / "bin" / "freebuff"),
))

PROOT_DISTRO = "ubuntu"

# ── MCP сервер ────────────────────────────────────────────────

MCP_HOST = "127.0.0.1"
MCP_PORT = 8411

MCP_SERVER_NAME = "freebuff-plugin"
MCP_SERVER_VERSION = "0.1.0"

# ── FastAPI ───────────────────────────────────────────────────

API_HOST = "127.0.0.1"
API_PORT = 8410

# ── Qwen локальная модель ────────────────────────────────────

QWEN_MODEL_0_5B = Path(os.environ.get(
    "QWEN_MODEL_0_5B",
    str(Path.home() / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"),
))

QWEN_MODEL_1_5B = "qwen2.5:1.5b"  # ollama

LLAMA_CLI = "llama-cli"

# ── Stream сессии ─────────────────────────────────────────────

STREAMS_DIR = FREEBUFF_ROOT / "context" / "streams"
SUMMARIES_DIR = FREEBUFF_ROOT / "context" / "summaries"

# ── Intent Detection ──────────────────────────────────────────

# Ключевые слова для роутера: Qwen (локально) vs freebuff (облачный агент)
INTENT_KEYWORDS: dict[str, list[str***REMOVED******REMOVED*** = {
    "local": [
        "статус", "батарея", "погода", "время", "дата",
        "привет", "пока", "спасибо", "как дела",
        "напомни", "батарейка", "заряд",
    ***REMOVED***,
    "freebuff": [
        "напиши код", "создай файл", "отрефактори", "напиши тест",
        "сделай миграцию", "настрой проект", "установи пакет",
        "запусти тесты", "закомить", "запушь",
        "создай архитектуру", "спроектируй", "разработай",
        "почини баг", "исправь ошибку",
    ***REMOVED***,
***REMOVED***
