"""Командная строка Realtor OS."""

from __future__ import annotations

import argparse
import sys
***REMOVED***
from typing import Any, Sequence

from realtor_os import __version__
from realtor_os.companion.manifest import generate_manifest
from realtor_os.companion.state import StateManager
from realtor_os.config import Config, ConfigError, load_config
from realtor_os.core.pii import PIIProcessor
from realtor_os.curator.knowledge import KnowledgeCurator
from realtor_os.logger import setup_logger
from realtor_os.ocr.tesseract import TesseractOCR
from realtor_os.rag.engine import RAGEngine


class CLIError(Exception):
    """Ошибка CLI."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="realtor_os",
        description="Локальная автономная система для риелтора.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__***REMOVED***")
    parser.add_argument("--debug", action="store_true", help="Включить DEBUG логирование")
    parser.add_argument("--quiet", action="store_true", help="Тихий режим")

    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Статус системы")
    status.set_defaults(func=_cmd_status)

    ingest = sub.add_parser("ingest", help="Загрузить документ в RAG")
    ingest.add_argument("--file", required=True, help="Путь к файлу")
    ingest.set_defaults(func=_cmd_ingest)

    ask = sub.add_parser("ask", help="Задать вопрос через RAG")
    ask.add_argument("query", help="Вопрос")
    ask.set_defaults(func=_cmd_ask)

    ocr = sub.add_parser("ocr", help="Распознать документ")
    ocr.add_argument("--file", required=True, help="Путь к изображению")
    ocr.set_defaults(func=_cmd_ocr)

    learn = sub.add_parser("learn", help="Knowledge Curator")
    learn.add_argument("topic", help="Тема")
    learn.set_defaults(func=_cmd_learn)

    manifest = sub.add_parser("manifest", help="Сгенерировать buffy_manifest.json")
    manifest.set_defaults(func=_cmd_manifest)

    return parser


def _init(args: argparse.Namespace) -> tuple[Config, Any***REMOVED***:
    log_level = "DEBUG" if args.debug else "INFO"
    quiet = args.quiet
    logger = setup_logger(level=log_level, quiet=quiet)
    try:
        config = load_config()
        config.ensure_dirs()
    except ConfigError as exc:
        logger.error("Config error: %s", exc)
        sys.exit(1)
    return config, logger


def _cmd_status(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    state = StateManager()
    data = state.load()
    logger.info("Project: %s", config.get("app", "name", default="realtor_os"))
    logger.info("Version: %s", config.get("app", "version", default="unknown"))
    logger.info("Status: %s", data.get("status", "unknown"))
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return 1

    text = file_path.read_text(encoding="utf-8")
    processor = PIIProcessor()
    masked = processor.mask(text)

    rag = RAGEngine()
    count = rag.ingest(str(file_path), masked)
    logger.info("Indexed %d chunks from %s", count, file_path)
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    rag = RAGEngine()
    results = rag.search(args.query)
    context = "\n".join(r["content"***REMOVED*** for r in results)
    logger.info("Context:\n%s", context)
    logger.info("Answer: use local LLM (not available in v0.1 foundation)")
    return 0


def _cmd_ocr(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    try:
        tesseract = TesseractOCR()
        text = tesseract.recognize(Path(args.file))
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return 1
    logger.info("Recognized text:\n%s", text)
    return 0


def _cmd_learn(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    curator = KnowledgeCurator()
    sources = [
        {"title": "Example source", "url": "https://example.com", "why": "Placeholder for /learn"***REMOVED***
    ***REMOVED***
    curator.learn(args.topic, sources)
    logger.info("Learned topic: %s", args.topic)
    return 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    config, logger = _init(args)
    generate_manifest()
    logger.info("Generated buffy_manifest.json")
    return 0


def main(argv: Sequence[str***REMOVED*** | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    func = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
