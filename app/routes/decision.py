from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import FinalDecisionResult, OverrideDecisionRequest
from app.services.storage import CandidateStorageService


router = APIRouter(tags=["decision"])

storage_service = CandidateStorageService()


@router.post("/decision/override", response_model=FinalDecisionResult)
def override_decision(request: OverrideDecisionRequest, db: Session = Depends(get_db)) -> FinalDecisionResult:
    try:
        version = storage_service.apply_override(
            db,
            candidate_id=request.candidate_id,
            version_id=request.version_id,
            recommendation=request.recommendation,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FinalDecisionResult.model_validate(version.final_decision)

