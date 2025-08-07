import asyncio
from playwright.async_api import async_playwright, Playwright


async def run(playwright: Playwright):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.goto("http://localhost:8000")
    await page.wait_for_load_state("networkidle")

    await page.wait_for_timeout(10000)

    # Insert your interactions or assertions here
    await page.screenshot(path="screenshot.png")

    await context.close()
    await browser.close()


async def main():
    async with async_playwright() as playwright:
        await run(playwright)


if __name__ == "__main__":
    asyncio.run(main())
