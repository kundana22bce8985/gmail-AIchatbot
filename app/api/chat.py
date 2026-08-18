from fastapi import APIRouter
from pydantic import BaseModel

from app.services.vector_store import search_emails
from app.services.llm_service import generate_answer


router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.post("/chat")
def chat(request: ChatRequest):
    # 1. Search FAISS
    documents = search_emails(request.question, k=5)

    # 2. Generate answer using Groq
    answer = generate_answer(
        request.question,
        documents
    )

    return {
        "question": request.question,
        "answer": answer
    }