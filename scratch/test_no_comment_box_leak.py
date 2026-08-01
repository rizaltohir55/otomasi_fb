import asyncio
import os
import json
from playwright.async_api import async_playwright

from manager.runner import fix_windows_stdout_encoding
from engine.collector import load_groups
from engine.browser import create_browser_context
from engine.dom_analyzer import find_caption_textbox, get_active_composer_dialog
from engine.composer import type_post_caption, is_composer_active

async def main():
    fix_windows_stdout_encoding()
    session_file = os.path.abspath("fb_session.json")
    groups = load_groups()

    async with async_playwright() as pw:
        browser, context, page = await create_browser_context(pw, session_file=session_file, headless=True)

        target_group = groups[0]
        print(f"Navigating to group feed (WITHOUT opening composer): {target_group}")
        await page.goto(target_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Check count of comment boxes on feed
        cmt_count = await page.locator('div[role="textbox"][contenteditable="true"]').count()
        print(f"Total visible contenteditable textboxes on feed (including comment boxes): {cmt_count}")

        # Check if is_composer_active detects active composer
        active = await is_composer_active(page)
        print(f"Is composer active on feed? {active}")
        assert active == False, "is_composer_active must be False on unopened feed!"

        # Check if find_caption_textbox finds any post caption box
        tb = await find_caption_textbox(page)
        print(f"find_caption_textbox result on unopened feed: {tb}")
        assert tb is None, "find_caption_textbox MUST BE None when no composer dialog is open!"

        # Try type_post_caption on unopened feed
        typed = await type_post_caption(page, "TEST CONTENT SHOULD NOT BE TYPED")
        print(f"type_post_caption result on unopened feed: {typed}")
        assert typed == False, "type_post_caption MUST BE False when no composer dialog is open!"

        print("\n✅ VERIFIKASI KEAMANAN SUKSES: Bot 100% KEBAL dari kebocoran komentar feed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
