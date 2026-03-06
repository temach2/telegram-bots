import aiosqlite
from datetime import datetime

async def init_db(db_path: str):
    """Инициализация БД, создание таблицы messages, если её нет."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,   -- 0 для сообщений бота
                text TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_data TEXT
            )
        ''')
        await db.commit()

async def save_message(db_path: str, chat_id: int, user_id: int, text: str, date=None):
    """
    Сохраняет сообщение в БД.
    Для сообщений бота передавать user_id = 0.
    """
    if date is None:
        date = datetime.utcnow().isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO messages (chat_id, user_id, text, date) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, text, date)
        )
        await db.commit()

async def get_last_messages(db_path: str, chat_id: int, limit: int = 10):
    """
    Возвращает последние 'limit' сообщений из указанного чата,
    отсортированных по времени (от старых к новым).
    Каждое сообщение – кортеж (user_id, text).
    """
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT user_id, text FROM messages WHERE chat_id = ? ORDER BY date DESC LIMIT ?",
            (chat_id, limit)
        )
        rows = await cursor.fetchall()
        # Возвращаем в хронологическом порядке (от старых к новым)
        return list(reversed(rows))