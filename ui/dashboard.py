"""
ui/dashboard.py
Antarmuka Terminal Dashboard CLI Interaktif FB AutoEngine 3.0 Ultra.
Mendukung Menu Utama & Sub-menu Manajemen Akun (CRUD: Create, Read, Update, Delete).
"""
import os
import time
import asyncio
from typing import List, Dict, Optional

import config

from manager.session_manager import (
    discover_all_sessions,
    interactive_login_new_account,
    relogin_existing_account,
    update_session_name,
    delete_session_file,
    import_session_file,
    verify_session_live_status,
)


def print_banner():
    """Tampilkan banner header CLI yang modern dan elegan."""
    banner = """
=================================================================
   🌐 FB AUTOENGINE 3.0 ULTRA - AUTOMATION ENGINE
      (Pure Desktop React ARIA Engine & Intelligent Stealth) 
=================================================================
"""
    print(banner)


def parse_account_indices(input_str: str, max_idx: int) -> List[int]:
    """
    Parse string input seperti '1, 3, 5' atau '1-3' atau '1, 3-5' menjadi list integer 0-based.
    """
    selected_indices = set()
    parts = [p.strip() for p in input_str.replace(" ", "").split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start, end = int(sub[0]), int(sub[1])
                for i in range(min(start, end), max(start, end) + 1):
                    if 1 <= i <= max_idx:
                        selected_indices.add(i - 1)
        elif part.isdigit():
            i = int(part)
            if 1 <= i <= max_idx:
                selected_indices.add(i - 1)
    return sorted(list(selected_indices))


def display_account_menu(sessions: List[Dict[str, str]]) -> List[str]:
    """
    Tampilkan menu pemilih akun Facebook dari file sesi yang ditemukan,
    serta opsi Manajemen Akun CRUD.
    """
    while True:
        sessions = discover_all_sessions()
        print("\n🔑 PILIH AKUN FACEBOOK:")
        if not sessions:
            print("   ⚠️ Belum ada file sesi tersimpan.")
        else:
            for idx, s in enumerate(sessions, 1):
                c_user = s.get("c_user", "Unknown")
                name   = s.get("name", "Akun Facebook")
                fname  = s.get("path", "")
                print(f"   [{idx}] 👤 {name} (ID: {c_user}) -> {fname}")

        opt_multi = len(sessions) + 1
        opt_all   = len(sessions) + 2
        opt_add   = len(sessions) + 3
        opt_crud  = len(sessions) + 4

        print(f"   [{opt_multi}] 🎯 PILIH BEBERAPA AKUN TERTENTU (MULTI-SELECT / CUSTOM)")
        print(f"   [{opt_all}] ⚡ JALANKAN SEMUA AKUN PARALEL (MULTI-PROCESS)")
        print(f"   [{opt_add}] ➕ Tambah / Login Akun Baru")
        print(f"   [{opt_crud}] ⚙️  MANAJEMEN AKUN (CRUD: Edit, Hapus, Relogin, Import)")
        print("   ---------------------------------------------------")

        try:
            choice = input("👉 Pilih nomor opsi [1..N] (atau ketik beberapa nomor cth: 1,3 atau 1-3): ").strip()
            if not choice:
                continue

            # 1. Cek jika pengguna memasukkan format multi-select langsung (misal: "1,3" atau "1-3")
            if ("," in choice or "-" in choice) and len(sessions) > 0:
                indices = parse_account_indices(choice, len(sessions))
                if indices:
                    selected_paths = [sessions[i]["path"] for i in indices]
                    names = ", ".join([sessions[i].get("name", "Akun") for i in indices])
                    print(f"👉 Memilih {len(selected_paths)} akun: {names}")
                    return selected_paths

            # 2. Cek jika berupa angka tunggal
            if choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(sessions):
                    selected = sessions[val - 1]["path"]
                    print(f"👉 Memilih akun: {sessions[val - 1].get('name')}")
                    return [selected]
                elif val == opt_multi:
                    print("\n🎯 PILIH BEBERAPA AKUN MANDIRI:")
                    multi_input = input("👉 Masukkan nomor-nomor akun (pisahkan koma/strip, cth: 1,3,5 atau 1-3): ").strip()
                    indices = parse_account_indices(multi_input, len(sessions))
                    if not indices:
                        print("❌ Nomor akun tidak valid.")
                        continue
                    selected_paths = [sessions[i]["path"] for i in indices]
                    names = ", ".join([sessions[i].get("name", "Akun") for i in indices])
                    print(f"👉 Memilih {len(selected_paths)} akun terpilih: {names}")
                    
                    if len(selected_paths) > 1:
                        w_in = input(f"⚡ Batas worker paralel bersamaan [1-{len(selected_paths)}, Default {config.MAX_CONCURRENT_WORKERS}]: ").strip()
                        if w_in.isdigit() and int(w_in) > 0:
                            config.MAX_CONCURRENT_WORKERS = int(w_in)
                    return selected_paths
                elif val == opt_all:
                    print(f"👉 Memilih seluruh {len(sessions)} akun tersimpan untuk eksekusi paralel!")
                    if len(sessions) > 1:
                        w_in = input(f"⚡ Batas worker paralel bersamaan [1-{len(sessions)}, Default {config.MAX_CONCURRENT_WORKERS}]: ").strip()
                        if w_in.isdigit() and int(w_in) > 0:
                            config.MAX_CONCURRENT_WORKERS = int(w_in)
                    return [s["path"] for s in sessions]
                elif val == opt_add:
                    return ["NEW_ACCOUNT"]
                elif val == opt_crud:
                    run_account_crud_sub_menu()
        except (ValueError, KeyboardInterrupt):
            return []



def run_account_crud_sub_menu():
    """
    Submenu Manajemen Akun Interaktif (CRUD: Create, Read, Update, Delete).
    """
    while True:
        sessions = discover_all_sessions()
        print("\n" + "=" * 65)
        print("⚙️  MANAJEMEN AKUN FACEBOOK (CRUD)")
        print("=" * 65)
        print("   [1] 📋 [READ] Lihat Detail Sesi Akun & Test Status Cookie")
        print("   [2] ➕ [CREATE] Tambah / Login Akun Baru (Browser GUI)")
        print("   [3] 📥 [CREATE] Import File Sesi JSON Kustom")
        print("   [4] ✍️  [UPDATE] Edit / Ubah Nama Panggil Akun")
        print("   [5] 🔄 [UPDATE] Login Ulang / Refresh Sesi Cookie Akun")
        print("   [6] 🗑️  [DELETE] Hapus / Buang Sesi Akun")
        print("   [0] 🔙 Kembali ke Menu Utama")
        print("   ---------------------------------------------------")

        choice = input("👉 Pilih menu manajemen [0..6]: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            # READ
            print("\n📋 DAFTAR SESI TERSIMPAN:")
            if not sessions:
                print("   ⚠️ Belum ada file sesi tersimpan.")
            else:
                for idx, s in enumerate(sessions, 1):
                    file_size = 0
                    mod_time = "N/A"
                    if os.path.exists(s["path"]):
                        st = os.stat(s["path"])
                        file_size = round(st.st_size / 1024, 1)
                        mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                    print(f"   [{idx}] 👤 {s.get('name')} | ID: {s.get('c_user')} | Ukuran: {file_size} KB | Edit: {mod_time}")
                    print(f"       Path: {s.get('path')}")

                test_live = input("\n🔍 Ingin menguji status LIVE akun ke Facebook secara langsung? [y/N]: ").strip().lower()
                if test_live == "y":
                    print("⌛ Menguji status sesi akun ke Facebook...")
                    for s in sessions:
                        res = asyncio.run(verify_session_live_status(s["path"]))
                        icon = "✅" if res["status"] == "ACTIVE" else "❌"
                        print(f"   {icon} [{res['name']}] Status: {res['status']} ({res['message']})")

            input("\nTekan Enter untuk kembali...")

        elif choice == "2":
            # CREATE - NEW LOGIN
            asyncio.run(interactive_login_new_account())
            input("\nTekan Enter untuk kembali...")

        elif choice == "3":
            # CREATE - IMPORT
            print("\n📥 IMPORT FILE SESI JSON:")
            src = input("👉 Masukkan path file JSON (cth: D:\\my_session.json): ").strip()
            if src:
                tag = input("👉 Masukkan nama panggil akun: ").strip()
                import_session_file(src, tag)
            input("\nTekan Enter untuk kembali...")

        elif choice == "4":
            # UPDATE - RENAME
            if not sessions:
                print("⚠️ Tidak ada sesi untuk diubah.")
                continue
            print("\n✍️ PILIH AKUN YANG INGIN DIUBAH NAMANYA:")
            for idx, s in enumerate(sessions, 1):
                print(f"   [{idx}] 👤 {s.get('name')} (ID: {s.get('c_user')})")
            
            sel = input("\n👉 Pilih nomor akun [1..N] (0 Batal): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(sessions):
                target = sessions[int(sel) - 1]
                new_n = input(f"👉 Masukkan nama baru untuk '{target.get('name')}': ").strip()
                if new_n:
                    if update_session_name(target["path"], new_n):
                        print(f"✅ Nama akun berhasil diubah menjadi: {new_n}")
            input("\nTekan Enter untuk kembali...")

        elif choice == "5":
            # UPDATE - RELOGIN
            if not sessions:
                print("⚠️ Tidak ada sesi untuk di-login ulang.")
                continue
            print("\n🔄 PILIH AKUN YANG INGIN DI-LOGIN ULANG:")
            for idx, s in enumerate(sessions, 1):
                print(f"   [{idx}] 👤 {s.get('name')} (ID: {s.get('c_user')})")
            
            sel = input("\n👉 Pilih nomor akun [1..N] (0 Batal): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(sessions):
                target = sessions[int(sel) - 1]
                asyncio.run(relogin_existing_account(target["path"]))
            input("\nTekan Enter untuk kembali...")

        elif choice == "6":
            # DELETE
            if not sessions:
                print("⚠️ Tidak ada sesi untuk dihapus.")
                continue
            print("\n🗑️ PILIH AKUN YANG INGIN DIHAPUS:")
            for idx, s in enumerate(sessions, 1):
                print(f"   [{idx}] 👤 {s.get('name')} (ID: {s.get('c_user')}) -> {s.get('path')}")
            
            sel = input("\n👉 Pilih nomor akun [1..N] (0 Batal): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(sessions):
                target = sessions[int(sel) - 1]
                confirm = input(f"⚠️ Yakin ingin menghapus sesi '{target.get('name')}'? [y/N]: ").strip().lower()
                if confirm == "y":
                    perm = input("   Metode: [1] Pindahkan ke Backup (.bak) [2] Hapus Permanen. Pilih [1/2]: ").strip()
                    delete_session_file(target["path"], permanent=(perm == "2"))
            input("\nTekan Enter untuk kembali...")


def display_mode_menu() -> str:
    """
    Tampilkan menu pemilih mode operasi otomasi.
    """
    print("\n📋 PILIH MODE OPERASI:")
    print("   [1] 🚀 Auto Post Ke Daftar Grup")
    print("   [2] ➕ Auto Join Semua Daftar Grup")
    print("   [3] ⚡ Auto Post + Auto Join (Join otomatis jika belum terdaftar)")
    print("   ---------------------------------------------------")

    while True:
        choice = input("👉 Pilih mode [1/2/3]: ").strip()
        if choice in ["1", "2", "3"]:
            mode_names = {
                "1": "Auto Post",
                "2": "Auto Join",
                "3": "Auto Post + Auto Join",
            }
            print(f"⚙️ Mode terpilih: [{choice}] {mode_names[choice]}")
            return choice


def display_headless_menu(default_headless: bool = True) -> bool:
    """
    Tampilkan menu pemilih mode browser (Headless vs GUI).
    """
    print("\n🖥️  PILIH MODE BROWSER DISPLAY:")
    print("   [1] 👻 Headless Mode (Tanpa Tampilan GUI - Ringan & Cepat) [Direkomendasikan]")
    print("   [2] 🖥️  GUI Mode (Tampilkan Jendela Browser Chrome)")
    print("   ---------------------------------------------------")

    default_str = "1" if default_headless else "2"
    while True:
        try:
            choice = input(f"👉 Pilih mode display [1/2] (Default: {default_str}): ").strip()
            if not choice:
                choice = default_str
            if choice == "2":
                print("⚙️ Display Mode: GUI Mode (Jendela Browser Terbuka)")
                return False
            elif choice == "1":
                print("⚙️ Display Mode: Headless Mode (Tanpa Tampilan GUI / Ringan & Hemat RAM)")
                return True
        except (KeyboardInterrupt, EOFError):
            return default_headless
