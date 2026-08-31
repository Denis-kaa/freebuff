"""Тесты модуля безопасности."""

import os
from pathlib import Path

import pytest

try:
    from Crypto.Cipher import AES  # noqa: F401
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

from realtor_os.core.security import SecurityError, decrypt_pii, encrypt_pii, get_encryption_key, validate_path

pytestmark = pytest.mark.skipif(not _HAS_CRYPTO, reason="pycryptodome not installed")


@pytest.fixture
def key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("PII_ENCRYPTION_KEY", "test-key-12345")
    return "test-key-12345"


def test_encrypt_decrypt(key: str) -> None:
    original = "ФИО Иванов Иван Иванович"
    encrypted = encrypt_pii(original, key)
    assert encrypted != original
    assert decrypt_pii(encrypted, key) == original


def test_decrypt_wrong_key() -> None:
    encrypted = encrypt_pii("secret", "right-key")
    with pytest.raises(SecurityError):
        decrypt_pii(encrypted, "wrong-key")


def test_empty_key_raises() -> None:
    with pytest.raises(SecurityError):
        encrypt_pii("data", "")


def test_get_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_ENCRYPTION_KEY", "env-key")
    assert get_encryption_key() == "env-key"


def test_validate_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ]altor_os.core.security as sec
    monkeypatch.setattr(sec, "PROJECT_ROOT", tmp_path)
    file_path = tmp_path / "test.txt"
    file_path.write_text("data")
    assert validate_path("test.txt") == file_path


def test_validate_path_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ]altor_os.core.security as sec
    monkeypatch.setattr(sec, "PROJECT_ROOT", tmp_path)
    with pytest.raises(SecurityError):
        validate_path("../etc/passwd")
