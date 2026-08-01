# 🌐 FB AutoEngine 3.0 Ultra

> **Enterprise-Grade Facebook Group Auto-Poster, Auto-Joiner & Multi-Account Automation Engine**
> Powered by Pure Desktop React ARIA Automation, Intelligent Stealth, and Parallel Multiprocessing.

---

## 📌 Deskripsi Proyek

**FB AutoEngine 3.0 Ultra** adalah sistem otomatisasi Facebook tingkat lanjut yang dirancang khusus untuk mempublikasikan postingan (teks & gambar) serta bergabung (*auto-join*) ke ratusan Grup Facebook secara otomatis, aman, dan efisien.

Engine versi 3.0 ini mengusung teknologi **Pure Desktop React ARIA DOM Intelligence** yang kebal terhadap perubahan nama class acak (*obfuscated class names*) Facebook, serta menghilangkan kebergantungan pada domain `mbasic` atau `mobile` untuk menghindari *security loop / bot detection* (`?_rdr`).

---

## ⚡ Fitur Utama

- **🚀 Dual-Engine Execution (Single & Multi-Account Parallel)**:
  Mendukung eksekusi 1 akun maupun banyak akun Facebook secara bersamaan menggunakan *multiprocessing pool*.
- **🎯 Pure Desktop React ARIA DOM Intelligence**:
  Navigasi presisi berbasis ARIA roles (`role="main"`, `role="dialog"`, `role="button"`, `div[contenteditable="true"]`) yang dinamis dan kebal update UI Facebook.
- **🖼️ Smart Media & Photo Upload Engine**:
  Penanganan pengunggahan gambar yang presisi langsung ke dalam modal komposer utama tanpa risiko terlampir di kolom komentar lain.
- **➕ Automatic Group Joiner & Q&A Solver**:
  Mendeteksi status keanggotaan grup (`JOINED`, `PENDING`, `UNJOINED`) dan menjawab kuesioner/aturan grup secara otomatis sebelum memposting.
- **🛡️ Advanced Stealth Shield**:
  Proteksi anti-deteksi bot (Chromium automation flags evasion, randomized viewport, realistic human typing emulation, CDP native click events).
- **📊 Real-time Terminal Dashboard**:
  Tampilan CLI interaktif yang informatif, berwarna, dan dilengkapi laporan pengujian unit komprehensif.

---

## 📁 Struktur Direktori

```text
otomasiFB/
├── autopost.py               # Entry point utama (CLI & Interactive Dashboard)
├── config.py                 # Konfigurasi terpusat (Timing, Stealth, Texts)
├── test_all.py               # Suite pengujian otomatis komprehensif (43 Test Cases)
├── caption.txt               # File teks caption postingan
├── groups.txt                # Daftar URL grup target (500+ link)
├── data/                     # Folder data referensi
├── media/                    # Folder tempat gambar postingan (.jpg, .png, .webp)
├── session/                  # Penyimpanan file sesi login Facebook (*.json)
├── logs/                     # Catatan aktivitas & log eksekusi
├── engine/                   # Core Engine Modules
│   ├── dom_analyzer.py       # Traversal ARIA DOM cerdas & penapis overlay
│   ├── composer.py           # Pembuat postingan, uploader gambar & submitter
│   ├── joiner.py             # Pemeriksa status keanggotaan & auto-joiner
│   ├── browser.py            # Launcher browser stealth & sesi cookie
│   ├── collector.py          # Pengumpul grup & file media
│   └── selectors.py          # Registry selektor ARIA multi-bahasa (ID/EN)
├── manager/                  # Task & Worker Managers
│   ├── runner.py             # Eksekutor loop worker & multiprocessing pool
│   └── session_manager.py    # Pengelola login & penemu file sesi
└── ui/                       # Dashboard Interface
    └── dashboard.py          # Tampilkan banner & menu interaktif
```

---

## 🚀 Cara Penggunaan

### 1. Persyaratan Sistem
- Python 3.9+
- Playwright Chromium (`pip install playwright && playwright install chromium`)

### 2. Jalankan Mode Interaktif
```powershell
python autopost.py
```

### 3. Jalankan Mode CLI (Otomatis)
- **Jalankan Akun Spesifik (Mode 3: Auto Post + Auto Join)**:
  ```powershell
  python autopost.py --session session/fb_session_raden_mas.json --mode 3
  ```
- **Jalankan Seluruh Akun Secara Paralel (Headless)**:
  ```powershell
  python autopost.py --all-accounts --mode 3 --headless
  ```

---

## 🧪 Pengujian Sistem

Untuk memastikan seluruh fungsi engine berjalan 100% tanpa kendala:
```powershell
python test_all.py
```

---

## 🔒 Keamanan & Anti-Banned

- Gunakan jeda antar grup yang wajar (`3.0` s/d `6.0` detik di `config.py`).
- Batasi jumlah posting harian per akun agar tetap terlihat seperti aktivitas manusia alami.
- Pastikan file sesi `session/*.json` tersimpan dengan aman dan tidak dibagikan secara publik.
