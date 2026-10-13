import asyncio
import re
from playwright.async_api import async_playwright

STORES = {
    "Ferner Jacobsen": "https://www.fernerjacobsen.no/herre/salg",
    "Follestad": "https://www.follestad.no/shop/salg/herre-salg/",
}


async def test_store(browser, name, url):
    print("\n" + "=" * 65)
    print(name)
    print(url)

    page = await browser.new_page(
        locale="nb-NO",
        viewport={"width": 1440, "height": 1000},
    )

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("HTTP-status:", response.status if response else "Ukjent")

        try:
            await page.wait_for_load_state(
                "networkidle",
                timeout=15000,
            )
        except Exception:
            print("Nettverket ble ikke helt stille; fortsetter testen.")

        # Gi JavaScript litt tid til å bygge produktlisten.
        await page.wait_for_timeout(3000)

        # Skroll ned for å utløse eventuell lazy loading.
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(1000)

        print("Sidetittel:", await page.title())
        print("Endelig URL:", page.url)

        # Tell elementer som har klassenavn knyttet til produkter/priser.
        class_info = await page.locator("[class]").evaluate_all(
            """elements => {
                const counts = {};
                for (const el of elements) {
                    for (const cls of el.classList) {
                        if (/product|price|sale|discount|item-card/i.test(cls)) {
                            counts[cls] = (counts[cls] || 0) + 1;
                        }
                    }
                }
                return Object.entries(counts)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 30);
            }"""
        )

        print("\nProdukt-/prisklasser:")
        for cls, count in class_info:
            print(f"  {cls}: {count}")

        # Finn lenker som kan være produkter.
        links = await page.locator("a[href]").evaluate_all(
            """elements => elements.map(a => ({
                text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                href: a.href,
                classes: a.className?.toString() || ''
            }))"""
        )

        candidates = []
        seen = set()

        for item in links:
            text = re.sub(r"\\s+", " ", item["text"]).strip()
            href = item["href"]
            path = href.lower().split("?")[0]

            if not text or len(text) < 3:
                continue

            # Ikke ta med vanlige navigasjonslenker.
            if any(
                x in path
                for x in (
                    "/shop/herre/",
                    "/shop/dame/",
                    "/shop/merker",
                    "/butikker",
                    "/frakt-og-levering",
                    "/favoritter",
                )
            ):
                continue

            looks_product_like = any(
                x in path
                for x in (
                    "/product/",
                    "/products/",
                    "/produkt/",
                    "/p/",
                )
            ) or re.search(
                r"product|product-card|product-item",
                item["classes"],
                re.IGNORECASE,
            )

            if looks_product_like and (text, href) not in seen:
                seen.add((text, href))
                candidates.append((text, href))

        print("\nMulige produktlenker:", len(candidates))
        for text, href in candidates[:25]:
            print(f"- {text[:120]} | {href}")

        # Vis tekstutdrag som inneholder priser.
        print("\nTekstutdrag med priser:")
        body_text = await page.locator("body").inner_text()
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]

        price_lines = []
        for i, line in enumerate(lines):
            if re.search(r"\\d[\\d .]*[,.-]\\s*(?:kr|NOK|–)?|\\d+\\s*,-", line, re.I):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                excerpt = " | ".join(lines[start:end])

                if excerpt not in price_lines:
                    price_lines.append(excerpt)

            if len(price_lines) >= 15:
                break

        for excerpt in price_lines:
            print("-", excerpt[:250])

        if not candidates:
            print("\nIngen produktlenker matchet filtrene.")
            print("Her er et utdrag av sideteksten:")
            print(body_text[:1500])

    except Exception as error:
        print("TESTFEIL:", repr(error))

    finally:
        await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for name, url in STORES.items():
            await test_store(browser, name, url)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
