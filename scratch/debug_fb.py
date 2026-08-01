"""
scratch/debug_fb.py
Skrip diagnosa mendalam untuk memeriksa elemen komposer Facebook Desktop.
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
        await page.wait_for_timeout(4000)

        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Dump main buttons
        buttons = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('div[role="button"], button, span'));
                return btns.map(b => ({
                    tag: b.tagName,
                    role: b.getAttribute('role'),
                    label: b.getAttribute('aria-label') || '',
                    text: (b.innerText || '').trim().substring(0, 50),
                    visible: b.offsetParent !== null
                })).filter(b => b.visible && (b.label || b.text));
            }
        """)
        print("\n--- BUTTONS DI HALAMAN GRUP ---")
        for b in buttons[:30]:
            print(f"  [{b['tag']}] role={b['role']} label='{b['label']}' text='{b['text']}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
