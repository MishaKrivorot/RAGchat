from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )

    # 🔥 універсальне створення
    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if collection_name not in names:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    # 🔥 старий метод залишаємо
    def recreate_collection(self, vector_size: int) -> None:
        self.client.recreate_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )

    # 🔥 універсальний upsert
    def upsert_points(self, points: list[PointStruct], collection_name: str | None = None) -> None:
        collection = collection_name or settings.QDRANT_COLLECTION

        self.client.upsert(
            collection_name=collection,
            points=points
        )

    # 🔥 пошук по конкретній колекції
    def search(self, query_vector: list[float], limit: int = 3, collection_name: str | None = None):
        collection = collection_name or settings.QDRANT_COLLECTION

        response = self.client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            with_payload=True
        )

        return response.points

    # 🔥 ОБ'ЄДНАНИЙ ПОШУК (FAQ + SITE)
    def search_all(
        self, query_vector: list[float], limit: int = 3,
        faq_min_score: float = 0.0, site_min_score: float = 0.0
    ):
        results = []

        # FAQ
        faq = self.search(query_vector, limit, settings.QDRANT_COLLECTION)
        for item in faq:
            if float(item.score) < faq_min_score:
                continue
            payload = item.payload or {}
            results.append({
                "id": item.id,                                  
                "likes": payload.get("likes", 0),
                "dislikes": payload.get("dislikes", 0),               
                "question": payload.get("question", payload.get("title", "")),
                "answer": payload.get("text", payload.get("answer", "")),
                "score": float(item.score),
                "source_type": "site", # (або "site" для колекції сайту)
                "url": payload.get("url", ""),
                "title": payload.get("title", "")
            })

        # SITE
        site = self.search(query_vector, limit, settings.SITE_COLLECTION)
        for item in site:
            if float(item.score) < site_min_score:
                continue
            payload = item.payload or {}
            results.append({
                "id": item.id,                                   # <-- НОВЕ
                "likes": payload.get("likes", 0),
                "dislikes": payload.get("dislikes", 0),               # <-- НОВЕ
                "question": payload.get("question", payload.get("title", "")),
                "answer": payload.get("text", payload.get("answer", "")),
                "score": float(item.score),
                "source_type": "site", # (або "site" для колекції сайту)
                "url": payload.get("url", ""),
                "title": payload.get("title", "")
            })

        # 🔥 сортування
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[: limit]

    def search_site_only(self, query_vector: list[float], limit: int = 10, min_score: float = 0.0):
        results = []
        site = self.search(query_vector, limit, settings.SITE_COLLECTION)
        for item in site:
            if float(item.score) < min_score:
                continue
            payload = item.payload or {}
            results.append({
                "id": item.id,                                   
                "likes": payload.get("likes", 0),
                "dislikes": payload.get("dislikes", 0),               
                "question": payload.get("question", payload.get("title", "")),
                "answer": payload.get("text", payload.get("answer", "")),
                "score": float(item.score),
                "source_type": "site",
                "url": payload.get("url", ""),
                "title": payload.get("title", "")
            })
        return results

    def scroll_collection(self, collection_name: str, limit: int = 10):
        records, _ = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True
        )
        return records
    # 🔥 НОВИЙ МЕТОД ДЛЯ ЛАЙКІВ
    # 🔥 МЕТОД ДЛЯ ЛАЙКІВ ТА ДИЗЛАЙКІВ
    def submit_feedback(self, point_id: int | str, collection_name: str, action: str) -> dict:
        if isinstance(point_id, str) and point_id.isdigit():
            point_id = int(point_id)
        points = self.client.retrieve(collection_name=collection_name, ids=[point_id])
        if not points:
            return {"likes": 0, "dislikes": 0}
        
        payload = points[0].payload or {}
        likes = payload.get("likes", 0)
        dislikes = payload.get("dislikes", 0)
        
        if action == "like":
            likes += 1
        elif action == "dislike":
            dislikes += 1
            
        self.client.set_payload(
            collection_name=collection_name,
            payload={"likes": likes, "dislikes": dislikes},
            points=[point_id]
        )
        return {"likes": likes, "dislikes": dislikes}