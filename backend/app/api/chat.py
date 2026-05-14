from fastapi import APIRouter
from app.schemas import QueryRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


@router.post("/", response_model=ChatResponse)
def chat(request: QueryRequest):
    result = chat_service.handle_question(request.question)
    return ChatResponse(**result)