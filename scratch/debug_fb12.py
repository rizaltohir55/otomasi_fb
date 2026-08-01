"""
scratch/debug_fb12.py
Uji coba pengisolasian ketat komposer postingan (bebas dari jebakan comment box feed).
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

        # Function to test strict dialog check
        async def is_modal_composer_active():
            dialogs = page.locator('div[role="dialog"]')
            cnt = await dialogs.count()
            for i in range(cnt):
                d = dialogs.nth(i)
                if await d.is_visible(timeout=300):
                    txt = (await d.inner_text() or "").lower()
                    label = (await d.get_attribute("aria-label") or "").lower()
                    if "memuat" in label or "loading" in label:
                        continue
                    if any(k in txt for k in ["buat postingan", "create post", "tulis sesuatu", "posting"]):
                        return True
            return False

        print(f"Cek komposer modal SEBELUM klik trigger: {await is_modal_composer_active()}")

        # Click trigger
        trigger = page.get_by_role("button", name="Tulis sesuatu...").first
        if await trigger.count() == 0:
            trigger = page.locator('div[role="main"] div[role="button"]:has-text("Tulis sesuatu")').first

        print("Klik trigger komposer...")
        await trigger.click()
        await page.wait_for_timeout(2000)

        print(f"Cek komposer modal SETELAH klik trigger: {await is_modal_composer_active()}")

        # Wait for dialog
        await page.wait_for_selector('div[role="dialog"]:has(div[role="textbox"])', timeout=10000)
        dialog = page.locator('div[role="dialog"]:has(div[role="textbox"])').first

        # Click Photo button
        photo_btn = dialog.locator('div[role="button"][aria-label="Foto/video"], div[role="button"]:has-text("Foto/video")').first
        if await photo_btn.count() > 0:
            print("Klik Foto/video di dalam modal dialog...")
            await photo_btn.click()
            await page.wait_for_timeout(1500)

        inp = dialog.locator('input[type="file"]').first
        images = [os.path.abspath(p) for p in find_media_images() if os.path.exists(p)]
        if images and await inp.count() > 0:
            print("Set input files pada DIALOG input file...")
            await inp.set_input_files(images)
            await inp.evaluate("""el => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""")
            await page.wait_for_timeout(4000)

        tb = dialog.locator('div[role="textbox"][contenteditable="true"]').first
        print("Mengetik caption di DIALOG...")
        await tb.click()
        await tb.press_sequentially("Tes postingan komposer modal bebas comment box feed", delay=30)
        await page.wait_for_timeout(2000)

        post_btn = dialog.locator('div[role="button"][aria-label="Posting"]').first
        print(f"Post btn aria-disabled: {await post_btn.get_attribute('aria-disabled')}")

        if await post_btn.get_attribute("aria-disabled") != "true":
            print("Klik tombol POSTING...")
            await post_btn.click()
            await page.wait_for_timeout(6000)
            print(f"Sukses! Dialog tertutup? {not await dialog.is_visible()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
