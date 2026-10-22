import html
import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "sale_results.json"
REPORT_FILE = BASE_DIR / "daily_deals.html"
MAX_PRODUCTS = 40


def format_price(value):
    return f"{int(value):,}".replace(",", " ") + " kr"


def load_products():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError("sale_results.json mangler. Kjør skraperen først.")

    with RESULTS_FILE.open("r", encoding="utf-8") as file:
        products = json.load(file)

    if not isinstance(products, list):
        raise ValueError("sale_results.json inneholder ikke en liste.")

    valid = []

    for product in products:
        try:
            original = int(product["original_price"])
            sale = int(product["sale_price"])
            url = str(product["url"])
            store = product["store"]
            name = str(product["name"]).strip()

            if (
                original <= sale
                or sale <= 0
                or not url.startswith("https://")
                or not name
                or store
                not in (
                    "Ferner Jacobsen",
                    "Follestad",
                )
            ):
                continue

            product = dict(product)
            product["name"] = name
            product["discount_kr"] = original - sale
            product["discount_percent"] = round((original - sale) / original * 100)

            valid.append(product)

        except KeyError, TypeError, ValueError:
            continue

    valid.sort(
        key=lambda p: (
            p["discount_percent"],
            p["discount_kr"],
        ),
        reverse=True,
    )

    return valid[:MAX_PRODUCTS]


def create_ai_summary(products):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    data = [
        {
            "store": p["store"],
            "brand": p.get("brand", ""),
            "name": p["name"],
            "original_price": p["original_price"],
            "sale_price": p["sale_price"],
            "discount_percent": p["discount_percent"],
        }
        for p in products
    ]

    prompt = f"""
Du er en norsk personlig shopper med ekspertise
på premium herremote.

Skriv en kort introduksjon på norsk til en rapport
med dagens designerkupp.

Krav:
- Skriv 2–4 korte setninger.
- Fremhev interessante tilbud basert på dataene.
- Ikke finn på produkter, priser eller egenskaper.
- Ikke gjenta hele produktlisten.
- Hvis datagrunnlaget er svakt, si at listen
  er sortert etter rabatt.

Tilbudsdata:
{json.dumps(data, ensure_ascii=False)}
"""

    response = llm.invoke(prompt)
    summary = str(response.content).strip()

    return summary or ("Her er dagens tilbud, sortert etter rabatt.")


def build_report(products, ai_summary):
    rows = []

    for index, p in enumerate(products, start=1):
        brand = str(p.get("brand") or "").strip()
        name = str(p["name"]).strip()
        title = f"{brand} {name}".strip()

        store = str(p["store"])
        url = str(p["url"])
        original = int(p["original_price"])
        sale = int(p["sale_price"])
        saving = int(p["discount_kr"])
        percent = int(p["discount_percent"])

        rows.append(f"""
        <article class="product">
            <div class="number">{index:02d}</div>
            <div class="details">
                <div class="brand">{html.escape(brand)}</div>
                <h3>{html.escape(title)}</h3>
                <div class="store">{html.escape(store)}</div>
                <p class="prices">
                    <s>{format_price(original)}</s>
                    <strong>{format_price(sale)}</strong>
                </p>
                <p class="saving">
                    Spar {format_price(saving)} ({percent} %)
                </p>
                <a href="{html.escape(url, quote=True)}"
                   target="_blank"
                   rel="noopener noreferrer">
                    Se produktet →
                </a>
            </div>
            <div class="discount">-{percent} %</div>
        </article>
        """)

    summary_html = html.escape(ai_summary).replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dagens designerkupp</title>
<style>
body {{
    font-family: Arial, sans-serif;
    max-width: 850px;
    margin: 40px auto;
    padding: 0 20px;
    color: #202020;
    background: #faf9f6;
}}
h1 {{ font-size: 32px; margin-bottom: 8px; }}
.subtitle {{ color: #666; }}
.summary {{
    background: white;
    padding: 22px;
    margin: 28px 0;
    border-radius: 8px;
    line-height: 1.7;
}}
.product {{
    display: flex;
    align-items: flex-start;
    gap: 18px;
    background: white;
    padding: 22px;
    margin-bottom: 12px;
    border-radius: 8px;
}}
.number {{ color: #888; font-size: 18px; }}
.details {{ flex: 1; min-width: 0; }}
.brand {{
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #777;
    font-size: 11px;
}}
h3 {{ margin: 6px 0; font-size: 17px; }}
.store {{ color: #777; font-size: 13px; }}
.prices {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.prices s {{ color: #888; }}
.saving {{ font-weight: bold; }}
.discount {{ font-weight: bold; white-space: nowrap; }}
a {{ color: #244e42; }}
footer {{ margin: 28px 0; color: #777; font-size: 12px; }}
@media(max-width: 520px) {{
    body {{ margin: 20px auto; padding: 0 12px; }}
    .product {{ gap: 10px; padding: 15px; }}
    h1 {{ font-size: 25px; }}
}}
</style>
</head>
<body>
    <h1>Dagens designerkupp</h1>
    <div class="subtitle">
        Ferner Jacobsen &amp; Follestad
    </div>

    <section class="summary">
        <strong>Dagens oppsummering</strong>
        <p>{summary_html}</p>
        <p><strong>Antall tilbud:</strong> {len(products)}</p>
    </section>

    {"".join(rows)}

    <footer>
        Tilbudene er basert på skraperens siste kjøring.
        Kontroller pris og tilgjengelighet hos butikken
        før kjøp.
    </footer>
</body>
</html>
"""


def main():
    products = load_products()

    if not products:
        raise RuntimeError("Ingen gyldige tilbud funnet. Rapport ble ikke laget.")

    print(f"Fant {len(products)} gyldige tilbud.")

    summary = create_ai_summary(products)
    report = build_report(products, summary)

    REPORT_FILE.write_text(report, encoding="utf-8")

    print(f"Rapport lagret: {REPORT_FILE}")


if __name__ == "__main__":
    main()
