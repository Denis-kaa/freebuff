"""Command-line interface for realtor_automation."""

from __future__ import annotations

import argparse
import logging
import sys
***REMOVED***
from typing import Any, cast

from realtor_automation.config import ConfigError, load_config
from realtor_automation.curator import build_plan
from realtor_automation.llm import LLMError, get_client
from realtor_automation.logger import setup_logger
from realtor_automation.ocr import OCRError, get_ocr_processor
from realtor_automation.rag import KnowledgeBase, RAGError
from realtor_automation.security import PIIEncryptor, SecurityError, validate_non_empty, validate_path
from realtor_automation.state import StateManager


class CLI:
    """Main CLI entry point."""

    def __init__(self) -> None:
        self._project_root = Path(__file__).resolve().parent.parent.parent
        self._config = self._load_config()
        self._paths = self._config.get("paths", {***REMOVED***)
        self._logger = self._setup_logger()
        self._state = self._setup_state()

    def _load_config(self) -> dict[str, Any***REMOVED***:
        try:
            return cast(dict[str, Any***REMOVED***, load_config(self._project_root))
        except ConfigError as exc:
            print(f"Configuration error: {exc***REMOVED***", file=sys.stderr)
            sys.exit(1)

    def _setup_logger(self) -> logging.Logger:
        app_cfg = self._config.get("app", {***REMOVED***)
        log_level = app_cfg.get("log_level", "INFO")
        quiet = app_cfg.get("quiet", False)
        logs_dir = Path(self._paths.get("logs", "logs"))
        return cast(
            logging.Logger,
            setup_logger(
                "realtor_automation",
                level=log_level,
                quiet=quiet,
                log_file=self._project_root / logs_dir / "app.log",
            ),
        )

    def _setup_state(self) -> StateManager:
        state_file = Path(self._paths.get("state_file", "data/project_state.json"))
        return StateManager(self._project_root / state_file)

    def _knowledge_base(self) -> KnowledgeBase:
        db_path = self._project_root / self._config.get("rag", {***REMOVED***).get("db_path", "data/knowledge.db")
        return KnowledgeBase(db_path)

    def _encryptor(self) -> PIIEncryptor:
        return PIIEncryptor()

    def run(self, args: list[str***REMOVED***) -> int:
        parser = self._build_parser()
        parsed = parser.parse_args(args)
        if not hasattr(parsed, "func"):
            parser.print_help()
            return 0
        try:
            return int(parsed.func(parsed))
        except SecurityError as exc:
            self._logger.error("Security error: %s", exc)
            return 1
        except (RAGError, OCRError, LLMError) as exc:
            self._logger.error("%s: %s", type(exc).__name__, exc)
            return 1

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="realtor_automation",
            description="Локальная автоматизация для риелтора.",
        )
        parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

        sub = parser.add_subparsers(dest="command")

        status = sub.add_parser("status", help="Показать текущий PROJECT STATE")
        status.set_defaults(func=self._cmd_status)

        ingest = sub.add_parser("ingest", help="Добавить документ в базу знаний")
        ingest.add_argument("--file", required=True, help="Путь к файлу")
        ingest.add_argument("--tag", default="", help="Тег категории")
        ingest.set_defaults(func=self._cmd_ingest)

        ask = sub.add_parser("ask", help="Задать вопрос локальному RAG")
        ask.add_argument("query", help="Запрос")
        ask.add_argument("--limit", type=int, default=5, help="Количество результатов")
        ask.set_defaults(func=self._cmd_ask)

        learn = sub.add_parser("learn", help="Сгенерировать план обучения по теме")
        learn.add_argument("topic", help="Тема")
        learn.set_defaults(func=self._cmd_learn)

        encrypt = sub.add_parser("encrypt", help="Зашифровать строку")
        encrypt.add_argument("value", help="Строка для шифрования")
        encrypt.set_defaults(func=self._cmd_encrypt)

        decrypt = sub.add_parser("decrypt", help="Расшифровать строку")
        decrypt.add_argument("value", help="Зашифрованная строка")
        decrypt.set_defaults(func=self._cmd_decrypt)

        ocr = sub.add_parser("ocr", help="Распознать текст на изображении")
        ocr.add_argument("--file", required=True, help="Путь к изображению")
        ocr.set_defaults(func=self._cmd_ocr)

        return parser

    def _cmd_status(self, _parsed: argparse.Namespace) -> int:
        print(self._state.format_state())
        return 0

    def _cmd_ingest(self, parsed: argparse.Namespace) -> int:
        file_path = validate_path(parsed.file)
        if not file_path.exists():
            self._logger.error("File not found: %s", file_path)
            return 1
        content = file_path.read_text(encoding="utf-8")
        kb = self._knowledge_base()
        count = kb.ingest(source=str(file_path), content=content, tag=parsed.tag)
        self._state.add_installed(f"doc:{file_path.name***REMOVED***")
        self._logger.info("Ingested %s (rows=%d)", file_path, count)
        return 0

    def _cmd_ask(self, parsed: argparse.Namespace) -> int:
        kb = self._knowledge_base()
        results = kb.search(parsed.query, limit=parsed.limit)
        if not results:
            print("Ничего не найдено.")
            return 0

        context = "\n\n".join(
            f"[{doc['tag'***REMOVED*** or 'general'***REMOVED******REMOVED*** {doc['source'***REMOVED******REMOVED***:\n{doc['content'***REMOVED***[:300***REMOVED******REMOVED***"
            for doc in results
        )

        try:
            client = get_client(self._config)
            prompt = (
                f"Ответь на вопрос риелтора, используя только предоставленный контекст:\n\n"
                f"Вопрос: {parsed.query***REMOVED***\n\nКонтекст:\n{context***REMOVED***\n\nОтвет:"
            )
            response = client.ask(prompt)
            print(response.content)
        except LLMError as exc:
            self._logger.warning("LLM unavailable, returning raw RAG results: %s", exc)
            print(context)
        return 0

    def _cmd_learn(self, parsed: argparse.Namespace) -> int:
        topic = validate_non_empty(parsed.topic, "topic")
        plan = build_plan(topic)
        print(plan.format())
        self._state.increment_knowledge()
        self._logger.info("Generated learning plan for: %s", topic)
        return 0

    def _cmd_encrypt(self, parsed: argparse.Namespace) -> int:
        value = validate_non_empty(parsed.value, "value")
        token = self._encryptor().encrypt(value)
        print(token)
        return 0

    def _cmd_decrypt(self, parsed: argparse.Namespace) -> int:
        value = validate_non_empty(parsed.value, "value")
        plaintext = self._encryptor().decrypt(value)
        print(plaintext)
        return 0

    def _cmd_ocr(self, parsed: argparse.Namespace) -> int:
        image_path = validate_path(parsed.file)
        processor = get_ocr_processor()
        text = processor.process_image(image_path)
        print(text)
        return 0


def main() -> int:
    """Entry point for the CLI."""
    return CLI().run(sys.argv[1:***REMOVED***)


if __name__ == "__main__":
    sys.exit(main())
