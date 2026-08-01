import asyncio
from playwright.async_api import async_playwright
import json

async def test_english_comment():
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
        
        # Click comment button
        comment_trig = page.locator('div[role="button"][aria-label*="comment" i], div[role="button"][aria-label*="komentar" i]').first
        if await comment_trig.count() > 0:
            await comment_trig.click()
            await page.wait_for_timeout(2500)
            
            # Dump all visible buttons and interactive elements in comment view
            elements = await page.evaluate('''
                () => {
                    const items = Array.from(document.querySelectorAll('div[role="button"], button, input, textarea'));
                    return items.map(el => ({
                        tag: el.tagName,
                        type: el.type || '',
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        text: (el.innerText || '').trim(),
                        html: el.outerHTML.slice(0, 150)
                    }));
                }
            ''')
            
            with open("scratch/english_comment_elements.json", "w", encoding="utf-8") as f:
                json.dump(elements, f, indent=2, ensure_ascii=False)
                
            print(f"Dumped {len(elements)} elements to scratch/english_comment_elements.json")
        else:
            print("Comment button not found on page.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_english_comment())
