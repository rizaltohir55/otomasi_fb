import asyncio
import os
import json
from playwright.async_api import async_playwright

from manager.runner import fix_windows_stdout_encoding
from engine.collector import load_groups, find_media_images, load_caption
from engine.browser import create_browser_context, verify_login_status
from engine.composer import open_group_composer, type_post_caption, attach_images, submit_post, is_composer_active
from engine.joiner import check_membership_status, join_group

async def handle_anonymous_post_modal(page):
    """Juga tangani jika modal 'Postingan anonim' muncul."""
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        for i in range(cnt):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=300):
                continue
            text = (await d.inner_text()).lower()
            if "postingan anonim" in text or "anonymous post" in text:
                print("   ℹ️ Modal 'Postingan anonim' terdeteksi. Menekan 'Buat Postingan Anonim'...")
                btn = d.locator(
                    'div[role="button"]:has-text("Buat Postingan Anonim"), '
                    'div[role="button"]:has-text("Create Anonymous Post"), '
                    'button:has-text("Buat Postingan Anonim"), '
                    'button:has-text("Create Anonymous Post")'
                ).first
                if await btn.count() > 0 and await btn.is_visible(timeout=800):
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Modal 'Postingan anonim' dikonfirmasi!")
                    return True
    except Exception:
        pass
    return False

async def main():
    fix_windows_stdout_encoding()
    session_file = os.path.abspath("fb_session.json")
    if not os.path.exists(session_file):
        print("fb_session.json not found")
        return

    groups = load_groups()
    if len(groups) < 10:
        print(f"Only found {len(groups)} groups, need 10")
        return

    target_groups = groups[:10]
    caption = load_caption()
    image_paths = find_media_images()

    print(f"\n=======================================================")
    print(f"🚀 SIMULASI REAL AUTOMATION: 10 GRUP FACEBOOK")
    print(f"=======================================================\n")

    results = []

    async with async_playwright() as pw:
        browser, context, page = await create_browser_context(pw, session_file=session_file, headless=True)

        print("🌐 Verifikasi login sesi...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        if not await verify_login_status(page, context):
            print("❌ Sesi belum login!")
            await browser.close()
            return

        print("✅ Status login terverifikasi aktif!")

        for idx, group_url in enumerate(target_groups, 1):
            print(f"\n-------------------------------------------------------")
            print(f"[{idx}/10] Target Grup: {group_url}")
            print(f"-------------------------------------------------------")

            group_res = {"url": group_url, "status": "FAILED", "note": ""}

            try:
                # 1. Cek keanggotaan
                mem_status = await check_membership_status(page, group_url)
                print(f"   📊 Status keanggotaan: {mem_status}")

                if mem_status == "UNJOINED":
                    print("   ℹ️ Belum bergabung. Mencoba auto-join...")
                    j_res = await join_group(page, group_url, auto_answer=True)
                    if j_res not in ("JOINED", "ALREADY_JOINED"):
                        print(f"   ⚠️ Auto join status: {j_res}. Skip posting.")
                        group_res["note"] = f"Join status: {j_res}"
                        results.append(group_res)
                        continue
                elif mem_status == "PENDING":
                    print("   ⏳ Permintaan keanggotaan pending admin approval. Skip posting.")
                    group_res["status"] = "PENDING_APPROVAL"
                    group_res["note"] = "Pending admin approval"
                    results.append(group_res)
                    continue

                # 2. Buka komposer
                opened = await open_group_composer(page, group_url)
                # Jikalau ada modal anonim
                await handle_anonymous_post_modal(page)

                if not await is_composer_active(page):
                    opened = await open_group_composer(page, group_url)

                if not opened and not await is_composer_active(page):
                    print("   ❌ Gagal membuka modal komposer.")
                    group_res["note"] = "Composer open failed"
                    results.append(group_res)
                    continue

                # 3. Upload gambar (jika ada)
                if image_paths:
                    await attach_images(page, image_paths[:1])

                # 4. Ketik caption
                caption_ok = await type_post_caption(page, caption)
                if not caption_ok:
                    print("   ❌ Caption gagal diketik.")
                    group_res["note"] = "Caption typing failed"
                    results.append(group_res)
                    continue

                # 5. Submit postingan
                posted = await submit_post(page)
                if posted:
                    print(f"   🎉 POSTINGAN SUKSES DI GRUP {idx}!")
                    group_res["status"] = "SUCCESS"
                else:
                    print(f"   ❌ POSTINGAN GAGAL DI GRUP {idx}.")
                    group_res["note"] = "Submit failed"

            except Exception as e:
                print(f"   ⚠️ Error pada grup {group_url}: {e}")
                group_res["note"] = str(e)

            results.append(group_res)
            await page.wait_for_timeout(3000)

        await browser.close()

    print(f"\n=======================================================")
    print(f"📊 LAPORAN SIMULASI 10 GRUP")
    print(f"=======================================================")
    success_cnt = sum(1 for r in results if r["status"] == "SUCCESS")
    pending_cnt = sum(1 for r in results if r["status"] == "PENDING_APPROVAL")
    failed_cnt  = sum(1 for r in results if r["status"] == "FAILED")

    for i, r in enumerate(results, 1):
        print(f"  [{i:02d}] {r['status']:<16} | {r['url']} | {r['note']}")

    print(f"\nTOTAL: Success={success_cnt}, Pending={pending_cnt}, Failed={failed_cnt}")

if __name__ == "__main__":
    asyncio.run(main())
