import asyncio
import json
import os
from playwright.async_api import async_playwright
from manager.runner import fix_windows_stdout_encoding

async def handle_anonymous_post_modal(page):
    """
    Jika modal 'Postingan anonim' muncul di layar, klik tombol 'Buat Postingan Anonim'.
    """
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        for i in range(cnt):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=300):
                continue
            text = (await d.inner_text()).lower()
            if "postingan anonim" in text or "anonymous post" in text:
                print("   ℹ️ Modal 'Postingan anonim' terdeteksi. Menekan 'Buat Postingan Anonim'...")
                btn = d.locator(
                    'div[role="button"]:has-text("Buat Postingan Anonim"), '
                    'div[role="button"]:has-text("Create Anonymous Post"), '
                    'button:has-text("Buat Postingan Anonim"), '
                    'button:has-text("Create Anonymous Post")'
                ).first
                if await btn.count() > 0 and await btn.is_visible(timeout=800):
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Modal 'Postingan anonim' dikonfirmasi!")
                    return True
    except Exception as e:
        print(f"   ⚠️ Error handling anon modal: {e}")
    return False

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

        # Trigger
        trig_loc = page.locator('div[role="button"]:has-text("Tulis sesuatu..."), div[role="button"]:has-text("Postingan anonim")').first
        if await trig_loc.count() > 0:
            print("Clicking trigger...")
            await trig_loc.click()
            await page.wait_for_timeout(2000)

        # Handle anonymous modal
        await handle_anonymous_post_modal(page)

        os.makedirs("scratch", exist_ok=True)
        await page.screenshot(path="scratch/anon_after_confirmation.png")

        # Check dialogs now
        dialogs_info = await page.evaluate("""() => {
            const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            return dialogs.map(d => ({
                ariaLabel: d.getAttribute('aria-label'),
                fullText: d.innerText.substring(0, 150).replace(/\\n/g, ' '),
                hasTextbox: d.querySelector('div[role="textbox"][contenteditable="true"]') !== null,
                buttons: Array.from(d.querySelectorAll('div[role="button"], button')).map(b => ({
                    label: b.getAttribute('aria-label'),
                    disabled: b.getAttribute('aria-disabled'),
                    text: b.innerText.replace(/\\n/g, ' ')
                }))
            }));
        }""")
        print(f"Dialogs after handle_anonymous_post_modal: {json.dumps(dialogs_info, indent=2, ensure_ascii=False)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
