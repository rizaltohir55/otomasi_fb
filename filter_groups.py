"""
filter_groups.py
Script Pemilah & Penghapus Grup Jual Beli (Buy/Sell Groups Filter) Pure DOM JS Analyzer.
Memeriksa seluruh grup di groups.txt dan menghapus grup berjenis posting 'Jual Beli',
hanya menyisakan grup berjenis posting 'Diskusi'.
"""
import os
import sys
import json
import asyncio
import shutil
from typing import List, Dict
from playwright.async_api import async_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from config import GROUPS_FILE, SESSION_DIR, SESSION_FILE

GROUPS_BAK = GROUPS_FILE + ".bak"
PROGRESS_FILE = os.path.join(BASE_DIR, "scratch", "group_filter_progress.json")
os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)

def get_best_session_file() -> str:
    """Cari file sesi login FB utama."""
    if os.path.exists(SESSION_FILE):
        return SESSION_FILE
    if os.path.exists(SESSION_DIR):
        files = [os.path.join(SESSION_DIR, f) for f in os.listdir(SESSION_DIR) if f.endswith(".json") and not f.endswith(".bak")]
        if files:
            return files[0]
    return ""

def load_progress() -> Dict[str, Dict]:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_progress(data: Dict[str, Dict]):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

async def check_group_type(context, url: str) -> Dict:
    """
    Periksa jenis postingan grup (Jual Beli vs Diskusi) menggunakan Murni Standard DOM JS.
    """
    page = None
    try:
        page = await context.new_page()
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1800)

        title = await page.title()
        clean_title = title.encode('ascii', 'ignore').decode('ascii').strip()

        # Deteksi via Pure JavaScript Native Selectors
        detection = await page.evaluate('''() => {
            const allBtns = Array.from(document.querySelectorAll('div[role="button"], span, a, input'));
            
            const sellTriggers = allBtns.filter(el => {
                const txt = (el.innerText || el.getAttribute('placeholder') || '').trim().toLowerCase();
                return txt === 'jual sesuatu' || 
                       txt === 'sell something' || 
                       txt === 'apa yang anda jual?' || 
                       txt === 'what are you selling?' ||
                       txt === 'buat postingan jual beli';
            });

            const discussionTriggers = allBtns.filter(el => {
                const txt = (el.innerText || el.getAttribute('placeholder') || '').trim().toLowerCase();
                return txt.includes('tulis sesuatu') || 
                       txt.includes('write something') ||
                       txt.includes('buat postingan publik');
            });

            const allTabs = Array.from(document.querySelectorAll('a[role="tab"], div[role="tab"], a'));
            const hasBuySellTab = allTabs.some(t => {
                const txt = (t.innerText || '').trim().toLowerCase();
                const href = (t.getAttribute('href') || '').toLowerCase();
                return href.includes('/buy_sell') || txt.includes('jual beli') || txt.includes('buy and sell');
            });

            return {
                sell_count: sellTriggers.length,
                disc_count: discussionTriggers.length,
                has_buy_sell_tab: hasBuySellTab
            };
        }''')

        # Kriteria Jual Beli vs Diskusi:
        # Jika terdapat tombol 'Jual Sesuatu' / 'Apa yang Anda jual?' -> JUAL_BELI
        # Atau jika tab Jual Beli aktif & tidak ada trigger Diskusi -> JUAL_BELI
        is_jual_beli = (detection["sell_count"] > 0) or (detection["has_buy_sell_tab"] and detection["disc_count"] == 0)

        return {
            "url": url,
            "title": clean_title,
            "is_jual_beli": is_jual_beli,
            "type": "JUAL_BELI" if is_jual_beli else "DISKUSI",
            "details": detection
        }
    except Exception as e:
        return {
            "url": url,
            "title": "Unknown",
            "is_jual_beli": False,
            "type": "UNKNOWN_ERROR",
            "error": str(e)
        }
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass

async def worker(worker_id: int, queue: asyncio.Queue, context, progress_store: Dict[str, Dict], lock: asyncio.Lock):
    while True:
        try:
            url = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        res = await check_group_type(context, url)
        
        async with lock:
            progress_store[url] = res
            save_progress(progress_store)
            
            idx = len(progress_store)
            tag = "🛒 JUAL_BELI" if res.get("is_jual_beli") else ("💬 DISKUSI" if res.get("type") == "DISKUSI" else "❓ ERROR")
            title_snippet = res.get("title", "")[:30]
            print(f"[{idx:04d}] [W{worker_id}] {tag:12s} | {title_snippet:30s} | {url}")

        queue.task_done()

