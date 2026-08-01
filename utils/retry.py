"""
utils/retry.py
Cooldown restriction, group skip-list, media validator, browser cleanup.
"""
import os
import time
import threading
import asyncio
from typing import Tuple

import config
from utils.helpers import log


class RestrictionCooldown:
    """Track akun yang kena rate-limit FB. Cooldown default 30 menit."""
    def __init__(self):
        self._lock = threading.RLock()
        self._restricted: dict = {}
        self._cooldown_sec = config.RESTRICTION_COOLDOWN_SEC

    def mark_restricted(self, c_user: str, reason: str = ""):
        if not c_user:
            return
        with self._lock:
            self._restricted[c_user] = time.time() + self._cooldown_sec
            log(f"🛡️ Akun {c_user} ditandai RESTRICTED {self._cooldown_sec}s. Reason: {reason}")

    def is_in_cooldown(self, c_user: str) -> bool:
        if not c_user:
            return False
        with self._lock:
            exp = self._restricted.get(c_user)
            if exp is None:
                return False
            if time.time() >= exp:
                self._restricted.pop(c_user, None)
                return False
            return True

    def remaining_sec(self, c_user: str) -> float:
        if not c_user:
            return 0.0
        with self._lock:
            exp = self._restricted.get(c_user, 0)
            return max(0.0, exp - time.time())

    def clear(self, c_user: str = None):
        with self._lock:
            if c_user:
                self._restricted.pop(c_user, None)
            else:
                self._restricted.clear()


restriction_cooldown = RestrictionCooldown()


class GroupSkipList:
    """Daftar grup yang gagal persisten. Disimpan ke file."""
    def __init__(self, filepath=None):
        self._filepath = filepath or config.GROUP_SKIP_FILE
        self._lock = threading.RLock()
        self._skipped: dict = {}
        self._load()

    def _load(self):
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
        except Exception:
            pass

    def _save(self):
        if not self._filepath:
            return
        try:
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
            with open(self._filepath, "w", encoding="utf-8") as f:
                for url, reason in self._skipped.items():
                    f.write(f"{url}#{reason}\n")
        except Exception:
            pass

    def is_skipped(self, url: str) -> bool:
        with self._lock:
            return url in self._skipped

    def add(self, url: str, reason: str = "failed"):
        with self._lock:
            if url and url not in self._skipped:
                self._skipped[url] = reason
                self._save()
                log(f"🚫 Grup di-skip-list: {url} ({reason})")

    def count(self) -> int:
        with self._lock:
            return len(self._skipped)


group_skip_list = GroupSkipList()


def validate_media_files(image_paths: list) -> Tuple[list, list]:
    """Pisahkan (valid, skipped). Skip file >4MB atau tidak ada."""
    valid, skipped = [], []
    max_bytes = config.MAX_MEDIA_SIZE_MB * 1024 * 1024
    for p in image_paths:
        if not os.path.exists(p):
            skipped.append((p, "not found"))
            continue
        try:
            size = os.path.getsize(p)
        except OSError:
            skipped.append((p, "cannot stat"))
            continue
        if size == 0:
            skipped.append((p, "empty"))
            continue
        if size > max_bytes:
            skipped.append((p, f"{size/1024/1024:.1f}MB > {config.MAX_MEDIA_SIZE_MB}MB"))
            continue
        valid.append(p)
    return valid, skipped


async def safe_browser_cleanup(browser=None, context=None, page=None):
    """Tutup browser dengan aman. Tidak throw exception."""
    for label, obj in [("page", page), ("context", context), ("browser", browser)]:
        if obj is None:
            continue
        try:
            await obj.close()
        except Exception:
            pass
