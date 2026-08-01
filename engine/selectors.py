"""
engine/selectors.py
Registry Selektor ARIA Facebook Desktop 2026 yang Terpusat & Modern.
Menghindari penggunaan obfuscated class names (.x1lliihq, dll).
"""
import config

# ── 1. COMPOSER TRIGGER SELECTORS ─────────────────────────────────────────────
DESKTOP_COMPOSER_TRIGGERS = [
    # Explicit text/label triggers (Multilingual)
    'div[role="button"][aria-label="Write something..."]',
    'div[role="button"][aria-label="Tulis sesuatu..."]',
    'div[role="button"][aria-label="Write something to the group..."]',
    'div[role="button"][aria-label="Tulis sesuatu di grup..."]',
    'div[role="button"][aria-label="What\'s on your mind?"]',
    'div[role="button"][aria-label="Apa yang Anda pikirkan?"]',
    'div[role="button"][aria-label="Escribe algo..."]',
    'div[role="button"][aria-label="Escreva algo..."]',
    'div[role="button"][aria-label="Exprimez-vous..."]',
    'div[role="button"][aria-label="Schreib etwas..."]',
    'div[role="button"]:has-text("Write something...")',
    'div[role="button"]:has-text("Tulis sesuatu...")',
    'div[role="button"]:has-text("What\'s on your mind")',
    'div[role="button"]:has-text("Apa yang Anda pikirkan")',
    'div[role="button"]:has-text("Escribe algo")',
    'div[role="button"]:has-text("Escreva algo")',
    'div[role="button"]:has-text("Exprimez-vous")',
    'div[role="button"]:has-text("Schreib etwas")',
    'div[role="button"]:has-text("Buat postingan")',
    'div[role="button"]:has-text("Create post")',
    'div[role="button"]:has-text("Crear publicación")',
    'span:has-text("Write something...")',
    'span:has-text("Tulis sesuatu...")',
    'span:has-text("Escribe algo...")',
    'span:has-text("Escreva algo...")',

    # Structural ARIA triggers (Language Independent)
    'div[role="region"] div[role="button"][aria-haspopup="dialog"]',
    'div[role="main"] div[role="button"][aria-haspopup="dialog"]',
    'div[role="button"][aria-haspopup="dialog"]',
    'div[role="main"] div[aria-placeholder]',
    'div[role="main"] span[aria-placeholder]',
]

# ── 2. CAPTION TEXTBOX SELECTORS ──────────────────────────────────────────────
CAPTION_TEXTBOX_SELECTORS = [
    'div[role="dialog"] div[role="textbox"][contenteditable="true"]',
    'div[role="dialog"] div[contenteditable="true"]',
    'div[role="dialog"] p',
    'div[role="textbox"][contenteditable="true"]',
    'div[contenteditable="true"]',
]

# ── 3. PHOTO / MEDIA BUTTON & FILE INPUT SELECTORS ────────────────────────────
PHOTO_BUTTON_SELECTORS = [
    'div[role="dialog"] div[role="button"][aria-label="Photo/video"]',
    'div[role="dialog"] div[role="button"][aria-label="Foto/video"]',
    'div[role="dialog"] div[role="button"][aria-label="Photo/Video"]',
    'div[role="dialog"] div[role="button"][aria-label="Foto/Video"]',
    'div[role="dialog"] div[role="button"][aria-label="Add to your post"]',
    'div[role="dialog"] div[role="button"][aria-label="Tambahkan ke postingan Anda"]',
    'div[role="dialog"] div[role="button"][aria-label="Agregar a tu publicación"]',
    'div[role="dialog"] div[role="button"][aria-label="Ajouter à votre publication"]',
    'div[role="dialog"] div[role="button"]:has-text("Photo/video")',
    'div[role="dialog"] div[role="button"]:has-text("Foto/video")',
    'div[role="dialog"] div[role="button"]:has-text("Photo/Video")',
    'div[role="dialog"] div[role="button"]:has-text("Foto/Video")',
]

FILE_INPUT_SELECTORS = [
    'div[role="dialog"] input[type="file"]',
    'form input[type="file"]',
    'input[type="file"][accept*="image"]',
    'input[type="file"]',
]

# ── 4. POST / SUBMIT BUTTON SELECTORS ─────────────────────────────────────────
POST_BUTTON_SELECTORS = [
    'div[role="dialog"] div[role="button"][aria-label="Post"]',
    'div[role="dialog"] div[role="button"][aria-label="Posting"]',
    'div[role="dialog"] div[role="button"][aria-label="Publicar"]',
    'div[role="dialog"] div[role="button"][aria-label="Publier"]',
    'div[role="dialog"] div[role="button"][aria-label="Posten"]',
    'div[role="dialog"] div[role="button"]:has-text("Post")',
    'div[role="dialog"] div[role="button"]:has-text("Posting")',
    'div[role="dialog"] div[role="button"]:has-text("Publicar")',
    'div[role="dialog"] div[role="button"]:has-text("Publier")',
    'div[role="dialog"] div[role="button"]:has-text("Posten")',
    'div[role="dialog"] button:has-text("Post")',
    'div[role="dialog"] button:has-text("Posting")',
    'div[role="dialog"] button:has-text("Publicar")',
    'div[role="dialog"] button:has-text("Publier")',
]

