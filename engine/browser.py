"""
engine/browser.py
Manajer Siklus Hidup Browser & Sesi Playwright Stealth.
"""
import os
import json
import time
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

import config
from utils.helpers import log


import hashlib

def generate_deterministic_profile(session_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Hasilkan profil fingerprint hardware & browser yang konsisten dan realistis
    berdasarkan hash unik ID c_user / file sesi.
    """
    info = get_session_info(session_file) if session_file else {}
    seed_key = info.get("c_user") or (os.path.basename(session_file) if session_file else "default_key")
    
    hash_num = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest(), 16)
    profile_idx = hash_num % len(config.SPOOF_PROFILES_POOL)
    
    profile = dict(config.SPOOF_PROFILES_POOL[profile_idx])
    profile["account_id"] = info.get("c_user", "N/A")
    profile["account_name"] = info.get("name", "Unknown")
    return profile


async def create_stealth_context(
    playwright: Playwright,
    session_file: Optional[str] = None,
    headless: bool = False,
    enable_spoof: bool = True
) -> Tuple[Browser, BrowserContext]:
    """
    Inisialisasi Chromium browser & stealth context untuk emulasi Facebook Desktop dengan
    Fingerprint & Stealth Spoofing Nyata (100% Bekerja di Headless Mode).
    """
    target_session = session_file or config.SESSION_FILE
    profile = generate_deterministic_profile(target_session) if enable_spoof else config.SPOOF_PROFILES_POOL[0]

    vw = profile["viewport"]["width"]
    vh = profile["viewport"]["height"]

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        f"--window-size={vw},{vh}",
    ]

    # Cek Proxy kustom jika ada di metadata sesi JSON
    proxy_config = None
    if target_session and os.path.exists(target_session):
        try:
            with open(target_session, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                proxy_str = s_data.get("meta", {}).get("proxy", "")
                if proxy_str:
                    proxy_config = {"server": proxy_str}
        except Exception:
            pass

    launch_kwargs: Dict[str, Any] = {
        "headless": headless,
        "args": launch_args,
    }
    if proxy_config:
        launch_kwargs["proxy"] = proxy_config

    browser = await playwright.chromium.launch(**launch_kwargs)

    context_kwargs: Dict[str, Any] = {
        "viewport": profile["viewport"],
        "user_agent": profile["user_agent"],
        "is_mobile": False,
        "has_touch": False,
        "device_scale_factor": profile.get("device_scale_factor", 1.0),
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "extra_http_headers": {
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-CH-UA": profile.get("sec_ch_ua", '"Chromium";v="126", "Google Chrome";v="126"'),
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f'"{profile.get("platform", "Windows")}"',
        },
    }

    if target_session and os.path.exists(target_session):
        # Validate JSON file integrity before passing to Playwright.
        # Playwright raises a cryptic error if storage_state file is malformed.
        try:
            with open(target_session, "r", encoding="utf-8") as f:
                _ = json.load(f)  # parse-check only
            context_kwargs["storage_state"] = target_session
        except json.JSONDecodeError as je:
            log(f"⚠️ File sesi {os.path.basename(target_session)} korup (JSON invalid): {je}")
            log(f"   ⚠️ Browser akan diluncurkan tanpa cookie sesi. Akun akan terlihat logged-out.")
            # Backup file korup agar user bisa investigasi
            try:
                bak = target_session + f".corrupt.{int(time.time())}"
                os.rename(target_session, bak)
                log(f"   📦 File korup dibackup ke: {os.path.basename(bak)}")
            except OSError:
                pass
        except Exception as e:
            log(f"⚠️ Gagal memuat storage_state dari {target_session}: {e}")

    context = await browser.new_context(**context_kwargs)

    # ── Pre-Navigation DOM Stealth Script Injection (Nyata untuk Headless & GUI) ──
    cores_val = profile.get("cores", 8)
    mem_val   = profile.get("memory", 8)
    vendor_val = profile.get("vendor", "Intel Inc.")
    renderer_val = profile.get("renderer", "Intel(R) UHD Graphics 620")

    stealth_js = f"""
    (() => {{
        // 1. Clear navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});

        // 2. Hardware Properties Spoofing
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {cores_val},
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {mem_val},
        }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => 0,
        }});
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['id-ID', 'id', 'en-US', 'en'],
        }});

        // 3. WebGL Vendor & Renderer Masking (Overriding SwiftShader/Headless Signatures)
        const getParameterWrapper = (origFn) => function(parameter) {{
            // 0x9245 = UNMASKED_VENDOR_WEBGL, 0x9246 = UNMASKED_RENDERER_WEBGL
            if (parameter === 0x9245) return '{vendor_val}';
            if (parameter === 0x9246) return '{renderer_val}';
            return origFn.apply(this, arguments);
        }};

        try {{
            WebGLRenderingContext.prototype.getParameter = getParameterWrapper(WebGLRenderingContext.prototype.getParameter);
            WebGL2RenderingContext.prototype.getParameter = getParameterWrapper(WebGL2RenderingContext.prototype.getParameter);
        }} catch(e) {{}}

        // 4. Canvas Subtle Pixel Noise (Fingerprint Noise Injection per Account)
        try {{
            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function() {{
                const res = origGetImageData.apply(this, arguments);
                if (res && res.data && res.data.length > 4) {{
                    // Berikan micro noise pada channel R pixel pertama tanpa merusak tampilan
                    res.data[0] = (res.data[0] ^ {cores_val}) & 0xFF;
                }}
                return res;
            }};
        }} catch(e) {{}}

        // 5. Mock Chrome Runtime (Terlihat seperti Chrome Desktop Asli)
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{ return {{}}; }},
            csi: function() {{ return {{}}; }},
            app: {{ isInstalled: false }}
        }};
    }})();
    """
    await context.add_init_script(stealth_js)

    return browser, context


def get_session_info(session_file: str) -> Dict[str, str]:
    """
    Baca metadata akun dari file sesi JSON (c_user cookie dan nama akun jika ada).
    """
    info = {"c_user": "", "name": "Akun Sesi", "path": session_file}
    if not os.path.exists(session_file):
        return info

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        for c in cookies:
            if c.get("name") == "c_user":
                info["c_user"] = str(c.get("value", ""))
                break

        # Cek jika ada metadata tersimpan
        if "meta" in data and isinstance(data["meta"], dict):
            name_val = data["meta"].get("name", "")
            if name_val:
                info["name"] = name_val

        # Formatting nama fallback jika nama masih default/kosong
        if info["name"] == "Akun Sesi":
            base_name = os.path.basename(session_file).replace(".json", "")
            if base_name.startswith("fb_session_"):
                raw_tag = base_name[len("fb_session_"):]
                clean_tag = raw_tag.replace("_", " ").title()
                if clean_tag:
                    info["name"] = clean_tag
            elif base_name == "fb_session":
                info["name"] = "Akun Utama (Root)"
    except Exception:
        pass

    return info


async def save_session_state(context: BrowserContext, session_file: str, name: str = ""):
    """Simpan cookie & storage state browser saat ini ke file JSON secara atomik."""
    temp_file = session_file + ".tmp"
    backup_file = session_file + ".bak"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(session_file)), exist_ok=True)
        state = await context.storage_state()

        if name:
            # Preserve existing meta keys (proxy, etc.) and only overwrite name
            existing_meta = {}
            try:
                if os.path.exists(session_file):
                    with open(session_file, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    existing_meta = old_data.get("meta", {}) or {}
            except Exception:
                pass
            existing_meta["name"] = name
            state["meta"] = existing_meta

        # Write to temp file first
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        # Backup existing before replacing
        if os.path.exists(session_file):
            try:
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(session_file, backup_file)
            except OSError:
                pass

        # Atomic rename
        os.rename(temp_file, session_file)
        # Remove backup on success
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except OSError:
                pass
        log(f"💾 Sesi berhasil disimpan ke: {os.path.basename(session_file)}")
    except Exception as e:
        log(f"❌ Gagal menyimpan sesi ke {session_file}: {e}")
        # Cleanup dangling temp file
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        # Restore from backup if possible
        if not os.path.exists(session_file) and os.path.exists(backup_file):
            try:
                os.rename(backup_file, session_file)
                log(f"   🔄 Sesi sebelumnya direstore dari backup.")
            except OSError:
                pass


async def handle_profile_selector_page(page: Page, worker_tag: str = "") -> bool:
    """
    Deteksi & tangani halaman profile-selector FB (multi-account).
    FB kadang menampilkan halaman "Jelajahi hal-hal yang Anda sukai" + "Lanjutkan"
    saat akun punya multiple profiles. Tanpa handler ini, otomasi akan stuck
    karena halaman ini bukan feed utama dan bukan halaman login.

    Mengembalikan True jika halaman profile-selector terdeteksi DAN berhasil di-handle.
    """
    try:
        body_text = (await page.locator("body").inner_text(timeout=1500)).lower()
        # Cek apakah ini halaman profile-selector
        is_selector = any(kw in body_text for kw in [
            "gunakan profil lain",
            "use another profile",
            "jelajahi hal-hal yang anda sukai",
            "explore things you're interested in",
        ])
        if not is_selector:
            return False

        log("   ℹ️ Halaman profile-selector FB terdeteksi. Mencoba klik 'Lanjutkan'...", worker_tag)

        # Cari tombol "Lanjutkan" / "Continue"
        continue_selectors = [
            'div[role="button"]:has-text("Lanjutkan")',
            'div[role="button"]:has-text("Continue")',
            'a:has-text("Lanjutkan")',
            'a:has-text("Continue")',
            'span:has-text("Lanjutkan")',
            'span:has-text("Continue")',
        ]
        for sel in continue_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible(timeout=500):
                    await btn.click(timeout=2000)
                    await page.wait_for_timeout(500)
                    log("   ✅ Berhasil klik 'Lanjutkan' di profile-selector.", worker_tag)
                    return True
            except Exception:
                continue

        log("   ⚠️ Halaman profile-selector terdeteksi tapi tombol 'Lanjutkan' tidak ditemukan.", worker_tag)
        return False
    except Exception:
        return False


async def verify_login_status(page: Page) -> bool:
    """
    Verifikasi apakah sesi di browser saat ini dalam kondisi ter-login di Facebook.

    Catatan penting: FB kadang MENGHAPUS cookie c_user via Set-Cookie header
    saat halaman pertama dimuat, jika FB mendeteksi sesi invalid (mis. device
    fingerprint berubah). Jadi keberadaan c_user SEBELUM navigasi bukan jaminan
    login. Verifikasi dilakukan SETELAH navigasi: cek cookie + cek konten halaman.

    Memeriksa:
    - URL: terlempar ke /login, /checkpoint, /recover -> False
    - Cookie c_user ada SETELAH halaman dimuat -> True (paling andal)
    - Teks checkpoint (2FA, "verify it's you") terdeteksi -> False
    - Halaman profile-selector (multi-account) -> handle via handle_profile_selector_page
    - Form login terlihat -> False
    """
    try:
        url_lower = page.url.lower()
        # Cek URL login/checkpoint/recover paling awal (paling cepat)
        if "login" in url_lower or "checkpoint" in url_lower or "recover" in url_lower:
            return False

        cookies = await page.context.cookies()
        c_user = any(c.get("name") == "c_user" for c in cookies)

        if c_user:
            # c_user masih ada setelah halaman dimuat — sesi aktif.
            # Tetap cek apakah halaman menampilkan checkpoint (2FA, verify identity)
            try:
                body_text = (await page.locator("body").inner_text(timeout=2000)).lower()
                for kw in config.CHECKPOINT_INDICATOR_TEXTS:
                    if kw in body_text:
                        return False
            except Exception:
                pass
            return True

        # c_user tidak ada — kemungkinan logged out ATAU di halaman profile-selector.
        # Coba handle profile-selector dulu (mungkin masih bisa login dengan klik Lanjutkan)
        handled = await handle_profile_selector_page(page, worker_tag="")
        if handled:
            # Re-check cookie setelah handle
            cookies = await page.context.cookies()
            if any(c.get("name") == "c_user" for c in cookies):
                return True

        # Cek elemen visual indikator login (last resort)
        try:
            profile_elem = page.get_by_role("link", name="Go to profile")
            if await profile_elem.count() > 0 and await profile_elem.first.is_visible(timeout=1000):
                return True
        except Exception:
            pass

        # Cek form login -> pasti logged out
        try:
            login_form = page.locator("input[name='email'], input[id='email']")
            if await login_form.count() > 0 and await login_form.first.is_visible(timeout=1000):
                return False
        except Exception:
            pass
    except Exception:
        pass
    return False


async def check_account_restriction(page: Page) -> Tuple[bool, str]:
    """
    Periksa apakah akun yang ter-login terkena pembatasan posting/grup dari Facebook
    (Restricted Account / Action Blocked).

    Memindai:
    - div[role="dialog"] dan div[role="alertdialog"] (modal pop-up)
    - div[role="banner"], div[role="alert"] (banner & toast notifikasi)
    - div[aria-live="polite"], div[aria-live="assertive"] (inline live regions FB modern)
    - inline body text (paling lambat, fallback)

    Mengembalikan (is_restricted: bool, restriction_reason: str).
    """
    try:
        # 1. Cek dialog modal peringatan pembatasan
        dialogs = page.locator('div[role="dialog"], div[role="alertdialog"]')
        count = await dialogs.count()
        for i in range(min(count, 5)):  # cap iteration untuk efisiensi
            d = dialogs.nth(i)
            try:
                if not await d.is_visible(timeout=200):
                    continue
                text = (await d.inner_text()).lower()
                for kw in config.RESTRICTION_TEXTS:
                    if kw in text:
                        return True, f"Pop-up modal: '{kw}'"
            except Exception:
                continue

        # 2. Cek banner notifikasi di bagian atas halaman
        banners = page.locator('div[role="banner"], div[role="alert"]')
        b_count = await banners.count()
        for j in range(min(b_count, 5)):
            b = banners.nth(j)
            try:
                if not await b.is_visible(timeout=200):
                    continue
                b_text = (await b.inner_text()).lower()
                for kw in config.RESTRICTION_TEXTS:
                    if kw in b_text:
                        return True, f"Banner notifikasi: '{kw}'"
            except Exception:
                continue

        # 3. Cek live regions (FB modern sering pakai aria-live untuk toast notifikasi)
        live_regions = page.locator('div[aria-live="polite"], div[aria-live="assertive"]')
        lr_count = await live_regions.count()
        for k in range(min(lr_count, 5)):
            lr = live_regions.nth(k)
            try:
                lr_text = (await lr.inner_text()).lower()
                if not lr_text.strip():
                    continue
                for kw in config.RESTRICTION_TEXTS:
                    if kw in lr_text:
                        return True, f"Live region toast: '{kw}'"
            except Exception:
                continue

    except Exception:
        pass
    return False, ""


async def is_on_checkpoint_page(page: Page) -> bool:
    """
    Deteksi apakah halaman saat ini adalah halaman checkpoint FB
    (2FA, verifikasi identitas, "Save device", dsb).
    Bisa dipakai sebelum setiap aksi automation untuk fail-fast.
    """
    try:
        url_lower = page.url.lower()
        if "checkpoint" in url_lower or "two_step_verification" in url_lower:
            return True
        body_text = (await page.locator("body").inner_text(timeout=2000)).lower()
        for kw in config.CHECKPOINT_INDICATOR_TEXTS:
            if kw in body_text:
                return True
    except Exception:
        pass
    return False

