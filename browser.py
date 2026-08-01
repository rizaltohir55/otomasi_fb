"""
browser.py — Stealth browser context + session verify + save.
"""
import os, json, time, hashlib
from typing import Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import config
from helpers import log, pick_profile, get_c_user, get_account_name


async def create_browser(p, session_file, headless=True):
    """Buat stealth browser + context dengan storage_state."""
    prof = pick_profile(session_file)
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox", "--disable-dev-shm-usage",
        f"--window-size={prof['vp']['width']},{prof['vp']['height']}",
    ]
    browser = await p.chromium.launch(headless=headless, args=args)

    ctx_kw = {
        "viewport": prof["vp"],
        "user_agent": prof["ua"],
        "is_mobile": False, "has_touch": False,
        "device_scale_factor": prof["scale"],
        "locale": "id-ID", "timezone_id": "Asia/Jakarta",
        "extra_http_headers": {
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Sec-CH-UA": prof["chua"],
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f'"{prof["platform"]}"',
        },
    }
    # Validate JSON before loading
    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                json.load(f)  # parse check
            ctx_kw["storage_state"] = session_file
        except Exception as e:
            log(f"⚠️ Sesi {os.path.basename(session_file)} korup: {e}")

    context = await browser.new_context(**ctx_kw)

    # Stealth JS injection
    cores, mem, vendor, gpu = prof["cores"], prof["mem"], prof["vendor"], prof["gpu"]
    await context.add_init_script(f"""
    (() => {{
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {cores} }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {mem} }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => 0 }});
        const gp = (fn) => function(p) {{
            if (p === 0x9245) return '{vendor}';
            if (p === 0x9246) return '{gpu}';
            return fn.apply(this, arguments);
        }};
        try {{
            WebGLRenderingContext.prototype.getParameter = gp(WebGLRenderingContext.prototype.getParameter);
            WebGL2RenderingContext.prototype.getParameter = gp(WebGL2RenderingContext.prototype.getParameter);
        }} catch(e) {{}}
        window.chrome = {{ runtime: {{}}, loadTimes: () => ({{}}), csi: () => ({{}}) }};
    }})();
    """)

    return browser, context


async def save_session(context, session_file, name=""):
    """Simpan cookie ke file JSON secara atomik."""
    tmp = session_file + ".tmp"
    try:
        state = await context.storage_state()
        if name:
            state["meta"] = {"name": name}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        if os.path.exists(session_file):
            os.remove(session_file)
        os.rename(tmp, session_file)
        log(f"💾 Sesi disimpan: {os.path.basename(session_file)}")
    except Exception as e:
        log(f"❌ Gagal save sesi: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)


async def is_logged_in(page):
    """Cek apakah user ter-login di Facebook."""
    try:
        url = page.url.lower()
        if "login" in url or "checkpoint" in url or "recover" in url:
            return False
        cookies = await page.context.cookies()
        if any(c.get("name") == "c_user" for c in cookies):
            # Double-check: no checkpoint text in body
            try:
                body = (await page.locator("body").inner_text(timeout=2000)).lower()
                for kw in config.CHECKPOINT_TEXTS:
                    if kw in body:
                        return False
            except Exception:
                pass
            return True
        # Profile-selector page (multi-account) = NOT logged in
        try:
            body = (await page.locator("body").inner_text(timeout=1500)).lower()
            if any(kw in body for kw in ["gunakan profil lain", "use another profile", "jelajahi hal-hal"]):
                return False
            if any(kw in body for kw in ["masuk", "log in", "daftar"]):
                return False
        except Exception:
            pass
        return False
    except Exception:
        return False


async def check_restriction(page):
    """Cek apakah akun kena pembatasan FB. Return (bool, reason)."""
    try:
        for sel in ['div[role="dialog"]', 'div[role="alert"]', 'div[aria-live="polite"]']:
            loc = page.locator(sel)
            cnt = await loc.count()
            for i in range(min(cnt, 5)):
                el = loc.nth(i)
                try:
                    txt = (await el.inner_text(timeout=200)).lower()
                    for kw in config.FAIL_TEXTS:
                        if kw in txt:
                            return True, kw
                except Exception:
                    continue
    except Exception:
        pass
    return False, ""


async def goto(page, url, timeout_ms=20000):
    """Navigasi dengan fallback."""
    try:
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        return True
    except Exception:
        try:
            await page.goto(url, timeout=12000, wait_until="commit")
            await page.wait_for_timeout(800)
            return True
        except Exception:
            return False


async def human_activity(page, duration_sec, tag=""):
    """
    Simulasi aktivitas manusia selama jeda panjang.
    - Scroll feed grup/home secara natural
    - Kadang buka notifikasi
    - Kadang hover elemen
    - Jeda acak antar aksi (5-20 detik)
    """
    import random
    log(f"🧑 Aktivitas manusia selama {duration_sec:.0f}s...", tag)
    end_time = time.time() + duration_sec

    activities = [
        "scroll_feed",
        "scroll_feed",
        "scroll_feed",  # lebih sering scroll
        "open_notifications",
        "open_home",
        "hover_posts",
    ]

    while time.time() < end_time:
        remaining = end_time - time.time()
        if remaining < 10:
            break

        action = random.choice(activities)
        try:
            if action == "scroll_feed":
                # Scroll feed secara natural (halaman saat ini)
                scroll_steps = random.randint(3, 7)
                for _ in range(scroll_steps):
                    if time.time() >= end_time:
                        break
                    scroll_amount = random.randint(200, 600)
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await page.wait_for_timeout(random.randint(2000, 5000))
                log(f"   📜 Scroll feed ({scroll_steps}x)", tag)

            elif action == "open_notifications":
                # Buka halaman notifikasi
                await goto(page, "https://www.facebook.com/notifications/", timeout_ms=15000)
                await page.wait_for_timeout(random.randint(3000, 8000))
                # Scroll notifikasi
                for _ in range(random.randint(2, 4)):
                    if time.time() >= end_time:
                        break
                    await page.evaluate(f"window.scrollBy(0, {random.randint(200, 400)})")
                    await page.wait_for_timeout(random.randint(2000, 4000))
                log(f"   🔔 Baca notifikasi", tag)

            elif action == "open_home":
                # Buka home feed
                await goto(page, "https://www.facebook.com/", timeout_ms=15000)
                await page.wait_for_timeout(random.randint(3000, 8000))
                # Scroll home feed
                for _ in range(random.randint(3, 6)):
                    if time.time() >= end_time:
                        break
                    await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
                    await page.wait_for_timeout(random.randint(2000, 5000))
                log(f"   🏠 Baca home feed", tag)

            elif action == "hover_posts":
                # Hover pada elemen post di feed
                try:
                    posts = page.locator('div[role="article"]')
                    cnt = await posts.count()
                    if cnt > 0:
                        idx = random.randint(0, min(cnt - 1, 5))
                        post = posts.nth(idx)
                        await post.hover(timeout=2000)
                        await page.wait_for_timeout(random.randint(1000, 3000))
                        log(f"   🖱️ Hover post #{idx}", tag)
                except Exception:
                    pass

        except Exception:
            pass

        # Jeda acak antar aktivitas (5-20 detik)
        pause = random.randint(5, 20)
        if time.time() + pause > end_time:
            pause = max(1, int(end_time - time.time()))
        await page.wait_for_timeout(pause * 1000)

    log(f"✅ Aktivitas selesai", tag)
