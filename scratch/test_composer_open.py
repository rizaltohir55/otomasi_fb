import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import asyncio
from playwright.async_api import async_playwright
from core.composer import open_composer_page, detect_composer_container, find_textbox

async def test_composer():
    session_path = "session/fb_session_raden_mas.json"
    url = "https://m.facebook.com/groups/981333168580018/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=session_path,
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        print(f"Opening group: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        res = await open_composer_page(page, group_id="981333168580018")
        print(f"open_composer_page result: {res}")
        
        container, ctype = await detect_composer_container(page)
        print(f"Container: {ctype}")
        
        tb = await find_textbox(container)
        if tb:
            print("SUCCESS! Textbox found!")
        else:
            print("FAILED! Textbox not found!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_composer())
