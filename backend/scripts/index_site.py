import hashlib
import time
from qdrant_client.models import PointStruct
from app.services.llm_service import LLMService
from app.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.site_crawler_service import SiteCrawlerService
from app.utils.text_splitter import split_text


START_URLS = [
    # --- ГОЛОВНА ТА ФАКУЛЬТЕТ ---
    "https://rex.knu.ua/",
    "https://rex.knu.ua/faculty/about-us/",               # Про факультет
    "https://rex.knu.ua/faculty/deans-office/",           # Деканат
    "https://rex.knu.ua/faculty/departments/",            # Кафедри факультету
    "https://rex.knu.ua/osvitni-programy/",               # Освітні програми
    
    # --- ДЛЯ ВСТУПНИКІВ (АБІТУРІЄНТІВ) ---
    "https://rex.knu.ua/for-graduates/for-entrance/",     # Загальна інформація до вступу
    "https://rex.knu.ua/for-graduates/for-entrance/entrance-rules/", # Правила прийому
    "https://rex.knu.ua/for-graduates/for-entrance/bachelors/",      # Вступ на бакалаврат
    "https://rex.knu.ua/for-graduates/for-entrance/masters/",        # Вступ до магістратури
    "https://rex.knu.ua/vstup-do-aspirantury/",           # Вступ до аспірантури
    "https://rex.knu.ua/for-graduates/for-entrance/pre-entry-courses/", # Підготовчі курси
    "https://rex.knu.ua/category/dlya-abituriyentiv/",    # Новини для абітурієнтів
    "https://rex.knu.ua/for-graduates/trainings-for-eig/",# Тренінги для ЄВІ/ЄФВВ
    
    # --- ДЛЯ СТУДЕНТІВ ---
    "https://rex.knu.ua/for-students/",                   # Головна сторінка студента
    "https://rex.knu.ua/for-students/class-times/",       # Розклад пар
    "https://rex.knu.ua/grafik-sesiyi/",                  # Графік сесії
    "https://rex.knu.ua/grafiky-pereskladannya/",         # Графіки перескладання
    "https://rex.knu.ua/for-students/dormitory/",         # Гуртожиток
    "https://rex.knu.ua/for-students/books-for-study/",   # Навчальні матеріали
    "https://rex.knu.ua/for-students/student-organizations/", # Студентські організації
    "https://rex.knu.ua/vybir-navchalnyh-dystsyplin/",    # Вибір навчальних дисциплін
    "https://rex.knu.ua/dodatkovi-baly/",                 # Додаткові бали
    "https://rex.knu.ua/pidsumkova-atestatsiya/",         # Підсумкова атестація
    
    # додаткові сторінки
    "https://rex.knu.ua/contacts/"                        # Загальні контакти
]


def make_point_id(url: str, chunk_index: int) -> int:
    raw = f"{url}::{chunk_index}".encode("utf-8")
    return int(hashlib.md5(raw).hexdigest()[:12], 16)


def main():
    embedding_service = EmbeddingService()
    qdrant_service = QdrantService()
    crawler = SiteCrawlerService()
    llm_service = LLMService()

    pages = crawler.crawl(START_URLS)

    if not pages:
        print("Не вдалося отримати сторінки з сайту.")
        return

    test_vector = embedding_service.embed_text("тест")
    qdrant_service.ensure_collection(
        collection_name=settings.SITE_COLLECTION,
        vector_size=len(test_vector)
    )

    points = []
    total_chunks = 0

    print("Починаємо генерацію векторів та питань...")

    for page in pages:
        chunks = split_text(page["text"], chunk_size=900, overlap=150)

        for idx, chunk in enumerate(chunks):
            # 1. Генеруємо питання через LLM
            generated_questions = llm_service.generate_questions_for_chunk(chunk)
            
            # Якщо сталася помилка LLM, беремо заголовок як запасний варіант
            if not generated_questions:
                generated_questions = page["title"]
            
            # 2. Об'єднуємо питання та відповідь для сильнішого вектора
            text_to_embed = f"Питання:\n{generated_questions}\n\nВідповідь:\n{chunk}"
            vector = embedding_service.embed_text(text_to_embed)

            payload = {
                "source_type": "website",
                "site": "rex.knu.ua",
                "url": page["url"],
                "title": page["title"],
                "chunk_index": idx,
                "text": chunk,
                "question": generated_questions,
                "answer": chunk
            }

            points.append(
                PointStruct(
                    id=make_point_id(page["url"], idx),
                    vector=vector,
                    payload=payload
                )
            )
            total_chunks += 1
            print(f"Оброблено чанк {total_chunks}...")
            
            time.sleep(1.5) 

    if points:
        qdrant_service.upsert_points(points=points, collection_name=settings.SITE_COLLECTION)

    print(f"Проіндексовано сторінок: {len(pages)}")
    print(f"Проіндексовано чанків: {total_chunks}")
    print(f"Колекція: {settings.SITE_COLLECTION}")

if __name__ == "__main__":
    main()