async def main():
    print("=================================================================")
    print("  [FILTER] PEMILAH & PENGHAPUS GRUP FB JUAL BELI (ONLY DISKUSI)")
    print("=================================================================")

    target_file = GROUPS_FILE
    if not os.path.exists(target_file) and os.path.exists(GROUPS_BAK):
        target_file = GROUPS_BAK

    if not os.path.exists(target_file):
        print(f"❌ File {target_file} tidak ditemukan!")
        return

    # 1. Backup file groups.txt
    if not os.path.exists(GROUPS_BAK):
        shutil.copyfile(target_file, GROUPS_BAK)
        print(f"✅ Backup berhasil dibuat: {GROUPS_BAK}")

    # 2. Baca daftar grup
    with open(GROUPS_BAK, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    urls = []
    for line in raw_lines:
        line_str = line.strip()
        if line_str and not line_str.startswith("#"):
            urls.append(line_str)

    progress_store = load_progress()
    
    # Hapus entri UNKNOWN_ERROR terdahulu agar diperiksa ulang dengan JS DOM selector yang bersih
    cleaned_progress = {k: v for k, v in progress_store.items() if v.get("type") != "UNKNOWN_ERROR"}
    if len(cleaned_progress) != len(progress_store):
        print(f"🧹 Membersihkan {len(progress_store) - len(cleaned_progress)} entri error terdahulu...")
        progress_store = cleaned_progress
        save_progress(progress_store)

    print(f"📊 Total grup original: {len(urls)} grup")
    print(f"🔄 Grup yang sudah berhasil diverifikasi: {len(progress_store)} grup")

    pending_urls = [u for u in urls if u not in progress_store]
    print(f"🎯 Grup yang perlu diperiksa saat ini: {len(pending_urls)} grup\n")

    session_file = get_best_session_file()
    if session_file:
        print(f"🔑 Menggunakan file sesi: {os.path.basename(session_file)}")

    # 3. Jalankan pengujian paralel Playwright (3 worker untuk kecepatan optimal)
    NUM_WORKERS = 3
    lock = asyncio.Lock()
    queue = asyncio.Queue()

    for u in pending_urls:
        queue.put_nowait(u)

    if pending_urls:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )

            context = await browser.new_context(
                storage_state=session_file if session_file else None,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )

            tasks = []
            for w_id in range(1, NUM_WORKERS + 1):
                t = asyncio.create_task(worker(w_id, queue, context, progress_store, lock))
                tasks.append(t)

            await asyncio.gather(*tasks)
            await browser.close()

    # 4. Filter hasil & perbarui groups.txt
    discussion_urls = []
    jual_beli_urls = []
    error_urls = []

    for u in urls:
        r = progress_store.get(u, {})
        t = r.get("type")
        if t == "DISKUSI":
            discussion_urls.append(u)
        elif t == "JUAL_BELI":
            jual_beli_urls.append(u)
        else:
            error_urls.append(u)
            discussion_urls.append(u)

    print("\n=================================================================")
    print("  📊 REKAPITULASI PEMILAHAN GRUP")
    print("=================================================================")
    print(f" Total Grup Diperiksa        : {len(urls)}")
    print(f" 🛒 Grup Jual Beli (Dihapus)  : {len(jual_beli_urls)}")
    print(f" 💬 Grup Diskusi (Disimpan)  : {len(discussion_urls) - len(error_urls)}")
    if error_urls:
        print(f" ⚠️  Grup Timeout/Error (Disimpan) : {len(error_urls)}")
    print("=================================================================\n")

    # Tulis ulang groups.txt
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        f.write("# ============================================\n")
        f.write("# Daftar link grup Facebook (satu link per baris)\n")
        f.write("# Baris yang diawali '#' diabaikan sebagai komentar\n")
        f.write(f"# Total: {len(discussion_urls)} grup Diskusi (Verified Filtered)\n")
        f.write("# ============================================\n\n")
        for u in discussion_urls:
            f.write(f"{u}\n")

    print(f"✅ Berhasil memperbarui {GROUPS_FILE}!")
    print(f"  - Total grup tersisa: {len(discussion_urls)} (Semua berjenis posting Diskusi)")
    print(f"  - File cadangan original disimpan di: {GROUPS_BAK}")

if __name__ == "__main__":
    asyncio.run(main())
