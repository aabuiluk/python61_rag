"""
Генерує PDF-каталоги з сайтів dask-centr.com.ua та goodwine.com.ua.

Запуск: python generate_catalogs.py
"""

import html
import json
import re
from datetime import date
from pathlib import Path

import requests
from fpdf import FPDF

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; python61_rag/1.0)"}
CATALOGS_DIR = Path(__file__).parent / "data" / "catalogs"
FONTS_DIR = Path(__file__).parent / "fonts"

# Компактні каталоги: RAG встигає проіндексувати за ~30 с
DASK_MAX_PRODUCTS = 12
GOODWINE_MAX_PRODUCTS = 8
FONT_FILE = FONTS_DIR / "DejaVuSans.ttf"
FONT_CANDIDATES = [
    FONT_FILE,
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def ensure_font() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Не знайдено шрифт з підтримкою кирилиці. "
        "Покладіть DejaVuSans.ttf у папку fonts/ або встановіть Arial Unicode."
    )


class CatalogPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.catalog_title = title
        font_path = ensure_font()
        self.add_font("DejaVu", "", str(font_path))
        self.set_auto_page_break(auto=True, margin=15)

    def header(self) -> None:
        self.set_font("DejaVu", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, self.catalog_title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Сторінка {self.page_no()}", align="C")

    def add_title_page(self, title: str, subtitle: str, info_lines: list[str]) -> None:
        self.add_page()
        self.set_x(self.l_margin)
        self.set_font("DejaVu", "", 20)
        self.set_text_color(0, 0, 0)
        self.ln(25)
        self.multi_cell(0, 11, title, align="C")
        self.ln(6)
        self.set_font("DejaVu", "", 12)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 7, subtitle, align="C")
        self.ln(10)
        self.set_font("DejaVu", "", 10)
        for line in info_lines:
            self.set_x(self.l_margin)
            self.multi_cell(0, 6, line[:120])
        self.ln(4)
        self.set_x(self.l_margin)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Дата формування каталогу: {date.today().isoformat()}")

    def add_section(self, title: str) -> None:
        self.ln(4)
        self.set_x(self.l_margin)
        self.set_font("DejaVu", "", 13)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 8, title)
        self.ln(2)

    def add_paragraph(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("DejaVu", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def add_product(self, index: int, article: str, name: str, extra: str = "") -> None:
        self.set_x(self.l_margin)
        self.set_font("DejaVu", "", 10)
        self.set_text_color(0, 0, 0)
        line = f"{index}. [{article}] {name}"
        if extra:
            line += f" — {extra}"
        self.multi_cell(0, 6, line[:220])


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def scrape_dask() -> dict:
    page_html = fetch_html("https://dask-centr.com.ua/")
    articles = re.findall(r"Артикул:\s*(\d+)", page_html)
    names = re.findall(
        r'class="product-name"[^>]*>\s*<a[^>]*>([^<]+)</a>', page_html
    )
    products = [
        {"article": art, "name": html.unescape(name).strip()}
        for art, name in zip(articles, names)
    ]

    categories = re.findall(
        r'class="category-name"[^>]*>\s*<a[^>]*>([^<]+)</a>', page_html
    )
    if not categories:
        categories = re.findall(
            r'<a[^>]+href="https://dask-centr\.com\.ua/[^"]+"[^>]*>\s*'
            r"(Меблева[^<]{3,40}|ДСП[^<]{0,30}|Ручки[^<]{0,30}|Завіси[^<]{0,30})",
            page_html,
        )

    cities = re.findall(
        r"(Київ|Львів|Одеса|Харків|Дніпро|Запоріжжя|Полтава|Кременчук|"
        r"Кривий Ріг|Біла Церква|Кам.янське)[^<\n]{0,60}",
        html.unescape(page_html),
    )

    return {
        "title": "ДАСк-Центр — каталог меблевої фурнітури",
        "url": "https://dask-centr.com.ua/",
        "description": (
            "Інтернет-магазин меблевої фурнітури, ДСП, стільниць, ХДФ, фанери. "
            "Наявність на складі, гарантія, доставка по Україні, онлайн-оплата."
        ),
        "phones": ["+38 (067) 448-17-60"],
        "cities": sorted(set(c.strip() for c in cities if c.strip()))[:5],
        "categories": sorted(set(html.unescape(c).strip() for c in categories))[:8],
        "products": products[:DASK_MAX_PRODUCTS],
    }


def parse_goodwine_product(product_id: str) -> dict | None:
    url = f"https://goodwine.com.ua/ua/catalog/product/view/id/{product_id}/"
    try:
        page_html = fetch_html(url)
    except requests.RequestException:
        return None

    match = re.search(
        r'<script type="application/ld\+json">(\{.*?"@type":"Product".*?\})</script>',
        page_html,
        re.S,
    )
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    offers = data.get("offers", {})
    price = offers.get("price", "")
    currency = offers.get("priceCurrency", "UAH")
    price_text = f"{price} {currency}" if price else ""

    return {
        "article": data.get("sku", product_id),
        "name": data.get("name", "").strip(),
        "price": price_text,
        "brand": data.get("brand", {}).get("name", "")
        if isinstance(data.get("brand"), dict)
        else str(data.get("brand", "")),
    }


def scrape_goodwine(max_products: int = GOODWINE_MAX_PRODUCTS) -> dict:
    page_html = fetch_html("https://goodwine.com.ua/ua/")
    product_ids = list(dict.fromkeys(re.findall(r"initCatalogForm\('(\d+)'\)", page_html)))

    products: list[dict] = []
    for product_id in product_ids[:max_products]:
        item = parse_goodwine_product(product_id)
        if item and item["name"]:
            products.append(item)

    return {
        "title": "Goodwine — каталог напоїв та продуктів",
        "url": "https://goodwine.com.ua/",
        "description": (
            "Інтернет-магазин Goodwine: вино, міцні напої, ігристі, делікатеси. "
            "Доставка по Києву та Україні, консультації сомельє."
        ),
        "sections": ["Вино", "Ігристі вина", "Міцні напої", "Делікатеси"],
        "products": products,
    }


def save_catalog_pdf(data: dict, output_path: Path) -> None:
    pdf = CatalogPDF(data["title"])
    pdf.add_page()
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "", 14)
    pdf.multi_cell(0, 8, data["title"])
    pdf.ln(2)
    pdf.set_font("DejaVu", "", 10)
    for line in [
        f"Сайт: {data['url']}",
        data["description"][:300],
        f"Телефон: {data['phones'][0]}" if data.get("phones") else "",
    ]:
        if line:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, line)
    pdf.ln(4)
    pdf.add_section("Товари")
    for i, product in enumerate(data["products"], 1):
        extra_parts = [p for p in [product.get("brand"), product.get("price")] if p]
        pdf.add_product(
            i,
            product.get("article", "?"),
            product.get("name", ""),
            ", ".join(extra_parts),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


def main() -> None:
    print("Завантаження даних з dask-centr.com.ua ...")
    dask_data = scrape_dask()
    dask_path = CATALOGS_DIR / "dask_catalog.pdf"
    save_catalog_pdf(dask_data, dask_path)
    print(f"  → {dask_path} ({len(dask_data['products'])} товарів)")

    print("Завантаження даних з goodwine.com.ua ...")
    goodwine_data = scrape_goodwine()
    goodwine_path = CATALOGS_DIR / "goodwine_catalog.pdf"
    save_catalog_pdf(goodwine_data, goodwine_path)
    print(f"  → {goodwine_path} ({len(goodwine_data['products'])} товарів)")

    print("\nГотово!")


if __name__ == "__main__":
    main()
