import asyncio
from playwright.async_api import async_playwright

async def test_posting_comment():
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
        await page.wait_for_timeout(3000)
        
        # Click comment button to open textarea & send button
        comment_btn = page.locator('div[role="button"][aria-label*="comment"]').first
        if await comment_btn.count() > 0:
            await comment_btn.click()
            await page.wait_for_timeout(2000)
            
            # Locate textarea
            textarea = page.locator('textarea[placeholder*="komentar"], textarea[placeholder*="comment"]').first
            if await textarea.count() > 0:
                await textarea.fill("Info ready mas")
                await page.wait_for_timeout(500)
                
                # Locate send button
                send_btn = page.locator('div[role="button"][aria-label*="Posting komentar"], div[role="button"][aria-label*="Post comment"]').first
                if await send_btn.count() > 0:
                    print("Found 'Posting komentar' button! Clicking it...")
                    await send_btn.click()
                    await page.wait_for_timeout(3000)
                    print("SUCCESS! Comment posted!")
                else:
                    print("Send button 'Posting komentar' not found.")
            else:
                print("Textarea not found.")
        else:
            print("Comment button not found.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_posting_comment())
