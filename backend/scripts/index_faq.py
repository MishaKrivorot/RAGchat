import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qdrant_client.models import PointStruct
from app.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService


def load_faq(path: str):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    faq_data = load_faq(settings.FAQ_PATH)

    embedding_service = EmbeddingService()
    qdrant_service = QdrantService()

    texts_for_embedding = [item["question"] for item in faq_data]

    first_vector = embedding_service.embed_text(texts_for_embedding[0])
    vector_size = len(first_vector)

    qdrant_service.recreate_collection(vector_size=vector_size)

    points = []
    for idx, item in enumerate(faq_data):
        text_to_embed = f"Питання: {item['question']} Відповідь: {item['answer']}"
        vector = embedding_service.embed_text(text_to_embed)
        
        points.append(
            PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "question": item["question"],
                    "answer": item["answer"]
                }
            )
        )

    qdrant_service.upsert_points(points)
    print(f"Indexed {len(points)} FAQ items into Qdrant collection '{settings.QDRANT_COLLECTION}'")


if __name__ == "__main__":
    main()