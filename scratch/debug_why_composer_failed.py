import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from playwright.async_api import async_playwright
from engine.browser import create_stealth_context
from engine.dom_analyzer import find_composer_trigger, get_active_composer_dialog

async def test_failing_groups():
    session_file = os.path.join(config.BASE_DIR, "fb_session.json")
    if not os.path.exists(session_file):
        sessions = [f for f in os.listdir(config.SESSION_DIR) if f.endswith(".json")]
        if sessions:
            session_file = os.path.join(config.SESSION_DIR, sessions[0])
            
    print(f"Using session: {session_file}")
    
    test_urls = [
        "https://www.facebook.com/groups/971072418695168/",
        "https://www.facebook.com/groups/1849644908643180/",
        "https://www.facebook.com/groups/270331667358702/",
        "https://www.facebook.com/groups/jualbelihpjakarta1/",
    ]
    
    async with async_playwright() as p:
        browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
        page = await context.new_page()
        
        for url in test_urls:
            print(f"\n--- Testing: {url} ---")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Check url redirect
            print(f"Current URL: {page.url}")
            
            # Check membership status indicators
            buttons = page.locator('div[role="main"] div[role="button"]')
            cnt = await buttons.count()
            print(f"Main buttons count: {cnt}")
            for i in range(min(cnt, 10)):
                b = buttons.nth(i)
                txt = (await b.inner_text()).strip()
                lbl = await b.get_attribute("aria-label") or ""
                print(f"  Btn {i}: txt='{txt}' | label='{lbl}'")
                
            # Check composer trigger
            trig = await find_composer_trigger(page)
            print(f"find_composer_trigger result: {trig}")
            if trig:
                await trig.click()
                await page.wait_for_timeout(2000)
                dialog = await get_active_composer_dialog(page)
                print(f"Active composer dialog after click: {dialog}")
            else:
                # Print all text in main
                main_txt = await page.locator('div[role="main"]').inner_text()
                print("Main text preview:", repr(main_txt[:200]))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_failing_groups())
