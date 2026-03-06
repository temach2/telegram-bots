import aiohttp
import base64
import asyncio
from aiohttp import ClientTimeout

async def generate_with_image(prompt: str, image_path: str, model: str, base_url: str, system: str = None) -> str:
    """
    Отправляет изображение и промт в Ollama vision model.
    Поддерживает системный промт.
    """
    url = f"{base_url.rstrip('/')}/api/generate"
    
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64_image],
        "stream": False
    }
    if system:
        payload["system"] = system
    
    timeout = ClientTimeout(total=300, connect=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                else:
                    error_text = await resp.text()
                    raise Exception(f"Ollama vision error {resp.status}: {error_text}")
        except asyncio.TimeoutError:
            raise Exception("Запрос к Ollama (vision) превысил время ожидания (5 минут).")
        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка подключения к Ollama: {e}")