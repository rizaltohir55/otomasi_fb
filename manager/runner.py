"""
manager/runner.py
Orkestrator Pengisi Daya Worker Single-Process & Multi-Process Paralel.
FB AutoEngine 3.0 Ultra - Real Stealth & High-Performance Multi-Account Engine.
"""
import sys
import os
import time
import random
import asyncio
import multiprocessing
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright

import config
from utils.helpers import log
from utils.browser import random_human_delay, safe_goto
from utils.monitor import live_monitor
from engine.browser import (
    create_stealth_context,
    save_session_state,
    verify_login_status,
    generate_deterministic_profile,
)
from engine.collector import load_caption, find_media_images
from engine.composer import execute_post_to_group
from engine.joiner import execute_join_group, check_membership_status
from engine.commenter import execute_auto_comment_on_group


def fix_windows_stdout_encoding():
    """Atur encoding konsol Windows agar mendukung karakter Unicode emoji dan simbol."""
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


async def worker_loop(
    session_file: str,
    groups: List[str],
    mode: str,
    worker_tag: str = "Worker",
    headless: bool = False,
    randomize_groups: bool = True,
    status_queue: Optional[multiprocessing.Queue] = None
) -> Dict[str, Any]:
    """
    Worker Loop Asinkron Utama yang mengeksekusi grup per grup untuk 1 akun.
    - mode 1: Auto Post
    - mode 2: Auto Join
    - mode 3: Auto Post + Auto Join (Join otomatis jika belum terdaftar)
    """
    start_time = time.time()
    profile = generate_deterministic_profile(session_file)
    account_name = profile.get("account_name", os.path.basename(session_file))
    spoof_info = f"{profile.get('renderer')} | {profile.get('viewport', {}).get('width')}x{profile.get('viewport', {}).get('height')}"

    log(f"🚀 Worker [{worker_tag}] dimulai | File Sesi: {os.path.basename(session_file)}")
    log(
        f"🛡️ Hardware Spoof: GPU [{profile.get('renderer')}] | "
        f"CPU [{profile.get('cores')} Core] | RAM [{profile.get('memory')}GB] | "
        f"Resolution [{profile.get('viewport', {}).get('width')}x{profile.get('viewport', {}).get('height')}]",
        worker_tag
    )

    caption = load_caption()
    media_images = find_media_images()

    worker_groups = list(groups)
    if randomize_groups:
        random.shuffle(worker_groups)
        log(f"🔀 Urutan posting grup DIAKAK (randomized) untuk [{worker_tag}].", worker_tag)
    else:
        log(f"📋 Urutan posting grup BERURUTAN (sequential) untuk [{worker_tag}].", worker_tag)

    success_count = 0
    fail_count = 0
    worker_status = "SELESAI"

    def notify_status(
        status: str,
        current_group: str = "",
        current_idx: int = 0,
        step_msg: str = "",
        delay_sec: float = 0.0
    ):
        try:
            live_monitor.update_worker(
                worker_tag=worker_tag,
                account_name=account_name,
                session_file=session_file,
                status=status,
                current_group=current_group,
                current_idx=current_idx,
                total_groups=len(worker_groups),
                success_count=success_count,
                fail_count=fail_count,
                step_msg=step_msg,
                spoof_info=spoof_info,
                delay_sec=delay_sec
            )
        except Exception:
            pass

        if status_queue:
            try:
                status_queue.put_nowait({
                    "action": "UPDATE_WORKER",
                    "worker_tag": worker_tag,
                    "account_name": account_name,
                    "session_file": session_file,
                    "status": status,
                    "current_group": current_group,
                    "current_idx": current_idx,
                    "total_groups": len(worker_groups),
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "step_msg": step_msg,
                    "spoof_info": spoof_info,
                    "delay_sec": delay_sec
                })
            except Exception:
                pass

    notify_status("INITIALIZING", step_msg="Menyiapkan browser context...")

    async with async_playwright() as p:
        try:
            browser, context = await create_stealth_context(p, session_file=session_file, headless=headless)
            page = await context.new_page()
        except Exception as e:
            log(f"❌ Gagal menginisialisasi browser context untuk [{worker_tag}]: {e}", worker_tag)
            notify_status("FAILED", step_msg=f"Gagal inisialisasi browser: {e}")
            return {
                "session_file": session_file,
                "worker_tag": worker_tag,
                "account_name": account_name,
                "status": "ERROR_INIT",
                "success_count": 0,
                "fail_count": len(worker_groups),
                "total_groups": len(worker_groups),
                "duration_sec": round(time.time() - start_time, 1),
                "spoof_info": spoof_info
            }

        # Verifikasi Login awal
        notify_status("CHECKING_LOGIN", step_msg="Memeriksa status cookie Facebook...")
        try:
            await safe_goto(page, "https://www.facebook.com/", timeout_ms=20000)
        except Exception as e:
            log(f"⚠️ Navigasi awal Facebook berhalangan: {e}", worker_tag)

        is_logged_in = await verify_login_status(page)
        if not is_logged_in:
            log(f"❌ Worker [{worker_tag}] GAGAL LOGIN. Cookie sesi kedaluwarsa atau ter-checkpoint.", worker_tag)
            notify_status("EXPIRED", step_msg="Sesi cookie kedaluwarsa/checkpoint")
            await browser.close()
            return {
                "session_file": session_file,
                "worker_tag": worker_tag,
                "account_name": account_name,
                "status": "EXPIRED",
                "success_count": 0,
                "fail_count": len(worker_groups),
                "total_groups": len(worker_groups),
                "duration_sec": round(time.time() - start_time, 1),
                "spoof_info": spoof_info
            }

        log(f"✅ Sesi terverifikasi aktif. Memulai pemrosesan {len(worker_groups)} grup...", worker_tag)

        for idx, group_url in enumerate(worker_groups, 1):
            log(f"\n[{worker_tag}] [{idx}/{len(worker_groups)}] Memproses grup: {group_url}")
            notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Memproses grup [{idx}/{len(worker_groups)}]")

            try:
                if mode in ["1", "3"]:
                    # Mode 1 & 3: Auto Post / Auto Post + Auto Join
                    mem_status = await check_membership_status(page, group_url, worker_tag=worker_tag)

                    if mem_status == "RESTRICTED":
                        log(f"   ⛔ AKUN DIBATASI FACEBOOK: Menghentikan worker [{worker_tag}] agar akun aman.", worker_tag)
                        fail_count += (len(worker_groups) - idx + 1)
                        worker_status = "RESTRICTED"
                        notify_status("RESTRICTED", current_group=group_url, current_idx=idx, step_msg="Akun dibatasi FB (Restricted)")
                        break

                    if mem_status == "UNKNOWN":
                        await page.wait_for_timeout(2000)
                        mem_status = await check_membership_status(page, group_url, worker_tag=worker_tag)

                    if mem_status == "NOT_LOGGED_IN":
                        log(f"   ❌ Sesi login terputus / kedaluwarsa pada grup {group_url}.", worker_tag)
                        log(f"   ⚠️ Menghentikan eksekusi worker [{worker_tag}] karena akun butuh login ulang.", worker_tag)
                        fail_count += (len(worker_groups) - idx + 1)
                        worker_status = "EXPIRED"
                        notify_status("EXPIRED", current_group=group_url, current_idx=idx, step_msg="Sesi login terputus saat eksekusi")
                        break

                    if mem_status in ["NOT_JOINED", "UNKNOWN"]:
                        log(f"   ℹ️ Terdeteksi belum bergabung (Status: {mem_status}). Menjalankan proses Gabung Grup...", worker_tag)
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Mengirim permintaan Gabung Grup...")
                        join_ok = await execute_join_group(page, group_url, worker_tag=worker_tag)
                        if not join_ok:
                            log(f"   ⚠️ Gagal bergabung ke grup. Postingan dibatalkan.", worker_tag)
                            fail_count += 1
                            notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Gagal gabung grup")
                            continue
                        await random_human_delay(2.0, 3.0)
                        mem_status = await check_membership_status(page, group_url, worker_tag=worker_tag)

                    if mem_status == "PENDING":
                        log(f"   ⏳ Permintaan bergabung dikirim & PENDING (Menunggu Persetujuan Admin). Post dibatalkan.", worker_tag)
                        fail_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Status bergabung Pending Admin")
                        continue

                    if mem_status != "JOINED":
                        log(f"   ⚠️ Status keanggotaan belum JOINED (Status akhir: {mem_status}). Post dibatalkan.", worker_tag)
                        fail_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Bukan anggota grup ({mem_status})")
                        continue

                    notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Menulis caption & mengunggah postingan...")
                    ok = await execute_post_to_group(page, group_url, caption, media_images, worker_tag=worker_tag)
                    if ok:
                        success_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Postingan berhasil dikirim!")
                        await execute_auto_comment_on_group(page, group_url)
                    else:
                        fail_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Gagal membuat postingan")

                elif mode == "2":
                    # Mode 2: Auto Join Saja
                    if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                        log(f"   ❌ Sesi login terputus / kedaluwarsa pada grup {group_url}.", worker_tag)
                        log(f"   ⚠️ Menghentikan eksekusi worker [{worker_tag}] karena akun mebutuhkan login ulang.", worker_tag)
                        fail_count += (len(worker_groups) - idx + 1)
                        worker_status = "EXPIRED"
                        notify_status("EXPIRED", current_group=group_url, current_idx=idx, step_msg="Sesi login terputus")
                        break
                    
                    notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Menjalankan Auto Join Grup...")
                    ok = await execute_join_group(page, group_url, worker_tag=worker_tag)
                    if ok:
                        success_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Berhasil kirim bergabung!")
                    else:
                        fail_count += 1
                        notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Gagal bergabung grup")

            except Exception as e:
                log(f"❌ Error pada grup {group_url}: {e}", worker_tag)
                fail_count += 1
                notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Error: {e}")

            if idx < len(worker_groups):
                delay = random.uniform(config.DELAY_BETWEEN_GROUPS_MIN, config.DELAY_BETWEEN_GROUPS_MAX)
                log(f"⏳ Jeda emulasi manusia {delay:.1f} detik...", worker_tag)
                notify_status("WAITING_DELAY", current_group=group_url, current_idx=idx, step_msg=f"Jeda manusia {delay:.1f}s", delay_sec=delay)
                await asyncio.sleep(delay)

        await save_session_state(context, session_file)
        await browser.close()

        duration = round(time.time() - start_time, 1)
        log(f"\n=======================================================", worker_tag)
        log(f"🎉 Worker [{worker_tag}] SELESAI ({duration} detik)", worker_tag)
        log(f"📊 Hasil: {success_count} Sukses | {fail_count} Gagal | Total {len(worker_groups)} Grup", worker_tag)
        log(f"=======================================================", worker_tag)

        notify_status("COMPLETED", current_idx=len(worker_groups), step_msg=f"Worker Selesai ({success_count} Sukses, {fail_count} Gagal)")

        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": worker_status,
            "success_count": success_count,
            "fail_count": fail_count,
            "total_groups": len(worker_groups),
            "duration_sec": duration,
            "spoof_info": spoof_info
        }


