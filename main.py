#!/usr/bin/env python3
"""
main.py — Entry point CLI FB AutoEngine.
"""
import sys, os, asyncio, argparse
import config
from helpers import log, discover_sessions, load_groups, normalize_url
from runner import fix_encoding, run_single, run_multi, VALID_MODES, MODE_NAMES


def banner():
    print("""
=================================================================
   🌐 FB AUTOENGINE 3.0 — TERMINAL ONLY
=================================================================
""")


def parse_indices(s, max_n):
    """Parse '1,3,5' atau '1-3' → list 0-based indices."""
    result = set()
    for part in s.replace(" ", "").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            if a.isdigit() and b.isdigit():
                for i in range(min(int(a), int(b)), max(int(a), int(b)) + 1):
                    if 1 <= i <= max_n:
                        result.add(i - 1)
        elif part.isdigit():
            i = int(part)
            if 1 <= i <= max_n:
                result.add(i - 1)
    return sorted(result)


def menu_accounts():
    """Menu interaktif pilih akun."""
    sessions = discover_sessions()
    print("\n🔑 PILIH AKUN:")
    if not sessions:
        print("   ⚠️ Belum ada akun. Jalankan: python login.py")
        return []
    for i, s in enumerate(sessions, 1):
        print(f"   [{i}] 👤 {s['name']} (ID: {s['c_user']})")
    print(f"   [A] ⚡ Semua akun paralel")
    print(f"   [Q] ❌ Keluar")
    print("   ---")
    choice = input("👉 Pilih (cth: 1,3 atau A atau Q): ").strip().upper()
    if choice == "Q":
        return []
    if choice == "A":
        return [s["path"] for s in sessions]
    indices = parse_indices(choice, len(sessions))
    if not indices:
        print("❌ Pilihan tidak valid.")
        return []
    return [sessions[i]["path"] for i in indices]


def menu_mode():
    print("\n📋 MODE:")
    print("   [1] 🚀 Auto Post")
    print("   [2] ➕ Auto Join")
    print("   [3] ⚡ Post + Join")
    while True:
        c = input("👉 Pilih [1/2/3]: ").strip()
        if c in VALID_MODES:
            print(f"⚙️ Mode: {MODE_NAMES[c]}")
            return c


def menu_headless():
    print("\n🖥️ BROWSER:")
    print("   [1] 👻 Headless (cepat, tanpa GUI)")
    print("   [2] 🖥️ GUI (tampilan browser)")
    while True:
        c = input("👉 Pilih [1/2] (default 1): ").strip()
        if c == "2":
            return False
        return True


def main():
    fix_encoding()
    banner()

    parser = argparse.ArgumentParser(description="FB AutoEngine 3.0")
    parser.add_argument("--session", type=str, help="Path file sesi JSON")
    parser.add_argument("--accounts", type=str, help="Nomor akun (cth: 1,3 atau 1-3)")
    parser.add_argument("--all", action="store_true", help="Semua akun paralel")
    parser.add_argument("--mode", type=str, choices=["1", "2", "3"], help="1=Post 2=Join 3=Both")
    parser.add_argument("--start", type=int, help="Index grup mulai")
    parser.add_argument("--end", type=int, help="Index grup akhir")
    parser.add_argument("--headless", action="store_true", help="Tanpa GUI")
    parser.add_argument("--max-workers", type=int, help="Batas worker paralel")
    parser.add_argument("--no-random", action="store_true", help="Jangan acak urutan grup")
    args = parser.parse_args()

    # ── Pilih akun ───────────────────────────────────────────────────────────
    if args.session:
        selected = [os.path.abspath(args.session)] if os.path.exists(args.session) else []
        if not selected:
            print(f"❌ File tidak ditemukan: {args.session}")
            return
    elif args.all or args.accounts:
        sessions = discover_sessions()
        if not sessions:
            print("❌ Belum ada akun.")
            return
        if args.all:
            selected = [s["path"] for s in sessions]
        else:
            indices = parse_indices(args.accounts, len(sessions))
            selected = [sessions[i]["path"] for i in indices]
    else:
        selected = menu_accounts()

    if not selected:
        return

    # ── Baca grup ────────────────────────────────────────────────────────────
    groups = load_groups()
    if not groups:
        print(f"❌ Tidak ada grup di {config.GROUPS_FILE}")
        return

    if args.start or args.end:
        st = max((args.start or 1) - 1, 0)
        ed = args.end if args.end else len(groups)
        groups = groups[st:ed]
        print(f"📍 Rentang: {st+1}-{ed} ({len(groups)} grup)")

    print(f"✅ {len(groups)} grup siap.")

    # ── Mode ─────────────────────────────────────────────────────────────────
    mode = args.mode or menu_mode()
    headless = args.headless if args.headless else (True if len(sys.argv) > 1 else menu_headless())
    randomize = not args.no_random

    print(f"\n⚙️ {len(selected)} Akun | {len(groups)} Grup | {MODE_NAMES[mode]} | Headless: {headless}")
    print(f"{'='*60}\n")

    # ── Eksekusi ─────────────────────────────────────────────────────────────
    if len(selected) > 1:
        run_multi(selected, groups, mode,
                  max_workers=args.max_workers, headless=headless, randomize=randomize)
    else:
        from helpers import get_account_name
        name = get_account_name(selected[0])
        run_single(selected[0], groups, mode, tag=name, headless=headless, randomize=randomize)


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