# ── 5. JOIN GROUP SELECTORS ───────────────────────────────────────────────────
JOIN_GROUP_SELECTORS = [
    # Multilingual explicit triggers
    'div[role="button"][aria-label="Gabung ke grup"]',
    'div[role="button"][aria-label="Join group"]',
    'div[role="button"][aria-label="Bergabung dengan grup"]',
    'div[role="button"][aria-label="Join Group"]',
    'div[role="button"][aria-label="Gabung grup"]',
    'div[role="button"][aria-label="Unirse al grupo"]',
    'div[role="button"][aria-label="Participar do grupo"]',
    'div[role="button"][aria-label="Rejoindre le groupe"]',
    'div[role="button"][aria-label="Gruppe beitreten"]',
    'div[role="button"]:has-text("Gabung ke grup")',
    'div[role="button"]:has-text("Join group")',
    'div[role="button"]:has-text("Bergabung dengan grup")',
    'div[role="button"]:has-text("Gabung grup")',
    'div[role="button"]:has-text("Join Group")',
    'div[role="button"]:has-text("Unirse al grupo")',
    'div[role="button"]:has-text("Participar do grupo")',
    'div[role="button"]:has-text("Rejoindre le groupe")',
    'div[role="button"]:has-text("Gruppe beitreten")',
    'button:has-text("Gabung ke grup")',
    'button:has-text("Join group")',
    'button:has-text("Bergabung dengan grup")',
    'button:has-text("Unirse al grupo")',
    'button:has-text("Rejoindre")',
    'a[role="button"][href*="/groups/join/"]',
    'a[href*="/groups/join/"]',
]

# ── 6. JOINED / MEMBERSHIP INDICATOR SELECTORS ────────────────────────────────
JOINED_INDICATOR_SELECTORS = [
    'div[role="button"][aria-label="Sudah bergabung"]',
    'div[role="button"][aria-label="Sudah Bergabung"]',
    'div[role="button"][aria-label="Bergabung"]',
    'div[role="button"][aria-label="Joined"]',
    'div[role="button"][aria-label="Undang"]',
    'div[role="button"][aria-label="Invite"]',
    'div[role="button"][aria-label="Unido"]',
    'div[role="button"][aria-label="Membre"]',
    'div[role="button"][aria-label="Beigetreten"]',
    'div[role="button"]:has-text("Sudah bergabung")',
    'div[role="button"]:has-text("Sudah Bergabung")',
    'div[role="button"]:has-text("Joined")',
    'div[role="button"]:has-text("Undang")',
    'div[role="button"]:has-text("Invite")',
    'div[role="button"]:has-text("Unido")',
    'div[role="button"]:has-text("Membre")',
    'div[role="button"]:has-text("Beigetreten")',
]

# ── 7. PENDING REQUEST INDICATOR SELECTORS ────────────────────────────────────
PENDING_INDICATOR_SELECTORS = [
    'div[role="button"][aria-label="Request sent"]',
    'div[role="button"][aria-label="Permintaan terkirim"]',
    'div[role="button"][aria-label="Cancel request"]',
    'div[role="button"][aria-label="Batalkan permintaan"]',
    'div[role="button"][aria-label="Solicitud enviada"]',
    'div[role="button"][aria-label="Demande envoyée"]',
    'div[role="button"][aria-label="Anfrage gesendet"]',
    'div[role="button"]:has-text("Request sent")',
    'div[role="button"]:has-text("Permintaan terkirim")',
    'div[role="button"]:has-text("Pending")',
    'div[role="button"]:has-text("Solicitud enviada")',
    'div[role="button"]:has-text("Demande envoyée")',
    'div[role="button"]:has-text("Anfrage gesendet")',
]

# ── 8. COMMENT BOX SELECTORS ──────────────────────────────────────────────────
COMMENT_BOX_SELECTORS = [
    'div[role="article"] div[role="textbox"][contenteditable="true"]',
    'div[role="textbox"][aria-label*="comment" i]',
    'div[role="textbox"][aria-label*="komentar" i]',
    'div[role="textbox"][aria-label*="comentario" i]',
    'div[role="textbox"][aria-label*="commentaire" i]',
    'div[role="textbox"][contenteditable="true"]',
]
