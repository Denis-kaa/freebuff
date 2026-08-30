"""Integration stubs for Yandex Disk and email.

Real implementations should:
- Encrypt files before upload.
- Use OAuth tokens from environment variables.
- Never send PII in plain text.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
}


class IntegrationError(RuntimeError):
    """Raised when an integration operation fails."""

    pass


@dataclass
class YandexDiskConfig:
    token: str
    upload_folder: str

    @classmethod
    def from_env(cls) -> "YandexDiskConfig":
        token = os.environ.get("YANDEX_DISK_TOKEN", "").strip()
        if not token:
            raise IntegrationError("YANDEX_DISK_TOKEN environment variable is missing")
        return cls(
            token=token,
            upload_folder=os.environ.get("YANDEX_DISK_UPLOAD_FOLDER", "/realtor_automation/encrypted"),
        )


@dataclass
class EmailConfig:
    host: str
    port: int
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "EmailConfig":
        missing = []
        host = os.environ.get("EMAIL_HOST", "")
        port = int(os.environ.get("EMAIL_PORT", "0"))
        user = os.environ.get("EMAIL_USER", "")
        password = os.environ.get("EMAIL_PASS", "")
        if not host:
            missing.append("EMAIL_HOST")
        if not port:
            missing.append("EMAIL_PORT")
        if not user:
            missing.append("EMAIL_USER")
        if not password:
            missing.append("EMAIL_PASS")
        if missing:
            raise IntegrationError(f"Missing email configuration: {', '.join(missing)}")
        return cls(host=host, port=port, user=user, password=password)


class YandexDiskUploader:
    """Stub uploader for Yandex Disk.

    Actual upload would use the Yandex Disk REST API with encrypted files.
    """

    def __init__(self, config: YandexDiskConfig) -> None:
        self._config = config

    def upload_encrypted(self, local_path: Path, remote_name: str) -> str:
        """Upload an already encrypted file to Yandex Disk.

        Args:
            local_path: Path to the encrypted file.
            remote_name: Target filename on Yandex Disk.

        Returns:
            A status message.
        """
        if not local_path.exists():
            raise IntegrationError(f"File not found: {local_path}")
        # Real implementation would call the Yandex Disk API here.
        return f"[YANDEX DISK UPLOAD STUB] {local_path} -> {self._config.upload_folder}/{remote_name}"


class EmailSender:
    """Stub email sender that sends only encrypted attachments."""

    def __init__(self, config: EmailConfig) -> None:
        self._config = config

    def send_encrypted_attachment(
        self, recipient: str, subject: str, encrypted_path: Path
    ) -> str:
        """Send an email with an encrypted attachment.

        Args:
            recipient: Recipient email address.
            subject: Email subject.
            encrypted_path: Path to the encrypted attachment.

        Returns:
            A status message.
        """
        if not encrypted_path.exists():
            raise IntegrationError(f"Attachment not found: {encrypted_path}")
        # Real implementation would use smtplib here.
        return (
            f"[EMAIL STUB] To: {recipient}, Subject: {subject}, "
            f"Attachment: {encrypted_path.name} via {self._config.host}:{self._config.port}"
        )
