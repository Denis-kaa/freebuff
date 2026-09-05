"""Google интеграции (6.md §30-35, §51).

GET    /integrations/google          — статус подключения
POST   /integrations/google/connect  — подключение (OAuth, не API key в UI)
DELETE /integrations/google/disconnect
POST   /google-sheets/import         — Sheets -> App (ручная команда, §33)
POST   /google-sheets/export         — App -> Sheets
"""
from fastapi import APIRouter, Depends, HTTPException

from .. import google_sheets

router = APIRouter(tags=["integrations"])
sheets_router = APIRouter(prefix="/google-sheets", tags=["google-sheets"])


@router.get("/integrations/google")
async def google_status():
    return google_sheets.status()


@router.post("/integrations/google/connect")
async def google_connect():
    try:
        return google_sheets.connect()
    except ConnectionError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.delete("/integrations/google/disconnect")
async def google_disconnect():
    return {"connected": False}


@sheets_router.post("/import")
async def google_import(payload: dict):
    try:
        result = google_sheets.import_sheet(payload.get("spreadsheet_id", ""),
                                            payload.get("sheet_name", ""))
        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=501, detail=str(e))


@sheets_router.post("/export")
async def google_export(payload: dict):
    try:
        result = google_sheets.export_sheet(payload.get("spreadsheet_id"),
                                            payload.get("rows", []), payload.get("headers", []))
        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=501, detail=str(e))