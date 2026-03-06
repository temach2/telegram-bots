import os
from pathlib import Path
from PIL import Image

def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Разбивает длинное сообщение на части, не превышающие max_length."""
    if len(text) <= max_length:
        return [text]
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        split_index = text.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        parts.append(text[:split_index])
        text = text[split_index:].lstrip()
    return parts

async def download_telegram_file(file, temp_dir: str) -> str:
    """Скачивает файл из Telegram во временную папку."""
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{file.file_id}.jpg")
    await file.download_to_drive(file_path)
    return file_path

def resize_image_if_needed(image_path: str, max_size: int = 480) -> str:
    """
    Уменьшает изображение, если его большая сторона превышает max_size.
    Возвращает путь к новому файлу (или исходный, если уменьшение не требовалось).
    """
    img = Image.open(image_path)
    if max(img.size) <= max_size:
        return image_path
    
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    base, ext = os.path.splitext(image_path)
    resized_path = f"{base}_resized{ext}"
    img.save(resized_path, quality=30)
    return resized_path

def cleanup_temp_file(file_path: str):
    """Удаляет временный файл."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")

def format_history_for_summary(messages):
    """
    Форматирует список сообщений (user_id, text) для подачи в модель.
    Возвращает строку вида:
    "Пользователь 12345: Привет!
     Пользователь 67890: Как дела?"
    """
    lines = []
    for user_id, text in messages:
        # Если это бот (user_id == 0), помечаем как "Бот"
        if user_id == 0:
            sender = "Бот"
        else:
            sender = f"Пользователь {user_id}"
        lines.append(f"{sender}: {text}")
    return "\n".join(lines)