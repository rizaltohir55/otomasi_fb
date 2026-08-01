"""
engine/composer.py
Modul Komposer Otomasi Postingan Grup Facebook Desktop 2026.
Arsitektur Pure ARIA Automation & High-Precision Execution.
"""
import os
import re
import asyncio
from typing import List, Tuple, Optional
from playwright.async_api import Page, Locator

import config
from utils.helpers import log, normalize_group_url
from utils.browser import random_human_delay, safe_goto
from utils.retry import validate_media_files
from engine.dom_analyzer import (
    dismiss_all_overlays,
    find_composer_trigger,
    find_caption_textbox,
    find_submit_button,
    get_active_composer_dialog,
)
from engine.browser import check_account_restriction, is_on_checkpoint_page
from engine.selectors import (
    DESKTOP_COMPOSER_TRIGGERS,
    CAPTION_TEXTBOX_SELECTORS,
    PHOTO_BUTTON_SELECTORS,
    FILE_INPUT_SELECTORS,
    POST_BUTTON_SELECTORS,
)


def extract_group_id_and_url(raw_url: str) -> Tuple[str, str]:
    """Ekstrak ID grup dan bentuk URL Desktop bersih (www.facebook.com)."""
    desktop_url, _, gid = normalize_group_url(raw_url)
    return gid, desktop_url


def extract_group_id_and_urls(raw_url: str) -> Tuple[str, str, str]:
    """Fungsi kompatibilitas: mengembalikan (gid, desktop_url, mobile_url)."""
    desktop_url, mobile_url, gid = normalize_group_url(raw_url)
    return gid, desktop_url, mobile_url


async def is_composer_active(page: Page) -> bool:
    """
    Periksa apakah modal dialog komposer postingan utama aktif di layar.
    """
    try:
        dialog = await get_active_composer_dialog(page)
        return dialog is not None
    except Exception:
        return False


async def handle_anonymous_post_modal(page: Page, worker_tag: str = "") -> bool:
    """
    Jika modal 'Postingan anonim' / 'Anonymous post' muncul, konfirmasi dengan menekan tombol konfirmasi.
    Mendukung berbagai bahasa (ID, EN, ES, FR, DE).
    """
    try:
        dialogs = page.locator('div[role="dialog"]')
        cnt = await dialogs.count()
        for i in range(cnt):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=300):
                continue
            text = (await d.inner_text()).lower()
            if any(kw in text for kw in ["postingan anonim", "anonymous post", "publicación anónima", "publication anonyme"]):
                log("   ℹ️ Modal 'Postingan anonim' terdeteksi. Menekan tombol konfirmasi...", worker_tag)
                btn = d.locator(
                    'div[role="button"]:has-text("Buat Postingan Anonim"), '
                    'div[role="button"]:has-text("Create Anonymous Post"), '
                    'div[role="button"]:has-text("Crear publicación anónima"), '
                    'button:has-text("Buat Postingan Anonim"), '
                    'button:has-text("Create Anonymous Post"), '
                    'div[role="button"]:has-text("Got It"), '
                    'div[role="button"]:has-text("Paham"), '
                    'div[role="button"]:has-text("Entendido")'
                ).first
                if await btn.count() > 0 and await btn.is_visible(timeout=800):
                    await btn.click()
                    await page.wait_for_timeout(1500)
                    log("   ✅ Modal 'Postingan anonim' dikonfirmasi!", worker_tag)
                    return True
    except Exception:
        pass
    return False


