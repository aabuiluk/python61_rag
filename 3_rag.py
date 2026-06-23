"""
3. Десктопний чат з RAG — відповіді в контексті текстових файлів.

Запуск: python 3_rag.py
Покладіть .txt файли в папку data/ (див. data/knowledge.txt як приклад).
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox

from openai_helper import SimpleRAG, load_env


class RAGChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з RAG (контекст з файлів)")
        self.root.geometry("700x550")

        status_frame = tk.Frame(root)
        status_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        self.status_label = tk.Label(status_frame, text="Індексація документів...")
        self.status_label.pack(side=tk.LEFT)

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.input_field = tk.Entry(input_frame)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_field.bind("<Return>", lambda e: self.send_message())

        send_btn = tk.Button(input_frame, text="Надіслати", command=self.send_message)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.rag = SimpleRAG()
        self.root.after(100, self.index_documents)

    def index_documents(self) -> None:
        try:
            count = self.rag.index()
            if count == 0:
                self.status_label.config(
                    text=f"Папка '{self.rag.data_dir}' порожня — додайте .txt файли"
                )
                self.append_text(
                    "Система",
                    "Немає документів для RAG. Додайте .txt у папку data/ і перезапустіть.\n",
                )
            else:
                self.status_label.config(text=f"Проіндексовано фрагментів: {count}")
                self.append_text(
                    "Система",
                    f"Готово! Завантажено {count} фрагментів. Задайте питання.\n",
                )
        except Exception as e:
            self.status_label.config(text="Помилка індексації")
            messagebox.showerror("Помилка", str(e))

    def append_text(self, author: str, text: str) -> None:
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{author}: {text}\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def send_message(self) -> None:
        question = self.input_field.get().strip()
        if not question:
            return

        self.input_field.delete(0, tk.END)
        self.append_text("Ви", question)

        self.root.config(cursor="watch")
        self.root.update()

        try:
            answer, chunks = self.rag.answer(question)
            self.append_text("ChatGPT", answer)

            if chunks:
                sources = ", ".join(f"{c['source']}#{c['chunk_id']}" for c in chunks)
                self.append_text("Контекст", f"Використано: {sources}\n")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
        finally:
            self.root.config(cursor="")


def main() -> None:
    load_env()
    root = tk.Tk()
    RAGChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
