"""Дизайн Reports Hub: токены Apple-стиля + акцент из логотипа (H3, спека §6)."""

from __future__ import annotations

from services_08.reports_hub.design.accent import extract_accent
from services_08.reports_hub.design.tokens import DEFAULT_ACCENT_DARK, DEFAULT_ACCENT_LIGHT, build_css, theme_script

__all__ = [
    "DEFAULT_ACCENT_DARK",
    "DEFAULT_ACCENT_LIGHT",
    "build_css",
    "extract_accent",
    "theme_script",
]

