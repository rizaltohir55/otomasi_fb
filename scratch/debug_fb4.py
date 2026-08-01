"""
scratch/debug_fb4.py
Inspeksi detail tombol header setelah mengklik Join (Bergabung).
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

        # Print all action buttons in the group header
        header_btns = await page.evaluate("""
            () => {
                const main = document.querySelector('div[role="main"]');
                if (!main) return [];
                const btns = Array.from(main.querySelectorAll('div[role="button"], button'));
                return btns.map(b => ({
                    label: b.getAttribute('aria-label') || '',
                    text: (b.innerText || '').trim(),
                    disabled: b.getAttribute('aria-disabled')
                })).filter(b => b.label || b.text);
            }
        """)
        print("--- MAIN BUTTONS BEFORE JOIN ---")
        for b in header_btns:
            print(f"  label='{b['label']}' text='{b['text']}' disabled={b['disabled']}")

        join_btn = page.get_by_role("button", name="Bergabung")
        if await join_btn.count() > 0 and await join_btn.first.is_visible():
            print("\nKlik Bergabung...")
            await join_btn.first.click()
            await page.wait_for_timeout(4000)

            header_btns_after = await page.evaluate("""
                () => {
                    const main = document.querySelector('div[role="main"]');
                    if (!main) return [];
                    const btns = Array.from(main.querySelectorAll('div[role="button"], button'));
                    return btns.map(b => ({
                        label: b.getAttribute('aria-label') || '',
                        text: (b.innerText || '').trim(),
                        disabled: b.getAttribute('aria-disabled')
                    })).filter(b => b.label || b.text);
                }
            """)
            print("\n--- MAIN BUTTONS AFTER JOIN ---")
            for b in header_btns_after:
                print(f"  label='{b['label']}' text='{b['text']}' disabled={b['disabled']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
