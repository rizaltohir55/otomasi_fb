"""
helpers.py — Log, URL, lock.
"""
import re, os, sys, time, hashlib, json
from datetime import datetime
import config


def log(msg, tag=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {'['+tag+'] ' if tag else ''}{msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(config.LOGS_DIR, "activity.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def normalize_url(raw):
    """Return (desktop_url, group_id)."""
    p = re.split(r"[?#]", raw.strip())[0]
    m = re.search(r"groups/([0-9a-zA-Z._-]+)", p)
    gid = m.group(1).rstrip("/") if m else ""
    if gid.lower() in ["create", "discover", "search", "feed", "category"]:
        gid = ""
    url = f"https://www.facebook.com/groups/{gid}/" if gid else raw
    return url, gid


def get_c_user(session_file):
    """Baca c_user dari file sesi JSON."""
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for c in data.get("cookies", []):
            if c.get("name") == "c_user":
                return str(c.get("value", ""))
    except Exception:
        pass
    return ""


def get_account_name(session_file):
    """Baca nama akun dari meta atau filename."""
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("meta", {}).get("name", "")
        if name:
            return name
    except Exception:
        pass
    base = os.path.basename(session_file).replace("fb_session_", "").replace(".json", "")
    return base.replace("_", " ").title() if base else "Unknown"


def pick_profile(session_file):
    """Pilih spoof profile deterministik berdasarkan c_user."""
    c = get_c_user(session_file) or os.path.basename(session_file)
    idx = int(hashlib.sha256(c.encode()).hexdigest(), 16) % len(config.PROFILES)
    return config.PROFILES[idx]


def lock_acquire(c_user, tag=""):
    """Cegah 2 proses untuk akun yang sama. Return True jika dapat lock."""
    if not c_user:
        return True
    tmp = "/tmp" if sys.platform != "win32" else os.environ.get("TEMP", ".")
    path = os.path.join(tmp, f"fb_lock_{c_user}.lock")
    try:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)
                    log(f"🔒 {c_user} sedang diproses PID {pid}. Skip.", tag)
                    return False
                except (ProcessLookupError, OSError):
                    pass
            except Exception:
                pass
        with open(path, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


def lock_release(c_user):
    if not c_user:
        return
    tmp = "/tmp" if sys.platform != "win32" else os.environ.get("TEMP", ".")
    try:
        os.remove(os.path.join(tmp, f"fb_lock_{c_user}.lock"))
    except Exception:
        pass


def load_groups(filepath=None):
    """Baca groups.txt, deduplikasi."""
    fp = filepath or config.GROUPS_FILE
    if not os.path.exists(fp):
        return []
    seen, result = set(), []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                url, gid = normalize_url(raw)
                if gid and gid not in seen:
                    seen.add(gid)
                    result.append(url)
                elif not gid and url not in seen:
                    seen.add(url)
                    result.append(url)
    except Exception:
        pass
    return result


def load_caption():
    try:
        with open(config.CAPTION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def find_media():
    """Cari gambar di folder media/."""
    import glob
    result = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        result.extend(glob.glob(os.path.join(config.MEDIA_DIR, ext)))
        result.extend(glob.glob(os.path.join(config.MEDIA_DIR, ext.upper())))
    max_bytes = config.MAX_MEDIA_MB * 1024 * 1024
    valid = []
    for p in sorted(set(result)):
        try:
            if os.path.getsize(p) <= max_bytes and os.path.getsize(p) > 0:
                valid.append(p)
        except Exception:
            pass
    return valid


def discover_sessions():
    """Cari semua file sesi JSON."""
    import glob
    paths = []
    for pattern in ["fb_session*.json", "session/fb_session*.json"]:
        paths.extend(glob.glob(os.path.join(config.DIR, pattern)))
    paths = sorted(set(os.path.abspath(p) for p in paths))
    sessions = []
    for p in paths:
        c = get_c_user(p)
        if c:
            sessions.append({"path": p, "c_user": c, "name": get_account_name(p)})
    return sessions