async def open_group_composer(page: Page, target_url: str, worker_tag: str = "") -> bool:
    """
    Buka halaman grup Facebook Desktop dan aktifkan modal komposer.
    Mendukung berbagai layout akun & grup (Grup standar, Grup Jual/Beli, Multi-bahasa).
    """
    gid, desktop_url = extract_group_id_and_url(target_url)
    log(f"   🎯 Membuka halaman komposer grup (ID={gid})...", worker_tag)

    # 0. Cek pembatasan akun FB terlebih dahulu
    is_res, res_reason = await check_account_restriction(page)
    if is_res:
        log(f"   ⛔ TERDETEKSI PEMBATASAN AKUN FB: {res_reason}", worker_tag)
        return False

    # 0b. Cek halaman checkpoint (2FA / verifikasi identitas)
    if await is_on_checkpoint_page(page):
        log(f"   🔐 Halaman CHECKPOINT terdeteksi. Tidak bisa membuka komposer.", worker_tag)
        return False

    # 1. Navigasi ke URL grup jika belum berada di halaman tersebut
    curr_url = page.url.lower()
    need_nav = True
    if "/groups/" in curr_url:
        if gid and gid.lower() in curr_url:
            need_nav = False
        elif re.search(r"/groups/\d+", curr_url):
            need_nav = False

    if need_nav:
        await safe_goto(page, desktop_url, timeout_ms=20000)

    await dismiss_all_overlays(page)
    await handle_anonymous_post_modal(page, worker_tag)

    # Cek jika komposer sudah aktif
    if await is_composer_active(page):
        log("   ✅ Komposer sudah aktif di layar.", worker_tag)
        return True

    # 2. Temukan trigger komposer via ARIA DOM Analyzer
    trigger_loc = await find_composer_trigger(page)
    
    # 3. Jika belum ditemukan (cth: grup Jual Beli / Buy-Sell Groups), coba klik tab "Diskusi" / "Discussion"
    if not trigger_loc:
        try:
            disc_tab_selectors = [
                'div[role="main"] a[role="tab"]:has-text("Diskusi")',
                'div[role="main"] a[role="tab"]:has-text("Discussion")',
                'a[role="tab"]:has-text("Diskusi")',
                'a[role="tab"]:has-text("Discussion")',
                'a:has-text("Diskusi")',
                'a:has-text("Discussion")',
                'a[role="tab"][href*="/discussion"]',
                'a[href*="/discussion"]',
            ]
            for sel in disc_tab_selectors:
                disc_tab = page.locator(sel).first
                if await disc_tab.count() > 0 and await disc_tab.is_visible(timeout=300):
                    log("   ℹ️ Berpindah ke tab 'Diskusi' / 'Discussion' grup Jual Beli...", worker_tag)
                    await disc_tab.click(timeout=1500)
                    await page.wait_for_timeout(1500)
                    trigger_loc = await find_composer_trigger(page)
                    if trigger_loc:
                        break
        except Exception:
            pass

    # 4. Fallback Navigasi Langsung ke URL /discussion/ jika tab click belum memicu
    if not trigger_loc and "/discussion" not in page.url:
        try:
            disc_url = f"https://www.facebook.com/groups/{gid}/discussion/"
            log(f"   🔄 Mencoba navigasi langsung ke URL Diskusi: {disc_url}", worker_tag)
            await page.goto(disc_url, timeout=config.NAVIGATION_TIMEOUT_MS, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await dismiss_all_overlays(page)
            trigger_loc = await find_composer_trigger(page)
        except Exception:
            pass

    # Klik trigger jika ditemukan
    if trigger_loc:
        try:
            try:
                await trigger_loc.click(timeout=2000)
            except Exception:
                await trigger_loc.click(force=True, timeout=2000)
            await page.wait_for_timeout(1200)
            await handle_anonymous_post_modal(page, worker_tag)
            if await is_composer_active(page):
                log("   ✅ Komposer berhasil terbuka via Dynamic ARIA Analyzer!", worker_tag)
                return True
        except Exception:
            pass

    # 5. Fallback via registry DESKTOP_COMPOSER_TRIGGERS
    for sel in DESKTOP_COMPOSER_TRIGGERS:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible(timeout=500):
                try:
                    await loc.click(timeout=2000)
                except Exception:
                    await loc.click(force=True, timeout=2000)
                await page.wait_for_timeout(1200)
                await handle_anonymous_post_modal(page, worker_tag)
                if await is_composer_active(page):
                    log("   ✅ Komposer berhasil terbuka via selector registry!", worker_tag)
                    return True
        except Exception:
            continue

    log("   ❌ Gagal membuka modal komposer grup.", worker_tag)
    return False


async def type_post_caption(page: Page, text_content: str, worker_tag: str = "") -> bool:
    """
    Mengetik caption postingan HANYA ke dalam modal dialog komposer utama.
    Menggunakan Shift+Enter antar baris agar format rapat tanpa baris kosong berlebih.
    """
    if not text_content:
        return True

    log("   ✍️  Mengetik caption postingan (format rapat & cepat)...", worker_tag)
    
    if not await is_composer_active(page):
        log("   ❌ Modal komposer tidak aktif. Dilarang mengetik caption!", worker_tag)
        return False

    textbox_loc = await find_caption_textbox(page)
    if not textbox_loc:
        log("   ❌ Textbox caption tidak ditemukan di dalam modal komposer.", worker_tag)
        return False

    try:
        try:
            await textbox_loc.click(timeout=2000)
        except Exception:
            try:
                await textbox_loc.click(force=True, timeout=1000)
            except Exception:
                await textbox_loc.focus()

        await page.wait_for_timeout(200)

        # Bersihkan jika ada draf teks terdahulu.
        # Catatan: Control+A pada contenteditable sering hanya memilih baris/paragraf saat ini,
        # bukan seluruh isi. Oleh karena itu, gunakan JS untuk memilih semua node,
        # lalu tekan Backspace. Fallback: klik 3x (triple-click = select all paragraph).
        try:
            # Pendekatan utama: JS selectAll pada elemen yang difokuskan
            await page.evaluate(
                """() => {
                    const el = document.activeElement;
                    if (!el) return;
                    const sel = window.getSelection();
                    if (!sel) return;
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }"""
            )
            await page.keyboard.press("Backspace")
        except Exception:
            # Fallback: triple-click + Backspace
            try:
                await textbox_loc.click(click_count=3, timeout=500)
                await page.keyboard.press("Backspace")
            except Exception:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
        await page.wait_for_timeout(100)

        # Pisahkan per baris dan ketik dengan Shift+Enter agar rapat
        raw_lines = text_content.splitlines()
        for idx, line in enumerate(raw_lines):
            line_str = line.strip()
            if line_str:
                await textbox_loc.press_sequentially(line_str, delay=config.TYPING_SPEED_MS)
            if idx < len(raw_lines) - 1:
                await page.keyboard.press("Shift+Enter")

        await page.wait_for_timeout(300)
        log("   ✅ Caption rapat berhasil diketik secara kilat!", worker_tag)
        return True
    except Exception as e:
        log(f"   ❌ Gagal mengetik caption: {e}", worker_tag)
        return False


async def attach_media_files(page: Page, image_paths: List[str], worker_tag: str = "") -> bool:
    """
    Upload berkas gambar ke dalam modal dialog komposer via file input HTML5 tersembunyi.

    Strategi:
    1. Validasi file (ada, ukuran <= MAX_MEDIA_SIZE_MB).
    2. Cari file input tersembunyi di DOM. Jika tidak ada, klik tombol Photo/video.
    3. Coba set_input_files pada file input.
    4. Fallback: pakai page.expect_file_chooser() + klik tombol photo.
    """
    if not image_paths:
        return True

    # 1. Validate file paths & sizes
    valid_paths, skipped = validate_media_files(image_paths)
    for path, reason in skipped:
        log(f"   ⚠️ Media diskip: {os.path.basename(path)} ({reason})", worker_tag)
    if not valid_paths:
        log("   ⚠️ Tidak ada berkas gambar valid untuk diunggah.", worker_tag)
        return False

    log(f"   🖼️  Mengunggah {len(valid_paths)} berkas gambar...", worker_tag)

    if not await is_composer_active(page):
        log("   ❌ Modal komposer tidak aktif. Upload dibatalkan.", worker_tag)
        return False

    # 2. Aktifkan area photo/video jika file input belum ter-render di DOM
    file_input = page.locator('div[role="dialog"] input[type="file"]').first
    try:
        if await file_input.count() == 0:
            for photo_sel in PHOTO_BUTTON_SELECTORS:
                try:
                    p_btn = page.locator(photo_sel).first
                    if await p_btn.count() > 0 and await p_btn.is_visible(timeout=500):
                        await p_btn.click(timeout=1500)
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
    except Exception:
        pass

    # 3. Cari file input di dalam modal dialog atau form
    file_input_loc = None
    for sel in FILE_INPUT_SELECTORS:
        try:
            inp = page.locator(sel).first
            if await inp.count() > 0:
                file_input_loc = inp
                break
        except Exception:
            continue

    # 4a. Pendekatan utama: set_input_files pada elemen input tersembunyi
    if file_input_loc:
        try:
            await file_input_loc.set_input_files(valid_paths)
            # Menunggu rendering pratinjau gambar oleh Facebook
            await page.wait_for_timeout(3000)
            log("   ✅ Berkas gambar berhasil diunggah via input!", worker_tag)
            return True
        except Exception as e:
            log(f"   ⚠️ Gagal upload via set_input_files: {e}. Mencoba fallback filechooser...", worker_tag)

    # 4b. Fallback: gunakan page.expect_file_chooser() + klik tombol photo
    # Pendekatan ini bekerja untuk layout FB yang file input-nya tidak terlihat/tidak bisa diakses.
    try:
        # Cari tombol photo/video yang bisa diklik
        photo_btn = None
        for photo_sel in PHOTO_BUTTON_SELECTORS:
            try:
                p_btn = page.locator(photo_sel).first
                if await p_btn.count() > 0 and await p_btn.is_visible(timeout=500):
                    photo_btn = p_btn
                    break
            except Exception:
                continue

        if photo_btn:
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                try:
                    await photo_btn.click(timeout=2000)
                except Exception:
                    await photo_btn.click(force=True, timeout=2000)
            file_chooser = await fc_info
            await file_chooser.set_files(valid_paths)
            await page.wait_for_timeout(3000)
            log("   ✅ Berkas gambar berhasil diunggah via filechooser fallback!", worker_tag)
            return True
    except Exception as e:
        log(f"   ❌ Fallback filechooser juga gagal: {e}", worker_tag)

    log("   ⚠️ Elemen input file tidak ditemukan di komposer & fallback gagal.", worker_tag)
    return False


async def submit_group_post(page: Page, worker_tag: str = "") -> bool:
    """
    Klik tombol submit Post/Posting di dalam modal dialog komposer dan konfirmasi status publikasi.
    """
    log("   🚀 Mengirim postingan...", worker_tag)

    if not await is_composer_active(page):
        log("   ❌ Modal komposer tidak aktif. Submit dibatalkan.", worker_tag)
        return False

    # Cek pembatasan akun FB
    is_res, res_reason = await check_account_restriction(page)
    if is_res:
        log(f"   ⛔ AKUN DIBATASI FACEBOOK: {res_reason}", worker_tag)
        return False

    submit_btn = await find_submit_button(page)
    if not submit_btn:
        log("   ❌ Tombol submit 'Post' / 'Posting' tidak ditemukan di dialog.", worker_tag)
        return False

    try:
        # Menunggu hingga tombol tidak lagi disabled (aria-disabled != "true") up to 15 detik
        for _ in range(30):
            aria_disabled = await submit_btn.get_attribute("aria-disabled")
            if aria_disabled != "true":
                break
            await page.wait_for_timeout(500)

        # Klik tombol submit utama
        log("   👉 Menekan tombol Submit ('Post' / 'Posting')...", worker_tag)
        await submit_btn.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        
        try:
            await submit_btn.click(timeout=3000)
        except Exception:
            await submit_btn.click(force=True, timeout=3000)

        log("   ⏳ Menunggu proses publikasi postingan Facebook...", worker_tag)

        # Polling hingga 10 detik untuk memastikan komposer tertutup atau persetujuan admin muncul
        for _ in range(10):
            await page.wait_for_timeout(1000)
            if not await is_composer_active(page):
                log("   ✅ Postingan BERHASIL terpublikasi / terkirim!", worker_tag)
                return True

            dialog = await get_active_composer_dialog(page)
            if dialog:
                inner_txt = (await dialog.inner_text()).lower()
                if any(kw in inner_txt for kw in ["persetujuan", "approval", "admin", "pending", "dikirim"]):
                    log("   ⏳ Postingan terkirim dan Menunggu Persetujuan Admin (Pending Approval).", worker_tag)
                    return True

        # Pemicu cadangan: tekan Control+Enter pada textbox caption di dalam modal dialog.
        # Pastikan textbox benar-benar difokuskan dan masih aktif (modal belum tertutup).
        log("   🔄 Menggunakan pemicu cadangan (Control+Enter)...", worker_tag)
        if await is_composer_active(page):
            tb = await find_caption_textbox(page)
            if tb:
                try:
                    # Klik dulu supaya yakin fokus di textbox (bukan di tombol lain)
                    try:
                        await tb.click(timeout=1000)
                    except Exception:
                        await tb.focus()
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Control+Enter")
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    log(f"   ⚠️ Control+Enter fallback gagal: {e}", worker_tag)
        else:
            # Modal sudah tertutup sejak pengecekan terakhir — mungkin post sudah berhasil
            log("   ℹ️ Modal komposer sudah tertutup — kemungkinan post sudah terkirim.", worker_tag)

        if not await is_composer_active(page):
            log("   ✅ Postingan BERHASIL terpublikasi via pemicu cadangan!", worker_tag)
            return True

        # Percobaan klik paksa ulang tombol submit jika dialog masih bertahan
        retry_btn = await find_submit_button(page)
        if retry_btn:
            await retry_btn.click(force=True, timeout=3000)
            await page.wait_for_timeout(4000)

        if not await is_composer_active(page):
            log("   ✅ Postingan BERHASIL terpublikasi pada percobaan ulang!", worker_tag)
            return True

    except Exception as e:
        log(f"   ❌ Gagal menekan tombol submit postingan: {e}", worker_tag)

    return False


async def execute_post_to_group(
    page: Page,
    target_url: str,
    caption: str,
    image_paths: Optional[List[str]] = None,
    worker_tag: str = ""
) -> bool:
    """
    Orkestrator Lengkap Alur Pembuatan Postingan Grup Facebook.
    1. Buka Komposer
    2. Ketik Caption
    3. Upload Media Gambar
    4. Submit & Konfirmasi
    """
    log(f"\n=======================================================", worker_tag)
    log(f"🌐 PROSES POSTING KE GRUP: {target_url}", worker_tag)
    log(f"=======================================================", worker_tag)

    # 1. Buka Komposer
    opened = await open_group_composer(page, target_url, worker_tag)
    if not opened:
        return False

    await random_human_delay(1.0, 2.0)

    # 2. Ketik Caption
    if caption:
        typed = await type_post_caption(page, caption, worker_tag)
        if not typed:
            return False

    await random_human_delay(1.0, 2.0)

    # 3. Upload Media Gambar (jika ada)
    if image_paths:
        await attach_media_files(page, image_paths, worker_tag)
        await random_human_delay(1.5, 3.0)

    # 4. Submit Postingan
    posted = await submit_group_post(page, worker_tag)
    return posted
