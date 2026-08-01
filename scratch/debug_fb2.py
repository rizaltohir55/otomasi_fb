"""
scratch/debug_fb2.py
Diagnosa komposer & tombol POSTING saat modal dialog terbuka.
"""
import asyncio
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if stream and hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))

fix_encoding()

from playwright.async_api import async_playwright
import config

SESSION_PATH = os.path.join(config.SESSION_DIR, "fb_session_raden_mas.json")
TARGET_GROUP = "https://facebook.com/groups/697937093629189/"

async def debug():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=SESSION_PATH,
            viewport={"width": 1440, "height": 900},
            user_agent=config.USER_AGENT_DESKTOP
        )
        page = await context.new_page()
        print(f"Navigasi ke {TARGET_GROUP}...")
        await page.goto(TARGET_GROUP, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 1. Inspect Join button vs Joined status
        join_btn = page.get_by_role("button", name="Bergabung")
        print(f"Join button (Bergabung) count: {await join_btn.count()}")
        if await join_btn.count() > 0:
            print(f"Join button visible: {await join_btn.first.is_visible()}")

        # 2. Try opening composer
        trigger = page.get_by_role("button", name="Tulis sesuatu...")
        if await trigger.count() == 0:
            trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu")').first
        
        print(f"Trigger count: {await trigger.count()}")
        if await trigger.count() > 0:
            print("Klik trigger komposer...")
            await trigger.click()
            await page.wait_for_timeout(3000)

            # Check if dialog opened
            dialog = page.locator('div[role="dialog"]').first
            print(f"Dialog visible: {await dialog.is_visible()}")

            if await dialog.is_visible():
                # Inspect buttons inside dialog
                dialog_btns = await dialog.evaluate("""
                    (d) => {
                        const btns = Array.from(d.querySelectorAll('div[role="button"], button'));
                        return btns.map(b => ({
                            label: b.getAttribute('aria-label') || '',
                            text: (b.innerText || '').trim(),
                            disabled: b.getAttribute('aria-disabled'),
                            class: b.className
                        }));
                    }
                """)
                print("\n--- BUTTONS DI DALAM DIALOG COMPOSER ---")
                for b in dialog_btns:
                    print(f"  label='{b['label']}' text='{b['text']}' disabled={b['disabled']}")

        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
