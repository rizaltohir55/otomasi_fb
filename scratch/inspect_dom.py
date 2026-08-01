import asyncio
import os
import json
from playwright.async_api import async_playwright

async def inspect():
    session_path = "session/fb_session_bernando_ptr.json"
    url = "https://m.facebook.com/groups/697937093629189/user/61592752584034/"
    
    os.makedirs("scratch", exist_ok=True)
    
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
        
        await page.screenshot(path="scratch/page.png")
        
        html = await page.content()
        with open("scratch/user_activity.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Test DOM selectors
        inspection = await page.evaluate('''() => {
            const results = [];
            const allElements = document.querySelectorAll('div, article, section, header');
            
            for (const el of allElements) {
                const text = (el.innerText || '').trim();
                const role = el.getAttribute('role') || '';
                const id = el.id || '';
                const className = el.className || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const dataFt = el.getAttribute('data-ft') || '';

                if (text.length > 20 && text.length < 3000) {
                    const hasLike = /suka|like/i.test(text) || /like/i.test(ariaLabel);
                    const hasComment = /komentar|comment/i.test(text) || /comment/i.test(ariaLabel);
                    if (hasLike || hasComment) {
                        results.push({
                            tagName: el.tagName,
                            id: id,
                            role: role,
                            className: className.slice(0, 50),
                            ariaLabel: ariaLabel,
                            dataFt: dataFt,
                            textSnippet: text.slice(0, 200),
                            childCount: el.children.length
                        });
                    }
                }
            }
            return results;
        }''')
        
        with open("scratch/inspection.json", "w", encoding="utf-8") as f:
            json.dump(inspection, f, indent=2, ensure_ascii=False)
            
        print(f"DONE: Dumped {len(inspection)} elements to scratch/inspection.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
