import asyncio
import os
import sys
sys.path.insert(0, ".")
from playwright.async_api import async_playwright

from engine.browser import create_stealth_context
from engine.collector import load_groups

async def debug_account_posting(session_file: str):
    groups = load_groups()
    test_group = groups[0] if groups else "https://www.facebook.com/groups/feed/"
    print(f" Menguji akun: {session_file} pada grup: {test_group}")

    async with async_playwright() as p:
        browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
        page = await context.new_page()
        try:
            print(" Navigasi ke halaman grup...")
            await page.goto(test_group, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            # Simpan screenshot 1: Halaman Utama Grup
            os.makedirs("scratch/screenshots", exist_ok=True)
            await page.screenshot(path="scratch/screenshots/1_group_feed.png")
            print(" Screenshot 1 tersimpan: scratch/screenshots/1_group_feed.png")

            # Cek keberadaan tombol composer "Write something..." / "Tulis sesuatu..."
            composer_triggers = page.locator(
                'div[role="button"]:has-text("Write something"), '
                'div[role="button"]:has-text("Tulis sesuatu"), '
                'span:has-text("Write something"), '
                'span:has-text("Tulis sesuatu"), '
                'div[aria-label*="Create a public post"], '
                'div[aria-label*="Buat postingan publik"]'
            )

            count = await composer_triggers.count()
            print(f" Jumlah elemen pemicu composer ditemukan: {count}")

            if count > 0:
                print(" Mengklik pemicu composer...")
                await composer_triggers.first.click(timeout=5000)
                await page.wait_for_timeout(3000)

                # Simpan screenshot 2: Setelah Klik Composer
                await page.screenshot(path="scratch/screenshots/2_after_click_composer.png")
                print(" Screenshot 2 tersimpan: scratch/screenshots/2_after_click_composer.png")
            else:
                print(" Tombol composer TIDAK DITEMUKAN / DIBATASI di halaman ini!")

            # Cek dialog modal atau alert di halaman
            dialogs = page.locator('div[role="dialog"], div[role="alertdialog"], div[role="alert"]')
            d_count = await dialogs.count()
            print(f" Jumlah modal/dialog/alert ditemukan: {d_count}")
            for i in range(d_count):
                txt = await dialogs.nth(i).inner_text()
                print(f"   --- Dialog #{i+1} Text ---")
                print(txt[:300])

            # Cek teks body lengkap untuk kata kunci pembatasan
            body_text = await page.locator("body").inner_text()
            print("\n Mengutip beberapa baris awal body halaman:")
            lines = [line.strip() for line in body_text.split("\n") if line.strip()]
            for line in lines[:20]:
                print("  >", line)

        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_account_posting("fb_session.json"))
