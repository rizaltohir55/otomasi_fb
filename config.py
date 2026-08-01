"""
config.py — Pengaturan terpusat.
"""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(DIR, "session")
MEDIA_DIR   = os.path.join(DIR, "media")
LOGS_DIR    = os.path.join(DIR, "logs")
DATA_DIR    = os.path.join(DIR, "data")
for d in [SESSION_DIR, MEDIA_DIR, LOGS_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

CAPTION_FILE = os.path.join(DIR, "caption.txt")
GROUPS_FILE  = os.path.join(DIR, "groups.txt")

# Timing (detik) — natural, tidak terlalu cepat
DELAY_MIN = 8.0    # minimal 8 detik antar grup
DELAY_MAX = 20.0   # maksimal 20 detik antar grup
TYPE_DELAY_MS = 15  # ketik lebih lambat (manusia rata-rata)
NAV_TIMEOUT = 30000
ELEMENT_TIMEOUT = 3000

# Concurrency
MAX_WORKERS = 3
STAGGER_SEC = 3.0
JITTER_MIN = 0.5
JITTER_MAX = 2.0

# Anti-ban
COOLDOWN_SEC = 1800  # 30 menit
MAX_MEDIA_MB = 4
SKIP_FILE = os.path.join(DATA_DIR, "skip_list.txt")

# Batas post per session — stop SEBELUM kena limit FB
MAX_POST_PER_SESSION = 8   # FB restriksi ~20 post, stop di 8 untuk sangat aman

# Auto-loop: setelah max post tercapai, jeda lalu lanjut otomatis
SESSION_BREAK_MIN = 600    # 10 menit jeda antar session
SESSION_BREAK_MAX = 1200   # 20 menit jeda maksimal
SESSION_MAX_LOOPS = 0      # 0 = unlimited (stop manual dengan Ctrl+C)

# Break panjang setiap N grup (simulasi istirahat manusia)
BREAK_EVERY_N = 4          # setiap 4 grup, ambil jeda panjang
BREAK_MIN_SEC = 120        # jeda 120-300 detik (2-5 menit)
BREAK_MAX_SEC = 300

# Rotasi caption — variasi teks supaya tidak identik
CAPTION_VARIATIONS = []  # diisi dari caption.txt, dipakai bergantian

# Spoof profiles
PROFILES = [
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
     "vp": {"width": 1366, "height": 768}, "scale": 1.0, "cores": 8, "mem": 8,
     "vendor": "Intel Inc.", "gpu": "Intel(R) UHD Graphics 620",
     "chua": '"Not/A)Brand";v="8", "Chromium";v="126"', "platform": "Windows"},
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
     "vp": {"width": 1920, "height": 1080}, "scale": 1.25, "cores": 16, "mem": 16,
     "vendor": "NVIDIA Corporation", "gpu": "NVIDIA GeForce RTX 3060",
     "chua": '"Not/A)Brand";v="8", "Chromium";v="125"', "platform": "Windows"},
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
     "vp": {"width": 1536, "height": 864}, "scale": 1.25, "cores": 8, "mem": 16,
     "vendor": "AMD", "gpu": "AMD Radeon(TM) Graphics",
     "chua": '"Not/A)Brand";v="8", "Chromium";v="124"', "platform": "Windows"},
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
     "vp": {"width": 1280, "height": 800}, "scale": 1.0, "cores": 4, "mem": 4,
     "vendor": "NVIDIA Corporation", "gpu": "NVIDIA GeForce GTX 1650",
     "chua": '"Not/A)Brand";v="8", "Chromium";v="123"', "platform": "Windows"},
]

# Teks multibahasa
TRIGGER_TEXTS = [
    "Write something...", "Tulis sesuatu...", "What's on your mind?",
    "Apa yang Anda pikirkan?", "Create a public post", "Buat postingan",
    "Escribe algo...", "Escreva algo...",
]
SUBMIT_TEXTS = ["Post", "Posting", "Publish", "Publikasikan", "Submit", "Kirim"]
JOIN_TEXTS = [
    "Gabung ke grup", "Join group", "Bergabung dengan grup",
    "Gabung grup", "Join Group",
    "Minta Bergabung", "Unirse al grupo", "Participar do grupo",
    "Rejoindre le groupe", "Gruppe beitreten",
]
JOINED_TEXTS = [
    "Sudah bergabung", "Joined", "Bergabung", "Gabung", "Undang", "Invite",
    "Anda anggota", "You're a member", "Member", "Anggota",
]
PENDING_TEXTS = [
    "Request sent", "Permintaan terkirim",
    "Cancel request", "Batalkan permintaan",
]
PHOTO_TEXTS = ["Photo/video", "Foto/video", "Add to your post", "Tambahkan ke"]
FAIL_TEXTS = [
    "kami membatasi", "anda bisa mencoba lagi nanti", "melindungi komunitas",
    "we limit how often", "try again later", "something went wrong",
    "terjadi kesalahan", "gagal memposting", "spam", "tidak dapat memposting",
    "you can't post", "action blocked",
]
CHECKPOINT_TEXTS = [
    "two-factor", "verifikasi dua langkah", "enter login code",
    "verify it's you", "confirm your identity", "upload a photo",
]
QA_ANSWERS = [
    "Setuju dengan aturan grup", "Saya baca dan setuju aturan",
    "Insya Allah taat aturan", "Mohon izin gabung", "Saya paham aturan",
]
