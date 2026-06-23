"""RAG по PDF/TXT (логіка з csc_rag/rag_core.py)."""

from __future__ import annotations

import io
import math
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from openai_helper import get_api_key, load_env

API_URL = "https://api.openai.com/v1/chat/completions"
EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
REQUEST_TIMEOUT_SEC = 120

CATALOG_DASK = Path("data/catalogs/dask_catalog.pdf")
CATALOG_GOODWINE = Path("data/catalogs/goodwine_catalog.pdf")


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def rag_settings() -> dict[str, int | float | str]:
    load_env()
    return {
        "chunk_size": _int_env("RAG_CHUNK_SIZE", 900),
        "chunk_overlap": _int_env("RAG_CHUNK_OVERLAP", 150),
        "top_k": _int_env("RAG_TOP_K", 6),
        "temperature": _float_env("RAG_TEMPERATURE", 0.2),
        "embed_batch": _int_env("RAG_EMBED_BATCH", 64),
        "max_tokens": _int_env("OPENAI_MAX_TOKENS", 1000),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    }


def embedding_model() -> str:
    m = (os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small").strip()
    return m or "text-embedding-3-small"


def _embeddings_error_hint(http_status: int, api_message: str) -> str:
    low = api_message.lower()
    hints: list[str] = []
    if http_status in (401, 403) or "permission" in low or "does not have access" in low:
        hints.append(
            "Перевірте API-ключ, проєкт та доступ до Embeddings на platform.openai.com."
        )
    hints.append("Спробуйте OPENAI_EMBEDDING_MODEL=text-embedding-ada-002 у .env.")
    if not hints:
        return ""
    return "\n\nПідказка:\n" + "\n".join(f"• {h}" for h in hints)


def extract_with_pypdf(path: str) -> tuple[str | None, str | None]:
    try:
        reader = PdfReader(path)
    except OSError as e:
        return None, f"Не вдалося відкрити файл: {e}"
    except Exception as e:
        return None, f"Помилка читання PDF (pypdf): {e}"

    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception as e:
            return None, f"Помилка витягу тексту зі сторінки (pypdf): {e}"
        t = t.strip()
        if t:
            parts.append(t)
    full = "\n\n".join(parts).strip()
    return (full if full else None), None


def extract_with_pymupdf(path: str) -> tuple[str | None, str | None]:
    try:
        import fitz
    except ImportError:
        return None, None
    try:
        doc = fitz.open(path)
    except Exception as e:
        return None, f"PyMuPDF: не вдалося відкрити PDF: {e}"
    try:
        parts: list[str] = []
        for page in doc:
            t = (page.get_text() or "").strip()
            if t:
                parts.append(t)
        full = "\n\n".join(parts).strip()
        return (full if full else None), None
    finally:
        doc.close()


def extract_with_ocr(path: str) -> tuple[str | None, str | None]:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError:
        return None, None
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return None, "OCR: Tesseract не знайдено."

    try:
        doc = fitz.open(path)
    except Exception as e:
        return None, f"OCR: не вдалося відкрити PDF: {e}"

    parts: list[str] = []
    try:
        for page in doc:
            plain = (page.get_text() or "").strip()
            if plain:
                parts.append(plain)
                continue
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                try:
                    ocr = pytesseract.image_to_string(img, lang="ukr+eng")
                except Exception:
                    ocr = pytesseract.image_to_string(img, lang="eng")
            except Exception as e:
                return None, f"OCR помилка на сторінці: {e}"
            ocr = ocr.strip()
            if ocr:
                parts.append(ocr)
    finally:
        doc.close()

    full = "\n\n".join(parts).strip()
    return (full if full else None), None


def extract_pdf_text(path: str) -> tuple[str | None, str | None]:
    t1, err_fatal = extract_with_pypdf(path)
    if err_fatal:
        return None, err_fatal

    t2, err_fitz = extract_with_pymupdf(path)
    if err_fitz and not t1 and not t2:
        return None, err_fitz

    candidates = [x for x in (t1, t2) if x]
    if candidates:
        best = max(candidates, key=len)
        if best.strip():
            return best.strip(), None

    t3, err_ocr = extract_with_ocr(path)
    if t3 and t3.strip():
        return t3.strip(), None

    tail = ""
    if err_ocr and "Tesseract" in (err_ocr or ""):
        tail = f" {err_ocr}"
    elif err_ocr:
        tail = f" OCR: {err_ocr}"

    return (
        None,
        "У PDF не знайдено тексту для індексації."
        f"{tail} Для сканів потрібен Tesseract.",
    )


def extract_file_text(path: str | Path) -> tuple[str | None, str | None]:
    file_path = Path(path)
    if file_path.suffix.lower() == ".txt":
        try:
            text = file_path.read_text(encoding="utf-8").strip()
        except OSError as e:
            return None, f"Не вдалося прочитати файл: {e}"
        return (text if text else None), None if text else (None, "Текстовий файл порожній.")
    if file_path.suffix.lower() == ".pdf":
        return extract_pdf_text(str(file_path))
    return None, "Підтримуються лише файли .pdf та .txt"


def chunk_text(
    text: str,
    max_len: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    settings = rag_settings()
    max_len = max_len if max_len is not None else int(settings["chunk_size"])
    overlap = overlap if overlap is not None else int(settings["chunk_overlap"])
    if max_len <= 0:
        return []
    step = max_len - overlap
    if step <= 0:
        step = max_len
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        chunks.append(text[i : i + max_len])
        i += step
    return chunks


def _norm_words(text: str) -> set[str]:
    words = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ0-9_]+", text.lower())
    return {w for w in words if len(w) >= 3}


def _query_hints(query: str) -> set[str]:
    q = query.lower()
    hints: set[str] = set()
    if any(k in q for k in ("колон", "стовпц", "columns", "column")):
        hints.update({"grid", "template", "columns", "grid-template-columns", "repeat", "1fr"})
    if any(k in q for k in ("рядк", "row", "rows")):
        hints.update({"grid", "template", "rows", "grid-template-rows", "repeat", "1fr"})
    if "grid" in q:
        hints.update({"grid-template-columns", "repeat", "gap"})
    if any(k in q for k in ("gap", "відступ", "проміж")):
        hints.update({"gap", "grid", "margin", "padding"})
    if any(k in q for k in ("ціна", "кошт", "грн", "артикул", "товар")):
        hints.update({"грн", "артикул", "ціна", "каталог", "товар"})
    return hints


def keyword_overlap_score(query: str, chunk: str) -> float:
    q = _norm_words(query)
    q.update(_query_hints(query))
    if not q:
        return 0.0
    c = _norm_words(chunk)
    if not c:
        return 0.0
    inter = len(q & c)
    return inter / (len(q) + 0.25 * len(c))


def cosine_sim(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    sa = 0.0
    sb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        sa += x * x
        sb += y * y
    if sa <= 0.0 or sb <= 0.0:
        return 0.0
    return dot / (math.sqrt(sa) * math.sqrt(sb))


def embed_batch(api_key: str, texts: list[str]) -> tuple[list[list[float]] | None, str | None]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"model": embedding_model(), "input": texts}
    try:
        response = requests.post(
            EMBEDDINGS_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as e:
        return None, f"Помилка мережі (embeddings): {e}"

    if response.status_code >= 400:
        try:
            err_json = response.json()
            err_message = err_json.get("error", {}).get("message", response.text)
        except ValueError:
            err_message = response.text
        return None, (
            f"HTTP {response.status_code} (embeddings): {err_message}"
            + _embeddings_error_hint(response.status_code, err_message)
        )

    try:
        data = response.json()
    except ValueError:
        return None, "Відповідь embeddings API не є JSON."

    rows = data.get("data")
    if not isinstance(rows, list) or not rows:
        return None, "Несподіваний формат відповіді embeddings."

    by_index: dict[int, list[float]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        emb = item.get("embedding")
        if isinstance(idx, int) and isinstance(emb, list) and emb:
            by_index[idx] = [float(x) for x in emb]

    ordered: list[list[float]] = []
    for i in range(len(texts)):
        vec = by_index.get(i)
        if vec is None:
            return None, "Неповні ембеддинги в відповіді API."
        ordered.append(vec)
    return ordered, None


def embed_all_chunks(
    api_key: str,
    chunks: list[str],
    on_progress: Callable[[int, int, str], None] | None = None,
) -> tuple[list[list[float]] | None, str | None]:
    settings = rag_settings()
    batch_size = int(settings["embed_batch"])
    all_vecs: list[list[float]] = []
    total = len(chunks)

    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        vecs, err = embed_batch(api_key, batch)
        if err:
            return None, err
        all_vecs.extend(vecs)
        done = min(start + len(batch), total)
        if on_progress:
            on_progress(done, total, f"Ембедінги: {done}/{total}")

    return all_vecs, None


def retrieve_indices(
    query: str,
    query_emb: list[float],
    chunks: list[str],
    chunk_embs: list[list[float]],
    k: int | None = None,
) -> tuple[list[int], str]:
    settings = rag_settings()
    k = min(k or int(settings["top_k"]), len(chunk_embs))
    scored: list[tuple[int, float, float, float]] = []
    for i, emb in enumerate(chunk_embs):
        sem = cosine_sim(query_emb, emb)
        lex = keyword_overlap_score(query, chunks[i])
        lex_boost = 0.35 if lex > 0.09 else 0.0
        total = 0.70 * sem + 0.30 * lex + lex_boost
        scored.append((i, total, sem, lex))
    scored.sort(key=lambda t: t[1], reverse=True)

    head = scored[: max(k + 4, k)]
    idx_set: set[int] = set()
    for i, *_ in head:
        idx_set.add(i)
        if i - 1 >= 0:
            idx_set.add(i - 1)
        if i + 1 < len(chunks):
            idx_set.add(i + 1)

    ordered = sorted(
        idx_set,
        key=lambda idx: next((s[1] for s in scored if s[0] == idx), -1.0),
        reverse=True,
    )
    final = ordered[: max(k + 2, k)]
    debug_rows = []
    for idx in final[:5]:
        row = next((s for s in scored if s[0] == idx), None)
        if row is None:
            continue
        debug_rows.append(f"#{idx} total={row[1]:.3f} sem={row[2]:.3f} lex={row[3]:.3f}")
    return final, "; ".join(debug_rows)


def build_system_prompt(context_blocks: list[str]) -> str:
    joined = "\n\n---\n\n".join(context_blocks)
    return (
        "Ти асистент з відповідями суворо за наведеним КОНТЕКСТОМ з документа.\n"
        "Правила:\n"
        "- Використовуй лише факти та формулювання, які прямо або логічно випливають з КОНТЕКСТУ.\n"
        "- Не додавай знання ззовні документа, не вигадуй деталей.\n"
        "- Якщо в контексті справді немає достатньої інформації — напиши, що в документі цього не знайдено.\n"
        "- Відповідай мовою запитання користувача.\n\n"
        f"КОНТЕКСТ:\n{joined}"
    )


def call_chat_rag(
    api_key: str, messages: list[dict[str, str]]
) -> tuple[str | None, str | None]:
    settings = rag_settings()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": settings["model"],
        "messages": messages,
        "temperature": settings["temperature"],
        "top_p": 1.0,
        "n": 1,
        "max_tokens": settings["max_tokens"],
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as e:
        return None, f"Помилка мережі/API: {e}"

    if response.status_code >= 400:
        try:
            err_json = response.json()
            err_message = err_json.get("error", {}).get("message", response.text)
        except ValueError:
            err_message = response.text
        return None, f"HTTP {response.status_code}: {err_message}"

    try:
        data = response.json()
    except ValueError:
        return None, "Відповідь API не є валідним JSON."

    try:
        reply = (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return None, "Несподіваний формат відповіді API."
    return reply, None


class SimpleRAG:
    """Індекс одного PDF/TXT для RAG-чату (інтерфейс для 3_rag.py)."""

    def __init__(self, source: str | Path | None = None) -> None:
        load_env()
        self.source = str(source) if source else ""
        self.pdf_name = ""
        self.chunks: list[str] = []
        self.chunk_embs: list[list[float]] = []
        self.raw_len = 0
        self.history: list[dict[str, str]] = []
        self.last_debug = ""
        if source:
            self.set_source(source)

    @property
    def documents(self) -> list[dict]:
        return [
            {"source": self.pdf_name, "chunk_id": i, "text": text}
            for i, text in enumerate(self.chunks)
        ]

    def set_source(self, source: str | Path) -> None:
        self.source = str(source)
        self.chunks = []
        self.chunk_embs = []
        self.history = []
        self.last_debug = ""

        raw, err = extract_file_text(source)
        if err:
            raise ValueError(err)
        if not raw:
            self.pdf_name = Path(source).name
            self.raw_len = 0
            return

        self.pdf_name = Path(source).name
        self.raw_len = len(raw)
        self.chunks = chunk_text(raw)

    def index(
        self,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> int:
        if not self.chunks:
            if on_progress:
                on_progress(0, 0, "Немає фрагментів для індексації")
            self.chunk_embs = []
            return 0

        api_key = get_api_key()
        embs, err = embed_all_chunks(api_key, self.chunks, on_progress=on_progress)
        if err:
            raise ValueError(err)
        self.chunk_embs = embs or []
        return len(self.chunks)

    def answer(self, question: str) -> tuple[str, list[dict]]:
        if not self.chunks or not self.chunk_embs:
            reply, _ = call_chat_rag(
                get_api_key(),
                [
                    {
                        "role": "system",
                        "content": "У базі знань немає документів. Попередь про це.",
                    },
                    {"role": "user", "content": question},
                ],
            )
            return reply or "", []

        api_key = get_api_key()
        q_vecs, err = embed_batch(api_key, [question])
        if err:
            raise ValueError(err)
        assert q_vecs is not None

        idxs, debug = retrieve_indices(
            question, q_vecs[0], self.chunks, self.chunk_embs
        )
        self.last_debug = debug
        context_blocks = [self.chunks[i] for i in idxs]
        used_chunks = [
            {"source": self.pdf_name, "chunk_id": i, "text": self.chunks[i]}
            for i in idxs
        ]

        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt(context_blocks)}
        ]
        messages.extend(self.history)
        messages.append({"role": "user", "content": question})

        reply, err2 = call_chat_rag(api_key, messages)
        if err2:
            raise ValueError(err2)

        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": reply or ""})
        return reply or "", used_chunks
