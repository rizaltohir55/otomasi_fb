import asyncio
import json
import os
from playwright.async_api import async_playwright
from engine.collector import load_groups

async def main():
    session_file = os.path.abspath("fb_session.json")
    if not os.path.exists(session_file):
        print("fb_session.json not found")
        return

    with open(session_file, "r", encoding="utf-8") as f:
        storage_state = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to Facebook Home...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        title = await page.title()
        url = page.url
        print(f"Loaded Home: Title='{title}', URL='{url}'")

        # Navigate to first group from groups.txt
        groups = load_groups()
        target_group = groups[0] if groups else "https://www.facebook.com/groups/100000000000000"
        print(f"Navigating to Group: {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        os.makedirs("scratch", exist_ok=True)
        await page.screenshot(path="scratch/group_page.png")
        print("Group screenshot saved to scratch/group_page.png")

        # Dump relevant DOM buttons and roles
        analysis = await page.evaluate("""() => {
            const result = {
                title: document.title,
                url: window.location.href,
                headings: Array.from(document.querySelectorAll('h1, h2')).map(h => h.innerText.trim()),
                buttons: Array.from(document.querySelectorAll('div[role="button"], button, a[role="button"]'))
                    .map(b => ({
                        tag: b.tagName,
                        role: b.getAttribute('role'),
                        ariaLabel: b.getAttribute('aria-label'),
                        innerText: b.innerText.substring(0, 50).replace(/\\n/g, ' '),
                        isVisible: b.offsetWidth > 0 && b.offsetHeight > 0
                    }))
                    .filter(b => b.isVisible)
                    .slice(0, 50),
                textboxes: Array.from(document.querySelectorAll('div[role="textbox"], textarea, input[type="text"]'))
                    .map(tb => ({
                        tag: tb.tagName,
                        role: tb.getAttribute('role'),
                        ariaLabel: tb.getAttribute('aria-label'),
                        contentEditable: tb.getAttribute('contenteditable'),
                        innerText: tb.innerText.substring(0, 50).replace(/\\n/g, ' ')
                    })),
                dialogs: Array.from(document.querySelectorAll('div[role="dialog"]')).map(d => ({
                    ariaLabel: d.getAttribute('aria-label'),
                    text: d.innerText.substring(0, 100).replace(/\\n/g, ' ')
                }))
            };
            return result;
        }""")

        with open("scratch/real_fb_dom.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print("DOM structure saved to scratch/real_fb_dom.json")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
