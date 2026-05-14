from fastembed import TextEmbedding
from app.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)

    def embed_text(self, text: str) -> list[float]:
        return list(self.model.embed([text]))[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self.model.embed(texts)]