"""
joiner.py — Cek membership + auto join grup.
"""
import re, asyncio, random
from typing import Tuple
from playwright.async_api import Page
import config
from helpers import log, normalize_url
from browser import goto, is_logged_in, check_restriction


async def check_membership(page, group_url, tag=""):
    """Return: JOINED, PENDING, NOT_JOINED, RESTRICTED, NOT_LOGGED_IN, UNKNOWN."""
    url, gid = normalize_url(group_url)

    # Navigasi ke grup jika belum
    curr = page.url.lower()
    need_nav = True
    if "/groups/" in curr and gid and gid.lower() in curr:
        need_nav = False
    elif re.search(r"/groups/\d+", curr):
        need_nav = False
    if need_nav:
        await goto(page, url, timeout_ms=20000)
        await page.wait_for_timeout(500)

    # Cek restriction
    is_res, reason = await check_restriction(page)
    if is_res:
        return "RESTRICTED"

    # Cek login
    if "login" in page.url.lower() or "checkpoint" in page.url.lower():
        return "NOT_LOGGED_IN"
    if not await is_logged_in(page):
        return "NOT_LOGGED_IN"

    # Cek tombol status
    scope = page.locator('div[role="main"]').first
    scopes = [scope, page] if await scope.count() > 0 else [page]

    # JOINED — cek duluan (prioritas tinggi)
    # Pakai aria-label untuk exact match, has-text untuk fallback
    for s in scopes:
        for txt in config.JOINED_TEXTS:
            try:
                # aria-label = exact match (tidak ada masalah substring)
                loc_aria = s.locator(f'div[role="button"][aria-label="{txt}"]')
                if await loc_aria.count() > 0 and await loc_aria.first.is_visible(timeout=300):
                    return "JOINED"
                # has-text = cek apakah teks EXACT match (bukan substring)
                loc_text = s.locator(f'div[role="button"]:has-text("{txt}")')
                cnt = await loc_text.count()
                for i in range(min(cnt, 5)):
                    el = loc_text.nth(i)
                    try:
                        inner = (await el.inner_text(timeout=300)).strip().lower()
                        if inner == txt.lower():  # EXACT match
                            if await el.is_visible(timeout=300):
                                return "JOINED"
                    except Exception:
                        continue
            except Exception:
                continue

    # PENDING
    for s in scopes:
        for txt in config.PENDING_TEXTS:
            try:
                loc = s.locator(f'div[role="button"][aria-label="{txt}"], div[role="button"]:has-text("{txt}")')
                if await loc.count() > 0 and await loc.first.is_visible(timeout=300):
                    return "PENDING"
            except Exception:
                continue

    # NOT_JOINED
    for s in scopes:
        for txt in config.JOIN_TEXTS:
            try:
                loc = s.locator(f'div[role="button"][aria-label="{txt}"], div[role="button"]:has-text("{txt}")')
                if await loc.count() > 0 and await loc.first.is_visible(timeout=300):
                    return "NOT_JOINED"
            except Exception:
                continue

    # Cek composer trigger = sudah anggota
    for txt in config.TRIGGER_TEXTS:
        try:
            loc = page.locator(f'div[role="button"]:has-text("{txt}"), span:has-text("{txt}")').first
            if await loc.count() > 0 and await loc.is_visible(timeout=300):
                return "JOINED"
        except Exception:
            continue

    return "UNKNOWN"


