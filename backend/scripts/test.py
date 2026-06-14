import time
import os
import requests
from google import genai
from groq import Groq

# Ваші тестові питання
test_questions = [
    "Які документи необхідні для вступу на бакалавр ФРЕКС?",
    "Який розклад іспитів у групи КІ факультету РЕКС?",
    "Розкажи про кафедру комп'ютерної інженерії факультету РЕКС?"   
]

# URL вашого розгорнутого бекенду на Railway
FRECS_API_URL = "https://frecs-chat.up.railway.app/api/chat/"


def run_benchmark():
    print("Ініціалізація клієнтів...")
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    for question in test_questions:
        print(f"\n" + "="*70)
        print(f"Запит: {question}")
        print("="*70)
        
        # ---------------------------------------------------------
        # 1. Тестування вашого RAG-чату (FRECS Bot)
        # ---------------------------------------------------------
        try:
            start_rag = time.perf_counter()
            payload = {
                "question": question,
                "session_id": "benchmark-test-session"
            }
            response = requests.post(FRECS_API_URL, json=payload)
            rag_latency = time.perf_counter() - start_rag
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n[FRECS RAG] Час відгуку: {rag_latency:.2f} секунд (Режим: {data.get('mode', 'N/A')})")
                print(f"[FRECS RAG] Повна відповідь:\n{data.get('reply', '')}\n")
            else:
                print(f"\n[FRECS RAG] Помилка сервера: HTTP {response.status_code}\n")
        except Exception as e:
            print(f"\n[FRECS RAG] Помилка підключення: {e}\n")

        # ---------------------------------------------------------
        # 2. Тестування моделі GPT-OSS 120B (через Groq)
        # ---------------------------------------------------------
        try:
            start_groq = time.perf_counter()
            groq_response = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": question}]
            )
            groq_latency = time.perf_counter() - start_groq
            print(f"[openai/gpt-oss-120b] Час відгуку: {groq_latency:.2f} секунд")
            print(f"[openai/gpt-oss-120b] Повна відповідь:\n{groq_response.choices[0].message.content}\n")
        except Exception as e:
            print(f"[openai/gpt-oss-120b] Помилка: {e}\n")

        # ---------------------------------------------------------
        # 3. Тестування Gemini 2.5 Flash (з обробкою помилки 503)
        # ---------------------------------------------------------
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_gem = time.perf_counter()
                gem_response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=question
                )
                gem_latency = time.perf_counter() - start_gem
                print(f"[Gemini Flash] Час відгуку: {gem_latency:.2f} секунд")
                print(f"[Gemini Flash] Повна відповідь:\n{gem_response.text}\n")
                break  # Вихід з циклу при успіху
                
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"[Gemini Flash] Сервер перевантажено (503). Спроба {attempt + 1} з {max_retries}. Очікування {wait_time} сек...")
                    time.sleep(wait_time)
                else:
                    print(f"[Gemini Flash] Помилка: {e}\n")
                    break

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GROQ_API_KEY"):
        print("ПОПЕРЕДЖЕННЯ: API ключі не знайдені у змінних оточення!")
        print("Встановіть GEMINI_API_KEY та GROQ_API_KEY перед запуском.")
    else:
        run_benchmark()