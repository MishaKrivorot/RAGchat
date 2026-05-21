from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.chat import router as chat_router

from app.schemas import FeedbackRequest
from app.services.qdrant_service import QdrantService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500", 
        "http://127.0.0.1:5500",
        "https://frecs-bot.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix=settings.API_PREFIX)

@app.post("/api/chat/feedback")
def handle_feedback(req: FeedbackRequest):
    qdrant = QdrantService()
    collection = settings.QDRANT_COLLECTION if req.source_type == "faq" else settings.SITE_COLLECTION
    
    counts = qdrant.submit_feedback(req.id, collection, req.action)
    
    return {"status": "success", "likes": counts["likes"], "dislikes": counts["dislikes"]}

@app.get("/")
def root():
    return {
        "message": "FAQ RAG backend is running",
        "version": settings.APP_VERSION
    }