"""Google Sheets integration (6.md §30-35).

Архитектура: Google Sheets <-> Sync/Import/Export Layer <-> PostgreSQL.
OAuth — не просим API key в интерфейсе (§30). MVP: ручная команда
App -> Sheets и Sheets -> App (§33), без realtime-синхронизации (§34).

Реальное подключение активируется при наличии OAuth-credentials в конфиге
(GOOGLE_SHEETS_CREDENTIALS JSON или GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET).
Без них endpoints честно возвращают 501 — не притворяемся подключёнными.
"""
import json
import os
from typing import Optional


def _credentials_path() -> Optional[str]:
    return os.environ.get("GOOGLE_SHEETS_CREDENTIALS")


def _oauth_env() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def is_configured() -> bool:
    return bool(_credentials_path() or _oauth_env())


def status() -> dict:
    """Статус подключения (6.md §30)."""
    configured = is_configured()
    return {
        "configured": configured,
        "connected": configured,  # MVP: подключение = наличие credentials в конфиге
        "email": os.environ.get("GOOGLE_SERVICE_ACCOUNT") or None,
        "sync_mode": "manual",  # §33: one-way по ручной команде, без realtime
        "note": "OAuth через credentials в конфиге; API key в интерфейсе не требуется.",
    }


def connect() -> dict:
    if not is_configured():
        raise ConnectionError("Google Sheets не настроен: добавьте GOOGLE_SHEETS_CREDENTIALS в конфиг сервера.")
    return status()


def list_spreadsheets() -> list[dict]:
    """Список таблиц Google (MVP: заглушка до реального OAuth)."""
    if not is_configured():
        raise ConnectionError("Google Sheets не настроен.")
    # TODO(6.md §31): gspread + credentials — перечисление доступных таблиц
    return []


def import_sheet(spreadsheet_id: str, sheet_name: str) -> dict:
    if not is_configured():
        raise ConnectionError("Google Sheets не настроен.")
    raise NotImplementedError("Импорт из Google Sheets: подключите OAuth-credentials (см. docs).")


def export_sheet(spreadsheet_id: Optional[str], rows: list[list], headers: list[str]) -> dict:
    if not is_configured():
        raise ConnectionError("Google Sheets не настроен.")
    raise NotImplementedError("Экспорт в Google Sheets: подключите OAuth-credentials (см. docs).")