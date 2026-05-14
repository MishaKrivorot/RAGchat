from app.config import settings
from app.services.qdrant_service import QdrantService


def main():
    qdrant = QdrantService()

    print("Collection:", settings.SITE_COLLECTION)
    print("-" * 100)

    points = qdrant.scroll_collection(settings.SITE_COLLECTION, limit=15)

    for p in points:
        payload = p.payload or {}
        print("=" * 100)
        print("ID:", p.id)
        print("TITLE:", payload.get("title", ""))
        print("URL:", payload.get("url", ""))
        print("SOURCE_TYPE:", payload.get("source_type", ""))
        print("TEXT:", payload.get("text", "")[:700])
        print()

if __name__ == "__main__":
    main()