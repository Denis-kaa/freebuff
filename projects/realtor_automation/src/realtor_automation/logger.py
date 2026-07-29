"""Logging setup for realtor_automation."""

from __future__ import annotations

import logging
import sys
***REMOVED***


class _LogLevels:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def setup_logger(
    name: str,
    level: str = "INFO",
    quiet: bool = False,
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure a logger with console and optional file output.

    Args:
        name: Logger name.
        level: Minimum log level.
        quiet: If True, suppress console output.
        log_file: Optional path to a log file.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers = [***REMOVED***
    logger.propagate = False

    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s***REMOVED*** %(name)s: %(message)s")
        )
        logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s***REMOVED*** %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    return logger
