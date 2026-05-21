import requests
from bs4 import BeautifulSoup
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

def normalize_text(text: str) -> str:
    return text.lower().replace("’", "'").replace("`", "'").replace("ё", "е")

# ==========================================
# КОНФІГУРАЦІЯ LIVE-МАРШРУТИЗАЦІЇ ТА СИНОНІМІВ
# ==========================================
LIVE_CATEGORIES = {
    "schedule": {
        "keywords": ["розклад", "пари", "заняття", "сесі", "іспит", "екзамен", "залік", "перескладан", "коли пари", "графік"],
        "urls": [
            ("Розклад пар", "https://rex.knu.ua/for-students/class-times/"),
            ("Графік сесії", "https://rex.knu.ua/grafik-sesiyi/"),
            ("Графіки перескладання", "https://rex.knu.ua/grafiky-pereskladannya/")
        ],
        "pdf_only": True
    },
    "about_us": {
        "keywords": ["про факультет", "історія факультету", "керівництво", "декан", "контакти", "про нас", "інформація про", "реквізити"],
        "urls": [("Про факультет", "https://rex.knu.ua/faculty/about-us/")],
        "pdf_only": False
    },
    "programs": {
        "keywords": ["освітні програм", "освітня програм", "спеціальніст", "спеціальност", "бакалавр", "магістр", "опп", "онп", "напрям"],
        "urls": [("Освітні програми", "https://rex.knu.ua/osvitni-programy/")],
        "pdf_only": False
    },
    "departments": {
        "keywords": ["кафедр", "викладач", "завідувач"],
        "urls": [("Кафедри факультету", "https://rex.knu.ua/faculty/departments/")],
        "pdf_only": False
    },
    "trainings": {
        "keywords": ["єві", "єфвв", "підготовка до", "курси", "тренінг", "вступні іспити"],
        "urls": [("Підготовка до ЄВІ/ЄФВВ", "https://rex.knu.ua/for-graduates/trainings-for-eig/")],
        "pdf_only": False
    },
    "electives": {
        "keywords": ["вибіркові дисциплін", "вибіркові предмет", "вибір дисциплін", "ф-каталог", "вільний вибір", "вибірков"],
        "urls": [("Вибір навчальних дисциплін", "https://rex.knu.ua/vybir-navchalnyh-dystsyplin/")],
        "pdf_only": False
    },
    "extra_points": {
        "keywords": ["додаткові бал", "рейтинг", "додатковий бал", "стипендія", "додаткових бал", "бали за активність"],
        "urls": [("Додаткові бали", "https://rex.knu.ua/dodatkovi-baly/")],
        "pdf_only": False
    },
    "final_exams": {
        "keywords": ["підсумкова атестаці", "захист диплом", "кваліфікаційна робот", "випускні іспит", "дипломна робот", "атестація"],
        "urls": [("Підсумкова атестація", "https://rex.knu.ua/pidsumkova-atestatsiya/")],
        "pdf_only": False
    }
}

# ==========================================
# АЛГОРИТМ ПЕРЕРАНЖУВАННЯ
# ==========================================
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

        url_mapping = {
            "вступ": ["for-entrance", "bachelors", "masters", "vstup", "entrance-rules"],
            "гуртожиток": ["dormitory"],
            "поселен": ["dormitory"],
            "організаці": ["student-organizations"],
            "студрад": ["student-organizations"],
            "деканат": ["deans-office"],
            "освіт": ["osvitni-programy"],
            "кафедр": ["departments"]
        }

        for keyword, paths in url_mapping.items():
            if keyword in query_norm:
                if any(path in url for path in paths) or keyword in title:
                    bonus += 0.25

        item = dict(item)
        raw_new_score = score + bonus
        item["reranked_score"] = min(max(raw_new_score, 0.0), 1.0) 
        item["score"] = item["reranked_score"] 
        boosted.append(item)

    boosted.sort(key=lambda x: x["score"], reverse=True)
    return boosted

# ==========================================
# ЛОГІКА LIVE-ПАРСИНГУ
# ==========================================
def fetch_live_page_content(url: str, pdf_only: bool = False) -> str:
    """Парсить сторінку в реальному часі: дістає PDF або чистий свіжий текст"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(resp.text, 'lxml')
        
        main_block = soup.find('main') or soup.find('div', class_='entry-content') or soup.body
        if not main_block:
            return ""

        if pdf_only:
            pdf_links = []
            for a in main_block.find_all('a', href=True):
                href = a['href']
                if href.lower().endswith('.pdf'):
                    text = a.get_text(strip=True) or "Документ"
                    pdf_links.append(f"• {text}: ({href})")
            return "\n".join(pdf_links)
        else:
            elements = main_block.find_all(['h2', 'h3', 'p', 'li', 'a'])
            lines = []
            for el in elements:
                if el.name == 'a' and el.get('href', '').endswith('.pdf'):
                    lines.append(f"📄 [Документ] {el.get_text(strip=True)}: {el['href']}")
                elif el.name in ['h2', 'h3']:
                    lines.append(f"\n🔹 {el.get_text(strip=True)}")
                elif el.name == 'li':
                    lines.append(f"- {el.get_text(strip=True)}")
                elif el.name == 'p':
                    text = el.get_text(strip=True)
                    if len(text) > 30:
                        lines.append(text)
            
            content = "\n".join(dict.fromkeys(lines))
            return content[:1500] + "...\n[Більше інформації за посиланням]" if len(content) > 1500 else content

    except Exception as e:
        print(f"Помилка live-парсингу {url}: {e}")
        return ""

class RetrievalService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def retrieve(self, user_question: str) -> dict:
        query_vector = self.embedding_service.embed_text(user_question)
        user_question_norm = normalize_text(user_question)

        # 1. Пошук по локальній базі Qdrant (Робимо завжди!)
        qdrant_results = self.qdrant_service.search_all(
            query_vector=query_vector,
            limit=15,
            faq_min_score=0.45,
            site_min_score=0.25
        )
        reranked_results = rerank_by_keywords(user_question, qdrant_results)

        # 2. Аналіз: Чи потрібен Live-парсинг?
        live_contexts = []
        matched_fallback_links = []
        
        for category, data in LIVE_CATEGORIES.items():
            if any(word in user_question_norm for word in data["keywords"]):
                for title, url in data["urls"]:
                    matched_fallback_links.append({"title": title, "url": url})
                    content = fetch_live_page_content(url, pdf_only=data["pdf_only"])
                    if content:
                        live_contexts.append(f"=== ОФІЦІЙНИЙ САЙТ: {title} ===\n{content}")

        # 3. Гібридне злиття (Live + Qdrant)
        if live_contexts:
            combined_live_text = "\n\n".join(live_contexts)

            live_source = {
                "id": "live_fetch_combined",
                "score": 1.0,
                "reranked_score": 1.0,
                "title": "🔴 Актуальна інформація з сайту (Live-парсинг)",
                "url": matched_fallback_links[0]["url"] if matched_fallback_links else "",
                "answer": f"УВАГА ДЛЯ LLM: Це найсвіжіші дані з сайту. Використовуй їх у першу чергу, а дані з інших джерел Qdrant - як доповнення.\n\n{combined_live_text}",
                "likes": 0,
                "dislikes": 0
            }
            final_results = [live_source] + reranked_results[:4]
            mode = "hybrid_live_qdrant"
        else:
            final_results = reranked_results[:5]
            mode = "general_qdrant"

        return {
            "mode": mode,
            "results": final_results,
            "fallback_links": matched_fallback_links
        }