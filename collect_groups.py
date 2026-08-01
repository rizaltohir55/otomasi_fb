"""
collect_groups.py
Pengumpul Link Grup Facebook Kilat (Bulk Group Card Extractor).
Mengumpulkan dan memverifikasi link grup Facebook ber-member besar dari berbagai kota di Indonesia.
Target: Up to 1500 Unique FB Groups (Anti-Duplicate System).
"""
import asyncio
import re
import os
import sys
from playwright.async_api import async_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import SESSION_FILE, GROUPS_FILE, USER_AGENT_DESKTOP

TARGET_COUNT = 1500

RESERVED_GIDS = {
    "create", "discover", "search", "feed", "category", "joins", "user", 
    "profile", "jobs", "events", "notifications", "messages", "groups",
    "sync", "about", "members", "media", "discussion", "announcements",
    "chats", "files", "albums", "buy_sell_discussion"
}

KOTA_BESAR = [
    # Jabodetabek
    "Jakarta", "Jakarta Selatan", "Jakarta Barat", "Jakarta Timur", "Jakarta Utara", "Jakarta Pusat",
    "Bogor", "Depok", "Tangerang", "Tangerang Selatan", "Bekasi", "Cikarang", "Karawang", "Cibinong",
    # Jawa Barat & Banten
    "Bandung", "Cimahi", "Serang", "Cilegon", "Cirebon", "Tasikmalaya", "Sukabumi", "Garut", "Purwakarta",
    "Subang", "Indramayu", "Majalengka", "Kuningan", "Sumedang", "Cianjur", "Banjar",
    # Jawa Tengah & DIY
    "Semarang", "Yogyakarta", "Solo", "Surakarta", "Purwokerto", "Cilacap", "Magelang", "Salatiga", "Tegal",
    "Pekalongan", "Kudus", "Pati", "Jepara", "Klaten", "Boyolali", "Sragen", "Karanganyar", "Wonogiri",
    "Kebumen", "Wonosobo", "Temanggung", "Banjarnegara", "Purbalingga", "Pemalang", "Batang", "Kendal", "Brebes",
    # Jawa Timur
    "Surabaya", "Malang", "Sidoarjo", "Gresik", "Jember", "Kediri", "Madiun", "Probolinggo", "Pasuruan",
    "Mojokerto", "Blitar", "Tulungagung", "Banyuwangi", "Tuban", "Lamongan", "Jombang", "Nganjuk", "Ngawi",
    "Ponorogo", "Pacitan", "Trenggalek", "Bondowoso", "Situbondo", "Lumajang", "Bangkalan", "Sampang", "Pamekasan", "Sumenep",
    # Bali & Nusa Tenggara
    "Denpasar", "Singaraja", "Badung", "Gianyar", "Tabanan", "Mataram", "Bima", "Sumbawa", "Kupang", "Ende", "Maumere",
    # Sumatra
    "Medan", "Palembang", "Pekanbaru", "Batam", "Bandar Lampung", "Padang", "Jambi", "Bengkulu", "Banda Aceh",
    "Pematangsiantar", "Tanjungbalai", "Binjai", "Tebing Tinggi", "Bukittinggi", "Payakumbuh", "Dumai", "Tanjungpinang",
    "Lubuklinggau", "Prabumulih", "Pagar Alam", "Pangkalpinang", "Metro", "Duri", "Lhokseumawe",
    # Kalimantan
    "Samarinda", "Banjarmasin", "Pontianak", "Balikpapan", "Palangkaraya", "Singkawang", "Tarakan", "Bontang", "Banjarbaru",
    # Sulawesi & Indonesia Timur
    "Makassar", "Manado", "Palu", "Kendari", "Gorontalo", "Bitung", "Parepare", "Palopo", "Bau-Bau",
    "Ambon", "Jayapura", "Sorong", "Manokwari", "Ternate", "Tidore"
]

KEYWORDS_PREFIX = [
    "jual beli hp",
    "fjb hp",
    "hp second",
    "bursa hp",
    "pasar hp",
    "forum hp",
    "jual beli hp bekas",
    "jual hp murah",
    "fjb smartphone",
    "jual beli gadget",
    "bursa hp second",
    "lapak hp",
    "konter hp online",
    "tukar tambah hp",
    "servis hp",
    "jual beli iphone",
    "jual beli android",
    "komunitas hp",
    "pasar hp second"
]


def extract_group_id(url: str) -> str:
    """Ekstrak Canonical Group ID dari URL Facebook."""
    if not url:
        return ""
    clean_url = url.split("?")[0].split("#")[0]
    m = re.search(r'/groups/([0-9a-zA-Z._-]+)', clean_url)
    if m:
        gid = m.group(1).strip("/").lower()
        if gid not in RESERVED_GIDS and len(gid) > 2:
            return gid
    return ""


