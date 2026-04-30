from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import AssistantChatRequest, AssistantChatResponse
from app.services.assistant import AssistantChatService


router = APIRouter(tags=["assistant"])

assistant_service = AssistantChatService()


@router.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    return assistant_service.answer(request)
