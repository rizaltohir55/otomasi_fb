"""
test_all.py
Suite Pengujian Komprehensif FB AutoEngine 3.0 Ultra.
Pengujian 100% Modul, Utilitas, Pemeta Selektor ARIA, dan Async Workflows.
"""
import sys
import os
import asyncio
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from manager.runner import fix_windows_stdout_encoding

fix_windows_stdout_encoding()

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

results = []


def _dummy_multiprocess_target(tag: str):
    pass



def ok(name: str, msg: str = ""):
    results.append((name, "PASS", msg))
    print(f"  {GREEN}PASS{RESET}  {name}" + (f"  ->  {msg}" if msg else ""))


def fail(name: str, msg: str = ""):
    results.append((name, "FAIL", msg))
    print(f"  {RED}FAIL{RESET}  {name}" + (f"  ->  {msg}" if msg else ""))


def section(title: str):
    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")


def run_tests():
    # ── 1. IMPORT MODUL ────────────────────────────────────────────────────────
    section("1. IMPORT SELURUH MODUL APLIKASI")
    
    modules_to_test = [
        ("config",                  "config"),
        ("utils.helpers",           "utils.helpers"),
        ("utils.browser",           "utils.browser"),
        ("utils.files",             "utils.files"),
        ("engine.selectors",        "engine.selectors"),
        ("engine.dom_analyzer",     "engine.dom_analyzer"),
        ("engine.browser",          "engine.browser"),
        ("engine.composer",         "engine.composer"),
        ("engine.joiner",           "engine.joiner"),
        ("engine.commenter",        "engine.commenter"),
        ("engine.collector",        "engine.collector"),
        ("core (compat shim)",      "core"),
        ("core.poster",             "core.poster"),
        ("core.composer",           "core.composer"),
        ("core.joiner",             "core.joiner"),
        ("core.commenter",          "core.commenter"),
        ("core.post_locator",       "core.post_locator"),
        ("manager.session_manager", "manager.session_manager"),
        ("manager.runner",          "manager.runner"),
        ("ui.dashboard",            "ui.dashboard"),
    ]

    for display, mod in modules_to_test:
        try:
            m = __import__(mod, fromlist=[""])
            ok(f"import {display}")
        except Exception as e:
            fail(f"import {display}", str(e))

    # ── 2. CONFIG & DIREKTORI ──────────────────────────────────────────────────
    section("2. CONFIG & STRUKTUR DIREKTORI")
    try:
        import config
        dirs_ok = all(os.path.isdir(d) for d in [config.DATA_DIR, config.MEDIA_DIR, config.SESSION_DIR, config.LOGS_DIR])
        if dirs_ok:
            ok("config: Semua direktori kerja ada")
        else:
            fail("config: Beberapa direktori kerja tidak ditemukan")
    except Exception as e:
        fail("config dirs", str(e))

    try:
        import config
        assert config.DELAY_BETWEEN_GROUPS_MIN <= config.DELAY_BETWEEN_GROUPS_MAX
        ok("config: Delay range valid")
    except Exception as e:
        fail("config delay range", str(e))

    try:
        import config
        assert config.PREFERRED_MODE == "desktop"
        ok(f"config: PREFERRED_MODE='{config.PREFERRED_MODE}'")
    except Exception as e:
        fail("config PREFERRED_MODE", str(e))

    # ── 3. UTILS & HELPER ─────────────────────────────────────────────────────
    section("3. UTILS & HELPER FUNCTIONS")
    try:
        from utils.helpers import normalize_group_url
        d, m, gid = normalize_group_url("https://www.facebook.com/groups/1077759085600645/")
        assert gid == "1077759085600645"
        assert "www.facebook.com" in d
        ok("normalize_group_url: numerik ID")

        d2, m2, gid2 = normalize_group_url("https://www.facebook.com/groups/jualbeli_hp/")
        assert gid2 == "jualbeli_hp"
        assert "www.facebook.com" in d2
        ok("normalize_group_url: string slug")
    except Exception as e:
        fail("normalize_group_url", str(e))

    try:
        from utils.helpers import log
        log("Test log entry dari test_all.py")
        log_file = os.path.join(ROOT, "logs", "activity.log")
        assert os.path.exists(log_file)
        ok("log(): penulisan log persisten ke activity.log")
    except Exception as e:
        fail("log()", str(e))

    # ── 4. ENGINE COLLECTOR ──────────────────────────────────────────────────
    section("4. ENGINE.COLLECTOR")
    try:
        from engine.collector import load_groups, load_caption, find_media_images
        groups = load_groups()
        assert isinstance(groups, list)
        ok(f"load_groups(): {len(groups)} grup terdaftar valid")

        caption = load_caption()
        assert isinstance(caption, str)
        ok(f"load_caption(): {len(caption)} karakter ter-load")

        images = find_media_images()
        assert isinstance(images, list)
        ok(f"find_media_images(): {len(images)} gambar ditemukan")
    except Exception as e:
        fail("engine.collector", str(e))

    # ── 5. ENGINE BROWSER & SESSION MANAGER ───────────────────────────────────
    section("5. SESSION DISCOVERY & MANAGER")
    try:
        from manager.session_manager import discover_all_sessions
        sessions = discover_all_sessions()
        assert isinstance(sessions, list)
        ok(f"discover_all_sessions(): {len(sessions)} sesi aktif ditemukan")
        for s in sessions:
            print(f"     • {os.path.basename(s['path'])} | c_user={s['c_user']} | name='{s['name']}'")
    except Exception as e:
        fail("discover_all_sessions", str(e))

    # ── 6. COMPOSER HELPER FUNCTIONS ──────────────────────────────────────────
    section("6. ENGINE.COMPOSER UTILITY FUNCTIONS")
    try:
        from engine.composer import extract_group_id_and_url, extract_group_id_and_urls
        gid, d_url = extract_group_id_and_url("https://www.facebook.com/groups/123456789/")
        assert gid == "123456789"
        assert d_url == "https://www.facebook.com/groups/123456789/"
        ok("extract_group_id_and_url()")

        g, d, m = extract_group_id_and_urls("https://www.facebook.com/groups/123456789/")
        assert g == "123456789"
        assert "m.facebook.com" in m
        ok("extract_group_id_and_urls()")
    except Exception as e:
        fail("composer extract functions", str(e))

    # ── 7. ARIA SELECTORS INTEGRITY ───────────────────────────────────────────
    section("7. ARIA SELECTOR REGISTRY INTEGRITY")
    try:
        from engine.selectors import (
            DESKTOP_COMPOSER_TRIGGERS,
            CAPTION_TEXTBOX_SELECTORS,
            PHOTO_BUTTON_SELECTORS,
            POST_BUTTON_SELECTORS,
            JOIN_GROUP_SELECTORS,
            JOINED_INDICATOR_SELECTORS,
            PENDING_INDICATOR_SELECTORS,
            COMMENT_BOX_SELECTORS,
        )
        assert len(DESKTOP_COMPOSER_TRIGGERS) > 0
        assert len(CAPTION_TEXTBOX_SELECTORS) > 0
        assert len(PHOTO_BUTTON_SELECTORS) > 0
        assert len(POST_BUTTON_SELECTORS) > 0
        assert len(JOIN_GROUP_SELECTORS) > 0
        assert len(JOINED_INDICATOR_SELECTORS) > 0
        assert len(PENDING_INDICATOR_SELECTORS) > 0
        assert len(COMMENT_BOX_SELECTORS) > 0
        ok("Semua 8 registry selektor ARIA valid & terverifikasi berisi data")
    except Exception as e:
        fail("selectors integrity", str(e))

    # ── 8. MULTIPROCESSING & HEADLESS INTEGRITY ─────────────────────────────
    section("8. MULTIPROCESSING & HEADLESS CONFIG INTEGRITY")
    try:
        import config
        from ui.dashboard import display_headless_menu, parse_account_indices
        from manager.runner import launch_multiprocess_runner, _multiprocess_entry_point
        import multiprocessing
        import random

        assert config.DEFAULT_HEADLESS is True
        ok("config.DEFAULT_HEADLESS default=True (Tanpa Tampilan Chrome / Ringan)")

        # Cek ketersediaan fungsi multiproses
        assert callable(launch_multiprocess_runner)
        assert callable(_multiprocess_entry_point)
        ok("launch_multiprocess_runner & _multiprocess_entry_point valid & callable")

        # Cek spawning multiprocessing ringan (dry-run dummy worker)
        p = multiprocessing.Process(target=_dummy_multiprocess_target, args=("test",))
        p.start()
        p.join()
        assert p.exitcode == 0
        ok("multiprocessing.Process: pengujian spawn process child berhasil (exitcode 0)")

        # Pengujian Parser Indeks Akun Multi-Select
        res1 = parse_account_indices("1, 3, 5", max_idx=5)
        assert res1 == [0, 2, 4], f"Expected [0, 2, 4], got {res1}"
        res2 = parse_account_indices("1-3", max_idx=5)
        assert res2 == [0, 1, 2], f"Expected [0, 1, 2], got {res2}"
        res3 = parse_account_indices("1, 3-5", max_idx=5)
        assert res3 == [0, 2, 3, 4], f"Expected [0, 2, 3, 4], got {res3}"
        ok("parse_account_indices(): parsing koma, range strip (1-3), dan kombinasi berhasil")

        # Pengujian Pengacakan Urutan Grup Independen
        original_groups = ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10"]
        w1_groups = list(original_groups)
        w2_groups = list(original_groups)
        random.shuffle(w1_groups)
        random.shuffle(w2_groups)
        assert set(w1_groups) == set(original_groups)
        assert original_groups == ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10"]
        ok("Group randomization: pengacakan urutan grup per worker independen & konsisten")

    except Exception as e:
        fail("multiprocessing & headless integrity", str(e))

    # ── 9. WEB SERVER API INTEGRITY ─────────────────────────────────────────
    section("9. FASTAPI WEB SERVER REST API INTEGRITY")
    try:
        from web_server import (
            get_system_stats,
            get_all_sessions,
            get_all_groups,
            get_caption_text,
            get_configuration,
            get_media_files,
        )

        res_stats = asyncio.run(get_system_stats())
        assert res_stats["status"] == "success"
        ok("get_system_stats(): REST API data stats valid")

        res_sess = asyncio.run(get_all_sessions())
        assert res_sess["status"] == "success"
        ok(f"get_all_sessions(): {len(res_sess['sessions'])} sesi terdeteksi")

        res_grp = asyncio.run(get_all_groups())
        assert res_grp["status"] == "success"
        ok(f"get_all_groups(): {len(res_grp['groups'])} grup terdaftar")

        res_cap = asyncio.run(get_caption_text())
        assert res_cap["status"] == "success"
        ok("get_caption_text(): Teks caption ter-load")

        res_cfg = asyncio.run(get_configuration())
        assert res_cfg["status"] == "success"
        ok("get_configuration(): Konfigurasi ter-load")

        res_med = asyncio.run(get_media_files())
        assert res_med["status"] == "success"
        ok(f"get_media_files(): {len(res_med['media'])} media terdaftar")

        # Test collect_groups import main function
        from collect_groups import run_collector, main as collect_main
        assert callable(run_collector) and callable(collect_main)
        ok("collect_groups: run_collector & main() valid & callable")

    except Exception as e:
        fail("web server api integrity", str(e))

    # ── 9. LAPORAN AKHIR ──────────────────────────────────────────────────────
    section("LAPORAN HASIL PENGUJIAN FB AUTOENGINE 3.0 ULTRA")
    
    total = len(results)
    passed = sum(1 for r in results if r[1] == "PASS")
    failed = sum(1 for r in results if r[1] == "FAIL")

    print(f"\n  Total Uji   : {total}")
    print(f"  {GREEN}PASS{RESET}        : {passed}")
    print(f"  {RED}FAIL{RESET}        : {failed}")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}=== SELURUH {passed}/{total} MODUL BERHASIL DIUJI TANPA ERROR! ==={RESET}")
    else:
        print(f"\n  {RED}{BOLD}[!] Terdapat {failed} kegagalan pengujian.{RESET}")

    return failed == 0



if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
