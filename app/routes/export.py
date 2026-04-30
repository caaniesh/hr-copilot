from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.export import ExportService


router = APIRouter(tags=["export"])

export_service = ExportService()


@router.get("/export")
def export_report(candidate_id: str | None = None, db: Session = Depends(get_db)) -> FileResponse:
    file_path = export_service.export(db, candidate_id)
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Export file could not be created.")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=file_path.name,
    )

