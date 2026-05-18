import requests
from bs4 import BeautifulSoup
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

# 🔥 Оновили статтю на актуальні лінки
SCHEDULE_URLS = [
    {"title": "Розклад пар", "url": "https://rex.knu.ua/for-students/class-times/"},
    {"title": "Графік сесії", "url": "https://rex.knu.ua/grafik-sesiyi/"},
    {"title": "Графіки перескладання", "url": "https://rex.knu.ua/grafiky-pereskladannya/"}
]

def normalize_text(text: str) -> str:
    return text.lower().replace("’", "'").replace("`", "'").replace("ё", "е")

def is_schedule_query(text: str) -> bool:
    text = normalize_text(text)
    keywords = [
        "розклад", "пари", "заняття", "урок",
        "сесія", "сесії", "іспит", "іспити", "екзамен", 
        "залік", "заліки", "перескладання", "захист",
        "коли пари", "який розклад"
    ]
    return any(word in text for word in keywords)

def is_programs_query(text: str) -> bool:
    text = normalize_text(text)
    keywords = [
        "освітні програми", "освітня програма", "які є програми",
        "спеціальності", "спеціальність", "програми навчання",
        "бакалавр", "магістр", "опп", "онп"
    ]
    return any(word in text for word in keywords)

def rerank_by_keywords(query: str, results: list[dict]) -> list[dict]:
    query_norm = normalize_text(query)
    query_words = [w for w in query_norm.split() if len(w) > 3]

    boosted = []
    for item in results:
        score = float(item.get("score", 0))
        likes = int(item.get("likes", 0))
        dislikes = int(item.get("dislikes", 0))
        title = normalize_text(item.get("title", ""))
        answer = normalize_text(item.get("answer", ""))
        url = normalize_text(item.get("url", ""))

        bonus = 0.0
        bonus += (likes * 0.02) - (dislikes * 0.05)

        for word in query_words:
            root = word[:4] 
            if root in title:
                bonus += 0.08
            if root in url:
                bonus += 0.05
            if root in answer:
                bonus += 0.02

        # 🔥 РОЗУМНИЙ МАРШРУТИЗАТОР ПО ВУЗЛАХ САЙТУ
        url_mapping = {
            "вступ": ["for-entrance", "bachelors", "masters", "vstup", "entrance-rules"],
            "гуртожиток": ["dormitory"],
            "поселен": ["dormitory"],
            "книг": ["books-for-study"],
            "матеріал": ["books-for-study"],
            "організаці": ["student-organizations"],
            "студрад": ["student-organizations"],
            "кафедр": ["departments"],
            "деканат": ["deans-office"]
        }

        for keyword, paths in url_mapping.items():
            if keyword in query_norm:
                if any(path in url for path in paths) or keyword in title:
                    bonus += 0.25

        # Залишаємо специфічні перевірки
        if any(w in query_norm for w in ["розклад", "сесі", "іспит", "перескладан", "залік"]):
            if any(u in url for u in ["class-times", "grafik-sesiyi", "grafiky-pereskladannya", "schedule"]) or \
               any(t in title for t in ["розклад", "сесія", "перескладання"]):
                bonus += 0.25

        if "освіт" in query_norm or "програм" in query_norm or "спеціальн" in query_norm:
            if "освіт" in title or "програм" in title:
                bonus += 0.20
            if "osvitni-programy" in url:
                bonus += 0.30

        item = dict(item)
        raw_new_score = score + bonus
        item["reranked_score"] = min(max(raw_new_score, 0.0), 1.0) 
        
        item["score"] = item["reranked_score"] 
        boosted.append(item)

    boosted.sort(key=lambda x: x["score"], reverse=True)
    return boosted

# ==========================================
# 🔥 ЛОГІКА LIVE-ПАРСИНГУ (В РЕАЛЬНОМУ ЧАСІ)
# ==========================================
def fetch_live_pdfs(url: str) -> str:
    """Парсить сторінку в реальному часі і дістає всі PDF-посилання"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Шукаємо основний контент
        main_block = soup.find('main') or soup.find('div', class_='entry-content') or soup.body
        if not main_block:
            return ""
            
        pdf_links = []
        for a in main_block.find_all('a', href=True):
            href = a['href']
            # Шукаємо всі посилання, що закінчуються на .pdf
            if href.lower().endswith('.pdf'):
                text = a.get_text(strip=True) or "Документ"
                # Додаємо форматування для LLM
                pdf_links.append(f"• {text}: ({href})")
        
        return "\n".join(pdf_links)
    except Exception as e:
        print(f"Помилка live-парсингу {url}: {e}")
        return ""

def get_live_schedule_context() -> str:
    """Збирає свіжі PDF з усіх сторінок розкладу та сесії"""
    pages = [
        ("РОЗКЛАД ПАР", "https://rex.knu.ua/for-students/class-times/"),
        ("ІСПИТИ, ЗАЛІКИ ТА ГРАФІК ЗАХИСТУ ДИПЛОМНИХ РОБІТ", "https://rex.knu.ua/grafik-sesiyi/"),
        ("ГРАФІКИ ПЕРЕСКЛАДАННЯ", "https://rex.knu.ua/grafiky-pereskladannya/")
    ]
    
    result_text = ""
    for title, url in pages:
        pdfs = fetch_live_pdfs(url)
        if pdfs:
            result_text += f"\n--- {title} ---\n{pdfs}\n"
            
    return result_text.strip()
# ==========================================

class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def retrieve(self, user_question: str) -> dict:
        query_vector = self.embedding_service.embed_text(user_question)

        # 🔥 Спеціальна логіка для розкладу (LIVE PARSING)
        if is_schedule_query(user_question):
            # 1. Пробуємо отримати розклад в реальному часі!
            live_text = get_live_schedule_context()
            
            if live_text:
                return {
                    "mode": "schedule_live",
                    "results": [{
                        "id": "live_fetch",
                        "score": 1.0,
                        "reranked_score": 1.0,
                        "title": "Розклади, графік сесії та перескладання (Live-дані)",
                        "url": "https://rex.knu.ua/for-students/",
                        "answer": f"Ось найсвіжіші PDF-документи, щойно отримані з усіх сторінок розкладу:\n{live_text}",
                        "likes": 0,
                        "dislikes": 0
                    }],
                    "fallback_links": SCHEDULE_URLS
                }
            
            # 2. Якщо сайт тимчасово не працює і live-парсинг не вдався, 
            # шукаємо в нашій базі Qdrant (Fallback)
            site_results = self.qdrant_service.search_site_only(
                query_vector=query_vector,
                limit=10,
                min_score=0.22
            )
            site_results = rerank_by_keywords(user_question, site_results)

            return {
                "mode": "schedule_qdrant",
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