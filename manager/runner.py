"""
manager/runner.py
Worker loop terminal-only. Single & multi-process.
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
from utils.helpers import log, acquire_account_lock, release_account_lock
from utils.browser import random_human_delay, safe_goto
from utils.retry import (
    safe_browser_cleanup,
    restriction_cooldown,
    group_skip_list,
    validate_media_files,
)
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

VALID_MODES = {"1", "2", "3"}


def fix_windows_stdout_encoding():
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def validate_mode(mode: str) -> str:
    m = str(mode).strip()
    if m not in VALID_MODES:
        raise ValueError(f"Mode tidak valid: '{m}'. Pilih: 1=Post, 2=Join, 3=Post+Join")
    return m


async def worker_loop(
    session_file: str,
    groups: List[str],
    mode: str,
    worker_tag: str = "Worker",
    headless: bool = False,
    randomize_groups: bool = True,
) -> Dict[str, Any]:
    """
    Worker loop untuk 1 akun. Terminal-only, tidak ada web monitor.
    - mode 1: Auto Post
    - mode 2: Auto Join
    - mode 3: Auto Post + Auto Join
    """
    start_time = time.time()
    profile = generate_deterministic_profile(session_file)
    account_name = profile.get("account_name", os.path.basename(session_file))
    spoof_info = f"{profile.get('renderer')} | {profile.get('viewport', {}).get('width')}x{profile.get('viewport', {}).get('height')}"

    # Inisialisasi c_user_id SEJAK AWAL
    info = get_session_info(session_file)
    c_user_id = info.get("c_user", "")

    log(f"🚀 Worker [{worker_tag}] dimulai | Akun: {account_name}", worker_tag)
    log(f"🛡️ Spoof: GPU [{profile.get('renderer')}] | CPU [{profile.get('cores')}] | RAM [{profile.get('memory')}GB]", worker_tag)

    # Validasi mode
    try:
        validate_mode(mode)
    except ValueError as ve:
        log(f"❌ {ve}", worker_tag)
        return {"status": "INVALID_MODE", "success_count": 0, "fail_count": len(groups)}

    # Lock: cegah 2 proses untuk akun yang sama
    if c_user_id and not acquire_account_lock(c_user_id, worker_tag):
        log(f"🔒 Akun [{worker_tag}] sedang diproses instance lain. Skip.", worker_tag)
        return {"status": "LOCKED", "success_count": 0, "fail_count": 0}

    # Cooldown check
    if c_user_id and restriction_cooldown.is_in_cooldown(c_user_id):
        remaining = restriction_cooldown.remaining_sec(c_user_id)
        log(f"🛡️ Akun [{worker_tag}] cooldown {remaining:.0f}s. Skip.", worker_tag)
        return {"status": "COOLDOWN", "success_count": 0, "fail_count": len(groups)}

    # Deduplikasi grup
    seen = set()
    worker_groups = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            worker_groups.append(g)

    # Session progress: skip grup yang sudah diproses dalam 1 jam
    progress_file = os.path.join(config.DATA_DIR, f"session_progress_{c_user_id or 'default'}.json")
    processed = set()
    try:
        if os.path.exists(progress_file):
            import json as _json
            with open(progress_file, "r", encoding="utf-8") as f:
                pdata = _json.load(f)
            now = time.time()
            valid = {k: v for k, v in pdata.items() if now - v < 3600}
            processed = set(valid.keys())
            if len(processed) > 0:
                log(f"📊 {len(processed)} grup sudah diproses <1 jam. Skip.", worker_tag)
    except Exception:
        pass

    before = len(worker_groups)
    worker_groups = [g for g in worker_groups if g not in processed]
    skipped = before - len(worker_groups)
    if skipped > 0:
        log(f"⏭️ {skipped} grup di-skip (sudah diproses). {len(worker_groups)} tersisa.", worker_tag)

    if not worker_groups:
        log(f"✅ Semua grup sudah diproses. Tidak ada yang perlu dilakukan.", worker_tag)
        if c_user_id:
            release_account_lock(c_user_id)
        return {"status": "DONE", "success_count": 0, "fail_count": 0, "total": before}

    if randomize_groups:
        random.shuffle(worker_groups)
        log(f"🔀 Urutan grup diacak ({len(worker_groups)} grup).", worker_tag)

    def mark_done(url):
        try:
            import json as _json
            data = {}
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, "r", encoding="utf-8") as f:
                        data = _json.load(f)
                except Exception:
                    pass
            data[url] = time.time()
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            with open(progress_file, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2)
        except Exception:
            pass

    caption = load_caption()
    media_images = find_media_images()

    success_count = 0
    fail_count = 0
    browser = None
    context = None
    page = None

    try:
        async with async_playwright() as p:
            log(f"   🌐 Meluncurkan browser (headless={headless})...", worker_tag)
            try:
                browser, context = await asyncio.wait_for(
                    create_stealth_context(p, session_file=session_file, headless=headless),
                    timeout=90.0
                )
                page = await context.new_page()
            except asyncio.TimeoutError:
                log(f"❌ Browser launch timeout (>90s).", worker_tag)
                return {"status": "ERROR_INIT", "success_count": 0, "fail_count": len(worker_groups)}
            except Exception as e:
                log(f"❌ Gagal init browser: {e}", worker_tag)
                return {"status": "ERROR_INIT", "success_count": 0, "fail_count": len(worker_groups)}

            # Verifikasi login
            log(f"   🔍 Cek login...", worker_tag)
            try:
                await safe_goto(page, "https://www.facebook.com/", timeout_ms=20000)
            except Exception:
                pass
            await handle_profile_selector_page(page, worker_tag=worker_tag)

            if not await verify_login_status(page):
                log(f"❌ GAGAL LOGIN. Sesi kedaluwarsa.", worker_tag)
                return {"status": "EXPIRED", "success_count": 0, "fail_count": len(worker_groups)}

            log(f"✅ Login OK. Memproses {len(worker_groups)} grup...", worker_tag)

            for idx, group_url in enumerate(worker_groups, 1):
                log(f"\n[{worker_tag}] [{idx}/{len(worker_groups)}] {group_url}")

                try:
                    if mode in ["1", "3"]:
                        mem = await check_membership_status(page, group_url, worker_tag=worker_tag)

                        if mem == "RESTRICTED":
                            log(f"   ⛔ DIBATASI FB! Stop worker.", worker_tag)
                            if c_user_id:
                                restriction_cooldown.mark_restricted(c_user_id, reason=f"group {group_url}")
                            fail_count += (len(worker_groups) - idx + 1)
                            break

                        if mem == "NOT_LOGGED_IN":
                            log(f"   ❌ Sesi terputus. Stop.", worker_tag)
                            fail_count += (len(worker_groups) - idx + 1)
                            break

                        if mem in ["NOT_JOINED", "UNKNOWN"]:
                            log(f"   ℹ️ Belum join. Mencoba join...", worker_tag)
                            join_ok = await execute_join_group(page, group_url, worker_tag=worker_tag)
                            if not join_ok:
                                log(f"   ⚠️ Gagal join. Skip post.", worker_tag)
                                fail_count += 1
                                group_skip_list.add(group_url, reason="join failed")
                                continue
                            await random_human_delay(1.0, 2.0)
                            mem = await check_membership_status(page, group_url, worker_tag=worker_tag)

                        if mem == "PENDING":
                            log(f"   ⏳ Join pending admin. Skip post.", worker_tag)
                            fail_count += 1
                            continue

                        if mem != "JOINED":
                            log(f"   ⚠️ Status: {mem}. Skip post.", worker_tag)
                            fail_count += 1
                            continue

                        # POST
                        ok, reason = await execute_post_to_group(page, group_url, caption, media_images, worker_tag=worker_tag)
                        if ok:
                            success_count += 1
                            mark_done(group_url)
                            log(f"   ✅ Post berhasil!", worker_tag)
                            try:
                                if config.AUTO_COMMENT_ENABLED or config.AUTO_LIKE_ENABLED:
                                    await execute_auto_comment_on_group(page, group_url)
                            except Exception as cmt_e:
                                log(f"   ⚠️ Auto-comment gagal: {cmt_e}", worker_tag)
                        else:
                            fail_count += 1
                            if reason == "rate_limited":
                                log(f"   ⛔ RATE LIMIT! Stop batch.", worker_tag)
                                if c_user_id:
                                    restriction_cooldown.mark_restricted(c_user_id, reason="rate_limited")
                                fail_count += (len(worker_groups) - idx)
                                break

                    elif mode == "2":
                        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                            log(f"   ❌ Sesi terputus. Stop.", worker_tag)
                            fail_count += (len(worker_groups) - idx + 1)
                            break

                        ok = await execute_join_group(page, group_url, worker_tag=worker_tag)
                        if ok:
                            success_count += 1
                            mark_done(group_url)
                            log(f"   ✅ Join berhasil!", worker_tag)
                        else:
                            fail_count += 1
                            group_skip_list.add(group_url, reason="join failed")

                except Exception as e:
                    log(f"❌ Error grup {group_url}: {e}", worker_tag)
                    fail_count += 1

                # Jeda antar grup
                if idx < len(worker_groups):
                    delay = random.uniform(config.DELAY_BETWEEN_GROUPS_MIN, config.DELAY_BETWEEN_GROUPS_MAX)
                    log(f"⏳ Jeda {delay:.1f}s...", worker_tag)
                    await asyncio.sleep(delay)

            # Save session
            try:
                if context:
                    await save_session_state(context, session_file)
            except Exception as e:
                log(f"⚠️ Gagal save session: {e}", worker_tag)

            duration = round(time.time() - start_time, 1)
            log(f"\n{'='*60}", worker_tag)
            log(f"🎉 [{worker_tag}] SELESAI ({duration}s)", worker_tag)
            log(f"📊 {success_count} Sukses | {fail_count} Gagal | {len(worker_groups)} Grup", worker_tag)
            log(f"{'='*60}", worker_tag)

            return {
                "status": "SELESAI",
                "success_count": success_count,
                "fail_count": fail_count,
                "total_groups": len(worker_groups),
                "duration_sec": duration,
            }

    except asyncio.CancelledError:
        log(f"🛑 [{worker_tag}] dibatalkan.", worker_tag)
        raise
    except Exception as e:
        log(f"💥 Fatal error [{worker_tag}]: {e}", worker_tag)
        return {"status": "FATAL_ERROR", "success_count": success_count, "fail_count": fail_count}
    finally:
        await safe_browser_cleanup(browser=browser, context=context, page=page)
        if c_user_id:
            release_account_lock(c_user_id)


# ── Multi-process ────────────────────────────────────────────────────────────

def _mp_entry(session_file, groups, mode, worker_tag, headless, randomize, result_queue):
    fix_windows_stdout_encoding()
    try:
        res = asyncio.run(worker_loop(session_file, groups, mode, worker_tag, headless, randomize))
        result_queue.put(res)
    except Exception as e:
        log(f"❌ Fatal [{worker_tag}]: {e}", worker_tag)
        result_queue.put({"status": "FATAL", "success_count": 0, "fail_count": len(groups)})


def run_worker_entry(session_file, groups, mode, worker_tag="Worker", headless=True, randomize_groups=True):
    """Jalankan single worker."""
    fix_windows_stdout_encoding()
    validate_mode(mode)
    try:
        return asyncio.run(worker_loop(session_file, groups, mode, worker_tag, headless, randomize_groups))
    except Exception as e:
        log(f"❌ Gagal: {e}")
        raise


def launch_multiprocess_runner(session_files, groups, mode="1", max_workers=None, headless=True, randomize_groups=True):
    """Jalankan multi-akun paralel."""
    validate_mode(mode)
    targets = session_files or []
    if not targets or not groups:
        log("❌ Tidak ada akun atau grup.")
        return

    max_w = max(1, min(max_workers or config.MAX_CONCURRENT_WORKERS, len(targets)))
    log(f"\n⚡ {len(targets)} akun paralel (max {max_w} workers)")
    log(f"⚙️ Mode: {mode} | Headless: {headless}")
    log(f"{'='*60}\n")

    result_queue = multiprocessing.Queue()
    pending = list(enumerate(targets, 1))
    active = []
    results = []

    try:
        while pending or active:
            while pending and len(active) < max_w:
                idx, s_file = pending.pop(0)
                profile = generate_deterministic_profile(s_file)
                name = profile.get("account_name", os.path.basename(s_file))
                tag = f"Akun-{idx} ({name})"

                proc = multiprocessing.Process(
                    target=_mp_entry,
                    args=(s_file, groups, mode, tag, headless, randomize_groups, result_queue)
                )
                proc.start()
                active.append(proc)
                log(f"🚀 Start [{tag}]")

                if pending:
                    jitter = random.uniform(config.WORKER_STARTUP_JITTER_MIN, config.WORKER_STARTUP_JITTER_MAX)
                    time.sleep(config.WORKER_STAGGER_DELAY_SEC + jitter)

            time.sleep(0.5)
            still = []
            for p in active:
                if p.is_alive():
                    still.append(p)
                else:
                    p.join(timeout=2)
            active = still

            while not result_queue.empty():
                try:
                    results.append(result_queue.get_nowait())
                except Exception:
                    break

    except KeyboardInterrupt:
        log("\n⛔ Ctrl+C! Stop semua worker...")
        for p in active:
            if p.is_alive():
                p.terminate()
        for p in active:
            if p.is_alive():
                try:
                    p.join(timeout=5)
                except Exception:
                    pass
                if p.is_alive():
                    p.kill()

    while not result_queue.empty():
        try:
            results.append(result_queue.get_nowait())
        except Exception:
            break

    # Cleanup zombies
    for p in active:
        if p.is_alive():
            try:
                p.kill()
                p.join(timeout=1)
            except Exception:
                pass

    # Summary
    total_s = sum(r.get("success_count", 0) for r in results)
    total_f = sum(r.get("fail_count", 0) for r in results)
    log(f"\n{'='*60}")
    log(f"📊 TOTAL: {total_s} Sukses | {total_f} Gagal | {len(results)} Akun")
    log(f"{'='*60}")
