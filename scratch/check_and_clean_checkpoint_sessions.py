"""
scratch/check_and_clean_checkpoint_sessions.py
Script Pemindai & Pembersih Sesi Akun Facebook yang Ter-checkpoint / Kedaluwarsa.
"""
import os
import sys
import asyncio
from playwright.async_api import async_playwright

# Tambahkan root project ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from manager.session_manager import discover_all_sessions, delete_session_file
from engine.browser import create_stealth_context, get_session_info, verify_login_status
from manager.runner import fix_windows_stdout_encoding


async def check_session_live(session_path: str) -> dict:
    info = get_session_info(session_path)
    res = {
        "path": session_path,
        "name": info.get("name", "Unknown"),
        "c_user": info.get("c_user", ""),
        "status": "CHECKING",
        "reason": ""
    }

    if not info.get("c_user"):
        res["status"] = "INVALID"
        res["reason"] = "Cookie c_user tidak ditemukan di file JSON"
        return res

    async with async_playwright() as p:
        try:
            browser, context = await create_stealth_context(p, session_file=session_path, headless=True)
            page = await context.new_page()

            await page.goto("https://www.facebook.com/", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            url_lower = page.url.lower()
            if "checkpoint" in url_lower or "login" in url_lower or "recover" in url_lower:
                res["status"] = "CHECKPOINT_EXPIRED"
                res["reason"] = f"Ter-redirect ke URL: {page.url}"
                await browser.close()
                return res

            is_active = await verify_login_status(page)
            if is_active:
                res["status"] = "ACTIVE"
                res["reason"] = "Sesi terverifikasi aktif & ter-login"
            else:
                res["status"] = "CHECKPOINT_EXPIRED"
                res["reason"] = f"Elemen login form terdeteksi / tidak ter-login (URL: {page.url})"

            await browser.close()
        except Exception as e:
            res["status"] = "ERROR"
            res["reason"] = str(e)

    return res


async def main():
    fix_windows_stdout_encoding()
    print("=================================================================")
    print("🔍 MEMINDAI AKUN FACEBOOK DENGAN STATUS CHECKPOINT / EXPIRED...")
    print("=================================================================")

    sessions = discover_all_sessions()
    if not sessions:
        print("❌ Tidak ada sesi yang tersimpan.")
        return

    print(f"📋 Ditemukan total {len(sessions)} file sesi untuk diperiksa.\n")

    checkpoint_expired_list = []
    active_list = []

    for idx, s in enumerate(sessions, 1):
        s_path = s["path"]
        s_name = s.get("name", os.path.basename(s_path))
        print(f"[{idx}/{len(sessions)}] Memeriksa: {s_name} ({os.path.basename(s_path)})...", end=" ", flush=True)

        res = await check_session_live(s_path)
        if res["status"] in ["CHECKPOINT_EXPIRED", "INVALID"]:
            print(f"❌ CHECKPOINT / EXPIRED ({res['reason']})")
            checkpoint_expired_list.append(res)
        else:
            print(f"✅ AKTIF ({res['reason']})")
            active_list.append(res)

    print("\n" + "=" * 65)
    print("📊 HASIL PEMINDAIAN SESI AKUN:")
    print("=" * 65)
    print(f"✅ Akun Aktif        : {len(active_list)}")
    print(f"❌ Akun Checkpoint/Expired: {len(checkpoint_expired_list)}")
    print("=" * 65)

    if checkpoint_expired_list:
        print("\n🗑️ MENGHAPUS / MEMBACKUP SESI AKUN CHECKPOINT & EXPIRED:")
        for r in checkpoint_expired_list:
            delete_session_file(r["path"], permanent=False)
            print(f"   📦 {r['name']} ({os.path.basename(r['path'])}) -> Dinonaktifkan ke .bak")
        print("\n🎉 Pembersihan sesi checkpoint selesai!")
    else:
        print("\n🎉 Tidak ada akun checkpoint / expired yang perlu dihapus.")


if __name__ == "__main__":
    asyncio.run(main())
