# 🌐 FB AutoEngine 3.0 Ultra — Terminal Only

> Otomasi posting & join grup Facebook via terminal CLI.

---

## 📌 Deskripsi

Sistem otomatisasi Facebook berbasis Playwright yang berjalan **hanya via terminal**.
Tidak ada web server, tidak ada dashboard web — murni CLI.

## ⚡ Fitur

- **Auto Post** ke ratusan grup Facebook (teks + gambar)
- **Auto Join** grup otomatis + jawab Q&A admin
- **Multi-Account Paralel** via multiprocessing
- **Stealth Engine** (fingerprint spoofing, anti-detection)
- **Session Management** (login, relogin, import cookie)
- **Anti-Duplikasi** (file lock + session progress tracking)
- **Cooldown Restriction** (akun kena rate-limit auto-pause 30 menit)

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/rizaltohir55/otomasi_fb.git
cd otomasi_fb

# Install
pip install -r requirements.txt
playwright install chromium

# Jalankan (menu interaktif)
python autopost.py
```

## 📋 Cara Pakai

### Login Akun Baru
```bash
python login_terminal.py
# Browser terbuka → login Facebook → cookie tersimpan otomatis
```

### Jalankan Otomasi
```bash
# Menu interaktif (pilih akun, mode, dll)
python autopost.py

# CLI langsung — 1 akun, mode post
python autopost.py --session session/fb_session_kayy.json --mode 1 --headless

# CLI — semua akun paralel
python autopost.py --all-accounts --mode 3 --headless --max-workers 3

# CLI — range grup tertentu
python autopost.py --accounts 1 --mode 1 --start 1 --end 50
```

### Mode Operasi
- `1` = Auto Post saja
- `2` = Auto Join saja
- `3` = Auto Post + Auto Join (join otomatis jika belum anggota)

## 📁 Struktur

```
otomasi_fb/
├── autopost.py              # Entry point CLI
├── login_terminal.py        # Login akun baru via browser GUI
├── config.py                # Konfigurasi terpusat
├── caption.txt              # Caption postingan
├── groups.txt               # Daftar URL grup target
├── requirements.txt         # Dependencies (playwright only)
├── engine/                  # Core automation
│   ├── browser.py           # Stealth browser context
│   ├── composer.py          # Post creation & submit
│   ├── joiner.py            # Group join automation
│   ├── commenter.py         # Auto comment
│   ├── collector.py         # Load groups/caption/media
│   ├── dom_analyzer.py      # ARIA DOM analysis
│   └── selectors.py         # CSS/ARIA selectors
├── manager/
│   ├── runner.py            # Worker loop (single & multi-process)
│   └── session_manager.py   # Session CRUD + verify
├── utils/
│   ├── helpers.py           # Logging, URL normalize, account lock
│   ├── browser.py           # Navigation helpers
│   ├── files.py             # File utilities
│   └── retry.py             # Cooldown, skip-list, media validator
├── ui/
│   └── dashboard.py         # CLI menu interaktif
├── session/                 # File sesi JSON (*.json)
├── media/                   # Gambar untuk posting
└── logs/                    # Activity log
```

## 🔒 Keamanan

- Gunakan jeda antar grup yang wajar (atur di `config.py`)
- Batasi jumlah posting harian per akun
- Jangan bagikan file sesi `session/*.json`
