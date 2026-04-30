from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import CopilotRequest, CopilotResponse, CodingAssessment, InterviewQuestion, QuestionsResponse
from app.services.copilot import InterviewCopilotService
from app.services.explainability import questions_from_context
from app.services.storage import CandidateStorageService


router = APIRouter(tags=["interview"])

storage_service = CandidateStorageService()
copilot_service = InterviewCopilotService()


@router.get("/questions", response_model=QuestionsResponse)
def get_questions(
    candidate_id: str,
    version_id: str | None = None,
    db: Session = Depends(get_db),
) -> QuestionsResponse:
    version = storage_service.get_version(db, candidate_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Candidate analysis was not found.")

    questions = [InterviewQuestion.model_validate(item) for item in version.interview_questions]
    coding_assessment = CodingAssessment.model_validate(version.coding_assessment)
    return QuestionsResponse(
        candidate_id=candidate_id,
        version_id=version.id,
        questions=questions,
        coding_questions=coding_assessment.questions,
    )


@router.post("/copilot", response_model=CopilotResponse)
def interview_copilot(request: CopilotRequest, db: Session = Depends(get_db)) -> CopilotResponse:
    command = request.resolved_command()
    if not command:
        raise HTTPException(status_code=400, detail="command is required (use 'command' or 'hr_command').")

    questions: list[InterviewQuestion] = []
    if request.candidate_id:
        version = storage_service.get_version(db, request.candidate_id, request.version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Candidate analysis was not found.")
        questions = [InterviewQuestion.model_validate(item) for item in version.interview_questions]
    elif request.candidate_context:
        for item in questions_from_context(request.candidate_context):
            questions.append(
                InterviewQuestion(
                    question=item["question"],
                    expected_answer=item["expected_answer"],
                    difficulty=item["difficulty"],
                    why_this_question=item["why_this_question"],
                    project_name=item["project_name"],
                )
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide candidate_id (saved analysis) or candidate_context with interview_questions.",
        )

    return copilot_service.respond(
        command=command,
        questions=questions,
        current_question_index=request.current_question_index,
    )

