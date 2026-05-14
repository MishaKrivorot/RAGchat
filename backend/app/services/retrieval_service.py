from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService


SCHEDULE_URLS = [
    {
        "title": "Розклад студентів",
        "url": "https://rex.knu.ua/for-students/schedule"
    },
    {
        "title": "Навчальний розклад факультету",
        "url": "https://rex.knu.ua/faculty/education-schedule"
    }
]


def normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("’", "'")
        .replace("`", "'")
        .replace("ё", "е")
    )


def is_schedule_query(text: str) -> bool:
    text = normalize_text(text)
    keywords = [
        "розклад", "пари", "заняття", "урок",
        "понеділок", "вівторок", "середа", "четвер",
        "п'ятниця", "пятниця", "субота",
        "курс", "група", "коли пари", "який розклад"
    ]
    return any(word in text for word in keywords)


def is_programs_query(text: str) -> bool:
    text = normalize_text(text)
    keywords = [
        "освітні програми",
        "освітня програма",
        "які є програми",
        "спеціальності",
        "спеціальність",
        "програми навчання",
        "бакалавр",
        "магістр",
        "опп",
        "онп"
    ]
    return any(word in text for word in keywords)


def rerank_by_keywords(query: str, results: list[dict]) -> list[dict]:
    query_norm = normalize_text(query)
    # Беремо слова довші за 3 символи, щоб відсіяти прийменники
    query_words = [w for w in query_norm.split() if len(w) > 3]

    boosted = []
    for item in results:
        score = float(item.get("score", 0))
        title = normalize_text(item.get("title", ""))
        answer = normalize_text(item.get("answer", ""))
        url = normalize_text(item.get("url", ""))

        bonus = 0.0

        for word in query_words:
            # Беремо перші 4 літери (корінь), щоб "попрати" і "пральн" мали більше шансів на збіг
            # або хоча б частково перетиналися
            root = word[:4] 
            if root in title:
                bonus += 0.08
            if root in url:
                bonus += 0.05
            if root in answer:
                bonus += 0.02

        if "розклад" in query_norm:
            if "schedule" in url or "розклад" in title:
                bonus += 0.20

        if "освіт" in query_norm or "програм" in query_norm or "спеціальн" in query_norm:
            if "освіт" in title or "програм" in title:
                bonus += 0.20
            if "osvitni-programy" in url:
                bonus += 0.30

        item = dict(item)
        item["reranked_score"] = score + bonus
        
        # ВИПРАВЛЕННЯ: перезаписуємо оригінальний score, щоб фронтенд і LLM бачили правильний порядок
        item["score"] = item["reranked_score"] 
        boosted.append(item)

    # Сортуємо вже за оновленим score
    boosted.sort(key=lambda x: x["score"], reverse=True)
    return boosted


class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def retrieve(self, user_question: str) -> dict:
        query_vector = self.embedding_service.embed_text(user_question)

        # Спеціальна логіка для розкладу
        if is_schedule_query(user_question):
            site_results = self.qdrant_service.search_site_only(
                query_vector=query_vector,
                limit=10,
                min_score=0.22
            )
            site_results = rerank_by_keywords(user_question, site_results)

            return {
                "mode": "schedule",
                "results": site_results[:5],
                "fallback_links": SCHEDULE_URLS
            }

        # Спеціальна логіка для освітніх програм
        if is_programs_query(user_question):
            site_results = self.qdrant_service.search_site_only(
                query_vector=query_vector,
                limit=10,
                min_score=0.20
            )
            site_results = rerank_by_keywords(user_question, site_results)

            return {
                "mode": "programs",
                "results": site_results[:5],
                "fallback_links": []
            }

        # Загальний пошук
        results = self.qdrant_service.search_all(
            query_vector=query_vector,
            limit=15,
            faq_min_score=0.45,
            site_min_score=0.30
        )
        results = rerank_by_keywords(user_question, results)

        return {
            "mode": "general",
            "results": results[:5],
            "fallback_links": []
        }
