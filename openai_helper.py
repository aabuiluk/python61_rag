"""Спільні функції для роботи з OpenAI API (лише requests, без інших бібліотек)."""

import os
from pathlib import Path

import requests

API_URL = "https://api.openai.com/v1/chat/completions"


def load_env(path: str = ".env") -> None:
    """Завантажує змінні з .env у os.environ (без python-dotenv)."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key == "sk-your-api-key-here":
        raise ValueError(
            "Не знайдено OPENAI_API_KEY. Скопіюйте .env.example у .env і вставте ключ."
        )
    return key


def get_chat_settings() -> dict:
    """Повертає всі налаштування чату з .env (зі значеннями за замовчуванням)."""
    return {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
        "max_tokens": int(os.environ.get("OPENAI_MAX_TOKENS", "1000")),
        "top_p": float(os.environ.get("OPENAI_TOP_P", "1.0")),
        "frequency_penalty": float(os.environ.get("OPENAI_FREQUENCY_PENALTY", "0.0")),
        "presence_penalty": float(os.environ.get("OPENAI_PRESENCE_PENALTY", "0.0")),
    }


def build_chat_payload(messages: list[dict], stream: bool = False) -> dict:
    """Формує тіло запиту до Chat Completions API."""
    settings = get_chat_settings()
    payload = {
        "model": settings["model"],
        "messages": messages,
        "temperature": settings["temperature"],
        "max_tokens": settings["max_tokens"],
        "top_p": settings["top_p"],
        "frequency_penalty": settings["frequency_penalty"],
        "presence_penalty": settings["presence_penalty"],
    }
    if stream:
        payload["stream"] = True
    return payload


def chat_completion(messages: list[dict]) -> str:
    """Надсилає запит до ChatGPT і повертає текст відповіді."""
    api_key = get_api_key()
    payload = build_chat_payload(messages)

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
