"""
run_web.py
Skrip Peluncur Utama Antarmuka Web Dashboard FB AutoEngine 3.0 Ultra.
Memulai server Uvicorn/FastAPI dan membuka browser web secara otomatis.
"""
import os
import sys
import time
import threading
import webbrowser
import uvicorn

import config
from utils.helpers import auto_pull_github

def open_browser_delayed(url: str, delay_sec: float = 1.5):

    time.sleep(delay_sec)
    print(f"🌐 Membuka browser web di: {url}")
    webbrowser.open(url)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    auto_pull_github()

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print("=================================================================")
    print("   🌐 FB AUTOENGINE 3.0 ULTRA - WEB CONTROL CENTER DASHBOARD")
    print(f"      Server URL: {url}")
    print("      Arsitektur: FastAPI + Uvicorn + Real-Time SSE Log Streaming")
    print("=================================================================\n")

    # Buka browser secara otomatis di thread terpisah
    threading.Thread(target=open_browser_delayed, args=(url, 1.5), daemon=True).start()

    # Jalankan Uvicorn Web Server
    uvicorn.run("web_server:app", host=host, port=port, log_level="info", reload=True)

if __name__ == "__main__":
    main()
