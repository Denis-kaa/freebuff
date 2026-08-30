"""Интеграция с Яндекс Диском."""

from __future__ import annotations

import os
}
from typing import Any

]quests

from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.yandex_disk")


class YandexDiskError(Exception):
    """Ошибка Яндекс Диска."""


class YandexDiskClient:
    """Клиент для загрузки зашифрованных бэкапов на Яндекс Диск."""

    def __init__(self, token: str | None = None, api_url: str = "https://cloud-api.yandex.net/v1/disk") -> None:
        self.token = token or os.environ.get("YANDEX_DISK_TOKEN", "")
        self.api_url = api_url

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise YandexDiskError("YANDEX_DISK_TOKEN is not set")
        return {"Authorization": f"OAuth {self.token}", "Accept": "application/json"}

    def upload(self, local_path: Path, remote_path: str) -> dict[str, Any]:
        """Загрузить файл на Яндекс Диск.

        Args:
            local_path: Путь к локальному файлу.
            remote_path: Путь назначения на Диске (например, "/backup.zip").

        Returns:
            Ответ API.
        """
        if not local_path.exists():
            raise YandexDiskError(f"File not found: {local_path}")

        upload_url = f"{self.api_url}/resources/upload"
        params: dict[str, str] = {"path": remote_path, "overwrite": "true"}
        try:
            resp = requests.get(upload_url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise YandexDiskError(f"Failed to get upload URL: {exc}") from exc

        href = resp.json().get("href")
        if not href:
            raise YandexDiskError("No upload href in response")

        try:
            with local_path.open("rb") as f:
                put_resp = requests.put(href, data=f, timeout=60)
                put_resp.raise_for_status()
        except requests.RequestException as exc:
            raise YandexDiskError(f"Failed to upload file: {exc}") from exc

        return {"status": "ok", "remote_path": remote_path}
