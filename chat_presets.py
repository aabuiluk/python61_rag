"""Пресети параметрів API та ролей system для програм 0, 1, 2."""

ROLE_PRESETS: list[dict[str, str]] = [
    {
        "id": "1",
        "name": "Помічник",
        "prompt": "Ти корисний помічник. Відповідай українською, коротко і зрозуміло.",
    },
    {
        "id": "2",
        "name": "Вчитель",
        "prompt": (
            "Ти терплячий вчитель. Пояснюй простою мовою, крок за кроком, "
            "з прикладами. Відповідай українською."
        ),
    },
    {
        "id": "3",
        "name": "Програміст",
        "prompt": (
            "Ти досвідчений Python-розробник. Давай практичні поради та приклади коду. "
            "Відповідай українською, код — у блоках markdown."
        ),
    },
    {
        "id": "4",
        "name": "Формальний експерт",
        "prompt": (
            "Ти експерт-аналітик. Відповідай структуровано: короткий висновок, "
            "потім деталі пунктами. Без емоцій, українською."
        ),
    },
    {
        "id": "5",
        "name": "Креативний автор",
        "prompt": (
            "Ти креативний автор. Відповідай живо, з прикладами та метафорами, "
            "але по суті. Українською."
        ),
    },
]

PARAMETER_PRESETS: list[dict] = [
    {
        "id": "1",
        "name": "Баланс (стандарт)",
        "description": "Універсальний чат — помірна креативність, звичайна довжина.",
        "settings": {
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
    },
    {
        "id": "2",
        "name": "Точні факти",
        "description": "Мінімум вигадок — для фактів, визначень, інструкцій.",
        "settings": {
            "temperature": 0.2,
            "max_tokens": 800,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
    },
    {
        "id": "3",
        "name": "Креатив",
        "description": "Різноманітні формулювання, ідеї, storytelling.",
        "settings": {
            "temperature": 1.0,
            "max_tokens": 1500,
            "top_p": 1.0,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.6,
        },
    },
    {
        "id": "4",
        "name": "Коротко",
        "description": "Стислі відповіді без «води».",
        "settings": {
            "temperature": 0.5,
            "max_tokens": 300,
            "top_p": 0.95,
            "frequency_penalty": 0.4,
            "presence_penalty": 0.0,
        },
    },
    {
        "id": "5",
        "name": "Розгорнуто",
        "description": "Довгі пояснення, есе, детальний розбір теми.",
        "settings": {
            "temperature": 0.6,
            "max_tokens": 2000,
            "top_p": 1.0,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.2,
        },
    },
]


def get_role_preset(preset_id: str) -> dict[str, str]:
    for preset in ROLE_PRESETS:
        if preset["id"] == preset_id:
            return preset
    return ROLE_PRESETS[0]


def get_parameter_preset(preset_id: str) -> dict:
    for preset in PARAMETER_PRESETS:
        if preset["id"] == preset_id:
            return preset
    return PARAMETER_PRESETS[0]


def print_role_menu() -> None:
    print("Оберіть роль (system prompt):")
    for p in ROLE_PRESETS:
        print(f"  {p['id']}. {p['name']}")
    print()


def print_parameter_menu() -> None:
    print("Оберіть пресет параметрів API:")
    for p in PARAMETER_PRESETS:
        print(f"  {p['id']}. {p['name']} — {p['description']}")
    print()


def ask_role_choice() -> dict[str, str]:
    print_role_menu()
    while True:
        try:
            choice = input("Номер ролі (1-5) [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            return ROLE_PRESETS[0]
        if choice in {p["id"] for p in ROLE_PRESETS}:
            preset = get_role_preset(choice)
            print(f"Обрано роль: {preset['name']}\n")
            return preset
        print("Введіть число від 1 до 5.")


def ask_parameter_choice() -> dict:
    print_parameter_menu()
    while True:
        try:
            choice = input("Номер пресету (1-5) [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            return PARAMETER_PRESETS[0]
        if choice in {p["id"] for p in PARAMETER_PRESETS}:
            preset = get_parameter_preset(choice)
            print(f"Обрано: {preset['name']}\n")
            return preset
        print("Введіть число від 1 до 5.")
