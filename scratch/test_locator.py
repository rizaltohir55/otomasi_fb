import asyncio
from playwright.async_api import async_playwright

async def test_detect():
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
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        
        # Test accurate JS locator
        res = await page.evaluate('''() => {
            // Find post cards on mobile Facebook user activity view
            // On m.facebook.com, post containers have 'Tulis komentar' or 'Write a comment' or 'Postingan Grup'
            const candidates = [];
            
            // Look for divs that contain 'Tulis komentar' or 'Write a comment' or have caption text
            const allDivs = Array.from(document.querySelectorAll('div'));
            
            for (const div of allDivs) {
                const text = (div.innerText || '');
                if (text.includes('Tulis komentar') || text.includes('Write a comment') || text.includes('Komentar') || text.includes('Comment')) {
                    // Make sure it's a card container, not the entire page root
                    if (text.length > 30 && text.length < 2500) {
                        candidates.push(div);
                    }
                }
            }
            
            if (candidates.length === 0) {
                // Fallback: look for divs under screen-root that have text
                for (const div of allDivs) {
                    const text = (div.innerText || '');
                    if (text.length > 50 && text.length < 2000 && /menit|jam|baru saja|just now/i.test(text)) {
                        candidates.push(div);
                    }
                }
            }
            
            // Pick the candidate that is closest to a post unit (smallest container that has the post text)
            let chosen = candidates[0];
            for (const cand of candidates) {
                if (cand.innerText.length < chosen.innerText.length && cand.innerText.length > 50) {
                    chosen = cand;
                }
            }
            
            if (chosen) {
                const key = `test-post-card-${Date.now()}`;
                chosen.setAttribute('data-test-post-card', key);
                return {
                    found: true,
                    selector: `[data-test-post-card="${key}"]`,
                    text: chosen.innerText.slice(0, 150)
                };
            }
            
            return { found: false };
        }''')
        
        print("Locator Result:", res)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_detect())
