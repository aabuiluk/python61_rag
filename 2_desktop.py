"""
2. Простий десктопний чат з ChatGPT (tkinter).

Запуск: python 2_desktop.py
"""

import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from openai_helper import chat_completion, load_env

SYSTEM_PROMPT = "Ти корисний помічник. Відповідай українською, коротко і зрозуміло."


class ChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з ChatGPT")
        self.root.geometry("600x520")
        self._sending = False

        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        tk.Label(root, text="Діалог:", anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))

        self.chat_area = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, state=tk.DISABLED, height=20
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(input_frame, text="Ваше питання (Enter — надіслати):", anchor="w").pack(
            fill=tk.X
        )

        row = tk.Frame(input_frame)
        row.pack(fill=tk.X, pady=(3, 0))

        self.input_field = tk.Text(row, height=3, wrap=tk.WORD)
        self.input_field.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_field.bind("<Return>", self._on_enter)
        self.input_field.bind("<Shift-Return>", lambda e: None)

        self.send_btn = tk.Button(row, text="Надіслати", width=12, command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=(8, 0), fill=tk.Y)

        self.status_label = tk.Label(input_frame, text="", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(3, 0))

        self.append_text("Система", "Вітаю! Введіть питання у поле внизу.\n")
        self.root.after(100, self._focus_input)

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
        state = tk.DISABLED if busy else tk.NORMAL
        self.input_field.config(state=state)
        self.send_btn.config(state=state)
        self.status_label.config(text="Очікую відповідь..." if busy else "")
        if not busy:
            self._focus_input()

    def append_text(self, author: str, text: str) -> None:
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{author}: {text}\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def send_message(self) -> None:
        if self._sending:
            return

        question = self._get_question()
        if not question:
            return

        self._clear_input()
        self.append_text("Ви", question)
        self.messages.append({"role": "user", "content": question})
        self._set_busy(True)

        def worker() -> None:
            try:
                answer = chat_completion(self.messages)
                self.root.after(0, lambda: self._on_success(answer))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, answer: str) -> None:
        self.messages.append({"role": "assistant", "content": answer})
        self.append_text("ChatGPT", answer)
        self._set_busy(False)

    def _on_error(self, error: Exception) -> None:
        self.messages.pop()
        self._set_busy(False)
        messagebox.showerror("Помилка", str(error))


def main() -> None:
    load_env()
    root = tk.Tk()
    ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
