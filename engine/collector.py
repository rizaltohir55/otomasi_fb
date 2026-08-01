"""
engine/collector.py
Modul Pengumpul Data (Collector & Loader) FB AutoEngine 3.0 Ultra.
Membaca dan memvalidasi file daftar grup, caption, dan media.
"""
import os
import re
from typing import List, Optional

import config
from utils.helpers import log, normalize_group_url
from utils.files import get_image_files


def load_groups(custom_filepath: Optional[str] = None) -> List[str]:
    """
    Membaca daftar URL grup dari file text, membersihkan duplikat, dan mengembalikan daftar URL Desktop valid.
    """
    target_file = custom_filepath or config.GROUPS_FILE
    if not os.path.exists(target_file):
        log(f"⚠️ File daftar grup tidak ditemukan di: {target_file}")
        return []

    valid_groups = []
    seen_ids = set()

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue

            desktop_url, _, gid = normalize_group_url(raw)
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                valid_groups.append(desktop_url)
            elif not gid and "facebook.com/groups/" in raw:
                if raw not in seen_ids:
                    seen_ids.add(raw)
                    valid_groups.append(raw)
    except Exception as e:
        log(f"❌ Gagal membaca file grup {target_file}: {e}")

    return valid_groups


def load_caption(custom_filepath: Optional[str] = None) -> str:
    """
    Membaca isi teks caption postingan dari caption.txt.
    """
    target_file = custom_filepath or config.CAPTION_FILE
    if not os.path.exists(target_file):
        return ""

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        log(f"⚠️ Gagal membaca file caption {target_file}: {e}")
        return ""


def find_media_images(media_dir: Optional[str] = None) -> List[str]:
    """
    Mengambil seluruh berkas gambar dari folder media.
    """
    target_dir = media_dir or config.MEDIA_DIR
    return get_image_files(target_dir)
