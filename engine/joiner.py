"""
engine/joiner.py
Modul Otomasi Bergabung Ke Grup Facebook (Auto Join Group Engine).
"""
import re
import asyncio
from typing import Tuple, Optional
from playwright.async_api import Page, Locator

import config
from utils.helpers import log, normalize_group_url
from utils.browser import random_human_delay, safe_goto
from engine.dom_analyzer import dismiss_all_overlays
from engine.browser import verify_login_status, check_account_restriction
from engine.selectors import (
    JOIN_GROUP_SELECTORS,
    JOINED_INDICATOR_SELECTORS,
    PENDING_INDICATOR_SELECTORS,
    DESKTOP_COMPOSER_TRIGGERS,
)


async def check_membership_status(page: Page, target_url: str, worker_tag: str = "") -> str:
    """
    Periksa status keanggotaan akun pada grup target.
    Mengembalikan salah satu status: 'JOINED', 'PENDING', 'NOT_JOINED', 'RESTRICTED', 'NOT_LOGGED_IN', atau 'UNKNOWN'.
    Mendukung berbagai layout DOM Facebook & multi-bahasa.
    """
    desktop_url, _, gid = normalize_group_url(target_url)

    # Cek jika browser belum berada di halaman grup (atau terlempar ke grup lain)
    curr_url = page.url.lower()
    need_nav = True
    if "/groups/" in curr_url:
        if gid and gid.lower() in curr_url:
            need_nav = False
        elif re.search(r"/groups/\d+", curr_url):
            # Jika URL berformat ID numerik pasca-redireksi, anggap sudah di grup
            need_nav = False

    if need_nav:
        await safe_goto(page, desktop_url, timeout_ms=20000)
        await page.wait_for_timeout(1000)

    # 1. Cek pembatasan akun (Restricted / Action Blocked)
    is_res, res_reason = await check_account_restriction(page)
    if is_res:
        log(f"   ⛔ TERDETEKSI PEMBATASAN AKUN FB: {res_reason}", worker_tag)
        return "RESTRICTED"

    # 2. Cek jika terlempar ke halaman login / checkpoint
    if "login" in page.url.lower() or "checkpoint" in page.url.lower() or "recover" in page.url.lower():
        return "NOT_LOGGED_IN"

    is_logged_in = await verify_login_status(page)
    if not is_logged_in:
        return "NOT_LOGGED_IN"

    await dismiss_all_overlays(page)

    # Scope pencarian: main_scope & page level
    main_scope = page.locator('div[role="main"]').first
    scopes = [main_scope, page] if await main_scope.count() > 0 else [page]

    # 3. PERIKSA TOMBOL STATUS SUDAH BERGABUNG ('JOINED') DAHULU
    for scope in scopes:
        for text in config.JOINED_INDICATOR_TEXTS:
            try:
                loc_label = scope.locator(f'div[role="button"][aria-label="{text}"]')
                if await loc_label.count() > 0 and await loc_label.first.is_visible(timeout=300):
                    return "JOINED"

                loc_text = scope.locator(f'div[role="button"]:has-text("{text}")')
                if await loc_text.count() > 0 and await loc_text.first.is_visible(timeout=300):
                    return "JOINED"
            except Exception:
                continue

        for sel in JOINED_INDICATOR_SELECTORS:
            try:
                loc = scope.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    return "JOINED"
            except Exception:
                continue

    # 4. PERIKSA TOMBOL STATUS PENDING ('PENDING')
    for scope in scopes:
        for text in config.PENDING_BUTTON_TEXTS:
            try:
                loc_label = scope.locator(f'div[role="button"][aria-label="{text}"], div[role="button"]:has-text("{text}")')
                if await loc_label.count() > 0 and await loc_label.first.is_visible(timeout=300):
                    return "PENDING"
            except Exception:
                continue

        for sel in PENDING_INDICATOR_SELECTORS:
            try:
                loc = scope.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    return "PENDING"
            except Exception:
                continue

    # 5. PERIKSA TOMBOL BELUM BERGABUNG ('NOT_JOINED')
    for scope in scopes:
        for text in config.JOIN_BUTTON_TEXTS:
            try:
                loc_label = scope.locator(f'div[role="button"][aria-label="{text}"]')
                if await loc_label.count() > 0 and await loc_label.first.is_visible(timeout=300):
                    return "NOT_JOINED"

                loc_text = scope.locator(f'div[role="button"]:has-text("{text}")')
                if await loc_text.count() > 0 and await loc_text.first.is_visible(timeout=300):
                    return "NOT_JOINED"
            except Exception:
                continue

        for sel in JOIN_GROUP_SELECTORS:
            try:
                loc = scope.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    return "NOT_JOINED"
            except Exception:
                continue

    # 6. PERIKSA ELEMEN KOMPOSER POSTINGAN ("Tulis sesuatu...") -> Indikator SUDAH BERGABUNG
    for scope in scopes:
        for comp_sel in DESKTOP_COMPOSER_TRIGGERS:
            try:
                loc_comp = scope.locator(comp_sel).first
                if await loc_comp.count() > 0 and await loc_comp.is_visible(timeout=300):
                    return "JOINED"
            except Exception:
                continue

    return "UNKNOWN"


