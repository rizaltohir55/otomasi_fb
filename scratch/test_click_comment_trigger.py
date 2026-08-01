import asyncio
from playwright.async_api import async_playwright

async def test_trigger_flow():
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
        
        # Click comment button (Elem 6: aria-label contains comment)
        comment_trigger = await page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('div[role="button"], button, a'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                if (aria.includes('comment') || aria.includes('komentar')) {
                    const key = `test-trigger-${Date.now()}`;
                    b.setAttribute('data-test-trigger', key);
                    return { found: true, selector: `[data-test-trigger="${key}"]` };
                }
            }
            return { found: false };
        }''')
        
        print("Trigger result:", comment_trigger)
        if comment_trigger["found"]:
            await page.click(comment_trigger["selector"])
            await page.wait_for_timeout(2000)
            
            # Find input box after clicking trigger
            inputs = await page.evaluate('''() => {
                const res = [];
                for (const el of document.querySelectorAll('input, textarea, div[role="textbox"], div[contenteditable="true"]')) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        res.push({
                            tag: el.tagName,
                            type: el.type || '',
                            placeholder: el.placeholder || '',
                            aria: el.getAttribute('aria-label') || '',
                            role: el.getAttribute('role') || ''
                        });
                    }
                }
                return res;
            }''')
            print("Visible inputs after trigger click:", inputs)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_trigger_flow())
