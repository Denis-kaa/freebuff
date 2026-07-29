"""Работа с персональными данными (PII)."""

from __future__ import annotations

import os
***REMOVED***

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
        masked = re.sub(r"\+?\d[\d\- ***REMOVED***{7,***REMOVED***\d", "***PHONE***", text)
        masked = re.sub(r"[\w.\-+***REMOVED***+@[\w.\-***REMOVED***+", "***EMAIL***", masked)
        masked = re.sub(r"\d{4***REMOVED***[\s-***REMOVED***?\d{6***REMOVED***", "***PASSPORT***", masked)
        return masked

    def encrypt(self, text: str) -> str:
        return encrypt_pii(text, self._key)

    def decrypt(self, ciphertext: str) -> str:
        return decrypt_pii(ciphertext, self._key)
