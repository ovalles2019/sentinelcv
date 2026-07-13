const POLL_FALLBACK_MS = 5000;
const POLL_IDLE_MS = 30000;
const MAX_LOG_ENTRIES = 60;
const CLIENT_ID = Math.random().toString(36).slice(2, 8);
const cards = new Map();
const lastSeen = new Map();
const lastHealth = new Map();
const lastFetched = new Map();

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

function logEvent(text, cls = "") {
  const list = document.getElementById("log-entries");
  const li = document.createElement("li");
  if (cls) li.className = cls;
  const time = new Date().toISOString().slice(11, 19);
  li.innerHTML = `<span class="t">${time}Z</span> ${text}`;
  list.prepend(li);
  while (list.children.length > MAX_LOG_ENTRIES) list.lastChild.remove();
}

function getCard(cam) {
  if (cards.has(cam.id)) return cards.get(cam.id);
  const tpl = document.getElementById("camera-template");
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.querySelector(".cam-name").textContent = cam.name;
  document.getElementById("cameras").appendChild(node);
  const refs = {
    root: node,
    dot: node.querySelector(".health-dot"),
    age: node.querySelector(".cam-age"),
    img: node.querySelector(".frame"),
    overlay: node.querySelector(".overlay"),
    acquiring: node.querySelector(".acquiring"),
    noSignal: node.querySelector(".no-signal"),
    detections: node.querySelector(".cam-detections"),
  };
  cards.set(cam.id, refs);
  return refs;
}

function drawBoxes(overlay, detections) {
  overlay.innerHTML = "";
  const ns = "http://www.w3.org/2000/svg";
  for (const d of detections) {
    const rect = document.createElementNS(ns, "rect");
    rect.setAttribute("x", d.x);
    rect.setAttribute("y", d.y);
    rect.setAttribute("width", d.w);
    rect.setAttribute("height", d.h);
    overlay.appendChild(rect);

    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", d.x + 0.004);
    text.setAttribute("y", Math.max(d.y - 0.01, 0.03));
    text.textContent = `${d.label} ${(d.confidence * 100).toFixed(0)}%`;
    overlay.appendChild(text);
  }
}

function ageString(iso) {
  if (!iso) return "never";
  const secs = Math.round((Date.now() - new Date(iso)) / 1000);
  return secs < 60 ? `${secs}s ago` : `${Math.round(secs / 60)}m ago`;
}

function trackHealthChange(cam) {
  const prev = lastHealth.get(cam.id);
  if (prev && prev !== cam.health) {
    const cls = cam.health === "Up" ? "detection" : "warn";
    logEvent(`${cam.name}: ${prev} → ${cam.health}`, cls);
  }
  lastHealth.set(cam.id, cam.health);
}

async function updateCamera(cam) {
  const card = getCard(cam);
  card.dot.className = "health-dot " + cam.health.toLowerCase();
  card.age.textContent = ageString(cam.lastSuccess);
  card.noSignal.classList.toggle("hidden", cam.health !== "Down");
  trackHealthChange(cam);

  if (cam.health === "Down") {
    card.detections.textContent = cam.lastError ?? "feed unreachable";
    return;
  }
  if (lastFetched.get(cam.id) === cam.lastSuccess) return;
  try {
    const frame = await fetchJson(`/api/frames/${cam.id}`);
    lastFetched.set(cam.id, cam.lastSuccess);
    card.img.src = `data:image/jpeg;base64,${frame.imageBase64}`;
    card.acquiring.classList.add("hidden");
    drawBoxes(card.overlay, frame.detections);
    card.detections.textContent = frame.detections.length
      ? frame.detections.map(d => `${d.label} ${(d.confidence * 100).toFixed(0)}%`).join(" · ")
      : "no objects detected";

    if (lastSeen.get(cam.id) !== frame.capturedAt) {
      lastSeen.set(cam.id, frame.capturedAt);
      if (frame.detections.length) {
        const summary = Object.entries(
          frame.detections.reduce((m, d) => ((m[d.label] = (m[d.label] ?? 0) + 1), m), {})
        ).map(([l, n]) => (n > 1 ? `${n}× ${l}` : l)).join(", ");
        logEvent(`${cam.name}: ${summary}`, "detection");
      }
    }
  } catch {
    /* no frame yet */
  }
}

let liveIntervalMs = 1200;
let liveStream = null;
let liveTimer = null;
let liveFacing = "environment";

async function openStream() {
  liveStream?.getTracks().forEach(t => t.stop());
  liveStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: liveFacing, width: { ideal: 1280 } },
    audio: false,
  });
  document.getElementById("live-video").srcObject = liveStream;
}

async function startLive() {
  const status = document.getElementById("live-status");
  if (!navigator.mediaDevices?.getUserMedia) {
    logEvent("live camera unavailable — needs HTTPS (or localhost)", "warn");
    alert("Camera access requires HTTPS or localhost.");
    return;
  }
  try {
    await openStream();
  } catch (err) {
    logEvent(`camera permission denied: ${err.name}`, "warn");
    return;
  }
  document.getElementById("live-panel").classList.remove("hidden");
  document.getElementById("live-cta").classList.add("hidden");
  logEvent("live device camera online", "detection");
  status.textContent = "analyzing…";
  liveTimer = setInterval(analyzeLiveFrame, liveIntervalMs);
}

