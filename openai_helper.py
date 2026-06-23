"""Спільні функції для роботи з OpenAI API (лише requests, без інших бібліотек)."""

import math
import os
import re
from pathlib import Path

import requests

API_URL = "https://api.openai.com/v1/chat/completions"
EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


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


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Отримує ембедінги для списку текстів одним запитом (швидша індексація RAG)."""
    if not texts:
        return []

    api_key = get_api_key()
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    response = requests.post(
        EMBEDDINGS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    items = sorted(response.json()["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in items]


def get_embedding(text: str) -> list[float]:
    """Отримує вектор ембедінгу для одного тексту (пошук у RAG)."""
    return get_embeddings([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def split_text_into_chunks(text: str, chunk_size: int | None = None) -> list[str]:
    """Розбиває текст на фрагменти за абзацами або за довжиною."""
    if chunk_size is None:
        chunk_size = int(os.environ.get("RAG_CHUNK_SIZE", "2000"))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= chunk_size:
            current = f"{current}\n{paragraph}".strip() if current else paragraph
        else:
            if current:
                chunks.append(current)
            if len(paragraph) <= chunk_size:
                current = paragraph
            else:
                for i in range(0, len(paragraph), chunk_size):
                    chunks.append(paragraph[i : i + chunk_size])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def read_file_text(file_path: Path) -> str:
    """Читає текст з .txt або .pdf файлу."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    return file_path.read_text(encoding="utf-8")


def load_rag_documents(source: str | Path) -> list[dict]:
    """Читає один файл або всі .txt/.pdf з папки."""
    path = Path(source)
    if not path.exists():
        return []

    documents: list[dict] = []
    files: list[Path]

    if path.is_file():
        files = [path]
    else:
        files = sorted(list(path.glob("*.txt")) + list(path.glob("*.pdf")))

    for file_path in files:
        text = read_file_text(file_path)
        if not text.strip():
            continue
        for i, chunk in enumerate(split_text_into_chunks(text)):
            documents.append({"source": file_path.name, "chunk_id": i, "text": chunk})
    return documents


# Готові каталоги в проєкті
CATALOG_DASK = Path("data/catalogs/dask_catalog.pdf")
CATALOG_GOODWINE = Path("data/catalogs/goodwine_catalog.pdf")


class SimpleRAG:
    """Простий RAG: ембедінги + косинусна схожість (без векторних БД)."""

    def __init__(self, source: str | Path | None = None):
        load_env()
        self.top_k = int(os.environ.get("RAG_TOP_K", "3"))
        self.source = str(source) if source else ""
        self.documents: list[dict] = []
        self.embeddings: list[list[float]] = []
        if source:
            self.set_source(source)

    def set_source(self, source: str | Path) -> None:
        """Завантажує документи з файлу або папки (без індексації)."""
        self.source = str(source)
        self.documents = load_rag_documents(source)
        self.embeddings = []

    def index(self) -> int:
        """Будує ембедінги для всіх фрагментів одним пакетом. Повертає кількість фрагментів."""
        texts = [doc["text"] for doc in self.documents]
        self.embeddings = get_embeddings(texts)
        return len(self.documents)

    def search(self, question: str) -> list[dict]:
        """Повертає top_k найближчих фрагментів до питання."""
        if not self.documents or not self.embeddings:
            return []

        query_vec = get_embedding(question)
        scored = [
            (cosine_similarity(query_vec, emb), doc)
            for emb, doc in zip(self.embeddings, self.documents)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[: self.top_k]]

    def answer(self, question: str) -> tuple[str, list[dict]]:
        """Відповідає з урахуванням контексту. Повертає (відповідь, використані фрагменти)."""
        chunks = self.search(question)

        if chunks:
            context = "\n\n---\n\n".join(
                f"[{c['source']}, фрагмент {c['chunk_id']}]\n{c['text']}" for c in chunks
            )
            system = (
                "Відповідай на питання користувача, спираючись лише на наведений контекст. "
                "Якщо в контексті немає відповіді — чесно скажи про це.\n\n"
                f"Контекст:\n{context}"
            )
        else:
            system = (
                "У базі знань немає документів. Відповідай загальними знаннями "
                "і попередь, що контекст з файлів відсутній."
            )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
        return chat_completion(messages), chunks
