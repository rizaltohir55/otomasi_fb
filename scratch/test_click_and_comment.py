import asyncio
import json
from playwright.async_api import async_playwright

async def test_live_comment_flow():
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
        print("1. Opening page...")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3500)
        
        # --- TEST LIKE BUTTON ---
        print("\n2. Testing Like Click...")
        like_btn = page.locator('div[role="button"][aria-label^="like"]').first
        if await like_btn.count() > 0 and await like_btn.is_visible():
            aria_before = await like_btn.get_attribute("aria-label") or ""
            print(f"   Like button found before click: aria={repr(aria_before)}")
            await like_btn.click()
            await page.wait_for_timeout(2000)
            
            # Check after click
            like_after = page.locator('div[role="button"][aria-label*="pressed"]').first
            if await like_after.count() > 0:
                aria_after = await like_after.get_attribute("aria-label") or ""
                print(f"   SUCCESS! Like clicked! Now aria={repr(aria_after)}")
            else:
                print("   Like status after click not changed to pressed.")
        else:
            print("   Like button not found or already pressed.")
            
        # --- TEST COMMENT BUTTON & DIALOG ---
        print("\n3. Testing Comment Click...")
        comment_btn = page.locator('div[role="button"][aria-label*="comment"]').first
        if await comment_btn.count() > 0 and await comment_btn.is_visible():
            print("   Clicking comment button...")
            await comment_btn.click()
            await page.wait_for_timeout(3000)
            
            await page.screenshot(path="scratch/after_comment_click.png")
            print("   Screenshot saved to scratch/after_comment_click.png")
            
            # Inspect input/textarea and buttons after clicking comment
            elements = await page.evaluate('''() => {
                const res = [];
                const all = document.querySelectorAll('input, textarea, div[role="textbox"], div[role="button"], button');
                for (const el of all) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        res.push({
                            tag: el.tagName,
                            type: el.type || '',
                            role: el.getAttribute('role') || '',
                            aria: el.getAttribute('aria-label') || '',
                            placeholder: el.getAttribute('placeholder') || '',
                            text: (el.innerText || '').slice(0, 50),
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                }
                return res;
            }''')
            
            with open("scratch/comment_modal_elements.json", "w", encoding="utf-8") as f:
                json.dump(elements, f, indent=2, ensure_ascii=False)
                
            print(f"   Found {len(elements)} visible interactive elements after comment click. Saved to scratch/comment_modal_elements.json")
        else:
            print("   Comment button not found.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_comment_flow())
