"""Шифрование и дешифрование PII."""

from __future__ import annotations

import base64
import binascii
import os
***REMOVED***

try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Random import get_random_bytes
except ImportError as _import_exc:  # pragma: no cover - fallback for missing pycryptodome
    AES = None  # type: ignore[assignment, misc***REMOVED***
    PBKDF2 = None  # type: ignore[assignment, misc***REMOVED***
    get_random_bytes = None  # type: ignore[assignment, misc***REMOVED***

from realtor_os.constants import PROJECT_ROOT

_SALT_SIZE = 16
_IV_SIZE = 16
_KEY_SIZE = 32
_ITERATIONS = 100_000


class SecurityError(Exception):
    """Ошибка безопасности."""


def _derive_key(password: bytes, salt: bytes) -> bytes:
    return PBKDF2(password, salt, dkLen=_KEY_SIZE, count=_ITERATIONS)  # noqa: S303


def _ensure_crypto() -> None:
    if AES is None or PBKDF2 is None or get_random_bytes is None:
        raise SecurityError(
            "pycryptodome is required for encryption. Install: pip install pycryptodome"
        )


def encrypt_pii(plaintext: str, key: str) -> str:
    """Зашифровать строку PII с помощью AES-256-GCM.

    Args:
        plaintext: Исходный текст.
        key: Парольная фраза или hex-ключ.

    Returns:
        Строка base64(salt + iv + ciphertext + tag).

    Raises:
        SecurityError: если key пустой.
    """
    _ensure_crypto()
    if not key:
        raise SecurityError("Encryption key is empty")

    data = plaintext.encode("utf-8")
    salt = get_random_bytes(_SALT_SIZE)
    derived = _derive_key(key.encode("utf-8"), salt)
    cipher = AES.new(derived, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    payload = salt + cipher.nonce + ciphertext + tag
    return base64.b64encode(payload).decode("ascii")


def decrypt_pii(ciphertext_b64: str, key: str) -> str:
    """Расшифровать строку PII.

    Args:
        ciphertext_b64: Зашифрованные данные от encrypt_pii.
        key: Парольная фраза или hex-ключ.

    Returns:
        Расшифрованный текст.

    Raises:
        SecurityError: если ключ неверный или данные повреждены.
    """
    _ensure_crypto()
    if not key:
        raise SecurityError("Encryption key is empty")

    try:
        payload = base64.b64decode(ciphertext_b64.encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise SecurityError("Invalid ciphertext encoding") from exc

    if len(payload) < _SALT_SIZE + _IV_SIZE + 16:
        raise SecurityError("Ciphertext too short")

    salt = payload[:_SALT_SIZE***REMOVED***
    nonce = payload[_SALT_SIZE : _SALT_SIZE + _IV_SIZE***REMOVED***
    rest = payload[_SALT_SIZE + _IV_SIZE :***REMOVED***
    tag = rest[-16:***REMOVED***
    ciphertext = rest[:-16***REMOVED***

    derived = _derive_key(key.encode("utf-8"), salt)
    cipher = AES.new(derived, AES.MODE_GCM, nonce=nonce)
    try:
        data = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise SecurityError("Decryption failed") from exc

    return data.decode("utf-8")


def get_encryption_key() -> str:
    """Получить ключ шифрования из переменной окружения."""
    key = os.environ.get("PII_ENCRYPTION_KEY", "")
    if not key:
        raise SecurityError("PII_ENCRYPTION_KEY is not set")
    return key


def validate_path(path: str | Path) -> Path:
    """Проверить, что путь находится внутри проекта.

    Raises:
        SecurityError: если путь выходит за пределы проекта.
    """
    resolved = (PROJECT_ROOT / Path(path)).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise SecurityError(f"Path escapes project root: {path***REMOVED***") from exc
    return resolved
