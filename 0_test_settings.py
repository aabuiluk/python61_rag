"""
0. Тестова програма: показує всі налаштування, які відправляються до ChatGPT.

Запуск: python 0_test_settings.py
"""

import json

from openai_helper import build_chat_payload, get_chat_settings, load_env

# Пояснення кожного параметра українською
PARAM_HELP = {
    "model": (
        "Назва моделі OpenAI. Визначає якість, швидкість і вартість відповіді. "
        "Наприклад: gpt-4o-mini, gpt-4o."
    ),
    "messages": (
        "Список повідомлень діалогу. Кожне має role (system / user / assistant) "
        "і content (текст). Саме це модель читає як контекст розмови."
    ),
    "temperature": (
        "«Креативність» від 0.0 до 2.0. 0 — передбачувані відповіді, "
        "вище 1 — більш випадкові та різноманітні."
    ),
    "max_tokens": (
        "Максимальна довжина відповіді в токенах (приблизно 1 токен ≈ 4 символи українською). "
        "Обмежує, скільки тексту модель може згенерувати."
    ),
    "top_p": (
        "Nucleus sampling: модель обирає слова з найімовірніших, поки їх сума ймовірності "
        "не досягне top_p. 1.0 — без обрізання, менші значення — строгіший відбір."
    ),
    "frequency_penalty": (
        "Штраф за повторення тих самих слів (-2.0 … 2.0). Позитивне значення "
        "зменшує повтори у відповіді."
    ),
    "presence_penalty": (
        "Штраф за повторення тем (-2.0 … 2.0). Схиляє модель говорити про нові теми, "
        "а не зациклюватися на вже згаданому."
    ),
    "stream": (
        "Якщо true — відповідь приходить частинами (потоково). "
        "У наших програмах завжди false (повна відповідь одразу)."
    ),
}

MESSAGE_ROLE_HELP = {
    "system": "Інструкції для моделі: стиль, правила, контекст (у RAG — фрагменти документів).",
    "user": "Повідомлення від користувача — питання або команда.",
    "assistant": "Попередні відповіді моделі. Потрібні для багатокрокового діалогу.",
}


def print_separator(title: str = "") -> None:
    print("\n" + "=" * 60)
    if title:
        print(title)
        print("=" * 60)


def main() -> None:
    load_env()

    print_separator("НАЛАШТУВАННЯ З .env")
    settings = get_chat_settings()
    for key, value in settings.items():
        print(f"  {key}: {value}")

    # Приклад повідомлень, як у реальному чаті
    example_messages = [
        {"role": "system", "content": "Ти корисний помічник. Відповідай українською."},
        {"role": "user", "content": "Що таке Python?"},
    ]

    payload = build_chat_payload(example_messages)

    print_separator("ТІЛО ЗАПИТУ (JSON), ЯКЕ ВІДПРАВЛЯЄТЬСЯ НА API")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    print_separator("ПОЯСНЕННЯ КОЖНОГО ПАРАМЕТРА")
    for key, value in payload.items():
        help_text = PARAM_HELP.get(key, "Додатковий параметр API.")
        print(f"\n▸ {key}")
        print(f"  Значення: {json.dumps(value, ensure_ascii=False) if not isinstance(value, list) else '(див. нижче)'}")
        print(f"  Пояснення: {help_text}")

    print_separator("СТРУКТУРА messages (приклад діалогу)")
    for i, msg in enumerate(example_messages, 1):
        role = msg["role"]
        print(f"\n  Повідомлення {i}:")
        print(f"    role: {role} — {MESSAGE_ROLE_HELP.get(role, '')}")
        print(f"    content: {msg['content']}")

    print_separator("HTTP-ЗАГОЛОВКИ ЗАПИТУ")
    print("  Authorization: Bearer <OPENAI_API_KEY>")
    print("    Ключ API з .env. Ніколи не публікуйте його в коді чи git.")
    print("  Content-Type: application/json")
    print("    Тіло запиту передається у форматі JSON.")

    print_separator("URL API")
    print("  POST https://api.openai.com/v1/chat/completions")
    print("\nЦя програма НЕ надсилає запит — лише показує, що було б відправлено.")
    print("Для реального чату запустіть: python 1_console.py\n")


if __name__ == "__main__":
    main()
