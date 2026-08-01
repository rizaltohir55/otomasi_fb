#!/usr/bin/env python3
"""
autopost.py
FB AutoEngine 3.0 — Terminal Only.
Entry point CLI untuk otomasi posting/join grup Facebook.
"""
import sys
import os
import argparse
import asyncio

import config
from manager.runner import fix_windows_stdout_encoding, run_worker_entry, launch_multiprocess_runner
from manager.session_manager import discover_all_sessions, interactive_login_new_account
from engine.collector import load_groups
from ui.dashboard import print_banner, display_account_menu, display_mode_menu, display_headless_menu, parse_account_indices


def main():
    fix_windows_stdout_encoding()

    parser = argparse.ArgumentParser(
        description="FB AutoEngine 3.0 Ultra (Terminal Only)"
    )
    parser.add_argument("--session",      type=str,  help="Path file sesi JSON")
    parser.add_argument("--sessions",     nargs="+", type=str, help="Path beberapa file sesi JSON")
    parser.add_argument("--accounts",     type=str,  help="Nomor akun (cth: 1,3,5 atau 1-3)")
    parser.add_argument("--all-accounts", action="store_true", help="Jalankan semua akun paralel")
    parser.add_argument("--mode",         type=str,  choices=["1", "2", "3"], help="1=Post, 2=Join, 3=Post+Join")
    parser.add_argument("--groups-file",  type=str,  help="Path file txt daftar grup kustom")
    parser.add_argument("--start",        type=int,  help="Index grup mulai (1-based)")
    parser.add_argument("--end",          type=int,  help="Index grup akhir (1-based)")
    parser.add_argument("--headless",     action="store_true", help="Browser tanpa GUI")
    parser.add_argument("--max-workers",  type=int,  default=None, help="Batas worker paralel")
    parser.add_argument("--no-random",    dest="randomize", action="store_false", default=True, help="Matikan acak urutan grup")
    args = parser.parse_args()

    print_banner()

    # ── 1. Pilih Akun ────────────────────────────────────────────────────────
    selected_sessions = []

    if args.sessions:
        for s in args.sessions:
            if os.path.exists(s):
                selected_sessions.append(os.path.abspath(s))
            else:
                print(f"⚠️ File tidak ditemukan: {s}")
    elif args.accounts:
        all_sessions = discover_all_sessions()
        if not all_sessions:
            print("❌ Belum ada akun tersimpan.")
            return
        indices = parse_account_indices(args.accounts, len(all_sessions))
        if not indices:
            print(f"❌ Nomor tidak valid: {args.accounts}")
            return
        selected_sessions = [all_sessions[i]["path"] for i in indices]
    elif args.session:
        if os.path.exists(args.session):
            selected_sessions = [os.path.abspath(args.session)]
        else:
            print(f"❌ File tidak ditemukan: {args.session}")
            return
    elif args.all_accounts:
        all_sessions = discover_all_sessions()
        if not all_sessions:
            print("❌ Belum ada akun tersimpan.")
            return
        selected_sessions = [s["path"] for s in all_sessions]
    else:
        # Mode interaktif
        all_sessions = discover_all_sessions()
        selection = display_account_menu(all_sessions)
        if not selection:
            print("❌ Tidak ada akun dipilih.")
            return
        if selection[0] == "NEW_ACCOUNT":
            new_path = asyncio.run(interactive_login_new_account())
            if new_path and os.path.exists(new_path):
                selected_sessions = [new_path]
            else:
                return
        else:
            selected_sessions = selection

    if not selected_sessions:
        print("❌ Sesi kosong.")
        return

    # ── 2. Baca Grup ─────────────────────────────────────────────────────────
    groups = load_groups(args.groups_file)
    if not groups:
        print(f"❌ Tidak ada grup di {config.GROUPS_FILE}")
        return

    if args.start or args.end:
        st = max((args.start or 1) - 1, 0)
        ed = args.end if args.end else len(groups)
        groups = groups[st:ed]
        print(f"📍 Rentang: {st+1}-{ed} ({len(groups)} grup)")

    print(f"✅ {len(groups)} grup target.")

    # ── 3. Mode & Browser ────────────────────────────────────────────────────
    mode = args.mode
    if not mode:
        mode = display_mode_menu()

    if args.headless:
        headless = True
    elif len(sys.argv) == 1:
        headless = display_headless_menu(config.DEFAULT_HEADLESS if hasattr(config, 'DEFAULT_HEADLESS') else True)
    else:
        headless = True

    randomize = getattr(args, "randomize", True)

    print(f"\n⚙️ {len(selected_sessions)} Akun | {len(groups)} Grup | Mode: {mode} | Headless: {headless} | Acak: {randomize}")
    print(f"{'='*60}\n")

    # ── 4. Eksekusi ──────────────────────────────────────────────────────────
    if len(selected_sessions) > 1:
        launch_multiprocess_runner(
            selected_sessions, groups, mode,
            max_workers=args.max_workers,
            headless=headless,
            randomize_groups=randomize,
        )
    else:
        s_file = selected_sessions[0]
        name = os.path.basename(s_file).replace("fb_session_", "").replace(".json", "").replace("_", " ").title()
        run_worker_entry(
            session_file=s_file,
            groups=groups,
            mode=mode,
            worker_tag=name,
            headless=headless,
            randomize_groups=randomize,
        )


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Dibatalkan.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
