"""Tests for security utilities."""

import os

import pytest

cryptography = pytest.importorskip("cryptography.fernet")

from realtor_automation.security import (  # noqa: E402
    PIIEncryptor,
    SecurityError,
    validate_non_empty,
    validate_path,
)


@pytest.fixture
def encryption_key() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


def test_encrypt_decrypt_roundtrip(encryption_key: str) -> None:
    os.environ["PII_ENCRYPTION_KEY"***REMOVED*** = encryption_key
    encryptor = PIIEncryptor()
    token = encryptor.encrypt("Иван Иванов")
    assert token != "Иван Иванов"
    assert encryptor.decrypt(token) == "Иван Иванов"


def test_redact_pii(encryption_key: str) -> None:
    os.environ["PII_ENCRYPTION_KEY"***REMOVED*** = encryption_key
    encryptor = PIIEncryptor()
    text = "Телефон: +7 999 123-45-67, паспорт: 1234 567890"
    redacted = encryptor.redact_pii(text)
    assert "[PHONE***REMOVED***" in redacted
    assert "[PASSPORT***REMOVED***" in redacted


def test_validate_non_empty() -> None:
    assert validate_non_empty("  hello  ") == "hello"
    with pytest.raises(SecurityError):
        validate_non_empty("   ")


def test_validate_path_traversal(tmp_path: str) -> None:
    with pytest.raises(SecurityError):
        validate_path("../../../etc/passwd")
