from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.retrieval_service import rerank_by_keywords


def main():
    query = input("Введіть запит: ").strip()

    emb = EmbeddingService()
    qdrant = QdrantService()

    vector = emb.embed_text(query)
    results = qdrant.search_site_only(vector, limit=10, min_score=0.15)
    results = rerank_by_keywords(query, results)

    print("\nRESULTS:\n")
    for i, item in enumerate(results, start=1):
        print("=" * 120)
        print(f"#{i}")
        print("TITLE:", item.get("title"))
        print("URL:", item.get("url"))
        print("SOURCE:", item.get("source_type"))
        print("SCORE:", item.get("score"))
        print("RERANKED:", item.get("reranked_score"))
        print("TEXT:", item.get("answer", "")[:800])
        print()

if __name__ == "__main__":
    main()