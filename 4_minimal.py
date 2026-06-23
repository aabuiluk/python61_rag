"""
4. Мінімальний консольний чат.

Запуск: python 4_minimal.py
Змініть SYSTEM_PROMPT і SETTINGS нижче — і перезапустіть програму.
Вихід: exit або порожній рядок
"""

from openai_helper import chat_completion, load_env

# --- змінюйте тут вручну ---
SYSTEM_PROMPT = "Ти корисний помічник. Відповідай українською, коротко."

SETTINGS = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 500,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}
# -------------------------


def main() -> None:
    load_env()  # лише OPENAI_API_KEY з .env
    print("Питання до ChatGPT (exit — вихід)")
    print(f"Модель: {SETTINGS['model']}, temperature: {SETTINGS['temperature']}\n")

    system = SYSTEM_PROMPT.strip()

    while True:
        question = input("Ви: ").strip()
        if not question or question.lower() in ("exit", "quit"):
            break

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": question})

        try:
            answer = chat_completion(messages, settings_override=SETTINGS)
            print(f"\nChatGPT: {answer}\n")
        except Exception as e:
            print(f"Помилка: {e}\n")


if __name__ == "__main__":
    main()
