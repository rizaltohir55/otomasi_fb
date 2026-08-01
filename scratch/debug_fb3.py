"""
scratch/debug_fb3.py
Uji coba Join Group pada grup 697937093629189.
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

        # Look for Join button
        join_btn = page.get_by_role("button", name="Bergabung")
        print(f"Join button count: {await join_btn.count()}")
        if await join_btn.count() > 0 and await join_btn.first.is_visible():
            print("Klik tombol Bergabung...")
            await join_btn.first.click()
            await page.wait_for_timeout(3000)

            # Check if modal dialog or questionnaire popped up
            dialog = page.locator('div[role="dialog"]').first
            if await dialog.count() > 0 and await dialog.is_visible():
                print("Dialog kuesioner/aturan grup muncul!")
                d_text = await dialog.inner_text()
                print(f"Konten dialog: {d_text[:200]}...")

            # Check status after join
            print("\nCek status pasca-join...")
            joined_btn = page.get_by_role("button", name="Sudah Bergabung")
            print(f"Sudah Bergabung count: {await joined_btn.count()}")

            pending_btn = page.get_by_role("button", name="Batalkan permintaan")
            print(f"Batalkan permintaan count: {await pending_btn.count()}")

        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
