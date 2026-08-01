"""
utils/retry.py
Utility retry, circuit-breaker, dan skip-list manager untuk FB AutoEngine 3.0 Ultra.

Tujuan:
- Menyediakan dekorator async `with_retry` yang konsisten untuk semua operasi Playwright.
- Menyediakan `RestrictionCooldown` untuk menghentikan sementara akun yang terkena limit FB.
- Menyediakan `GroupSkipList` persisten untuk mencatat grup yang selalu gagal.
- Menyediakan `CancellationToken` kooperatif agar worker_loop bisa dihentikan secara halus.
"""
import os
import asyncio
import functools
import random
import time
import threading
from typing import Any, Callable, Optional, Set, Dict, Tuple
from datetime import datetime

import config
from utils.helpers import log


# ── 1. Cancellation Token (kooperatif) ────────────────────────────────────────
class CancellationToken:
    """
    Token pembatalan kooperatif lintas coroutine.
    Worker_loop dapat memeriksa `token.is_cancelled()` secara berkala
    dan keluar secara halus ketika pengguna memanggil `/api/runner/stop`.
    """
    def __init__(self):
        self._event = asyncio.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    async def wait(self, timeout: Optional[float] = None) -> bool:
        try:
            if timeout is None:
                await self._event.wait()
                return True
            return await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return False

    def reset(self) -> None:
        self._event.clear()


# Singleton global cancellation token
_global_cancel_token = CancellationToken()


def get_global_cancel_token() -> CancellationToken:
    return _global_cancel_token


def trigger_global_cancel() -> None:
    _global_cancel_token.cancel()


def reset_global_cancel() -> None:
    _global_cancel_token.reset()


# ── 2. Async Retry Decorator ──────────────────────────────────────────────────
def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, int], None]] = None,
):
    """
    Dekorator async dengan exponential backoff + jitter.

    Parameter:
    - max_attempts: total percobaan (termasuk pertama).
    - base_delay: delay awal (detik).
    - max_delay: batas atas delay (detik).
    - exceptions: tuple exception yang akan di-retry. Exception lain langsung re-raise.
    - on_retry: callback dipanggil setiap kali retry dilakukan dengan (exc, attempt, max_attempts).
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_exc: Optional[Exception] = None
            while attempt < max_attempts:
                attempt += 1
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt >= max_attempts:
                        raise
                    # Exponential backoff + jitter (full jitter strategy)
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    jitter = random.uniform(0, delay / 2)
                    sleep_for = delay + jitter
                    if on_retry:
                        try:
                            on_retry(e, attempt, max_attempts)
                        except Exception:
                            pass
                    await asyncio.sleep(sleep_for)
            # Shouldn't reach here, but as a safety net
            if last_exc:
                raise last_exc
        return wrapper
    return decorator


# ── 3. Restriction Cooldown (thread-safe) ─────────────────────────────────────
class RestrictionCooldown:
    """
    Catat timestamp kapan akun (c_user) terakhir kali terdeteksi RESTRICTED.
    Worker lain tidak boleh memakai akun tersebut sebelum cooldown selesai.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._restricted: Dict[str, float] = {}  # c_user -> expiry_timestamp
        self._cooldown_sec: int = config.RESTRICTION_COOLDOWN_SEC

    def mark_restricted(self, c_user: str, reason: str = "") -> None:
        if not c_user:
            return
        with self._lock:
            self._restricted[c_user] = time.time() + self._cooldown_sec
            log(f"🛡️ Akun c_user={c_user} ditandai RESTRICTED selama {self._cooldown_sec}s. Reason: {reason or 'N/A'}")

    def is_in_cooldown(self, c_user: str) -> bool:
        if not c_user:
            return False
        with self._lock:
            exp = self._restricted.get(c_user)
            if exp is None:
                return False
            if time.time() >= exp:
                # Cooldown expired, remove entry
                self._restricted.pop(c_user, None)
                return False
            return True

    def remaining_sec(self, c_user: str) -> float:
        if not c_user:
            return 0.0
        with self._lock:
            exp = self._restricted.get(c_user)
            if exp is None:
                return 0.0
            remaining = exp - time.time()
            return max(0.0, remaining)

    def clear(self, c_user: str = None) -> None:
        with self._lock:
            if c_user:
                self._restricted.pop(c_user, None)
            else:
                self._restricted.clear()

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            # Purge expired entries
            now = time.time()
            expired = [k for k, v in self._restricted.items() if v <= now]
            for k in expired:
                self._restricted.pop(k, None)
            return dict(self._restricted)


