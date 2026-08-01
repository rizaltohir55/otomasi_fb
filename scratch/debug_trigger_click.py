import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
import asyncio
from playwright.async_api import async_playwright

async def debug_trigger():
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
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        
        # Click write something
        loc = page.locator('span:has-text("Write something..."), span:has-text("Tulis sesuatu..."), div:has-text("Write something...")').first
        if await loc.count() > 0:
            print("Found trigger! Clicking...")
            await loc.click()
            await page.wait_for_timeout(3000)
            
            print(f"Page URL after trigger click: {page.url}")
            
            # Print visible textboxes & buttons
            info = await page.evaluate('''
                () => {
                    const els = Array.from(document.querySelectorAll('div[role="button"], button, textarea, div[role="textbox"], input'));
                    return els.map(e => ({
                        tag: e.tagName,
                        role: e.getAttribute('role') || '',
                        aria: e.getAttribute('aria-label') || '',
                        placeholder: e.getAttribute('placeholder') || '',
                        text: (e.innerText || e.value || '').slice(0, 50)
                    })).filter(x => x.text || x.placeholder || x.aria);
                }
            ''')
            print(f"Found {len(info)} interactive elements:")
            for item in info:
                print("  -", item)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_trigger())
