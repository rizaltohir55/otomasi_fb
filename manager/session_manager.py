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
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright

import config
from utils.helpers import log
from engine.browser import get_session_info, save_session_state


# ── X Server / Xvfb Helper ────────────────────────────────────────────────────
_xvfb_process: Optional[subprocess.Popen] = None


def _ensure_display() -> bool:
    """
    Pastikan ada DISPLAY environment variable yang valid untuk launch browser GUI.

    - Jika DISPLAY sudah set (ada X server) → return True.
    - Jika DISPLAY kosong DAN xvfb-run/Xvfb tersedia → start Xvfb virtual display,
      set DISPLAY=:99, return True.
    - Jika tidak ada X server maupun Xvfb → return False (caller harus fallback
      ke headless mode atau report error yang jelas).

    Return True jika browser GUI bisa di-launch.
    """
    global _xvfb_process

    # Di Windows, browser GUI selalu dapat dibuka langsung tanpa X server / Xvfb
    if os.name == "nt" or sys.platform == "win32":
        return True

    # Sudah ada DISPLAY — asumsikan X server berjalan
    if os.environ.get("DISPLAY"):
        return True

    # Cari Xvfb binary
    xvfb_bin = shutil.which("Xvfb")
    if not xvfb_bin:
        log("   ⚠️ Tidak ada X server (DISPLAY kosong) dan Xvfb tidak terinstall.")
        log("   ℹ️ Install dengan: sudo apt-get install -y xvfb")
        return False

    # Start Xvfb di display :99 dengan resolution 1366x768x24
    try:
        _xvfb_process = subprocess.Popen(
            [xvfb_bin, ":99", "-screen", "0", "1366x768x24", "-ac", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Beri waktu Xvfb untuk start
        time.sleep(1.0)
        if _xvfb_process.poll() is not None:
            log("   ⚠️ Xvfb gagal start (process exited immediately).")
            _xvfb_process = None
            return False
        os.environ["DISPLAY"] = ":99"
        log("   🖥️ Xvfb virtual display dimulai di :99 (headless server detected).")
        return True
    except Exception as e:
        log(f"   ⚠️ Gagal start Xvfb: {e}")
        _xvfb_process = None
        return False


def _cleanup_xvfb():
    """Cleanup Xvfb process saat aplikasi shutdown."""
    global _xvfb_process
    if _xvfb_process is not None:
        try:
            _xvfb_process.terminate()
            _xvfb_process.wait(timeout=3)
        except Exception:
            try:
                _xvfb_process.kill()
            except Exception:
                pass
        _xvfb_process = None


def _can_launch_gui_browser() -> bool:
    """Cek apakah browser GUI (headless=False) bisa di-launch di environment ini."""
    return _ensure_display()



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

    PENTING: Fitur ini HANYA bisa dipakai jika server punya display yang BISA DILIHAT user:
    - Desktop lokal (DISPLAY sudah set) → browser GUI terbuka di monitor user
    - Server remote dengan VNC/RDP → user bisa lihat virtual display via VNC client
    - Server remote TANPA VNC → user TIDAK BISA lihat browser → gunakan Import Sesi JSON

    Deteksi: jika DISPLAY kosong DAN Xvfb start OK, browser terbuka di virtual display :99
    TAPI user remote tidak bisa interact kecuali ada VNC. Return error jelas + arahkan
    ke Import Sesi JSON.
    """
    log("\n🔑 [LOGIN INTERAKTIF AKUN BARU]")

    # Cek environment: apakah user bisa melihat browser GUI?
    # Jika DISPLAY kosong → server headless/remote → user TIDAK BISA interact
    # dengan browser GUI. Langsung arahkan ke Import Sesi JSON (jangan buka browser).
    if not os.environ.get("DISPLAY"):
        log("   ❌ Tidak dapat membuka browser GUI di environment ini.")
        log("   ℹ️ Server ini berjalan tanpa display (headless/remote).")
        log("   ℹ️ Browser GUI tidak bisa ditampilkan ke Anda.")
        log("")
        log("   📋 CARA ALTERNATIF: Import Sesi JSON")
        log("   1. Buka Facebook di browser LOKAL Anda (Chrome/Firefox di komputer Anda)")
        log("   2. Login ke akun Facebook yang ingin ditambahkan")
        log("   3. Install extension 'EditThisCookie' atau 'Cookie-Editor'")
        log("   4. Klik icon extension → Export semua cookie sebagai JSON")
        log("   5. Klik tombol 'Import Sesi' di dashboard web ini")
        log("   6. Paste JSON cookie ke form Import + isi nama akun")
        log("   7. Klik 'Import Sesi' — akun baru akan tersimpan")
        log("")
        log("   ℹ️ Jika Anda punya akses VNC/RDP ke server, set DISPLAY env var")
        log("      sebelum menjalankan server untuk mengaktifkan browser GUI.")
        return ""

    if not account_tag:
        try:
            account_tag = input("   Masukkan nama panggil akun ini (cth: Akun_Utama): ").strip()
        except (EOFError, RuntimeError):
            account_tag = ""

    if not account_tag:
        account_tag = f"account_{int(asyncio.get_event_loop().time())}"

    safe_tag = "".join([c if c.isalnum() else "_" for c in account_tag]).lower()
    target_path = os.path.join(config.SESSION_DIR, f"fb_session_{safe_tag}.json")

    browser = None
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768", "--no-sandbox"],
                )
            except Exception as launch_e:
                err_msg = str(launch_e)
                if "Missing X server" in err_msg or "$DISPLAY" in err_msg:
                    log("   ❌ Browser GUI gagal dibuka: Missing X server.")
                    log("   ℹ️ Xvfb mungkin gagal start. Gunakan Import Sesi JSON sebagai alternatif.")
                else:
                    log(f"   ❌ Browser GUI gagal dibuka: {launch_e}")
                return ""

            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=config.USER_AGENT_DESKTOP,
            )
            page = await context.new_page()

            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            log("   👉 Browser GUI terbuka. Menunggu login...")
            log("   ⏳ Timeout: 4 menit.")

            logged_in = False
            for i in range(120):
                await asyncio.sleep(2)
                cookies = await context.cookies()
                if any(c.get("name") == "c_user" for c in cookies):
                    logged_in = True
                    break
                if i > 0 and i % 15 == 0:
                    remaining = 240 - (i * 2)
                    log(f"   ⏳ Menunggu login... {remaining}s tersisa")

            if logged_in:
                await page.wait_for_timeout(2000)
                await save_session_state(context, target_path, name=account_tag)
                log(f"   🎉 Login BERHASIL! Sesi disimpan ke: {target_path}")
                await browser.close()
                return target_path
            else:
                log("   ❌ Waktu login habis (4 menit) atau login gagal.")
                log("   ℹ️ Jika Anda tidak bisa melihat browser, gunakan Import Sesi JSON.")
                await browser.close()
                return ""
    except Exception as e:
        log(f"   ❌ Error saat login interaktif: {e}")
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return ""


async def relogin_existing_account(session_file: str) -> bool:
    """
    Buka Chromium GUI interaktif untuk memperbarui/refresh cookie sesi pada file sesi yang sudah ada.

    PENTING: Fitur ini HANYA bisa dipakai jika server punya display yang BISA DILIHAT user.
    Untuk server remote tanpa VNC/RDP, gunakan Import Sesi JSON sebagai alternatif.
    """
    info = get_session_info(session_file)
    curr_name = info.get("name", os.path.basename(session_file))
    log(f"\n🔄 [LOGIN ULANG / REFRESH SESI: {curr_name}]")
    log(f"   Target file: {session_file}")

    # Cek environment: jika DISPLAY kosong → server headless/remote
    # User TIDAK BISA interact dengan browser GUI. Langsung arahkan ke Import Sesi JSON.
    if not os.environ.get("DISPLAY"):
        log("   ❌ Tidak dapat membuka browser GUI di environment ini.")
        log("   ℹ️ Server ini berjalan tanpa display (headless/remote).")
        log("   ℹ️ Browser GUI tidak bisa ditampilkan ke Anda.")
        log("")
        log("   📋 CARA ALTERNATIF: Import Sesi JSON (Refresh Cookie)")
        log("   1. Buka Facebook di browser LOKAL Anda (Chrome/Firefox di komputer Anda)")
        log("   2. Login ke akun Facebook yang ingin di-refresh")
        log("   3. Install extension 'EditThisCookie' atau 'Cookie-Editor'")
        log("   4. Klik icon extension → Export semua cookie sebagai JSON")
        log("   5. Klik tombol 'Import Sesi' di dashboard web ini")
        log(f"   6. Isi nama akun: '{curr_name}' (atau nama baru)")
        log("   7. Paste JSON cookie ke form Import")
        log("   8. Klik 'Import Sesi' — sesi baru akan tersimpan")
        log(f"   9. Hapus sesi lama ({os.path.basename(session_file)}) manual jika perlu")
        log("")
        log("   ℹ️ Jika Anda punya akses VNC/RDP ke server, set DISPLAY env var")
        log("      sebelum menjalankan server untuk mengaktifkan browser GUI.")
        return False

    browser = None
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled", "--window-size=1366,768", "--no-sandbox"],
                )
            except Exception as launch_e:
                err_msg = str(launch_e)
                if "Missing X server" in err_msg or "$DISPLAY" in err_msg:
                    log("   ❌ Browser GUI gagal dibuka: Missing X server.")
                    log("   ℹ️ Xvfb mungkin gagal start. Gunakan Import Sesi JSON sebagai alternatif.")
                else:
                    log(f"   ❌ Browser GUI gagal dibuka: {launch_e}")
                return False

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
            log("   👉 Browser GUI terbuka. Menunggu login...")

            logged_in = False
            for i in range(120):
                await asyncio.sleep(2)
                cookies = await context.cookies()
                if any(c.get("name") == "c_user" for c in cookies):
                    logged_in = True
                    break
                if i > 0 and i % 15 == 0:
                    remaining = 240 - (i * 2)
                    log(f"   ⏳ Menunggu relogin... {remaining}s tersisa")

            if logged_in:
                await page.wait_for_timeout(2000)
                await save_session_state(context, session_file, name=curr_name)
                log(f"   🎉 Sesi {curr_name} BERHASIL diperbarui & disimpan!")
                await browser.close()
                return True
            else:
                log("   ❌ Waktu login habis (4 menit) atau login gagal.")
                log("   ℹ️ Jika Anda tidak bisa melihat browser, gunakan Import Sesi JSON.")
                await browser.close()
                return False
    except Exception as e:
        log(f"   ❌ Error saat relogin: {e}")
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
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
    Uji status live sesi ke Facebook secara akurat menggunakan Playwright headless.

    Sebelumnya pakai urllib.request mentah, tapi FB menolak dengan HTTP 400
    (deteksi bot — urllib tidak ada JS execution, header tidak lengkap,
    fingerprint bot). Playwright dengan stealth context terbukti akurat
    di live test.

    Strategi:
    1. Validasi file sesi (ada, JSON valid, c_user + xs ada, belum expired).
    2. Buka Chromium headless dengan stealth context + storage_state.
    3. Navigasi ke https://www.facebook.com/ (domcontentloaded, timeout 20s).
    4. Cek URL: login/checkpoint/recover → EXPIRED/CHECKPOINT.
    5. Cek cookie c_user SETELAH navigasi (FB kadang hapus via Set-Cookie
       kalau sesi invalid di sisi server).
    6. Cek body text untuk checkpoint indicators (2FA, "verify it's you").
    7. Cek restriction (modal/banner/aria-live).
    8. Return status: ACTIVE / EXPIRED / CHECKPOINT / RESTRICTED / UNKNOWN.
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

    # ── 1. Validasi file sesi ──────────────────────────────────────────────
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as je:
        result["status"] = "EXPIRED"
        result["message"] = f"File sesi korup (JSON invalid): {je}"
        return result
    except Exception as e:
        result["status"] = "EXPIRED"
        result["message"] = f"Gagal membaca file sesi: {e}"
        return result

    cookies = data.get("cookies", [])
    c_user_val = next((c.get("value") for c in cookies if c.get("name") == "c_user"), "")
    xs_val = next((c.get("value") for c in cookies if c.get("name") == "xs"), "")

    if not c_user_val:
        result["status"] = "EXPIRED"
        result["message"] = "Cookie c_user tidak ditemukan di file sesi"
        return result
    if not xs_val:
        result["status"] = "EXPIRED"
        result["message"] = "Cookie xs tidak ditemukan (sesi tidak valid untuk otentikasi FB)"
        return result

    # Cek expiration timestamp cookie c_user
    c_user_cookie = next((c for c in cookies if c.get("name") == "c_user"), {})
    exp = c_user_cookie.get("expires", 0)
    if exp > 0 and exp < time.time():
        result["status"] = "EXPIRED"
        result["message"] = f"Cookie c_user telah kedaluwarsa (exp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))})"
        return result

    # ── 2. Verifikasi via Playwright headless ──────────────────────────────
    # Jalankan di thread terpisah dengan event loop baru agar tidak conflict
    # dengan event loop FastAPI utama.
    def playwright_check() -> Tuple[str, str]:
        from playwright.async_api import async_playwright
        from engine.browser import create_stealth_context, verify_login_status, check_account_restriction

        # Buat event loop baru di thread ini
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _check():
            browser = None
            context = None
            try:
                async with async_playwright() as p:
                    browser, context = await create_stealth_context(
                        p, session_file=session_file, headless=True
                    )
                    page = await context.new_page()

                    # Navigasi ke Facebook home
                    try:
                        await page.goto(
                            "https://www.facebook.com/",
                            wait_until="domcontentloaded",
                            timeout=20000
                        )
                    except Exception as nav_e:
                        # Fallback: coba dengan wait_until="commit"
                        try:
                            await page.goto(
                                "https://www.facebook.com/",
                                wait_until="commit",
                                timeout=12000
                            )
                        except Exception:
                            return "UNKNOWN", f"Navigasi FB gagal: {nav_e}"

                    await page.wait_for_timeout(2500)

                    final_url = page.url.lower()

                    # Cek URL login/checkpoint/recover
                    if "login" in final_url or "recover" in final_url:
                        return "EXPIRED", "Sesi kedaluwarsa (redirect ke halaman login)"
                    if "checkpoint" in final_url or "two_step" in final_url:
                        return "CHECKPOINT", "Akun terkena checkpoint FB (2FA/verifikasi)"

                    # Cek cookie c_user SETELAH navigasi
                    # FB kadang hapus c_user via Set-Cookie kalau sesi invalid di server.
                    # Halaman profile-selector ("Jelajahi hal-hal yang Anda sukai" + "Lanjutkan")
                    # muncul ketika FB mengenali device tapi sesi login TIDAK valid —
                    # user perlu re-login manual. Jadi profile-selector TANPA c_user = EXPIRED.
                    cookies_after = await context.cookies()
                    c_user_after = any(c.get("name") == "c_user" for c in cookies_after)
                    if not c_user_after:
                        # Cek apakah ini halaman profile-selector (multi-account device)
                        try:
                            body_text = (await page.locator("body").inner_text(timeout=1500)).lower()
                            if any(kw in body_text for kw in [
                                "gunakan profil lain", "use another profile",
                                "jelajahi hal-hal yang anda sukai"
                            ]):
                                # Profile selector tanpa c_user = sesi sudah invalid,
                                # FB hanya mengenali device. User perlu relogin.
                                return "EXPIRED", "Sesi kedaluwarsa (halaman profile-selector — perlu relogin)"
                            # Cek form login
                            if any(kw in body_text for kw in ["masuk", "log in", "daftar", "sign up"]):
                                return "EXPIRED", "Sesi kedaluwarsa (form login terlihat)"
                        except Exception:
                            pass
                        return "EXPIRED", "Sesi kedaluwarsa (c_user dihapus FB setelah navigasi)"

                    # c_user masih ada — cek checkpoint indicators di body
                    try:
                        body_text = (await page.locator("body").inner_text(timeout=2000)).lower()
                        for kw in config.CHECKPOINT_INDICATOR_TEXTS:
                            if kw in body_text:
                                return "CHECKPOINT", f"Halaman checkpoint terdeteksi: '{kw}'"
                    except Exception:
                        pass

                    # Cek restriction
                    is_res, res_reason = await check_account_restriction(page)
                    if is_res:
                        return "RESTRICTED", f"Akun dibatasi FB: {res_reason}"

                    # Semua cek lolos — sesi aktif
                    return "ACTIVE", "Sesi aktif & terverifikasi via Playwright"

            except Exception as e:
                err_msg = str(e) or type(e).__name__
                # Playwright timeout atau browser crash
                if "Target page, context or browser has been closed" in err_msg:
                    return "UNKNOWN", "Browser ditutup sebelum verifikasi selesai"
                return "UNKNOWN", f"Error verifikasi: {err_msg}"
            finally:
                try:
                    if context: await context.close()
                except Exception:
                    pass
                try:
                    if browser: await browser.close()
                except Exception:
                    pass

        try:
            return loop.run_until_complete(_check())
        finally:
            try:
                loop.close()
            except Exception:
                pass

    try:
        status, msg = await asyncio.to_thread(playwright_check)
        result["status"] = status
        result["message"] = msg
    except Exception as e:
        result["status"] = "UNKNOWN"
        result["message"] = f"Error thread: {e}"

    return result

