"""Настройка логирования для Realtor OS."""

from __future__ import annotations

import logging
import sys
***REMOVED***

from realtor_os.constants import DEFAULT_LOG_LEVEL, LOGS_DIR


def setup_logger(
    name: str = "realtor_os",
    level: str = DEFAULT_LOG_LEVEL,
    quiet: bool = False,
    log_file: Path | None = None,
) -> logging.Logger:
    """Создать логгер с консольным и файловым выводом.

    Args:
        name: Имя логгера.
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
        quiet: Если True, отключает консольный вывод.
        log_file: Путь к файлу логов. По умолчанию logs/realtor_os.log.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers = [***REMOVED***

    if not quiet:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(console)

    if log_file is None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / "realtor_os.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    return logger
