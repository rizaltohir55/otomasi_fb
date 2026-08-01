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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for url in TEST_URLS:
            print(f"\n==========================================")
            print(f"Target URL: {url}")
            try:
                await page.goto(url, timeout=25000, wait_until="networkidle")
                await page.wait_for_timeout(2000)

                title = await page.title()
                print(f"Group Title: {title}")

                # Detect elements specific to Buy/Sell vs Discussion
                sell_btn_cnt = await page.locator('div[role="button"]:has-text("Jual Sesuatu"), div[role="button"]:has-text("Sell Something"), span:has-text("Jual Sesuatu"), span:has-text("Sell Something"), a:has-text("Jual Sesuatu"), a:has-text("Sell Something")').count()
                
                apa_jual_cnt = await page.locator('span:has-text("Apa yang Anda jual"), div:has-text("Apa yang Anda jual"), span:has-text("What are you selling")').count()
                
                tulis_sesuatu_cnt = await page.locator('span:has-text("Tulis sesuatu"), span:has-text("Write something")').count()

                disc_tab = await page.locator('a[role="tab"]:has-text("Diskusi"), a[role="tab"]:has-text("Discussion"), a[href*="/discussion"]').count()
                
                buy_sell_tab = await page.locator('a[role="tab"]:has-text("Jual Beli"), a[role="tab"]:has-text("Buy and Sell"), a[href*="/buy_sell"]').count()

                print(f"- 'Jual Sesuatu' / 'Sell Something' elements: {sell_btn_cnt}")
                print(f"- 'Apa yang Anda jual' elements: {apa_jual_cnt}")
                print(f"- 'Tulis sesuatu' / 'Write something' elements: {tulis_sesuatu_cnt}")
                print(f"- Discussion tab elements: {disc_tab}")
                print(f"- Buy & Sell tab elements: {buy_sell_tab}")

                # Determine post type
                if sell_btn_cnt > 0 or apa_jual_cnt > 0 or buy_sell_tab > 0:
                    group_type = "JUAL_BELI (Buy/Sell)"
                else:
                    group_type = "DISKUSI (Discussion)"
                
                print(f"==> CLASSIFICATION RESULT: {group_type}")

            except Exception as e:
                print(f"Error checking {url}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
