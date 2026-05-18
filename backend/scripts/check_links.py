from app.services.site_crawler_service import SiteCrawlerService
from app.services.llm_service import LLMService

def main():
    crawler = SiteCrawlerService()
    llm = LLMService()
    
    urls = [
        "https://rex.knu.ua/for-students/class-times/",
        "https://rex.knu.ua/grafik-sesiyi/"
    ]
    
    for url in urls:
        print(f"\n{'='*60}\n🔗 ТЕСТУЄМО СТОРІНКУ: {url}\n{'='*60}")
        
        try:
            response = crawler.session.get(url, timeout=crawler.timeout)
            html = response.text
        except Exception as e:
            print(f"Помилка завантаження: {e}")
            continue

        title, text = crawler._extract_text(html)
        
        print(f"📌 ЗАГОЛОВОК: {title}")
        print(f"📄 ЯК ТЕКСТ БАЧИТЬ БАЗА (перші 400 симв):\n{text[:400]}...\n")
        
        print("🤖 ПИТАННЯ ВІД LLM ДЛЯ ЦЬОГО ТЕКСТУ:")
        # Беремо перші 900 символів (як під час реальної індексації)
        # Беремо перші 900 символів (як під час реальної індексації)
        questions = llm.generate_questions_for_chunk(text[:900], title)
        print(questions)
        print("="*60)

if __name__ == "__main__":
    main()