async def handle_join_confirmation_modals(page: Page, worker_tag: str = "") -> bool:
    """
    Menangani dialog / modal konfirmasi pasca-klik tombol 'Bergabung dengan grup'.
    Mengisi pertanyaan keanggotaan admin, menandai checkbox aturan grup, dan menekan submit modal.
    """
    try:
        dialogs = page.locator('div[role="dialog"]')
        count = await dialogs.count()
        if count == 0:
            return False

        handled = False
        for i in range(count):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=400):
                continue

            dialog_text = (await d.inner_text()).lower()

            # 1. Cek jika modal adalah prompt login / sesi terputus
            if any(term in dialog_text for term in ["log in", "masuk ke facebook", "masuk untuk melanjutkan", "log in to continue", "iniciar sesión"]):
                log("   ⚠️ Modal login terdeteksi. Sesi akun membutuhkan login ulang!", worker_tag)
                return False

            # 2. Isi pertanyaan keanggotaan admin grup (textarea, input, contenteditable)
            textareas = d.locator('textarea, input[type="text"], div[role="textbox"][contenteditable="true"]')
            ta_count = await textareas.count()
            if ta_count > 0:
                log(f"   📋 Mengisi {ta_count} pertanyaan keanggotaan admin grup...", worker_tag)
                for j in range(ta_count):
                    ta = textareas.nth(j)
                    if await ta.is_visible(timeout=300):
                        try:
                            await ta.click(timeout=500)
                            await ta.fill("Setuju dengan aturan grup")
                            await page.wait_for_timeout(300)
                        except Exception:
                            try:
                                await ta.press_sequentially("Setuju dengan aturan grup", delay=10)
                            except Exception:
                                pass

            # 3. Tandai checkbox persetujuan aturan grup
            checkboxes = d.locator('input[type="checkbox"], div[role="checkbox"], label:has(input[type="checkbox"])')
            cb_count = await checkboxes.count()
            for c in range(cb_count):
                cb = checkboxes.nth(c)
                if await cb.is_visible(timeout=300):
                    try:
                        checked = await cb.get_attribute("aria-checked")
                        if checked != "true":
                            await cb.click(timeout=1000)
                            await page.wait_for_timeout(300)
                    except Exception:
                        pass

            # 4. Cari dan klik tombol konfirmasi / submit di dalam modal (Multilingual)
            confirm_selectors = [
                'div[role="button"][aria-label="Gabung ke grup"]',
                'div[role="button"][aria-label="Join group"]',
                'div[role="button"][aria-label="Gabung ke Grup"]',
                'div[role="button"][aria-label="Join Group"]',
                'div[role="button"][aria-label="Bergabung"]',
                'div[role="button"][aria-label="Unirse"]',
                'div[role="button"]:has-text("Kirim ke Admin")',
                'div[role="button"]:has-text("Submit to admins")',
                'div[role="button"]:has-text("Gabung ke grup")',
                'div[role="button"]:has-text("Join group")',
                'div[role="button"]:has-text("Gabung ke Grup")',
                'div[role="button"]:has-text("Join Group")',
                'div[role="button"]:has-text("Bergabung")',
                'div[role="button"]:has-text("Gabung")',
                'div[role="button"]:has-text("Submit")',
                'div[role="button"]:has-text("Kirim")',
                'div[role="button"]:has-text("Selesai")',
                'div[role="button"]:has-text("Done")',
                'div[role="button"]:has-text("Lanjutkan")',
                'div[role="button"]:has-text("Continue")',
                'div[role="button"]:has-text("Setuju")',
                'div[role="button"]:has-text("Agree")',
                'button:has-text("Kirim")',
                'button:has-text("Submit")',
                'button:has-text("Gabung")',
                'button:has-text("Join")',
                'button:has-text("Lanjutkan")',
            ]

            for sel in confirm_selectors:
                try:
                    c_btn = d.locator(sel).first
                    if await c_btn.count() > 0 and await c_btn.is_visible(timeout=400):
                        btn_txt = clean_text(await c_btn.inner_text()) or "Submit Modal"
                        log(f"   👉 Menekan tombol konfirmasi modal ({btn_txt})...", worker_tag)
                        try:
                            await c_btn.click(timeout=2000)
                        except Exception:
                            await c_btn.click(force=True, timeout=2000)
                        await page.wait_for_timeout(2000)
                        handled = True
                        break
                except Exception:
                    continue

            if not handled:
                # Fallback: Klik tombol aksi utama di bagian bawah modal
                try:
                    modal_btns = d.locator('div[role="button"]')
                    b_count = await modal_btns.count()
                    for idx in range(b_count - 1, -1, -1):
                        mb = modal_btns.nth(idx)
                        if await mb.is_visible(timeout=300):
                            label = (await mb.get_attribute("aria-label") or "").lower()
                            txt = (await mb.inner_text() or "").lower()
                            if not any(cl in label or cl in txt for cl in ["close", "tutup", "cancel", "batal"]):
                                log(f"   👉 Menekan tombol utama modal fallback ({txt or label})...", worker_tag)
                                await mb.click(force=True, timeout=2000)
                                await page.wait_for_timeout(2000)
                                handled = True
                                break
                except Exception:
                    pass

        return handled
    except Exception as e:
        log(f"   ⚠️ Gagal memproses modal konfirmasi bergabung: {e}", worker_tag)

    return False


