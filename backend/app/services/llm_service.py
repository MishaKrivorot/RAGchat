from groq import Groq
from app.config import settings


class LLMService:
    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set")

        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_query(self, user_question: str) -> str:
        prompt = f"""
Переформулюй запит користувача для пошуку у FAQ або базі знань університету.

Правила:
- збережи початковий зміст;
- прибери зайві слова;
- зроби формулювання коротким, чітким і придатним для пошуку;
- не додавай нових фактів;
- поверни тільки готовий пошуковий запит, без пояснень.

Запит користувача:
{user_question}
""".strip()

        response = self.client.chat.completions.create(
            model=settings.CHAT_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ти допомагаєш переформульовувати запити для пошуку у FAQ."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        return response.choices[0].message.content.strip()

    def generate_answer(
        self,
        user_question: str,
        contexts: list[dict],
        confidence: float = 0.0,
        score_gap: float = 0.0
    ) -> str:
        context_text = "\n\n".join(
            [
                f"Джерело {index + 1}:\n"
                f"Відповідь: {item.get('answer', '')}"
                for index, item in enumerate(contexts)
            ]
        )

        prompt = f"""
Ти — розумний, точний та корисний FAQ-асистент факультету.

🔥 ВАЖЛИВІ ПРАВИЛА:
1. АНАЛІЗ УСІХ ДЖЕРЕЛ: Тобі передано до 5 джерел інформації. Уважно проаналізуй їх усі! Збери до купи всю релевантну інформацію, щоб дати повну та розгорнуту відповідь на питання.
2. ФОРМАТ (БЕЗ РОЗГОРТОК): Формуй відповідь звичайним текстом. Використовуй абзаци, марковані списки та жирний шрифт для виділення головного. КАТЕГОРИЧНО ЗАБОРОНЕНО використовувати HTML-теги `<details>` та `<summary>`.
3. БЕЗ ВОДИ: Жодних вступних чи виправдувальних фраз (заборони собі писати "Згідно з джерелами...", "Наданий контекст говорить..."). Починай одразу з суті.
4. ЧЕСНІСТЬ: Видавай лише ту інформацію, яка є в джерелах. Якщо відповіді немає, коротко порадь звернутися до деканату.

🎓 СПЕЦІАЛЬНІ ПРАВИЛА ВСТУПУ (ФОРМУЛИ ТА БАЛИ):
- Завжди чітко розрізняй ступені: БАКАЛАВР пов'язаний виключно з НМТ (Національний мультипредметний тест), а МАГІСТРАТУРА пов'язана з ЄВІ та ЄФВВ.
- Якщо користувач питає "за якою формулою вираховується бал при вступі?", але не уточнює (бакалавр чи магістр) — ти ОБОВ'ЯЗКОВО повинен знайти в джерелах і вивести ОБИДВІ формули, чітко підписавши: "Для вступу на бакалаврат:" та "Для вступу до магістратури:".

📅 СПЕЦІАЛЬНІ ПРАВИЛА ДЛЯ РОЗКЛАДУ:
- Якщо користувач питає про розклад, але не вказує свою групу чи курс — НЕ ВГАДУЙ! Ввічливо попроси його уточнити ці дані.

Контекст:
{context_text}

Питання користувача:
{user_question}

Сформуй повну та розгорнуту відповідь:
""".strip()

        response = self.client.chat.completions.create(
            model=settings.CHAT_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ти строгий і дуже точний помічник факультету. Видавай лише факти з контексту звичайним відформатованим текстом, аналізуючи всі надані джерела."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.15
        )

        return response.choices[0].message.content.strip()

    def generate_no_context_answer(self, user_question: str) -> str:
        prompt = f"""
Ти корисний асистент FAQ-системи університету.

У базі знань не знайдено надійної відповіді на запит користувача.
Потрібно відповісти українською мовою.

Правила:
- не вигадуй фактів;
- прямо скажи, що точної відповіді у базі знань немає;
- можна м'яко пояснити, що запит варто уточнити;
- порадь звернутися до адміністрації / деканату / відповідального підрозділу;
- відповідь має бути короткою, ввічливою і природною.

Питання користувача:
{user_question}
""".strip()

        response = self.client.chat.completions.create(
            model=settings.CHAT_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти чесний FAQ-помічник. "
                        "Якщо надійного контексту немає, не вигадуй інформацію."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        return response.choices[0].message.content.strip()

    def generate_questions_for_chunk(self, chunk_text: str) -> str:
        import time
        prompt = f"""
Прочитай цей уривок тексту. Сформулюй 2-3 короткі запитання українською мовою, на які текст дає відповідь.
Правила: ТІЛЬКИ питання з нового рядка. Без нумерації, без вступних слів.

Текст:
{chunk_text}
""".strip()

        for attempt in range(5):
            try:
                response = self.client.chat.completions.create(
                    model=settings.INDEX_LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "Ти помічник, який формує питання."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                answer = response.choices[0].message.content.strip()
                
                # 🔥 ФІЛЬТР ВІДМОВ LLM: Якщо модель каже "не бачу", "не можу" - відкидаємо
                bad_phrases = ["не бачу", "не можу", "надішліть", "відсутній", "не містить"]
                if any(phrase in answer.lower() for phrase in bad_phrases):
                    return ""
                    
                return answer
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    time.sleep(65)
                else:
                    return ""
        return ""

    def generate_web_answer(self, user_question: str, web_results: list[dict]) -> str:
        context_text = "\n\n".join(
            [
                f"Сайт: {item['title']}\n"
                f"Посилання: {item['href']}\n"
                f"Текст: {item['body']}"
                for item in web_results
            ]
        )

        prompt = f"""
Ти корисний асистент факультету. У нашій локальній базі не знайшлося відповіді, тому ми здійснили пошук по сайтах КНУ.

Ось що вдалося знайти в мережі:
{context_text}

Питання користувача:
{user_question}

Правила:
1. Сформуй коротку, чітку відповідь на основі цих веб-результатів.
2. Не вигадуй фактів. Якщо у веб-результатах теж немає точної відповіді, так і скажи.
3. ОБОВ'ЯЗКОВО використовуй HTML-розгортки <details> і <summary> для оформлення джерел.
4. У якості заголовка <summary> пиши "Знайдено в мережі: [Назва сайту]".

Сформуй відповідь:
""".strip()

        response = self.client.chat.completions.create(
            model=settings.CHAT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "Ти асистент, який формує відповіді на основі веб-пошуку."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
