from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import UploadResumeResponse
from app.services.extractor import ResumeExtractionService
from app.services.parser import ResumeParserService
from app.services.storage import CandidateStorageService
from app.utils.config import settings
from app.utils.hr_notes import humanize_parsing_warnings
from app.utils.text import safe_filename


router = APIRouter(tags=["resume"])

parser_service = ResumeParserService()
extractor_service = ResumeExtractionService()
storage_service = CandidateStorageService()


@router.post("/upload_resume", response_model=UploadResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadResumeResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A resume filename is required.")

    extension = f".{file.filename.rsplit('.', 1)[-1].lower()}" if "." in file.filename else ""
    if extension not in parser_service.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported types: PDF, DOC, DOCX, TXT.",
        )

    payload = await file.read()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(payload) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File is larger than {settings.max_upload_size_mb} MB.")

    stored_name = f"{uuid4().hex}_{safe_filename(file.filename)}"
    stored_path = settings.upload_dir / stored_name
    stored_path.write_bytes(payload)

    try:
        raw_text, parser_used, warnings = parser_service.parse_file(stored_path)
        preview = extractor_service.extract(raw_text)
        upload = storage_service.create_upload(
            db,
            filename=file.filename,
            stored_path=stored_path,
            content_type=file.content_type,
            parser_used=parser_used,
            raw_text=raw_text,
            extracted_preview=preview.model_dump(),
            warnings=warnings,
        )
        return UploadResumeResponse(
            upload_id=upload.id,
            filename=upload.original_filename,
            parser_used=upload.parser_used,
            preview=preview,
            warnings=humanize_parsing_warnings(upload.parsing_warnings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail=f"Resume processing failed: {exc}") from exc

