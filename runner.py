"""
runner.py — Worker loop: single & multi-process.
"""
import sys, os, time, random, asyncio, multiprocessing, json
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import config
from helpers import (log, get_c_user, get_account_name, pick_profile,
                     lock_acquire, lock_release, load_groups, load_caption,
                     find_media, discover_sessions, normalize_url)
from browser import create_browser, save_session, is_logged_in, check_restriction, goto
from poster import post_to_group
from joiner import check_membership, execute_join

VALID_MODES = {"1", "2", "3"}
MODE_NAMES = {"1": "Post", "2": "Join", "3": "Post+Join"}


def fix_encoding():
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


# ── Skip-list (grup yang gagal persisten) ────────────────────────────────────
def skip_list_load():
    if not os.path.exists(config.SKIP_FILE):
        return set()
    try:
        with open(config.SKIP_FILE, "r", encoding="utf-8") as f:
            return set(l.strip().split("#")[0].strip() for l in f if l.strip() and not l.startswith("#"))
    except Exception:
        return set()


def skip_list_add(url, reason="failed"):
    try:
        os.makedirs(os.path.dirname(config.SKIP_FILE), exist_ok=True)
        with open(config.SKIP_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}#{reason}\n")
    except Exception:
        pass


# ── Cooldown (in-memory) ────────────────────────────────────────────────────
_cooldowns: dict = {}

def cooldown_mark(c_user, reason=""):
    if c_user:
        _cooldowns[c_user] = time.time() + config.COOLDOWN_SEC
        log(f"🛡️ {c_user} cooldown {config.COOLDOWN_SEC}s ({reason})")

def cooldown_active(c_user):
    if not c_user:
        return False
    exp = _cooldowns.get(c_user)
    if exp is None:
        return False
    if time.time() >= exp:
        _cooldowns.pop(c_user, None)
        return False
    return True


# ── Session progress (anti-duplikasi 1 jam) ─────────────────────────────────
def progress_load(c_user):
    fp = os.path.join(config.DATA_DIR, f"progress_{c_user or 'default'}.json")
    try:
        if os.path.exists(fp):
            with open(fp, "r") as f:
                data = json.load(f)
            now = time.time()
            valid = {k: v for k, v in data.items() if now - v < 3600}
            return set(valid.keys()), fp
    except Exception:
        pass
    return set(), fp