async def execute_join(page, group_url, tag=""):
    """Join grup. Return True jika berhasil."""
    url, gid = normalize_url(group_url)
    log(f"➕ Join grup: {group_url}", tag)

    # Cari tombol Join — comprehensive: text + aria-label + href + structural
    join_btn = None

    # Strategy A: text-based (multibahasa)
    for txt in config.JOIN_TEXTS:
        for sel in [f'div[role="button"][aria-label="{txt}"]',
                    f'div[role="button"]:has-text("{txt}")',
                    f'button:has-text("{txt}")',
                    f'a[role="button"]:has-text("{txt}")']:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    join_btn = loc
                    break
            except Exception:
                continue
        if join_btn:
            break

    # Strategy B: href-based (link join)
    if not join_btn:
        try:
            loc = page.locator('a[href*="/groups/join/"]').first
            if await loc.count() > 0 and await loc.is_visible(timeout=300):
                join_btn = loc
        except Exception:
            pass

    # Strategy C: scroll ke atas lalu cari lagi (FB hide tombol saat scroll)
    if not join_btn:
        try:
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            for txt in config.JOIN_TEXTS:
                loc = page.locator(f'div[role="button"]:has-text("{txt}")').first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    join_btn = loc
                    break
        except Exception:
            pass

    # Strategy D: reload + cari lagi
    if not join_btn:
        log(f"   🔄 Reload (cari tombol Join)...", tag)
        await page.reload(wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        for txt in config.JOIN_TEXTS:
            for sel in [f'div[role="button"][aria-label="{txt}"]',
                        f'div[role="button"]:has-text("{txt}")',
                        f'button:has-text("{txt}")']:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=300):
                        join_btn = loc
                        break
                except Exception:
                    continue
            if join_btn:
                break

    if not join_btn:
        log(f"   ❌ Tombol Join tidak ditemukan", tag)
        return False

    # Klik tombol Join — retry 2x
    clicked = False
    for attempt in range(2):
        try:
            await join_btn.scroll_into_view_if_needed(timeout=2000)
            await page.wait_for_timeout(300)
            await join_btn.click(timeout=3000)
            await page.wait_for_timeout(1500)
            clicked = True
            break
        except Exception:
            try:
                await join_btn.click(force=True, timeout=3000)
                await page.wait_for_timeout(1500)
                clicked = True
                break
            except Exception as e:
                if attempt == 0:
                    log(f"   ⚠️ Retry klik Join...", tag)
                else:
                    log(f"   ❌ Gagal klik Join: {e}", tag)

    if not clicked:
        return False

    # Handle modal konfirmasi / Q&A
    await _handle_join_modal(page, tag)

    # Polling status
    poll_max = 10  # 10 detik
    for i in range(poll_max):
        await page.wait_for_timeout(1000)
        # Cek restriction
        is_res, _ = await check_restriction(page)
        if is_res:
            return False
        status = await check_membership(page, group_url, tag)
        if status in ["JOINED", "PENDING"]:
            log(f"   ✅ Join berhasil! Status: {status}", tag)
            return True
        if status in ["RESTRICTED", "NOT_LOGGED_IN"]:
            return False

    # Retry: handle modal lagi
    await _handle_join_modal(page, tag)
    await page.wait_for_timeout(2000)
    status = await check_membership(page, group_url, tag)
    if status in ["JOINED", "PENDING"]:
        log(f"   ✅ Join berhasil! Status: {status}", tag)
        return True

    # Retry 2: reload halaman grup lalu cek lagi
    log(f"   🔄 Reload halaman grup (cek status join)...", tag)
    await goto(page, group_url, timeout_ms=20000)
    await page.wait_for_timeout(2000)
    status = await check_membership(page, group_url, tag)
    if status in ["JOINED", "PENDING"]:
        log(f"   ✅ Join berhasil! Status: {status}", tag)
        return True

    # Cek apakah grup private (butuh approval admin) — tombol "Minta Bergabung"
    for txt in ["Minta Bergabung", "Minta bergabung", "Request to join", "Solicitar unirse"]:
        try:
            loc = page.locator(f'div[role="button"][aria-label="{txt}"], div[role="button"]:has-text("{txt}")')
            if await loc.count() > 0 and await loc.first.is_visible(timeout=300):
                log(f"   ⏳ Grup private — join request dikirim, menunggu admin approval.", tag)
                return True  # anggap sukses (pending admin)
        except Exception:
            continue

    log(f"   ❌ Gagal join. Status: {status}", tag)
    return False


async def _handle_join_modal(page, tag=""):
    """Handle modal konfirmasi join (Q&A, checkbox, tombol submit)."""
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        if cnt == 0:
            return False

        for i in range(min(cnt, 3)):
            d = dialogs.nth(i)
            try:
                if not await d.is_visible(timeout=400):
                    continue
            except Exception:
                continue

            # Cek modal login
            try:
                txt = (await d.inner_text()).lower()
                if any(t in txt for t in ["log in", "masuk ke facebook", "masuk untuk melanjutkan"]):
                    return False
            except Exception:
                pass

            # Isi Q&A dengan jawaban acak
            textareas = d.locator('textarea, input[type="text"], div[contenteditable="true"]')
            ta_count = await textareas.count()
            if ta_count > 0:
                answers = list(config.QA_ANSWERS)
                random.shuffle(answers)
                for j in range(ta_count):
                    ta = textareas.nth(j)
                    try:
                        if not await ta.is_visible(timeout=300):
                            continue
                        ans = answers[j % len(answers)]
                        await ta.click(timeout=500)
                        await ta.fill(ans)
                        await page.wait_for_timeout(300)
                    except Exception:
                        try:
                            await ta.press_sequentially(ans, delay=10)
                        except Exception:
                            pass

            # Checkbox
            checkboxes = d.locator('input[type="checkbox"], div[role="checkbox"]')
            cb_count = await checkboxes.count()
            for c in range(cb_count):
                cb = checkboxes.nth(c)
                try:
                    if await cb.is_visible(timeout=300):
                        checked = await cb.get_attribute("aria-checked")
                        if checked != "true":
                            await cb.click(timeout=1000)
                            await page.wait_for_timeout(300)
                except Exception:
                    pass

            # Klik tombol konfirmasi
            for sel_text in ["Gabung ke grup", "Join group", "Gabung", "Submit", "Kirim",
                             "Selesai", "Done", "Lanjutkan", "Continue", "Setuju"]:
                try:
                    btn = d.locator(f'div[role="button"]:has-text("{sel_text}"), button:has-text("{sel_text}")').first
                    if await btn.count() > 0 and await btn.is_visible(timeout=400):
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(1500)
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False
