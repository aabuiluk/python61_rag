"""
2. Простий десктопний чат з ChatGPT (tkinter).

Запуск: python 2_desktop.py
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox

from openai_helper import chat_completion, load_env

SYSTEM_PROMPT = "Ти корисний помічник. Відповідай українською, коротко і зрозуміло."


class ChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Чат з ChatGPT")
        self.root.geometry("600x500")

        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.input_field = tk.Entry(input_frame)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_field.bind("<Return>", lambda e: self.send_message())

        send_btn = tk.Button(input_frame, text="Надіслати", command=self.send_message)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.append_text("Система", "Вітаю! Задайте питання.\n")

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
        self.messages.append({"role": "user", "content": question})

        self.root.config(cursor="watch")
        self.root.update()

        try:
            answer = chat_completion(self.messages)
            self.messages.append({"role": "assistant", "content": answer})
            self.append_text("ChatGPT", answer)
        except Exception as e:
            self.messages.pop()
            messagebox.showerror("Помилка", str(e))
        finally:
            self.root.config(cursor="")


def main() -> None:
    load_env()
    root = tk.Tk()
    ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
