import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN provided")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")          # по умолчанию gemma
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "chat_history.db")

# (не используется, оставлен для совместимости)
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "промт")

# Temporary directory for images
TEMP_IMAGE_DIR = os.getenv("TEMP_IMAGE_DIR", "temp_images")

# Системный промт (значение по умолчанию – из задания)
DEFAULT_SYSTEM_PROMPT = ( 
    
)
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)