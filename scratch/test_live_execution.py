import asyncio
import os
import json
from playwright.async_api import async_playwright

import config
from manager.runner import fix_windows_stdout_encoding
from engine.browser import create_browser_context, verify_login_status
from engine.collector import load_caption, find_media_images, load_groups
from engine.composer import open_group_composer, type_post_caption, attach_images, submit_post
from engine.joiner import check_membership_status

async def main():
    fix_windows_stdout_encoding()
    session_file = os.path.abspath("fb_session.json")
    groups = load_groups()
    if not groups:
        print("No groups found")
        return

    target_group = groups[0]
    caption = load_caption()
    images = find_media_images()

    print(f"Testing live execution on group: {target_group}")

    async with async_playwright() as pw:
        browser, context, page = await create_browser_context(pw, session_file=session_file, headless=True)

        print("Navigating to Facebook Home...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        if not await verify_login_status(page, context):
            print("Login verification failed!")
            await browser.close()
            return

        print("Login verified!")

        # Cek status keanggotaan
        status = await check_membership_status(page, target_group)
        print(f"Group membership status: {status}")

        # Buka komposer
        opened = await open_group_composer(page, target_group)
        print(f"Composer opened: {opened}")

        if opened:
            # Upload gambar jika ada
            if images:
                print(f"Attaching images: {images}")
                await attach_images(page, images[:1])

            # Ketik caption
            print(f"Typing caption: '{caption[:30]}...'")
            await type_post_caption(page, caption)

            # Screenshot sebelum submit
            os.makedirs("scratch", exist_ok=True)
            await page.screenshot(path="scratch/live_before_submit.png")
            print("Screenshot saved to scratch/live_before_submit.png")

        await browser.close()
        print("Live test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
