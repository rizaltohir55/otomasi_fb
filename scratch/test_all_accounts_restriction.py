import asyncio
import os
import sys
sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from engine.browser import create_stealth_context, check_account_restriction, verify_login_status
from manager.session_manager import discover_all_sessions
from engine.joiner import check_membership_status
from engine.collector import load_groups

async def deep_check_account(p, session_file: str, group_url: str) -> dict:
    info = {"file": session_file, "name": os.path.basename(session_file), "status": "UNKNOWN", "reason": ""}
    browser, context = await create_stealth_context(p, session_file=session_file, headless=True)
    page = await context.new_page()

    try:
        # 1. Navigasi ke Halaman Utama FB
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)

        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            info["status"] = "EXPIRED"
            info["reason"] = "Cookie Login Kedaluwarsa / Checkpoint"
            return info

        # 2. Cek Notifikasi Pembatasan Akun Global (FB Restriction Notice Page / Support Inbox)
        await page.goto("https://www.facebook.com/me/", wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(1500)
        
        is_res, reason = await check_account_restriction(page)
        if is_res:
            info["status"] = "RESTRICTED"
            info["reason"] = f"Aktivitas Dibatasi FB: {reason}"
            return info

        # 3. Uji pada Halaman Grup
        await page.goto(group_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # Cek keanggotaan
        mem_status = await check_membership_status(page, group_url)
        if mem_status in ["UNJOINED", "REQUESTED"]:
            info["status"] = "UNJOINED"
            info["reason"] = f"Akun Belum Menjadi Anggota Grup Ini (Status: {mem_status})"
            return info

        # Buka Komposer
        composer_trig = page.locator(
            'div[role="button"]:has-text("Write something"), '
            'div[role="button"]:has-text("Tulis sesuatu"), '
            'span:has-text("Write something"), '
            'span:has-text("Tulis sesuatu")'
        )

        if await composer_trig.count() > 0:
            await composer_trig.first.click(timeout=5000)
            await page.wait_for_timeout(2000)

            # Cek restriction di dalam modal komposer
            is_res, reason = await check_account_restriction(page)
            if is_res:
                info["status"] = "RESTRICTED"
                info["reason"] = f"Dibatasi saat Buka Komposer: {reason}"
                return info

            # Cek teks "Anda tidak dapat memposting" / "Dibatasi"
            body = (await page.locator("body").inner_text()).lower()
            restriction_keywords = [
                "dibatasi", "restricted", "temporarily blocked", "terkunci sementara",
                "tidak dapat memposting", "cannot post", "action blocked", "tindakan diblokir",
                "anda tidak bisa", "you can't post"
            ]
            for kw in restriction_keywords:
                if kw in body:
                    info["status"] = "RESTRICTED"
                    info["reason"] = f"Dibatasi FB: '{kw}'"
                    return info

        info["status"] = "ACTIVE"
        info["reason"] = "Akun Aktif & Berhasil Buka Komposer Grup"
        return info

    except Exception as e:
        info["status"] = "ERROR"
        info["reason"] = str(e)
        return info
    finally:
        try:
            await context.close()
            await browser.close()
        except Exception:
            pass

async def main():
    sessions = discover_all_sessions()
    groups = load_groups()
    test_group = groups[0] if groups else "https://www.facebook.com/groups/feed/"

    print("=================================================================")
    print(" DEEP INSPECTION AUDIT SELURUH AKUN (CEK COMPOSER & RESTRICTION)")
    print("=================================================================\n")

    async with async_playwright() as p:
        for s in sessions:
            res = await deep_check_account(p, s["path"], test_group)
            print(f"[{res['name']}] -> Status: {res['status']} | Reason: {res['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
