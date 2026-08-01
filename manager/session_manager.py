"""
manager/session_manager.py
Pengelola Sesi Akun Multi-Account Facebook.
Mendukung penemuan file sesi, validasi c_user, dan login interaktif akun baru.
"""
import os
import glob
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright

import config
from utils.helpers import log
from engine.browser import get_session_info, save_session_state



def discover_all_sessions() -> List[Dict[str, str]]:
    """
    Cari seluruh file sesi JSON yang tersimpan di folder session/ maupun di root directory.

    Memvalidasi bahwa setiap sesi memiliki cookie `c_user` DAN `xs` (keduanya wajib
    untuk otentikasi FB yang valid). Sesi tanpa `xs` tetap dikembalikan tetapi ditandai
    `xs_present=False` agar UI bisa memperingatkan user.
    """
    session_files = []

    # 1. Root directory session files
    root_files = glob.glob(os.path.join(config.BASE_DIR, "*.json"))
    for f in root_files:
        filename = os.path.basename(f)
        if filename.startswith("fb_session") or filename == "fb_session.json":
            session_files.append(os.path.abspath(f))

    # 2. Folder session/ directory files
    sub_files = glob.glob(os.path.join(config.SESSION_DIR, "*.json"))
    for f in sub_files:
        session_files.append(os.path.abspath(f))

    # Deduplikasi path
    unique_paths = sorted(list(set(session_files)))

    sessions_data = []
    for sp in unique_paths:
        info = get_session_info(sp)
        if info["c_user"]:
            # Tambahkan flag xs_present
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cookies = data.get("cookies", [])
                info["xs_present"] = any(c.get("name") == "xs" for c in cookies)
            except Exception:
                info["xs_present"] = False
            sessions_data.append(info)

    return sessions_data


async def interactive_login_new_account(account_tag: Optional[str] = None) -> str:
    """
    Buka Chromium GUI interaktif agar pengguna dapat login ke akun Facebook baru secara manual,
    lalu secara otomatis menyimpan cookie sesi ke file JSON.
    """
    log("\n🔑 [LOGIN INTERAKTIF AKUN BARU]")
    log("   Browser GUI akan terbuka. Silakan lakukan login ke Facebook di browser.")

    if not account_tag:
        try:
            account_tag = input("   Masukkan nama panggil akun ini (cth: Akun_Utama): ").strip()
        except (EOFError, RuntimeError):
            account_tag = ""

    if not account_tag:
        account_tag = f"account_{int(asyncio.get_event_loop().time())}"

    safe_tag = "".join([c if c.isalnum() else "_" for c in account_tag]).lower()
    target_path = os.path.join(config.SESSION_DIR, f"fb_session_{safe_tag}.json")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=config.USER_AGENT_DESKTOP,
        )
        page = await context.new_page()

        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        log("   👉 Menunggu Anda menyelesaikan login di browser...")

        # Polling sampai cookie c_user terdeteksi
        logged_in = False
        for _ in range(120):  # Maksimal 2 menit
            await asyncio.sleep(2)
            cookies = await context.cookies()
            if any(c.get("name") == "c_user" for c in cookies):
                logged_in = True
                break

        if logged_in:
            await page.wait_for_timeout(2000)
            await save_session_state(context, target_path, name=account_tag)
            log(f"   🎉 Login BERHASIL! Sesi disimpan ke: {target_path}")
            await browser.close()
            return target_path
        else:
            log("   ❌ Waktu login habis atau login gagal.")
            await browser.close()
            return ""


async def relogin_existing_account(session_file: str) -> bool:
    """
    Buka Chromium GUI interaktif untuk memperbarui/refresh cookie sesi pada file sesi yang sudah ada.
    """
    info = get_session_info(session_file)
    curr_name = info.get("name", os.path.basename(session_file))
    log(f"\n🔄 [LOGIN ULANG / REFRESH SESI: {curr_name}]")
    log(f"   Target file: {session_file}")
    log("   Browser GUI akan terbuka. Silakan selesaikan login / verifikasi akun di browser.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768"],
        )
        context_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": config.USER_AGENT_DESKTOP,
        }
        if os.path.exists(session_file):
            try:
                context_kwargs["storage_state"] = session_file
            except Exception:
                pass

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        log("   👉 Menunggu proses login / verifikasi selesai...")

        logged_in = False
        for _ in range(120):  # Maksimal 2 menit
            await asyncio.sleep(2)
            cookies = await context.cookies()
            if any(c.get("name") == "c_user" for c in cookies):
                logged_in = True
                break

        if logged_in:
            await page.wait_for_timeout(2000)
            await save_session_state(context, session_file, name=curr_name)
            log(f"   🎉 Sesi {curr_name} BERHASIL diperbarui & disimpan!")
            await browser.close()
            return True
        else:
            log("   ❌ Waktu login habis atau login gagal.")
            await browser.close()
            return False


def update_session_name(session_file: str, new_name: str) -> bool:
    """
    Ubah metadata nama panggil akun di dalam file sesi JSON.
    """
    if not os.path.exists(session_file):
        return False

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "meta" not in data or not isinstance(data["meta"], dict):
            data["meta"] = {}

        data["meta"]["name"] = new_name.strip()

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return True
    except Exception as e:
        log(f"❌ Gagal memperbarui nama sesi: {e}")
        return False


