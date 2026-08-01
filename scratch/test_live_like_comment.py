import asyncio
from playwright.async_api import async_playwright

async def test_live_interaction():
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
        
        # Test finding like button with case-insensitive JS selector
        like_btn = await page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('div[role="button"], button, a'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                const text = (b.innerText || '').toLowerCase();
                if ((aria.includes('like') || aria.includes('suka') || text.includes('suka')) && !aria.includes('pressed') && !aria.includes('batal')) {
                    const key = `test-like-${Date.now()}`;
                    b.setAttribute('data-test-like', key);
                    return { found: true, selector: `[data-test-like="${key}"]`, aria: aria };
                }
            }
            return { found: false };
        }''')
        
        print("Like button result:", like_btn)
        
        # Test finding comment button
        comment_btn = await page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('div[role="button"], button, a'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                const text = (b.innerText || '').toLowerCase();
                if (aria.includes('comment') || aria.includes('komentar') || text.includes('komentar')) {
                    const key = `test-comment-${Date.now()}`;
                    b.setAttribute('data-test-comment', key);
                    return { found: true, selector: `[data-test-comment="${key}"]`, aria: aria };
                }
            }
            return { found: false };
        }''')
        
        print("Comment trigger result:", comment_btn)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_interaction())
