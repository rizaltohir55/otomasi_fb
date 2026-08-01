import asyncio
import os
import json
from playwright.async_api import async_playwright

from manager.runner import fix_windows_stdout_encoding
from engine.collector import load_groups, find_media_images, load_caption
from engine.browser import create_browser_context, verify_login_status
from engine.composer import open_group_composer, type_post_caption, attach_images, submit_post, is_composer_active, handle_anonymous_post_modal
from engine.joiner import check_membership_status, join_group

async def main():
    fix_windows_stdout_encoding()
    session_file = os.path.abspath("fb_session.json")
    groups = load_groups()
    caption = load_caption()
    image_paths = find_media_images()

    print(f"\n=======================================================")
    print(f"🚀 PENCARIAN & SIMULASI REAL AUTOMATION: 10 GRUP JOINED")
    print(f"=======================================================\n")

    results = []
    processed_count = 0

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

        for idx, group_url in enumerate(groups, 1):
            if processed_count >= 10:
                break

            group_res = {"url": group_url, "status": "FAILED", "note": ""}

            try:
                # 1. Cek keanggotaan
                mem_status = await check_membership_status(page, group_url)

                if mem_status == "UNJOINED":
                    print(f"[{idx}] {group_url} -> UNJOINED. Mencoba join...")
                    j_res = await join_group(page, group_url, auto_answer=True)
                    if j_res not in ("JOINED", "ALREADY_JOINED"):
                        continue
                    mem_status = "JOINED"
                elif mem_status == "PENDING":
                    # Skip pending groups to find joined ones
                    continue

                processed_count += 1
                print(f"\n-------------------------------------------------------")
                print(f"[{processed_count}/10] Memproses Grup JOINED: {group_url}")
                print(f"-------------------------------------------------------")

                # 2. Buka komposer
                opened = await open_group_composer(page, group_url)
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
                    print(f"   🎉 POSTINGAN SUKSES DI GRUP JOINED [{processed_count}/10]!")
                    group_res["status"] = "SUCCESS"
                else:
                    print(f"   ❌ POSTINGAN GAGAL DI GRUP [{processed_count}/10].")
                    group_res["note"] = "Submit failed"

            except Exception as e:
                print(f"   ⚠️ Error pada grup {group_url}: {e}")
                group_res["note"] = str(e)

            results.append(group_res)
            await page.wait_for_timeout(3000)

        await browser.close()

    print(f"\n=======================================================")
    print(f"📊 LAPORAN SIMULASI 10 GRUP JOINED")
    print(f"=======================================================")
    success_cnt = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_cnt  = sum(1 for r in results if r["status"] == "FAILED")

    for i, r in enumerate(results, 1):
        print(f"  [{i:02d}] {r['status']:<16} | {r['url']} | {r['note']}")

    print(f"\nTOTAL: Success={success_cnt}, Failed={failed_cnt}")

if __name__ == "__main__":
    asyncio.run(main())
