from duckduckgo_search import DDGS

class WebSearchService:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, limit: int = 3) -> list[dict]:
        search_query = f"{query} site:knu.ua"
        
        try:
            results = self.ddgs.text(search_query, region='ua-uk', safesearch='moderate', max_results=limit)
            
            if not results:
                return []
                
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                }
                for r in results
            ]
        except Exception as e:
            print(f"Помилка веб-пошуку: {e}")
            return []
