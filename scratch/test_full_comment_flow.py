import asyncio
from playwright.async_api import async_playwright

async def test_flow():
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
        
        # 1. Smart JS locator for user activity page
        match = await page.evaluate('''() => {
            const cleanStr = val => (val || '')
                .replace(/[\\u200e\\u200f\\u200b-\\u200d\\ufeff]/g, '')
                .toLowerCase()
                .replace(/[^\\w\\s]/g, ' ')
                .replace(/\\s+/g, ' ')
                .trim();

            // Find all divs containing post text / buttons
            const allDivs = Array.from(document.querySelectorAll('div'));
            const cards = [];

            for (const div of allDivs) {
                const text = cleanStr(div.innerText || '');
                if (text.length > 50 && text.length < 1500) {
                    if (text.includes('bernando ptr') || text.includes('menit') || text.includes('jam') || text.includes('tulis komentar') || text.includes('suka')) {
                        cards.push(div);
                    }
                }
            }

            if (cards.length > 0) {
                // Pick top card
                const chosen = cards[0];
                const key = `test-post-scope-${Date.now()}`;
                chosen.setAttribute('data-test-post-scope', key);
                return { found: true, selector: `[data-test-post-scope="${key}"]` };
            }

            return { found: false };
        }''')
        
        print("Match result:", match)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_flow())