async function flipLive() {
  if (!liveStream) return;
  liveFacing = liveFacing === "environment" ? "user" : "environment";
  try {
    await openStream();
    document.getElementById("live-overlay").innerHTML = "";
    logEvent(`camera switched to ${liveFacing === "user" ? "front" : "back"}`);
  } catch (err) {
    liveFacing = liveFacing === "environment" ? "user" : "environment";
    try { await openStream(); } catch { /* ignore */ }
    logEvent(`camera switch failed: ${err.name}`, "warn");
  }
}

function stopLive() {
  clearInterval(liveTimer);
  liveStream?.getTracks().forEach(t => t.stop());
  liveStream = null;
  document.getElementById("live-panel").classList.add("hidden");
  document.getElementById("live-cta").classList.remove("hidden");
  logEvent("live device camera stopped");
}

let liveBusy = false;

async function analyzeLiveFrame() {
  const video = document.getElementById("live-video");
  if (!liveStream || video.videoWidth === 0 || liveBusy) return;
  liveBusy = true;
  try {
    await analyzeLiveFrameInner(video);
  } finally {
    liveBusy = false;
  }
}

async function analyzeLiveFrameInner(video) {
  const scale = Math.min(1, 960 / video.videoWidth);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise(r => canvas.toBlob(r, "image/jpeg", 0.7));
  const status = document.getElementById("live-status");
  try {
    const res = await fetch(`/api/analyze?device=browser-${CLIENT_ID}`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: blob,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const detections = await res.json();
    drawBoxes(document.getElementById("live-overlay"), detections);
    document.getElementById("live-detections").textContent = detections.length
      ? detections.map(d => `${d.label} ${(d.confidence * 100).toFixed(0)}%`).join(" · ")
      : "no objects detected";
    status.textContent = `live · ${canvas.width}×${canvas.height}`;
  } catch (err) {
    status.textContent = "analyze failed";
    logEvent(`live analyze failed: ${err.message}`, "warn");
  }
}

async function refresh() {
  try {
    const [cams, stats] = await Promise.all([
      fetchJson("/api/cameras"),
      fetchJson("/api/stats?minutes=10"),
    ]);

    document.getElementById("stat-total").textContent = stats.total;
    document.getElementById("stat-cams-up").textContent =
      `${cams.filter(c => c.health === "Up").length}/${cams.length}`;
    document.getElementById("stat-labels").innerHTML = Object.entries(stats.byLabel)
      .sort((a, b) => b[1] - a[1])
      .map(([label, n]) => `<span class="chip">${label} ${n}</span>`)
      .join("") || `<span class="chip">none yet</span>`;

    await Promise.all(cams.map(updateCamera));
  } catch (err) {
    console.error("refresh failed", err);
  }
}

function tickClock() {
  document.getElementById("clock").textContent =
    new Date().toISOString().slice(11, 19) + " UTC";
}

let pollTimer = null;
let refreshQueued = false;

function setPollInterval(ms) {
  clearInterval(pollTimer);
  pollTimer = setInterval(refresh, ms);
}

function queueRefresh() {
  if (refreshQueued) return;
  refreshQueued = true;
  setTimeout(async () => { refreshQueued = false; await refresh(); }, 400);
}

function initRealtime() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}/ws/detections`;
  let ws;
  let reconnectDelay = 1000;

  function connect() {
    ws = new WebSocket(url);

    ws.addEventListener("open", () => {
      logEvent("realtime link established", "detection");
      setPollInterval(POLL_IDLE_MS);
      reconnectDelay = 1000;
    });

    ws.addEventListener("message", (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "frame" || msg.event === "feedFault") {
          queueRefresh();
        } else if (msg.event === "liveDetections") {
          const m = msg.payload;
          if (m.device && m.device.includes(CLIENT_ID)) return;
          const counts = (m.detections || []).reduce(
            (acc, d) => ((acc[d.label] = (acc[d.label] ?? 0) + 1), acc),
            {}
          );
          const summary = Object.entries(counts)
            .map(([l, n]) => (n > 1 ? `${n}× ${l}` : l))
            .join(", ");
          if (summary) logEvent(`${m.device}: ${summary}`, "detection");
        }
      } catch (err) {
        console.error("ws message parse failed", err);
      }
    });

    ws.addEventListener("close", () => {
      logEvent("realtime link degraded — falling back to polling", "warn");
      setPollInterval(POLL_FALLBACK_MS);
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 15000);
    });

    ws.addEventListener("error", () => {
      try { ws.close(); } catch { /* ignore */ }
    });
  }

  connect();
}

async function init() {
  document.getElementById("cameras").addEventListener("mousemove", e => {
    const card = e.target.closest(".camera");
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${e.clientX - r.left}px`);
    card.style.setProperty("--my", `${e.clientY - r.top}px`);
  });

  document.getElementById("live-btn").addEventListener("click", startLive);
  document.getElementById("live-flip").addEventListener("click", flipLive);
  document.getElementById("live-stop").addEventListener("click", stopLive);
  tickClock();
  setInterval(tickClock, 1000);
  try {
    const mode = await fetchJson("/api/mode");
    const badge = document.getElementById("mode-badge");
    const labels = { mock: "MOCK DETECTIONS", azure: "AZURE AI VISION" };
    badge.textContent = labels[mode.provider] ?? mode.provider.toUpperCase();
    badge.classList.add(mode.provider === "mock" ? "mock" : "live");
    logEvent(`pipeline online — ${labels[mode.provider] ?? mode.provider}`, "detection");
  } catch { /* non-fatal */ }
  await refresh();
  setPollInterval(POLL_FALLBACK_MS);
  initRealtime();
}

init();
