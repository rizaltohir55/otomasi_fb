"""
utils/files.py
Utility sistem berkas dan direktori.
"""
import os
import glob
from typing import List


def get_image_files(media_dir: str) -> List[str]:
    """Ambil seluruh daftar berkas gambar ber-ekstensi valid dari folder media."""
    if not os.path.exists(media_dir):
        return []
    valid_exts = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    images = []
    for ext in valid_exts:
        images.extend(glob.glob(os.path.join(media_dir, ext)))
        images.extend(glob.glob(os.path.join(media_dir, ext.upper())))
    return sorted(list(set(images)))


def read_text_file(filepath: str) -> str:
    """Baca isi file teks dengan encoding UTF-8."""
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def write_text_file(filepath: str, content: str) -> bool:
    """Tulis konten string ke file teks dengan encoding UTF-8."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False