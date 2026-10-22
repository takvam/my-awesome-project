import asyncio
from playwright.async_api import async_playwright


async def main():
    url = "https://www.follestad.no/shop/salg/herre-salg/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="nb-NO")

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.locator(".product-card").first.wait_for(timeout=30000)

        cards = page.locator(".product-card")
        print("Antall produktkort ved start:", await cards.count())

        for i in range(await cards.count()):
            card = cards.nth(i)

            if await card.locator(".price-sale").count() == 0:
                continue

            print("\n" + "=" * 60)
            print("PRODUKTKORT:", i)

            print(
                "TEKST:\n",
                (await card.inner_text())[:1000],
            )

            print(
                "\nPRISELEMENTER:",
                await card.locator(
                    ".price, .price-regular, .price-sale, del, ins, s"
                ).evaluate_all(
                    """els => els.map(el => ({
                        tag: el.tagName,
                        className: el.className,
                        text: el.innerText
                    }))"""
                ),
            )

            print(
                "\nLENKER:",
                await card.locator("a[href]").evaluate_all(
                    """els => els.map(a => ({
                        text: (a.innerText || "").trim(),
                        href: a.href,
                        className: String(a.className || "")
                    }))"""
                ),
            )

            print("\nHTML:")
            print((await card.evaluate("el => el.outerHTML"))[:5000])

            # Ett kort er nok for å finne riktig struktur.
            break

        await browser.close()


asyncio.run(main())