def clean_and_load_groups() -> tuple[set, set]:
    """Muat daftar grup yang ada dan bersihkan duplikat secara ketat."""
    if not os.path.exists(GROUPS_FILE):
        return set(), set()

    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    unique_entries = []
    seen_gids = set()
    existing_urls = set()

    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue

        gid = extract_group_id(raw)
        if gid and gid not in seen_gids:
            seen_gids.add(gid)
            canonical_url = f"https://facebook.com/groups/{gid}/"
            existing_urls.add(canonical_url)
            unique_entries.append(canonical_url)

    # Tulis ulang file groups.txt dengan header terbaru
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        f.write("# ============================================\n")
        f.write("# Daftar link grup Facebook (satu link per baris)\n")
        f.write("# Baris yang diawali '#' diabaikan sebagai komentar\n")
        f.write(f"# Total: {len(unique_entries)} grup (Verified Unique)\n")
        f.write("# ============================================\n\n")
        for u in unique_entries:
            f.write(f"{u}\n")

    return existing_urls, seen_gids


def save_group_url(canonical_url: str, existing_urls: set, seen_gids: set) -> bool:
    """Simpan URL grup baru ke file groups.txt secara langsung."""
    gid = extract_group_id(canonical_url)
    if not gid or gid in seen_gids:
        return False

    seen_gids.add(gid)
    existing_urls.add(canonical_url)

    with open(GROUPS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{canonical_url}\n")
    return True


async def setup_desktop_browser(playwright, session_file: str = None):
    """Inisialisasi browser Playwright Chromium untuk pengumpulan grup."""
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--window-size=1366,768",
        ],
    )

    context_args = {
        "viewport": {"width": 1366, "height": 768},
        "user_agent": USER_AGENT_DESKTOP,
        "is_mobile": False,
        "has_touch": False,
    }

    target_session = session_file or SESSION_FILE
    if os.path.exists(target_session):
        context_args["storage_state"] = target_session

    context = await browser.new_context(**context_args)
    page = await context.new_page()
    return browser, context, page


async def run_collector():
    """Jalankan pengumpul link grup otomatis."""
    print("=================================================================")
    print(f"  [SEARCH] PENGUMPUL LINK GRUP FACEBOOK (TARGET: {TARGET_COUNT} GRUP)")
    print("=================================================================")

    existing_urls, seen_gids = clean_and_load_groups()
    print(f"[STATUS] Grup unik tersimpan di groups.txt saat ini: {len(existing_urls)} grup.")

    if len(existing_urls) >= TARGET_COUNT:
        print(f"[SUCCESS] Target {TARGET_COUNT} grup sudah tercapai! Tidak perlu pencarian tambahan.")
        return

    async with async_playwright() as p:
        browser, context, page = await setup_desktop_browser(p)

        try:
            await page.goto("https://www.facebook.com/groups/", timeout=30000)
            await page.wait_for_timeout(3000)

            for prefix in KEYWORDS_PREFIX:
                for kota in KOTA_BESAR:
                    if len(existing_urls) >= TARGET_COUNT:
                        break

                    query = f"{prefix} {kota}"
                    search_url = f"https://www.facebook.com/search/groups/?q={query.replace(' ', '%20')}"
                    print(f"\n[QUERY] Mencari: '{query}'...")

                    try:
                        await page.goto(search_url, timeout=25000)
                        await page.wait_for_timeout(2500)

                        # Scroll lebih dalam (5 kali) untuk memuat lebih banyak kartu grup
                        for _ in range(5):
                            await page.mouse.wheel(0, 800)
                            await page.wait_for_timeout(1200)

                        links = await page.locator('a[href*="/groups/"]').all()
                        added_in_query = 0

                        for link in links:
                            href = await link.get_attribute("href")
                            if href:
                                gid = extract_group_id(href)
                                if gid and gid not in seen_gids:
                                    canon = f"https://facebook.com/groups/{gid}/"
                                    if save_group_url(canon, existing_urls, seen_gids):
                                        added_in_query += 1

                        print(f"   [+] Ditambahkan {added_in_query} grup baru (Total: {len(existing_urls)}/{TARGET_COUNT})")

                    except Exception as e:
                        print(f"   [!] Warning pada query '{query}': {e}")

                    await asyncio.sleep(1.5)

        finally:
            await browser.close()

    # Pembersihan akhir file untuk memperbarui jumlah total di header
    clean_and_load_groups()
    print(f"\n[FINISH] Pengumpulan Selesai! Total grup unik tersimpan: {len(seen_gids)}")


async def main():
    """Alias untuk run_collector() untuk kompatibilitas import."""
    await run_collector()


if __name__ == "__main__":
    asyncio.run(run_collector())


