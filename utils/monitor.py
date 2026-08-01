"""
utils/monitor.py
Manajer Pelacak Status Real-Time Live Monitor untuk FB AutoEngine 3.0 Ultra.
Mengelola state terpusat progress master, status worker per akun, event stream, dan KPI metrics.
"""
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

class LiveMonitorManager:
    """Manajer status real-time thread-safe untuk memantau eksekusi otomasi multi-akun."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self.is_running: bool = False
        self.mode: str = "1"
        self.mode_text: str = "Auto Post ke Grup"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_accounts: int = 0
        self.total_groups_target: int = 0
        self.total_groups_processed: int = 0
        self.total_success: int = 0
        self.total_fail: int = 0
        self.active_workers_count: int = 0
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.recent_events: List[Dict[str, Any]] = []
        self.max_events: int = 50

    def reset(
        self,
        total_accounts: int,
        total_groups_target: int,
        mode: str = "1",
        session_files: Optional[List[str]] = None,
        groups_count: int = 0
    ):
        """Reset state monitor sebelum memulai sesi otomasi baru dan inisialisasi kartu worker."""
        with self._lock:
            self.is_running = True
            self.mode = mode
            mode_map = {
                "1": "Auto Post ke Grup",
                "2": "Auto Join Grup",
                "3": "Auto Post + Auto Join"
            }
            self.mode_text = mode_map.get(str(mode), "Auto Post ke Grup")
            self.start_time = time.time()
            self.end_time = None
            self.total_accounts = total_accounts
            self.total_groups_target = total_groups_target
            self.total_groups_processed = 0
            self.total_success = 0
            self.total_fail = 0
            self.active_workers_count = total_accounts
            self.workers.clear()
            self.recent_events.clear()
            self.add_event("SYSTEM", "START", f"Otomasi dimulai ({total_accounts} akun | {total_groups_target} total grup target)")

            if session_files:
                from engine.browser import generate_deterministic_profile
                for idx, s_file in enumerate(session_files, 1):
                    try:
                        profile = generate_deterministic_profile(s_file)
                        acc_name = profile.get("account_name", os.path.basename(s_file))
                        wtag = f"Akun-{idx} ({acc_name})"
                        spoof = f"{profile.get('renderer')} | {profile.get('viewport', {}).get('width')}x{profile.get('viewport', {}).get('height')}"
                        self.workers[wtag] = {
                            "worker_tag": wtag,
                            "account_name": acc_name,
                            "session_file": s_file,
                            "status": "INITIALIZING",
                            "current_group": "",
                            "current_idx": 0,
                            "total_groups": groups_count,
                            "success_count": 0,
                            "fail_count": 0,
                            "progress_percent": 0.0,
                            "step_msg": "Menyiapkan worker browser...",
                            "spoof_info": spoof,
                            "delay_sec": 0.0,
                            "delay_until": 0.0,
                            "last_update_time": time.time()
                        }
                    except Exception:
                        pass

    def update_worker(
        self,
        worker_tag: str,
        account_name: str,
        session_file: str,
        status: str,
        current_group: str = "",
        current_idx: int = 0,
        total_groups: int = 0,
        success_count: int = 0,
        fail_count: int = 0,
        step_msg: str = "",
        spoof_info: str = "",
        delay_sec: float = 0.0
    ):
        """Perbarui status individual worker akun."""
        with self._lock:
            now = time.time()
            
            prev_worker = self.workers.get(worker_tag, {})
            prev_success = prev_worker.get("success_count", 0)
            prev_fail = prev_worker.get("fail_count", 0)
            
            worker_data = {
                "worker_tag": worker_tag,
                "account_name": account_name or worker_tag,
                "session_file": session_file,
                "status": status,  # INITIALIZING, CHECKING_LOGIN, PROCESSING, WAITING_DELAY, SUCCESS, FAILED, COMPLETED, EXPIRED
                "current_group": current_group,
                "current_idx": current_idx,
                "total_groups": total_groups,
                "success_count": success_count,
                "fail_count": fail_count,
                "progress_percent": round((current_idx / total_groups * 100), 1) if total_groups > 0 else 0.0,
                "step_msg": step_msg,
                "spoof_info": spoof_info,
                "delay_sec": delay_sec,
                "delay_until": (now + delay_sec) if delay_sec > 0 else 0.0,
                "last_update_time": now
            }
            
            self.workers[worker_tag] = worker_data
            
            # Hitung rekap statistik global
            tot_proc = 0
            tot_succ = 0
            tot_fail = 0
            active_cnt = 0
            
            for w in self.workers.values():
                tot_proc += w.get("current_idx", 0)
                tot_succ += w.get("success_count", 0)
                tot_fail += w.get("fail_count", 0)
                if w.get("status") in ["INITIALIZING", "CHECKING_LOGIN", "PROCESSING", "WAITING_DELAY"]:
                    active_cnt += 1

            self.total_groups_processed = tot_proc
            self.total_success = tot_succ
            self.total_fail = tot_fail
            self.active_workers_count = active_cnt
            
            # Catat event baru jika ada perubahan sukses/gagal atau status penting
            if success_count > prev_success:
                self.add_event(worker_tag, "SUCCESS", f"Post/Join Berhasil di {current_group}")
            elif fail_count > prev_fail:
                self.add_event(worker_tag, "FAIL", f"Gagal di {current_group}: {step_msg}")
            elif status == "EXPIRED":
                self.add_event(worker_tag, "EXPIRED", "Sesi login kedaluwarsa / checkpoint.")
            elif status == "COMPLETED":
                self.add_event(worker_tag, "COMPLETED", f"Worker selesai ({success_count} sukses, {fail_count} gagal)")

    def add_event(self, worker_tag: str, event_type: str, message: str):
        """Tambahkan event log aktivitas baru ke event stream."""
        with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            event_obj = {
                "timestamp": ts,
                "worker_tag": worker_tag,
                "type": event_type,  # START, SUCCESS, FAIL, DELAY, EXPIRED, COMPLETED, SYSTEM
                "message": message
            }
            self.recent_events.insert(0, event_obj)
            if len(self.recent_events) > self.max_events:
                self.recent_events.pop()

    def mark_completed(self, status_msg: str = "COMPLETED"):
        """Tandai seluruh sesi otomasi telah selesai."""
        with self._lock:
            self.is_running = False
            self.end_time = time.time()
            self.active_workers_count = 0
            self.add_event("SYSTEM", "END", f"Seluruh proses otomasi {status_msg}")

    def get_live_status(self) -> Dict[str, Any]:
        """Ambil snapshot data live status terstruktur untuk API / Web UI."""
        with self._lock:
            now = time.time()
            elapsed_sec = 0.0
            if self.start_time:
                if self.is_running:
                    elapsed_sec = round(now - self.start_time, 1)
                elif self.end_time:
                    elapsed_sec = round(self.end_time - self.start_time, 1)
                    
            overall_percent = 0.0
            if self.total_groups_target > 0:
                overall_percent = min(100.0, round((self.total_groups_processed / self.total_groups_target) * 100, 1))

            # Hitung Estimasi Sisa Waktu (ETA)
            eta_sec = 0
            if self.is_running and overall_percent > 0 and elapsed_sec > 0:
                total_est_sec = (elapsed_sec / overall_percent) * 100
                eta_sec = max(0, int(total_est_sec - elapsed_sec))

            # Update delay_remaining per worker
            workers_list = []
            for wtag, wdata in self.workers.items():
                w_copy = dict(wdata)
                delay_until = w_copy.get("delay_until", 0.0)
                if delay_until > now:
                    w_copy["delay_remaining"] = round(delay_until - now, 1)
                else:
                    w_copy["delay_remaining"] = 0.0
                workers_list.append(w_copy)

            return {
                "is_running": self.is_running,
                "mode": self.mode,
                "mode_text": self.mode_text,
                "start_time": self.start_time,
                "elapsed_sec": elapsed_sec,
                "eta_sec": eta_sec,
                "total_accounts": self.total_accounts,
                "total_groups_target": self.total_groups_target,
                "total_groups_processed": self.total_groups_processed,
                "total_success": self.total_success,
                "total_fail": self.total_fail,
                "active_workers_count": self.active_workers_count,
                "overall_percent": overall_percent,
                "workers": workers_list,
                "recent_events": self.recent_events[:30]
            }


# Singleton global instance
live_monitor = LiveMonitorManager()
