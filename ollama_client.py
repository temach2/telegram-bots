import aiohttp
import asyncio
from aiohttp import ClientTimeout

async def generate(prompt: str, model: str, base_url: str, system: str = None) -> str:
    """
    Отправляет запрос к Ollama generate.
    Если передан system, добавляет его в payload.
    """
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
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
                    raise Exception(f"Ollama error {resp.status}: {error_text}")
        except asyncio.TimeoutError:
            raise Exception("Запрос к Ollama превысил время ожидания (5 минут).")
        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка подключения к Ollama: {e}")