# Singleton instance
restriction_cooldown = RestrictionCooldown()


# ── 4. Group Skip-List Persistent ─────────────────────────────────────────────
class GroupSkipList:
    """
    Daftar hitam grup yang konsisten gagal (composer tidak bisa dibuka N kali).
    Disimpan ke file agar sesi berikutnya bisa langsung skip.
    Format: satu URL per baris, dengan optional suffix `#<reason>`.
    """
    def __init__(self, filepath: Optional[str] = None):
        self._filepath = filepath or config.GROUP_SKIP_FILE
        self._lock = threading.RLock()
        self._skipped: Dict[str, str] = {}  # url -> reason
        self._load()

    def _load(self) -> None:
        if not self._filepath or not os.path.exists(self._filepath):
            return
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "#" in line:
                        url, reason = line.split("#", 1)
                        self._skipped[url.strip()] = reason.strip()
                    else:
                        self._skipped[line] = "previously failed"
        except Exception as e:
            log(f"⚠️ Gagal memuat group skip-list: {e}")

    def _save(self) -> None:
        if not self._filepath:
            return
        try:
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
            with open(self._filepath, "w", encoding="utf-8") as f:
                f.write("# Group skip-list FB AutoEngine 3.0 Ultra\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                for url, reason in self._skipped.items():
                    f.write(f"{url}#{reason}\n")
        except Exception as e:
            log(f"⚠️ Gagal menyimpan group skip-list: {e}")

    def is_skipped(self, url: str) -> bool:
        with self._lock:
            return url in self._skipped

    def add(self, url: str, reason: str = "failed") -> None:
        with self._lock:
            if url and url not in self._skipped:
                self._skipped[url] = reason
                self._save()
                log(f"🚫 Grup ditambahkan ke skip-list: {url} (reason: {reason})")

    def remove(self, url: str) -> None:
        with self._lock:
            if url in self._skipped:
                self._skipped.pop(url)
                self._save()

    def list_all(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._skipped)

    def count(self) -> int:
        with self._lock:
            return len(self._skipped)

    def clear(self) -> None:
        with self._lock:
            self._skipped.clear()
            self._save()


# Singleton instance
group_skip_list = GroupSkipList()


# ── 5. Media File Validator ───────────────────────────────────────────────────
def validate_media_files(image_paths: list) -> Tuple[list, list]:
    """
    Pisahkan path media menjadi (valid, skipped).
    Skip file yang: tidak ada / ukuran 0 / melebihi MAX_MEDIA_SIZE_MB.
    """
    valid: list = []
    skipped: list = []
    max_bytes = config.MAX_MEDIA_SIZE_MB * 1024 * 1024
    for p in image_paths:
        if not os.path.exists(p):
            skipped.append((p, "file not found"))
            continue
        try:
            size = os.path.getsize(p)
        except OSError:
            skipped.append((p, "cannot stat file"))
            continue
        if size == 0:
            skipped.append((p, "empty file"))
            continue
        if size > max_bytes:
            skipped.append((p, f"size {size/1024/1024:.2f}MB > limit {config.MAX_MEDIA_SIZE_MB}MB"))
            continue
        valid.append(p)
    return valid, skipped


# ── 6. Safe Async Browser Cleanup Helper ──────────────────────────────────────
async def safe_browser_cleanup(browser=None, context=None, page=None) -> None:
    """
    Tutup page → context → browser secara berurutan dengan masing-masing try/except.
    Tidak akan melempar exception apapun.
    """
    for label, obj in [("page", page), ("context", context), ("browser", browser)]:
        if obj is None:
            continue
        try:
            await obj.close()
        except Exception as e:
            log(f"⚠️ Cleanup {label} gagal: {e}")
