#!/usr/bin/env python3
"""
login.py — Login akun Facebook via browser GUI di terminal lokal.
"""
import sys, os, asyncio
from playwright.async_api import async_playwright
import config
from helpers import log, get_account_name
from browser import save_session


async def login_new(tag=""):
    """Buka browser GUI, tunggu user login, simpan cookie."""
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        print("❌ Tidak ada display. Jalankan di komputer lokal dengan monitor.")
        print("   Windows: OK | Linux desktop: OK | Server remote: tidak bisa")
        return ""

    if not tag:
        try:
            tag = input("Nama akun (cth: Akun_Baru): ").strip()
        except (EOFError, RuntimeError):
            tag = ""
    if not tag:
        tag = f"akun_{int(asyncio.get_event_loop().time())}"

    safe = "".join(c if c.isalnum() else "_" for c in tag).lower()
    path = os.path.join(config.SESSION_DIR, f"fb_session_{safe}.json")

    print(f"\n🔑 Login akun: {tag}")
    print(f"   Browser akan terbuka. Login Facebook di browser.")
    print(f"   Timeout: 4 menit.\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768", "--no-sandbox"],
            )
        except Exception as e:
            if "Missing X server" in str(e) or "$DISPLAY" in str(e):
                print("❌ Browser GUI gagal: tidak ada display.")
            else:
                print(f"❌ Browser gagal: {e}")
            return ""

        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=config.PROFILES[0]["ua"],
        )
        page = await context.new_page()
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        print("👉 Browser terbuka. Login Facebook sekarang...")

        for i in range(120):
            await asyncio.sleep(2)
            cookies = await context.cookies()
            if any(c.get("name") == "c_user" for c in cookies):
                await page.wait_for_timeout(2000)
                await save_session(context, path, tag)
                print(f"\n🎉 Login berhasil! Sesi: {path}")
                await browser.close()
                return path
            if i > 0 and i % 15 == 0:
                print(f"⏳ Menunggu... {240 - i*2}s tersisa")

        print("\n❌ Timeout (4 menit). Login gagal.")
        await browser.close()
        return ""


async def relogin(session_file):
    """Refresh cookie akun yang sudah ada."""
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        print("❌ Tidak ada display. Jalankan di komputer lokal.")
        return False

    name = get_account_name(session_file)
    print(f"\n🔄 Relogin: {name}")
    print(f"   File: {session_file}")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768", "--no-sandbox"],
            )
        except Exception as e:
            print(f"❌ Browser gagal: {e}")
            return False

        kw = {"viewport": {"width": 1366, "height": 768}, "user_agent": config.PROFILES[0]["ua"]}
        if os.path.exists(session_file):
            try:
                kw["storage_state"] = session_file
            except Exception:
                pass

        context = await browser.new_context(**kw)
        page = await context.new_page()
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        print("👉 Login ulang di browser...")

        for i in range(120):
            await asyncio.sleep(2)
            cookies = await context.cookies()
            if any(c.get("name") == "c_user" for c in cookies):
                await page.wait_for_timeout(2000)
                await save_session(context, session_file, name)
                print(f"\n🎉 Relogin berhasil!")
                await browser.close()
                return True
            if i > 0 and i % 15 == 0:
                print(f"⏳ Menunggu... {240 - i*2}s tersisa")

        print("\n❌ Timeout.")
        await browser.close()
        return False


def main():
    print("""
=================================================================
   🔑 FB AUTOENGINE — LOGIN TERMINAL
=================================================================
""")
    while True:
        print("\n📋 MENU:")
        print("   [1] ➕ Login Akun Baru")
        print("   [2] 🔄 Relogin Akun Existing")
        print("   [3] 📋 Lihat Sesi Tersimpan")
        print("   [0] ❌ Keluar")
        c = input("\n👉 Pilih [0-3]: ").strip()

        if c == "0":
            break
        elif c == "1":
            asyncio.run(login_new())
        elif c == "2":
            from helpers import discover_sessions
            sessions = discover_sessions()
            if not sessions:
                print("⚠️ Belum ada sesi.")
                continue
            for i, s in enumerate(sessions, 1):
                print(f"   [{i}] {s['name']} (ID: {s['c_user']})")
            sel = input("👉 Pilih [1-N]: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(sessions):
                asyncio.run(relogin(sessions[int(sel)-1]["path"]))
        elif c == "3":
            from helpers import discover_sessions
            sessions = discover_sessions()
            if not sessions:
                print("⚠️ Belum ada sesi.")
            else:
                for i, s in enumerate(sessions, 1):
                    print(f"   [{i}] {s['name']} | ID: {s['c_user']} | {s['path']}")

        if c in ["1", "2", "3"]:
            input("\nTekan Enter...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Dibatalkan.")
