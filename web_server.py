"""
web_server.py
Server Backend FastAPI & Real-Time SSE Streamer untuk FB AutoEngine 3.0 Ultra.
Menyediakan REST API & Server-Sent Events (SSE) untuk Antarmuka Web Dashboard.
"""
import os
import sys
import glob
import json
import asyncio
import shutil
import threading
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from utils.helpers import log, log_broadcaster
from utils.files import read_text_file, write_text_file
from utils.monitor import live_monitor
from manager.session_manager import (
    discover_all_sessions,
    interactive_login_new_account,
    relogin_existing_account,
    update_session_name,
    delete_session_file,
    import_session_file,
    verify_session_live_status,
)
from engine.collector import load_groups, load_caption, find_media_images
from manager.runner import launch_multiprocess_runner, worker_loop, run_worker_entry

app = FastAPI(
    title="FB AutoEngine 3.0 Ultra - Web Control Center",
    description="Antarmuka Web Control Center Interaktif & Real-Time untuk FB AutoEngine 3.0 Ultra",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    err_msg = str(exc) or type(exc).__name__
    log(f"❌ Unhandled Exception [{request.url.path}]: {err_msg}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"Server Error: {err_msg}", "detail": tb}
    )



# Folder static web frontend
WEB_DIR = os.path.join(config.BASE_DIR, "web")
os.makedirs(WEB_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Mount media directory untuk preview gambar/video
app.mount("/media_files", StaticFiles(directory=config.MEDIA_DIR), name="media_files")

# Status State Runner Terpusat
class RunnerState:
    def __init__(self):
        self.is_running: bool = False
        self.current_task: Optional[asyncio.Task] = None
        self.last_status: str = "IDLE"
        self.active_sessions: List[str] = []
        self.mode: str = "1"
        self.total_groups: int = 0
        self.completed_workers: int = 0

runner_state = RunnerState()


# ── Model Schemas Pydantic ───────────────────────────────────────────────────

class RenameSessionRequest(BaseModel):
    session_path: str
    new_name: str

class DeleteSessionRequest(BaseModel):
    session_path: str

class VerifySessionRequest(BaseModel):
    session_path: str

class ImportSessionRequest(BaseModel):
    json_content: str
    name: Optional[str] = "Imported_Account"

class UpdateGroupsRequest(BaseModel):
    groups: List[str]

class UpdateCaptionRequest(BaseModel):
    caption: str

class StartRunnerRequest(BaseModel):
    selected_sessions: List[str]
    mode: str = "1"
    groups_file: Optional[str] = None
    start_idx: Optional[int] = 1
    end_idx: Optional[int] = None
    headless: bool = True
    max_workers: Optional[int] = 3
    randomize_groups: bool = True
    custom_caption: Optional[str] = None

class UpdateConfigRequest(BaseModel):
    delay_min: float
    delay_max: float
    max_workers: int
    default_headless: bool
    auto_like: bool
    auto_comment: bool
    auto_comments: List[str]


# ── REST API Endpoints ────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>FB AutoEngine 3.0 Ultra API Server Running</h1><p>Frontend file index.html belum dimuat.</p>")


@app.get("/api/stats")
async def get_system_stats():
    sessions = discover_all_sessions()
    groups = load_groups()
    caption = load_caption()
    media = find_media_images()
    
    return {
        "status": "success",
        "data": {
            "total_accounts": len(sessions),
            "total_groups": len(groups),
            "has_caption": bool(caption.strip()),
            "caption_length": len(caption),
            "total_media": len(media),
            "is_running": runner_state.is_running,
            "runner_status": runner_state.last_status,
            "active_workers": len(runner_state.active_sessions) if runner_state.is_running else 0
        }
    }


@app.get("/api/sessions")
async def get_all_sessions():
    sessions = discover_all_sessions()
    return {"status": "success", "sessions": sessions}


@app.post("/api/sessions/login-new")
async def api_login_new_account(background_tasks: BackgroundTasks, tag: Optional[str] = "New_Account"):
    """Pemicu Login Akun Baru via Chromium GUI Interaktif."""
    if runner_state.is_running:
        raise HTTPException(status_code=400, detail="Otomasi sedang berjalan. Harap tunggu hingga selesai.")

    async def run_login_task():
        log(f"🔑 Web Interface: Memulai Login Akun Baru [{tag}]...")
        # Jalankan interactive login
        try:
            account_tag = tag or "New_Account"
            safe_tag = "".join([c if c.isalnum() else "_" for c in account_tag]).lower()
            target_path = os.path.join(config.SESSION_DIR, f"fb_session_{safe_tag}.json")
            
            # Kita jalankan login interaktif via session_manager
            res_path = await interactive_login_new_account(account_tag=account_tag)
            if res_path and os.path.exists(res_path):
                log(f"🎉 Login Akun Baru Berhasil! Tersimpan di {res_path}")
            else:
                log("❌ Login Akun Baru Dibatalkan atau Gagal.")
        except Exception as e:
            log(f"❌ Error Login Akun Baru: {e}")

    background_tasks.add_task(run_login_task)
    return {"status": "success", "message": "Browser GUI login interaktif akan segera terbuka di layar komputer anda."}


@app.post("/api/sessions/relogin")
async def api_relogin_account(req: VerifySessionRequest, background_tasks: BackgroundTasks):
    """Pemicu Relogin / Refresh cookie untuk akun yang sudah ada."""
    if not os.path.exists(req.session_path):
        raise HTTPException(status_code=404, detail="File sesi tidak ditemukan.")

    async def run_relogin_task():
        log(f"🔄 Web Interface: Memulai Refresh Sesi {os.path.basename(req.session_path)}...")
        try:
            ok = await relogin_existing_account(req.session_path)
            if ok:
                log(f"🎉 Sesi {os.path.basename(req.session_path)} BERHASIL diperbarui!")
            else:
                log(f"❌ Sesi {os.path.basename(req.session_path)} GAGAL diperbarui.")
        except Exception as e:
            log(f"❌ Error Relogin Sesi: {e}")

    background_tasks.add_task(run_relogin_task)
    return {"status": "success", "message": "Browser GUI refresh sesi akan segera terbuka di layar."}


@app.put("/api/sessions/rename")
async def api_rename_session(req: RenameSessionRequest):
    if not os.path.exists(req.session_path):
        raise HTTPException(status_code=404, detail="File sesi tidak ditemukan.")
    
    ok = update_session_name(req.session_path, req.new_name)
    if ok:
        log(f"✏️ Sesi {os.path.basename(req.session_path)} berhasil di-rename menjadi '{req.new_name}'.")
        return {"status": "success", "message": f"Sesi berhasil diubah menjadi {req.new_name}"}
    raise HTTPException(status_code=500, detail="Gagal mengubah nama sesi.")


@app.delete("/api/sessions/delete")
async def api_delete_session(req: DeleteSessionRequest):
    if not os.path.exists(req.session_path):
        raise HTTPException(status_code=404, detail="File sesi tidak ditemukan.")
    
    ok = delete_session_file(req.session_path)
    if ok:
        log(f"🗑️ File sesi {os.path.basename(req.session_path)} berhasil dihapus.")
        return {"status": "success", "message": "File sesi berhasil dihapus."}
    raise HTTPException(status_code=500, detail="Gagal menghapus file sesi.")


@app.post("/api/sessions/import")
async def api_import_session(req: ImportSessionRequest):
    try:
        data = json.loads(req.json_content)
        temp_file = os.path.join(config.SESSION_DIR, "_temp_import.json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        saved_path = import_session_file(temp_file, req.name or "Imported_Account")
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        if saved_path:
            log(f"📥 Berhasil mengimpor akun baru ke: {saved_path}")
            return {"status": "success", "message": "Berhasil mengimpor sesi akun.", "path": saved_path}
        raise HTTPException(status_code=400, detail="Data sesi JSON tidak valid (Cookie c_user tidak ditemukan).")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Format JSON tidak valid.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/verify")
async def api_verify_session(req: VerifySessionRequest):
    if not os.path.exists(req.session_path):
        raise HTTPException(status_code=404, detail="File sesi tidak ditemukan.")
    
    log(f"🔍 Memeriksa live status sesi: {os.path.basename(req.session_path)}...")
    live_res = await verify_session_live_status(req.session_path)
    is_live = (live_res.get("status") == "ACTIVE")
    status_str = live_res.get("message") or ("AKTIF / LIVE" if is_live else "KEDALUWARSA / CHECKPOINT")
    log(f"📊 Live Status [{os.path.basename(req.session_path)}]: {status_str}")
    return {"status": "success", "is_live": is_live, "status_text": status_str, "details": live_res}



@app.post("/api/sessions/verify-all")
async def api_verify_all_sessions():
    """Memeriksa status keaktifan seluruh cookie akun sesi sekaligus (cek login cepat)."""
    sessions = discover_all_sessions()
    results = []
    log(f"🔍 Memeriksa live status seluruh akun ({len(sessions)} akun)...")
    for s in sessions:
        spath = s.get("path", "")
        if os.path.exists(spath):
            res = await verify_session_live_status(spath)
            st = res.get("status", "EXPIRED")
            results.append({
                "path": spath,
                "name": s.get("name", "Akun"),
                "c_user": s.get("c_user", ""),
                "status": st,
                "message": res.get("message", st)
            })
    log("📊 Selesai mengecek live status seluruh akun.")
    return {"status": "success", "results": results}


def _run_playwright_posting_check(sessions: list, test_group_url: str) -> list:
    """Fungsi pembantu yang berjalan di thread mandiri dengan WindowsProactorEventLoop khusus."""
    import sys
    import asyncio
    from playwright.async_api import async_playwright
    from engine.browser import create_stealth_context, check_account_restriction, verify_login_status

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _async_runner():
        semaphore = asyncio.Semaphore(2)
        async def check_single(p, s: dict) -> dict:
            spath = s.get("path", "")
            sname = s.get("name", "Akun")

            if not os.path.exists(spath):
                return {"path": spath, "name": sname, "status": "EXPIRED", "message": "File sesi tidak ditemukan"}

            async with semaphore:
                log(f"   🔍 Memeriksa akun: {sname}...")
                browser = None
                context = None
                try:
                    browser, context = await create_stealth_context(p, session_file=spath, headless=True)
                    page = await context.new_page()

                    # 1. Navigasi ke Feed Utama Grup (Grup Tempat Akun Terdaftar)
                    target_url = "https://www.facebook.com/groups/feed/"
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=12000)
                    await page.wait_for_timeout(2000)

                    current_url = page.url.lower()
                    if "login" in current_url or "checkpoint" in current_url:
                        return {"path": spath, "name": sname, "status": "EXPIRED", "message": "Sesi Kedaluwarsa / Checkpoint"}

                    is_logged_in = await verify_login_status(page)
                    if not is_logged_in:
                        return {"path": spath, "name": sname, "status": "EXPIRED", "message": "Sesi Kedaluwarsa"}

                    # 2. Cek pembatasan global awal di halaman
                    is_res, reason = await check_account_restriction(page)
                    if is_res:
                        log(f"   ⛔ [{sname}] DIBATASI: {reason}")
                        return {"path": spath, "name": sname, "status": "RESTRICTED", "message": reason}

                    # 3. Klik Pemicu Komposer Grup ("Tulis sesuatu...", "Write something...")
                    composer_trig = page.locator(
                        'div[role="button"]:has-text("Write something"), '
                        'div[role="button"]:has-text("Tulis sesuatu"), '
                        'span:has-text("Write something"), '
                        'span:has-text("Tulis sesuatu"), '
                        'div[aria-label*="Create a public post"], '
                        'div[aria-label*="Buat postingan publik"]'
                    )

                    if await composer_trig.count() > 0:
                        try:
                            await composer_trig.first.click(timeout=4000)
                            await page.wait_for_timeout(2000)
                        except Exception:
                            pass

                    # 4. Cek restriction setelah komposer terbuka (modal dialog / alert)
                    is_res_after, reason_after = await check_account_restriction(page)
                    if is_res_after:
                        log(f"   ⛔ [{sname}] DIBATASI: {reason_after}")
                        return {"path": spath, "name": sname, "status": "RESTRICTED", "message": reason_after}

                    # 5. Cek teks pembatasan spesifik di seluruh body halaman
                    try:
                        body_text = (await page.locator("body").inner_text()).lower()
                        for kw in config.RESTRICTION_TEXTS:
                            if kw in body_text:
                                log(f"   ⛔ [{sname}] DIBATASI: Teks '{kw}' terdeteksi")
                                return {"path": spath, "name": sname, "status": "RESTRICTED", "message": f"Dibatasi FB: '{kw}'"}
                    except Exception:
                        pass

                    log(f"   ✅ [{sname}] Tidak ada pembatasan — akun dapat memposting.")
                    return {"path": spath, "name": sname, "status": "ACTIVE", "message": "Akun Aktif & Dapat Memposting"}

                except Exception as e:
                    err_msg = str(e) or type(e).__name__
                    log(f"   ⚠️ [{sname}] Warning saat cek posting: {err_msg}")
                    return {"path": spath, "name": sname, "status": "ACTIVE", "message": "Akun Aktif"}
                finally:
                    try:
                        if context: await context.close()
                        if browser: await browser.close()
                    except Exception:
                        pass

        async with async_playwright() as p:
            tasks = [check_single(p, s) for s in sessions]
            return await asyncio.gather(*tasks)

    try:
        return loop.run_until_complete(_async_runner())
    finally:
        loop.close()



@app.post("/api/sessions/check-posting")
async def api_check_posting_ability():
    """
    Memeriksa kemampuan posting ke grup untuk seluruh akun secara paralel & ultra-cepat.
    Mendeteksi akun yang terkena pembatasan FB (Restricted, Action Blocked, dll).
    Menjalankan Playwright di ProactorEventLoop thread khusus agar 100% kompatibel di Windows/Uvicorn.
    """
    sessions = discover_all_sessions()
    groups = load_groups()
    test_group_url = groups[0].strip() if groups and groups[0].strip() else "https://www.facebook.com/groups/feed/"

    log(f"🔬 Memulai cek kemampuan posting ultra-cepat ({len(sessions)} akun)...")

    results = await asyncio.to_thread(_run_playwright_posting_check, sessions, test_group_url)

    log(f"🔬 Cek kemampuan posting selesai: {len(results)} akun diperiksa.")
    return {"status": "success", "results": list(results)}








@app.get("/api/groups")
async def get_all_groups():
    groups = load_groups()
    raw_content = ""
    if os.path.exists(config.GROUPS_FILE):
        raw_content = read_text_file(config.GROUPS_FILE)
    return {"status": "success", "groups": groups, "raw_content": raw_content}


@app.post("/api/groups")
async def api_update_groups(req: UpdateGroupsRequest):
    valid_lines = [g.strip() for g in req.groups if g.strip()]
    content = "\n".join(valid_lines)
    write_text_file(config.GROUPS_FILE, content)
    log(f"👥 Daftar grup diperbarui ({len(valid_lines)} link grup).")
    return {"status": "success", "message": f"{len(valid_lines)} grup berhasil disimpan.", "count": len(valid_lines)}


@app.post("/api/groups/clean")
async def api_clean_groups():
    """Hapus duplikat dan baris kosong dari groups.txt secara otomatis."""
    groups = load_groups()
    seen = set()
    cleaned = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            cleaned.append(g)
    
    content = "\n".join(cleaned)
    write_text_file(config.GROUPS_FILE, content)
    removed_count = len(groups) - len(cleaned)
    log(f"🧹 Berhasil membersihkan daftar grup: {removed_count} duplikat dihapus ({len(cleaned)} grup unik bersisa).")
    return {"status": "success", "message": f"{removed_count} duplikat dihapus.", "cleaned_count": len(cleaned), "groups": cleaned, "raw_content": content}



@app.post("/api/groups/collect")
async def api_collect_groups(background_tasks: BackgroundTasks):
    """Jalankan kolektor grup otomatis dari skrip collect_groups.py"""
    if runner_state.is_running:
        raise HTTPException(status_code=400, detail="Otomasi sedang berjalan.")

    async def run_collector_task():
        log("🔍 Memulai Koleksi Grup Otomatis (Collect Groups Engine)...")
        try:
            from collect_groups import run_collector as collect_main
            await collect_main()
            log("🎉 Koleksi Grup Selesai! groups.txt telah diperbarui.")
        except Exception as e:
            log(f"❌ Error saat pengumpulan grup: {e}")

    background_tasks.add_task(run_collector_task)
    return {"status": "success", "message": "Proses pencarian & pengumpulan grup otomatis telah dimulai di background."}


@app.get("/api/caption")
async def get_caption_text():
    caption = load_caption()
    return {"status": "success", "caption": caption}


@app.post("/api/caption")
async def api_update_caption(req: UpdateCaptionRequest):
    write_text_file(config.CAPTION_FILE, req.caption)
    log(f"📝 Text Caption diperbarui ({len(req.caption)} karakter).")
    return {"status": "success", "message": "Caption postingan berhasil disimpan."}


@app.get("/api/media")
async def get_media_files():
    images = find_media_images()
    items = []
    for img in images:
        bname = os.path.basename(img)
        items.append({
            "name": bname,
            "path": img,
            "url": f"/media_files/{bname}",
            "size": os.path.getsize(img) if os.path.exists(img) else 0
        })
    return {"status": "success", "media": items}


@app.post("/api/media/upload")
async def api_upload_media(file: UploadFile = File(...)):
    filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
    target_path = os.path.join(config.MEDIA_DIR, filename)
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    log(f"🖼️ Media berhasil diunggah: {filename}")
    return {"status": "success", "message": f"Media {filename} berhasil diunggah.", "filename": filename, "url": f"/media_files/{filename}"}


@app.delete("/api/media")
async def api_delete_media(filename: str):
    target_path = os.path.join(config.MEDIA_DIR, filename)
    if os.path.exists(target_path):
        os.remove(target_path)
        log(f"🗑️ Media dihapus: {filename}")
        return {"status": "success", "message": f"Media {filename} berhasil dihapus."}
    raise HTTPException(status_code=404, detail="File media tidak ditemukan.")


@app.get("/api/config")
async def get_configuration():
    return {
        "status": "success",
        "config": {
            "delay_min": config.DELAY_BETWEEN_GROUPS_MIN,
            "delay_max": config.DELAY_BETWEEN_GROUPS_MAX,
            "max_workers": config.MAX_CONCURRENT_WORKERS,
            "default_headless": config.DEFAULT_HEADLESS,
            "auto_like": config.AUTO_LIKE_ENABLED,
            "auto_comment": config.AUTO_COMMENT_ENABLED,
            "auto_comments": config.AUTO_COMMENTS,
        }
    }


@app.post("/api/config")
async def api_update_config(req: UpdateConfigRequest):
    config.DELAY_BETWEEN_GROUPS_MIN = req.delay_min
    config.DELAY_BETWEEN_GROUPS_MAX = req.delay_max
    config.MAX_CONCURRENT_WORKERS = req.max_workers
    config.DEFAULT_HEADLESS = req.default_headless
    config.AUTO_LIKE_ENABLED = req.auto_like
    config.AUTO_COMMENT_ENABLED = req.auto_comment
    config.AUTO_COMMENTS = req.auto_comments
    
    log("⚙️ Konfigurasi sistem diperbarui.")
    return {"status": "success", "message": "Konfigurasi sistem berhasil disimpan."}


# ── Runner Execution Endpoints ────────────────────────────────────────────────

async def async_runner_wrapper(req: StartRunnerRequest):
    runner_state.is_running = True
    runner_state.last_status = "RUNNING"
    runner_state.active_sessions = req.selected_sessions
    
    log("\n=========================================================")
    log(f"🚀 WEB INTERFACE: MEMULAI PROSES OTOMASI")
    log(f"   Jumlah Akun: {len(req.selected_sessions)} Akun")
    log(f"   Mode: {req.mode} | Headless: {req.headless} | Workers Paralel: {req.max_workers}")
    log("=========================================================\n")

    if req.custom_caption:
        write_text_file(config.CAPTION_FILE, req.custom_caption)

    groups = load_groups(req.groups_file)
    if not groups:
        log("❌ Tidak ada grup valid yang ditemukan di groups.txt.")
        runner_state.is_running = False
        runner_state.last_status = "FAILED_NO_GROUPS"
        live_monitor.mark_completed("Gagal: groups.txt kosong")
        return

    # Filter grup range jika ada
    if req.start_idx or req.end_idx:
        st = max((req.start_idx or 1) - 1, 0)
        ed = req.end_idx if req.end_idx else len(groups)
        groups = groups[st:ed]

    tot_target = len(req.selected_sessions) * len(groups)
    live_monitor.reset(
        total_accounts=len(req.selected_sessions),
        total_groups_target=tot_target,
        mode=req.mode,
        session_files=req.selected_sessions,
        groups_count=len(groups)
    )

    try:
        if len(req.selected_sessions) == 1:
            # Single session worker (asinkron native di event loop FastAPI)
            s_file = req.selected_sessions[0]
            log(f"⚡ Menjalankan Single Account Worker untuk: {os.path.basename(s_file)}")
            await worker_loop(
                session_file=s_file,
                groups=groups,
                mode=req.mode,
                worker_tag="WebWorker-1",
                headless=req.headless,
                randomize_groups=req.randomize_groups
            )
        else:
            # Multi-process runner (dijalankan di thread pool terpisah agar non-blocking)
            log(f"⚡ Menjalankan Multi-Process Engine ({len(req.selected_sessions)} Sesi Paralel)")
            await asyncio.to_thread(
                launch_multiprocess_runner,
                session_files=req.selected_sessions,
                groups=groups,
                mode=req.mode,
                headless=req.headless,
                max_workers=req.max_workers,
                randomize_groups=req.randomize_groups
            )
        log("🎉 SELESAI: Seluruh proses otomasi telah dirampungkan!")
        runner_state.last_status = "COMPLETED"
    except Exception as e:
        log(f"❌ Error selama eksekusi otomasi: {e}")
        runner_state.last_status = "ERROR"
    finally:
        runner_state.is_running = False
        runner_state.active_sessions = []


@app.post("/api/runner/start")
async def start_runner(req: StartRunnerRequest, background_tasks: BackgroundTasks):
    if runner_state.is_running:
        raise HTTPException(status_code=400, detail="Otomasi sedang berjalan.")

    if not req.selected_sessions:
        raise HTTPException(status_code=400, detail="Harap pilih minimal 1 sesi akun Facebook.")

    task = asyncio.create_task(async_runner_wrapper(req))
    runner_state.current_task = task
    
    return {"status": "success", "message": f"Otomasi dimulai untuk {len(req.selected_sessions)} akun."}


@app.get("/api/runner/live-status")
async def get_runner_live_status():
    """Endpoint REST API untuk snapshot status Live Monitor real-time."""
    return {
        "status": "success",
        "data": live_monitor.get_live_status()
    }


@app.post("/api/runner/stop")
async def stop_runner():
    if not runner_state.is_running:
        return {"status": "success", "message": "Tidak ada otomasi yang sedang berjalan."}

    if runner_state.current_task and not runner_state.current_task.done():
        runner_state.current_task.cancel()
        
    runner_state.is_running = False
    runner_state.last_status = "ABORTED"
    live_monitor.mark_completed("ABORTED oleh pengguna")
    log("🛑 Web Interface: Sinyal pembatalan otomasi dikirim. Menghentikan worker...")
    return {"status": "success", "message": "Sinyal pembatalan otomasi dikirim."}


# ── Server-Sent Events (SSE) Real-Time Log Streaming ─────────────────────────

@app.get("/api/runner/stream-logs")
async def stream_logs(request: Request):
    """
    Endpoint SSE (Server-Sent Events) untuk streaming log konsol terminal secara real-time ke browser client.
    """
    queue = log_broadcaster.subscribe()

    async def log_generator():
        try:
            # Kirim log riwayat awal dari activity.log (100 baris terakhir) jika ada
            log_file = os.path.join(config.LOGS_DIR, "activity.log")
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()[-60:]
                        for line in lines:
                            yield f"data: {json.dumps({'message': line.strip()})}\n\n"
                except Exception:
                    pass

            # Listen untuk pesan log baru
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps({'message': msg})}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat untuk menjaga koneksi SSE tetap hidup
                    yield f": heartbeat\n\n"
        finally:
            log_broadcaster.unsubscribe(queue)

    return StreamingResponse(log_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=False)
