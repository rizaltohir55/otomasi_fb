import asyncio
from playwright.async_api import async_playwright

async def test_wait():
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
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(3000)
        
        # Wait for feed cards to render
        try:
            await page.wait_for_selector('div.m', timeout=10000)
            print("Feed cards 'div.m' loaded!")
        except Exception as e:
            print("Timeout waiting for div.m:", e)
            
        # Count buttons with aria-label
        info = await page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('[aria-label]'));
            return btns.map(b => ({
                tag: b.tagName,
                aria: b.getAttribute('aria-label'),
                text: b.innerText.slice(0, 50)
            })).filter(x => x.aria && (x.aria.toLowerCase().includes('like') || x.aria.toLowerCase().includes('comment') || x.aria.toLowerCase().includes('suka') || x.aria.toLowerCase().includes('komentar')));
        }''')
        
        print(f"Found {len(info)} matching action buttons:")
        for idx, item in enumerate(info, 1):
            print(f"  Button {idx}: aria={repr(item['aria'])}, tag={item['tag']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_wait())
