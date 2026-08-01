import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import asyncio
from playwright.async_api import async_playwright
from core.commenter import _add_comments_mobile, _like_post_mobile

async def test_live_comment():
    session_path = "session/fb_session_raden_mas.json"
    url = "https://m.facebook.com/groups/697937093629189/user/61592763443703/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=session_path,
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        print("Testing Auto-Like...")
        await _like_post_mobile(page)
        
        print("Testing Auto-Comment...")
        await _add_comments_mobile(page, ["Gasken bro", "Ready mas"])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_comment())
