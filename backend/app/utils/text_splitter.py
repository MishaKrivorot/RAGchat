import re

def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    # Очищаємо зайві пробіли
    text = " ".join(text.split())
    if len(text) <= chunk_size:
        return [text]

    # Розбиваємо текст на речення (за крапкою, знаком питання або окликом)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Якщо додавання наступного речення не перевищує ліміт
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            # Зберігаємо поточний чанк
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Починаємо новий чанк з поточного речення
            current_chunk = sentence + " "

    # Додаємо останній чанк, якщо він залишився
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks