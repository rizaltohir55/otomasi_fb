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
  loadSkipList();
  loadCooldown();

  // Connect Real-Time SSE Log Stream & Live Monitor
  initLogStream();
  initLiveMonitor();

  // Attach Event Handlers
  initEventHandlers();

  // Auto Refresh Stats every 5 seconds
  setInterval(loadStats, 5000);
  // Refresh skip-list & cooldown every 10 seconds
  setInterval(loadSkipList, 10000);
  setInterval(loadCooldown, 10000);

  // Global error handlers
  window.addEventListener("unhandledrejection", (e) => {
    console.error("Unhandled promise rejection:", e.reason);
    showToast("Terjadi error tidak terduga: " + (e.reason?.message || e.reason), "error", 5000);
  });
  window.addEventListener("error", (e) => {
    console.error("Global error:", e.error);
    showToast("Error: " + e.message, "error", 5000);
  });

  // beforeunload guard when automation is running
  window.addEventListener("beforeunload", (e) => {
    if (window._isAutomationRunning) {
      e.preventDefault();
      e.returnValue = "Otomasi sedang berjalan. Yakin ingin meninggalkan halaman?";
      return e.returnValue;
    }
  });

  // ESC key to close modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay:not(.hidden)").forEach(m => {
        m.classList.add("hidden");
      });
    }
  });

  // Click on modal overlay (outside card) to close
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.add("hidden");
      }
    });
  });
});


// ── 0. UTILITIES ──────────────────────────────────────────────────────────────

/**
 * Escape HTML special characters in a string to prevent XSS via innerHTML.
 * Use this for ANY value sourced from the server (account name, group URL, step_msg, etc.)
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Safe attribute escape (for href, data-*, etc.)
 */
function escapeAttr(str) {
  return escapeHtml(str);
}

/**
 * Wrapper around fetch() that:
 * - Always returns {ok, json, status} tuple
 * - Catches network errors
 * - Handles non-JSON responses gracefully
 * - Never throws (caller checks .ok)
 */
async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    let json = null;
    try {
      json = await res.json();
    } catch (e) {
      // Response is not JSON (e.g., HTML error page from proxy)
      json = { status: "error", message: `HTTP ${res.status}: respons bukan JSON` };
    }
    return { ok: res.ok, status: res.status, json };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      json: { status: "error", message: `Network error: ${err.message}` }
    };
  }
}

/**
 * Extract human-readable error message from API response.
 * Backend success: {status, message}; FastAPI error: {detail}; others: fallback.
 */
function getApiError(json) {
  if (!json) return "Unknown error";
  return json.detail || json.message || json.error || "Operasi gagal";
}


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
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "polite");

  let icon = "fa-circle-info";
  if (type === "success") icon = "fa-circle-check";
  else if (type === "error") icon = "fa-circle-xmark";
  else if (type === "warning") icon = "fa-triangle-exclamation";

  // Escape message to prevent XSS — message can contain server-controlled text
  toast.innerHTML = `
    <i class="fa-solid ${icon}" aria-hidden="true"></i>
    <span>${escapeHtml(message)}</span>
    <button class="toast-close" aria-label="Tutup notifikasi">&times;</button>
  `;

  let fadeTimer = null;
  toast.querySelector(".toast-close").addEventListener("click", () => {
    if (fadeTimer) clearTimeout(fadeTimer);
    toast.remove();
  });

  container.appendChild(toast);

  fadeTimer = setTimeout(() => {
    toast.classList.add("fade-out");
    fadeTimer = setTimeout(() => toast.remove(), 400);
  }, duration);
}


