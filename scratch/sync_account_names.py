"""
scratch/sync_account_names.py
Skrip untuk mengecek 1 per 1 akun Facebook dari file sesi JSON,
mengambil nama asli dari profil Facebook, dan memperbarui metadata & nama file sesi.
"""
import os
import sys
import json
import re
import asyncio
from playwright.async_api import async_playwright

# Tambahkan root project ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from manager.session_manager import discover_all_sessions, update_session_name
from engine.browser import create_stealth_context, get_session_info, verify_login_status
from manager.runner import fix_windows_stdout_encoding


async def extract_real_name_from_fb(page) -> str:
    """
    Buka halaman profil /me dan ambil nama asli dari title, h1, atau elemen navigasi.
    """
    try:
        # Coba navigasi ke profil
        await page.goto("https://www.facebook.com/me", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(4000)

        # 1. Coba dari H1 (biasanya nama utama profil di halaman profil)
        h1_loc = page.locator("h1")
        if await h1_loc.count() > 0:
            for i in range(await h1_loc.count()):
                txt = (await h1_loc.nth(i).text_content() or "").strip()
                if txt and txt.lower() not in ["facebook", "menu", "notifikasi", "notifications", "search", "cari"]:
                    # Abaikan string pendek atau kata sistem
                    if len(txt) > 2 and not re.match(r"^\d+$", txt):
                        return txt

        # 2. Coba dari Page Title
        title = await page.title()
        if title:
            # Bersihkan badge notifikasi seperti "(3) "
            clean_title = re.sub(r"^\(\d+\)\s*", "", title).strip()
            # Bersihkan akhiran "| Facebook" atau "- Facebook"
            clean_title = re.sub(r"\s*[\|-]\s*Facebook$", "", clean_title, flags=re.IGNORECASE).strip()
            clean_title = re.sub(r"\s*Facebook$", "", clean_title, flags=re.IGNORECASE).strip()

            if clean_title and clean_title.lower() not in ["facebook", "log in", "masuk"]:
                return clean_title

        # 3. Coba dari elemen aria-label profil di navbar
        profile_link = page.locator("a[href*='facebook.com/me'], a[aria-label*='Profil'], a[aria-label*='Profile']")
        if await profile_link.count() > 0:
            label = await profile_link.first.get_attribute("aria-label") or ""
            if label:
                clean_label = re.sub(r"(Profil|Profile|Go to profile|Buka profil)\s*", "", label, flags=re.IGNORECASE).strip()
                if clean_label:
                    return clean_label

    except Exception as e:
        print(f"⚠️ Warning saat mengambil nama: {e}")

    return ""


async def process_account(p, s_info):
    s_path = s_info["path"]
    curr_name = s_info.get("name", "Unknown")
    c_user = s_info.get("c_user", "")

    print(f"\n---------------------------------------------------------")
    print(f"👤 Memeriksa Akun: {curr_name}")
    print(f"📁 Path File    : {s_path}")
    print(f"🆔 ID c_user    : {c_user}")

    if not c_user:
        print(f"❌ File sesi tidak valid (Cookie c_user tidak ditemukan).")
        return None

    try:
        browser, context = await create_stealth_context(p, session_file=s_path, headless=True)
        page = await context.new_page()

        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        url_lower = page.url.lower()
        if "login" in url_lower or "checkpoint" in url_lower or "recover" in url_lower:
            print(f"❌ Sesi Expired / Checkpoint! (URL: {page.url})")
            await browser.close()
            return {
                "path": s_path,
                "c_user": c_user,
                "old_name": curr_name,
                "real_name": "",
                "status": "EXPIRED"
            }

        real_name = await extract_real_name_from_fb(page)
        await browser.close()

        if real_name:
            print(f"✨ Nama Asli Terdeteksi dari FB: '{real_name}'")
            return {
                "path": s_path,
                "c_user": c_user,
                "old_name": curr_name,
                "real_name": real_name,
                "status": "OK"
            }
        else:
            print(f"⚠️ Tidak dapat mendeteksi nama profil secara otomatis.")
            return {
                "path": s_path,
                "c_user": c_user,
                "old_name": curr_name,
                "real_name": curr_name,
                "status": "NAME_NOT_FOUND"
            }

    except Exception as e:
        print(f"❌ Error saat memproses {s_path}: {e}")
        return {
            "path": s_path,
            "c_user": c_user,
            "old_name": curr_name,
            "real_name": "",
            "status": "ERROR"
        }


async def main():
    fix_windows_stdout_encoding()
    print("=========================================================")
    print("🔍 VERIFIKASI & PENESUAIAN NAMA AKUN FB DENGAN NAMA ASLI")
    print("=========================================================")

    sessions = discover_all_sessions()
    if not sessions:
        print("❌ Tidak ada sesi yang ditemukan.")
        return

    print(f"📋 Ditemukan total {len(sessions)} file sesi.\n")

    results = []
    async with async_playwright() as p:
        for idx, s in enumerate(sessions, 1):
            print(f"\n[Akun {idx}/{len(sessions)}]")
            res = await process_account(p, s)
            if res:
                results.append(res)

    print("\n" + "=" * 65)
    print("📊 REKAPITULASI PEMERIKSAAN NAMA AKUN:")
    print("=" * 65)

    updated_count = 0
    for res in results:
        status = res["status"]
        s_path = res["path"]
        old_name = res["old_name"]
        real_name = res["real_name"]
        c_user = res["c_user"]

        print(f"\n📁 File: {os.path.basename(s_path)} (ID: {c_user})")
        print(f"   Nama lama : {old_name}")

        if status == "OK" and real_name:
            print(f"   Nama asli : {real_name}")
            # Update meta name di file json
            success = update_session_name(s_path, real_name)
            if success:
                print(f"   ✅ Metadata nama berhasil diperbarui di file JSON!")
                updated_count += 1
            else:
                print(f"   ❌ Gagal memperbarui metadata file JSON.")

            # Opsional: Jika ingin mengganti nama file agar rapi (cth: fb_session_<nama_asli>.json)
            # Biarkan file root fb_session.json jika itu akun utama, atau rename secara aman.
            safe_name_tag = "".join([c if c.isalnum() else "_" for c in real_name]).lower()
            safe_name_tag = re.sub(r"_+", "_", safe_name_tag).strip("_")

            dir_name = os.path.dirname(s_path)
            old_base = os.path.basename(s_path)

            if old_base != "fb_session.json" and safe_name_tag:
                new_base = f"fb_session_{safe_name_tag}.json"
                new_path = os.path.join(dir_name, new_base)
                if s_path != new_path and not os.path.exists(new_path):
                    try:
                        os.rename(s_path, new_path)
                        print(f"   🏷️ File di-rename menjadi: {new_base}")
                    except Exception as e:
                        print(f"   ⚠️ Gagal rename file: {e}")
                elif s_path != new_path and os.path.exists(new_path):
                    print(f"   ℹ️ File {new_base} sudah ada, mempertahankan path saat ini.")
        elif status == "EXPIRED":
            print(f"   ❌ Status: EXPIRED / CHECKPOINT (Silakan login ulang akun ini)")
        else:
            print(f"   ⚠️ Status: {status}")

    print("\n" + "=" * 65)
    print(f"🎉 Selesai! Total {updated_count} akun berhasil disesuaikan ke nama asli.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
