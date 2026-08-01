"""
config.py
Konfigurasi terpusat FB AutoEngine 3.0 Ultra.
Arsitektur Pure Desktop React ARIA Automation & Stealth Engine.
"""
import os

# ── Base Directory Structure ──────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
MEDIA_DIR   = os.path.join(BASE_DIR, "media")
SESSION_DIR = os.path.join(BASE_DIR, "session")
LOGS_DIR    = os.path.join(BASE_DIR, "logs")

# Pastikan seluruh direktori esensial selalu ada
for _path in [DATA_DIR, MEDIA_DIR, SESSION_DIR, LOGS_DIR]:
    os.makedirs(_path, exist_ok=True)


def resolve_file_path(filename: str, default_folder: str) -> str:
    """Cari file di root directory terlebih dahulu; jika tidak ada, gunakan default_folder."""
    root_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(root_path):
        return root_path
    return os.path.join(default_folder, filename)


SESSION_FILE = resolve_file_path("fb_session.json", SESSION_DIR)
CAPTION_FILE = resolve_file_path("caption.txt", DATA_DIR)
GROUPS_FILE  = resolve_file_path("groups.txt", DATA_DIR)

# ── Behavior & Stealth Settings ─────────────────────────────────────────────
DEFAULT_HEADLESS: bool = True
PREFERRED_MODE: str    = "desktop"  # Pure Desktop React ARIA Engine

# Timing settings (detik/milidetik)
DELAY_BETWEEN_GROUPS_MIN: float = 2.0
DELAY_BETWEEN_GROUPS_MAX: float = 4.0
TYPING_SPEED_MS: int            = 5
NAVIGATION_TIMEOUT_MS: int      = 45000
ELEMENT_TIMEOUT_MS: int         = 5000

# Feature Switches
AUTO_LIKE_ENABLED: bool    = False
AUTO_COMMENT_ENABLED: bool = False
AUTO_COMMENTS: list[str]   = ["Gasken", "Ready", "Inbox", "Up", "Mantap"]

# ── Multi-Account Execution & Concurrency ──────────────────────────────────────
MAX_CONCURRENT_WORKERS: int      = 3
WORKER_STAGGER_DELAY_SEC: float  = 3.0

# ── Real Fingerprint & Stealth Spoofing Profiles Pool ───────────────────────
SPOOF_PROFILES_POOL = [
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "viewport": {"width": 1366, "height": 768},
        "device_scale_factor": 1.0,
        "cores": 8,
        "memory": 8,
        "vendor": "Intel Inc.",
        "renderer": "Intel(R) UHD Graphics 620",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "device_scale_factor": 1.25,
        "cores": 16,
        "memory": 16,
        "vendor": "NVIDIA Corporation",
        "renderer": "NVIDIA GeForce RTX 3060/PCIe/SSE2",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="125", "Google Chrome";v="125"',
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1536, "height": 864},
        "device_scale_factor": 1.25,
        "cores": 8,
        "memory": 16,
        "vendor": "AMD",
        "renderer": "AMD Radeon(TM) Graphics",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="124", "Google Chrome";v="124"',
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        "viewport": {"width": 1440, "height": 900},
        "device_scale_factor": 1.0,
        "cores": 4,
        "memory": 8,
        "vendor": "Intel Inc.",
        "renderer": "Intel(R) Iris(R) Xe Graphics",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "viewport": {"width": 1280, "height": 800},
        "device_scale_factor": 1.0,
        "cores": 4,
        "memory": 4,
        "vendor": "NVIDIA Corporation",
        "renderer": "NVIDIA GeForce GTX 1650/PCIe/SSE2",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"',
        "platform": "Windows",
    },
]

# User-Agent String Desktop Chrome Modern Default
USER_AGENT_DESKTOP = SPOOF_PROFILES_POOL[0]["user_agent"]

