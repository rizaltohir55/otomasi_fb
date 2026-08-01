/* ==========================================================================
   FB AUTOENGINE 3.0 ULTRA - FRONTEND LOGIC & REAL-TIME LIVE MONITOR
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  // Navigation & Tab Controller
  initNavigation();

  // Data Loading & API Initializers
  loadStats();
  loadSessions();
  loadGroups();
  loadCaption();
  loadMedia();
  loadConfig();

  // Connect Real-Time SSE Log Stream & Live Monitor
  initLogStream();
  initLiveMonitor();

  // Attach Event Handlers
  initEventHandlers();

  // Auto Refresh Stats every 5 seconds
  setInterval(loadStats, 5000);
});


// ── 1. NAVIGATION & TAB CONTROLLER ───────────────────────────────────────────
const tabMeta = {
  "tab-dashboard": { title: "Dashboard Overview", sub: "Ringkasan status sistem dan performa akun Facebook" },
  "tab-sessions":  { title: "Manajemen Akun Facebook", sub: "Kelola file sesi, login interaktif, dan status keaktifan cookie" },
  "tab-groups":    { title: "Daftar Grup Target", sub: "Kelola daftar link grup target postingan (groups.txt)" },
  "tab-poster":    { title: "AutoPost Runner Controller", sub: "Konfigurasi parameter dan jalankan otomasi postingan multi-akun" },
  "tab-monitor":   { title: "Real-Time Live Monitor", sub: "Visualisasi status real-time, progress master, dan status worker per akun" },
  "tab-logs":      { title: "Live Console Terminal", sub: "Streaming log aktivitas Playwright dan worker secara real-time" },
  "tab-settings":  { title: "Pengaturan Sistem", sub: "Konfigurasi jeda waktu, batas worker, dan profil stealth" }
};

function initNavigation() {
  const navButtons = document.querySelectorAll(".nav-btn");
  const tabViews = document.querySelectorAll(".tab-view");

  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchToTab(targetTab);
    });
  });
}

function switchToTab(targetTab) {
  const navButtons = document.querySelectorAll(".nav-btn");
  const tabViews = document.querySelectorAll(".tab-view");
  const headerTitle = document.getElementById("header-title");
  const headerSubtitle = document.getElementById("header-subtitle");

  navButtons.forEach(b => b.classList.remove("active"));
  tabViews.forEach(v => v.classList.remove("active"));

  const targetBtn = document.querySelector(`.nav-btn[data-tab="${targetTab}"]`);
  if (targetBtn) targetBtn.classList.add("active");

  const activeView = document.getElementById(targetTab);
  if (activeView) activeView.classList.add("active");

  if (tabMeta[targetTab]) {
    headerTitle.textContent = tabMeta[targetTab].title;
    headerSubtitle.textContent = tabMeta[targetTab].sub;
  }
}


// ── Toast Notification System ────────────────────────────────────────────────
function showToast(message, type = "info", duration = 3500) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  let icon = "fa-circle-info";
  if (type === "success") icon = "fa-circle-check";
  else if (type === "error") icon = "fa-circle-xmark";
  else if (type === "warning") icon = "fa-triangle-exclamation";

  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <span>${message}</span>
    <button class="toast-close">&times;</button>
  `;

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 400);
  }, duration);
}


// ── 2. DATA LOADERS ───────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const json = await res.json();
    if (json.status === "success") {
      const d = json.data;
      document.getElementById("stat-total-accounts").textContent = d.total_accounts;
      document.getElementById("stat-total-groups").textContent = d.total_groups;
      document.getElementById("stat-total-media").textContent = d.total_media;
      document.getElementById("stat-runner-status").textContent = d.runner_status;

      document.getElementById("badge-account-count").textContent = d.total_accounts;
      document.getElementById("badge-group-count").textContent = d.total_groups;

      const statusPill = document.getElementById("status-pill");
      const statusText = document.getElementById("status-text");
      const btnStart = document.getElementById("btn-start-automation");
      const btnStop = document.getElementById("btn-stop-automation");
      const floatingBar = document.getElementById("floating-runner-bar");

      if (d.is_running) {
        statusPill.classList.add("running");
        statusText.textContent = `RUNNING (${d.active_workers} WORKERS)`;
        if (btnStart) btnStart.classList.add("hidden");
        if (btnStop) btnStop.classList.remove("hidden");
        if (floatingBar) floatingBar.classList.remove("hidden");
      } else {
        statusPill.classList.remove("running");
        statusText.textContent = "IDLE / SIAP";
        if (btnStart) btnStart.classList.remove("hidden");
        if (btnStop) btnStop.classList.add("hidden");
        if (floatingBar) floatingBar.classList.add("hidden");
      }
    }
  } catch (err) {
    console.error("Gagal memuat stats:", err);
  }
}


// Cache untuk menyimpan hasil verifikasi status akun (path -> {status, message})
let _verifyStatusCache = {};

function getStatusBadgeHTML(status) {
  if (!status) return '';
  const map = {
    ACTIVE:      { cls: 'live',       icon: 'fa-circle-check',  label: '✅ AKTIF' },
    CHECKPOINT:  { cls: 'checkpoint', icon: 'fa-triangle-exclamation', label: '⚠️ CHECKPOINT' },
    RESTRICTED:  { cls: 'restricted', icon: 'fa-ban',           label: '⛔ DIBATASI FB' },
    EXPIRED:     { cls: 'expired',    icon: 'fa-circle-xmark',  label: '❌ KEDALUWARSA' },
    INVALID:     { cls: 'expired',    icon: 'fa-circle-xmark',  label: '❌ INVALID' },
  };
  const info = map[status] || { cls: 'unknown', icon: 'fa-question', label: status };
  return `<span class="acc-status-badge ${info.cls}"><i class="fa-solid ${info.icon}"></i> ${info.label}</span>`;
}

async function loadSessions(statusMap = null) {
  const container = document.getElementById("sessions-container");
  const checkboxContainer = document.getElementById("custom-acc-checkboxes");
  // Merge status cache jika ada data baru dari verify-all
  if (statusMap) Object.assign(_verifyStatusCache, statusMap);
  
  try {
    const res = await fetch("/api/sessions");
    const json = await res.json();
    
    if (json.status === "success") {
      const sessions = json.sessions;
      
      if (!sessions || sessions.length === 0) {
        container.innerHTML = `
          <div class="card-panel" style="grid-column: 1/-1; text-align: center; padding: 40px;">
            <i class="fa-solid fa-folder-open" style="font-size: 48px; color: var(--text-dim); margin-bottom: 12px;"></i>
            <h3>Belum Ada Akun Facebook Tersimpan</h3>
            <p class="text-muted" style="margin-top: 6px;">Klik tombol "Login Akun Baru" di atas untuk menambahkan akun pertama Anda.</p>
          </div>
        `;
        if (checkboxContainer) checkboxContainer.innerHTML = "<p class='text-muted'>Belum ada akun.</p>";
        return;
      }

      // Render Account Cards
      container.innerHTML = sessions.map(s => {
        const name = s.name || "Akun Facebook";
        const c_user = s.c_user || "Unknown";
        const filename = s.path ? s.path.split(/[\\/]/).pop() : "";
        const cachedStatus = _verifyStatusCache[s.path];
        const badgeHTML = cachedStatus ? getStatusBadgeHTML(cachedStatus.status) : '';
        const statusMsg = cachedStatus ? `<small style="color:var(--text-dim);display:block;margin-top:4px;">${cachedStatus.message}</small>` : '';
        
        return `
          <div class="account-card" data-path="${s.path}" id="acc-card-${c_user}">
            <div class="acc-header">
              <div class="acc-avatar">${name.charAt(0).toUpperCase()}</div>
              <div class="acc-details">
                <h4>${name}</h4>
                <code>ID: ${c_user}</code>
                ${badgeHTML}
                ${statusMsg}
              </div>
            </div>
            <div class="acc-path" title="${s.path}">${filename}</div>
            <div class="acc-actions">
              <button class="btn btn-sm btn-outline btn-verify-acc" data-path="${s.path}" data-cuser="${c_user}"><i class="fa-solid fa-shield-cat"></i> Cek Status</button>
              <button class="btn btn-sm btn-outline btn-relogin-acc" data-path="${s.path}"><i class="fa-solid fa-arrows-rotate"></i> Relogin</button>
              <button class="btn btn-sm btn-outline btn-rename-acc" data-path="${s.path}" data-name="${name}"><i class="fa-solid fa-pen"></i></button>
              <button class="btn btn-sm btn-danger btn-delete-acc" data-path="${s.path}"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>
        `;
      }).join("");

      // Render Custom Account Checkboxes for Poster tab
      if (checkboxContainer) {
        checkboxContainer.innerHTML = sessions.map((s, idx) => `
          <label class="checkbox-label" style="margin-bottom: 8px;">
            <input type="checkbox" name="selected-acc" value="${s.path}" checked>
            <span>👤 ${s.name || "Akun"} (ID: ${s.c_user})</span>
          </label>
        `).join("");
      }

      attachAccountCardListeners();
    }
  } catch (err) {
    console.error("Gagal memuat sesi:", err);
  }
}

async function loadGroups() {
  const textarea = document.getElementById("groups-textarea");
  try {
    const res = await fetch("/api/groups");
    const json = await res.json();
    if (json.status === "success") {
      textarea.value = json.raw_content || json.groups.join("\n");
      updateGroupsCount();
    }
  } catch (err) {
    console.error("Gagal memuat grup:", err);
  }
}

function updateGroupsCount() {
  const textarea = document.getElementById("groups-textarea");
  const countLabel = document.getElementById("groups-line-count");
  if (!textarea || !countLabel) return;
  const lines = textarea.value.split("\n").filter(l => l.trim());
  countLabel.textContent = `${lines.length} link grup terdeteksi`;
}

async function loadCaption() {
  const textarea = document.getElementById("post-caption-textarea");
  try {
    const res = await fetch("/api/caption");
    const json = await res.json();
    if (json.status === "success" && textarea) {
      textarea.value = json.caption;
    }
  } catch (err) {
    console.error("Gagal memuat caption:", err);
  }
}

async function loadMedia() {
  const container = document.getElementById("media-gallery");
  try {
    const res = await fetch("/api/media");
    const json = await res.json();
    if (json.status === "success" && container) {
      const items = json.media;
      if (!items || items.length === 0) {
        container.innerHTML = "<p class='text-muted' style='grid-column: 1/-1;'>Belum ada media foto/video diunggah.</p>";
        return;
      }

      container.innerHTML = items.map(m => `
        <div class="media-thumb" title="${m.name}">
          <img src="${m.url}" alt="${m.name}">
          <button class="media-thumb-del" data-filename="${m.name}">&times;</button>
        </div>
      `).join("");

      document.querySelectorAll(".media-thumb-del").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const fname = btn.getAttribute("data-filename");
          await fetch(`/api/media?filename=${encodeURIComponent(fname)}`, { method: "DELETE" });
          loadMedia();
          loadStats();
        });
      });
    }
  } catch (err) {
    console.error("Gagal memuat media:", err);
  }
}

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const json = await res.json();
    if (json.status === "success") {
      const cfg = json.config;
      document.getElementById("cfg-delay-min").value = cfg.delay_min;
      document.getElementById("cfg-delay-max").value = cfg.delay_max;
      document.getElementById("cfg-max-workers").value = cfg.max_workers;
      document.getElementById("cfg-headless").value = String(cfg.default_headless);
      document.getElementById("cfg-auto-like").checked = cfg.auto_like;
      document.getElementById("cfg-auto-comment").checked = cfg.auto_comment;
    }
  } catch (err) {
    console.error("Gagal memuat konfigurasi:", err);
  }
}


// ── 3. REAL-TIME LIVE MONITOR CONTROLLER ────────────────────────────────────
function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return "00:00";
  const s = Math.floor(seconds);
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hrs > 0) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function initLiveMonitor() {
  const btnMonStop = document.getElementById("btn-mon-stop");
  const btnMonTerminal = document.getElementById("btn-mon-goto-terminal");

  if (btnMonStop) {
    btnMonStop.addEventListener("click", async () => {
      if (confirm("Apakah Anda yakin ingin menghentikan eksekusi otomasi?")) {
        const res = await fetch("/api/runner/stop", { method: "POST" });
        const json = await res.json();
        alert(json.message);
      }
    });
  }

  if (btnMonTerminal) {
    btnMonTerminal.addEventListener("click", () => {
      switchToTab("tab-logs");
    });
  }

  // Poll live status every 1 second
  setInterval(pollLiveStatus, 1000);
}

async function pollLiveStatus() {
  try {
    const res = await fetch("/api/runner/live-status");
    const json = await res.json();
    if (json.status === "success") {
      renderLiveMonitor(json.data);
    }
  } catch (err) {
    // Silent fetch error
  }
}

function renderLiveMonitor(d) {
  const badgeLive = document.getElementById("badge-live-monitor");
  const statusPill = document.getElementById("mon-live-status-pill");
  const statusText = document.getElementById("mon-live-status-text");
  const modeTag = document.getElementById("mon-mode-tag");
  const masterPercent = document.getElementById("mon-master-percent-text");
  const masterFill = document.getElementById("mon-master-progress-fill");
  const processedText = document.getElementById("mon-processed-text");
  const elapsedText = document.getElementById("mon-elapsed-text");
  const etaText = document.getElementById("mon-eta-text");

  // KPI elements
  const statTarget = document.getElementById("mon-stat-target");
  const statSuccess = document.getElementById("mon-stat-success");
  const statFail = document.getElementById("mon-stat-fail");
  const statWorkers = document.getElementById("mon-stat-workers");

  // Containers
  const workersContainer = document.getElementById("mon-workers-container");
  const activityStream = document.getElementById("mon-activity-stream");

  // Badge sidebar
  if (badgeLive) {
    if (d.is_running) badgeLive.classList.remove("hidden");
    else badgeLive.classList.add("hidden");
  }

  // Header status pill
  if (statusPill && statusText) {
    statusPill.className = "live-pill";
    if (d.is_running) {
      statusPill.classList.add("running");
      statusText.textContent = `RUNNING (${d.active_workers_count} WORKERS)`;
    } else if (d.total_groups_processed > 0 && d.total_groups_processed >= d.total_groups_target) {
      statusPill.classList.add("completed");
      statusText.textContent = "COMPLETED / SELESAI";
    } else {
      statusPill.classList.add("idle");
      statusText.textContent = "IDLE / SIAP";
    }
  }

  if (modeTag) modeTag.textContent = d.mode_text || "Auto Post ke Grup";

  // Progress calculations
  const pct = d.overall_percent || 0.0;
  if (masterPercent) masterPercent.textContent = `${pct.toFixed(1)}%`;
  if (masterFill) masterFill.style.width = `${pct}%`;
  if (processedText) processedText.textContent = `${d.total_groups_processed} / ${d.total_groups_target} Grup`;
  if (elapsedText) elapsedText.textContent = formatTime(d.elapsed_sec);
  if (etaText) etaText.textContent = d.is_running ? formatTime(d.eta_sec) : "--:--";

  // KPI stats
  if (statTarget) statTarget.textContent = d.total_groups_target;
  if (statSuccess) statSuccess.textContent = d.total_success;
  if (statFail) statFail.textContent = d.total_fail;
  if (statWorkers) statWorkers.textContent = d.active_workers_count;

  // Render Worker Cards
  if (workersContainer) {
    const workers = d.workers || [];
    if (workers.length === 0) {
      workersContainer.innerHTML = `
        <div class="empty-monitor-notice">
          <i class="fa-solid fa-gauge-simple-high"></i>
          <p>Belum ada otomasi yang sedang berjalan. Jalankan otomasi untuk melihat monitor status real-time.</p>
        </div>
      `;
    } else {
      workersContainer.innerHTML = workers.map(w => {
        const name = w.account_name || "Akun Facebook";
        const initial = name.charAt(0).toUpperCase();
        const statusStr = (w.status || "IDLE").toLowerCase();
        const currGrp = w.current_group || "";
        const grpDisplay = currGrp ? `<a href="${currGrp}" target="_blank" rel="noopener">${currGrp}</a>` : "Belum memilih grup";
        const delayRem = w.delay_remaining || 0.0;
        
        let cardClass = "worker-live-card";
        if (statusStr === "processing") cardClass += " active";
        else if (statusStr === "waiting_delay") cardClass += " waiting";
        else if (statusStr === "completed") cardClass += " completed";
        else if (statusStr === "expired") cardClass += " expired";

        return `
          <div class="${cardClass}">
            <div class="worker-card-header">
              <div class="worker-identity">
                <div class="worker-avatar">${initial}</div>
                <div class="worker-info">
                  <h5>${name}</h5>
                  <span class="worker-tag-badge">${w.worker_tag}</span>
                </div>
              </div>
              <span class="worker-status-tag ${statusStr}">${w.status}</span>
            </div>

            <div class="worker-spoof-pill" title="Hardware Fingerprint Spoofed">
              <i class="fa-solid fa-microchip"></i> ${w.spoof_info || "Hardware Spoofed"}
            </div>

            <div class="worker-mini-progress">
              <div class="mini-progress-text">
                <span>Progress Akun</span>
                <span>${w.current_idx} / ${w.total_groups} (${w.progress_percent || 0}%)</span>
              </div>
              <div class="mini-progress-bar">
                <div class="mini-progress-fill" style="width: ${w.progress_percent || 0}%;"></div>
              </div>
            </div>

            <div class="worker-target-group">
              <small style="display:block; color:var(--text-dim); margin-bottom:2px;">Grup Target Aktif:</small>
              ${grpDisplay}
            </div>

            ${delayRem > 0 ? `
              <div class="worker-delay-timer">
                <i class="fa-solid fa-hourglass-half fa-spin"></i> Jeda Emulasi Manusia: ${delayRem.toFixed(1)}s
              </div>
            ` : ""}

            <div class="worker-last-action">
              💬 ${w.step_msg || "Menunggu aksi selanjutnya..."}
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // Render Activity Stream Log
  if (activityStream) {
    const events = d.recent_events || [];
    if (events.length === 0) {
      activityStream.innerHTML = `
        <div class="stream-line system">
          <span class="stream-time">[--:--:--]</span>
          <span class="stream-msg">System Live Monitor Siap. Menunggu eksekusi worker...</span>
        </div>
      `;
    } else {
      activityStream.innerHTML = events.map(e => {
        const typeClass = (e.type || "system").toLowerCase();
        return `
          <div class="stream-line ${typeClass}">
            <span class="stream-time">[${e.timestamp}]</span>
            <span class="stream-msg"><strong>[${e.worker_tag}]</strong> ${e.message}</span>
          </div>
        `;
      }).join("");
    }
  }
}


// ── 4. LOG TERMINAL SSE STREAM ───────────────────────────────────────────────
function initLogStream() {
  const terminalOutput = document.getElementById("terminal-output");
  const autoscrollToggle = document.getElementById("autoscroll-toggle");

  const evtSource = new EventSource("/api/runner/stream-logs");

  evtSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data && data.message) {
        appendLogLine(data.message);
      }
    } catch (e) {
      appendLogLine(event.data);
    }
  };

  function appendLogLine(msg) {
    if (!terminalOutput) return;
    
    let lineClass = "info";
    if (msg.includes("❌") || msg.includes("Gagal") || msg.includes("Error")) lineClass = "error";
    else if (msg.includes("🎉") || msg.includes("✅") || msg.includes("Sukses")) lineClass = "success";
    else if (msg.includes("⚠️") || msg.includes("⏳") || msg.includes("Jeda")) lineClass = "warning";

    const div = document.createElement("div");
    div.className = `log-line ${lineClass}`;
    div.textContent = msg;
    terminalOutput.appendChild(div);

    if (autoscrollToggle && autoscrollToggle.checked) {
      terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
  }
}


// ── 5. EVENT HANDLERS & MODALS ──────────────────────────────────────────────
function initEventHandlers() {
  // Quick Actions in Dashboard
  const btnQuickAll = document.getElementById("btn-quick-run-all");
  const btnQuickCollect = document.getElementById("btn-quick-collect");
  const btnQuickStart = document.getElementById("btn-quick-start");
  const btnBarMonitor = document.getElementById("btn-bar-goto-monitor");
  const btnBarTerminal = document.getElementById("btn-bar-goto-terminal");

  if (btnQuickAll) btnQuickAll.addEventListener("click", () => startAutomationRun(true));
  if (btnQuickCollect) btnQuickCollect.addEventListener("click", triggerCollectGroups);
  if (btnQuickStart) btnQuickStart.addEventListener("click", () => startAutomationRun(true));

  if (btnBarMonitor) btnBarMonitor.addEventListener("click", () => switchToTab("tab-monitor"));
  if (btnBarTerminal) btnBarTerminal.addEventListener("click", () => switchToTab("tab-logs"));

  // Batch Verify All Accounts
  const btnVerifyAll = document.getElementById("btn-verify-all-acc");
  if (btnVerifyAll) {
    btnVerifyAll.addEventListener("click", async () => {
      btnVerifyAll.disabled = true;
      btnVerifyAll.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Memeriksa Semua Akun...';
      showToast("🔍 Memeriksa live status seluruh akun...", "info");
      
      try {
        const res = await fetch("/api/sessions/verify-all", { method: "POST" });
        const json = await res.json();
        if (json.status === "success") {
          // Build status map dari hasil verifikasi
          const statusMap = {};
          json.results.forEach(r => { statusMap[r.path] = { status: r.status, message: r.message }; });
          
          // Hitung statistik
          const activeCount    = json.results.filter(r => r.status === 'ACTIVE').length;
          const expiredCount   = json.results.filter(r => r.status === 'EXPIRED').length;
          const restrictedCount= json.results.filter(r => r.status === 'RESTRICTED').length;
          const checkpointCount= json.results.filter(r => r.status === 'CHECKPOINT').length;

          // Render kartu akun dengan status badge
          await loadSessions(statusMap);
          attachAccountCardListeners();

          // Tampilkan ringkasan via toast
          const summary = `✅ ${activeCount} Aktif | ❌ ${expiredCount} Expired | ⛔ ${restrictedCount} Dibatasi | ⚠️ ${checkpointCount} Checkpoint`;
          showToast(`Verifikasi Selesai — ${summary}`, activeCount === json.results.length ? 'success' : 'warning', 7000);
        }
      } catch (err) {
        showToast("❌ Gagal memverifikasi status akun: " + err.message, "error");
      } finally {
        btnVerifyAll.disabled = false;
        btnVerifyAll.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Cek Status Login';
      }
    });
  }

  // Cek Kemampuan Posting (Deep Check via Playwright)
  const btnCheckPosting = document.getElementById("btn-check-posting");
  if (btnCheckPosting) {
    btnCheckPosting.addEventListener("click", async () => {
      btnCheckPosting.disabled = true;
      btnCheckPosting.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Memeriksa Posting... (Mohon Tunggu)';
      showToast("🔬 Memeriksa kemampuan posting ke grup... Ini mungkin memakan 1-2 menit.", "info", 8000);

      try {
        const res = await fetch("/api/sessions/check-posting", { method: "POST" });
        const json = await res.json();
        if (res.ok && json.status === "success") {
          // Build status map dari hasil cek posting
          const statusMap = {};
          json.results.forEach(r => { statusMap[r.path] = { status: r.status, message: r.message }; });

          // Hitung statistik
          const activeCount     = json.results.filter(r => r.status === 'ACTIVE').length;
          const restrictedCount = json.results.filter(r => r.status === 'RESTRICTED').length;
          const expiredCount    = json.results.filter(r => r.status === 'EXPIRED').length;

          // Render kartu akun dengan status badge
          await loadSessions(statusMap);
          attachAccountCardListeners();

          // Toast ringkasan
          const toastType = restrictedCount > 0 ? 'warning' : 'success';
          const summary = `✅ ${activeCount} Bisa Posting | ⛔ ${restrictedCount} Dibatasi FB | ❌ ${expiredCount} Expired`;
          showToast(`Cek Posting Selesai — ${summary}`, toastType, 8000);
        } else {
          showToast("❌ Gagal cek kemampuan posting: " + (json.message || json.detail || "Server error"), "error");
        }
      } catch (err) {
        showToast("❌ Gagal cek kemampuan posting: " + err.message, "error");
      } finally {
        btnCheckPosting.disabled = false;
        btnCheckPosting.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Cek Kemampuan Posting';
      }
    });
  }

  // Groups Editor & Clean Duplicates
  const btnSaveGroups = document.getElementById("btn-save-groups");
  const btnCleanGroups = document.getElementById("btn-clean-groups");
  const btnTriggerCollect = document.getElementById("btn-trigger-collect");
  const groupsTextarea = document.getElementById("groups-textarea");

  if (btnSaveGroups) {
    btnSaveGroups.addEventListener("click", async () => {
      const lines = groupsTextarea.value.split("\n");
      const res = await fetch("/api/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groups: lines })
      });
      const json = await res.json();
      showToast(json.message, "success");
      loadStats();
    });
  }

  if (btnCleanGroups) {
    btnCleanGroups.addEventListener("click", async () => {
      const res = await fetch("/api/groups/clean", { method: "POST" });
      const json = await res.json();
      if (json.status === "success") {
        groupsTextarea.value = json.raw_content;
        updateGroupsCount();
        showToast(`🧹 Pembersihan Selesai: ${json.message}`, "success");
        loadStats();
      }
    });
  }

  if (btnTriggerCollect) btnTriggerCollect.addEventListener("click", triggerCollectGroups);
  if (groupsTextarea) groupsTextarea.addEventListener("input", updateGroupsCount);

  // Caption Save
  const btnSaveCaption = document.getElementById("btn-save-caption");
  if (btnSaveCaption) {
    btnSaveCaption.addEventListener("click", async () => {
      const text = document.getElementById("post-caption-textarea").value;
      const res = await fetch("/api/caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caption: text })
      });
      const json = await res.json();
      showToast(json.message, "success");
    });
  }

  // Media Upload
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("media-file-input");
  if (uploadZone && fileInput) {
    uploadZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      if (fileInput.files.length > 0) {
        for (let i = 0; i < fileInput.files.length; i++) {
          const formData = new FormData();
          formData.append("file", fileInput.files[i]);
          await fetch("/api/media/upload", { method: "POST", body: formData });
        }
        showToast(`🖼️ ${fileInput.files.length} media berhasil diunggah!`, "success");
        loadMedia();
        loadStats();
      }
    });
  }


  // Account Mode Toggle in Poster
  const accModeRadios = document.querySelectorAll('input[name="acc-mode"]');
  const customAccBox = document.getElementById("custom-acc-checkboxes");
  accModeRadios.forEach(r => {
    r.addEventListener("change", () => {
      if (r.value === "custom") {
        customAccBox.classList.remove("hidden");
      } else {
        customAccBox.classList.add("hidden");
      }
    });
  });

  // Start Automation Execution
  const btnStartAutomation = document.getElementById("btn-start-automation");
  if (btnStartAutomation) {
    btnStartAutomation.addEventListener("click", () => {
      startAutomationRun(false);
    });
  }

  // Stop Automation Execution
  const btnStopAutomation = document.getElementById("btn-stop-automation");
  if (btnStopAutomation) {
    btnStopAutomation.addEventListener("click", async () => {
      if (confirm("Apakah Anda yakin ingin menghentikan seluruh proses otomasi?")) {
        const res = await fetch("/api/runner/stop", { method: "POST" });
        const json = await res.json();
        alert(json.message);
      }
    });
  }

  // Clear Logs
  const btnClearLogs = document.getElementById("btn-clear-logs");
  if (btnClearLogs) {
    btnClearLogs.addEventListener("click", () => {
      document.getElementById("terminal-output").innerHTML = '<div class="log-line info">[System] Log dibersihkan.</div>';
    });
  }

  // Account CRUD buttons
  const btnAddAccount = document.getElementById("btn-add-account");
  if (btnAddAccount) {
    btnAddAccount.addEventListener("click", async () => {
      const tag = prompt("Masukkan nama panggil alias untuk akun baru ini:", "Akun_Baru");
      if (tag === null) return;
      const res = await fetch(`/api/sessions/login-new?tag=${encodeURIComponent(tag)}`, { method: "POST" });
      const json = await res.json();
      alert(json.message);
      switchToTab("tab-logs");
    });
  }

  const btnImportSession = document.getElementById("btn-import-session");
  if (btnImportSession) {
    btnImportSession.addEventListener("click", () => {
      openModal("modal-import");
    });
  }

  const btnSubmitImport = document.getElementById("btn-submit-import");
  if (btnSubmitImport) {
    btnSubmitImport.addEventListener("click", async () => {
      const name = document.getElementById("import-name-input").value;
      const jsonContent = document.getElementById("import-json-textarea").value;
      if (!jsonContent.trim()) return alert("Isi JSON cookie tidak boleh kosong.");

      const res = await fetch("/api/sessions/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || "Imported_Account", json_content: jsonContent })
      });
      const json = await res.json();
      if (res.ok) {
        alert(json.message);
        closeModal("modal-import");
        loadSessions();
        loadStats();
      } else {
        alert("Gagal mengimpor: " + json.detail);
      }
    });
  }

  // Save Settings
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        delay_min: parseFloat(document.getElementById("cfg-delay-min").value),
        delay_max: parseFloat(document.getElementById("cfg-delay-max").value),
        max_workers: parseInt(document.getElementById("cfg-max-workers").value),
        default_headless: document.getElementById("cfg-headless").value === "true",
        auto_like: document.getElementById("cfg-auto-like").checked,
        auto_comment: document.getElementById("cfg-auto-comment").checked,
        auto_comments: ["Gasken", "Ready", "Inbox", "Up", "Mantap"]
      };

      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      alert(json.message);
    });
  }

  // Close modals
  document.querySelectorAll("[data-close]").forEach(el => {
    el.addEventListener("click", () => {
      const targetId = el.getAttribute("data-close");
      closeModal(targetId);
    });
  });
}

function attachAccountCardListeners() {
  document.querySelectorAll(".btn-verify-acc").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      const cuser = btn.getAttribute("data-cuser") || "";
      const card = document.getElementById(`acc-card-${cuser}`) || btn.closest(".account-card");
      
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Memeriksa...';

      try {
        const res = await fetch("/api/sessions/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_path: path })
        });
        const json = await res.json();
        const status = json.details?.status || (json.is_live ? "ACTIVE" : "EXPIRED");
        const message = json.status_text || "";

        // Simpan ke cache
        _verifyStatusCache[path] = { status, message };

        // Update badge pada kartu akun secara langsung (tanpa reload seluruh list)
        if (card) {
          const detailsEl = card.querySelector(".acc-details");
          if (detailsEl) {
            // Hapus badge & pesan lama, tambahkan yang baru
            detailsEl.querySelectorAll(".acc-status-badge, small").forEach(el => el.remove());
            detailsEl.insertAdjacentHTML("beforeend", getStatusBadgeHTML(status));
            detailsEl.insertAdjacentHTML("beforeend", `<small style="color:var(--text-dim);display:block;margin-top:4px;">${message}</small>`);
          }
        }

        showToast(`${json.is_live ? "✅" : "❌"} ${message}`, json.is_live ? "success" : "warning");
      } catch (err) {
        showToast("❌ Gagal cek status: " + err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-shield-cat"></i> Cek Status';
      }
    });
  });


  document.querySelectorAll(".btn-relogin-acc").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      const res = await fetch("/api/sessions/relogin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_path: path })
      });
      const json = await res.json();
      alert(json.message);
      switchToTab("tab-logs");
    });
  });

  document.querySelectorAll(".btn-rename-acc").forEach(btn => {
    btn.addEventListener("click", () => {
      const path = btn.getAttribute("data-path");
      const currName = btn.getAttribute("data-name");
      document.getElementById("rename-path-input").value = path;
      document.getElementById("rename-name-input").value = currName;
      openModal("modal-rename");
    });
  });

  const btnSaveRename = document.getElementById("btn-save-rename");
  if (btnSaveRename) {
    btnSaveRename.onclick = async () => {
      const path = document.getElementById("rename-path-input").value;
      const newName = document.getElementById("rename-name-input").value;
      if (!newName.trim()) return;

      const res = await fetch("/api/sessions/rename", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_path: path, new_name: newName })
      });
      const json = await res.json();
      if (res.ok) {
        closeModal("modal-rename");
        loadSessions();
      } else {
        alert(json.detail);
      }
    };
  }

  document.querySelectorAll(".btn-delete-acc").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      if (confirm(`Apakah Anda yakin ingin menghapus sesi akun ini?\nPath: ${path}`)) {
        const res = await fetch("/api/sessions/delete", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_path: path })
        });
        const json = await res.json();
        if (res.ok) {
          loadSessions();
          loadStats();
        } else {
          alert(json.detail);
        }
      }
    });
  });
}

async function triggerCollectGroups() {
  if (confirm("Jalankan kolektor pencarian grup otomatis sekarang?")) {
    const res = await fetch("/api/groups/collect", { method: "POST" });
    const json = await res.json();
    alert(json.message);
    switchToTab("tab-logs");
  }
}

async function startAutomationRun(runAllOverride = false) {
  let selectedSessions = [];
  
  if (runAllOverride) {
    const res = await fetch("/api/sessions");
    const json = await res.json();
    selectedSessions = json.sessions.map(s => s.path);
  } else {
    const accModeEl = document.querySelector('input[name="acc-mode"]:checked');
    const accMode = accModeEl ? accModeEl.value : "all";
    if (accMode === "all") {
      const res = await fetch("/api/sessions");
      const json = await res.json();
      selectedSessions = json.sessions.map(s => s.path);
    } else {
      document.querySelectorAll('input[name="selected-acc"]:checked').forEach(cb => {
        selectedSessions.push(cb.value);
      });
    }
  }

  if (selectedSessions.length === 0) {
    return alert("Harap pilih minimal 1 akun Facebook untuk diproses.");
  }

  const payload = {
    selected_sessions: selectedSessions,
    mode: document.getElementById("runner-mode-select").value,
    start_idx: parseInt(document.getElementById("runner-start-idx").value) || 1,
    end_idx: parseInt(document.getElementById("runner-end-idx").value) || null,
    headless: document.getElementById("runner-headless-select").value === "true",
    max_workers: parseInt(document.getElementById("runner-max-workers").value) || 3,
    randomize_groups: document.getElementById("runner-randomize-groups").checked,
    custom_caption: document.getElementById("post-caption-textarea").value
  };

  const res = await fetch("/api/runner/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const json = await res.json();
  if (res.ok) {
    showToast("🚀 Otomasi dimulai! Beralih ke Live Monitor...", "success");
    await loadStats();
    switchToTab("tab-monitor");
  } else {
    showToast("❌ Gagal memulai otomasi: " + (json.detail || json.message || "Unknown error"), "error");
  }
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}

