"""
engine/commenter.py
Modul Otomasi Komentar & Interaksi Postingan Grup Facebook Desktop 2026.
"""
import asyncio
import random
from typing import List, Optional
from playwright.async_api import Page, Locator

import config
from utils.helpers import log, normalize_group_url
from utils.browser import random_human_delay
from engine.selectors import COMMENT_BOX_SELECTORS


async def auto_like_first_post(page: Page) -> bool:
    """
    Sukai (Like) postingan pertama yang ada di feed grup.
    """
    try:
        articles = page.locator('div[role="article"]')
        if await articles.count() == 0:
            return False

        first_article = articles.first
        like_btn = first_article.locator(
            'div[role="button"][aria-label="Like"], '
            'div[role="button"][aria-label="Suka"], '
            'div[role="button"]:has-text("Like"), '
            'div[role="button"]:has-text("Suka")'
        ).first

        if await like_btn.count() > 0 and await like_btn.is_visible(timeout=1000):
            await like_btn.click()
            log("   👍 Postingan pertama berhasil di-Like!")
            return True
    except Exception as e:
        log(f"   ⚠️ Gagal memberikan Like ke postingan: {e}")
    return False


async def post_comment_on_article(page: Page, article_locator: Locator, comment_text: str) -> bool:
    """
    Beri komentar pada postingan spesifik di feed grup.
    """
    if not comment_text:
        return False

    try:
        # 1. Cari box komentar di dalam artikel
        comment_box = None
        for sel in COMMENT_BOX_SELECTORS:
            try:
                cb = article_locator.locator(sel).first
                if await cb.count() > 0 and await cb.is_visible(timeout=500):
                    comment_box = cb
                    break
            except Exception:
                continue

        if not comment_box:
            # Klik tombol 'Comment' / 'Beri komentar' untuk mengaktifkan box komentar
            cmt_btn = article_locator.locator(
                'div[role="button"][aria-label="Comment"], '
                'div[role="button"][aria-label="Komentar"], '
                'div[role="button"]:has-text("Comment"), '
                'div[role="button"]:has-text("Komentar")'
            ).first
            if await cmt_btn.count() > 0 and await cmt_btn.is_visible(timeout=500):
                await cmt_btn.click()
                await page.wait_for_timeout(1000)
                comment_box = article_locator.locator('div[role="textbox"][contenteditable="true"]').first

        if comment_box and await comment_box.count() > 0:
            await comment_box.click(timeout=1000)
            await page.wait_for_timeout(300)
            await comment_box.press_sequentially(comment_text, delay=config.TYPING_SPEED_MS)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)
            log(f"   💬 Komentar '{comment_text}' berhasil terkirim!")
            return True
    except Exception as e:
        log(f"   ❌ Gagal mengirim komentar: {e}")

    return False


async def execute_auto_comment_on_group(page: Page, target_url: str) -> bool:
    """
    Orkestrator Otomasi Komentar Postingan Grup Facebook.
    """
    if not config.AUTO_COMMENT_ENABLED:
        return True

    comment_text = random.choice(config.AUTO_COMMENTS) if config.AUTO_COMMENTS else "Up"
    log(f"   💬 Menjalankan Auto-Comment pada grup: {target_url}")

    articles = page.locator('div[role="article"]')
    if await articles.count() > 0:
        return await post_comment_on_article(page, articles.first, comment_text)

    log("   ⚠️ Tidak ditemukan artikel postingan di feed grup.")
    return False
