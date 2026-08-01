"""
engine/dom_analyzer.py
Analyzer ARIA DOM Facebook Desktop 2026 yang Presisi & Dinamis.
"""
from typing import Optional
from playwright.async_api import Page, Locator

import config
from engine.selectors import (
    DESKTOP_COMPOSER_TRIGGERS,
    CAPTION_TEXTBOX_SELECTORS,
    POST_BUTTON_SELECTORS,
)


async def dismiss_all_overlays(page: Page, preserve_composer: bool = True):
    """
    Tutup dialog overlay, pop-up notifikasi, cookie consent, atau backdrop modal pengganggu.
    Mendukung berbagai bahasa (Indonesian, English, Spanish, French, German, dll).

    Parameter:
    - preserve_composer: jika True, JANGAN tutup dialog yang merupakan modal composer
      postingan aktif (yaitu dialog yang berisi textbox contenteditable + tombol Post).
      Default True — komposer aktif tidak akan ditutup secara tidak sengaja.
    """
    # Identifikasi modal composer aktif supaya tidak ikut ditutup.
    composer_dialog = None
    if preserve_composer:
        try:
            composer_dialog = await get_active_composer_dialog(page)
        except Exception:
            composer_dialog = None

    # Helper: cek apakah sebuah locator berada di dalam composer dialog aktif
    async def _is_inside_composer(loc: Locator) -> bool:
        if composer_dialog is None:
            return False
        try:
            # Pakai evaluate: cek apakah elemen adalah descendant dari composer dialog
            return await loc.evaluate(
                "(el, root) => { if (!root || !el) return false; return root.contains(el); }",
                composer_dialog
            )
        except Exception:
            return False

    dismiss_buttons = [
        # Explicit aria-labels
        'div[role="dialog"] div[role="button"][aria-label="Close"]',
        'div[role="dialog"] div[role="button"][aria-label="Tutup"]',
        'div[role="dialog"] div[role="button"][aria-label="Cerrar"]',
        'div[role="dialog"] div[role="button"][aria-label="Fermer"]',
        'div[role="dialog"] div[role="button"][aria-label="Schließen"]',
        'div[role="dialog"] div[role="button"][aria-label="Not Now"]',
        'div[role="dialog"] div[role="button"][aria-label="Lain Kali"]',
        'div[role="dialog"] div[role="button"][aria-label="Ahora no"]',
        'div[role="dialog"] div[role="button"][aria-label="Plus tard"]',
        # Cookie banner buttons
        'button:has-text("Decline optional cookies")',
        'button:has-text("Allow all cookies")',
        'button:has-text("Only allow essential cookies")',
        'button:has-text("Izinkan semua cookie")',
        'button:has-text("Tolak cookie opsional")',
        'button:has-text("Aceptar todas las cookies")',
        'button:has-text("Autoriser tous les cookies")',
        'button:has-text("Alle Cookies erlauben")',
        # Modal confirmation / tooltips
        'div[role="button"]:has-text("Got It")',
        'div[role="button"]:has-text("Paham")',
        'div[role="button"]:has-text("Entendido")',
        'div[role="button"]:has-text("Compris")',
    ]
    for sel in dismiss_buttons:
        try:
            btn = page.locator(sel).first
            if await btn.count() == 0:
                continue
            if not await btn.is_visible(timeout=300):
                continue
            # Skip jika tombol berada di dalam composer dialog aktif
            if preserve_composer and await _is_inside_composer(btn):
                continue
            await btn.click(timeout=1000)
            await page.wait_for_timeout(500)
        except Exception:
            pass


async def get_active_composer_dialog(page: Page) -> Optional[Locator]:
    """
    Cari dan kembalikan Locator modal dialog (div[role="dialog"]) tempat komposer postingan berada.
    """
    try:
        dialogs = page.locator('div[role="dialog"]')
        count = await dialogs.count()
        for i in range(count):
            d = dialogs.nth(i)
            if not await d.is_visible(timeout=300):
                continue
            
            # Cek jika di dalam dialog ada textbox contenteditable
            tb = d.locator('div[role="textbox"][contenteditable="true"], div[contenteditable="true"]').first
            if await tb.count() > 0 and await tb.is_visible(timeout=300):
                return d
                
            for txt in config.SUBMIT_BUTTON_TEXTS:
                pb = d.locator(
                    f'div[role="button"][aria-label="{txt}"], '
                    f'div[role="button"]:has-text("{txt}"), '
                    f'button:has-text("{txt}")'
                ).first
                if await pb.count() > 0 and await pb.is_visible(timeout=300):
                    return d
    except Exception:
        pass
    return None


