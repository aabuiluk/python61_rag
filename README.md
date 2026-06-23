# python61_rag

Прості програми для роботи з ChatGPT API (лише `requests` + `tkinter`).

## Підготовка

```bash
pip install -r requirements.txt
cp .env.example .env
# Відредагуйте .env — вставте OPENAI_API_KEY
```

## Програми

| Файл | Опис |
|------|------|
| `0_test_settings.py` | Показує всі параметри запиту до API з поясненнями (без реального запиту) |
| `1_console.py` | Консольний чат |
| `2_desktop.py` | Десктопний чат (tkinter) |
| `3_rag.py` | Чат з RAG — відповіді на основі `.txt` файлів у папці `data/` |

## Запуск

```bash
python 0_test_settings.py
python 1_console.py
python 2_desktop.py
python 3_rag.py
```

Для RAG покладіть свої `.txt` документи в `data/` (є приклад `data/knowledge.txt`).
