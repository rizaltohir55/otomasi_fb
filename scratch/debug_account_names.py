"""
scratch/debug_account_names.py
Skrip debug mendalam untuk mengekstrak nama asli profil dari facebook.com/profile.php?id=<c_user>
"""
import os
import sys
import json
import re
import asyncio
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from manager.session_manager import discover_all_sessions, update_session_name
from engine.browser import create_stealth_context
from manager.runner import fix_windows_stdout_encoding


async def get_real_name_for_account(p, s_info):
    s_path = s_info["path"]
    c_user = s_info.get("c_user", "")
    curr_name = s_info.get("name", "Unknown")

    print(f"\n=========================================================")
    print(f"👤 Memproses: {curr_name} ({os.path.basename(s_path)})")
    print(f"🆔 c_user  : {c_user}")

    if not c_user:
        print("❌ Cookie c_user tidak ada.")
        return None

    try:
        browser, context = await create_stealth_context(p, session_file=s_path, headless=True)
        page = await context.new_page()

        # Buka profil via profile.php?id=<c_user>
        target_url = f"https://www.facebook.com/profile.php?id={c_user}"
        print(f"🌐 Navigasi ke: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        final_url = page.url
        print(f"📍 Final URL: {final_url}")

        if "login" in final_url.lower() or "checkpoint" in final_url.lower():
            print("❌ Sesi kedaluwarsa atau checkpoint.")
            await browser.close()
            return {"path": s_path, "c_user": c_user, "old_name": curr_name, "real_name": "", "status": "EXPIRED"}

        # 1. Ambil Page Title
        title = await page.title()
        print(f"📄 Page Title: '{title}'")

        clean_title = re.sub(r"^\(\d+\)\s*", "", title).strip()
        clean_title = re.sub(r"\s*[\|-]\s*Facebook$", "", clean_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r"\s*Facebook$", "", clean_title, flags=re.IGNORECASE).strip()

        # 2. Cari semua H1
        h1_texts = []
        h1_loc = page.locator("h1")
        count_h1 = await h1_loc.count()
        for i in range(count_h1):
            t = (await h1_loc.nth(i).text_content() or "").strip()
            if t:
                h1_texts.append(t)
        print(f"🏷️ H1 Elements: {h1_texts}")

        # 3. Cari elemen profil di navbar / sidebar
        # Biasanya tombol akun di kanan atas (aria-label="Profil Anda", "Your profile", atau "Account")
        # atau link profil
        profile_names_found = []
        
        # Coba dari H1 yang paling cocok (biasanya H1 pertama yang bukan "Facebook" atau nama sistem)
        candidate_name = ""
        for h1_t in h1_texts:
            if h1_t.lower() not in ["facebook", "menu", "notifikasi", "notifications", "search", "cari", "pemberitahuan"]:
                if len(h1_t) > 2:
                    candidate_name = h1_t
                    break

        if not candidate_name and clean_title and clean_title.lower() not in ["facebook", "log in", "masuk"]:
            candidate_name = clean_title

        # Coba selector spesifik desktop react FB: svg / span / a di header profile
        if not candidate_name:
            # Selector aria-label atau alt dari foto profil header
            img_avatar = page.locator("svg[aria-label*='profil'], svg[aria-label*='profile'], img[alt*='profil'], img[alt*='profile']")
            if await img_avatar.count() > 0:
                alt_txt = await img_avatar.first.get_attribute("alt") or await img_avatar.first.get_attribute("aria-label") or ""
                print(f"🖼️ Avatar alt/label: {alt_txt}")

        await browser.close()

        if candidate_name:
            print(f"✅ NAMA ASLI BERHASIL DITEMUKAN: '{candidate_name}'")
            return {"path": s_path, "c_user": c_user, "old_name": curr_name, "real_name": candidate_name, "status": "OK"}
        else:
            print("⚠️ Nama tidak terdeteksi.")
            return {"path": s_path, "c_user": c_user, "old_name": curr_name, "real_name": curr_name, "status": "NOT_FOUND"}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"path": s_path, "c_user": c_user, "old_name": curr_name, "real_name": "", "status": "ERROR"}


async def main():
    fix_windows_stdout_encoding()
    sessions = discover_all_sessions()
    print(f"Total sesi: {len(sessions)}")

    async with async_playwright() as p:
        results = []
        for s in sessions:
            res = await get_real_name_for_account(p, s)
            if res:
                results.append(res)

    print("\n" + "=" * 65)
    print("📊 REKAP DIAGNOSTIK NAMA AKUN:")
    print("=" * 65)
    for r in results:
        print(f"{os.path.basename(r['path'])} (c_user: {r['c_user']}) -> Lama: '{r['old_name']}' | Real: '{r['real_name']}' | Status: {r['status']}")


if __name__ == "__main__":
    asyncio.run(main())