# ── Multilingual ARIA Text Patterns (Indonesian, English, Spanish, French, German, Portuguese, Tagalog, Vietnamese, Malay) ─────────────
COMPOSER_TRIGGER_TEXTS = [
    # Indonesian
    "Write something...",
    "Tulis sesuatu...",
    "Write something to the group...",
    "Tulis sesuatu di grup...",
    "What's on your mind?",
    "Apa yang Anda pikirkan?",
    "Create a public post...",
    "Buat postingan publik...",
    "Create a post",
    "Buat postingan",
    "Write something",
    "Tulis sesuatu",
    "Jual sesuatu",
    # English
    "What are you selling?",
    "Create a post...",
    "Write a post...",
    "Sell something",
    # Spanish
    "Escribe algo...",
    "Escribe algo en el grupo...",
    "¿Qué estás pensando?",
    "Crear publicación",
    "Vender algo",
    # Portuguese
    "Escreva algo...",
    "No que você está pensando?",
    "Criar publicação",
    "Vender algo",
    # French
    "Exprimez-vous...",
    "Qu'avez-vous en tête ?",
    "Créer une publication",
    "Vendre quelque chose",
    # German
    "Schreib etwas...",
    "Was machst du gerade?",
    "Beitrag erstellen",
    "Etwas verkaufen",
    # Tagalog / Vietnamese
    "Magsulat ng sesuatu...",
    "Ano ang nasa isip mo?",
    "Viết gì đó...",
    "Bạn đang nghĩ gì?",
]

SUBMIT_BUTTON_TEXTS = [
    "Post",
    "Posting",
    "Submit",
    "Kirim",
    "Publish",
    "Publikasikan",
    "Save",
    "Simpan",
    "Publicar",
    "Enviar",
    "Compartir",
    "Publier",
    "Partager",
    "Posten",
    "Veröffentlichen",
]

PHOTO_BUTTON_TEXTS = [
    "Photo/video",
    "Foto/video",
    "Photo/Video",
    "Foto/Video",
    "Photo",
    "Foto",
    "Add photo/video",
    "Tambah foto/video",
    "Tambahkan ke postingan Anda",
    "Add to your post",
    "Agregar a tu publicación",
    "Ajouter à votre publication",
    "Zu deinem Beitrag hinzufügen",
    "Adicionar à sua publicação",
]

JOIN_BUTTON_TEXTS = [
    "Gabung ke grup",
    "Join group",
    "Bergabung dengan grup",
    "Gabung grup",
    "Gabung dengan grup",
    "Gabung",
    "Join Group",
    "Request to join",
    "Minta Bergabung",
    "Minta bergabung",
    "Minta bergabung dengan grup",
    "Join",
    "Unirse al grupo",
    "Unirme",
    "Unirse",
    "Solicitar unirse",
    "Participar do grupo",
    "Participar",
    "Rejoindre le groupe",
    "Rejoindre",
    "Demander à rejoindre",
    "Gruppe beitreten",
    "Beitreten",
    "Beitritt anfragen",
    "Sumali sa grupo",
    "Sumali",
    "Tham gia nhóm",
]

JOINED_INDICATOR_TEXTS = [
    "Sudah bergabung",
    "Sudah Bergabung",
    "Bergabung",
    "Joined",
    "Undang",
    "Invite",
    "Anda anggota",
    "You're a member",
    "Anggota",
    "Member",
    "Unido",
    "Unida",
    "Invitar",
    "Eres miembro",
    "Miembro",
    "Participando",
    "Convidar",
    "Você é membro",
    "Membre",
    "Inviter",
    "Vous êtes membre",
    "Beigetreten",
    "Einladen",
    "Du bist Mitglied",
    "Mitglied",
]

PENDING_BUTTON_TEXTS = [
    "Request sent",
    "Permintaan terkirim",
    "Cancel request",
    "Batalkan permintaan",
    "Pending",
    "Menunggu persetujuan",
    "Solicitud enviada",
    "Cancelar solicitud",
    "Pendiente",
    "Solicitação enviada",
    "Cancelar solicitação",
    "Pendente",
    "Demande envoyée",
    "Annuler la demande",
    "En attente",
    "Anfrage gesendet",
    "Anfrage abbrechen",
    "Ausstehend",
]

COMMENT_BOX_TEXTS = [
    "Write a comment...",
    "Tulis komentar...",
    "Write a public comment...",
    "Tulis komentar publik...",
    "Write a comment",
    "Tulis komentar",
    "Comment",
    "Beri komentar",
    "Escribe un comentario...",
    "Escreva um comentário...",
    "Écrire un commentaire...",
    "Schreibe einen Kommentar...",
    "Viết bình luận...",
]

RESTRICTION_TEXTS = [
    "anda tidak dapat memposting",
    "tidak dapat memposting di grup",
    "tidak dapat menggunakan fitur ini saat ini",
    "posting dibatasi",
    "anda sementara dilarang",
    "akun anda dibatasi",
    "fitur ini dibatasi",
    "aktivitas anda dibatasi",
    "batas sementara",
    "you can't post right now",
    "you can't post to groups",
    "you're temporarily blocked",
    "you can't use this feature right now",
    "account restricted",
    "feature restricted",
    "action blocked",
    "temporarily restricted",
]

