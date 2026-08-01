"""
utils/browser.py
Utility pembantu untuk interaksi browser & Playwright context.
"""
import random
import asyncio
from playwright.async_api import Page


async def random_human_delay(min_sec: float = 0.5, max_sec: float = 1.5):
    """Lakukan penundaan acak untuk mensimulasikan jeda berpikir manusia.
    Dioptimalkan: default 0.5-1.5s (was 1.5-4.0s) untuk kecepatan 2-3x."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def scroll_page_naturally(page: Page, distance: int = 400):
    """Lakukan scroll halaman secara halus menyerupai pengguna manusia."""
    try:
        await page.mouse.wheel(0, distance)
        await asyncio.sleep(0.3)
    except Exception:
        pass


async def safe_goto(page: Page, url: str, timeout_ms: int = 20000) -> bool:
    """
    Navigasi super-cepat & tahan banting ke URL target.
    Menggunakan fallback 'commit' jika 'domcontentloaded' tertahan oleh asset Facebook.
    Dioptimalkan: post-navigation delay dikurangi dari 1000ms → 500ms.
    """
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