async def execute_join_group(page: Page, target_url: str, worker_tag: str = "") -> bool:
    """
    Orkestrator Lengkap Otomasi Bergabung Ke Grup Facebook.
    """
    desktop_url, _, gid = normalize_group_url(target_url)
    log(f"\n-------------------------------------------------------", worker_tag)
    log(f"➕ PROSES BERGABUNG KE GRUP: {target_url}", worker_tag)
    log(f"-------------------------------------------------------", worker_tag)

    status = await check_membership_status(page, target_url, worker_tag)

    if status == "RESTRICTED":
        log("   ⛔ AKUN DIBATASI: Tidak dapat melakukan Auto Join.", worker_tag)
        return False

    if status == "NOT_LOGGED_IN":
        log("   ❌ Akun tidak ter-login atau sesi kedaluwarsa.", worker_tag)
        return False

    if status == "JOINED":
        log(f"   ✅ Akun SUDAH BERGABUNG di grup (ID={gid}).", worker_tag)
        return True

    if status == "PENDING":
        log(f"   ⏳ Permintaan bergabung sedang PENDING / Menunggu Persetujuan Admin.", worker_tag)
        return True

    log("   👉 Menekan tombol 'Bergabung dengan grup' / 'Join group'...", worker_tag)

    # Cari tombol Join Group di halaman utama
    join_btn = None
    for text in config.JOIN_BUTTON_TEXTS:
        try:
            loc_aria = page.locator(f'div[role="button"][aria-label="{text}"]')
            if await loc_aria.count() > 0 and await loc_aria.first.is_visible(timeout=300):
                join_btn = loc_aria.first
                break

            loc_text = page.locator(f'div[role="button"]:has-text("{text}")')
            if await loc_text.count() > 0 and await loc_text.first.is_visible(timeout=300):
                join_btn = loc_text.first
                break
        except Exception:
            continue

    if not join_btn:
        for sel in JOIN_GROUP_SELECTORS:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    join_btn = loc
                    break
            except Exception:
                continue

    if not join_btn:
        await page.wait_for_timeout(1200)
        for text in config.JOIN_BUTTON_TEXTS:
            try:
                loc_aria = page.locator(f'div[role="button"][aria-label="{text}"]')
                if await loc_aria.count() > 0 and await loc_aria.first.is_visible(timeout=300):
                    join_btn = loc_aria.first
                    break
            except Exception:
                continue

    if not join_btn:
        modal_handled = await handle_join_confirmation_modals(page, worker_tag)
        if not modal_handled:
            log("   ❌ Tombol 'Bergabung dengan grup' tidak ditemukan pada halaman.", worker_tag)
            return False

    if join_btn:
        try:
            await join_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            await join_btn.click(timeout=3000)
            await page.wait_for_timeout(2000)
        except Exception:
            try:
                await join_btn.click(force=True, timeout=3000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                log(f"   ⚠️ Gagal klik tombol join utama: {e}", worker_tag)

    # Tangani modal konfirmasi / pertanyaan jika ada
    await handle_join_confirmation_modals(page, worker_tag)

    # Dynamic polling hingga 5 detik untuk pembaruan status pasca-klik
    new_status = "UNKNOWN"
    for _ in range(5):
        await page.wait_for_timeout(1000)
        new_status = await check_membership_status(page, target_url, worker_tag)
        if new_status in ["JOINED", "PENDING"]:
            break

    if new_status in ["JOINED", "PENDING"]:
        log(f"   ✅ Berhasil bergabung ke grup! Status saat ini: {new_status}", worker_tag)
        return True
    else:
        # Re-check modal sekali lagi
        if await handle_join_confirmation_modals(page, worker_tag):
            await page.wait_for_timeout(2000)
            new_status = await check_membership_status(page, target_url, worker_tag)

        if new_status in ["JOINED", "PENDING"]:
            log(f"   ✅ Berhasil bergabung ke grup! Status saat ini: {new_status}", worker_tag)
            return True
        else:
            log(f"   ❌ Gagal bergabung ke grup (Status akhir: {new_status}).", worker_tag)
            return False


def clean_text(text: str) -> str:
    """Helper pembersih whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()
