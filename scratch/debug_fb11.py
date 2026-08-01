"""
scratch/debug_fb11.py
Uji coba pengungsian loading dialog dan perolehan composer dialog sejati.
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

        # Open composer trigger
        trigger = page.get_by_role("button", name="Tulis sesuatu...").first
        if await trigger.count() == 0:
            trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu")').first

        print("Klik trigger komposer...")
        await trigger.click()

        # Wait for real composer dialog
        print("Menunggu dialog komposer sejati (bukan loading)...")
        await page.wait_for_selector('div[role="dialog"]:has(div[role="textbox"])', timeout=10000)
        dialog = page.locator('div[role="dialog"]:has(div[role="textbox"])').first

        print("✅ Dialog komposer sejati terdeteksi!")

        # Dump elements in real dialog
        dialog_btns = await dialog.evaluate("""
            (d) => {
                const btns = Array.from(d.querySelectorAll('div[role="button"], button'));
                return btns.map(b => ({
                    label: b.getAttribute('aria-label') || '',
                    text: (b.innerText || '').trim()
                })).filter(b => b.label || b.text);
            }
        """)
        print("\n--- BUTTONS DI COMPOSER DIALOG SEJATI ---")
        for b in dialog_btns:
            print(f"  label='{b['label']}' text='{b['text']}'")

        # Find Photo/video button in dialog
        photo_btn = dialog.locator('div[role="button"][aria-label="Foto/video"], div[role="button"]:has-text("Foto/video")').first
        print(f"\nPhoto/video button count di dialog sejati: {await photo_btn.count()}")

        if await photo_btn.count() > 0:
            print("Klik tombol Foto/video...")
            await photo_btn.click()
            await page.wait_for_timeout(2000)

            # Check input[type="file"] INSIDE dialog
            inp_file = dialog.locator('input[type="file"]').first
            print(f"Input file count di dialog sejati: {await inp_file.count()}")

            images = [os.path.abspath(p) for p in find_media_images() if os.path.exists(p)]
            if images and await inp_file.count() > 0:
                print(f"Set input files ({len(images)} gambar) pada input file DIALOG SEJATI...")
                await inp_file.set_input_files(images)
                await inp_file.evaluate("""el => {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""")
                await page.wait_for_timeout(4000)

            tb = dialog.locator('div[role="textbox"][contenteditable="true"]').first
            print("Mengetik caption...")
            await tb.click()
            await tb.press_sequentially("Tes postingan gambar & teks via FB AutoEngine 3.0", delay=30)
            await page.wait_for_timeout(2000)

            post_btn = dialog.locator('div[role="button"][aria-label="Posting"]').first
            print(f"Post btn aria-disabled: {await post_btn.get_attribute('aria-disabled')}")

            if await post_btn.get_attribute("aria-disabled") != "true":
                print("Melakukan CDP click pada tombol POSTING...")
                await post_btn.click()
                await page.wait_for_timeout(6000)
                print(f"Post sukses, dialog tertutup? {not await dialog.is_visible()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
