import asyncio
import os
import sys
import json

from playwright.async_api import async_playwright

SESSION_FILE = r"d:\Project\otomasiFB\session\fb_session_kayy_andromeda.json"
TEST_URLS = [
    "https://facebook.com/groups/1481477745503794/",
    "https://facebook.com/groups/697937093629189/",
    "https://facebook.com/groups/981333168580018/",
    "https://facebook.com/groups/2324361217720714/",
    "https://facebook.com/groups/1417425938580689/",
]

async def main():
    if not os.path.exists(SESSION_FILE):
        print(f"Session file not found: {SESSION_FILE}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for url in TEST_URLS:
            print(f"\n--- Checking: {url} ---")
            try:
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                
                title = await page.title()
                print(f"Title: {title}")

                # Check indicators for Buy/Sell vs Discussion
                # 1. Look for 'Sell Something', 'Jual Sesuatu', 'Apa yang Anda jual?', 'Item for sale'
                body_text = await page.evaluate("document.body.innerText")
                
                has_sell_something = any(kw in body_text.lower() for kw in [
                    "sell something", "jual sesuatu", "apa yang anda jual", 
                    "what are you selling", "buat postingan jual beli", "sell item"
                ])
                
                # Check composer placeholder text or buttons
                composer_text = await page.evaluate('''() => {
                    const triggers = Array.from(document.querySelectorAll('div[role="button"], span, div'));
                    for (let el of triggers) {
                        const t = (el.innerText || '').trim();
                        if (t.includes("Apa yang Anda jual") || t.includes("Sell Something") || t.includes("Jual Sesuatu") || t.includes("Tulis sesuatu") || t.includes("Write something")) {
                            return t;
                        }
                    }
                    return "";
                }''')

                # Check if "Buy and Sell" or "Jual Beli" tab exists or if "Diskusi" tab is separate
                has_buy_sell_tab = await page.evaluate('''() => {
                    const tabs = Array.from(document.querySelectorAll('a[role="tab"], div[role="tab"]'));
                    return tabs.map(t => t.innerText.trim()).filter(Boolean);
                }''')

                print(f"Composer Trigger / Text: {composer_text}")
                print(f"Tabs found: {has_buy_sell_tab}")
                print(f"Has Sell Keywords in page: {has_sell_something}")

                # Check URL redirect or canonical
                current_url = page.url
                print(f"Final URL: {current_url}")

            except Exception as e:
                print(f"Error checking {url}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
