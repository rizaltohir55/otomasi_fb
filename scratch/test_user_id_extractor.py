import asyncio
from playwright.async_api import async_playwright
import re

async def test_user_id():
    session_path = "session/fb_session_bernando_ptr.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=session_path,
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        await page.goto("https://m.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Test Cookie User ID
        cookies = await context.cookies()
        c_user = next((c["value"] for c in cookies if c["name"] == "c_user"), "")
        print("Cookie c_user:", c_user)
        
        # Test DOM User ID
        dom_id = await page.evaluate('''() => {
            for (const a of document.querySelectorAll('a[href]')) {
                const href = a.href || '';
                const m = href.match(/facebook\\.com\\/(\\d{8,})/);
                if (m) return m[1];
                const m2 = href.match(/id=(\\d{8,})/);
                if (m2) return m2[1];
            }
            return '';
        }''')
        print("DOM User ID:", dom_id)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_user_id())
