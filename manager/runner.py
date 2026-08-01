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
from utils.retry import (
    safe_browser_cleanup,
    restriction_cooldown,
    group_skip_list,
    get_global_cancel_token,
    reset_global_cancel,
)
from utils.helpers import acquire_account_lock, release_account_lock
from engine.browser import (
    create_stealth_context,
    save_session_state,
    verify_login_status,
    generate_deterministic_profile,
    get_session_info,
    handle_profile_selector_page,
)
from engine.collector import load_caption, find_media_images
from engine.composer import execute_post_to_group
from engine.joiner import execute_join_group, check_membership_status
from engine.commenter import execute_auto_comment_on_group


# ── Mode constants ─────────────────────────────────────────────────────────────
VALID_MODES = {"1", "2", "3"}
MODE_TEXT = {
    "1": "Auto Post ke Grup",
    "2": "Auto Join Grup",
    "3": "Auto Post + Auto Join",
}


def fix_windows_stdout_encoding():
    """Atur encoding konsol Windows agar mendukung karakter Unicode emoji dan simbol."""
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def validate_mode(mode: str) -> str:
    """Validasi mode input. Return mode jika valid, raise ValueError jika tidak."""
    mode_str = str(mode).strip()
    if mode_str not in VALID_MODES:
        raise ValueError(f"Mode tidak valid: '{mode}'. Mode yang didukung: {sorted(VALID_MODES)} ({MODE_TEXT})")
    return mode_str


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
    # Deduplikasi grup dalam sesi ini (jaga-jaga kalau ada duplikat dari caller)
    seen_in_session = set()
    deduped_groups = []
    for g in worker_groups:
        if g not in seen_in_session:
            seen_in_session.add(g)
            deduped_groups.append(g)
    if len(deduped_groups) < len(worker_groups):
        log(f"🧹 {len(worker_groups) - len(deduped_groups)} grup duplikat dihapus dalam sesi ini.", worker_tag)
    worker_groups = deduped_groups

    # ── Session progress tracking: skip grup yang sudah diproses dalam 1 jam terakhir ──
    # Cegah duplikasi posting saat user klik Start berkali-kali.
    # File: data/session_progress_{c_user}.json
    # Format: { "url": timestamp } — entri >1 jam dianggap expired & dihapus.
    progress_file = os.path.join(config.DATA_DIR, f"session_progress_{c_user_id or 'default'}.json")
    processed_recently = set()
    try:
        if os.path.exists(progress_file):
            import json as _json
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = _json.load(f)
            now = time.time()
            # Hapus entri >1 jam, simpan yang masih valid
            valid = {k: v for k, v in progress_data.items() if now - v < 3600}
            processed_recently = set(valid.keys())
            if len(processed_recently) > 0:
                log(f"📊 {len(processed_recently)} grup sudah diproses dalam 1 jam terakhir — akan di-skip.", worker_tag)
            # Update file dengan entri valid saja (cleanup expired)
            if len(valid) < len(progress_data):
                with open(progress_file, "w", encoding="utf-8") as f:
                    _json.dump(valid, f, indent=2)
    except Exception as e:
        log(f"⚠️ Gagal membaca session progress: {e}", worker_tag)

    # Filter grup yang sudah diproses baru-baru ini
    before_count = len(worker_groups)
    worker_groups = [g for g in worker_groups if g not in processed_recently]
    skipped_progress = before_count - len(worker_groups)
    if skipped_progress > 0:
        log(f"⏭️ {skipped_progress} grup di-skip (sudah diproses dalam 1 jam terakhir). {len(worker_groups)} grup tersisa.", worker_tag)

    if not worker_groups:
        log(f"✅ Semua grup sudah diproses dalam 1 jam terakhir. Tidak ada yang perlu dilakukan.", worker_tag)
        notify_status("COMPLETED", step_msg=f"Semua grup sudah diproses ({before_count} grup)")
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": "ALREADY_DONE",
            "success_count": 0,
            "fail_count": 0,
            "total_groups": before_count,
            "duration_sec": round(time.time() - start_time, 1),
            "spoof_info": spoof_info
        }

    if randomize_groups:
        random.shuffle(worker_groups)
        log(f"🔀 Urutan posting grup DIAKAK (randomized) untuk [{worker_tag}].", worker_tag)
    else:
        log(f"📋 Urutan posting grup BERURUTAN (sequential) untuk [{worker_tag}].", worker_tag)

    success_count = 0
    fail_count = 0
    worker_status = "SELESAI"

    # Helper: simpan grup yang berhasil diproses ke session progress file
    def mark_group_processed(g_url: str):
        """Catat grup ke session progress file supaya tidak diulang dalam 1 jam."""
        try:
            import json as _json
            data = {}
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, "r", encoding="utf-8") as f:
                        data = _json.load(f)
                except Exception:
                    data = {}
            data[g_url] = time.time()
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            with open(progress_file, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2)
        except Exception:
            pass  # non-fatal: progress tracking gagal, lanjutkan

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

    # Cek cooldown pembatasan — kalau akun masih cooldown, langsung fail tanpa buka browser
    info = get_session_info(session_file)
    c_user_id = info.get("c_user", "")
    if c_user_id and restriction_cooldown.is_in_cooldown(c_user_id):
        remaining = restriction_cooldown.remaining_sec(c_user_id)
        log(f"🛡️ Akun [{worker_tag}] masih dalam cooldown RESTRICTED ({remaining:.0f}s tersisa). Skip.", worker_tag)
        notify_status("RESTRICTED", step_msg=f"Akun cooldown {remaining:.0f}s")
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": "RESTRICTED_COOLDOWN",
            "success_count": 0,
            "fail_count": len(worker_groups),
            "total_groups": len(worker_groups),
            "duration_sec": round(time.time() - start_time, 1),
            "spoof_info": spoof_info
        }

    # ── Global Instance Lock: cegah 2 proses berjalan bersamaan untuk akun yang sama ──
    # Ini mengatasi duplikasi posting saat:
    # - User jalankan autopost.py 2x di terminal
    # - User jalankan terminal + web server bersamaan
    # - Web server di-trigger saat terminal sedang running
    if c_user_id and not acquire_account_lock(c_user_id, worker_tag=worker_tag):
        log(f"🔒 Akun [{worker_tag}] sedang diproses oleh instance lain. Skip untuk cegah duplikasi.", worker_tag)
        notify_status("SKIPPED", step_msg="Akun sedang diproses oleh instance lain (lock aktif)")
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": "LOCKED_BY_OTHER",
            "success_count": 0,
            "fail_count": 0,
            "total_groups": len(worker_groups),
            "duration_sec": round(time.time() - start_time, 1),
            "spoof_info": spoof_info
        }

    # Validasi mode input (fail fast)
    try:
        validate_mode(mode)
    except ValueError as ve:
        log(f"❌ {ve}", worker_tag)
        notify_status("FAILED", step_msg=str(ve))
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": "INVALID_MODE",
            "success_count": 0,
            "fail_count": len(worker_groups),
            "total_groups": len(worker_groups),
            "duration_sec": round(time.time() - start_time, 1),
            "spoof_info": spoof_info
        }

    # Filter grup yang ada di skip-list
    initial_count = len(worker_groups)
    if group_skip_list.count() > 0:
        worker_groups = [g for g in worker_groups if not group_skip_list.is_skipped(g)]
        skipped_count = initial_count - len(worker_groups)
        if skipped_count > 0:
            log(f"🚫 {skipped_count} grup diskip (ada di skip-list). {len(worker_groups)} grup tersisa.", worker_tag)

    # Reset cancellation token di awal setiap worker_loop
    cancel_token = get_global_cancel_token()
    try:
        cancel_token.reset()
    except Exception:
        pass

    browser = None
    context = None
    page = None

    try:
        async with async_playwright() as p:
            try:
                # Sub-step progress supaya UI tidak terlihat stuck saat browser launch
                notify_status("INITIALIZING", step_msg="Meluncurkan browser Chromium...")
                log(f"   🌐 Meluncurkan browser Chromium (headless={headless})...", worker_tag)

                # Timeout wrapper: kalau create_stealth_context > 90 detik, abort
                # (normal: 5-15 detik; lambat: 30-60 detik; stuck: >90 detik)
                try:
                    browser, context = await asyncio.wait_for(
                        create_stealth_context(p, session_file=session_file, headless=headless),
                        timeout=90.0
                    )
                except asyncio.TimeoutError:
                    log(f"❌ Browser launch timeout (>90s) untuk [{worker_tag}].", worker_tag)
                    notify_status("FAILED", step_msg="Browser launch timeout (>90s). Coba restart server.")
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

                notify_status("INITIALIZING", step_msg="Membuka halaman browser...")
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

            # Coba handle profile-selector page (multi-account) jika muncul
            await handle_profile_selector_page(page, worker_tag=worker_tag)

            is_logged_in = await verify_login_status(page)
            if not is_logged_in:
                log(f"❌ Worker [{worker_tag}] GAGAL LOGIN. Cookie sesi kedaluwarsa atau ter-checkpoint.", worker_tag)
                notify_status("EXPIRED", step_msg="Sesi cookie kedaluwarsa/checkpoint")
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
                # Cek cancellation token sebelum memproses grup berikutnya
                if cancel_token.is_cancelled():
                    log(f"🛑 Cancellation diterima — menghentikan worker [{worker_tag}] pada grup {idx}.", worker_tag)
                    fail_count += (len(worker_groups) - idx + 1)
                    worker_status = "ABORTED"
                    notify_status("ABORTED", current_group=group_url, current_idx=idx, step_msg="Dibatalkan pengguna")
                    break

                log(f"\n[{worker_tag}] [{idx}/{len(worker_groups)}] Memproses grup: {group_url}")
                notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Memproses grup [{idx}/{len(worker_groups)}]")

                try:
                    if mode in ["1", "3"]:
                        # Mode 1 & 3: Auto Post / Auto Post + Auto Join
                        mem_status = await check_membership_status(page, group_url, worker_tag=worker_tag)

                        if mem_status == "RESTRICTED":
                            log(f"   ⛔ AKUN DIBATASI FACEBOOK: Menghentikan worker [{worker_tag}] agar akun aman.", worker_tag)
                            # Tandai cooldown agar worker lain tidak pakai akun ini
                            if c_user_id:
                                restriction_cooldown.mark_restricted(c_user_id, reason=f"detected at group {group_url}")
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
                                # Tandai grup ke skip-list supaya tidak di-retry sesi berikutnya
                                group_skip_list.add(group_url, reason="join failed")
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
                        ok, reason = await execute_post_to_group(page, group_url, caption, media_images, worker_tag=worker_tag)
                        if ok:
                            success_count += 1
                            notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Postingan berhasil dikirim!")
                            mark_group_processed(group_url)  # cegah duplikasi posting
                            # Auto-comment hanya jika fitur diaktifkan di config
                            try:
                                if config.AUTO_COMMENT_ENABLED or config.AUTO_LIKE_ENABLED:
                                    await execute_auto_comment_on_group(page, group_url)
                            except Exception as cmt_e:
                                log(f"   ⚠️ Auto-comment gagal (non-fatal): {cmt_e}", worker_tag)
                        else:
                            fail_count += 1
                            notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Gagal membuat postingan ({reason})")

                            # Jika kegagalan karena rate-limit, hentikan batch worker segera
                            # supaya tidak memperburuk status rate-limit akun.
                            if reason == "rate_limited":
                                log(f"   ⛔ RATE LIMIT terdeteksi pada grup {group_url}.", worker_tag)
                                log(f"   🛑 Menghentikan batch worker [{worker_tag}] agar akun tidak semakin dibatasi.", worker_tag)
                                # Tandai cooldown RESTRICTED (FB biasanya memberlakukan 30 menit)
                                if c_user_id:
                                    restriction_cooldown.mark_restricted(c_user_id, reason="rate_limited during post submit")
                                fail_count += (len(worker_groups) - idx)
                                worker_status = "RATE_LIMITED"
                                notify_status("RATE_LIMITED", current_group=group_url, current_idx=idx, step_msg="Rate limit FB — worker dihentikan")
                                break

                            # Jika composer bocor dari grup sebelumnya (detected via reason),
                            # skip grup ini supaya tidak double-post ke grup salah
                            if reason == "composer_open_failed":
                                group_skip_list.add(group_url, reason="composer open failed")

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
                            mark_group_processed(group_url)  # cegah duplikasi join
                        else:
                            fail_count += 1
                            group_skip_list.add(group_url, reason="join failed (mode 2)")
                            notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg="Gagal bergabung grup")

                except Exception as e:
                    log(f"❌ Error pada grup {group_url}: {e}", worker_tag)
                    fail_count += 1
                    notify_status("PROCESSING", current_group=group_url, current_idx=idx, step_msg=f"Error: {e}")

                # Jeda emulasi manusia antar grup (skip jeda untuk grup terakhir)
                if idx < len(worker_groups):
                    delay = random.uniform(config.DELAY_BETWEEN_GROUPS_MIN, config.DELAY_BETWEEN_GROUPS_MAX)
                    log(f"⏳ Jeda emulasi manusia {delay:.1f} detik...", worker_tag)
                    notify_status("WAITING_DELAY", current_group=group_url, current_idx=idx, step_msg=f"Jeda manusia {delay:.1f}s", delay_sec=delay)
                    # Sleep secara iteratif supaya bisa dicek cancellation setiap 0.5s
                    sleep_end = time.time() + delay
                    while time.time() < sleep_end:
                        if cancel_token.is_cancelled():
                            log(f"🛑 Cancellation diterima saat jeda worker [{worker_tag}].", worker_tag)
                            worker_status = "ABORTED"
                            break
                        await asyncio.sleep(0.5)
                    if worker_status == "ABORTED":
                        break

            # Save session state SEBELUM browser.close() agar cookie terbaru tersimpan
            try:
                if context:
                    await save_session_state(context, session_file)
            except Exception as save_e:
                log(f"⚠️ Gagal menyimpan sesi akhir: {save_e}", worker_tag)

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

    except asyncio.CancelledError:
        log(f"🛑 Worker [{worker_tag}] dibatalkan (CancelledError).", worker_tag)
        worker_status = "ABORTED"
        raise
    except Exception as fatal_e:
        log(f"💥 Fatal error pada worker [{worker_tag}]: {fatal_e}", worker_tag)
        worker_status = "FATAL_ERROR"
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": account_name,
            "status": worker_status,
            "success_count": success_count,
            "fail_count": fail_count + (len(worker_groups) - success_count - fail_count),
            "total_groups": len(worker_groups),
            "duration_sec": round(time.time() - start_time, 1),
            "spoof_info": spoof_info
        }
    finally:
        # Selalu tutup browser dengan aman walau terjadi exception.
        # Ini mencegah zombie Chromium yang menguras RAM.
        await safe_browser_cleanup(browser=browser, context=context, page=page)
        # Lepas lock supaya instance lain bisa jalan setelah ini selesai
        if c_user_id:
            release_account_lock(c_user_id)


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
        # Pengguna menekan Ctrl+C — kirim sinyal cancel ke child process lain via shared token.
        # (Tidak bisa langsung pakai global token karena separate process, tapi parent akan
        # menangkap ini dan meng-terminate sibling juga.)
        log(f"🛑 Worker [{worker_tag}] diinterrupt oleh pengguna (KeyboardInterrupt).", worker_tag)
        result_queue.put({
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": worker_tag,
            "status": "ABORTED",
            "success_count": 0,
            "fail_count": len(groups),
            "total_groups": len(groups),
            "duration_sec": 0,
            "spoof_info": "N/A"
        })
    except asyncio.CancelledError:
        log(f"🛑 Worker [{worker_tag}] dibatalkan (CancelledError).", worker_tag)
        result_queue.put({
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": worker_tag,
            "status": "ABORTED",
            "success_count": 0,
            "fail_count": len(groups),
            "total_groups": len(groups),
            "duration_sec": 0,
            "spoof_info": "N/A"
        })
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
    # Validasi mode sebelum reset monitor
    try:
        validate_mode(mode)
    except ValueError as ve:
        log(f"❌ {ve}")
        live_monitor.mark_completed(f"Gagal: mode tidak valid '{mode}'")
        raise ve
    live_monitor.reset(total_accounts=1, total_groups_target=len(groups), mode=mode)
    try:
        res = asyncio.run(worker_loop(session_file, groups, mode, worker_tag, headless, randomize_groups))
        live_monitor.mark_completed("Selesai")
        return res
    except asyncio.CancelledError:
        log(f"🛑 Worker tunggal dibatalkan (CancelledError).")
        live_monitor.mark_completed("Dibatalkan")
        return {
            "session_file": session_file,
            "worker_tag": worker_tag,
            "account_name": worker_tag,
            "status": "ABORTED",
            "success_count": 0,
            "fail_count": len(groups),
            "total_groups": len(groups),
            "duration_sec": 0,
            "spoof_info": "N/A"
        }
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

    Peningkatan:
    - Validasi mode input (fail fast sebelum spawn process).
    - Jitter acak saat startup tiap worker supaya tidak semua akun membuka FB bersamaan.
    - join(timeout) pada child process setelah terminate supaya tidak ada proses orphan.
    - Drain status_queue dengan interval lebih panjang (200ms) untuk kurangi CPU usage.
    - Setiap child process yang crash tidak menghentikan sibling lain.
    """
    # Validasi mode SEBELUM spawn process apapun
    try:
        validate_mode(mode)
    except ValueError as ve:
        log(f"❌ {ve}")
        live_monitor.mark_completed(f"Gagal: mode tidak valid '{mode}'")
        return

    targets = session_files or selected_sessions or []
    groups_list = groups or []
    if not targets:
        log("❌ Tidak ada sesi akun dipilih untuk multi-process runner.")
        live_monitor.mark_completed("Gagal: tidak ada akun")
        return
    if not groups_list:
        log("❌ Daftar grup kosong — tidak ada yang bisa diproses.")
        live_monitor.mark_completed("Gagal: groups.txt kosong")
        return

    start_total_time = time.time()
    effective_max_workers = max_workers or config.MAX_CONCURRENT_WORKERS
    effective_max_workers = max(1, min(effective_max_workers, len(targets)))

    total_groups_target = len(targets) * len(groups_list)
    live_monitor.reset(total_accounts=len(targets), total_groups_target=total_groups_target, mode=mode)

    log(f"\n=======================================================")
    log(f"⚡ MENJALANKAN {len(targets)} AKUN (PARALEL CONCURRENCY POOL)")
    log(f"⚙️ Worker Paralel Maksimal: {effective_max_workers} Akun Bersamaan (Stagger Delay: {config.WORKER_STAGGER_DELAY_SEC}s)")
    log(f"⚙️ Mode: {MODE_TEXT.get(str(mode), mode)} | Browser: {'Headless' if headless else 'GUI'}")
    log(f"🛡️ Fingerprint Spoofing: AKTIF (User-Agent, Viewport, WebGL GPU, Client Hints & Canvas Noise)")
    log(f"🎲 Startup Jitter: {config.WORKER_STARTUP_JITTER_MIN}-{config.WORKER_STARTUP_JITTER_MAX}s per worker")
    log(f"=======================================================")

    result_queue = multiprocessing.Queue()
    status_queue = multiprocessing.Queue()

    pending_sessions = list(enumerate(targets, 1))
    active_processes = []
    results = []

    def drain_status():
        # Drain dengan batas iterasi agar tidak busy-loop kalau antrian sangat panjang
        for _ in range(50):
            try:
                smsg = status_queue.get_nowait()
            except Exception:
                break
            if smsg.get("action") == "UPDATE_WORKER":
                try:
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
                    pass

    def sleep_and_drain(sec: float):
        # Drain tiap 200ms (lebih hemat CPU dibanding 100ms) + responsif terhadap KeyboardInterrupt
        end_t = time.time() + sec
        while time.time() < end_t:
            drain_status()
            time.sleep(0.2)

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
                log(f"🚀 Memulai worker [{tag}] (Active: {len(active_processes)}/{effective_max_workers})...")

                if pending_sessions:
                    # Jitter acak + stagger delay supaya tidak semua worker nge-hit FB bersamaan
                    stagger = config.WORKER_STAGGER_DELAY_SEC
                    jitter = random.uniform(
                        config.WORKER_STARTUP_JITTER_MIN,
                        config.WORKER_STARTUP_JITTER_MAX
                    )
                    total_wait = stagger + jitter
                    sleep_and_drain(total_wait)

            # Cek & kurangi isi status_queue untuk pembaruan live_monitor
            drain_status()
            sleep_and_drain(0.4)

            still_active = []
            for p in active_processes:
                if p.is_alive():
                    still_active.append(p)
                else:
                    # join dengan timeout supaya tidak block selamanya
                    try:
                        p.join(timeout=2.0)
                    except Exception:
                        pass
                    # Cek exit code untuk log
                    exit_code = p.exitcode
                    if exit_code is not None and exit_code != 0:
                        log(f"⚠️ Worker process PID {p.pid} keluar dengan exit code {exit_code}.")
            active_processes = still_active

            # Kumpulkan hasil dari result_queue
            for _ in range(50):
                try:
                    res = result_queue.get_nowait()
                    results.append(res)
                except Exception:
                    break

    except KeyboardInterrupt:
        log("\n⛔ Pembatalan oleh pengguna (Ctrl+C)! Menghentikan seluruh worker paralel...")
        # 1. Kirim SIGTERM dulu untuk graceful shutdown
        for p in active_processes:
            if p.is_alive():
                try:
                    p.terminate()
                except Exception:
                    pass
        # 2. Tunggu maksimal 5 detik untuk graceful exit
        grace_deadline = time.time() + 5.0
        for p in active_processes:
            remaining = max(0.1, grace_deadline - time.time())
            try:
                p.join(timeout=remaining)
            except Exception:
                pass
        # 3. SIGKILL yang masih hidup (force kill)
        for p in active_processes:
            if p.is_alive():
                try:
                    log(f"💀 Force-killing PID {p.pid} (tidak merespons SIGTERM).")
                    p.kill()
                    p.join(timeout=1.0)
                except Exception:
                    pass
        log("✅ Seluruh child process telah dihentikan.")
        live_monitor.mark_completed("Dibatalkan pengguna")

    # Kumpulkan sisa hasil
    for _ in range(100):
        try:
            res = result_queue.get_nowait()
            results.append(res)
        except Exception:
            break

    # Pastikan tidak ada proses zombie tertinggal
    for p in active_processes:
        if p.is_alive():
            try:
                p.kill()
                p.join(timeout=1.0)
            except Exception:
                pass

    total_dur = round(time.time() - start_total_time, 1)
    live_monitor.mark_completed("Selesai")

    if results:
        print_multi_account_summary(results, total_dur)
    else:
        log("\n🎉 Eksekusi multi-akun selesai.")
