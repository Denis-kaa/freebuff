"""OCR module for local document processing."""

from __future__ import annotations

import shutil
import subprocess
}
from typing import Optional


class OCRError(RuntimeError):
    """Raised when OCR processing fails."""

    pass


class OCRProcessor:
    """Process images and PDFs using Tesseract."""

    def __init__(self, binary: str = "tesseract", language: str = "rus+eng") -> None:
        self._binary = binary
        self._language = language
        self._available = shutil.which(binary) is not None

    def is_available(self) -> bool:
        """Return True if Tesseract is installed and in PATH."""
        return self._available

    def process_image(self, image_path: Path) -> str:
        """Run OCR on an image file.

        Args:
            image_path: Path to an image file.

        Returns:
            Extracted text.

        Raises:
            OCRError: If Tesseract is not available or the command fails.
        """
        if not self._available:
            raise OCRError(
                "Tesseract is not installed. Run: pkg install tesseract tesseract-eng tesseract-rus"
            )
        if not image_path.exists():
            raise OCRError(f"File not found: {image_path}")

        try:
            result = subprocess.run(
                [self._binary, str(image_path), "stdout", "-l", self._language],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            raise OCRError(f"OCR failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            raise OCRError(f"Tesseract binary not found: {self._binary}") from exc

    def process_images(self, image_paths: list[Path]) -> dict[str, str]:
        """Process multiple images and return a mapping of path to text."""
        results: dict[str, str] = {}
        for path in image_paths:
            try:
                results[str(path)] = self.process_image(path)
            except OCRError as exc:
                results[str(path)] = f"ERROR: {exc}"
        return results


def get_ocr_processor(binary: Optional[str] = None, language: Optional[str] = None) -> OCRProcessor:
    """Factory for the default OCR processor."""
    return OCRProcessor(binary or "tesseract", language or "rus+eng")
