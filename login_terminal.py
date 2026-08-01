#!/usr/bin/env python3
"""
login_terminal.py
Script standalone untuk login akun Facebook baru via terminal di komputer LOKAL.

Gunakan script ini di komputer lokal Anda (Windows/Mac/Linux desktop) untuk:
1. Login akun Facebook baru → cookie tersimpan ke session/fb_session_*.json
2. Relogin akun yang sudah ada → refresh cookie yang expired

Setelah login, copy file sesi JSON ke folder session/ di server otomasi.

Cara pakai:
  python3 login_terminal.py              # Menu interaktif
  python3 login_terminal.py --new        # Langsung login akun baru
  python3 login_terminal.py --relogin session/fb_session_xxx.json  # Relogin akun existing

Prasyarat:
  pip install playwright
  playwright install chromium
"""
import sys
import os
import asyncio

# Tambahkan direktori script ke path agar import module bekerja
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import config
from manager.session_manager import (
    interactive_login_new_account,
    relogin_existing_account,
    discover_all_sessions,
    get_session_info,
)


def print_banner():
    """Tampilkan banner."""
    print("""
=================================================================
   🔑 FB AUTOENGINE 3.0 - LOGIN TERMINAL (LOKAL)
      Login akun Facebook via browser GUI di komputer Anda
=================================================================
""")


def print_menu():
    """Tampilkan menu utama."""
    print("\n📋 MENU:")
    print("   [1] ➕ Login Akun Baru")
    print("   [2] 🔄 Relogin Akun Existing (Refresh Cookie)")
    print("   [3] 📋 Lihat Daftar Sesi Tersimpan")
    print("   [0] ❌ Keluar")
    print("   ---------------------------------------------------")


def list_sessions():
    """Tampilkan daftar sesi tersimpan."""
    sessions = discover_all_sessions()
    if not sessions:
        print("\n   ⚠️ Belum ada sesi tersimpan.")
        return []
    print("\n📋 DAFTAR SESI TERSIMPAN:")
    for idx, s in enumerate(sessions, 1):
        print(f"   [{idx}] 👤 {s.get('name', 'Akun')} (ID: {s.get('c_user', '?')})")
        print(f"       Path: {s.get('path', '')}")
    return sessions


def check_environment():
    """Cek apakah environment mendukung browser GUI."""
    # Windows selalu support GUI
    if sys.platform == "win32":
        print("✅ Environment: Windows (browser GUI tersedia)")
        return True
    # Linux/Mac: cek DISPLAY
    if os.environ.get("DISPLAY"):
        print(f"✅ Environment: Linux/Mac (DISPLAY={os.environ['DISPLAY']})")
        return True
    print("❌ Environment: Headless server (tidak ada display)")
    print("   Script ini harus dijalankan di komputer LOKAL dengan monitor.")
    print("   Untuk server remote, gunakan Import Sesi JSON via web dashboard.")
    return False


async def login_new():
    """Login akun baru."""
    print("\n➕ LOGIN AKUN BARU")
    print("   Browser Chromium akan terbuka. Silakan login ke Facebook di browser tersebut.")
    print("   Setelah login berhasil, cookie akan otomatis tersimpan.")
    print()

    tag = input("   Masukkan nama panggil akun ini (cth: Akun_Utama): ").strip()
    if not tag:
        tag = f"akun_{int(asyncio.get_event_loop().time())}"

    result_path = await interactive_login_new_account(account_tag=tag)

    if result_path and os.path.exists(result_path):
        print(f"\n🎉 Login BERHASIL!")
        print(f"   File sesi tersimpan: {result_path}")
        print(f"\n📋 LANGKAH SELANJUTNYA:")
        print(f"   1. Copy file {os.path.basename(result_path)} ke folder session/ di server otomasi")
        print(f"   2. Atau push ke git: git add {result_path} && git commit && git push")
        print(f"   3. Restart server otomasi atau refresh dashboard web")
    else:
        print("\n❌ Login gagal atau dibatalkan.")


async def relogin_existing():
    """Relogin akun yang sudah ada."""
    sessions = list_sessions()
    if not sessions:
        return

    print("\n🔄 RELOGIN AKUN EXISTING")
    sel = input("👉 Pilih nomor akun [1..N] (0 Batal): ").strip()
    if not sel.isdigit() or int(sel) == 0:
        print("   Dibatalkan.")
        return
    idx = int(sel) - 1
    if idx < 0 or idx >= len(sessions):
        print("   ❌ Nomor tidak valid.")
        return

    target = sessions[idx]
    print(f"\n   Target: {target.get('name', 'Akun')}")
    print(f"   Path: {target.get('path', '')}")
    print(f"   Browser akan terbuka. Login ulang ke akun ini di browser.\n")

    ok = await relogin_existing_account(target["path"])
    if ok:
        print(f"\n🎉 Relogin BERHASIL!")
        print(f"   File sesi diperbarui: {target.get('path', '')}")
        print(f"\n📋 LANGKAH SELANJUTNYA:")
        print(f"   1. Copy file {os.path.basename(target.get('path', ''))} ke server otomasi")
        print(f"   2. Atau push ke git: git add {target.get('path', '')} && git commit && git push")
    else:
        print("\n❌ Relogin gagal atau dibatalkan.")


async def main():
    """Entry point utama."""
    print_banner()

    # Parse argumen CLI
    if len(sys.argv) > 1:
        if sys.argv[1] == "--new":
            if not check_environment():
                return
            await login_new()
            return
        elif sys.argv[1] == "--relogin" and len(sys.argv) > 2:
            if not check_environment():
                return
            session_path = sys.argv[2]
            if not os.path.exists(session_path):
                print(f"❌ File tidak ditemukan: {session_path}")
                return
            ok = await relogin_existing_account(session_path)
            if ok:
                print(f"\n🎉 Relogin BERHASIL! File diperbarui: {session_path}")
            else:
                print("\n❌ Relogin gagal.")
            return
        elif sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return

    # Mode interaktif
    if not check_environment():
        print("\n💡 Untuk server remote, gunakan web dashboard → tombol 'Import Sesi'")
        return

    while True:
        print_menu()
        choice = input("👉 Pilih menu [0..3]: ").strip()

        if choice == "0":
            print("\n👋 Keluar. Sampai jumpa!")
            break
        elif choice == "1":
            await login_new()
        elif choice == "2":
            await relogin_existing()
        elif choice == "3":
            list_sessions()
        else:
            print("   ❌ Pilihan tidak valid.")

        if choice in ["1", "2", "3"]:
            input("\nTekan Enter untuk kembali ke menu...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⛔ Dibatalkan oleh pengguna (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
