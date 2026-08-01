import asyncio
import json
import os
from playwright.async_api import async_playwright

from manager.runner import fix_windows_stdout_encoding
from engine.collector import load_groups, find_media_images, load_caption
from engine.composer import open_group_composer, type_post_caption, attach_images, submit_post, is_composer_active

async def main():
    fix_windows_stdout_encoding()
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
        target_group = "https://facebook.com/groups/697937093629189/"
        print(f"Navigating to Group: {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        opened = await open_group_composer(page, target_group)
        print(f"Composer opened: {opened}")

        images = find_media_images()
        if images:
            print(f"Attaching images: {images}")
            await attach_images(page, images[:1])

        caption = load_caption()
        print("Typing caption...")
        await type_post_caption(page, caption)

        print("Submitting post...")
        result = await submit_post(page)
        print(f"Submit post result: {result}")

        # Final check: is composer active?
        active = await is_composer_active(page)
        print(f"Is composer still active? {active}")

        os.makedirs("scratch", exist_ok=True)
        await page.screenshot(path="scratch/after_submit_fix.png")
        print("Saved screenshot to scratch/after_submit_fix.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
