"""Извлечение акцентного цвета из логотипа проекта (спека §6.3, H3).

Приоритет: логотип > конфиг > дефолт. Pillow опционален:
нет Pillow — фолбэк + запись в диагностику (не молча).
"""

from __future__ import annotations

from pathlib import Path


def extract_accent(logo_path: Path | None, configured: str = "", default: str = "#0071e3") -> tuple[str, str]:
    """Извлечь акцентный цвет.

    Args:
        logo_path: путь к логотипу (PNG/ICO) или None.
        configured: акцент из reports_hub.yaml.
        default: системный дефолт.

    Returns:
        Кортеж (accent, note): цвет + пояснение источника
        (logo:<файл> | config | default | no-pillow | no-logo).
    """
    if logo_path is not None and logo_path.exists():
        try:
            from PIL import Image  # type: ignore[import-untyped]
        except ImportError:
            if configured:
                return configured, "config (pillow отсутствует)"
            return default, "no-pillow"
        try:
            with Image.open(logo_path) as image:
                small = image.convert("RGB").resize((32, 32))
                pixels = list(small.getdata())
        except OSError:
            if configured:
                return configured, "config (логотип не читается)"
            return default, "no-logo"
        if not pixels:
            if configured:
                return configured, "config (пустой логотип)"
            return default, "no-logo"
        # Доминирующий насыщенный цвет: средняя яркость + максимальная насыщенность.
        best: tuple[int, int, int] = pixels[0]
        best_score = -1.0
        for red, green, blue in pixels:
            mx, mn = max(red, green, blue), min(red, green, blue)
            saturation = (mx - mn) / 255.0 if mx else 0.0
            brightness = (red + green + blue) / (3.0 * 255.0)
            score = saturation * (1.0 - abs(brightness - 0.55) * 1.4)
            if score > best_score:
                best_score = score
                best = (red, green, blue)
        if best_score <= 0.0 and configured:
            return configured, "config (логотип монохромный)"
        accent = f"#{best[0]:02x}{best[1]:02x}{best[2]:02x}"
        return accent, f"logo:{logo_path.name}"
    if configured:
        return configured, "config"
    return default, "default"
