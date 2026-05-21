from pydantic import BaseModel, Field
from typing import List, Optional, Union


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None


class SourceItem(BaseModel):
    id: Union[str, int, None] = None
    likes: int = 0
    dislikes: int = 0
    question: Optional[str] = ""
    answer: str
    score: float
    source_type: Optional[str] = ""
    url: Optional[str] = ""
    title: Optional[str] = ""
    reranked_score: Optional[float] = None

class ChatResponse(BaseModel):
    reply: str
    mode: str
    confidence: float
    sources: List[SourceItem] = []
    fallback_links: Optional[List[dict]] = None

class FeedbackRequest(BaseModel):
    id: str | int
    source_type: str
    action: str