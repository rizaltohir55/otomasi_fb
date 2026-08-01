"""
scratch/debug_fb10.py
Inspeksi elemen komposer di dalam dialog secara detail.
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
from engine.collector import find_media_images

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

        # Open composer
        trigger = page.get_by_role("button", name="Tulis sesuatu...").first
        if await trigger.count() == 0:
            trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu")').first

        print("Klik trigger komposer...")
        await trigger.click()
        await page.wait_for_timeout(2500)

        dialog = page.locator('div[role="dialog"]').first
        if await dialog.is_visible():
            # Dump all clickable elements inside dialog
            elements = await dialog.evaluate("""
                (d) => {
                    const nodes = Array.from(d.querySelectorAll('*'));
                    return nodes.map(n => ({
                        tag: n.tagName,
                        role: n.getAttribute('role'),
                        ariaLabel: n.getAttribute('aria-label') || '',
                        text: (n.innerText || '').substring(0, 40),
                        isInput: n.tagName === 'INPUT',
                        inputType: n.getAttribute('type') || ''
                    })).filter(n => n.ariaLabel || n.isInput || (n.role === 'button' && n.text));
                }
            """)
            print("\n--- ELEMEN DI DALAM COMPOSER DIALOG ---")
            for e in elements:
                print(f"[{e['tag']}] role={e['role']} ariaLabel='{e['ariaLabel']}' text='{e['text']}' type='{e['inputType']}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
