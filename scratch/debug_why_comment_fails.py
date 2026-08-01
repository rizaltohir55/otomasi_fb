import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from playwright.async_api import async_playwright

async def main():
    session_file = os.path.abspath("session/fb_session_fendi.json")
    desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    print("DEBUGGING: Intercepting Facebook GraphQL responses during comment submit...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1280, "height": 900},
            storage_state=session_file
        )
        page = await context.new_page()

        # Listen to responses
        graphql_responses = []
        async def on_response(response):
            if "graphql" in response.url or "comment" in response.url:
                try:
                    text = await response.text()
                    graphql_responses.append((response.url, response.status, text[:300]))
                except Exception:
                    pass

        page.on("response", on_response)

        share_url = "https://www.facebook.com/share/p/19G6e97TUg/"
        print(f"Navigating to: {share_url}")
        await page.goto(share_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Look for comment box
        textbox = page.locator('div[role="textbox"][aria-label*="Tulis komentar"], div[role="textbox"]').first
        if await textbox.count() == 0:
            print("Textbox not found!")
            await browser.close()
            return

        print("Clicking textbox...")
        await textbox.click(force=True)
        await page.wait_for_timeout(500)

        comment_text = "REAL_TEST_COMMENT_CHECK"
        print(f"Typing: '{comment_text}'...")
        await page.keyboard.type(comment_text, delay=80)
        await page.wait_for_timeout(1000)

        send_btn = page.locator(
            'div[role="button"][aria-label="Posting komentar"], '
            'div[role="button"][aria-label="Comment"], '
            'div[role="button"][aria-label*="Posting komentar"]'
        ).first

        disabled = await send_btn.get_attribute("aria-disabled") if await send_btn.count() > 0 else "true"
        print(f"Send button aria-disabled = '{disabled}'")

        print("Clicking send button with force=True...")
        if await send_btn.count() > 0:
            await send_btn.click(force=True)
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(5000)

        print(f"\nCaptured {len(graphql_responses)} GraphQL/Comment network responses after click:")
        for url, status, snippet in graphql_responses[-10:]:
            print(f"  [{status}] {url[:80]}... => {snippet}")

        # Screenshot
        await page.screenshot(path="scratch/debug_comment_after.png")

        # Now check if REAL comment element exists outside textbox!
        real_comment_exists = await page.evaluate("""
            (target) => {
                const elements = Array.from(document.querySelectorAll('span, div, p'));
                for (const el of elements) {
                    if (el.getAttribute('role') !== 'textbox' && !el.closest('[role="textbox"]') && !el.closest('[contenteditable="true"]')) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t === target) return true;
                    }
                }
                return false;
            }
        """, comment_text)

        print(f"\nREAL COMMENT EXISTS IN FEED OUTSIDE TEXTBOX: {real_comment_exists}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
