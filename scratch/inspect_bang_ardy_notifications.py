import asyncio
import os
import sys
sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from engine.browser import create_stealth_context

async def inspect_bang_ardy_details():
    session_file = "fb_session.json"
    print(f"=== INSPEKSI DETIL PEMBATASAN UNTUK BANG ARDY ({session_file}) ===")

    async with async_playwright() as p:
        browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
        page = await context.new_page()

        os.makedirs("scratch/screenshots", exist_ok=True)

        try:
            # 1. Cek Halaman Notifikasi FB (Facebook Notifications)
            print("\n1. Membuka https://www.facebook.com/notifications ...")
            await page.goto("https://www.facebook.com/notifications", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="scratch/screenshots/ardy_notifications.png")

            notif_text = await page.locator("body").inner_text()
            print("   --- Kata kunci pembatasan di Notifikasi: ---")
            lines = [line.strip() for line in notif_text.split("\n") if line.strip()]
            for line in lines[:30]:
                if any(kw in line.lower() for kw in ["dibatasi", "restricted", "grup", "group", "block", "blokir", "peringatan", "warning", "standar komunitas"]):
                    print("   [NOTIF] >", line)

            # 2. Cek Halaman Support Inbox / Pelanggaran (Facebook Support Inbox)
            print("\n2. Membuka https://www.facebook.com/support ...")
            await page.goto("https://www.facebook.com/support", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="scratch/screenshots/ardy_support_inbox.png")

            support_text = await page.locator("body").inner_text()
            print("   --- Teks Halaman Support Inbox: ---")
            lines_supp = [line.strip() for line in support_text.split("\n") if line.strip()]
            for line in lines_supp[:30]:
                print("   [SUPPORT] >", line)

            # 3. Uji Pengetikan & Cek Tombol "Posting" di Grup
            from engine.collector import load_groups
            groups = load_groups()
            test_group = groups[0] if groups else "https://www.facebook.com/groups/feed/"

            print(f"\n3. Membuka Grup Uji ({test_group}) & Mengetik Teks di Komposer...")
            await page.goto(test_group, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)

            composer_trig = page.locator(
                'div[role="button"]:has-text("Write something"), '
                'div[role="button"]:has-text("Tulis sesuatu"), '
                'span:has-text("Write something"), '
                'span:has-text("Tulis sesuatu")'
            )

            if await composer_trig.count() > 0:
                await composer_trig.first.click(timeout=5000)
                await page.wait_for_timeout(2000)

                # Ketik teks uji di komposer
                editor = page.locator('div[role="textbox"], div[contenteditable="true"]')
                if await editor.count() > 0:
                    await editor.first.click()
                    await editor.first.fill("Tes Otomasi")
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path="scratch/screenshots/ardy_composer_filled.png")
                    print("   Teks berhasil diketik di komposer.")

                # Cek atribut/status tombol "Posting"
                post_btn = page.locator('div[role="button"][aria-label="Posting"], div[role="button"][aria-label="Post"]')
                if await post_btn.count() > 0:
                    is_disabled = await post_btn.first.get_attribute("aria-disabled")
                    print(f"   Status Tombol Posting aria-disabled = {is_disabled}")

                # Cek jika ada popup dialog alert yang muncul saat komposer aktif
                dialogs = page.locator('div[role="dialog"], div[role="alertdialog"], div[role="alert"]')
                for idx in range(await dialogs.count()):
                    d_txt = await dialogs.nth(idx).inner_text()
                    print(f"   [DIALOG #{idx+1}]", d_txt[:200].replace("\n", " "))

        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_bang_ardy_details())
