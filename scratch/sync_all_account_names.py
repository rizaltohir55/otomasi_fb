"""
scratch/sync_all_account_names.py
Sinkronisasi & Penyesuaian Nama Akun Facebook ke Nama Asli.
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


async def extract_account_real_name(page, c_user: str) -> str:
    """
    Ekstrak nama asli akun dari DOM Facebook (beranda & profil).
    """
    js = f"""() => {{
        const c_user = "{c_user}";
        
        // 1. Direct link matching profile.php?id=<c_user>
        const profileLinks = Array.from(document.querySelectorAll(`a[href*="profile.php?id=${{c_user}}"]`));
        for (const a of profileLinks) {{
            const txt = (a.innerText || "").trim();
            if (txt && !txt.toLowerCase().includes("facebook") && !txt.toLowerCase().includes("linimasa")) {{
                return txt;
            }}
            const aria = a.getAttribute("aria-label") || "";
            if (aria) {{
                let clean = aria.replace(/^(Linimasa|Timeline of)\s*/i, "").replace(/\s*'s timeline$/i, "").trim();
                if (clean) return clean;
            }}
        }}

        // 2. Link profil di Left Rail / Sidebar Navigation
        const navLinks = Array.from(document.querySelectorAll('div[role="navigation"] a, div[data-pagelet="LeftRail"] a'));
        for (const a of navLinks) {{
            const href = a.getAttribute("href") || "";
            if (href.includes("profile.php") || href.includes("/me")) {{
                const txt = (a.innerText || "").trim();
                if (txt && txt.length > 2 && !["beranda", "reels", "teman", "grup", "home", "groups", "friends"].includes(txt.toLowerCase())) {{
                    return txt;
                }}
                const aria = a.getAttribute("aria-label") || "";
                if (aria) {{
                    let clean = aria.replace(/^(Linimasa|Timeline of)\s*/i, "").replace(/\s*'s timeline$/i, "").trim();
                    if (clean && !["beranda", "reels", "teman", "grup", "home", "groups", "friends"].includes(clean.toLowerCase())) {{
                        return clean;
                    }}
                }}
            }}
        }}

        // 3. Cari tombol profil di header kanan atas
        const topAvatars = Array.from(document.querySelectorAll('a[aria-label*="Profil"], a[aria-label*="Profile"]'));
        for (const a of topAvatars) {{
            const aria = a.getAttribute("aria-label") || "";
            let clean = aria.replace(/^(Profil|Profile|Go to profile|Buka profil)\s*/i, "").replace(/\s*Anda$/i, "").trim();
            if (clean && clean.length > 2 && clean.toLowerCase() !== "anda") return clean;
        }}

        return "";
    }}"""

    name = await page.evaluate(js)
    if name:
        return name

    # Fallback ke Title Halaman
    title = await page.title()
    if title:
        clean = re.sub(r"^\(\d+\)\s*", "", title).strip()
        clean = re.sub(r"\s*[\|-]\s*Facebook$", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"\s*Facebook$", "", clean, flags=re.IGNORECASE).strip()
        if clean and clean.lower() not in ["facebook", "log in", "masuk", "beranda"]:
            return clean

    return ""


async def process_single_account(p, s_info):
    s_path = s_info["path"]
    c_user = s_info.get("c_user", "")
    old_name = s_info.get("name", "Unknown")

    print(f"\n---------------------------------------------------------")
    print(f"📁 File sesi: {os.path.basename(s_path)}")
    print(f"🆔 c_user   : {c_user}")
    print(f"🏷️ Nama lama: {old_name}")

    if not c_user:
        print("❌ Cookie c_user tidak ditemukan.")
        return {"path": s_path, "c_user": c_user, "old_name": old_name, "real_name": "", "status": "INVALID"}

    try:
        browser, context = await create_stealth_context(p, session_file=s_path, headless=True)
        page = await context.new_page()

        # Buka beranda FB
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            print("❌ Sesi Expired atau Ter-checkpoint.")
            await browser.close()
            return {"path": s_path, "c_user": c_user, "old_name": old_name, "real_name": "", "status": "EXPIRED"}

        real_name = await extract_account_real_name(page, c_user)

        # Jika beranda belum menampilkan link profile.php?id=<c_user>, coba navigasi ke profile.php
        if not real_name:
            await page.goto(f"https://www.facebook.com/profile.php?id={c_user}", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
            real_name = await extract_account_real_name(page, c_user)

        await browser.close()

        if real_name:
            print(f"✨ NAMA ASLI TERDETEKSI: '{real_name}'")
            return {"path": s_path, "c_user": c_user, "old_name": old_name, "real_name": real_name, "status": "OK"}
        else:
            print("⚠️ Nama asli tidak terdeteksi secara otomatis.")
            return {"path": s_path, "c_user": c_user, "old_name": old_name, "real_name": old_name, "status": "NOT_FOUND"}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"path": s_path, "c_user": c_user, "old_name": old_name, "real_name": "", "status": "ERROR"}


async def main():
    fix_windows_stdout_encoding()
    print("=========================================================")
    print("🔄 PROSES PENYESUAIAN NAMA SELURUH AKUN FB KE NAMA ASLI")
    print("=========================================================")

    sessions = discover_all_sessions()
    if not sessions:
        print("❌ Tidak ada sesi yang tersimpan.")
        return

    print(f"📋 Memeriksa total {len(sessions)} akun sesi...\n")

    results = []
    async with async_playwright() as p:
        for idx, s in enumerate(sessions, 1):
            print(f"[{idx}/{len(sessions)}]", end="")
            res = await process_single_account(p, s)
            if res:
                results.append(res)

    print("\n" + "=" * 65)
    print("📊 HASIL AKHIR PENYESUAIAN NAMA AKUN:")
    print("=" * 65)

    updated_count = 0
    for res in results:
        status = res["status"]
        s_path = res["path"]
        old_name = res["old_name"]
        real_name = res["real_name"]
        c_user = res["c_user"]

        filename = os.path.basename(s_path)
        print(f"\n📌 Account ID: {c_user} ({filename})")

        if status == "OK" and real_name:
            print(f"   Nama Sebelumnya: {old_name}")
            print(f"   Nama Asli Baru  : {real_name}")

            # 1. Update metadata JSON
            updated = update_session_name(s_path, real_name)

            # 2. Rename file sesi jika bukan fb_session.json utama dan nama berubah
            safe_name_tag = "".join([c if c.isalnum() else "_" for c in real_name]).lower()
            safe_name_tag = re.sub(r"_+", "_", safe_name_tag).strip("_")

            dir_name = os.path.dirname(s_path)
            if filename != "fb_session.json" and safe_name_tag:
                new_filename = f"fb_session_{safe_name_tag}.json"
                new_path = os.path.join(dir_name, new_filename)

                if s_path != new_path and not os.path.exists(new_path):
                    try:
                        os.rename(s_path, new_path)
                        print(f"   🏷️ File disesuaikan: {filename} ➔ {new_filename}")
                    except Exception as e:
                        print(f"   ⚠️ Gagal merename file: {e}")
                elif s_path != new_path and os.path.exists(new_path):
                    print(f"   ℹ️ File {new_filename} sudah ada.")

            if updated:
                print("   ✅ Status: Berhasil diperbarui!")
                updated_count += 1
            else:
                print("   ❌ Status: Gagal update metadata JSON")
        else:
            print(f"   Nama Saat Ini: {old_name}")
            print(f"   ⚠️ Status: {status}")

    print("\n" + "=" * 65)
    print(f"🎉 Selesai! {updated_count} dari {len(sessions)} akun berhasil disesuaikan dengan nama asli.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
