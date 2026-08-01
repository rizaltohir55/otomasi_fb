"""
poster.py — Post ke grup: buka komposer, ketik caption, upload media, submit.
"""
import os, re, asyncio, time
from typing import Tuple, Optional, List
from playwright.async_api import Page
import config
from helpers import log
from browser import check_restriction, goto


async def _find_trigger(page):
    """Cari tombol trigger komposer ('Tulis sesuatu...', 'Write something...')."""
    scope = page.locator('div[role="main"]').first
    scopes = [scope, page] if await scope.count() > 0 else [page]
    for s in scopes:
        for txt in config.TRIGGER_TEXTS:
            for sel in [f'div[role="button"][aria-label="{txt}"]',
                        f'div[role="button"]:has-text("{txt}")',
                        f'span:has-text("{txt}")']:
                try:
                    loc = s.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=300):
                        return loc
                except Exception:
                    continue
    return None


async def _find_textbox(page):
    """Cari textbox di dalam dialog komposer aktif."""
    for sel in ['div[role="dialog"] div[contenteditable="true"]',
                'div[role="textbox"][contenteditable="true"]']:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible(timeout=500):
                return loc
        except Exception:
            continue
    return None


async def _find_submit(page):
    """Cari tombol Post/Posting di dalam dialog."""
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        for i in range(min(cnt, 5)):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=200):
                continue
            btns = d.locator('div[role="button"], button')
            bc = await btns.count()
            for j in range(bc):
                b = btns.nth(j)
                try:
                    if not await b.is_visible(timeout=200):
                        continue
                    lbl = (await b.get_attribute("aria-label") or "").strip().lower()
                    txt = (await b.inner_text()).strip().lower()
                    for t in config.SUBMIT_TEXTS:
                        if t.lower() in [lbl, txt] or txt.startswith(t.lower()) or lbl.startswith(t.lower()):
                            # Skip toolbar buttons
                            skip = ["tambah", "add", "foto", "photo", "tag", "check", "feeling"]
                            if any(s in lbl or s in txt for s in skip):
                                continue
                            return b
                except Exception:
                    continue
    except Exception:
        pass
    return None


async def _dialog_active(page):
    """Cek apakah dialog komposer aktif."""
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        for i in range(min(cnt, 3)):
            d = dialogs.nth(i)
            if await d.is_visible(timeout=300):
                tb = d.locator('div[contenteditable="true"]').first
                if await tb.count() > 0:
                    return True
                for t in config.SUBMIT_TEXTS:
                    pb = d.locator(f'div[role="button"]:has-text("{t}")').first
                    if await pb.count() > 0:
                        return True
    except Exception:
        pass
    return False


async def _close_dialog(page, tag=""):
    """Tutup dialog komposer."""
    for sel in ['div[role="dialog"] div[role="button"][aria-label="Tutup"]',
                'div[role="dialog"] div[role="button"][aria-label="Close"]']:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible(timeout=300):
                await btn.click(timeout=1500)
                await page.wait_for_timeout(500)
                if not await _dialog_active(page):
                    return True
        except Exception:
            continue
    for _ in range(3):
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)
            if not await _dialog_active(page):
                return True
        except Exception:
            break
    return False


def _detect_fail(page, tag=""):
    """Cek rate-limit/error di dialog. Return (bool, reason)."""
    pass  # placeholder, akan di-inline di submit


