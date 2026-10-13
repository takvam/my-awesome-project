import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="nb-NO")

        await page.goto(
            "https://www.fernerjacobsen.no/herre/salg",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.get_by_text(
            "48 Hour Holdall - Navy",
            exact=False,
        ).first.wait_for(timeout=20000)

        result = await page.get_by_text(
            "48 Hour Holdall - Navy",
            exact=False,
        ).first.evaluate(
            """el => {
                let node = el;
                const result = [];

                for (let i = 0; node && i < 7; i++, node = node.parentElement) {
                    result.push({
                        tag: node.tagName,
                        classes: String(node.className || "").slice(0, 300),
                        href: node.closest("a")?.href || "",
                        html: node.outerHTML.slice(0, 1800)
                    });
                }

                return result;
            }"""
        )

        for i, item in enumerate(result):
            print(f"\\n--- Forelder {i} ---")
            print("Tag:", item["tag"])
            print("Klasser:", item["classes"])
            print("Lenke:", item["href"])
            print("HTML:", item["html"])

        await browser.close()


asyncio.run(main())
