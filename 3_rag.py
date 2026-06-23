"""
3. Десктопний чат з RAG — відповіді в контексті обраного каталогу.

Запуск: python 3_rag.py

Джерела:
  - ДАСк-Центр (data/catalogs/dask_catalog.pdf)
  - Goodwine (data/catalogs/goodwine_catalog.pdf)
  - Свій файл (.pdf або .txt)
"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

from openai_helper import CATALOG_DASK, CATALOG_GOODWINE, SimpleRAG, load_env

SOURCE_DASK = "dask"
SOURCE_GOODWINE = "goodwine"
SOURCE_CUSTOM = "custom"


class RAGChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з RAG (контекст з каталогу)")
        self.root.geometry("760x600")
        self._sending = False
        self._indexing = False
        self._source_var = tk.StringVar(value=SOURCE_DASK)
        self._custom_path = ""
        self.rag = SimpleRAG()

        source_frame = tk.LabelFrame(root, text="Джерело для RAG", padx=10, pady=8)
        source_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Radiobutton(
            source_frame,
            text="ДАСк-Центр (меблева фурнітура)",
            variable=self._source_var,
            value=SOURCE_DASK,
            command=self.on_source_change,
        ).pack(anchor="w")
        tk.Radiobutton(
            source_frame,
            text="Goodwine (напої та продукти)",
            variable=self._source_var,
            value=SOURCE_GOODWINE,
            command=self.on_source_change,
        ).pack(anchor="w")

        custom_row = tk.Frame(source_frame)
        custom_row.pack(fill=tk.X, anchor="w")
        tk.Radiobutton(
            custom_row,
            text="Свій файл:",
            variable=self._source_var,
            value=SOURCE_CUSTOM,
            command=self.on_source_change,
        ).pack(side=tk.LEFT)
        self._custom_label = tk.Label(custom_row, text="не обрано", fg="gray")
        self._custom_label.pack(side=tk.LEFT, padx=(5, 10))
        tk.Button(custom_row, text="Обрати...", command=self.pick_custom_file).pack(side=tk.LEFT)

        self.status_label = tk.Label(root, text="Оберіть джерело та дочекайтесь індексації...")
        self.status_label.pack(fill=tk.X, padx=10, pady=(8, 0))

        tk.Label(root, text="Діалог:", anchor="w").pack(fill=tk.X, padx=10, pady=(5, 0))
        self.chat_area = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, state=tk.DISABLED, height=18
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(input_frame, text="Ваше питання (Enter — надіслати):", anchor="w").pack(fill=tk.X)

        row = tk.Frame(input_frame)
        row.pack(fill=tk.X, pady=(3, 0))
        self.input_field = tk.Text(row, height=3, wrap=tk.WORD)
        self.input_field.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_field.bind("<Return>", self._on_enter)
        self.input_field.bind("<Shift-Return>", lambda e: None)

        self.send_btn = tk.Button(row, text="Надіслати", width=12, command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=(8, 0), fill=tk.Y)

        self.root.after(100, self.on_source_change)

    def _focus_input(self) -> None:
        self.input_field.focus_set()
        self.input_field.focus_force()

    def _on_enter(self, event: tk.Event) -> str | None:
        if event.state & 0x1:
            return None
        self.send_message()
        return "break"

    def _get_question(self) -> str:
        return self.input_field.get("1.0", tk.END).strip()

    def _clear_input(self) -> None:
        self.input_field.delete("1.0", tk.END)

    def _set_busy(self, busy: bool) -> None:
        self._sending = busy
        state = tk.DISABLED if busy or self._indexing else tk.NORMAL
        self.input_field.config(state=state)
        self.send_btn.config(state=state)
        if not busy and not self._indexing:
            self._focus_input()

    def append_text(self, author: str, text: str) -> None:
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{author}: {text}\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def get_selected_path(self) -> Path | None:
        source = self._source_var.get()
        if source == SOURCE_DASK:
            return CATALOG_DASK
        if source == SOURCE_GOODWINE:
            return CATALOG_GOODWINE
        if source == SOURCE_CUSTOM:
            if not self._custom_path:
                return None
            return Path(self._custom_path)
        return None

    def pick_custom_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл для RAG",
            filetypes=[
                ("Підтримувані", "*.pdf *.txt"),
                ("PDF", "*.pdf"),
                ("Текст", "*.txt"),
                ("Усі файли", "*.*"),
            ],
        )
        if not path:
            return
        self._custom_path = path
        self._custom_label.config(text=Path(path).name, fg="black")
        self._source_var.set(SOURCE_CUSTOM)
        self.on_source_change()

    def on_source_change(self) -> None:
        if self._indexing:
            return

        path = self.get_selected_path()
        if path is None:
            self.status_label.config(text="Оберіть свій файл (.pdf або .txt)")
            return
        if not path.exists():
            self.status_label.config(text=f"Файл не знайдено: {path}")
            messagebox.showerror(
                "Файл не знайдено",
                f"Каталог відсутній:\n{path}\n\n"
                "Запустіть: python generate_catalogs.py",
            )
            return

        self._indexing = True
        self._set_busy(True)
        self.status_label.config(text=f"Індексація: {path.name}...")
        self.append_text("Система", f"Завантажую {path.name}...\n")

        def worker() -> None:
            try:
                self.rag.set_source(path)
                count = self.rag.index()
                self.root.after(0, lambda: self._on_indexed(path.name, count, None))
            except Exception as e:
                self.root.after(0, lambda: self._on_indexed(path.name, 0, e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_indexed(self, name: str, count: int, error: Exception | None) -> None:
        self._indexing = False
        self._set_busy(False)
        if error:
            self.status_label.config(text="Помилка індексації")
            messagebox.showerror("Помилка", str(error))
            return
        if count == 0:
            self.status_label.config(text=f"{name}: порожній або нечитабельний файл")
            self.append_text("Система", "Не вдалося отримати текст з файлу.\n")
            return
        self.status_label.config(text=f"{name}: проіндексовано {count} фрагментів")
        self.append_text("Система", f"Готово! {count} фрагментів. Задайте питання.\n")
        self._focus_input()

    def send_message(self) -> None:
        if self._sending or self._indexing:
            return
        if not self.rag.documents:
            messagebox.showwarning("Увага", "Спочатку оберіть і проіндексуйте джерело.")
            return

        question = self._get_question()
        if not question:
            return

        self._clear_input()
        self.append_text("Ви", question)
        self._set_busy(True)
        self.status_label.config(text="Очікую відповідь...")

        def worker() -> None:
            try:
                answer, chunks = self.rag.answer(question)
                self.root.after(0, lambda: self._on_answer(answer, chunks, None))
            except Exception as e:
                self.root.after(0, lambda: self._on_answer("", [], e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_answer(
        self, answer: str, chunks: list[dict], error: Exception | None
    ) -> None:
        self._set_busy(False)
        if error:
            self.status_label.config(text="Помилка запиту")
            messagebox.showerror("Помилка", str(error))
            return

        self.append_text("ChatGPT", answer)
        if chunks:
            sources = ", ".join(f"{c['source']}#{c['chunk_id']}" for c in chunks)
            self.append_text("Контекст", f"Використано: {sources}\n")
        self.status_label.config(text=f"Готово. Фрагментів у базі: {len(self.rag.documents)}")


def main() -> None:
    load_env()
    root = tk.Tk()
    RAGChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
