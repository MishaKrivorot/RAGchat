from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.chat import router as chat_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # потім краще обмежити
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {
        "message": "FAQ RAG backend is running",
        "version": settings.APP_VERSION
    }