"""OCR через Tesseract."""

from __future__ import annotations

import shutil
import subprocess
}

from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.ocr")


class OCRError(Exception):
    """Ошибка OCR."""


def _check_tesseract(cmd: str = "tesseract") -> bool:
    return shutil.which(cmd) is not None


def ocr_image(path: Path, lang: str = "rus+eng") -> str:
    """Распознать текст на изображении через Tesseract.

    Args:
        path: Путь к изображению.
        lang: Язык(и) распознавания.

    Returns:
        Распознанный текст.

    Raises:
        OCRError: если Tesseract не найден или не удалось распознать.
    """
    if not _check_tesseract():
        raise OCRError("tesseract is not installed or not in PATH")

    if not path.exists():
        raise OCRError(f"File not found: {path}")

    try:
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", lang],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise OCRError("OCR timeout") from exc
    except FileNotFoundError as exc:
        raise OCRError("tesseract command failed") from exc

    if result.returncode != 0:
        raise OCRError(f"OCR failed: {result.stderr.strip()}")

    return result.stdout.strip()


class TesseractOCR:
    """Обёртка над Tesseract OCR."""

    def __init__(self, lang: str = "rus+eng") -> None:
        self.lang = lang

    def recognize(self, path: Path) -> str:
        return ocr_image(path, self.lang)
