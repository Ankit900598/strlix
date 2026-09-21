(function () {
  const cfg = window.STRLIX_MARKET || {};
  const MARKET_API = cfg.marketApi || null; // e.g. http://127.0.0.1:8792
  const STREAM = cfg.streamUrl || "http://127.0.0.1:8789";
  const STREAM_FALLBACK = cfg.streamFallback || "http://127.0.0.1:8787";
  const PAY_MODE = cfg.payMode || "test";

  const els = {
    grid: document.getElementById("deviceGrid"),
    android: document.getElementById("fAndroid"),
    ram: document.getElementById("fRam"),
    rom: document.getElementById("fRom"),
    tier: document.getElementById("fTier"),
    q: document.getElementById("fQ"),
    stage: document.getElementById("phoneStage"),
    stageTitle: document.getElementById("stageTitle"),
    stageScreen: document.getElementById("stageScreen"),
    modal: document.getElementById("payModal"),
    modalBody: document.getElementById("payBody"),
    sessionPill: document.getElementById("sessionPill"),
    claimPrompt: document.getElementById("claimPrompt"),
    claimForm: document.getElementById("claimForm"),
    claimEmail: document.getElementById("claimEmail"),
    claimName: document.getElementById("claimName"),
    claimMessage: document.getElementById("claimMessage"),
    dismissClaim: document.getElementById("dismissClaim"),
    stageStatus: document.getElementById("stageStatus"),
    token: null,
  };

  let devices = [];
  let selected = null;
  let refreshToken = localStorage.getItem("strlix_refresh_token") || "";
  let isAnonymous = false;

  function money(cents) {
    return `$${(cents / 100).toFixed(2)}`;
  }

  // M06 revise: real RTT from stream /health — never hardcode ms.
  let latencyTimer = null;
  const rttSamples = [];

  function setLatencyChip(text, title, cls) {
    const el = document.getElementById("latencyChip");
    if (!el) return;
    el.textContent = text;
    el.title = title || "";
    el.className = "pill latency" + (cls ? " " + cls : "");
  }

  async function measureStreamRtt() {
    const base = (selected && selected.preview === "live" ? STREAM : STREAM_FALLBACK) || STREAM;
    const url = base.replace(/\/$/, "") + "/health";
    const t0 = performance.now();
    try {
      const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
      const to = setTimeout(() => { if (ctrl) ctrl.abort(); }, 4000);
      let mode = "cors";
      let r;
      try {
        r = await fetch(url, {
          method: "GET",
          cache: "no-store",
          mode: "cors",
          signal: ctrl ? ctrl.signal : undefined,
        });
      } catch (corsErr) {
        // Cross-origin without ACAO: still time an opaque request (honest RTT, labeled est.)
        mode = "no-cors";
        r = await fetch(url, {
          method: "GET",
          cache: "no-store",
          mode: "no-cors",
          signal: ctrl ? ctrl.signal : undefined,
        });
      }
      clearTimeout(to);
      try { if (mode === "cors") await r.text(); } catch (_) {}
      const ms = Math.round(performance.now() - t0);
      if (mode === "cors" && !r.ok && r.status === 0) throw new Error("unreachable");
      rttSamples.push(ms);
      if (rttSamples.length > 30) rttSamples.shift();
      const last = rttSamples[rttSamples.length - 1];
      const band = last < 60 ? "ok" : last < 120 ? "warn" : "err";
      setLatencyChip(
        "RTT est. " + last + " ms",
        "HTTP RTT to stream /health via " + mode + " (not hardcoded). Samples: " + rttSamples.slice(-5).join(", "),
        band
      );
    } catch (e) {
      setLatencyChip("RTT —", "not measured — stream /health unreachable", "muted");
    }
  }

  function startLatencyLoop() {
    stopLatencyLoop();
    setLatencyChip("RTT …", "measuring", "muted");
    measureStreamRtt();
    latencyTimer = setInterval(measureStreamRtt, 2500);
  }

  function stopLatencyLoop() {
    if (latencyTimer) { clearInterval(latencyTimer); latencyTimer = null; }
    rttSamples.length = 0;
  }

  async function loadDevices() {
    if (MARKET_API) {
      const r = await fetch(MARKET_API + "/v1/devices");
      const j = await r.json();
      devices = j.devices || [];
    } else {
      const r = await fetch("devices.json");
      const j = await r.json();
      devices = j.devices || [];
    }
    populateFilters();
    render();
  }

  function populateFilters() {
    const androids = [...new Set(devices.map((d) => d.android))].sort((a, b) => a - b);
    const rams = [...new Set(devices.map((d) => d.ram_gb))].sort((a, b) => a - b);
    const roms = [...new Set(devices.map((d) => d.rom_gb))].sort((a, b) => a - b);
    const tiers = [...new Set(devices.map((d) => d.tier))];
    fillSelect(els.android, androids, (v) => `Android ${v}`);
    fillSelect(els.ram, rams, (v) => `${v} GB`);
    fillSelect(els.rom, roms, (v) => `${v} GB`);
    fillSelect(els.tier, tiers, (v) => v);
  }

  function fillSelect(sel, values, labelFn) {
    const cur = sel.value;
    sel.innerHTML = `<option value="">Any</option>` + values.map((v) => `<option value="${v}">${labelFn(v)}</option>`).join("");
    if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
  }

  function filtered() {
    const a = els.android.value, ram = els.ram.value, rom = els.rom.value, tier = els.tier.value;
    const q = (els.q.value || "").toLowerCase();
    return devices.filter((d) => {
      if (a && String(d.android) !== a) return false;
      if (ram && String(d.ram_gb) !== ram) return false;
      if (rom && String(d.rom_gb) !== rom) return false;
      if (tier && d.tier !== tier) return false;
      if (q && !`${d.model} ${d.android_label} ${d.tier}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function render() {
    const list = filtered();
    els.grid.innerHTML = list.map((d) => {
      const legacy = d.android <= 8 ? "legacy" : "";
      const gone = d.available ? "" : "gone";
      return `<article class="card" data-id="${d.id}">
        <h3>${escapeHtml(d.model)}</h3>
        <div class="meta">
          <span class="chip ${legacy}">${escapeHtml(d.android_label)}</span>
          <span class="chip">${d.ram_gb} GB RAM</span>
          <span class="chip">${d.rom_gb} GB ROM</span>
          <span class="chip">${escapeHtml(d.tier)}</span>
          <span class="chip net" title="Honest network class — not residential anti-detect">${escapeHtml(d.network || "datacenter")}</span>
          ${d.available ? "" : '<span class="chip gone">Unavailable</span>'}
        </div>
        <div class="price">${money(d.price_hour_cents)}/hr · ${money(d.price_day_cents)}/day <span class="meta" style="display:inline">· ${escapeHtml(d.region || "")}</span></div>
        <p class="meta">${escapeHtml(d.notes || "")}</p>
        <div class="actions">
          <button class="btn primary" data-act="open" ${d.available ? "" : "disabled"}>Open phone</button>
          <button class="btn" data-act="buy" ${d.available ? "" : "disabled"}>Rent</button>
        </div>
      </article>`;
    }).join("") || `<p class="meta">No devices match filters.</p>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function setSessionPill(text) {
    if (els.sessionPill) els.sessionPill.textContent = text;
  }

  function openFullscreen(device, lease, options = {}) {
    selected = device;
    els.stageTitle.textContent = `${device.model} · ${device.android_label}`;
    const streamBase = device.preview === "live" ? STREAM : STREAM_FALLBACK;
    // Prefer embedding existing viewer; graceful note for mock SKUs
    const src = device.preview === "live"
      ? streamBase + "/"
      : null;
    if (src) {
      els.stageScreen.innerHTML = `<iframe title="Cloud phone stream" src="${src}" allow="autoplay; clipboard-read; clipboard-write; microphone"></iframe>
        <div class="ask-hint">AI lives inside the phone · Ask on device · Esc to exit</div>`;
    } else {
      els.stageScreen.innerHTML = `<div style="padding:20px;text-align:center">
          <strong>${escapeHtml(device.model)}</strong>
          <p style="color:#8b9bb8;font-size:13px;line-height:1.5;margin:10px 0">
            Conceptual pool image (${escapeHtml(device.android_label)}, ${device.ram_gb}/${device.rom_gb} GB).
            Live stream binds when this SKU is provisioned. JPEG/H.264 viewer still works on Android&nbsp;7+ web shells via graceful fallback.
          </p>
          <button class="btn primary" id="openLiveAnyway">Open live pool preview</button>
        </div>
        <div class="ask-hint">Esc / Close exits fullscreen</div>`;
      setTimeout(() => {
        const b = document.getElementById("openLiveAnyway");
        if (b) b.onclick = () => {
          els.stageScreen.innerHTML = `<iframe title="Cloud phone stream" src="${STREAM_FALLBACK}/" allow="autoplay; microphone"></iframe>`;
        };
      }, 0);
    }
    els.stage.classList.add("open");
    els.stage.setAttribute("aria-hidden", "false");
    if (els.stageStatus) els.stageStatus.textContent = `${device.model} preview opened. Phone stream is ready for keyboard focus.`;
    document.getElementById("closeStage").focus();
    if (lease) sessionStorage.setItem("strlix_lease", JSON.stringify(lease));
    if (options.wow && isAnonymous) showClaimPrompt();
  }

  function closeFullscreen() {
    els.stage.classList.remove("open");
    els.stage.setAttribute("aria-hidden", "true");
    if (els.stageStatus) els.stageStatus.textContent = "Phone preview closed";
    els.stageScreen.innerHTML = "";
    if (els.claimPrompt) els.claimPrompt.hidden = true;
    stopLatencyLoop();
  }

  function saveAuthSession(j) {
    els.token = j.access_token;
    isAnonymous = !!j.is_anonymous;
    if (j.refresh_token) {
      refreshToken = j.refresh_token;
      // Only a bearer refresh token is persisted; no email or device metadata.
      localStorage.setItem("strlix_refresh_token", refreshToken);
    }
    setSessionPill(isAnonymous ? "Anonymous session · Save account" : "Account session");
    return els.token;
  }

  async function readJson(response) {
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(body.detail || body.message || `Request failed (${response.status})`);
    return body;
  }

  async function refreshAuth() {
    if (!MARKET_API || !refreshToken) return false;
    try {
      const r = await fetch(MARKET_API + "/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      saveAuthSession(await readJson(r));
      return true;
    } catch (_) {
      els.token = null;
      refreshToken = "";
      localStorage.removeItem("strlix_refresh_token");
      setSessionPill("Guest preview · no signup");
      return false;
    }
  }

  async function ensureAuth() {
    if (els.token) return els.token;
    if (!MARKET_API) {
      els.token = "local-demo";
      return els.token;
    }
    // Remove the old pre-anonymous fake identity, but only when a visitor
    // actually starts checkout. Preview remains zero-auth and zero-storage.
    localStorage.removeItem("strlix_email");
    if (await refreshAuth()) return els.token;
    const r = await fetch(MARKET_API + "/v1/auth/anon", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return saveAuthSession(await readJson(r));
  }

  async function apiJson(path, options = {}) {
    const token = await ensureAuth();
    const headers = Object.assign({}, options.headers || {}, { Authorization: "Bearer " + token });
    let r = await fetch(MARKET_API + path, Object.assign({}, options, { headers }));
    if (r.status === 401 && refreshToken && await refreshAuth()) {
      headers.Authorization = "Bearer " + els.token;
      r = await fetch(MARKET_API + path, Object.assign({}, options, { headers }));
    }
    return readJson(r);
  }

  // Minimal async-task bridge for phone-first UI surfaces. The API stores only
  // an allow-listed kind and returns queued → running → done; no chat payloads.
  async function createPollableJob(kind = "phone_task") {
    if (!MARKET_API) throw new Error("async jobs require market-api");
    return apiJson("/v1/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind }),
    });
  }

  async function getPollableJob(jobId) {
    return apiJson("/v1/jobs/" + encodeURIComponent(jobId));
  }

  async function pollPollableJob(jobId, options = {}) {
    const intervalMs = Math.max(250, Math.min(Number(options.intervalMs) || 500, 5000));
    const timeoutMs = Math.max(1000, Math.min(Number(options.timeoutMs) || 30000, 120000));
    const onUpdate = typeof options.onUpdate === "function" ? options.onUpdate : () => {};
    const started = performance.now();
    while (true) {
      const job = await getPollableJob(jobId);
      onUpdate(job);
      if (job.status === "done") return job;
      if (performance.now() - started >= timeoutMs) throw new Error("job polling timed out");
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  }

  // Native wrappers and the in-phone viewer can opt into the same helper without
  // adding an outside chat surface: window.StrlixJobs.create(...), .poll(...).
  window.StrlixJobs = {
    create: createPollableJob,
    get: getPollableJob,
    poll: pollPollableJob,
  };

  function claimPromptDismissed() {
    const at = Number(localStorage.getItem("strlix_claim_dismissed_at") || 0);
    return at && Date.now() - at < 7 * 24 * 60 * 60 * 1000;
  }

  function showClaimPrompt() {
    if (!els.claimPrompt || claimPromptDismissed()) return;
    els.claimPrompt.hidden = false;
    els.claimMessage.textContent = "";
    els.claimEmail.focus();
  }

  async function claimSession(event) {
    event.preventDefault();
    const submit = els.claimForm.querySelector("[type=submit]");
    submit.disabled = true;
    els.claimMessage.textContent = "Saving…";
    try {
      const body = { email: els.claimEmail.value.trim() };
      if (els.claimName.value.trim()) body.display_name = els.claimName.value.trim();
      saveAuthSession(await apiJson("/v1/auth/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }));
      els.claimMessage.textContent = "Saved. Your rental is linked to this email.";
      els.claimForm.querySelectorAll("input,button").forEach((el) => { el.disabled = true; });
    } catch (err) {
      els.claimMessage.textContent = err.message;
      submit.disabled = false;
    }
  }

  async function startCheckout(device) {
    selected = device;
    els.modal.classList.add("open");
    els.modalBody.innerHTML = `<p class="pill test">PAYMENT MODE: ${PAY_MODE.toUpperCase()} — no real charges</p>
      <p>Rent <strong>${escapeHtml(device.model)}</strong> (${escapeHtml(device.android_label)}, ${device.ram_gb} GB / ${device.rom_gb} GB).</p>
      <div class="row">
        <button class="btn primary" data-plan="hour">Pay ${money(device.price_hour_cents)} / hour</button>
        <button class="btn primary" data-plan="day">Pay ${money(device.price_day_cents)} / day</button>
        <button class="btn" id="payCancel">Cancel</button>
      </div>
      <p style="margin-top:12px;font-size:11px">Stripe/Razorpay test keys via env · webhook stubs on market-api</p>`;
    els.modalBody.querySelector("#payCancel").onclick = () => els.modal.classList.remove("open");
    els.modalBody.querySelectorAll("[data-plan]").forEach((btn) => {
      btn.onclick = () => confirmPay(device, btn.getAttribute("data-plan"));
    });
  }

  async function confirmPay(device, plan) {
    const buttons = [...els.modalBody.querySelectorAll("[data-plan]")];
    buttons.forEach((button) => { button.disabled = true; });
    try {
      if (!MARKET_API) {
        // Local stub without API
        els.modal.classList.remove("open");
        openFullscreen(device, { local: true, plan, device_id: device.id });
        return;
      }
      const session = await apiJson("/v1/checkout/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: device.id, plan }),
      });
      const confirmed = await apiJson(`/v1/checkout/confirm?order_id=${encodeURIComponent(session.order_id)}`, {
        method: "POST",
      });
      els.modal.classList.remove("open");
      openFullscreen(device, confirmed, { wow: true });
    } catch (err) {
      els.modalBody.insertAdjacentHTML("beforeend", `<p class="claim-message">${escapeHtml(err.message)}</p>`);
      buttons.forEach((button) => { button.disabled = false; });
    }
  }

  els.claimForm.addEventListener("submit", claimSession);
  els.dismissClaim.addEventListener("click", () => {
    localStorage.setItem("strlix_claim_dismissed_at", String(Date.now()));
    els.claimPrompt.hidden = true;
  });

  document.getElementById("miniPhone").addEventListener("click", () => {
    const live = devices.find((d) => d.preview === "live") || devices[0];
    if (live) openFullscreen(live);
  });
  document.getElementById("miniPhone").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); document.getElementById("miniPhone").click(); }
  });
  document.getElementById("closeStage").onclick = closeFullscreen;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeFullscreen(); });
  ["fAndroid", "fRam", "fRom", "fTier", "fQ"].forEach((id) => {
    document.getElementById(id).addEventListener("input", render);
    document.getElementById(id).addEventListener("change", render);
  });
  els.grid.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const card = btn.closest("[data-id]");
    const d = devices.find((x) => x.id === card.dataset.id);
    if (!d) return;
    if (btn.dataset.act === "open") openFullscreen(d);
    if (btn.dataset.act === "buy") startCheckout(d);
  });
  document.getElementById("btnTry").onclick = () => document.getElementById("miniPhone").click();

  loadDevices().catch((err) => {
    els.grid.innerHTML = `<p class="meta">Failed to load catalog: ${escapeHtml(err.message)}</p>`;
  });
})();