async def find_composer_trigger(page: Page) -> Optional[Locator]:
    """
    Temukan tombol trigger pembuka komposer di halaman grup ("Write something...", "Tulis sesuatu...").
    Dinamis & Multi-bahasa: Mencakup pencarian di main_scope & page level.
    """
    main_scope = page.locator('div[role="main"]').first
    scopes = [main_scope, page] if await main_scope.count() > 0 else [page]

    # 1. Pencarian berbasis daftar teks terkonfigurasi pada scope
    for scope in scopes:
        for text in config.COMPOSER_TRIGGER_TEXTS:
            try:
                # Cari via aria-label
                loc_label = scope.locator(f'div[role="button"][aria-label="{text}"]')
                if await loc_label.count() > 0 and await loc_label.first.is_visible(timeout=300):
                    return loc_label.first

                # Cari via has-text
                loc_text = scope.locator(f'div[role="button"]:has-text("{text}")')
                if await loc_text.count() > 0 and await loc_text.first.is_visible(timeout=300):
                    return loc_text.first

                # Cari via span/div placeholder
                loc_span = scope.locator(f'span:has-text("{text}")')
                if await loc_span.count() > 0 and await loc_span.first.is_visible(timeout=300):
                    return loc_span.first
            except Exception:
                continue

    # 2. Fallback via registry DESKTOP_COMPOSER_TRIGGERS
    for scope in scopes:
        for sel in DESKTOP_COMPOSER_TRIGGERS:
            try:
                loc = scope.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    return loc
            except Exception:
                continue

    # 3. Fallback elemen ber-attribute aria-placeholder
    for scope in scopes:
        try:
            placeholder_loc = scope.locator('div[aria-placeholder], span[aria-placeholder]').first
            if await placeholder_loc.count() > 0 and await placeholder_loc.is_visible(timeout=300):
                return placeholder_loc
        except Exception:
            pass

    return None


async def find_caption_textbox(page: Page) -> Optional[Locator]:
    """
    Temukan elemen textbox pengetikan caption HANYA di dalam modal dialog komposer aktif.
    """
    dialog = await get_active_composer_dialog(page)
    search_root = dialog if dialog is not None else page.locator('div[role="dialog"]')

    for sel in CAPTION_TEXTBOX_SELECTORS:
        try:
            target_sel = sel if sel.startswith('div[role="dialog"]') else f'div[role="dialog"] {sel}'
            loc = page.locator(target_sel).first
            if await loc.count() > 0 and await loc.is_visible(timeout=500):
                return loc
        except Exception:
            continue

    # Fallback pencarian langsung textbox contenteditable di dialog
    try:
        tb = search_root.locator('div[role="textbox"][contenteditable="true"]').first
        if await tb.count() > 0 and await tb.is_visible(timeout=500):
            return tb
    except Exception:
        pass

    return None


async def find_submit_button(page: Page) -> Optional[Locator]:
    """
    Temukan tombol submit ("Post" / "Posting" / "Publicar" / "Publier" / "Posten") HANYA di dalam modal dialog komposer aktif.
    Sangat ketat: Mengabaikan tombol toolbar seperti 'Tambahkan ke postingan Anda' / 'Add to your post'.
    """
    dialog = await get_active_composer_dialog(page)
    if not dialog:
        return None

    # Daftar kata pengabaian tombol toolbar & dialog pengganggu dalam berbagai bahasa
    ignore_keywords = [
        "tambahkan ke", "add to", "agregar a", "ajouter à", "foto/video", "photo/video", "foto/vídeo",
        "tandai", "tag", "perasaan", "feeling", "singgah", "check in",
        "opsi", "option", "edit", "batal", "cancel", "tutup", "close", "hapus", "delete"
    ]

    target_submit_words = [t.strip().lower() for t in config.SUBMIT_BUTTON_TEXTS]

    try:
        buttons = dialog.locator('div[role="button"], button')
        cnt = await buttons.count()
        for i in range(cnt):
            b = buttons.nth(i)
            if not await b.is_visible(timeout=200):
                continue

            lbl = (await b.get_attribute("aria-label") or "").strip().lower()
            txt = (await b.inner_text()).strip().lower()

            # Filter pengabaian tombol toolbar
            if any(kw in lbl for kw in ignore_keywords) or any(kw in txt for kw in ignore_keywords):
                continue

            # Check exact match submit target
            if lbl in target_submit_words or txt in target_submit_words:
                return b

            # Alt check substring match jika text/label dimulai dengan salah satu kata submit target
            if any(txt.startswith(tw) or lbl.startswith(tw) for tw in target_submit_words):
                return b
    except Exception:
        pass

    # Fallback pencarian langsung via ARIA label presisi terkonfigurasi
    for target in config.SUBMIT_BUTTON_TEXTS:
        try:
            loc_aria = dialog.locator(f'div[role="button"][aria-label="{target}"], button[aria-label="{target}"]')
            if await loc_aria.count() > 0 and await loc_aria.first.is_visible(timeout=300):
                return loc_aria.first
        except Exception:
            continue

    return None
