"""
3. Десктопний чат з RAG — відповіді в контексті вашого файлу (.pdf або .txt).

Запуск: python 3_rag.py
"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from openai_helper import load_env
from rag_core import SimpleRAG


class RAGChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з RAG (ваш файл)")
        self.root.geometry("760x620")
        self._sending = False
        self._indexing = False
        self._index_job_id = 0
        self._indexed_source = ""
        self._file_path = ""
        self.rag = SimpleRAG()

        source_frame = tk.LabelFrame(root, text="Ваш документ для RAG", padx=10, pady=8)
        source_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        file_row = tk.Frame(source_frame)
        file_row.pack(fill=tk.X)
        tk.Label(file_row, text="Файл:").pack(side=tk.LEFT)
        self._file_label = tk.Label(file_row, text="не обрано", fg="gray")
        self._file_label.pack(side=tk.LEFT, padx=(5, 10))
        tk.Button(file_row, text="Обрати...", command=self.pick_file).pack(side=tk.LEFT)

        action_row = tk.Frame(source_frame)
        action_row.pack(fill=tk.X, pady=(8, 0))
        self.index_btn = tk.Button(
            action_row,
            text="Проіндексувати",
            width=16,
            command=self.start_indexing,
        )
        self.index_btn.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            root, text="Оберіть файл (.pdf або .txt) і натисніть «Проіндексувати»"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=(8, 0))

        progress_frame = tk.Frame(root)
        progress_frame.pack(fill=tk.X, padx=10, pady=(4, 0))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, maximum=100, variable=self.progress_var, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X)
        self.progress_label = tk.Label(progress_frame, text="", fg="gray")
        self.progress_label.pack(anchor="w", pady=(2, 0))

        tk.Label(root, text="Діалог (можна виділяти і копіювати):", anchor="w").pack(
            fill=tk.X, padx=10, pady=(5, 0)
        )
        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=18)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.chat_area.bind("<KeyPress>", self._chat_readonly_key)

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

    def _chat_readonly_key(self, event: tk.Event) -> str | None:
        """Дозволяє навігацію та копіювання, блокує редагування."""
        key = event.keysym
        if key in {
            "Left", "Right", "Up", "Down", "Home", "End",
            "Prior", "Next", "Shift_L", "Shift_R",
            "Control_L", "Control_R", "Meta_L", "Meta_R", "Alt_L", "Alt_R",
        }:
            return None
        if key.lower() in {"c", "a", "insert"}:
            return None
        if event.char and event.char.isprintable():
            return "break"
        if key in {"BackSpace", "Delete", "Return", "space", "Tab"}:
            return "break"
        return None

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

    def _reset_progress(self) -> None:
        self.progress_var.set(0)
        self.progress_label.config(text="")

    def _set_progress(self, job_id: int, value: float, maximum: float, text: str) -> None:
        if job_id != self._index_job_id:
            return
        self.progress_bar.config(maximum=max(maximum, 1))
        self.progress_var.set(value)
        self.progress_label.config(text=text)

    def _cancel_indexing(self, reason: str) -> None:
        if not self._indexing:
            return
        self._index_job_id += 1
        self._indexing = False
        self.index_btn.config(state=tk.NORMAL)
        self._set_busy(False)
        self._reset_progress()
        self.append_text("Система", f"{reason}\n")

    def append_text(self, author: str, text: str) -> None:
        self.chat_area.insert(tk.END, f"{author}: {text}\n")
        self.chat_area.see(tk.END)

    def get_selected_path(self) -> Path | None:
        if not self._file_path:
            return None
        return Path(self._file_path)

    def pick_file(self) -> None:
        if self._indexing:
            self._cancel_indexing("Індексацію скасовано: обрано інший файл.")

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

        self._file_path = path
        self._file_label.config(text=Path(path).name, fg="black")
        self._update_file_status()

    def _update_file_status(self) -> None:
        path = self.get_selected_path()
        if path is None:
            self.status_label.config(
                text="Оберіть файл (.pdf або .txt) і натисніть «Проіндексувати»"
            )
            return
        if not path.exists():
            self.status_label.config(text=f"Файл не знайдено: {path.name}")
            return
        if str(path) == self._indexed_source:
            self.status_label.config(
                text=f"{path.name} уже проіндексовано. Можна ставити питання."
            )
        else:
            self.status_label.config(
                text=f"Обрано: {path.name}. Натисніть «Проіндексувати»"
            )

    def start_indexing(self) -> None:
        path = self.get_selected_path()
        if path is None:
            messagebox.showwarning("Увага", "Спочатку оберіть файл.")
            return
        if not path.exists():
            messagebox.showerror("Файл не знайдено", f"Файл відсутній:\n{path}")
            return

        if self._indexing:
            self._cancel_indexing("Попередню індексацію перервано.")

        self._indexing = True
        self._index_job_id += 1
        job_id = self._index_job_id

        self.index_btn.config(state=tk.DISABLED)
        self._set_busy(True)
        self._reset_progress()
        self._set_progress(job_id, 0, 100, "Початок...")
        self.status_label.config(text=f"Індексація: {path.name}...")
        self.append_text("Система", f"Індексую {path.name}...\n")

        def report(job: int, value: float, maximum: float, text: str) -> None:
            self.root.after(0, lambda: self._set_progress(job, value, maximum, text))

        def worker() -> None:
            try:
                report(job_id, 5, 100, "Читаю файл...")
                rag = SimpleRAG()
                try:
                    rag.set_source(path)
                except ValueError as e:
                    self.root.after(
                        0, lambda: self._on_indexed(job_id, path, None, 0, e)
                    )
                    return
                chunk_count = len(rag.documents)

                if chunk_count == 0:
                    self.root.after(
                        0, lambda: self._on_indexed(job_id, path, rag, 0, None)
                    )
                    return

                report(job_id, 15, 100, f"Знайдено фрагментів: {chunk_count}")

                def on_embed_progress(done: int, total: int, message: str) -> None:
                    value = 15 + (80 * done / total) if total else 15
                    report(job_id, value, 100, message)

                try:
                    count = rag.index(on_progress=on_embed_progress)
                except ValueError as e:
                    self.root.after(
                        0, lambda: self._on_indexed(job_id, path, None, 0, e)
                    )
                    return
                report(job_id, 100, 100, "Завершено")
                self.root.after(
                    0, lambda: self._on_indexed(job_id, path, rag, count, None)
                )
            except Exception as e:
                self.root.after(
                    0, lambda: self._on_indexed(job_id, path, None, 0, e)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_indexed(
        self,
        job_id: int,
        path: Path,
        rag: SimpleRAG | None,
        count: int,
        error: Exception | None,
    ) -> None:
        if job_id != self._index_job_id:
            return

        self._indexing = False
        self.index_btn.config(state=tk.NORMAL)
        self._set_busy(False)

        if error:
            self._reset_progress()
            self.status_label.config(text="Помилка індексації")
            messagebox.showerror("Помилка", str(error))
            return

        if count == 0 or rag is None:
            self._reset_progress()
            self.status_label.config(text=f"{path.name}: порожній або нечитабельний файл")
            self.append_text("Система", "Не вдалося отримати текст з файлу.\n")
            return

        self.rag = rag
        self._indexed_source = str(path)
        self._set_progress(job_id, 100, 100, f"Готово: {count} фрагментів")
        self.status_label.config(text=f"{path.name}: проіндексовано {count} фрагментів")
        self.append_text("Система", f"Готово! {count} фрагментів. Задайте питання.\n")
        self._focus_input()

    def send_message(self) -> None:
        if self._sending or self._indexing:
            return
        if not self.rag.documents:
            messagebox.showwarning(
                "Увага", "Спочатку оберіть файл і натисніть «Проіндексувати»."
            )
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
        if self.rag.last_debug:
            self.append_text("Пошук", f"{self.rag.last_debug}\n")
        self.status_label.config(text=f"Готово. Фрагментів у базі: {len(self.rag.documents)}")


def main() -> None:
    load_env()
    root = tk.Tk()
    RAGChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
