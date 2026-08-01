"""
utils/browser.py
Utility pembantu untuk interaksi browser & Playwright context.
"""
import random
import asyncio
from playwright.async_api import Page


async def random_human_delay(min_sec: float = 1.5, max_sec: float = 4.0):
    """Lakukan penundaan acak untuk mensimulasikan jeda berpikir manusia."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def scroll_page_naturally(page: Page, distance: int = 400):
    """Lakukan scroll halaman secara halus menyerupai pengguna manusia."""
    try:
        await page.mouse.wheel(0, distance)
        await asyncio.sleep(0.5)
    except Exception:
        pass


async def safe_goto(page: Page, url: str, timeout_ms: int = 20000) -> bool:
    """
    Navigasi super-cepat & tahan banting ke URL target.
    Menggunakan fallback 'commit' jika 'domcontentloaded' tertahan oleh asset Facebook.
    """
    try:
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        return True
    except Exception:
        try:
            await page.goto(url, timeout=12000, wait_until="commit")
            await page.wait_for_timeout(1500)
            return True
        except Exception:
            return False
