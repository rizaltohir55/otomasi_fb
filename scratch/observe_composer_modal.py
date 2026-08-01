import asyncio
import json
import os
from playwright.async_api import async_playwright
from engine.collector import load_groups

async def main():
    session_file = os.path.abspath("fb_session.json")
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

        groups = load_groups()
        target_group = groups[0]
        print(f"Navigating to Group: {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Click trigger button
        trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu...")').first
        if await trigger.count() > 0:
            print("Clicking 'Tulis sesuatu...' trigger...")
            await trigger.click()
            await page.wait_for_timeout(3000)

        # Screenshot modal
        await page.screenshot(path="scratch/composer_modal.png")
        print("Composer modal screenshot saved to scratch/composer_modal.png")

        # Dump dialog DOM
        modal_analysis = await page.evaluate("""() => {
            const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            return dialogs.map(d => ({
                ariaLabel: d.getAttribute('aria-label'),
                className: d.className,
                buttons: Array.from(d.querySelectorAll('div[role="button"], button')).map(b => ({
                    ariaLabel: b.getAttribute('aria-label'),
                    ariaDisabled: b.getAttribute('aria-disabled'),
                    innerText: b.innerText.replace(/\\n/g, ' '),
                    role: b.getAttribute('role')
                })),
                textboxes: Array.from(d.querySelectorAll('div[role="textbox"], textarea, div[contenteditable="true"]')).map(tb => ({
                    ariaLabel: tb.getAttribute('aria-label'),
                    role: tb.getAttribute('role'),
                    contentEditable: tb.getAttribute('contenteditable'),
                    innerText: tb.innerText.replace(/\\n/g, ' ')
                })),
                fileInputs: Array.from(d.querySelectorAll('input[type="file"]')).map(inp => ({
                    name: inp.name,
                    multiple: inp.multiple,
                    accept: inp.accept
                }))
            }));
        }""")

        with open("scratch/composer_modal_dom.json", "w", encoding="utf-8") as f:
            json.dump(modal_analysis, f, indent=2, ensure_ascii=False)
        print("Composer modal DOM saved to scratch/composer_modal_dom.json")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