def _multiprocess_entry_point(
    session_file: str,
    groups: List[str],
    mode: str,
    worker_tag: str,
    headless: bool,
    randomize_groups: bool,
    result_queue: multiprocessing.Queue,
    status_queue: Optional[multiprocessing.Queue] = None
):
    """Entry point isolated per proses worker paralel."""
    fix_windows_stdout_encoding()
    try:
        res = asyncio.run(worker_loop(session_file, groups, mode, worker_tag, headless, randomize_groups, status_queue=status_queue))
        result_queue.put(res)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"❌ Error fatal pada proses worker [{worker_tag}]: {e}", worker_tag)
        result_queue.put({
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": worker_tag,
            "status": "FATAL_ERROR",
            "success_count": 0,
            "fail_count": len(groups),
            "total_groups": len(groups),
            "duration_sec": 0,
            "spoof_info": "N/A"
        })


def run_worker_entry(
    session_file: str,
    groups: List[str],
    mode: str,
    worker_tag: str = "Worker",
    headless: bool = True,
    randomize_groups: bool = True
):
    """Jalankan worker tunggal di dalam event loop utama."""
    fix_windows_stdout_encoding()
    live_monitor.reset(total_accounts=1, total_groups_target=len(groups), mode=mode)
    try:
        res = asyncio.run(worker_loop(session_file, groups, mode, worker_tag, headless, randomize_groups))
        live_monitor.mark_completed("Selesai")
        return res
    except Exception as e:
        live_monitor.mark_completed(f"Gagal: {e}")
        raise e


