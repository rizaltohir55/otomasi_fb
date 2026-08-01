"""
scratch/debug_fb7.py
Uji coba pengetikan caption & pergeseran status tombol POSTING (disabled -> enabled).
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
            tb = dialog.locator('div[role="textbox"][contenteditable="true"]').first
            print(f"Textbox count: {await tb.count()}")

            # Check post button status BEFORE typing
            post_btn = dialog.locator('div[role="button"][aria-label="Posting"], div[role="button"]:has-text("Posting")').first
            print("Status tombol POSTING SEBELUM diketik:")
            print(f"  disabled={await post_btn.get_attribute('aria-disabled')}")

            # Type caption
            print("\nMengetik caption 'Tes postingan otomatis'...")
            await tb.click()
            await tb.press_sequentially("Tes postingan otomatis via FB AutoEngine", delay=30)
            await page.wait_for_timeout(2000)

            # Check post button status AFTER typing
            print("Status tombol POSTING SETELAH diketik:")
            print(f"  disabled={await post_btn.get_attribute('aria-disabled')}")

            # Try clicking Post button
            print("\nMencoba klik tombol POSTING...")
            if await post_btn.get_attribute('aria-disabled') != "true":
                print("Tombol POSTING aktif! Melakukan klik...")
                # Test click methods
                await post_btn.click()
                print("Tunggu 5 detik melihat apakah dialog tertutup...")
                await page.wait_for_timeout(5000)
                print(f"Dialog masih visible? {await dialog.is_visible()}")
            else:
                print("Tombol POSTING masih disabled!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
