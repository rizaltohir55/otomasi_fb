"""
scratch/debug_fb8.py
Pengujian submit postingan dengan Playwright native click vs mouse click vs Control+Enter.
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

            print("Mengetik caption...")
            await tb.click()
            await tb.press_sequentially("Tes postingan otomatis via FB AutoEngine 3.0", delay=30)
            await page.wait_for_timeout(1500)

            post_btn = dialog.locator('div[role="button"][aria-label="Posting"]').first
            print(f"Post btn aria-disabled: {await post_btn.get_attribute('aria-disabled')}")

            print("Mencoba Playwright native post_btn.click()...")
            await post_btn.click()
            await page.wait_for_timeout(4000)

            is_open = await dialog.is_visible()
            print(f"Setelah native click, dialog masih terbuka? {is_open}")

            if is_open:
                print("Native click tidak menutup dialog. Mencoba mouse click pada bounding box...")
                box = await post_btn.bounding_box()
                if box:
                    await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    await page.wait_for_timeout(4000)
                    print(f"Setelah mouse click, dialog masih terbuka? {await dialog.is_visible()}")

            if await dialog.is_visible():
                print("Mencoba shortcut Control+Enter pada textbox...")
                await tb.click()
                await page.keyboard.press("Control+Enter")
                await page.wait_for_timeout(4000)
                print(f"Setelah Control+Enter, dialog masih terbuka? {await dialog.is_visible()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
