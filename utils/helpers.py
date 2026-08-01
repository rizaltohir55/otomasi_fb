"""
utils/helpers.py
Utility terpusat: logging, normalize URL, account lock.
"""
import re
import os
import sys
import time
from datetime import datetime

import config

_LOCK_FILES: dict = {}


def log(msg: str, worker_tag: str = ""):
    """Tulis log ke stdout + file activity.log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{worker_tag}] " if worker_tag else ""
    line = f"[{ts}] {prefix}{msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(config.LOGS_DIR, "activity.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def normalize_group_url(raw_url: str):
    """Ekstrak (desktop_url, mobile_url, group_id)."""
    cleaned = raw_url.strip()
    path = re.split(r"[?#]", cleaned)[0]
    match = re.search(r"groups/([0-9a-zA-Z._-]+)", path)
    gid = match.group(1).rstrip("/") if match else path.strip("/").split("/")[-1]
    if gid.lower() in ["create", "discover", "search", "feed", "category", "joins"]:
        gid = ""
    desktop = f"https://www.facebook.com/groups/{gid}/" if gid else cleaned
    mobile  = f"https://m.facebook.com/groups/{gid}/" if gid else cleaned
    return desktop, mobile, gid


def acquire_account_lock(c_user: str, worker_tag: str = "") -> bool:
    """Cegah 2 proses berjalan untuk akun yang sama. Return True jika lock didapat."""
    if not c_user:
        return True
    lock_path = os.path.join("/tmp" if sys.platform != "win32" else os.environ.get("TEMP", "."), f"otomasi_fb_{c_user}.lock")
    try:
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r") as f:
                    old_pid = int(f.read().strip())
                try:
                    os.kill(old_pid, 0)
                    log(f"🔒 Akun {c_user} sedang diproses PID {old_pid}. Skip.", worker_tag)
                    return False
                except ProcessLookupError:
                    os.remove(lock_path)
                except PermissionError:
                    log(f"🔒 Akun {c_user} sedang diproses PID {old_pid}. Skip.", worker_tag)
                    return False
                except OSError:
                    log(f"🔒 Akun {c_user} sedang diproses PID {old_pid}. Skip.", worker_tag)
                    return False
            except (ValueError, IOError):
                pass
        with open(lock_path, "w") as f:
            f.write(str(os.getpid()))
        _LOCK_FILES[c_user] = lock_path
        return True
    except Exception:
        return True


def release_account_lock(c_user: str):
    """Lepas lock."""
    if not c_user:
        return
    p = _LOCK_FILES.pop(c_user, None)
    if p and os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()
