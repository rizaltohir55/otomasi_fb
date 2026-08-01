import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    session_file = os.path.abspath("session/fb_session_fendi.json")
    desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    print("INSPECTING comment_create GraphQL payload...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1280, "height": 900},
            storage_state=session_file
        )
        page = await context.new_page()

        comment_responses = []

        async def on_response(response):
            if "graphql" in response.url:
                try:
                    text = await response.text()
                    if "comment_create" in text or "CommentCreate" in text:
                        comment_responses.append(text)
                except Exception:
                    pass

        page.on("response", on_response)

        share_url = "https://www.facebook.com/share/p/19G6e97TUg/"
        await page.goto(share_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        textbox = page.locator('div[role="textbox"][aria-label*="Tulis komentar"], div[role="textbox"]').first
        if await textbox.count() == 0:
            print("Textbox not found")
            await browser.close()
            return

        await textbox.click(force=True)
        await page.wait_for_timeout(500)

        test_msg = f"TEST_PAYLOAD_CHECK_{os.urandom(2).hex()}"
        await page.keyboard.type(test_msg, delay=80)
        await page.wait_for_timeout(1000)

        send_btn = page.locator('div[role="button"][aria-label="Posting komentar"], div[role="button"][aria-label*="Posting komentar"]').first
        if await send_btn.count() > 0:
            await send_btn.click(force=True)
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(6000)

        print(f"\nFound {len(comment_responses)} comment_create GraphQL payloads:")
        for idx, payload in enumerate(comment_responses, 1):
            print(f"\n--- Payload #{idx} ---")
            print(payload[:1500])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
