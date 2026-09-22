(function () {
  const cfg = window.STRLIX_MARKET || {};
  const params = new URLSearchParams(location.search);

  function isLoopbackHost(hostname) {
    const h = String(hostname || "").toLowerCase();
    return h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h === "::1";
  }

  function isLoopbackUrl(value) {
    try {
      const u = new URL(value, location.href);
      return isLoopbackHost(u.hostname);
    } catch (_) {
      return false;
    }
  }

  function stripSlash(s) {
    return String(s || "").replace(/\/$/, "");
  }

  // Same-origin on public HTTPS. Never keep 127.0.0.1 when the page is not local —
  // that is why real phones break (unreachable + mixed content).
  function resolveApiBase() {
    if (params.has("api")) return stripSlash(params.get("api"));
    if (Object.prototype.hasOwnProperty.call(cfg, "marketApi")) {
      const raw = cfg.marketApi;
      if (raw == null) return null;
      const v = stripSlash(raw);
      if (v && isLoopbackUrl(v) && !isLoopbackHost(location.hostname)) return "";
      return v;
    }
    return "";
  }

  function resolveStreamBase(key, fallback) {
    const q = key === "streamUrl" ? params.get("stream") : params.get("streamFallback");
    if (q) return stripSlash(q);
    const raw = cfg[key];
    if (raw != null && String(raw).trim() !== "") {
      const v = stripSlash(raw);
      if (isLoopbackUrl(v) && !isLoopbackHost(location.hostname)) return fallback;
      return v;
    }
    return fallback;
  }

  const MARKET_API = resolveApiBase(); // "" = same-origin; null = static-only
  const hasMarketApi = MARKET_API !== null;
  const STREAM = resolveStreamBase("streamUrl", "/stream");
  const STREAM_FALLBACK = resolveStreamBase("streamFallback", STREAM);

  let PAY_MODE = cfg.payMode || "test";
  let FREE_MONTH = (cfg.billingMode || "free_month") === "free_month" || cfg.freeLaunch !== false;
  let LAUNCH_COPY = "Free for your first month — no card required.";
  let INVITE_REQUIRED = false;

  const IFRAME_ALLOW = [
    "autoplay",
    "clipboard-read",
    "clipboard-write",
    "microphone",
    "camera",
    "fullscreen",
    "display-capture",
  ].join("; ");

  function paintLaunch() {
    const payPill = document.getElementById("payPill");
    const copy = document.getElementById("freeMonthCopy");
    if (copy) copy.textContent = LAUNCH_COPY;
    if (!payPill) return;
    if (FREE_MONTH) {
      payPill.textContent = "Free month";
      payPill.classList.add("free");
      payPill.title = LAUNCH_COPY + " Stripe stays in test mode.";
      return;
    }
    payPill.textContent = "PAY: " + String(PAY_MODE).toUpperCase();
    payPill.classList.toggle("free", false);
    payPill.title = PAY_MODE === "live"
      ? "LIVE gated on — real charges possible"
      : "Stripe/Razorpay test mode — no real charges";
  }

  async function refreshPayGates() {
    if (!hasMarketApi) { paintLaunch(); return; }
    try {
      const base = MARKET_API;
      const [gates, launch] = await Promise.all([
        fetch(base + "/v1/payments/status").then((r) => r.json()),
        fetch(base + "/v1/launch").then((r) => r.json()),
      ]);
      PAY_MODE = gates.effective_mode || PAY_MODE;
      if (typeof launch.free_month_active === "boolean") FREE_MONTH = launch.free_month_active;
      if (launch.copy) LAUNCH_COPY = launch.copy;
      INVITE_REQUIRED = !!launch.invite_required;
      paintLaunch();
      render();
    } catch (_) {
      paintLaunch();
    }
  }
  refreshPayGates();

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
    stageLive: document.getElementById("stageLive"),
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
  let activeStreamBase = STREAM;

  function money(cents) {
    return `$${(cents / 100).toFixed(2)}`;
  }

  let latencyTimer = null;
  const rttSamples = [];

  function setLatencyChip(text, title, cls) {
    const el = document.getElementById("latencyChip");
    if (!el) return;
    el.textContent = text;
    el.title = title || "";
    el.className = "pill soft latency" + (cls ? " " + cls : "");
  }

  async function measureStreamRtt() {
    const base = activeStreamBase || STREAM;
    const url = stripSlash(base) + "/health";
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
          credentials: "same-origin",
          signal: ctrl ? ctrl.signal : undefined,
        });
      } catch (_) {
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
      rttSamples.push(ms);
      if (rttSamples.length > 30) rttSamples.shift();
      const last = rttSamples[rttSamples.length - 1];
      const band = last < 60 ? "ok" : last < 120 ? "warn" : "err";
      setLatencyChip(
        "RTT " + last + " ms",
        "Health RTT to " + url + " (" + mode + "). Taps are POST /adb/tap on the phone stream, measured on the phone as tap · Nms. See demo/launch/PHONE-TOUCH-AUDIO.md.",
        band
      );
      if (els.stageLive) els.stageLive.classList.toggle("on", band === "ok" || band === "warn");
    } catch (_) {
      setLatencyChip("RTT —", "stream /health unreachable — is /stream attached to AFD?", "muted");
      if (els.stageLive) els.stageLive.classList.remove("on");
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

  function apiUrl(path) {
    return MARKET_API + path;
  }

  async function loadDevices() {
    if (hasMarketApi) {
      try {
        const r = await fetch(apiUrl("/v1/devices"));
        if (r.ok) {
          const j = await r.json();
          devices = j.devices || [];
          populateFilters();
          render();
          return;
        }
      } catch (_) {
        /* fall through to static catalog */
      }
    }
    const r = await fetch("devices.json");
    const j = await r.json();
    devices = j.devices || [];
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
      return `<article class="device-row" data-id="${d.id}">
        <h3>${escapeHtml(d.model)}</h3>
        <div class="meta">
          <span class="chip ${legacy}">${escapeHtml(d.android_label)}</span>
          <span class="chip">${d.ram_gb} GB RAM</span>
          <span class="chip">${d.rom_gb} GB ROM</span>
          <span class="chip">${escapeHtml(d.tier)}</span>
          <span class="chip net" title="Honest network class — not residential anti-detect">${escapeHtml(d.network || "datacenter")}</span>
          ${d.available ? "" : '<span class="chip gone">Unavailable</span>'}
        </div>
        <div class="price">${FREE_MONTH ? escapeHtml(LAUNCH_COPY) : `${money(d.price_hour_cents)}/hr · ${money(d.price_day_cents)}/day`} <span class="meta" style="display:inline">· ${escapeHtml(d.region || "")}</span></div>
        <p class="meta">${escapeHtml(d.notes || "")}</p>
        <div class="actions">
          <button class="btn primary" data-act="open" ${d.available ? "" : "disabled"}>Open phone</button>
          <button class="btn ghost" data-act="buy" ${d.available ? "" : "disabled"}>${FREE_MONTH ? "Free month" : "Rent"}</button>
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

  function pickStreamBase(device, lease) {
    const fromLease = lease && (lease.stream_url || lease.stream_after_pay);
    if (fromLease) {
      const v = stripSlash(fromLease);
      if (!(isLoopbackUrl(v) && !isLoopbackHost(location.hostname))) return v;
    }
    if (device && device.preview === "live") return STREAM;
    return STREAM_FALLBACK || STREAM;
  }

  function streamViewerSrc(base) {
    const root = stripSlash(base) + "/";
    const u = new URL(root, location.href);
    u.searchParams.set("embed", "1");
    // Bust the static viewer when market-api ships a new embed.
    if (cfg.viewerRev) u.searchParams.set("v", String(cfg.viewerRev));
    // Absolute stream hosts must keep origin.
    // Path-only return made phones load /?embed=1 on azurefd (404) forever.
    if (u.origin !== location.origin) return u.href;
    return u.pathname + u.search + u.hash;
  }

  function streamOrigin() {
    try { return new URL(activeStreamBase || STREAM, location.href).origin; }
    catch (_) { return ""; }
  }

  function showStreamUnavailable(bootEl, reason) {
    if (!bootEl) return;
    bootEl.hidden = false;
    bootEl.classList.add("err");
    bootEl.innerHTML = `<div>
        <strong>Stream not reachable yet</strong>
        <p>${escapeHtml(reason || "Public /stream is not attached to Front Door, or the stream host is down.")}</p>
        <p style="margin-top:8px;color:var(--muted)">Operators: <code>web-market/DEPLOY.md</code> · <code>ATTACH-AFD-STREAM.sh</code></p>
      </div>
      <div class="ask-peek"><span class="ask-s">S</span> Ask stays inside the phone</div>`;
  }

  async function probeStreamReady(base) {
    try {
      const r = await fetch(stripSlash(base) + "/health", {
        method: "GET",
        cache: "no-store",
        mode: "cors",
        credentials: "same-origin",
      });
      return r.ok;
    } catch (_) {
      return false;
    }
  }

  function mountLiveIframe(src, device) {
    const boot = `<div class="stream-boot" id="streamBoot">
      <div>
        <strong>Waking ${escapeHtml(device.model)}</strong>
        <p>Stream loads inside this bezel. Ask Strlix stays on the phone — not a side panel.</p>
      </div>
      <div class="ask-peek"><span class="ask-s">S</span> Ask Strlix…</div>
    </div>`;
    els.stageScreen.innerHTML = boot +
      `<iframe id="streamFrame" title="Cloud phone stream" src="${escapeHtml(src)}"
        allow="${IFRAME_ALLOW}"
        allowfullscreen
        referrerpolicy="no-referrer-when-downgrade"
        importance="high"></iframe>`;

    const frame = document.getElementById("streamFrame");
    const bootEl = document.getElementById("streamBoot");
    let settled = false;

    const hideBoot = () => {
      if (settled || !bootEl) return;
      settled = true;
      bootEl.hidden = true;
      bootEl.classList.add("gone");
    };

    probeStreamReady(activeStreamBase).then((ok) => {
      if (!ok) {
        showStreamUnavailable(
          bootEl,
          "No response from " + stripSlash(activeStreamBase) + "/health. Attach desktop-api under /stream on AFD, then retry."
        );
        settled = true;
        return;
      }
      // Health ok — reveal as soon as the iframe loads. The overlay does not
      // receive taps (pointer-events: none), so a slow hide cannot eat the first touch.
      if (frame) {
        frame.addEventListener("load", () => {
          try { frame.focus({ preventScroll: true }); } catch (_) {}
          hideBoot();
        }, { once: true });
        setTimeout(hideBoot, 900);
      }
    });

    if (frame) {
      frame.addEventListener("error", () => {
        showStreamUnavailable(bootEl, "The stream iframe failed to load.");
        settled = true;
      });
    }
  }

  function openFullscreen(device, lease, options = {}) {
    selected = device;
    els.stageTitle.textContent = `${device.model} · ${device.android_label}`;
    activeStreamBase = pickStreamBase(device, lease);

    if (device.preview === "live" || (lease && (lease.stream_url || lease.granted_free || lease.local))) {
      const liveDevice = device.preview === "live" ? device : (devices.find((d) => d.preview === "live") || device);
      if (device.preview !== "live" && liveDevice !== device) {
        // Conceptual SKU — still open the live pool so the phone path works.
        activeStreamBase = pickStreamBase(liveDevice, lease);
      }
      const src = streamViewerSrc(activeStreamBase);
      // Stay in the market shell. Navigating the tab away dropped Close and
      // made the first tap feel like a broken page load.
      if (device.preview === "live") {
        mountLiveIframe(src, device);
      } else {
        els.stageScreen.innerHTML = `<div class="stream-boot">
          <div>
            <strong>${escapeHtml(device.model)}</strong>
            <p>Conceptual pool image (${escapeHtml(device.android_label)}, ${device.ram_gb}/${device.rom_gb} GB).
            Live stream binds when this SKU is provisioned.</p>
          </div>
          <button class="btn primary" id="openLiveAnyway" type="button">Open live pool preview</button>
        </div>`;
        const b = document.getElementById("openLiveAnyway");
        if (b) b.onclick = () => mountLiveIframe(streamViewerSrc(STREAM_FALLBACK || STREAM), liveDevice);
      }
    } else {
      els.stageScreen.innerHTML = `<div class="stream-boot">
        <div>
          <strong>${escapeHtml(device.model)}</strong>
          <p>No live preview for this SKU yet.</p>
        </div>
        <button class="btn primary" id="openLiveAnyway" type="button">Open live pool preview</button>
      </div>`;
      const b = document.getElementById("openLiveAnyway");
      if (b) b.onclick = () => {
        activeStreamBase = STREAM_FALLBACK || STREAM;
        mountLiveIframe(streamViewerSrc(activeStreamBase), device);
        startLatencyLoop();
      };
    }

    els.stage.classList.add("open");
    els.stage.setAttribute("aria-hidden", "false");
    document.body.classList.add("phone-open");
    document.body.style.overflow = "hidden";
    if (els.stageStatus) els.stageStatus.textContent = `${device.model} preview opened.`;
    pokeChrome();
    requestStageFullscreen();
    document.getElementById("closeStage").focus();
    if (lease) sessionStorage.setItem("strlix_lease", JSON.stringify(lease));
    if (options.wow && isAnonymous) showClaimPrompt();
    startLatencyLoop();
  }

  function closeFullscreen() {
    els.stage.classList.remove("open", "chrome-hide");
    els.stage.setAttribute("aria-hidden", "true");
    document.body.classList.remove("phone-open");
    document.body.style.overflow = "";
    if (document.fullscreenElement) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen;
      if (exit) exit.call(document).catch(() => {});
    }
    if (els.stageStatus) els.stageStatus.textContent = "Phone preview closed";
    els.stageScreen.innerHTML = "";
    if (els.claimPrompt) els.claimPrompt.hidden = true;
    if (els.stageLive) els.stageLive.classList.remove("on");
    stopLatencyLoop();
  }

  function saveAuthSession(j) {
    els.token = j.access_token;
    isAnonymous = !!j.is_anonymous;
    if (j.refresh_token) {
      refreshToken = j.refresh_token;
      localStorage.setItem("strlix_refresh_token", refreshToken);
    }
    setSessionPill(isAnonymous ? "Anonymous · Save account" : "Account session");
    return els.token;
  }

  async function readJson(response) {
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(body.detail || body.message || `Request failed (${response.status})`);
    return body;
  }

  async function refreshAuth() {
    if (!hasMarketApi || !refreshToken) return false;
    try {
      const r = await fetch(apiUrl("/v1/auth/refresh"), {
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
      setSessionPill("Guest · no signup");
      return false;
    }
  }

  async function ensureAuth() {
    if (els.token) return els.token;
    if (!hasMarketApi) {
      els.token = "local-demo";
      return els.token;
    }
    localStorage.removeItem("strlix_email");
    if (await refreshAuth()) return els.token;
    const r = await fetch(apiUrl("/v1/auth/anon"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return saveAuthSession(await readJson(r));
  }

  async function apiJson(path, options = {}) {
    const token = await ensureAuth();
    const headers = Object.assign({}, options.headers || {}, { Authorization: "Bearer " + token });
    let r = await fetch(apiUrl(path), Object.assign({}, options, { headers }));
    if (r.status === 401 && refreshToken && await refreshAuth()) {
      headers.Authorization = "Bearer " + els.token;
      r = await fetch(apiUrl(path), Object.assign({}, options, { headers }));
    }
    return readJson(r);
  }

  async function createPollableJob(kind = "phone_task") {
    if (!hasMarketApi) throw new Error("async jobs require market-api");
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

  async function startFreeMonth(device) {
    selected = device;
    els.modal.classList.add("open");
    const invite = INVITE_REQUIRED
      ? `<label class="sr-only" for="freeInvite">Invite code</label>
         <input id="freeInvite" type="text" maxlength="64" placeholder="Invite code" required />`
      : `<label class="sr-only" for="freeInvite">Invite code (optional)</label>
         <input id="freeInvite" type="text" maxlength="64" placeholder="Invite code (optional)" />`;
    els.modalBody.innerHTML = `<p class="pill free">${escapeHtml(LAUNCH_COPY)}</p>
      <p>Open <strong>${escapeHtml(device.model)}</strong> for the free month. Stripe is not used.</p>
      <label class="sr-only" for="freeEmail">Email for the waitlist (optional)</label>
      <input id="freeEmail" type="email" autocomplete="email" placeholder="Email for the waitlist (optional)" />
      ${invite}
      <div class="row">
        <button class="btn primary" id="freeStart" type="button">Start free month</button>
        <button class="btn ghost" id="payCancel" type="button">Cancel</button>
      </div>`;
    els.modalBody.querySelector("#payCancel").onclick = () => els.modal.classList.remove("open");
    els.modalBody.querySelector("#freeStart").onclick = () => confirmFree(device);
  }

  async function confirmFree(device) {
    const button = els.modalBody.querySelector("#freeStart");
    if (button) button.disabled = true;
    const email = (els.modalBody.querySelector("#freeEmail").value || "").trim();
    const invite = (els.modalBody.querySelector("#freeInvite").value || "").trim();
    try {
      if (hasMarketApi && email) {
        const joined = await fetch(apiUrl("/v1/waitlist"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, invite_code: invite || undefined }),
        });
        await readJson(joined);
      }
      if (!hasMarketApi) {
        els.modal.classList.remove("open");
        openFullscreen(device, { local: true, plan: "free_month", device_id: device.id, card_required: false }, { wow: false });
        return;
      }
      const granted = await apiJson("/v1/access/grant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: device.id, invite_code: invite || undefined }),
      });
      els.modal.classList.remove("open");
      openFullscreen(device, granted, { wow: true });
    } catch (err) {
      els.modalBody.insertAdjacentHTML("beforeend", `<p class="claim-message">${escapeHtml(err.message)}</p>`);
      if (button) button.disabled = false;
    }
  }

  async function startCheckout(device) {
    if (FREE_MONTH) return startFreeMonth(device);
    selected = device;
    els.modal.classList.add("open");
    els.modalBody.innerHTML = `<p class="pill soft">PAYMENT MODE: ${PAY_MODE.toUpperCase()} — no real charges</p>
      <p>Rent <strong>${escapeHtml(device.model)}</strong> (${escapeHtml(device.android_label)}, ${device.ram_gb} GB / ${device.rom_gb} GB).</p>
      <div class="row">
        <button class="btn primary" data-plan="hour">Pay ${money(device.price_hour_cents)} / hour</button>
        <button class="btn primary" data-plan="day">Pay ${money(device.price_day_cents)} / day</button>
        <button class="btn ghost" id="payCancel">Cancel</button>
      </div>
      <p style="margin-top:12px;font-size:11px">Gated payments · live needs PAYMENTS_LIVE + Key Vault keys</p>`;
    els.modalBody.querySelector("#payCancel").onclick = () => els.modal.classList.remove("open");
    els.modalBody.querySelectorAll("[data-plan]").forEach((btn) => {
      btn.onclick = () => confirmPay(device, btn.getAttribute("data-plan"));
    });
  }

  async function confirmPay(device, plan) {
    const buttons = [...els.modalBody.querySelectorAll("[data-plan]")];
    buttons.forEach((button) => { button.disabled = true; });
    try {
      if (!hasMarketApi) {
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

  let chromeTimer = 0;
  function immersivePhone() {
    return window.matchMedia("(max-width: 920px), (max-height: 520px) and (pointer: coarse)").matches;
  }
  function pokeChrome() {
    if (!els.stage.classList.contains("open")) return;
    els.stage.classList.remove("chrome-hide");
    clearTimeout(chromeTimer);
    if (!immersivePhone()) return;
    chromeTimer = setTimeout(() => {
      if (els.stage.classList.contains("open")) els.stage.classList.add("chrome-hide");
    }, 2200);
  }
  function requestStageFullscreen() {
    if (!immersivePhone()) return;
    const req = els.stage.requestFullscreen || els.stage.webkitRequestFullscreen;
    if (!req || document.fullscreenElement) return;
    req.call(els.stage).catch(() => {});
  }

  window.addEventListener("message", (ev) => {
    const data = ev.data;
    if (!data || data.source !== "strlix-viewer") return;
    const allowed = streamOrigin();
    if (allowed && ev.origin !== allowed && ev.origin !== location.origin) return;
    if (data.type === "strlix-first-frame") {
      const bootEl = document.getElementById("streamBoot");
      if (bootEl) {
        bootEl.hidden = true;
        bootEl.classList.add("gone");
      }
      if (els.stageLive) els.stageLive.classList.add("on");
    }
  });
  els.stage.addEventListener("pointerdown", pokeChrome);

  function openHeroPhone() {
    const live = devices.find((d) => d.preview === "live") || devices[0];
    if (live) openFullscreen(live);
  }

  document.getElementById("heroPhone").addEventListener("click", openHeroPhone);
  document.getElementById("closeStage").onclick = closeFullscreen;
  document.getElementById("btnAskHint").onclick = () => {
    const frame = document.getElementById("streamFrame");
    if (frame && frame.contentWindow) {
      try { frame.contentWindow.postMessage({ type: "strlix-open-ask" }, location.origin); } catch (_) {}
    }
    const hint = document.createElement("div");
    hint.className = "inphone-ask";
    hint.innerHTML = `<span class="smark">S</span><span>Ask is inside the phone · ⌘K / Ctrl+K in the stream</span>`;
    els.stageScreen.appendChild(hint);
    setTimeout(() => hint.remove(), 2800);
  };
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
  document.getElementById("btnTry").onclick = openHeroPhone;
  document.getElementById("btnTry2").onclick = openHeroPhone;
  document.getElementById("btnCatalog").onclick = () => {
    document.getElementById("catalog").scrollIntoView({ behavior: "smooth" });
  };

  loadDevices().then(() => {
    if (params.get("open") === "1") openHeroPhone();
  }).catch((err) => {
    els.grid.innerHTML = `<p class="meta">Failed to load catalog: ${escapeHtml(err.message)}</p>`;
  });
})();
