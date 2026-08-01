"""
utils/helpers.py
Fungsi bantuan & utility terpusat untuk FB AutoEngine 3.0 Ultra.
"""
import re
import os
import sys
import time
import subprocess
import asyncio
from datetime import datetime
from typing import Tuple, Set, Optional

import config


# ── Global Instance Lock ─────────────────────────────────────────────────────
# Cegah 2 instance otomasi berjalan bersamaan untuk akun yang sama.
# Pakai file lock di /tmp/otomasi_fb_{c_user}.lock dengan fcntl.flock.
# File lock otomatis dilepas saat process exit (bahkan via kill -9).

_LOCK_FILES: dict = {}  # c_user → file handle (keep open to hold lock)

def acquire_account_lock(c_user: str, worker_tag: str = "") -> bool:
    """
    Acquire exclusive lock untuk akun tertentu (by c_user).
    Return True jika berhasil (lock didapat), False jika akun sedang diproses instance lain.

    Lock dipegang selama process hidup. Otomatis dilepas saat process exit.
    """
    if not c_user:
        return True  # no c_user = no lock needed

    lock_path = os.path.join("/tmp", f"otomasi_fb_{c_user}.lock")
    try:
        # Cek apakah lock sudah dipegang oleh process lain
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r") as f:
                    old_pid = int(f.read().strip())
                # Cek apakah process itu masih hidup
                # os.kill(pid, 0) raises:
                # - ProcessLookupError (OSError) jika PID tidak ada → lock stale
                # - PermissionError jika PID ada tapi tidak ada permission → lock valid
                # - Tidak raise apa-apa jika PID ada dan punya permission → lock valid
                try:
                    os.kill(old_pid, 0)
                    # Tidak raise → process ada dan punya permission → lock valid
                    log(f"🔒 Akun c_user={c_user} sedang diproses oleh PID {old_pid}. Skip duplikasi.", worker_tag)
                    return False
                except ProcessLookupError:
                    # Process tidak ditemukan → lock stale, hapus
                    os.remove(lock_path)
                except PermissionError:
                    # Process ada tapi kita tidak punya permission untuk signal → lock valid
                    log(f"🔒 Akun c_user={c_user} sedang diproses oleh PID {old_pid} (permission denied). Skip duplikasi.", worker_tag)
                    return False
                except OSError:
                    # Error lain (termasuk PID 1 di container) → anggap lock valid (konservatif)
                    log(f"🔒 Akun c_user={c_user} sedang diproses oleh PID {old_pid}. Skip duplikasi.", worker_tag)
                    return False
            except (ValueError, IOError):
                pass

        # Acquire lock dengan menulis PID ke file
        with open(lock_path, "w") as f:
            f.write(str(os.getpid()))
        _LOCK_FILES[c_user] = lock_path
        log(f"🔓 Lock acquired untuk c_user={c_user} (PID={os.getpid()})", worker_tag)
        return True
    except Exception as e:
        log(f"⚠️ Gagal acquire lock untuk {c_user}: {e}. Lanjut tanpa lock.", worker_tag)
        return True  # non-fatal: lanjut tanpa lock


def release_account_lock(c_user: str):
    """Lepas lock untuk akun tertentu."""
    if not c_user:
        return
    lock_path = _LOCK_FILES.pop(c_user, None)
    if lock_path and os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except Exception:
            pass


def safe_print(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        safe_str = msg.encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii')
        print(safe_str, flush=True)
    except Exception:
        pass


def auto_pull_github():
    """
    Melakukan git pull otomatis dari GitHub saat startup untuk memastikan
    kode di mesin lokal selalu ter-sinkronisasi dengan repository remote.
    """
    safe_print("🔄 Memeriksa & menyinkronkan kode terbaru dari GitHub...")
    try:
        res = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            timeout=15
        )
        output = res.stdout.strip() or res.stderr.strip()
        if res.returncode == 0:
            if "Already up to date" in output or "Already up-to-date" in output:
                safe_print("✅ Kode lokal sudah sinkron dengan repository GitHub.")
            else:
                safe_print(f"⚡ Pembaruan dari GitHub berhasil ditarik:\n{output}")
        else:
            safe_print(f"⚠️ Catatan sinkronisasi GitHub: {output}")
    except subprocess.TimeoutExpired:
        safe_print("⚠️ Waktu sinkronisasi GitHub habis (timeout 15 detik), melanjutkan dengan kode saat ini.")
def auto_push_sessions(session_file: str = ""):
    """
    Otomatis stage, commit, dan push file sesi Facebook (*.json) ke GitHub.
    """
    safe_print("⬆️ Menyinkronkan & mengunggah file sesi ke GitHub...")
    try:
        targets = ["fb_session*.json", "session/*.json", "groups.txt"]
        if session_file and os.path.exists(session_file):
            targets.append(session_file)

        # Stage files
        subprocess.run(["git", "add"] + targets, capture_output=True, text=True, timeout=10)

        # Cek apakah ada perubahan yang di-stage
        diff_res = subprocess.run(["git", "diff", "--staged", "--name-only"], capture_output=True, text=True, timeout=10)
        staged_files = diff_res.stdout.strip()
        if not staged_files:
            safe_print("ℹ️ Tidak ada perubahan sesi baru yang perlu di-push.")
            return

        tag_name = os.path.basename(session_file) if session_file else "session files"
        commit_msg = f"chore(session): update {tag_name} cookies & state"

        commit_res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True, timeout=15)
        if commit_res.returncode == 0:
            push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=30)
            if push_res.returncode == 0:
                safe_print(f"🚀 Sesi ({tag_name}) BERHASIL di-push ke GitHub!")
            else:
                err = push_res.stderr.strip() or push_res.stdout.strip()
                safe_print(f"⚠️ Gagal push sesi ke GitHub: {err}")
        else:
            err = commit_res.stderr.strip() or commit_res.stdout.strip()
            safe_print(f"⚠️ Gagal commit sesi: {err}")
    except Exception as e:
        safe_print(f"⚠️ Gagal auto-push sesi: {e}")





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

