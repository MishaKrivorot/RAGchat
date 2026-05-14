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
            ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar"
        )
        if parsed.path.lower().endswith(bad_suffixes):
            return False

        return True

    def _clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def _extract_pdf_text(self, url: str) -> tuple[str, str]:
        try:
            import pymupdf4llm
            import tempfile
            import os

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Зберігаємо файл тимчасово, оскільки pymupdf4llm працює з файловою системою
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            # Магія: конвертуємо PDF у Markdown зі збереженням таблиць!
            md_text = pymupdf4llm.to_markdown(tmp_path)
            os.remove(tmp_path)

            title = url.split("/")[-1]
            if not title:
                title = "Документ розкладу/сесії"

            return title, md_text.strip()
        except ImportError:
            print(f"pymupdf4llm не встановлено. Не можу обробити {url}")
            return "PDF Document", ""
        except Exception as e:
            print(f"Помилка обробки PDF {url}: {e}")
            return "PDF Document", ""

    def _extract_text(self, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "noscript", "svg", "img", "form", "iframe"]):
            tag.decompose()

        for selector in [
            "header", "footer", "nav", ".menu", ".navbar", ".sidebar",
            ".widget", ".breadcrumbs", ".search-form"
        ]:
            for el in soup.select(selector):
                el.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else "Без назви"

        main_candidates = [
            soup.find("main"),
            soup.find("article"),
            soup.find("div", class_="entry-content"),
            soup.find("div", class_="post-content"),
            soup.find("div", class_="content"),
        ]

        main_block = next((item for item in main_candidates if item), soup.body or soup)

        text = " ".join(main_block.stripped_strings)
        text = " ".join(text.split())

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

    def _extract_text(self, html: str) -> tuple[str, str]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "noscript", "svg", "img", "form", "iframe"]):
            tag.decompose()

        for selector in [
            "header", "footer", "nav", ".menu", ".navbar", ".sidebar",
            ".widget", ".breadcrumbs", ".search-form"
        ]:
            for el in soup.select(selector):
                el.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else "Без назви"

        main_candidates = [
            soup.find("main"),
            soup.find("article"),
            soup.find("div", class_="entry-content"),
            soup.find("div", class_="post-content"),
            soup.find("div", class_="content"),
        ]

        main_block = next((item for item in main_candidates if item), soup.body or soup)

        if main_block:
            text = " ".join(main_block.stripped_strings)
            text = " ".join(text.split())
        else:
            text = ""

        return title, text

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

            if current_url.lower().endswith(".pdf"):
                visited.add(current_url)
                try:
                    title, text = self._extract_pdf_text(current_url)
                    if text and len(text) > 50:
                        pages.append({
                            "url": current_url,
                            "title": title,
                            "text": text
                        })
                except Exception as e:
                    # ТЕПЕР МИ БАЧИМО ПОМИЛКУ PDF
                    print(f"❌ Помилка PDF {current_url}: {e}")
                    pass
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