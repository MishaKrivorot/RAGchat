import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FAQ RAG Chatbot")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")

    FAQ_PATH: str = os.getenv("FAQ_PATH", "data/faqs.json")

    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "faq_collection")
    SITE_COLLECTION: str = os.getenv("SITE_COLLECTION", "site_collection")

    TOP_K: int = int(os.getenv("TOP_K", "3"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.45"))
    MIN_SCORE_GAP: float = float(os.getenv("MIN_SCORE_GAP", "0.08"))

    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"

    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # === РОЗДІЛЕННЯ МОДЕЛЕЙ ===
    CHAT_LLM_MODEL: str = os.getenv("CHAT_LLM_MODEL", "llama-3.3-70b-versatile")
    INDEX_LLM_MODEL: str = os.getenv("INDEX_LLM_MODEL", "llama-3.1-8b-instant")

    SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://rex.knu.ua")
    SITE_MAX_PAGES: int = int(os.getenv("SITE_MAX_PAGES", "50"))
    SITE_REQUEST_TIMEOUT: int = int(os.getenv("SITE_REQUEST_TIMEOUT", "20"))

settings = Settings()