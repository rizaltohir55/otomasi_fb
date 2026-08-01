"""
scratch/debug_fb9.py
Uji coba spesifik upload gambar di dalam MODAL DIALOG COMPOSER (bukan comment box feed).
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

        # Open composer
        trigger = page.get_by_role("button", name="Tulis sesuatu...").first
        if await trigger.count() == 0:
            trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu")').first

        print("Klik trigger komposer...")
        await trigger.click()
        await page.wait_for_timeout(2000)

        dialog = page.locator('div[role="dialog"]').first
        if await dialog.is_visible():
            # Check input[type="file"] BEFORE clicking photo button
            inp_before = dialog.locator('input[type="file"]')
            print(f"Input file count di dialog SEBELUM klik tombol foto: {await inp_before.count()}")

            # Find and click Photo/Video button INSIDE dialog
            photo_btn = dialog.locator('div[role="button"][aria-label="Foto/video"], div[role="button"]:has-text("Foto/video")').first
            print(f"Photo btn count di dialog: {await photo_btn.count()}")
            if await photo_btn.count() > 0:
                print("Klik tombol Foto/video di dalam dialog...")
                await photo_btn.click()
                await page.wait_for_timeout(2000)

            inp_after = dialog.locator('input[type="file"]')
            print(f"Input file count di dialog SETELAH klik tombol foto: {await inp_after.count()}")

            # Get media images
            images = [os.path.abspath(p) for p in config.find_media_images() if os.path.exists(p)]
            if images and await inp_after.count() > 0:
                inp = inp_after.first
                print(f"Set input files ({len(images)} gambar) pada input file DIALOG...")
                await inp.set_input_files(images)
                await inp.evaluate("""el => {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""")
                await page.wait_for_timeout(4000)

            # Type caption
            tb = dialog.locator('div[role="textbox"][contenteditable="true"]').first
            print("Mengetik caption...")
            await tb.click()
            await tb.press_sequentially("Tes postingan otomatis gambar via FB AutoEngine 3.0", delay=30)
            await page.wait_for_timeout(2000)

            # Inspect Posting button
            post_btn = dialog.locator('div[role="button"][aria-label="Posting"]').first
            print(f"Post btn aria-disabled: {await post_btn.get_attribute('aria-disabled')}")

            if await post_btn.get_attribute("aria-disabled") != "true":
                print("Klik tombol POSTING...")
                await post_btn.click()
                await page.wait_for_timeout(5000)
                print(f"Dialog tertutup? {not await dialog.is_visible()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