// ── 2. DATA LOADERS ───────────────────────────────────────────────────────────
async function loadStats() {
  const { ok, json } = await apiFetch("/api/stats");
  if (!ok || json.status !== "success") {
    console.error("Gagal memuat stats:", getApiError(json));
    return;
  }
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

  // Track running state for beforeunload guard
  window._isAutomationRunning = !!d.is_running;

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

  const { ok, json } = await apiFetch("/api/sessions");
  if (!ok || json.status !== "success") {
    // Show error state instead of infinite spinner
    if (container) {
      container.innerHTML = `
        <div class="card-panel" style="grid-column: 1/-1; text-align: center; padding: 40px;">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 48px; color: var(--danger); margin-bottom: 12px;"></i>
          <h3>Gagal Memuat Daftar Akun</h3>
          <p class="text-muted" style="margin-top: 6px;">${escapeHtml(getApiError(json))}</p>
          <button class="btn btn-primary" style="margin-top: 12px;" onclick="loadSessions()"><i class="fa-solid fa-rotate"></i> Coba Lagi</button>
        </div>
      `;
    }
    return;
  }

  const sessions = json.sessions || [];

  if (sessions.length === 0) {
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

  // Render Account Cards — ALL server fields escaped
  container.innerHTML = sessions.map(s => {
    const rawName = s.name || "Akun Facebook";
    const initial = rawName.charAt(0).toUpperCase();
    const name = escapeHtml(rawName);
    const c_user = escapeHtml(s.c_user || "Unknown");
    const path = escapeAttr(s.path || "");
    const filename = escapeHtml(s.path ? s.path.split(/[\\/]/).pop() : "");
    const cachedStatus = _verifyStatusCache[s.path];
    const badgeHTML = cachedStatus ? getStatusBadgeHTML(cachedStatus.status) : '';
    const statusMsg = cachedStatus ? `<small style="color:var(--text-dim);display:block;margin-top:4px;">${escapeHtml(cachedStatus.message)}</small>` : '';
    const xsPresent = s.xs_present === true;
    const xsBadge = xsPresent
      ? ''
      : `<span class="acc-status-badge expired" title="Cookie xs tidak ditemukan — sesi tidak valid untuk otentikasi FB"><i class="fa-solid fa-cookie-bite"></i> xs MISSING</span>`;

    return `
      <div class="account-card" data-path="${path}" id="acc-card-${c_user}">
        <div class="acc-header">
          <div class="acc-avatar">${escapeHtml(initial)}</div>
          <div class="acc-details">
            <h4>${name}</h4>
            <code>ID: ${c_user}</code>
            ${xsBadge}
            ${badgeHTML}
            ${statusMsg}
          </div>
        </div>
        <div class="acc-path" title="${escapeAttr(s.path || "")}">${filename}</div>
        <div class="acc-actions">
          <button class="btn btn-sm btn-outline btn-verify-acc" data-path="${path}" data-cuser="${c_user}" aria-label="Cek status sesi"><i class="fa-solid fa-shield-cat"></i> Cek Status</button>
          <button class="btn btn-sm btn-outline btn-relogin-acc" data-path="${path}" aria-label="Relogin akun"><i class="fa-solid fa-arrows-rotate"></i> Relogin</button>
          <button class="btn btn-sm btn-outline btn-rename-acc" data-path="${path}" data-name="${name}" aria-label="Ubah nama akun"><i class="fa-solid fa-pen"></i></button>
          <button class="btn btn-sm btn-danger btn-delete-acc" data-path="${path}" aria-label="Hapus akun"><i class="fa-solid fa-trash"></i></button>
        </div>
      </div>
    `;
  }).join("");

  // Render Custom Account Checkboxes — unchecked by default (user chooses which to use)
  if (checkboxContainer) {
    checkboxContainer.innerHTML = sessions.map(s => `
      <label class="checkbox-label" style="margin-bottom: 8px;">
        <input type="checkbox" name="selected-acc" value="${escapeAttr(s.path)}">
        <span>👤 ${escapeHtml(s.name || "Akun")} (ID: ${escapeHtml(s.c_user)})</span>
      </label>
    `).join("");
  }

  attachAccountCardListeners();
}


// ── SKIP-LIST & COOLDOWN LOADERS (NEW) ────────────────────────────────────────

async function loadSkipList() {
  const container = document.getElementById("skip-list-container");
  if (!container) return;

  const { ok, json } = await apiFetch("/api/runner/skip-list");
  if (!ok || json.status !== "success") {
    container.innerHTML = `<div class="empty-monitor-notice"><i class="fa-solid fa-triangle-exclamation"></i><p>Gagal memuat skip-list: ${escapeHtml(getApiError(json))}</p></div>`;
    return;
  }

  const items = json.skip_list || [];
  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-monitor-notice">
        <i class="fa-solid fa-circle-check"></i>
        <p>Belum ada grup di skip-list.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="margin-bottom:8px;color:var(--text-dim);font-size:0.9em;">
      <strong>${items.length}</strong> grup di skip-list:
    </div>
    <div class="skip-list-items">
      ${items.map(item => `
        <div class="skip-list-item">
          <code title="${escapeAttr(item.url)}">${escapeHtml(item.url.length > 80 ? item.url.slice(0, 77) + '...' : item.url)}</code>
          <span class="skip-reason">${escapeHtml(item.reason || 'failed')}</span>
        </div>
      `).join("")}
    </div>
  `;
}

async function loadCooldown() {
  const container = document.getElementById("cooldown-container");
  if (!container) return;

  const { ok, json } = await apiFetch("/api/runner/cooldown");
  if (!ok || json.status !== "success") {
    container.innerHTML = `<div class="empty-monitor-notice"><i class="fa-solid fa-triangle-exclamation"></i><p>Gagal memuat cooldown: ${escapeHtml(getApiError(json))}</p></div>`;
    return;
  }

  const items = json.cooldown || [];
  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-monitor-notice">
        <i class="fa-solid fa-circle-check"></i>
        <p>Tidak ada akun dalam cooldown.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="margin-bottom:8px;color:var(--text-dim);font-size:0.9em;">
      <strong>${items.length}</strong> akun dalam cooldown RESTRICTED:
    </div>
    <div class="cooldown-items">
      ${items.map(item => {
        const remainingMin = Math.max(0, Math.ceil((item.remaining_sec || 0) / 60));
        const expiryDate = new Date((item.expires_at || 0) * 1000);
        return `
          <div class="cooldown-item">
            <div>
              <code>c_user: ${escapeHtml(item.c_user)}</code>
              <span class="cooldown-remaining" title="Expires: ${escapeAttr(expiryDate.toLocaleString())}">
                ⏳ ${remainingMin} menit tersisa
              </span>
            </div>
            <button class="btn btn-sm btn-outline btn-release-cooldown" data-cuser="${escapeAttr(item.c_user)}" aria-label="Lepas cooldown untuk akun ini">
              <i class="fa-solid fa-unlock"></i> Lepas
            </button>
          </div>
        `;
      }).join("")}
    </div>
  `;

  // Attach release-cooldown button handlers
  container.querySelectorAll(".btn-release-cooldown").forEach(btn => {
    btn.addEventListener("click", async () => {
      const cuser = btn.getAttribute("data-cuser");
      const { ok, json } = await apiFetch(`/api/runner/cooldown?c_user=${encodeURIComponent(cuser)}`, { method: "DELETE" });
      if (ok && json.status === "success") {
        showToast(`✅ Cooldown dilepas untuk c_user ${cuser}`, "success");
        loadCooldown();
      } else {
        showToast(`❌ Gagal: ${getApiError(json)}`, "error");
      }
    });
  });
}


async function loadGroups() {
  const textarea = document.getElementById("groups-textarea");
  if (!textarea) return;
  const { ok, json } = await apiFetch("/api/groups");
  if (ok && json.status === "success") {
    textarea.value = json.raw_content || (json.groups || []).join("\n");
    updateGroupsCount();
  } else {
    console.error("Gagal memuat grup:", getApiError(json));
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
  if (!textarea) return;
  const { ok, json } = await apiFetch("/api/caption");
  if (ok && json.status === "success") {
    textarea.value = json.caption || "";
  } else {
    console.error("Gagal memuat caption:", getApiError(json));
  }
}

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return `${bytes.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

async function loadMedia() {
  const container = document.getElementById("media-gallery");
  if (!container) return;
  const { ok, json } = await apiFetch("/api/media");
  if (!ok || json.status !== "success") {
    console.error("Gagal memuat media:", getApiError(json));
    return;
  }
  const items = json.media || [];
  if (items.length === 0) {
    container.innerHTML = "<p class='text-muted' style='grid-column: 1/-1;'>Belum ada media foto/video diunggah.</p>";
    return;
  }

  container.innerHTML = items.map(m => {
    const name = escapeHtml(m.name || "");
    const url = escapeAttr(m.url || "");
    const sizeStr = formatBytes(m.size);
    return `
      <div class="media-thumb" title="${name}">
        <img src="${url}" alt="${name}">
        <button class="media-thumb-del" data-filename="${escapeAttr(m.name)}" aria-label="Hapus ${name}">&times;</button>
        <div class="media-thumb-info">
          <small>${name}</small>
          <small class="text-muted">${sizeStr}</small>
        </div>
      </div>
    `;
  }).join("");

  document.querySelectorAll(".media-thumb-del").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const fname = btn.getAttribute("data-filename");
      if (!confirm(`Hapus file media "${fname}"?`)) return;
      const { ok, json } = await apiFetch(`/api/media?filename=${encodeURIComponent(fname)}`, { method: "DELETE" });
      if (ok && json.status === "success") {
        showToast(`🗑️ Media ${fname} dihapus`, "success");
        loadMedia();
        loadStats();
      } else {
        showToast(`❌ Gagal hapus media: ${getApiError(json)}`, "error");
      }
    });
  });
}

async function loadConfig() {
  const { ok, json } = await apiFetch("/api/config");
  if (!ok || json.status !== "success") {
    console.error("Gagal memuat konfigurasi:", getApiError(json));
    return;
  }
  const cfg = json.config;
  document.getElementById("cfg-delay-min").value = cfg.delay_min;
  document.getElementById("cfg-delay-max").value = cfg.delay_max;
  document.getElementById("cfg-max-workers").value = cfg.max_workers;
  document.getElementById("cfg-headless").value = String(cfg.default_headless);
  document.getElementById("cfg-auto-like").checked = cfg.auto_like;
  document.getElementById("cfg-auto-comment").checked = cfg.auto_comment;
  // Populate auto_comments textarea (one per line)
  const commentsEl = document.getElementById("cfg-auto-comments");
  if (commentsEl && Array.isArray(cfg.auto_comments)) {
    commentsEl.value = cfg.auto_comments.join("\n");
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
      if (!confirm("Apakah Anda yakin ingin menghentikan eksekusi otomasi?")) return;
      btnMonStop.disabled = true;
      btnMonStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menghentikan...';
      const { ok, json } = await apiFetch("/api/runner/stop", { method: "POST" });
      btnMonStop.disabled = false;
      btnMonStop.innerHTML = '<i class="fa-solid fa-circle-stop"></i> Hentikan Otomasi';
      if (ok && json.status === "success") {
        showToast("🛑 " + (json.message || "Sinyal pembatalan dikirim"), "warning");
        loadStats();
      } else {
        showToast("❌ Gagal menghentikan: " + getApiError(json), "error");
      }
    });
  }

  if (btnMonTerminal) {
    btnMonTerminal.addEventListener("click", () => {
      switchToTab("tab-logs");
    });
  }

  // Poll live status every 1 second (with in-flight guard)
  setInterval(pollLiveStatus, 1000);
}

let _pollLiveStatusInFlight = false;
async function pollLiveStatus() {
  if (_pollLiveStatusInFlight) return;
  _pollLiveStatusInFlight = true;
  try {
    const { ok, json } = await apiFetch("/api/runner/live-status");
    if (ok && json.status === "success") {
      renderLiveMonitor(json.data);
    }
  } finally {
    _pollLiveStatusInFlight = false;
  }
}

/**
 * Validate a URL is safe to render as <a href>.
 * Rejects javascript:, data:, vbscript: schemes — only allow http/https.
 */
function safeUrl(url) {
  if (!url || typeof url !== "string") return null;
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return null;
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

  // Render Worker Cards — ALL server fields escaped to prevent XSS
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
        const rawName = w.account_name || "Akun Facebook";
        const initial = escapeHtml(rawName.charAt(0).toUpperCase());
        const name = escapeHtml(rawName);
        const statusStr = escapeAttr((w.status || "IDLE").toLowerCase());
        const statusLabel = escapeHtml(w.status || "IDLE");
        const currGrp = w.current_group || "";
        const safeGrpUrl = safeUrl(currGrp);
        const grpDisplay = safeGrpUrl
          ? `<a href="${escapeAttr(safeGrpUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(safeGrpUrl)}</a>`
          : (currGrp ? `<code>${escapeHtml(currGrp)}</code>` : "Belum memilih grup");
        const delayRem = w.delay_remaining || 0.0;

        let cardClass = "worker-live-card";
        if (statusStr === "processing") cardClass += " active";
        else if (statusStr === "waiting_delay") cardClass += " waiting";
        else if (statusStr === "completed") cardClass += " completed";
        else if (statusStr === "expired") cardClass += " expired";
        else if (statusStr === "restricted" || statusStr === "rate_limited") cardClass += " expired";

        return `
          <div class="${cardClass}">
            <div class="worker-card-header">
              <div class="worker-identity">
                <div class="worker-avatar">${initial}</div>
                <div class="worker-info">
                  <h5>${name}</h5>
                  <span class="worker-tag-badge">${escapeHtml(w.worker_tag || "")}</span>
                </div>
              </div>
              <span class="worker-status-tag ${statusStr}">${statusLabel}</span>
            </div>

            <div class="worker-spoof-pill" title="Hardware Fingerprint Spoofed">
              <i class="fa-solid fa-microchip"></i> ${escapeHtml(w.spoof_info || "Hardware Spoofed")}
            </div>

            <div class="worker-mini-progress">
              <div class="mini-progress-text">
                <span>Progress Akun</span>
                <span>${escapeHtml(String(w.current_idx || 0))} / ${escapeHtml(String(w.total_groups || 0))} (${escapeHtml(String(w.progress_percent || 0))}%)</span>
              </div>
              <div class="mini-progress-bar">
                <div class="mini-progress-fill" style="width: ${escapeAttr(String(w.progress_percent || 0))}%;"></div>
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
              💬 ${escapeHtml(w.step_msg || "Menunggu aksi selanjutnya...")}
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // Render Activity Stream Log — escaped
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
        const typeClass = escapeAttr((e.type || "system").toLowerCase());
        return `
          <div class="stream-line ${typeClass}">
            <span class="stream-time">[${escapeHtml(e.timestamp || "")}]</span>
            <span class="stream-msg"><strong>[${escapeHtml(e.worker_tag || "")}]</strong> ${escapeHtml(e.message || "")}</span>
          </div>
        `;
      }).join("");
    }
  }
}


// ── 4. LOG TERMINAL SSE STREAM ───────────────────────────────────────────────
const MAX_LOG_LINES = 500;

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

  evtSource.onerror = () => {
    // Browser auto-reconnects; show transient notice only on first error
    appendLogLine("[System] Koneksi SSE terputus. Mencoba menghubungkan ulang...");
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

    // Cap log lines to prevent DOM bloat & scroll lag
    while (terminalOutput.children.length > MAX_LOG_LINES) {
      terminalOutput.removeChild(terminalOutput.firstChild);
    }

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
      const { ok, json } = await apiFetch("/api/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groups: lines })
      });
      if (ok && json.status === "success") {
        showToast(`✅ ${json.message}`, "success");
        loadStats();
      } else {
        showToast("❌ Gagal simpan grup: " + getApiError(json), "error");
      }
    });
  }

  if (btnCleanGroups) {
    btnCleanGroups.addEventListener("click", async () => {
      const { ok, json } = await apiFetch("/api/groups/clean", { method: "POST" });
      if (ok && json.status === "success") {
        groupsTextarea.value = json.raw_content || (json.groups || []).join("\n");
        updateGroupsCount();
        showToast(`🧹 ${json.message}`, "success");
        loadStats();
      } else {
        showToast("❌ Gagal clean grup: " + getApiError(json), "error");
      }
    });
  }

  if (btnTriggerCollect) btnTriggerCollect.addEventListener("click", triggerCollectGroups);

  // Skip-list clear button
  const btnClearSkipList = document.getElementById("btn-clear-skiplist");
  if (btnClearSkipList) {
    btnClearSkipList.addEventListener("click", async () => {
      if (!confirm("Bersihkan seluruh skip-list grup? Grup yang sudah ditandai gagal akan bisa di-retry lagi.")) return;
      const { ok, json } = await apiFetch("/api/runner/skip-list", { method: "DELETE" });
      if (ok && json.status === "success") {
        showToast("🧹 Skip-list dibersihkan", "success");
        loadSkipList();
      } else {
        showToast("❌ Gagal: " + getApiError(json), "error");
      }
    });
  }
  const btnRefreshSkipList = document.getElementById("btn-refresh-skiplist");
  if (btnRefreshSkipList) btnRefreshSkipList.addEventListener("click", loadSkipList);

  // Cooldown clear button
  const btnClearCooldown = document.getElementById("btn-clear-cooldown");
  if (btnClearCooldown) {
    btnClearCooldown.addEventListener("click", async () => {
      if (!confirm("Bersihkan seluruh cooldown RESTRICTED? Akun-akun tersebut akan bisa dipakai lagi segera.")) return;
      const { ok, json } = await apiFetch("/api/runner/cooldown", { method: "DELETE" });
      if (ok && json.status === "success") {
        showToast("🛡️ Cooldown dibersihkan", "success");
        loadCooldown();
      } else {
        showToast("❌ Gagal: " + getApiError(json), "error");
      }
    });
  }
  const btnRefreshCooldown = document.getElementById("btn-refresh-cooldown");
  if (btnRefreshCooldown) btnRefreshCooldown.addEventListener("click", loadCooldown);
  if (groupsTextarea) groupsTextarea.addEventListener("input", updateGroupsCount);

  // Caption Save
  const btnSaveCaption = document.getElementById("btn-save-caption");
  if (btnSaveCaption) {
    btnSaveCaption.addEventListener("click", async () => {
      const text = document.getElementById("post-caption-textarea").value;
      const { ok, json } = await apiFetch("/api/caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caption: text })
      });
      if (ok && json.status === "success") {
        showToast("📝 " + json.message, "success");
      } else {
        showToast("❌ Gagal simpan caption: " + getApiError(json), "error");
      }
    });
  }

  // Media Upload
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("media-file-input");
  if (uploadZone && fileInput) {
    uploadZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      if (fileInput.files.length > 0) {
        let successCount = 0;
        let failCount = 0;
        for (let i = 0; i < fileInput.files.length; i++) {
          const formData = new FormData();
          formData.append("file", fileInput.files[i]);
          const { ok, json } = await apiFetch("/api/media/upload", { method: "POST", body: formData });
          if (ok && json.status === "success") successCount++; else failCount++;
        }
        // Reset fileInput so re-selecting the same file fires 'change' again
        fileInput.value = "";
        if (successCount > 0) {
          showToast(`🖼️ ${successCount} media berhasil diunggah${failCount > 0 ? `, ${failCount} gagal` : ''}!`, failCount > 0 ? "warning" : "success");
        } else {
          showToast(`❌ Semua ${failCount} media gagal diunggah`, "error");
        }
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
      if (!confirm("Apakah Anda yakin ingin menghentikan seluruh proses otomasi?")) return;
      btnStopAutomation.disabled = true;
      btnStopAutomation.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menghentikan...';
      const { ok, json } = await apiFetch("/api/runner/stop", { method: "POST" });
      btnStopAutomation.disabled = false;
      btnStopAutomation.innerHTML = '<i class="fa-solid fa-circle-stop"></i> Hentikan Otomasi';
      if (ok && json.status === "success") {
        showToast("🛑 " + (json.message || "Otomasi dihentikan"), "warning");
        loadStats();
      } else {
        showToast("❌ Gagal: " + getApiError(json), "error");
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
      if (tag === null || !tag.trim()) return;
      const { ok, json } = await apiFetch(`/api/sessions/login-new?tag=${encodeURIComponent(tag.trim())}`, { method: "POST" });
      if (ok && json.status === "success") {
        showToast("🔑 " + json.message + " Browser GUI akan terbuka untuk login.", "success", 6000);
        switchToTab("tab-logs");
      } else {
        showToast("❌ Gagal: " + getApiError(json), "error");
      }
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
      const name = document.getElementById("import-name-input").value.trim();
      const jsonContent = document.getElementById("import-json-textarea").value.trim();
      if (!jsonContent) {
        showToast("⚠️ Isi JSON cookie tidak boleh kosong.", "warning");
        return;
      }
      // Validate JSON is parseable before sending
      try {
        JSON.parse(jsonContent);
      } catch (e) {
        showToast("❌ JSON tidak valid: " + e.message, "error");
        return;
      }
      btnSubmitImport.disabled = true;
      const { ok, json } = await apiFetch("/api/sessions/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || "Imported_Account", json_content: jsonContent })
      });
      btnSubmitImport.disabled = false;
      if (ok && json.status === "success") {
        showToast("🎉 " + json.message, "success");
        closeModal("modal-import");
        document.getElementById("import-json-textarea").value = "";
        document.getElementById("import-name-input").value = "";
        loadSessions();
        loadStats();
      } else {
        showToast("❌ Gagal mengimpor: " + getApiError(json), "error");
      }
    });
  }

  // Save Settings
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const delayMin = parseFloat(document.getElementById("cfg-delay-min").value);
      const delayMax = parseFloat(document.getElementById("cfg-delay-max").value);
      const maxWorkers = parseInt(document.getElementById("cfg-max-workers").value);

      // Validation
      if (isNaN(delayMin) || delayMin < 0) {
        showToast("❌ Jeda minimal harus angka >= 0", "error");
        return;
      }
      if (isNaN(delayMax) || delayMax < 0) {
        showToast("❌ Jeda maksimal harus angka >= 0", "error");
        return;
      }
      if (delayMin > delayMax) {
        showToast("❌ Jeda minimal tidak boleh lebih besar dari jeda maksimal", "error");
        return;
      }
      if (isNaN(maxWorkers) || maxWorkers < 1) {
        showToast("❌ Worker paralel minimal 1", "error");
        return;
      }

      // Parse auto_comments from textarea (one per line)
      const commentsText = document.getElementById("cfg-auto-comments").value;
      const autoComments = commentsText.split("\n").map(s => s.trim()).filter(s => s.length > 0);

      const body = {
        delay_min: delayMin,
        delay_max: delayMax,
        max_workers: maxWorkers,
        default_headless: document.getElementById("cfg-headless").value === "true",
        auto_like: document.getElementById("cfg-auto-like").checked,
        auto_comment: document.getElementById("cfg-auto-comment").checked,
        auto_comments: autoComments.length > 0 ? autoComments : ["Up"]
      };

      const submitBtn = settingsForm.querySelector('button[type="submit"]');
      if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menyimpan...'; }
      const { ok, json } = await apiFetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Simpan Konfigurasi'; }
      if (ok && json.status === "success") {
        showToast("⚙️ " + json.message, "success");
      } else {
        showToast("❌ Gagal simpan konfigurasi: " + getApiError(json), "error");
      }
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
      const { ok, json } = await apiFetch("/api/sessions/relogin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_path: path })
      });
      if (ok && json.status === "success") {
        showToast("🔄 " + json.message, "success");
        switchToTab("tab-logs");
      } else {
        showToast("❌ Gagal relogin: " + getApiError(json), "error");
      }
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
      const newName = document.getElementById("rename-name-input").value.trim();
      if (!newName) {
        showToast("⚠️ Nama tidak boleh kosong", "warning");
        return;
      }
      const { ok, json } = await apiFetch("/api/sessions/rename", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_path: path, new_name: newName })
      });
      if (ok && json.status === "success") {
        showToast("✏️ " + json.message, "success");
        closeModal("modal-rename");
        loadSessions();
      } else {
        showToast("❌ Gagal rename: " + getApiError(json), "error");
      }
    };
  }

  document.querySelectorAll(".btn-delete-acc").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      if (!confirm(`Apakah Anda yakin ingin menghapus sesi akun ini?\nPath: ${path}`)) return;
      const { ok, json } = await apiFetch("/api/sessions/delete", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_path: path })
      });
      if (ok && json.status === "success") {
        showToast("🗑️ " + json.message, "success");
        // Hapus cache untuk path ini
        delete _verifyStatusCache[path];
        loadSessions();
        loadStats();
      } else {
        showToast("❌ Gagal hapus: " + getApiError(json), "error");
      }
    });
  });
}

async function triggerCollectGroups() {
  if (!confirm("Jalankan kolektor pencarian grup otomatis sekarang?")) return;
  const { ok, json } = await apiFetch("/api/groups/collect", { method: "POST" });
  if (ok && json.status === "success") {
    showToast("🔍 " + json.message, "success");
    switchToTab("tab-logs");
  } else {
    showToast("❌ Gagal: " + getApiError(json), "error");
  }
}

async function startAutomationRun(runAllOverride = false) {
  let selectedSessions = [];

  if (runAllOverride) {
    const { ok, json } = await apiFetch("/api/sessions");
    if (!ok || !Array.isArray(json.sessions)) {
      showToast("❌ Gagal memuat daftar akun", "error");
      return;
    }
    selectedSessions = json.sessions.map(s => s.path);
  } else {
    const accModeEl = document.querySelector('input[name="acc-mode"]:checked');
    const accMode = accModeEl ? accModeEl.value : "all";
    if (accMode === "all") {
      const { ok, json } = await apiFetch("/api/sessions");
      if (!ok || !Array.isArray(json.sessions)) {
        showToast("❌ Gagal memuat daftar akun", "error");
        return;
      }
      selectedSessions = json.sessions.map(s => s.path);
    } else {
      document.querySelectorAll('input[name="selected-acc"]:checked').forEach(cb => {
        selectedSessions.push(cb.value);
      });
    }
  }

  if (selectedSessions.length === 0) {
    showToast("⚠️ Harap pilih minimal 1 akun Facebook untuk diproses.", "warning");
    return;
  }

  // Validate mode (defense-in-depth, even though <select> enforces it)
  const mode = document.getElementById("runner-mode-select").value;
  if (!["1", "2", "3"].includes(mode)) {
    showToast("❌ Mode tidak valid. Pilih 1 (Post), 2 (Join), atau 3 (Post+Join).", "error");
    return;
  }

  // Validate start/end idx
  const startIdx = parseInt(document.getElementById("runner-start-idx").value) || 1;
  let endIdx = parseInt(document.getElementById("runner-end-idx").value) || null;
  if (endIdx !== null && endIdx < 1) {
    showToast("❌ Index akhir harus >= 1 atau kosongkan untuk semua grup.", "error");
    return;
  }
  if (endIdx !== null && endIdx < startIdx) {
    showToast("❌ Index akhir tidak boleh lebih kecil dari index awal.", "error");
    return;
  }

  const maxWorkers = parseInt(document.getElementById("runner-max-workers").value) || 3;
  if (maxWorkers < 1 || maxWorkers > 10) {
    showToast("⚠️ Worker paralel disarankan 1-10. Lanjut dengan nilai default 3.", "warning");
  }

  const payload = {
    selected_sessions: selectedSessions,
    mode: mode,
    start_idx: startIdx,
    end_idx: endIdx,
    headless: document.getElementById("runner-headless-select").value === "true",
    max_workers: maxWorkers,
    randomize_groups: document.getElementById("runner-randomize-groups").checked,
    custom_caption: document.getElementById("post-caption-textarea").value
  };

  const { ok, json } = await apiFetch("/api/runner/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (ok && json.status === "success") {
    showToast("🚀 " + json.message, "success");
    await loadStats();
    switchToTab("tab-monitor");
  } else {
    showToast("❌ Gagal memulai otomasi: " + getApiError(json), "error", 6000);
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

