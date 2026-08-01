import asyncio
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _fix_encoding():
    for s in ("stdout", "stderr"):
        stream = getattr(sys, s)
        if stream and hasattr(stream, "encoding") and stream.encoding and stream.encoding.lower() != "utf-8":
            try:
                setattr(sys, s, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
            except Exception:
                pass

_fix_encoding()

from playwright.async_api import async_playwright
from core.composer import is_composer_open, click_composer_trigger, open_composer_page, type_caption, submit_post, detect_composer_container

SESSION_FILE = r"d:\Project\otomasiFB\session\fb_session_raden_mas.json"
TEST_URL = "https://m.facebook.com/groups/697937093629189/"

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            viewport={"width": 412, "height": 915},
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Testing group post flow on {TEST_URL}...")
        await page.goto(TEST_URL, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        composer_open_before = await is_composer_open(page)
        print("Composer open initially?", composer_open_before)
        
        opened = await open_composer_page(page)
        print("open_composer_page result:", opened)
        
        container, ctype = await detect_composer_container(page)
        print("Container detected:", ctype)
        
        caption_ok = await type_caption(page, "Tes postingan otomatis", container)
        print("type_caption result:", caption_ok)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
