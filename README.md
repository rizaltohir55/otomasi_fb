# 🌐 FB AutoEngine 3.0 — Terminal Only

Otomasi posting & join grup Facebook via terminal CLI.

## Quick Start

```bash
git clone https://github.com/rizaltohir55/otomasi_fb.git
cd otomasi_fb
pip install -r requirements.txt
playwright install chromium

# Login akun
python login.py

# Jalankan otomasi (menu interaktif)
python main.py
```

## Struktur (flat — 8 file)

```
main.py       — Entry point CLI
login.py      — Login akun via browser GUI
config.py     — Pengaturan
helpers.py    — Log, URL, lock, load data
browser.py    — Stealth browser + session
poster.py     — Post ke grup (composer, type, upload, submit)
joiner.py     — Join grup (membership, Q&A)
runner.py     — Worker loop + multi-process
```

## Mode

- `1` = Auto Post
- `2` = Auto Join
- `3` = Post + Join
