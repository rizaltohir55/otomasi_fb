"""
autopost.py
Skrip Utama FB AutoEngine 3.0 Ultra.
Mendukung Mode Interaktif Terminal maupun Mode Argumen CLI (Multi-Account & Multi-Process).
"""
import sys
import os
import argparse
import asyncio

import config
from utils.helpers import auto_pull_github
from manager.runner import fix_windows_stdout_encoding, run_worker_entry, launch_multiprocess_runner
from manager.session_manager import discover_all_sessions, interactive_login_new_account
from engine.collector import load_groups
from ui.dashboard import print_banner, display_account_menu, display_mode_menu, display_headless_menu, parse_account_indices


def main():
    fix_windows_stdout_encoding()
    auto_pull_github()

    parser = argparse.ArgumentParser(
        description="FB AutoEngine 3.0 Ultra (Pure Desktop React ARIA Automation & Multi-Account Engine)"
    )
    parser.add_argument("--web",          action="store_true", help="Buka Antarmuka Web (Web Control Center GUI)")
    parser.add_argument("--session",      type=str,  help="Path ke file sesi JSON (opsional)")
    parser.add_argument("--sessions",     nargs="+", type=str, help="Path ke beberapa file sesi JSON")
    parser.add_argument("--accounts",     type=str,  help="Indeks/nomor akun yang ingin dijalankan (cth: 1,3,5 atau 1-3)")
    parser.add_argument("--all-accounts", action="store_true", help="Jalankan seluruh akun tersimpan secara paralel")
    parser.add_argument("--mode",         type=str,  choices=["1", "2", "3"], help="1=Post, 2=Join, 3=Post+Join")
    parser.add_argument("--groups-file",  type=str,  help="Path file txt daftar grup kustom")
    parser.add_argument("--start",        type=int,  help="Indeks grup mulai (1-based)")
    parser.add_argument("--end",          type=int,  help="Indeks grup akhir (1-based)")
    parser.add_argument("--headless",     action="store_true", help="Jalankan browser tanpa tampilan GUI")
    parser.add_argument("--max-workers",  type=int, default=None, help="Batas maksimal worker akun paralel bersamaan")
    parser.add_argument("--no-random-groups", dest="randomize_groups", action="store_false", default=True, help="Matikan pengacakan urutan grup per akun")
    args = parser.parse_args()

    if args.web:
        import run_web
        run_web.main()
        return

    print_banner()


    # ── 1. Tentukan Sesi Akun Facebook ─────────────────────────────────────────
    selected_sessions = []

    if args.sessions:
        for s_path in args.sessions:
            if os.path.exists(s_path):
                selected_sessions.append(os.path.abspath(s_path))
            else:
                print(f"⚠️ File sesi tidak ditemukan: {s_path}")
    elif args.accounts:
        all_sessions = discover_all_sessions()
        if not all_sessions:
            print("❌ Belum ada akun tersimpan di folder session/ atau root.")
            return
        indices = parse_account_indices(args.accounts, len(all_sessions))
        if not indices:
            print(f"❌ Nomor akun tidak valid: {args.accounts}")
            return
        selected_sessions = [all_sessions[i]["path"] for i in indices]
    elif args.session:
        if os.path.exists(args.session):
            selected_sessions = [os.path.abspath(args.session)]
        else:
            print(f"❌ File sesi tidak ditemukan: {args.session}")
            return
    elif args.all_accounts:
        all_sessions = discover_all_sessions()
        if not all_sessions:
            print("❌ Belum ada akun tersimpan di folder session/ atau root.")
            return
        selected_sessions = [s["path"] for s in all_sessions]
    else:
        # Mode Interaktif Dashboard
        all_sessions = discover_all_sessions()
        selection = display_account_menu(all_sessions)
        if not selection:
            print("❌ Tidak ada akun yang dipilih.")
            return

        if selection[0] == "NEW_ACCOUNT":
            new_path = asyncio.run(interactive_login_new_account())
            if os.path.exists(new_path):
                selected_sessions = [new_path]
            else:
                return
        else:
            selected_sessions = selection

    if not selected_sessions:
        print("❌ Sesi akun kosong. Keluar.")
        return

    # ── 2. Baca & Filter Daftar Grup ──────────────────────────────────────────
    groups = load_groups(args.groups_file)
    if not groups:
        print("❌ Tidak ada daftar grup yang ditemukan untuk diproses.")
        print(f"   Pastikan file {config.GROUPS_FILE} berisi link grup Facebook valid.")
        return

    if args.start or args.end:
        start_idx = max((args.start or 1) - 1, 0)
        end_idx   = args.end if args.end else len(groups)
        groups    = groups[start_idx:end_idx]
        print(f"📍 Rentang grup difilter: {start_idx + 1} s/d {end_idx} (Total: {len(groups)} grup)")

    print(f"✅ Ditemukan {len(groups)} grup target valid.")

    # ── 3. Tentukan Mode Operasi & Browser ───────────────────────────────────
    mode = args.mode
    if not mode:
        mode = display_mode_menu()

    if args.headless:
        headless_mode = True
    elif len(sys.argv) == 1:
        # Mode Interaktif Terminal
        headless_mode = display_headless_menu(config.DEFAULT_HEADLESS)
    else:
        headless_mode = config.DEFAULT_HEADLESS

    randomize_groups = getattr(args, "randomize_groups", True)

    print(f"⚙️ Menjalankan {len(selected_sessions)} Akun | {len(groups)} Grup | Mode: {mode} | Headless: {'AKTIF' if headless_mode else 'NON-AKTIF'} | Posting Grup: {'ACAK (Random)' if randomize_groups else 'BERURUTAN'}")

    # ── 4. Eksekusi Engine ───────────────────────────────────────────────────
    if len(selected_sessions) > 1:
        # Jalankan Multi-Akun Paralel
        launch_multiprocess_runner(
            selected_sessions,
            groups,
            mode,
            max_workers=args.max_workers,
            headless=headless_mode,
            randomize_groups=randomize_groups
        )
    else:
        # Jalankan Single Akun
        single_session = selected_sessions[0]
        sess_name = (
            os.path.basename(single_session)
            .replace("fb_session_", "")
            .replace(".json", "")
            .replace("_", " ")
            .title()
        )
        run_worker_entry(
            session_file=single_session,
            groups=groups,
            mode=mode,
            worker_tag=f"Akun-{sess_name}",
            headless=headless_mode,
            randomize_groups=randomize_groups,
        )


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Dibatalkan oleh pengguna.")
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}")