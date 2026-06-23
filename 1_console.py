"""
1. Простий консольний чат з ChatGPT.

Запуск: python 1_console.py
Команди: exit або quit — вихід
"""

from openai_helper import chat_completion, load_env

SYSTEM_PROMPT = "Ти корисний помічник. Відповідай українською, коротко і зрозуміло."


def main() -> None:
    load_env()

    print("Консольний чат з ChatGPT")
    print("Введіть питання (exit або quit — вихід)\n")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            question = input("Ви: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо побачення!")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "вихід"):
            print("До побачення!")
            break

        messages.append({"role": "user", "content": question})

        try:
            answer = chat_completion(messages)
        except Exception as e:
            print(f"Помилка: {e}\n")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": answer})
        print(f"\nChatGPT: {answer}\n")


if __name__ == "__main__":
    main()
