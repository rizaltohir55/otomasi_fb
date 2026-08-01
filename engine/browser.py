"""
engine/browser.py
Manajer Siklus Hidup Browser & Sesi Playwright Stealth.
"""
import os
import json
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
        try:
            context_kwargs["storage_state"] = target_session
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
    try:
        os.makedirs(os.path.dirname(os.path.abspath(session_file)), exist_ok=True)
        state = await context.storage_state()
        
        if name:
            state["meta"] = {"name": name}
            
        temp_file = session_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
        if os.path.exists(session_file):
            os.remove(session_file)
        os.rename(temp_file, session_file)
        log(f"💾 Sesi berhasil disimpan ke: {os.path.basename(session_file)}")
    except Exception as e:
        log(f"❌ Gagal menyimpan sesi ke {session_file}: {e}")


async def verify_login_status(page: Page) -> bool:
    """Verifikasi apakah sesi di browser saat ini dalam kondisi ter-login di Facebook."""
    try:
        url_lower = page.url.lower()
        if "login" in url_lower or "checkpoint" in url_lower or "recover" in url_lower:
            return False

        cookies = await page.context.cookies()
        c_user = any(c.get("name") == "c_user" for c in cookies)
        if c_user:
            return True

        # Cek elemen visual indikator login
        profile_elem = page.get_by_role("link", name="Go to profile")
        if await profile_elem.count() > 0 and await profile_elem.first.is_visible(timeout=1000):
            return True

        login_form = page.locator("input[name='email'], input[id='email']")
        if await login_form.count() > 0 and await login_form.first.is_visible(timeout=1000):
            return False
    except Exception:
        pass
    return False


async def check_account_restriction(page: Page) -> Tuple[bool, str]:
    """
    Periksa apakah akun yang ter-login terkena pembatasan posting/grup dari Facebook (Restricted Account / Action Blocked).
    Mengembalikan (is_restricted: bool, restriction_reason: str).
    """
    try:
        # 1. Cek dialog modal peringatan pembatasan
        dialogs = page.locator('div[role="dialog"], div[role="alertdialog"]')
        count = await dialogs.count()
        for i in range(count):
            d = dialogs.nth(i)
            if await d.is_visible(timeout=200):
                text = (await d.inner_text()).lower()
                for kw in config.RESTRICTION_TEXTS:
                    if kw in text:
                        return True, f"Pop-up modal: '{kw}'"

        # 2. Cek banner notifikasi di bagian atas halaman
        banners = page.locator('div[role="banner"], div[role="alert"]')
        b_count = await banners.count()
        for j in range(b_count):
            b = banners.nth(j)
            if await b.is_visible(timeout=200):
                b_text = (await b.inner_text()).lower()
                for kw in config.RESTRICTION_TEXTS:
                    if kw in b_text:
                        return True, f"Banner notifikasi: '{kw}'"

    except Exception:
        pass
    return False, ""

