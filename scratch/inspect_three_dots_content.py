"""
scratch/inspect_three_dots_content.py
Script untuk menginspeksi elemen di dalam menu 3-titik postingan milik akun.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from playwright.async_api import async_playwright
from utils.browser import setup_browser, login

async def main():
    session_file = os.path.abspath("session/fb_session_key_andromeda.json")
    if not os.path.exists(session_file):
        session_file = os.path.abspath("session/fb_session_fendi.json")

    print(f"🚀 Inspecting 3-dots for: {session_file}")

    async with async_playwright() as playwright:
        browser, context, page = await setup_browser(playwright, session_file=session_file)

        if not await login(page, context, session_file=session_file):
            print("❌ Login failed")
            await browser.close()
            return

        test_group = "https://m.facebook.com/groups/697937093629189/"
        await page.goto(test_group, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Cari tombol 3 titik yang berakhiran nama akun (More options for ...)
        btn = page.locator('div[role="button"][aria-label*="More options for"], div[role="button"][aria-label*="Opsi lainnya untuk"]').first

        if await btn.count() > 0:
            aria = await btn.get_attribute("aria-label")
            print(f"🎯 Clicking button: '{aria}'")
            await btn.click()
            await page.wait_for_timeout(2000)

            # Inspeksi semua elemen HTML di modal drawer
            info = await page.evaluate("""
                () => {
                    const res = [];
                    const all = Array.from(document.querySelectorAll('body *'));
                    for (const el of all) {
                        const text = (el.innerText || el.textContent || '').trim();
                        const href = el.href || el.getAttribute('href') || '';
                        const aria = el.getAttribute('aria-label') || '';
                        const role = el.getAttribute('role') || '';
                        if (href || text.includes('Copy') || text.includes('Salin') || text.includes('View') || text.includes('Lihat') || text.includes('link') || text.includes('tautan')) {
                            res.push({ tag: el.tagName, text, href, aria, role, outerHTML: el.outerHTML.substring(0, 150) });
                        }
                    }
                    return res;
                }
            """)

            print(f"\nFound {len(info)} menu elements:")
            for item in info[:15]:
                print(item)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
