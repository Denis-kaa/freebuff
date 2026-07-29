"""Security utilities for encrypting PII and validating input."""

from __future__ import annotations

import os
***REMOVED***
***REMOVED***


class SecurityError(RuntimeError):
    """Raised when a security operation fails or input is invalid."""

    pass


class PIIEncryptor:
    """Encrypt and decrypt personally identifiable information (PII)."""

    def __init__(self, key: bytes | None = None) -> None:
        """Initialize with a Fernet key.

        Args:
            key: Optional 32-byte URL-safe base64-encoded Fernet key.
                If omitted, the ``PII_ENCRYPTION_KEY`` environment variable is used.

        Raises:
            SecurityError: If no key is provided and the environment variable is missing.
        """
        raw_key = key or os.environ.get("PII_ENCRYPTION_KEY", "").encode()
        if not raw_key:
            raise SecurityError(
                "PII encryption key is missing. Set PII_ENCRYPTION_KEY environment variable."
            )
        try:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(raw_key)
        except ImportError as exc:
            raise SecurityError(
                "cryptography package is not installed. Run: pip install cryptography"
            ) from exc
        except ValueError as exc:
            raise SecurityError(f"Invalid PII encryption key: {exc***REMOVED***") from exc

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a URL-safe token."""
        if not isinstance(plaintext, str):
            raise SecurityError("Plaintext must be a string")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Decrypt a previously encrypted token."""
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            raise SecurityError(f"Failed to decrypt token: {exc***REMOVED***") from exc

    def redact_pii(self, text: str) -> str:
        """Replace common Russian PII patterns with [REDACTED***REMOVED***."""
        # Passport series/number, phone, email, SNILS-like numbers.
        ***REMOVED***
            (r"\d{4***REMOVED***\s?\d{6***REMOVED***", "[PASSPORT***REMOVED***"),  # passport
            (r"\+?7\s?\d{3***REMOVED***[\s\-***REMOVED***?\d{3***REMOVED***[\s\-***REMOVED***?\d{2***REMOVED***[\s\-***REMOVED***?\d{2***REMOVED***", "[PHONE***REMOVED***"),
            (r"[a-zA-Z0-9._%+-***REMOVED***+@[a-zA-Z0-9.-***REMOVED***+\.[a-zA-Z***REMOVED***{2,***REMOVED***", "[EMAIL***REMOVED***"),
            (r"\d{3***REMOVED***[\s\-***REMOVED***?\d{3***REMOVED***[\s\-***REMOVED***?\d{3***REMOVED***[\s\-***REMOVED***?\d{2***REMOVED***", "[SNILS***REMOVED***"),
        ***REMOVED***
        redacted = text
        for pattern, replacement in patterns:
            redacted = re.sub(pattern, replacement, redacted)
        return redacted


def validate_path(path: str) -> Path:
    """Validate that a path is inside the project directory.

    Args:
        path: User-provided path.

    Returns:
        Resolved Path object.

    Raises:
        SecurityError: If the path attempts path traversal outside the project.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    resolved = (project_root / path).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise SecurityError(f"Path traversal detected: {path***REMOVED***") from exc
    return resolved


def validate_non_empty(value: str, name: str = "value") -> str:
    """Return the stripped value or raise SecurityError if empty."""
    if not isinstance(value, str):
        raise SecurityError(f"{name***REMOVED*** must be a string")
    stripped = value.strip()
    if not stripped:
        raise SecurityError(f"{name***REMOVED*** cannot be empty")
    return stripped
