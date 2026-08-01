import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_buttons():
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
        await page.wait_for_timeout(3500)
        
        # 1. Inspect exact Like button elements
        like_info = await page.evaluate('''() => {
            const results = [];
            // In mobile FB, buttons have role="button" or data-sigil or aria-label
            const buttons = document.querySelectorAll('div[role="button"], button, a[role="button"]');
            for (const b of buttons) {
                const aria = b.getAttribute('aria-label') || '';
                const sigil = b.getAttribute('data-sigil') || '';
                const text = (b.innerText || '').trim();
                const html = b.outerHTML.slice(0, 300);
                
                if (/like|suka/i.test(aria) || /like|suka/i.test(sigil) || text === 'Suka' || text === 'Like') {
                    results.push({
                        tagName: b.tagName,
                        aria: aria,
                        sigil: sigil,
                        text: text,
                        outerHTML: html
                    });
                }
            }
            return results;
        }''')
        
        print(f"=== Found {len(like_info)} Like Buttons ===")
        for idx, item in enumerate(like_info, 1):
            print(f"Like Btn {idx}: aria={repr(item['aria'])}, sigil={repr(item['sigil'])}, text={repr(item['text'])}")
            print(f"   HTML: {item['outerHTML']}\n")
            
        # 2. Inspect Comment triggers and comment inputs / send buttons
        comment_info = await page.evaluate('''() => {
            const results = [];
            const elements = document.querySelectorAll('div[role="button"], button, input, textarea, a');
            for (const el of elements) {
                const aria = el.getAttribute('aria-label') || '';
                const sigil = el.getAttribute('data-sigil') || '';
                const text = (el.innerText || '').trim();
                const type = el.getAttribute('type') || '';
                const value = el.getAttribute('value') || '';
                
                if (/comment|komentar|kirim|send|post/i.test(aria) || /comment|komentar|kirim|send|post/i.test(sigil) || /kirim|comment|post/i.test(text) || /kirim|comment|post/i.test(value)) {
                    results.push({
                        tagName: el.tagName,
                        type: type,
                        value: value,
                        aria: aria,
                        sigil: sigil,
                        text: text,
                        outerHTML: el.outerHTML.slice(0, 300)
                    });
                }
            }
            return results;
        }''')
        
        print(f"=== Found {len(comment_info)} Comment/Send Elements ===")
        for idx, item in enumerate(comment_info, 1):
            print(f"Comment Elem {idx}: tag={item['tagName']}, type={item['type']}, value={repr(item['value'])}, aria={repr(item['aria'])}, text={repr(item['text'])}")
            print(f"   HTML: {item['outerHTML']}\n")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_buttons())
