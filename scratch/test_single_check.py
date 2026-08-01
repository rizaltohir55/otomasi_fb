import asyncio
import os
import sys

from playwright.async_api import async_playwright

SESSION_FILE = r"d:\Project\otomasiFB\fb_session.json"
TEST_URLS = [
    "https://facebook.com/groups/1481477745503794/",
    "https://facebook.com/groups/697937093629189/",
    "https://facebook.com/groups/1849644908643180/"
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )

        for url in TEST_URLS:
            page = await context.new_page()
            try:
                print(f"Navigating to {url}...")
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                title = await page.title()
                print(f"Title: {title}")

                sell_cnt = await page.locator('div[role="button"]:has-text("Jual Sesuatu"), div[role="button"]:has-text("Sell Something"), span:has-text("Jual Sesuatu"), span:has-text("Sell Something")').count()
                disc_cnt = await page.locator('span:has-text("Tulis sesuatu"), span:has-text("Write something")').count()

                print(f"Sell count: {sell_cnt}, Disc count: {disc_cnt}")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
