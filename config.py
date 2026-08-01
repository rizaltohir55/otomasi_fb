"""
config.py
Konfigurasi terpusat FB AutoEngine 3.0 — Terminal Only.
"""
import os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
MEDIA_DIR   = os.path.join(BASE_DIR, "media")
SESSION_DIR = os.path.join(BASE_DIR, "session")
LOGS_DIR    = os.path.join(BASE_DIR, "logs")

for _p in [DATA_DIR, MEDIA_DIR, SESSION_DIR, LOGS_DIR]:
    os.makedirs(_p, exist_ok=True)

SESSION_FILE = os.path.join(BASE_DIR, "fb_session.json")
CAPTION_FILE = os.path.join(BASE_DIR, "caption.txt")
GROUPS_FILE  = os.path.join(BASE_DIR, "groups.txt")

# ── Timing ───────────────────────────────────────────────────────────────────
DELAY_BETWEEN_GROUPS_MIN: float = 1.0
DELAY_BETWEEN_GROUPS_MAX: float = 2.0
TYPING_SPEED_MS: int            = 3
NAVIGATION_TIMEOUT_MS: int      = 30000
ELEMENT_TIMEOUT_MS: int         = 3000

# ── Feature Switches ─────────────────────────────────────────────────────────
AUTO_LIKE_ENABLED: bool    = False
AUTO_COMMENT_ENABLED: bool = False
AUTO_COMMENTS: list        = ["Gasken", "Ready", "Inbox", "Up", "Mantap"]

# ── Concurrency ──────────────────────────────────────────────────────────────
MAX_CONCURRENT_WORKERS: int      = 3
WORKER_STAGGER_DELAY_SEC: float  = 3.0
WORKER_STARTUP_JITTER_MIN: float = 0.5
WORKER_STARTUP_JITTER_MAX: float = 2.0

# ── Anti-Ban ─────────────────────────────────────────────────────────────────
RESTRICTION_COOLDOWN_SEC: int = 30 * 60
GROUP_SKIP_FILE: str = os.path.join(DATA_DIR, "group_skip_list.txt")
MAX_RETRY_PER_GROUP: int = 1
JOIN_POLL_MAX_SEC: int = 7
MAX_MEDIA_SIZE_MB: int = 4

JOIN_QA_ANSWER_POOL: list = [
    "Setuju dengan aturan grup",
    "Saya baca dan setuju aturan",
    "Insya Allah taat aturan",
    "Mohon izin gabung, saya setuju",
    "Saya sudah paham aturan grup",
]

# ── Text Patterns ────────────────────────────────────────────────────────────
COMPOSER_TRIGGER_TEXTS = [
    "Write something...", "Tulis sesuatu...", "What's on your mind?",
    "Apa yang Anda pikirkan?", "Create a public post...",
    "Buat postingan publik...", "Create a post", "Buat postingan",
    "Escribe algo...", "Escreva algo...", "Exprimez-vous...", "Schreib etwas...",
]

SUBMIT_BUTTON_TEXTS = [
    "Post", "Posting", "Submit", "Kirim", "Publish", "Publikasikan",
    "Save", "Simpan", "Publicar", "Enviar", "Publier", "Posten",
]

PHOTO_BUTTON_TEXTS = [
    "Photo/video", "Foto/video", "Photo/Video", "Foto/Video",
    "Add to your post", "Tambahkan ke postingan Anda",
]

JOIN_BUTTON_TEXTS = [
    "Gabung ke grup", "Join group", "Bergabung dengan grup",
    "Gabung grup", "Gabung", "Join Group", "Request to join",
    "Minta Bergabung", "Join", "Unirse al grupo", "Participar do grupo",
    "Rejoindre le groupe", "Gruppe beitreten",
]

JOINED_INDICATOR_TEXTS = [
    "Sudah bergabung", "Sudah Bergabung", "Bergabung", "Joined",
    "Undang", "Invite", "Anda anggota", "You're a member", "Anggota", "Member",
]

PENDING_BUTTON_TEXTS = [
    "Request sent", "Permintaan terkirim", "Cancel request",
    "Batalkan permintaan", "Pending", "Menunggu persetujuan",
]

COMMENT_BOX_TEXTS = [
    "Write a comment...", "Tulis komentar...", "Comment", "Beri komentar",
]

RESTRICTION_TEXTS = [
    "anda tidak dapat memposting", "tidak dapat memposting di grup",
    "anda sementara dilarang", "akun anda dibatasi", "fitur ini dibatasi",
    "aktivitas anda dibatasi", "you can't post right now",
    "you're temporarily blocked", "account restricted", "action blocked",
    "temporarily restricted", "kami membatasi seberapa sering anda dapat memposting",
    "anda bisa mencoba lagi nanti", "melindungi komunitas dari spam",
    "we limit how often you can post", "try again later",
    "akun ditangguhkan sementara",
]

COMPOSER_POST_FAILURE_TEXTS = [
    "kami membatasi seberapa sering anda dapat memposting",
    "anda bisa mencoba lagi nanti", "melindungi komunitas dari spam",
    "we limit how often you can post", "you can try again later",
    "menunggu persetujuan admin", "pending admin approval",
    "terjadi kesalahan", "something went wrong", "gagal memposting",
    "coba lagi nanti", "terlihat seperti spam", "looks like spam",
]

CHECKPOINT_INDICATOR_TEXTS = [
    "two-factor authentication", "verifikasi dua langkah",
    "enter login code", "masukkan kode login",
    "save your login info", "verify it's you",
    "confirm your identity", "upload a photo of yourself",
]

PROFILE_SELECTOR_TEXTS = [
    "gunakan profil lain", "use another profile",
    "jelajahi hal-hal yang anda sukai",
]

# ── Fingerprint Profiles ─────────────────────────────────────────────────────
SPOOF_PROFILES_POOL = [
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
     "viewport": {"width": 1366, "height": 768}, "device_scale_factor": 1.0,
     "cores": 8, "memory": 8, "vendor": "Intel Inc.", "renderer": "Intel(R) UHD Graphics 620",
     "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"', "platform": "Windows"},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
     "viewport": {"width": 1920, "height": 1080}, "device_scale_factor": 1.25,
     "cores": 16, "memory": 16, "vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 3060/PCIe/SSE2",
     "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="125", "Google Chrome";v="125"', "platform": "Windows"},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
     "viewport": {"width": 1536, "height": 864}, "device_scale_factor": 1.25,
     "cores": 8, "memory": 16, "vendor": "AMD", "renderer": "AMD Radeon(TM) Graphics",
     "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="124", "Google Chrome";v="124"', "platform": "Windows"},
    {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
     "viewport": {"width": 1280, "height": 800}, "device_scale_factor": 1.0,
     "cores": 4, "memory": 4, "vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce GTX 1650/PCIe/SSE2",
     "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"', "platform": "Windows"},
]

USER_AGENT_DESKTOP = SPOOF_PROFILES_POOL[0]["user_agent"]
