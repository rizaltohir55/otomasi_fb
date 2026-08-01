"""
scratch/debug_fb6.py
Inspeksi elemen tombol Bergabung secara mendalam.
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

        # Dump details of all buttons containing "Bergabung"
        info = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                return btns.map(b => ({
                    html: b.outerHTML.substring(0, 300),
                    label: b.getAttribute('aria-label'),
                    text: b.innerText,
                    visible: b.offsetParent !== null,
                    rect: b.getBoundingClientRect()
                })).filter(b => (b.label && b.label.includes("Bergabung")) || (b.text && b.text.includes("Bergabung")));
            }
        """)
        print("--- TOMBOL BERGABUNG DI HALAMAN ---")
        for i, b in enumerate(info):
            print(f"[{i+1}] visible={b['visible']} label='{b['label']}' text='{b['text']}' rect={b['rect']}\nHTML: {b['html']}\n")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
