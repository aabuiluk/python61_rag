# python61_rag

Прості програми для роботи з ChatGPT API.

## Підготовка

```bash
pip install -r requirements.txt
cp .env.example .env
# Відредагуйте .env — вставте OPENAI_API_KEY
```

## PDF-каталоги для RAG

```bash
python generate_catalogs.py
```

Створює в `data/catalogs/`:
- `dask_catalog.pdf` — товари з [dask-centr.com.ua](https://dask-centr.com.ua/)
- `goodwine_catalog.pdf` — товари з [goodwine.com.ua](https://goodwine.com.ua/)

## Програми

| Файл | Опис |
|------|------|
| `0_test_settings.py` | Показує всі параметри запиту до API з поясненнями |
| `1_console.py` | Консольний чат |
| `2_desktop.py` | Десктопний чат (tkinter) |
| `3_rag.py` | Чат з RAG — оберіть каталог ДАСк, Goodwine або свій файл |
| `generate_catalogs.py` | Оновлення PDF-каталогів з сайтів |

## Запуск

```bash
python 0_test_settings.py
python 1_console.py
python 2_desktop.py
python 3_rag.py
```
