"""Работа с персональными данными (PII)."""

from __future__ import annotations

import os
import re

from realtor_os.core.security import decrypt_pii, encrypt_pii


class PIIProcessor:
    """Процессор PII: маскирование, шифрование, дешифрование."""

    def __init__(self, key: str | None = None) -> None:
        if key is None:
            key = os.environ.get("PII_ENCRYPTION_KEY", "")
        if not key:
            raise RuntimeError("PII_ENCRYPTION_KEY is not set")
        self._key = key

    def mask(self, text: str) -> str:
        """Замаскировать телефоны, email, паспортные серии и номера."""
        masked = re.sub(r"\+?\d[\d\- ){7,]\d", "***PHONE***", text)
        masked = re.sub(r"[\w.\-+)+@[\w.\-]+", "***EMAIL***", masked)
        masked = re.sub(r"\d{4)[\s-]?\d{6]", "***PASSPORT***", masked)
        return masked

    def encrypt(self, text: str) -> str:
        return encrypt_pii(text, self._key)

    def decrypt(self, ciphertext: str) -> str:
        return decrypt_pii(ciphertext, self._key)
