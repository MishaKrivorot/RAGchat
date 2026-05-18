from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.config import settings


class SiteCrawlerService:
    def __init__(self) -> None:
        self.base_url = settings.SITE_BASE_URL.rstrip("/")
        self.domain = urlparse(self.base_url).netloc
        self.timeout = settings.SITE_REQUEST_TIMEOUT
        self.max_pages = settings.SITE_MAX_PAGES
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def _is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != self.domain:
            return False

        bad_suffixes = (
            ".jpg", ".jpeg", ".png", ".gif", ".svg",
            ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".pdf"
        )
        if parsed.path.lower().endswith(bad_suffixes):
            return False

        return True

    def _clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def _extract_text(self, html: str) -> tuple[str, str]:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin 
        
        soup = BeautifulSoup(html, "lxml")

        # 1. Видаляємо технічні та непотрібні теги
        for tag in soup(["script", "style", "noscript", "svg", "img", "form", "iframe"]):
            tag.decompose()

        # 2. Видаляємо навігацію, меню, шапки та підвали
        for selector in [
            "header", "footer", "nav", ".menu", ".navbar", ".sidebar",
            ".widget", ".breadcrumbs", ".search-form"
        ]:
            for el in soup.select(selector):
                el.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else "Без назви"

        # 3. Шукаємо блок з головним контентом
        main_candidates = [
            soup.find("main"),
            soup.find("article"),
            soup.find("div", class_="entry-content"),
            soup.find("div", class_="post-content"),
            soup.find("div", class_="content"),
        ]

        main_block = next((item for item in main_candidates if item), soup.body or soup)

        if main_block:
            # 🔥 4. Зберігаємо посилання у форматі "Текст (URL)"
            for a in main_block.find_all("a", href=True):
                link_text = a.get_text(strip=True)
                url = a["href"]
                # Ігноруємо порожні тексти та внутрішні якорі сторінки
                if link_text and not url.startswith("#"):
                    full_url = urljoin(self.base_url, url) 
                    a.string = f"{link_text} ({full_url})" 

            # 5. Витягуємо чистий текст (вже з дописаними URL)
            text = " ".join(main_block.stripped_strings)
            text = " ".join(text.split())
        else:
            text = ""

        return title, text

    def _extract_links(self, html: str, current_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(current_url, href)
            full_url = self._clean_url(full_url)

            if self._is_valid_url(full_url):
                links.append(full_url)

        return list(dict.fromkeys(links))

    def crawl(self, start_urls: list[str]) -> list[dict]:
        visited = set()
        queue = deque(start_urls)
        pages = []

        while queue and len(visited) < self.max_pages:
            current_url = self._clean_url(queue.popleft())

            if current_url in visited:
                continue
            if not self._is_valid_url(current_url):
                continue
            try:
                response = self.session.get(current_url, timeout=self.timeout)
                response.raise_for_status()
                html = response.text
            except Exception as e:
                # ТЕПЕР МИ БАЧИМО ПОМИЛКУ ЗАВАНТАЖЕННЯ СТОРІНКИ
                print(f"❌ Помилка завантаження {current_url}: {e}")
                visited.add(current_url)
                continue

            visited.add(current_url)

            try:
                title, text = self._extract_text(html)
            except Exception as e:
                # НА ВСЯКИЙ ВИПАДОК ДОДАВ ВИВІД І СЮДИ
                print(f"❌ Помилка витягування тексту з {current_url}: {e}")
                continue

            if text and len(text) > 200:
                pages.append({
                    "url": current_url,
                    "title": title,
                    "text": text
                })

            links = self._extract_links(html, current_url)
            for link in links:
                if link not in visited:
                    queue.append(link)

        return pages