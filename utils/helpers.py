"""
utils/helpers.py
Fungsi bantuan & utility terpusat untuk FB AutoEngine 3.0 Ultra.
"""
import re
import os
import sys
import time
from datetime import datetime

from typing import Tuple

import asyncio
from typing import Tuple, Set

import config


class LogBroadcaster:
    """Manajer penyiaran pesan log real-time untuk WebSocket/SSE Web Interface."""
    def __init__(self):
        self.subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subscribers.discard(q)

    def broadcast(self, message: str):
        for q in list(self.subscribers):
            try:
                q.put_nowait(message)
            except Exception:
                pass


log_broadcaster = LogBroadcaster()


def normalize_group_url(raw_url: str) -> Tuple[str, str, str]:
    """
    Ekstrak Canonical Group ID dan bentuk URL bersih.
    Mengembalikan (desktop_url, mobile_url, group_id).
    """
    cleaned = raw_url.strip()
    cleaned_path = re.split(r"[?#]", cleaned)[0]
    
    match = re.search(r"groups/([0-9a-zA-Z._-]+)", cleaned_path)
    if match:
        gid = match.group(1).rstrip("/")
    else:
        gid = cleaned_path.strip("/").split("/")[-1]

    # Abaikan kata kunci bawaan FB yang bukan ID grup real
    if gid.lower() in ["create", "discover", "search", "feed", "category", "joins"]:
        gid = ""

    desktop_url = f"https://www.facebook.com/groups/{gid}/" if gid else cleaned
    mobile_url  = f"https://m.facebook.com/groups/{gid}/" if gid else cleaned

    return desktop_url, mobile_url, gid


def log(msg: str, worker_tag: str = ""):
    """Tulis pesan log bergaya konsol, broadcast ke SSE web, dan simpan secara persisten ke logs/activity.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{worker_tag}] " if worker_tag else ""
    formatted = f"[{timestamp}] {prefix}{msg}"
    
    try:
        print(formatted, flush=True)
    except UnicodeEncodeError:
        # Fallback encode jika terminal Windows menggunakan cp1252 / cp437
        safe_str = formatted.encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii')
        print(safe_str, flush=True)
    except Exception:
        pass

    log_broadcaster.broadcast(formatted)
    
    log_file = os.path.join(config.LOGS_DIR, "activity.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass



def clean_text(text: str) -> str:
    """Bersihkan whitespace berlebih dari string."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

