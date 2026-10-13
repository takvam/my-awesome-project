import asyncio
import re
from dataclasses import dataclass, asdict
from typing import Optional

from playwright.async_api import async_playwright


STORES = {
    "Ferner Jacobsen": {
        "url": "https://www.fernerjacobsen.no/herre/salg",
        "card_selector": '[role="listitem"][data-product-id]',
    },
    "Follestad": {
        "url": "https://www.follestad.no/shop/salg/herre-salg/",
        "card_selector": ".product-card",
    },
}


@dataclass
class Product:
    store: str
    brand: str
    name: str
    sale_price: int
    original_price: int
    discount_kr: int
    discount_percent: int
    url: str


def parse_price(value: str) -> Optional[int]:
    """Konverterer f.eks. '1 819 kr' og '3 560,–' til heltall."""
    if not value:
        return None

    cleaned = value.replace("\xa0", " ").strip()
    match = re.search(r"\d[\d .]*", cleaned)

    if not match:
        return None

    digits = re.sub(r"\D", "", match.group(0))
    return int(digits) if digits else None


async def load_all_products(page, selector):
    """Skroller siden for å utløse eventuell lasting av flere produkter."""
    previous_count = -1
    stable_rounds = 0

    for _ in range(30):
        count = await page.locator(selector).count()

        if count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= 3:
            break

        previous_count = count

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)

    return await page.locator(selector).evaluate_all(
        """cards => cards.map(card => {
            const text = selector =>
                card.querySelector(selector)?.innerText?.trim() || "";

            const link = card.querySelector(
                "a[href*='/produkt/'], a[data-product-id], a[href]"
            );

            return {
                url: link?.href || "",
                brand: text(".product-card-brand") ||
                       text('[class*="text-primary-headings"]'),
                name: text(".product-card-title") ||
                      text('[class*="font-serif"][class*="text-light"]'),
                regular: text(".price-regular"),
                sale: text(".price-sale"),
                struck: card.querySelector("s")?.innerText?.trim() || "",
                current: text('[class*="text-accent-bronze"][class*="font-serif"]'),
                full_text: card.innerText || ""
            };
        })"""
    )


def make_product(store, item):
    if not item["url"]:
        return None

    if store == "Ferner Jacobsen":
        # Ferner viser førprisen i et <s>-element.
        original = parse_price(item["struck"])
        sale = parse_price(item["current"])

        # Fallback hvis klassene på prisfeltet endres.
        if original is None or sale is None:
            return None

        brand = item["brand"]
        name = item["name"]

    else:
        # Follestad: prisene er markert med egne CSS-klasser.
        original = parse_price(item["regular"])
        sale = parse_price(item["sale"])

        if original is None or sale is None:
            return None

        brand = item["brand"]
        name = item["name"]

    # Beskytt mot feilmerking og produkter uten reell rabatt.
    if not name or not original or not sale:
        return None

    if sale >= original:
        return None

    discount_kr = original - sale
    discount_percent = round(discount_kr / original * 100)

    return Product(
        store=store,
        brand=brand,
        name=name,
        sale_price=sale,
        original_price=original,
        discount_kr=discount_kr,
        discount_percent=discount_percent,
        url=item["url"],
    )


async def scrape_store(browser, store, config):
    print(f"Henter produkter fra {store} ...")

    page = await browser.new_page(
        locale="nb-NO",
        viewport={"width": 1440, "height": 1000},
    )

    try:
        response = await page.goto(
            config["url"],
            wait_until="domcontentloaded",
            timeout=60000,
        )

        if response and response.status >= 400:
            print(f"  HTTP-feil: {response.status}")
            return []

        await page.locator(config["card_selector"]).first.wait_for(timeout=30000)

        items = await load_all_products(
            page,
            config["card_selector"],
        )

        products = []
        seen_urls = set()

        for item in items:
            product = make_product(store, item)

            if product and product.url not in seen_urls:
                seen_urls.add(product.url)
                products.append(product)

        print(f"  Fant {len(items)} produktkort, {len(products)} bekreftede tilbud.")

        return products

    except Exception as error:
        print(f"  Feil under henting: {error}")
        return []

    finally:
        await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        all_products = []

        try:
            for store, config in STORES.items():
                products = await scrape_store(browser, store, config)
                all_products.extend(products)
        finally:
            await browser.close()

    all_products.sort(
        key=lambda p: (p.discount_percent, p.discount_kr),
        reverse=True,
    )

    print("\n" + "=" * 70)
    print(f"BEKREFTede TILBUD: {len(all_products)}")
    print("=" * 70)

    for product in all_products[:50]:
        print(f"\n{product.store} — {product.brand}")
        print(product.name)
        print(
            f"Før: {product.original_price:,} kr | "
            f"Nå: {product.sale_price:,} kr".replace(",", " ")
        )
        print(
            f"Spar {product.discount_kr:,} kr ({product.discount_percent} %)".replace(
                ",", " "
            )
        )
        print(product.url)

    # Lagre alle funn slik at de kan brukes av e-postagenten senere.
    with open("sale_results.json", "w", encoding="utf-8") as file:
        import json

        json.dump(
            [asdict(p) for p in all_products],
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\nResultatene er lagret i sale_results.json")


if __name__ == "__main__":
    asyncio.run(main())
