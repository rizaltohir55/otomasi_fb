"""
scratch/debug_fb5.py
Inspeksi dialog konfirmasi pasca-klik tombol Bergabung.
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

        btn = page.locator('div[role="main"] div[role="button"]:has-text("Bergabung")').first
        if await btn.count() > 0:
            print("Klik tombol Bergabung dengan mouse click...")
            box = await btn.bounding_box()
            if box:
                await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                await page.wait_for_timeout(3000)

            # Check all open dialogs on page
            dialogs = page.locator('div[role="dialog"]')
            cnt = await dialogs.count()
            print(f"\nJumlah dialog terbuka setelah klik Join: {cnt}")
            for i in range(cnt):
                d = dialogs.nth(i)
                txt = await d.inner_text()
                print(f"Dialog {i+1}:\n{txt}\n---")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