def progress_mark(fp, url):
    try:
        data = {}
        if os.path.exists(fp):
            try:
                with open(fp, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data[url] = time.time()
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ── Worker loop ─────────────────────────────────────────────────────────────
async def worker_loop(session_file, groups, mode, tag="Worker", headless=True, randomize=True):
    """Proses 1 akun: post/join ke list grup."""
    start = time.time()
    c_user = get_c_user(session_file)
    name = get_account_name(session_file)
    prof = pick_profile(session_file)
    spoof = f"{prof['gpu']} | {prof['vp']['width']}x{prof['vp']['height']}"

    log(f"🚀 [{tag}] mulai | {name}", tag)
    log(f"🛡️ Spoof: {spoof}", tag)

    # Validasi mode
    if mode not in VALID_MODES:
        log(f"❌ Mode invalid: {mode}", tag)
        return {"status": "INVALID_MODE", "ok": 0, "fail": len(groups)}

    # Lock
    if not lock_acquire(c_user, tag):
        log(f"🔒 [{tag}] sedang diproses instance lain. Skip.", tag)
        return {"status": "LOCKED", "ok": 0, "fail": 0}

    # Cooldown
    if cooldown_active(c_user):
        log(f"🛡️ [{tag}] cooldown aktif. Skip.", tag)
        return {"status": "COOLDOWN", "ok": 0, "fail": len(groups)}

    # Dedup grup
    seen = set()
    deduped = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            deduped.append(g)

    # Skip-list
    skip = skip_list_load()
    if skip:
        before = len(deduped)
        deduped = [g for g in deduped if g not in skip]
        if before > len(deduped):
            log(f"🚫 {before - len(deduped)} grup di-skip-list", tag)

    # Session progress
    processed, prog_file = progress_load(c_user)
    if processed:
        before = len(deduped)
        deduped = [g for g in deduped if g not in processed]
        log(f"⏭️ {before - len(deduped)} grup sudah diproses <1jam. {len(deduped)} tersisa.", tag)

    if not deduped:
        log(f"✅ Semua grup sudah diproses.", tag)
        lock_release(c_user)
        return {"status": "DONE", "ok": 0, "fail": 0}

    # Acak
    if randomize:
        random.shuffle(deduped)
        log(f"🔀 Urutan diacak ({len(deduped)} grup)", tag)

    caption = load_caption()
    media = find_media()

    ok_count = 0
    fail_count = 0
    browser = None
    context = None
    page = None

    try:
        async with async_playwright() as p:
            # Launch browser
            log(f"   🌐 Launch browser (headless={headless})...", tag)
            try:
                browser, context = await asyncio.wait_for(
                    create_browser(p, session_file, headless=headless),
                    timeout=90.0
                )
                page = await context.new_page()
            except asyncio.TimeoutError:
                log(f"❌ Browser launch timeout", tag)
                return {"status": "ERROR", "ok": 0, "fail": len(deduped)}
            except Exception as e:
                log(f"❌ Browser error: {e}", tag)
                return {"status": "ERROR", "ok": 0, "fail": len(deduped)}

            # Login check
            log(f"   🔍 Cek login...", tag)
            await goto(page, "https://www.facebook.com/")
            if not await is_logged_in(page):
                log(f"❌ GAGAL LOGIN. Sesi kedaluwarsa.", tag)
                return {"status": "EXPIRED", "ok": 0, "fail": len(deduped)}

            log(f"✅ Login OK. Proses {len(deduped)} grup...", tag)

            for idx, gurl in enumerate(deduped, 1):
                log(f"\n[{tag}] [{idx}/{len(deduped)}] {gurl}")

                try:
                    if mode in ["1", "3"]:
                        # Cek membership
                        mem = await check_membership(page, gurl, tag)

                        if mem == "RESTRICTED":
                            log(f"   ⛔ DIBATASI! Stop.", tag)
                            cooldown_mark(c_user, "restricted")
                            fail_count += (len(deduped) - idx + 1)
                            break

                        if mem == "NOT_LOGGED_IN":
                            log(f"   ❌ Sesi putus. Stop.", tag)
                            fail_count += (len(deduped) - idx + 1)
                            break

                        if mem in ["NOT_JOINED", "UNKNOWN"]:
                            if mode == "3":
                                log(f"   ℹ️ Belum join. Join dulu...", tag)
                                jok = await execute_join(page, gurl, tag)
                                if not jok:
                                    log(f"   ⚠️ Gagal join. Skip post.", tag)
                                    fail_count += 1
                                    skip_list_add(gurl, "join failed")
                                    continue
                                await asyncio.sleep(random.uniform(1, 2))
                                mem = await check_membership(page, gurl, tag)
                            else:
                                log(f"   ⚠️ Bukan anggota. Skip.", tag)
                                fail_count += 1
                                continue

                        if mem == "PENDING":
                            log(f"   ⏳ Join pending. Skip post.", tag)
                            fail_count += 1
                            continue

                        if mem != "JOINED":
                            log(f"   ⚠️ Status: {mem}. Skip.", tag)
                            fail_count += 1
                            continue

                        # POST
                        success, reason = await post_to_group(page, gurl, caption, media, tag)
                        if success:
                            ok_count += 1
                            progress_mark(prog_file, gurl)
                            log(f"   ✅ Berhasil! ({reason})", tag)
                        else:
                            fail_count += 1
                            if "rate_limited" in reason:
                                log(f"   ⛔ RATE LIMIT! Stop batch.", tag)
                                cooldown_mark(c_user, "rate_limited")
                                fail_count += (len(deduped) - idx)
                                break
                            log(f"   ❌ Gagal: {reason}", tag)

                    elif mode == "2":
                        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                            log(f"   ❌ Sesi putus. Stop.", tag)
                            fail_count += (len(deduped) - idx + 1)
                            break

                        jok = await execute_join(page, gurl, tag)
                        if jok:
                            ok_count += 1
                            progress_mark(prog_file, gurl)
                            log(f"   ✅ Join berhasil!", tag)
                        else:
                            fail_count += 1
                            skip_list_add(gurl, "join failed")

                except Exception as e:
                    log(f"❌ Error: {e}", tag)
                    fail_count += 1

                # Jeda
                if idx < len(deduped):
                    delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX)
                    log(f"⏳ Jeda {delay:.1f}s...", tag)
                    await asyncio.sleep(delay)

            # Save session
            try:
                if context:
                    await save_session(context, session_file, name)
            except Exception:
                pass

            dur = round(time.time() - start, 1)
            log(f"\n{'='*60}", tag)
            log(f"🎉 [{tag}] SELESAI ({dur}s)", tag)
            log(f"📊 {ok_count} OK | {fail_count} Gagal | {len(deduped)} Grup", tag)
            log(f"{'='*60}", tag)

            return {"status": "SELESAI", "ok": ok_count, "fail": fail_count, "dur": dur}

    except asyncio.CancelledError:
        log(f"🛑 [{tag}] dibatalkan.", tag)
        raise
    except Exception as e:
        log(f"💥 Fatal [{tag}]: {e}", tag)
        return {"status": "FATAL", "ok": ok_count, "fail": fail_count}
    finally:
        # Cleanup browser
        for obj in [page, context, browser]:
            if obj:
                try:
                    await obj.close()
                except Exception:
                    pass
        lock_release(c_user)


