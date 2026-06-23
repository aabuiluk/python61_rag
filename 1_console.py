"""
1. Простий консольний чат з ChatGPT.

Запуск: python 1_console.py
Команди: exit / quit — вихід; role — змінити роль
"""

from chat_presets import ROLE_PRESETS, ask_role_choice
from openai_helper import chat_completion, load_env


def apply_role(messages: list[dict], prompt: str) -> None:
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = prompt
    else:
        messages.insert(0, {"role": "system", "content": prompt})


def main() -> None:
    load_env()

    print("Консольний чат з ChatGPT")
    role = ask_role_choice()
    messages: list[dict] = []
    apply_role(messages, role["prompt"])

    print("Введіть питання (exit — вихід, role — змінити роль)\n")

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
        if question.lower() == "role":
            print()
            role = ask_role_choice()
            apply_role(messages, role["prompt"])
            print("Роль змінено. Історія діалогу збережена.\n")
            continue

        messages.append({"role": "user", "content": question})

        try:
            answer = chat_completion(messages)
        except Exception as e:
            print(f"Помилка: {e}\n")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": answer})
        print(f"\nChatGPT ({role['name']}): {answer}\n")


if __name__ == "__main__":
    main()
