import asyncio
from playwright.async_api import async_playwright

async def test_multi_comment_flow():
    session_path = "session/fb_session_bernando_ptr.json"
    url = "https://m.facebook.com/groups/697937093629189/user/61592752584034/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=session_path,
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        print(f"Opening {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        # Smart Comment Box Finder Function
        async def find_textbox():
            comment_box_selectors = [
                'div[role="textbox"][contenteditable="true"]',
                'div[role="textbox"]',
                'textarea[placeholder*="komentar" i]',
                'textarea[placeholder*="comment" i]',
                '[aria-label*="komentar" i]',
                '[aria-label*="comment" i]',
                'textarea[name="comment_text"]',
                'textarea',
            ]
            for sel in comment_box_selectors:
                try:
                    tb = page.locator(sel).first
                    if await tb.count() > 0 and await tb.is_visible(timeout=1000):
                        return tb
                except Exception:
                    pass
            return None

        tb = await find_textbox()
        if tb:
            print("Found comment textbox!")
            aria = await tb.get_attribute("aria-label") or ""
            placeholder = await tb.get_attribute("placeholder") or ""
            print(f"Textbox info: aria={repr(aria)}, placeholder={repr(placeholder)}")
        else:
            print("Comment textbox not found directly, trying comment trigger...")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_multi_comment_flow())
