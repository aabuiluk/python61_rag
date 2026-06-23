"""
2. Простий десктопний чат з ChatGPT (tkinter).

Запуск: python 2_desktop.py
"""

import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from chat_presets import ROLE_PRESETS
from openai_helper import chat_completion, load_env


class ChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з ChatGPT")
        self.root.geometry("600x580")
        self._sending = False
        self._role_var = tk.StringVar(value=ROLE_PRESETS[0]["id"])
        self.messages: list[dict] = []
        self._apply_role(ROLE_PRESETS[0]["prompt"])

        role_frame = tk.LabelFrame(root, text="Роль помічника", padx=10, pady=8)
        role_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        for preset in ROLE_PRESETS:
            tk.Radiobutton(
                role_frame,
                text=preset["name"],
                variable=self._role_var,
                value=preset["id"],
                command=self.on_role_change,
            ).pack(anchor="w")

        tk.Label(root, text="Діалог (можна виділяти і копіювати):", anchor="w").pack(
            fill=tk.X, padx=10, pady=(10, 0)
        )

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=18)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.chat_area.bind("<KeyPress>", self._chat_readonly_key)

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

        role_name = ROLE_PRESETS[0]["name"]
        self.append_text("Система", f"Вітаю! Роль: {role_name}. Задайте питання.\n")
        self.root.after(100, self._focus_input)

    def _current_role(self) -> dict:
        role_id = self._role_var.get()
        for preset in ROLE_PRESETS:
            if preset["id"] == role_id:
                return preset
        return ROLE_PRESETS[0]

    def _apply_role(self, prompt: str) -> None:
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = prompt
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    def on_role_change(self) -> None:
        role = self._current_role()
        self._apply_role(role["prompt"])
        self.append_text("Система", f"Роль змінено на: {role['name']}\n")

    def _chat_readonly_key(self, event: tk.Event) -> str | None:
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
        state = tk.DISABLED if busy else tk.NORMAL
        self.input_field.config(state=state)
        self.send_btn.config(state=state)
        self.status_label.config(text="Очікую відповідь..." if busy else "")
        if not busy:
            self._focus_input()

    def append_text(self, author: str, text: str) -> None:
        self.chat_area.insert(tk.END, f"{author}: {text}\n")
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
        role_name = self._current_role()["name"]
        self.messages.append({"role": "assistant", "content": answer})
        self.append_text(f"ChatGPT ({role_name})", answer)
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