def print_multi_account_summary(results: List[Dict[str, Any]], total_duration_sec: float):
    """Cetak tabel rekapitulasi performa multi-akun yang rapi dan elegan."""
    print("\n" + "=" * 90)
    print("📊 REKAPITULASI HASIL EKSEKUSI MULTI-AKUN (FB AUTOENGINE 3.0 ULTRA)")
    print("=" * 90)
    header = f"{'NO':<4} {'NAMA AKUN':<22} {'STATUS':<12} {'SUKSES':<8} {'GAGAL':<8} {'HARDWARE SPOOFED GPU / RES'}"
    print(header)
    print("-" * 90)

    total_success = 0
    total_fail = 0

    for idx, r in enumerate(results, 1):
        name = str(r.get("account_name", "Unknown"))[:20]
        status = r.get("status", "N/A")
        status_icon = "✅ SELESAI" if status in ["SELESAI", "COMPLETED"] else ("❌ " + status)
        succ = r.get("success_count", 0)
        fail = r.get("fail_count", 0)
        spoof = str(r.get("spoof_info", "N/A"))

        total_success += succ
        total_fail += fail

        row = f"{idx:<4} {name:<22} {status_icon:<12} {succ:<8} {fail:<8} {spoof}"
        print(row)

    print("=" * 90)
    mins = int(total_duration_sec // 60)
    secs = int(total_duration_sec % 60)
    dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    print(f"⏱️ Total Waktu: {dur_str} | Total Post Sukses: {total_success} | Total Gagal: {total_fail} | Akun Diproses: {len(results)}")
    print("=" * 90 + "\n")


def launch_multiprocess_runner(
    session_files: Optional[List[str]] = None,
    groups: Optional[List[str]] = None,
    mode: str = "1",
    max_workers: Optional[int] = None,
    headless: bool = True,
    randomize_groups: bool = True,
    selected_sessions: Optional[List[str]] = None
):
    """
    Luncurkan seluruh worker multi-akun secara terkontrol menggunakan Worker Concurrency Pool & Stagger Delay.
    """
    targets = session_files or selected_sessions or []
    groups_list = groups or []
    start_total_time = time.time()
    effective_max_workers = max_workers or config.MAX_CONCURRENT_WORKERS
    effective_max_workers = max(1, min(effective_max_workers, len(targets)))
    
    total_groups_target = len(targets) * len(groups_list)
    live_monitor.reset(total_accounts=len(targets), total_groups_target=total_groups_target, mode=mode)

    log(f"\n=======================================================")
    log(f"⚡ MENJALANKAN {len(targets)} AKUN (PARALEL CONCURRENCY POOL)")
    log(f"⚙️ Worker Paralel Maksimal: {effective_max_workers} Akun Bersamaan (Stagger Delay: {config.WORKER_STAGGER_DELAY_SEC}s)")
    log(f"⚙️ Mode Browser: {'Headless (Stealth / Hemat CPU & RAM)' if headless else 'GUI Mode (Tampilan Chrome)'}")
    log(f"🛡️ Fingerprint Spoofing: AKTIF (User-Agent, Viewport, WebGL GPU, Client Hints & Canvas Noise)")
    log(f"=======================================================")

    result_queue = multiprocessing.Queue()
    status_queue = multiprocessing.Queue()

    pending_sessions = list(enumerate(targets, 1))
    active_processes = []
    results = []

    def drain_status():
        while not status_queue.empty():
            try:
                smsg = status_queue.get_nowait()
                if smsg.get("action") == "UPDATE_WORKER":
                    live_monitor.update_worker(
                        worker_tag=smsg["worker_tag"],
                        account_name=smsg["account_name"],
                        session_file=smsg["session_file"],
                        status=smsg["status"],
                        current_group=smsg.get("current_group", ""),
                        current_idx=smsg.get("current_idx", 0),
                        total_groups=smsg.get("total_groups", 0),
                        success_count=smsg.get("success_count", 0),
                        fail_count=smsg.get("fail_count", 0),
                        step_msg=smsg.get("step_msg", ""),
                        spoof_info=smsg.get("spoof_info", ""),
                        delay_sec=smsg.get("delay_sec", 0.0)
                    )
            except Exception:
                break

    def sleep_and_drain(sec: float):
        end_t = time.time() + sec
        while time.time() < end_t:
            drain_status()
            time.sleep(0.1)

    try:
        while pending_sessions or active_processes:
            # Luncurkan worker baru jika slot active_processes < effective_max_workers
            while pending_sessions and len(active_processes) < effective_max_workers:
                idx, s_file = pending_sessions.pop(0)
                profile = generate_deterministic_profile(s_file)
                sess_name = profile.get("account_name", os.path.basename(s_file))
                tag = f"Akun-{idx} ({sess_name})"

                p = multiprocessing.Process(
                    target=_multiprocess_entry_point,
                    args=(s_file, groups_list, mode, tag, headless, randomize_groups, result_queue, status_queue)
                )
                p.start()
                active_processes.append(p)
                log(f"🚀 Memulai worker [{tag}] (Active Workers: {len(active_processes)}/{effective_max_workers})...")

                if pending_sessions and config.WORKER_STAGGER_DELAY_SEC > 0:
                    sleep_and_drain(config.WORKER_STAGGER_DELAY_SEC)

            # Cek & kurangi isi status_queue untuk pembaruan live_monitor
            drain_status()
            sleep_and_drain(0.4)
            
            still_active = []
            for p in active_processes:
                if p.is_alive():
                    still_active.append(p)
                else:
                    p.join()
            active_processes = still_active

            # Kumpulkan hasil dari result_queue
            while not result_queue.empty():
                try:
                    res = result_queue.get_nowait()
                    results.append(res)
                except Exception:
                    break

    except KeyboardInterrupt:
        log("\n⛔ Pembatalan oleh pengguna (Ctrl+C)! Menghentikan seluruh worker paralel...")
        for p in active_processes:
            if p.is_alive():
                p.terminate()
        log("✅ Seluruh child process telah dihentikan secara bersih.")
        live_monitor.mark_completed("Dibatalkan pengguna")

    # Kumpulkan sisa hasil
    while not result_queue.empty():
        try:
            res = result_queue.get_nowait()
            results.append(res)
        except Exception:
            break

    total_dur = round(time.time() - start_total_time, 1)
    live_monitor.mark_completed("Selesai")

    if results:
        print_multi_account_summary(results, total_dur)
    else:
        log("\n🎉 Eksekusi multi-akun selesai.")
