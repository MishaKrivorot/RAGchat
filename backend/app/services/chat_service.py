from app.config import settings
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.web_search_service import WebSearchService  # Додано сервіс веб-пошуку
from app.utils.greetings import is_greeting, greeting_response


class ChatService:
    def __init__(self) -> None:
        self.retrieval_service = RetrievalService()
        self.llm_service = LLMService() if settings.USE_LLM else None
        self.web_search = WebSearchService()  # Ініціалізація веб-пошуку

    def handle_question(self, question: str) -> dict:
        if is_greeting(question):
            return {
                "reply": greeting_response(),
                "mode": "greeting",
                "confidence": 1.0,
                "sources": [],
                "fallback_links": []
            }

        try:
            search_question = question

            if settings.USE_LLM and self.llm_service:
                search_question = self.llm_service.rewrite_query(question)

            retrieval_data = self.retrieval_service.retrieve(search_question)
            results = retrieval_data.get("results", [])
            retrieval_mode = retrieval_data.get("mode", "general")
            fallback_links = retrieval_data.get("fallback_links", [])

        except Exception as e:
            return {
                "reply": f"Сталася помилка під час обробки запиту: {str(e)}",
                "mode": "error",
                "confidence": 0.0,
                "sources": [],
                "fallback_links": []
            }

        top_score = results[0].get("reranked_score", results[0].get("score", 0.0)) if results else 0.0
        min_score = settings.SIMILARITY_THRESHOLD

        # 🔥 FALLBACK (ВЕБ-ПОШУК): Якщо результатів немає або впевненість занадто низька
        if not results or top_score < min_score:
            web_results = self.web_search.search(search_question, limit=3)

            if web_results and settings.USE_LLM and self.llm_service:
                try:
                    answer = self.llm_service.generate_web_answer(question, web_results)
                    
                    # Маскуємо результати під стандартні "джерела", щоб фронтенд малював розгортки
                    formatted_web_sources = [
                        {
                            "question": f"Знайдено в мережі: {r['title']}",
                            "answer": f"{r['body']}\n\nПосилання: {r['href']}",
                            "score": top_score
                        }
                        for r in web_results
                    ]
                    
                    return {
                        "reply": answer,
                        "mode": "web_search_fallback",
                        "confidence": top_score,
                        "sources": formatted_web_sources,
                        "fallback_links": fallback_links
                    }
                except Exception as e:
                    pass # Якщо сталася помилка LLM при роботі з інтернетом, йдемо до генерації відмови

            # Якщо і в інтернеті нічого немає або виникла помилка
            if settings.USE_LLM and self.llm_service:
                try:
                    answer = self.llm_service.generate_no_context_answer(question)
                    return {
                        "reply": answer,
                        "mode": "llm_no_context",
                        "confidence": 0.0,
                        "sources": [],
                        "fallback_links": []
                    }
                except Exception as e:
                    return {
                        "reply": f"Я не знайшов відповіді у базі знань. Помилка LLM: {str(e)}",
                        "mode": "no_results",
                        "confidence": 0.0,
                        "sources": [],
                        "fallback_links": []
                    }

            return {
                "reply": "Я не знайшов релевантної відповіді у базі знань.",
                "mode": "no_results",
                "confidence": 0.0,
                "sources": [],
                "fallback_links": fallback_links
            }


        # --- СТАРА ЛОГІКА ДЛЯ ЛОКАЛЬНОЇ БАЗИ (ЯКЩО ВПЕВНЕНІСТЬ ВИСОКА) ---
        sources = results
        second_score = sources[1].get("reranked_score", sources[1].get("score", 0.0)) if len(sources) > 1 else 0.0
        score_gap = top_score - second_score
        min_gap = getattr(settings, "MIN_SCORE_GAP", 0.08)

        # Відсікаємо занадто шумні джерела, але залишаємо більше корисних
        filtered_sources = [
            item for item in sources
            if item.get("reranked_score", item.get("score", 0.0)) >= max(top_score - 0.15, 0.0)
        ]

        if not filtered_sources:
            filtered_sources = [sources[0]]

        # 🔥 ЗМІНА: Беремо всі 5 джерел для глибокого аналізу, а не 1
        filtered_sources = filtered_sources[:5]

        if settings.USE_LLM and self.llm_service:
            try:
                answer = self.llm_service.generate_answer(
                    user_question=question,
                    contexts=filtered_sources,
                    confidence=top_score,
                    score_gap=score_gap
                )

                mode = "rag_llm"
                if score_gap < min_gap:
                    mode = "rag_llm_low_confidence"

                return {
                    "reply": answer,
                    "mode": mode,
                    "confidence": top_score,
                    "sources": sources,
                    "fallback_links": fallback_links
                }
            except Exception as e:
                return {
                    "reply": f"Сталася помилка під час генерації відповіді: {str(e)}",
                    "mode": "error",
                    "confidence": top_score,
                    "sources": sources,
                    "fallback_links": fallback_links
                }

        return {
            "reply": sources[0]["answer"],
            "mode": retrieval_mode,
            "confidence": top_score,
            "sources": sources,
            "fallback_links": fallback_links
        }