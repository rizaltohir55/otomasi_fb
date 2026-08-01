import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from playwright.async_api import async_playwright

async def main():
    session_file = os.path.abspath("session/fb_session_fendi.json")
    desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    print("VERIFYING: Opening Kayy Andromeda's post permalink to check comments...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1280, "height": 900},
            storage_state=session_file
        )
        page = await context.new_page()

        # Kayy Andromeda's post permalink from task-818 / user log
        target_url = "https://www.facebook.com/share/p/19G6e97TUg/"
        print(f"Navigating to Kayy Andromeda post: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        await page.screenshot(path="scratch/kayy_andromeda_post_comments.png")

        content = await page.content()
        print("\nChecking comments in Kayy Andromeda's post HTML:")
        for c in ["Gasken", "Inbox", "Satset"]:
            if c in content:
                print(f"  FOUND: Comment '{c}' IS PRESENT!")
            else:
                print(f"  MISSING: Comment '{c}' is missing")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
