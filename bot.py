import logging
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes
import config
import database
import ollama_client
import ollama_vision_client
import utils

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_USER_ID = 0  # условный ID для сообщений бота в БД

async def post_init(app: Application):
    await database.init_db(config.DATABASE_PATH)
    logger.info("Database initialized")

async def save_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет входящее сообщение пользователя в БД (текст или подпись к фото)."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text or update.message.caption
    if not text:
        return
    date = update.message.date.isoformat()
    try:
        await database.save_message(config.DATABASE_PATH, chat_id, user_id, text, date)
    except Exception as e:
        logger.error(f"Failed to save message: {e}")

async def save_bot_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет ответ бота в БД с user_id = 0."""
    try:
        await database.save_message(config.DATABASE_PATH, chat_id, BOT_USER_ID, text)
    except Exception as e:
        logger.error(f"Failed to save bot message: {e}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает любое текстовое сообщение (не команду и не от бота).
    Сохраняет сообщение пользователя, генерирует ответ с системным промтом,
    отправляет ответ в чат и сохраняет его.
    """
    # Игнорируем сообщения от самого бота
    if update.effective_user.id == context.bot.id:
        return

    # Сохраняем сообщение пользователя
    await save_user_message(update, context)

    # Получаем текст запроса
    query = update.message.text
    if not query:
        return

    await update.message.chat.send_action(action="typing")

    try:
        logger.info(f"Processing text: {query[:50]}...")
        start_time = time.time()
        response = await ollama_client.generate(
            prompt=query,
            model=config.OLLAMA_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            system=config.SYSTEM_PROMPT  # передаём системный промт
        )
        elapsed = time.time() - start_time

        if not response:
            response = "🤔 Не могу ничего придумать. Попробуй ещё раз!"

        # Отправляем ответ в чат (не как ответ на конкретное сообщение)
        await update.message.chat.send_message(
            f"⏱ {elapsed:.2f} с\n\n{response}"
        )
        # Сохраняем ответ бота
        await save_bot_message(update.effective_chat.id, response, context)

    except Exception as e:
        logger.exception("Error while generating response")
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения с фото (если есть подпись).
    Сохраняет подпись, генерирует ответ с vision-моделью, отправляет и сохраняет.
    """
    if update.effective_user.id == context.bot.id:
        return

    # Сохраняем подпись пользователя
    await save_user_message(update, context)

    caption = update.message.caption
    if not caption:
        return

    logger.info("Processing image with vision model...")

    photo = update.message.photo[-1]
    await update.message.chat.send_action(action="typing")

    temp_file_path = None
    resized_path = None
    try:
        file = await context.bot.get_file(photo.file_id)
        temp_file_path = await utils.download_telegram_file(file, config.TEMP_IMAGE_DIR)
        resized_path = utils.resize_image_if_needed(temp_file_path, max_size=1024)
        logger.info(f"Image ready: {resized_path}")

        start_time = time.time()
        response = await ollama_vision_client.generate_with_image(
            prompt=caption,
            image_path=resized_path,
            model=config.OLLAMA_VISION_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            system=config.SYSTEM_PROMPT  # тот же системный промт (можно адаптировать при желании)
        )
        elapsed = time.time() - start_time

        if not response:
            response = "🖼 Не удалось распознать изображение."

        await update.message.chat.send_message(
            f"🖼 Анализ изображения\n⏱ {elapsed:.2f} с\n\n{response}"
        )
        await save_bot_message(update.effective_chat.id, response, context)

    except Exception as e:
        logger.exception("Error processing image")
        await update.message.reply_text(f"Ошибка при обработке изображения: {e}")
    finally:
        if temp_file_path:
            utils.cleanup_temp_file(temp_file_path)
        if resized_path and resized_path != temp_file_path:
            utils.cleanup_temp_file(resized_path)

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /summary.
    Получает последние 50 сообщений из БД, формирует промт для сводки,
    отправляет запрос модели и выводит результат.
    """
    if update.effective_user.id == context.bot.id:
        return

    chat_id = update.effective_chat.id

    # Сообщим, что начали
    await update.message.chat.send_action(action="typing")
    processing_msg = await update.message.reply_text("🔍 Собираю историю сообщений...")

    try:
        # Получаем последние 50 сообщений из БД
        messages = await database.get_last_messages(config.DATABASE_PATH, chat_id, limit=10)
        if not messages:
            await processing_msg.edit_text("В этом чате пока нет сообщений.")
            return

        # Форматируем историю
        history_text = utils.format_history_for_summary(messages)
        prompt = f"Сделай краткую сводку (саммари) последних сообщений в чате. Вот они:\n\n{history_text}"

        # Генерируем ответ
        response = await ollama_client.generate(
            prompt=prompt,
            model=config.OLLAMA_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            system="Ты — ассистент, который делает краткие саммари диалогов.\n-\n-Проанализируй последние 10–20 сообщений в чате. Выдели основные темы, ключевые вопросы, принятые решения и важные выводы.\n- Напиши итог строго в 3–5 предложений, сухим фактологическим языком, без лишних слов, оценок и эмодзи. Только суть."  # используем тот же дружелюбный стиль
        )

        if not response:
            response = "Не удалось составить сводку."

        # Удаляем временное сообщение
        await processing_msg.delete()

        # Отправляем сводку
        await update.message.chat.send_message(f"📋 *Сводка последних сообщений:*\n\n{response}", parse_mode="Markdown")
        # Сохраняем ответ бота
        await save_bot_message(chat_id, response, context)

    except Exception as e:
        logger.exception("Error in summary command")
        await processing_msg.edit_text(f"Ошибка при создании сводки: {e}")

def main():
    app = Application.builder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()

    # Команда /summary
    app.add_handler(CommandHandler("summary", summary_command))

    # Обработчик текстовых сообщений (не команды) – должен быть после CommandHandler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED,
        handle_text_message
    ))

    # Обработчик фото с подписью
    app.add_handler(MessageHandler(
        filters.PHOTO & ~filters.COMMAND & ~filters.UpdateType.EDITED,
        handle_photo_message
    ))

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()