# ── Multi-process ───────────────────────────────────────────────────────────
def _mp_entry(sfile, groups, mode, tag, headless, randomize, rq):
    fix_encoding()
    try:
        res = asyncio.run(worker_loop(sfile, groups, mode, tag, headless, randomize))
        rq.put(res)
    except Exception as e:
        log(f"❌ Fatal [{tag}]: {e}", tag)
        rq.put({"status": "FATAL", "ok": 0, "fail": len(groups)})


def run_single(sfile, groups, mode, tag="Worker", headless=True, randomize=True):
    fix_encoding()
    return asyncio.run(worker_loop(sfile, groups, mode, tag, headless, randomize))


def run_multi(session_files, groups, mode="1", max_workers=None, headless=True, randomize=True):
    if mode not in VALID_MODES:
        log(f"❌ Mode invalid: {mode}")
        return
    targets = session_files or []
    if not targets or not groups:
        log("❌ Tidak ada akun atau grup.")
        return

    mw = max(1, min(max_workers or config.MAX_WORKERS, len(targets)))
    log(f"\n⚡ {len(targets)} akun paralel (max {mw} workers)")
    log(f"⚙️ Mode: {MODE_NAMES[mode]} | Headless: {headless}")
    log(f"{'='*60}\n")

    rq = multiprocessing.Queue()
    pending = list(enumerate(targets, 1))
    active = []
    results = []

    try:
        while pending or active:
            while pending and len(active) < mw:
                idx, sf = pending.pop(0)
                name = get_account_name(sf)
                tag = f"Akun-{idx} ({name})"
                p = multiprocessing.Process(target=_mp_entry,
                    args=(sf, groups, mode, tag, headless, randomize, rq))
                p.start()
                active.append(p)
                log(f"🚀 Start [{tag}]")
                if pending:
                    time.sleep(config.STAGGER_SEC + random.uniform(config.JITTER_MIN, config.JITTER_MAX))

            time.sleep(0.5)
            still = []
            for p in active:
                if p.is_alive():
                    still.append(p)
                else:
                    p.join(timeout=2)
            active = still

            while not rq.empty():
                try:
                    results.append(rq.get_nowait())
                except Exception:
                    break

    except KeyboardInterrupt:
        log("\n⛔ Ctrl+C! Stop semua...")
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

    while not rq.empty():
        try:
            results.append(rq.get_nowait())
        except Exception:
            break

    for p in active:
        if p.is_alive():
            try:
                p.kill()
                p.join(timeout=1)
            except Exception:
                pass

    total_ok = sum(r.get("ok", 0) for r in results)
    total_fail = sum(r.get("fail", 0) for r in results)
    log(f"\n{'='*60}")
    log(f"📊 TOTAL: {total_ok} OK | {total_fail} Gagal | {len(results)} Akun")
    log(f"{'='*60}")