async def post_to_group(page, group_url, caption, media_paths, tag=""):
    """
    Post ke grup. Return (success: bool, reason: str).
    reason ASLI — bukan 'unknown'.
    """
    gid = ""
    m = re.search(r"groups/([0-9a-zA-Z._-]+)", group_url)
    if m:
        gid = m.group(1).rstrip("/")

    log(f"🌐 Post ke: {group_url}", tag)

    # ── 1. Buka komposer ─────────────────────────────────────────────────────
    is_res, res_reason = await check_restriction(page)
    if is_res:
        return False, f"restricted: {res_reason}"

    # Navigasi ke grup
    curr = page.url.lower()
    need_nav = True
    if "/groups/" in curr and gid and gid.lower() in curr:
        need_nav = False
    if need_nav:
        await goto(page, group_url)

    # Cek apakah komposer sudah aktif (mungkin dari grup sebelumnya)
    if await _dialog_active(page):
        # Cek apakah ini komposer grup yang benar
        try:
            curr_gid = re.search(r"/groups/([0-9a-zA-Z._-]+)", page.url.lower())
            curr_gid = curr_gid.group(1) if curr_gid else ""
            if gid and curr_gid and gid != curr_gid:
                log(f"   ⚠️ Komposer bocor dari grup lain. Tutup.", tag)
                await _close_dialog(page, tag)
                await goto(page, group_url)
        except Exception:
            pass

    if not await _dialog_active(page):
        # Cari trigger — coba 3 strategi berturut-turut
        trigger = await _find_trigger(page)

        # Strategi 1: tab Diskusi (grup Jual-Beli)
        if not trigger:
            try:
                disc = page.locator('a[role="tab"]:has-text("Diskusi"), a[role="tab"]:has-text("Discussion")').first
                if await disc.count() > 0:
                    await disc.click(timeout=2000)
                    await page.wait_for_timeout(800)
                    trigger = await _find_trigger(page)
            except Exception:
                pass

        # Strategi 2: reload halaman
        if not trigger:
            log(f"   🔄 Reload halaman (komposer belum muncul)...", tag)
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            trigger = await _find_trigger(page)
            if not trigger:
                try:
                    disc = page.locator('a[role="tab"]:has-text("Diskusi"), a[role="tab"]:has-text("Discussion")').first
                    if await disc.count() > 0:
                        await disc.click(timeout=2000)
                        await page.wait_for_timeout(800)
                        trigger = await _find_trigger(page)
                except Exception:
                    pass

        # Strategi 3: navigasi langsung ke URL /discussion/
        if not trigger and gid:
            disc_url = f"https://www.facebook.com/groups/{gid}/discussion/"
            log(f"   🔄 Navigasi ke {disc_url}...", tag)
            await goto(page, disc_url, timeout_ms=20000)
            await page.wait_for_timeout(2000)
            trigger = await _find_trigger(page)

        # Strategi 4: scroll halaman ke atas + tunggu 3 detik (FB lazy-load)
        if not trigger:
            log(f"   🔄 Scroll + tunggu (lazy-load)...", tag)
            try:
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, 300)")
                await page.wait_for_timeout(2000)
                trigger = await _find_trigger(page)
            except Exception:
                pass

        if trigger:
            try:
                await trigger.click(timeout=3000)
            except Exception:
                await trigger.click(force=True, timeout=3000)
            await page.wait_for_timeout(800)

    if not await _dialog_active(page):
        return False, "composer_tidak_terbuka"

    # ── 2. Ketik caption ─────────────────────────────────────────────────────
    if caption:
        tb = await _find_textbox(page)
        if not tb:
            await _close_dialog(page, tag)
            return False, "textbox_tidak_ditemukan"
        try:
            await tb.click(timeout=2000)
        except Exception:
            await tb.focus()
        await page.wait_for_timeout(100)

        # Clear draft via JS
        try:
            await page.evaluate("""() => {
                const el = document.activeElement;
                if (!el) return;
                const sel = window.getSelection();
                if (!sel) return;
                const r = document.createRange();
                r.selectNodeContents(el);
                sel.removeAllRanges();
                sel.addRange(r);
            }""")
            await page.keyboard.press("Backspace")
        except Exception:
            pass
        await page.wait_for_timeout(100)

        # Ketik per baris
        for i, line in enumerate(caption.splitlines()):
            line = line.strip()
            if line:
                await tb.press_sequentially(line, delay=config.TYPE_DELAY_MS)
            if i < caption.count("\n"):
                await page.keyboard.press("Shift+Enter")
        await page.wait_for_timeout(300)
        log(f"   ✍️ Caption diketik ({len(caption)} chars)", tag)

    # ── 3. Upload media ──────────────────────────────────────────────────────
    if media_paths:
        valid = [p for p in media_paths if os.path.exists(p) and os.path.getsize(p) > 0
                 and os.path.getsize(p) <= config.MAX_MEDIA_MB * 1024 * 1024]
        if valid:
            # Cari file input
            file_input = None
            for sel in ['div[role="dialog"] input[type="file"]',
                        'form input[type="file"]', 'input[type="file"]']:
                try:
                    inp = page.locator(sel).first
                    if await inp.count() > 0:
                        file_input = inp
                        break
                except Exception:
                    continue

            if file_input:
                try:
                    await file_input.set_input_files(valid)
                    await page.wait_for_timeout(1500)
                    log(f"   🖼️ {len(valid)} gambar diupload", tag)
                except Exception as e:
                    log(f"   ⚠️ Upload gagal: {e}", tag)
            else:
                log(f"   ⚠️ File input tidak ditemukan", tag)

    # ── 4. Submit ────────────────────────────────────────────────────────────
    await page.wait_for_timeout(300)
    is_res, res_reason = await check_restriction(page)
    if is_res:
        await _close_dialog(page, tag)
        return False, f"restricted: {res_reason}"

    submit_btn = await _find_submit(page)
    if not submit_btn:
        await _close_dialog(page, tag)
        return False, "tombol_post_tidak_ditemukan"

    # Tunggu tombol tidak disabled
    for _ in range(30):
        ad = await submit_btn.get_attribute("aria-disabled")
        if ad != "true":
            break
        await page.wait_for_timeout(500)

    url_before = page.url
    log(f"   👉 Klik Post...", tag)
    try:
        await submit_btn.scroll_into_view_if_needed()
        await page.wait_for_timeout(200)
        await submit_btn.click(timeout=3000)
    except Exception:
        await submit_btn.click(force=True, timeout=3000)

    # ── 5. Polling 30 detik — cek SUKSES / GAGAL ─────────────────────────────
    log(f"   ⏳ Menunggu publikasi (max 30s)...", tag)
    for i in range(60):  # 60 x 500ms = 30 detik
        await page.wait_for_timeout(500)

        # (a) Komposer tertutup = SUKSES
        if not await _dialog_active(page):
            log(f"   ✅ POST BERHASIL! (komposer tertutup)", tag)
            return True, "success"

        # (b) URL berubah = redirect = SUKSES
        url_now = page.url
        if url_now != url_before and "login" not in url_now.lower():
            log(f"   ✅ POST BERHASIL! (URL redirect)", tag)
            return True, "success_redirect"

        # (c) Cek rate-limit / error di dialog
        try:
            dialog = page.locator('div[role="dialog"]').first
            if await dialog.count() > 0:
                txt = (await dialog.inner_text(timeout=500)).lower()
                for kw in config.FAIL_TEXTS:
                    if kw in txt:
                        log(f"   ⛔ GAGAL: {kw}", tag)
                        await _close_dialog(page, tag)
                        return False, f"rate_limited: {kw}"
                # (d) Pending admin = SUKSES
                if any(kw in txt for kw in ["persetujuan", "approval", "admin", "pending", "dikirim"]):
                    log(f"   ⏳ POST TERKIRIM — Menunggu persetujuan admin", tag)
                    return True, "pending_admin"
        except Exception:
            pass

        if (i + 1) % 10 == 0:
            log(f"   ⏳ Masih menunggu... ({(i+1)*500}ms)", tag)

    # ── 6. Fallback: Control+Enter ───────────────────────────────────────────
    log(f"   🔄 Fallback: Ctrl+Enter...", tag)
    if await _dialog_active(page):
        tb = await _find_textbox(page)
        if tb:
            try:
                await tb.click(timeout=1000)
                await page.wait_for_timeout(100)
                await page.keyboard.press("Control+Enter")
                await page.wait_for_timeout(6000)
            except Exception:
                pass

    if not await _dialog_active(page):
        log(f"   ✅ POST BERHASIL via Ctrl+Enter!", tag)
        return True, "success_ctrl_enter"

    url_now = page.url
    if url_now != url_before and "login" not in url_now.lower():
        log(f"   ✅ POST BERHASIL! (redirect setelah fallback)", tag)
        return True, "success_redirect"

    # ── 7. CAPTURE DIALOG ASLI untuk reason ──────────────────────────────────
    dialog_text = ""
    try:
        dialog = page.locator('div[role="dialog"]').first
        if await dialog.count() > 0:
            dialog_text = (await dialog.inner_text(timeout=2000)).strip()
            log(f"   📋 Dialog asli:", tag)
            for line in dialog_text[:500].split("\n"):
                line = line.strip()
                if line:
                    log(f"      | {line}", tag)
    except Exception:
        pass

    # Cek body untuk indikator sukses
    try:
        body = (await page.locator("body").inner_text(timeout=2000)).lower()
        for kw in ["post berhasil", "published", "postingan berhasil", "your post"]:
            if kw in body:
                log(f"   ✅ POST BERHASIL (body indicator: {kw})", tag)
                await _close_dialog(page, tag)
                return True, "success_body"
    except Exception:
        pass

    if not dialog_text:
        log(f"   ✅ Dialog kosong — post kemungkinan berhasil", tag)
        return True, "success_dialog_empty"

    # Beri reason ASLI
    dl = dialog_text.lower()
    if "membatasi" in dl or "coba lagi" in dl:
        reason = "rate_limited"
    elif "spam" in dl:
        reason = "spam_detected"
    elif "persetujuan" in dl or "admin" in dl:
        log(f"   ⏳ POST TERKIRIM — pending admin", tag)
        return True, "pending_admin"
    elif "tidak dapat" in dl or "can't" in dl:
        reason = f"fb_blocked: {dialog_text[:200]}"
    else:
        reason = f"dialog: {dialog_text[:300]}"

    log(f"   ❌ GAGAL — Reason: {reason}", tag)
    await _close_dialog(page, tag)
    return False, reason