def delete_session_file(session_file: str, permanent: bool = False) -> bool:
    """
    Hapus file sesi JSON (Permanen atau ubah ke ekstensi .bak).
    """
    if not os.path.exists(session_file):
        return False

    try:
        if permanent:
            os.remove(session_file)
            log(f"🗑️ File sesi berhasil dihapus secara permanen: {os.path.basename(session_file)}")
        else:
            bak_path = session_file + ".bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)
            os.rename(session_file, bak_path)
            log(f"📦 File sesi berhasil dinonaktifkan (di-rename ke .bak): {os.path.basename(bak_path)}")
        return True
    except Exception as e:
        log(f"❌ Gagal menghapus file sesi: {e}")
        return False


def import_session_file(source_path: str, account_tag: str) -> str:
    """
    Import file sesi JSON kustom dari komputer ke folder session/.
    """
    source_path = source_path.strip().strip('"').strip("'")
    if not os.path.exists(source_path):
        log(f"❌ File tidak ditemukan: {source_path}")
        return ""

    try:
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        c_user = next((c["value"] for c in cookies if c.get("name") == "c_user"), "")
        if not c_user:
            log("❌ File sesi tidak valid (Cookie 'c_user' tidak ditemukan di JSON).")
            return ""

        if not account_tag:
            account_tag = f"imported_{c_user}"

        safe_tag = "".join([c if c.isalnum() else "_" for c in account_tag]).lower()
        target_path = os.path.join(config.SESSION_DIR, f"fb_session_{safe_tag}.json")

        if "meta" not in data or not isinstance(data["meta"], dict):
            data["meta"] = {}
        data["meta"]["name"] = account_tag

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        log(f"🎉 Berhasil mengimpor sesi {account_tag} (ID: {c_user}) ke: {target_path}")
        return target_path
    except Exception as e:
        log(f"❌ Gagal mengimpor file sesi: {e}")
        return ""


async def verify_session_live_status(session_file: str) -> Dict[str, Any]:
    """
    Uji status live sesi ke Facebook secara cepat & kilat (<1 detik).
    """
    info = get_session_info(session_file)
    result = {
        "file": session_file,
        "name": info.get("name", "Unknown"),
        "c_user": info.get("c_user", ""),
        "status": "CHECKING",
        "message": "",
    }

    if not os.path.exists(session_file):
        result["status"] = "EXPIRED"
        result["message"] = "File sesi tidak ditemukan"
        return result

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        c_user = next((c.get("value") for c in cookies if c.get("name") == "c_user"), "")
        xs = next((c.get("value") for c in cookies if c.get("name") == "xs"), "")

        if not c_user or not xs:
            result["status"] = "EXPIRED"
            result["message"] = "Cookie c_user / xs tidak ditemukan"
            return result

        # Cek expiration timestamp jika ada
        c_user_cookie = next((c for c in cookies if c.get("name") == "c_user"), {})
        exp = c_user_cookie.get("expires", 0)
        if exp > 0 and exp < time.time():
            result["status"] = "EXPIRED"
            result["message"] = "Cookie c_user telah kedaluwarsa"
            return result

        # Jalankan HTTP GET cepat ke m.facebook.com via threadpool agar non-blocking
        def http_check() -> Tuple[str, str]:
            try:
                import urllib.request
                import urllib.error
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if "name" in c and "value" in c])
                req = urllib.request.Request(
                    "https://m.facebook.com/",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                        "Cookie": cookie_str
                    }
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    final_url = resp.geturl().lower()
                    body = resp.read().decode("utf-8", errors="ignore").lower()
                    if "checkpoint" in final_url or "checkpoint" in body:
                        return "CHECKPOINT", "Akun Terkena Checkpoint FB"
                    elif "login" in final_url:
                        return "EXPIRED", "Sesi Kedaluwarsa (Redirect Login)"
                    elif any(kw in body for kw in config.RESTRICTION_TEXTS):
                        return "RESTRICTED", "Akun Dibatasi FB (Restricted)"
                    else:
                        return "ACTIVE", "Sesi Aktif & Terverifikasi"
            except urllib.error.HTTPError as he:
                # HTTP 4xx/5xx — sesi mungkin valid tapi FB menolak request ini.
                # Jangan false-positive ACTIVE; kembalikan UNKNOWN.
                return "UNKNOWN", f"HTTP {he.code} — sesi tidak dapat diverifikasi"
            except urllib.error.URLError as ue:
                # Network error (DNS, timeout, refused) — tidak bisa memastikan status sesi.
                return "UNKNOWN", f"Network error: {ue.reason}"
            except Exception as e:
                # Exception tak terduga lain — konservatif: UNKNOWN, bukan ACTIVE.
                return "UNKNOWN", f"Error tidak terduga: {e}"

        status, msg = await asyncio.to_thread(http_check)
        result["status"] = status
        result["message"] = msg

    except Exception as e:
        result["status"] = "EXPIRED"
        result["message"] = str(e)

    return result

