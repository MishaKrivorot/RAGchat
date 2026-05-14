GREETINGS = {
    "привіт", "добрий день", "доброго дня", "хай", "hello", "hi", "hey"
}


def is_greeting(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in GREETINGS


def greeting_response() -> str:
    return (
        "Вітаю! Я готовий допомогти з питаннями по FAQ. "
        "Напишіть своє запитання."
    )