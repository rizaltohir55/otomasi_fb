import asyncio
import json
import os
from playwright.async_api import async_playwright

from manager.runner import fix_windows_stdout_encoding

async def main():
    fix_windows_stdout_encoding()
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

        target_group = "https://facebook.com/groups/1417425938580689/"
        print(f"Navigating to Anonymous Post Group: {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        os.makedirs("scratch", exist_ok=True)
        await page.screenshot(path="scratch/anon_group_initial.png")

        # Find composer triggers on this page
        triggers = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('div[role="button"], button, span'));
            return btns.map(b => ({
                tag: b.tagName,
                role: b.getAttribute('role'),
                label: b.getAttribute('aria-label'),
                text: b.innerText.substring(0, 50).replace(/\\n/g, ' '),
                visible: b.offsetWidth > 0 && b.offsetHeight > 0
            })).filter(b => b.visible && (
                b.text.includes('Tulis') || b.text.includes('Write') || b.text.includes('anonim') || b.text.includes('Buat')
            ));
        }""")
        print(f"Triggers found: {json.dumps(triggers, indent=2, ensure_ascii=False)}")

        # Click trigger 'Tulis sesuatu...' or 'Postingan anonim'
        trig_loc = page.locator('div[role="button"]:has-text("Tulis sesuatu..."), div[role="button"]:has-text("Postingan anonim")').first
        if await trig_loc.count() > 0:
            print("Clicking trigger...")
            await trig_loc.click()
            await page.wait_for_timeout(2500)

        await page.screenshot(path="scratch/anon_after_trigger.png")

        # Dump dialog info
        dialogs_info = await page.evaluate("""() => {
            const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            return dialogs.map(d => ({
                ariaLabel: d.getAttribute('aria-label'),
                title: d.querySelector('h1, h2, span')?.innerText || '',
                fullText: d.innerText.substring(0, 200).replace(/\\n/g, ' '),
                buttons: Array.from(d.querySelectorAll('div[role="button"], button')).map(b => ({
                    label: b.getAttribute('aria-label'),
                    disabled: b.getAttribute('aria-disabled'),
                    text: b.innerText.replace(/\\n/g, ' ')
                }))
            }));
        }""")
        print(f"Dialogs after trigger: {json.dumps(dialogs_info, indent=2, ensure_ascii=False)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
