import asyncio
import json
import os
from playwright.async_api import async_playwright
from engine.collector import load_groups, find_media_images

async def main():
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

        groups = load_groups()
        target_group = groups[0]
        print(f"Navigating to Group: {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Click trigger button
        trigger = page.locator('div[role="button"]:has-text("Tulis sesuatu...")').first
        if await trigger.count() > 0:
            print("Clicking 'Tulis sesuatu...' trigger...")
            await trigger.click()
            await page.wait_for_timeout(3000)

        # Get dialog
        dialog = page.locator('div[role="dialog"]').first
        textbox = dialog.locator('div[role="textbox"][contenteditable="true"]').first

        print("Typing test text into textbox...")
        await textbox.click()
        await textbox.press_sequentially("Tes Otomasi Facebook UI UX Real 2026", delay=50)
        await page.wait_for_timeout(1500)

        # Attach image if available
        media_imgs = find_media_images()
        if media_imgs:
            print(f"Attaching image: {media_imgs[0]}")
            file_input = dialog.locator('input[type="file"]').first
            if await file_input.count() > 0:
                await file_input.set_input_files([os.path.abspath(media_imgs[0])])
                await page.wait_for_timeout(3000)

        # Check Post button status
        post_btn = dialog.locator('div[role="button"][aria-label="Posting"], div[role="button"]:has-text("Posting")').first
        is_disabled = await post_btn.get_attribute("aria-disabled")
        print(f"Post Button aria-disabled = {is_disabled}")

        await page.screenshot(path="scratch/composer_filled.png")
        print("Filled composer screenshot saved to scratch/composer_filled.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
