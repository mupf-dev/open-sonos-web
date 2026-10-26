"use strict";

/* ================================================================ Hilfen */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (s) => { s = Math.max(0, Math.floor(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = String(s % 60).padStart(2, "0"); return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`; };
const store = { get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

const ICONS = {
  play: ['<path d="M7 4.6v14.8a.8.8 0 0 0 1.2.7l12.3-7.4a.8.8 0 0 0 0-1.4L8.2 3.9A.8.8 0 0 0 7 4.6z"/>', 1],
  pause: ['<rect x="6" y="4.5" width="4.2" height="15" rx="1.2"/><rect x="13.8" y="4.5" width="4.2" height="15" rx="1.2"/>', 1],
  next: ['<path d="M4.5 5.6v12.8a.8.8 0 0 0 1.2.7l10-6.4a.8.8 0 0 0 0-1.4l-10-6.4a.8.8 0 0 0-1.2.7z"/><rect x="17" y="4.5" width="2.6" height="15" rx="1.1"/>', 1],
  prev: ['<path d="M19.5 5.6v12.8a.8.8 0 0 1-1.2.7l-10-6.4a.8.8 0 0 1 0-1.4l10-6.4a.8.8 0 0 1 1.2.7z"/><rect x="4.4" y="4.5" width="2.6" height="15" rx="1.1"/>', 1],
  shuffle: ['<path d="M16 4h4v4M4 20 20 4M20 16v4h-4M14.5 14.5 20 20M4 4l5 5"/>'],
  repeat: ['<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>'],
  vol: ['<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9.5 9.5 0 0 1 0 13"/>'],
  mute: ['<path d="M11 5 6 9H3v6h3l5 4z"/><path d="m22 9-6 6M16 9l6 6"/>'],
  more: ['<circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/>', 1],
  music: ['<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'],
  sun: ['<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'],
  moon: ['<path d="M20.5 13.5A8.5 8.5 0 1 1 10.5 3.5a6.6 6.6 0 0 0 10 10z"/>'],
  auto: ['<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>'],
  search: ['<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'],
  trash: ['<path d="M4 7h16M9 7V4h6v3M18 7l-.8 13H6.8L6 7M10 11v6M14 11v6"/>'],
  plus: ['<path d="M12 5v14M5 12h14"/>'],
  close: ['<path d="M18 6 6 18M6 6l12 12"/>'],
  chevron: ['<path d="m9 6 6 6-6 6"/>'],
  drag: ['<path d="M9 6h.01M9 12h.01M9 18h.01M15 6h.01M15 12h.01M15 18h.01" stroke-width="3"/>'],
  sleep: ['<path d="M20.5 13.5A8.5 8.5 0 1 1 10.5 3.5a6.6 6.6 0 0 0 10 10z"/><path d="M15 3h4l-4 4h4"/>'],
  tv: ['<rect x="2.5" y="6.5" width="19" height="13" rx="2"/><path d="m16 2.5-4 4-4-4"/>'],
  input: ['<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5"/>'],
  queue: ['<path d="M3 6h13M3 12h13M3 18h8M16 15v6l5-3z"/>'],
  addq: ['<path d="M3 6h12M3 12h12M3 18h7M18 14v8M14 18h8"/>'],
  nextup: ['<path d="M3 6h12M3 12h7M14 14l7 4-7 4z"/>'],
  edit: ['<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/>'],
  alarm: ['<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M5 3 2 6M19 3l3 3"/>'],
  speaker: ['<rect x="5" y="2" width="14" height="20" rx="3"/><circle cx="12" cy="14" r="4"/><path d="M12 6.5h.01" stroke-width="2.6"/>'],
  link: ['<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>'],
  unlink: ['<path d="M15 7h2a5 5 0 0 1 0 10h-2M9 17H7A5 5 0 0 1 7 7h2"/>'],
  fade: ['<path d="M3 18c6 0 12-12 18-12M3 6c6 0 12 12 18 12"/>'],
  folder: ['<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'],
  radio: ['<rect x="2.5" y="8" width="19" height="13" rx="2"/><path d="m6 8 11-5"/><circle cx="15.5" cy="14.5" r="3"/><path d="M6 12.5h4M6 16.5h4"/>'],
  star: ['<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3l-5.5 2.9 1-6.2L3 9.6l6.2-.9z"/>'],
  save: ['<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h7M8 21v-7h8v7"/>'],
  refresh: ['<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'],
  person: ['<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'],
  album: ['<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>'],
  video: ['<rect x="2.5" y="5.5" width="14" height="13" rx="2"/><path d="m16.5 10 5-3v10l-5-3z"/>'],
  expand: ['<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'],
  shrink: ['<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>'],
  stage: ['<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="12" cy="12" r="4.2"/><path d="M12 12h.01" stroke-width="2.6"/>'],
  list: ['<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" />'],
};
const icon = (n, cls = "") => { const [p, fill] = ICONS[n] || ICONS.music; return `<svg viewBox="0 0 24 24" class="${fill ? "fill " : ""}${cls}" aria-hidden="true">${p}</svg>`; };
const mosaic = (arts, cls = "") =>
  `<div class="thumb mosaic ${cls}">${arts.slice(0, 4).map((a) => `<i style="background-image:url(&quot;${esc(a)}&quot;)"></i>`).join("")}</div>`;
const thumb = (url, cls = "", fallback = "music") =>
  `<div class="thumb ${cls}"${url ? ` style="background-image:url(&quot;${esc(url)}&quot;)"` : ""}>${url ? "" : icon(fallback)}</div>`;
const KIND_ICON = { musicArtist: "person", person: "person", musicAlbum: "album", playlistContainer: "list", musicGenre: "music", container: "folder", audioBroadcast: "radio", favorite: "star" };

/* ================================================================ API */
async function api(path, opts = {}) {
  const r = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body !== undefined ? { "Content-Type": "application/json" } : {},
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.code ? _(`err.${data.code}`, data.params || {}, data.error) : (data.error || data.detail || _("err.http", { status: r.status })));
  return data;
}
const post = (p, b = {}) => api(p, { method: "POST", body: b });
const zone = (action, body = {}) => post(`/api/zones/${encodeURIComponent(S.group.coordinator)}/${action}`, body);
async function act(fn, msg) {
  try { await fn(); if (msg) toast(msg); } catch (e) { toast(e.message); }
  refreshSoon();
}

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 2600);
}

/* ================================================================ Zustand */
const S = {
  system: null, state: null, stateAt: 0, group: null,
  sel: store.get("room", ""), view: store.get("view", "now"),
  busy: false, pending: {}, settings: {}, seekUntil: 0,
  lib: { root: "A:ALBUMARTIST", stack: [], search: "" },
  queueKey: "", pollTimer: null,
};

function override(key, value) {
  const p = S.pending[key];
  return p && p.until > Date.now() ? p.value : value;
}
function setPending(key, value) { S.pending[key] = { value, until: Date.now() + 2500 }; }

const throttles = {};
function throttle(key, fn, wait = 180) {
  const t = throttles[key] || (throttles[key] = { last: 0, timer: null });
  const run = () => { t.last = Date.now(); t.timer = null; fn(); };
  clearTimeout(t.timer);
  if (Date.now() - t.last >= wait) run(); else t.timer = setTimeout(run, wait - (Date.now() - t.last));
}

function pickGroup() {
  const groups = S.state?.groups || [];
  S.group = groups.find((g) => g.members.some((m) => m.uid === S.sel)) || groups.find((g) => g.uid === S.sel) || groups[0] || null;
  if (S.group && !S.group.members.some((m) => m.uid === S.sel)) S.sel = S.group.coordinator;
}

async function poll() {
  clearTimeout(S.pollTimer);
  try {
    const st = await api("/api/state");
    S.state = st;
    S.stateAt = performance.now();
    pickGroup();
    renderLive();
  } catch (e) {
    if (!S.state) { S.state = { connected: false, groups: [] }; renderLive(); }
  }
  S.pollTimer = setTimeout(poll, document.hidden ? 6000 : 1500);
}
function refreshSoon(ms = 250) { clearTimeout(S.pollTimer); S.pollTimer = setTimeout(poll, ms); }

function setHTML(el, html) {
  if (!el || el._html === html) return;
  if (S.busy && el.contains(document.activeElement)) return;
  el._html = html;
  el.innerHTML = html;
  paintRanges(el);
}
function paintRanges(root = document) {
  $$('input[type=range]', root).forEach((r) => r.style.setProperty("--p", `${((r.value - r.min) / (r.max - r.min || 1)) * 100}%`));
}

/* ================================================================ Rendering: immer sichtbar */
function renderLive() {
  if (!S.state.connected) {
    setHTML($("#rooms"), "");
    setHTML($("#player"), "");
    $("#roomTitle").textContent = _("status.not_connected");
    if (S.view !== "connect") showView("connect");
    return;
  }
  if (S.view === "connect") showView("now");
  renderRooms();
  renderPlayer();
  $("#roomTitle").textContent = S.group?.name || "–";
  if (S.view === "now") setHTML($("#view"), viewNow());
  renderStage();
  if (S.view === "rooms") renderGroupsSection();
  if (S.view === "queue") {
    const key = `${S.group?.coordinator}|${S.group?.track.queue_position}|${S.group?.track.title}`;
    if (key !== S.queueKey) loadQueue();
  }
  tick();
}

function nowLine(g) {
  if (g.state === "ERROR") return _("status.unreachable");
  const t = g.track || {}, title = trackTitle(g);
  if (!title) return _("now.no_music");
  return [title, t.artist].filter(Boolean).join(" · ");
}

function renderRooms() {
  const html = S.state.groups.map((g) => {
    const playing = g.state === "PLAYING";
    return `<button class="room ${g === S.group ? "active" : ""}" data-act="room" data-uid="${esc(g.coordinator)}">
      ${thumb(g.track?.art, "", "speaker")}
      <div class="meta"><div class="name ellipsis">${esc(g.name)}</div>
      <div class="np ellipsis">${playing ? '<span class="eq"><i></i><i></i><i></i></span>' : ""}${esc(nowLine(g))}</div></div>
    </button>`;
  }).join("");
  setHTML($("#rooms"), html);
}

/* Titel zur Anzeige: bei TV/Line-In liefert Sonos keinen, dann den Quellnamen */
function trackTitle(g) {
  const t = g.track || {};
  if (t.title) return t.title;
  return g.source === "TV" || g.source === "LINE_IN" ? _(`source.${g.source}`) : "";
}

function playIcon(g) { return g.state === "PLAYING" ? icon("pause") : icon("play"); }
function repeatBtn(g, cls = "") {
  const on = g.repeat !== "off";
  return `<button class="icon-btn badge repeat ${on ? "" : "off"} ${cls}" data-act="repeat" ${g.repeat === "one" ? 'data-dot="1"' : ""} title="${_(`ctl.repeat_${g.repeat}`)}">${icon("repeat")}</button>`;
}
function canSkip(g) { return g.source !== "RADIO" && g.source !== "TV" && g.source !== "LINE_IN" && g.track.duration > 0; }

function renderPlayer() {
  const g = S.group;
  if (!g) return setHTML($("#player"), "");
  const t = g.track || {};
  const vol = override(`gv:${g.coordinator}`, g.volume);
  const muted = override(`gm:${g.coordinator}`, g.mute);
  setHTML($("#player"), `
    <div class="p-track" data-act="view" data-view="now">
      ${thumb(t.art)}
      <div class="meta" style="min-width:0">
        <div class="t ellipsis">${esc(trackTitle(g) || _("now.no_music"))}</div>
        <div class="s ellipsis">${esc(t.artist || g.name)}</div>
      </div>
    </div>
    <div class="p-center">
      <div class="controls">
        <button class="icon-btn shuffle ${g.shuffle ? "" : "off"}" data-act="shuffle" title="${_("ctl.shuffle")}">${icon("shuffle")}</button>
        <button class="icon-btn prev" data-act="transport" data-arg="previous" title="${_("ctl.previous")}" ${canSkip(g) ? "" : "disabled"}>${icon("prev")}</button>
        <button class="icon-btn play-btn" data-act="toggle" title="${_("ctl.play_pause")}">${playIcon(g)}</button>
        <button class="icon-btn" data-act="transport" data-arg="next" title="${_("ctl.next")}" ${canSkip(g) ? "" : "disabled"}>${icon("next")}</button>
        ${repeatBtn(g)}
      </div>
      ${t.duration ? `<div class="p-progress"><span data-pos>0:00</span><input type="range" class="seek" data-prog min="0" max="${t.duration}" value="0" aria-label="${_("ctl.position")}"><span>${fmt(t.duration)}</span></div>` : ""}
    </div>
    <div class="p-right">
      <span class="p-room ellipsis">${esc(g.name)}</span>
      <button class="icon-btn sm" data-act="stageopen" title="${_("stage.open_title")}">${icon("stage")}</button>
      <button class="icon-btn sm" data-act="gmute" title="${_("ctl.mute")}">${icon(muted ? "mute" : "vol")}</button>
      <input type="range" min="0" max="100" value="${vol}" data-vol="group" aria-label="${_("ctl.volume")}">
    </div>`);
}

/* Fortschritt lokal weiterzählen, ohne neu zu rendern */
function tick() {
  const g = S.group;
  if (!g || !g.track) return;
  const t = g.track;
  let pos = t.position || 0;
  if (g.state === "PLAYING") pos += (performance.now() - S.stateAt) / 1000;
  if (t.duration) pos = Math.min(pos, t.duration);
  $$("[data-prog]").forEach((r) => {
    if (S.busy && document.activeElement === r) return;
    if (Date.now() < S.seekUntil) return;
    r.value = Math.floor(pos);
    r.style.setProperty("--p", t.duration ? `${(pos / t.duration) * 100}%` : "0%");
  });
  $$("[data-pos]").forEach((el) => { el.textContent = fmt(pos); });
  followLyrics(pos);
  syncVideo();
  $$("[data-sleep]").forEach((el) => {
    const left = g.sleep ? g.sleep - (performance.now() - S.stateAt) / 1000 : 0;
    el.textContent = left > 0 ? _("sleep.remaining", { time: fmt(left) }) : _("sleep.label");
  });
}
setInterval(tick, 500);

/* ================================================================ Bühne: alternative „Jetzt läuft“-Ansicht */
S.nowMode = store.get("nowMode", "classic");
S.stagePanel = store.get("stagePanel", "lyrics");
S.media = { key: null };
S.lyricIdx = -1;

const stageActive = () => S.view === "now" && S.nowMode === "stage" && S.state?.connected && S.group;
const mediaKey = (g) => `${g.coordinator}|${g.track?.artist}|${g.track?.title}`;

function renderStage() {
  const el = $("#stage");
  if (!stageActive()) {
    if (el.classList.contains("open")) { stopVideo(); el.classList.remove("open"); el.innerHTML = ""; }
    document.body.classList.remove("staged");
    return;
  }
  el.classList.add("open");
  document.body.classList.add("staged");
  if (!$("#stageContent")) el.innerHTML = '<div class="stage-content" id="stageContent"></div><div class="stage-video" id="stageVideo" hidden></div>';
  const content = $("#stageContent");
  const g = S.group, t = g.track || {};
  if (S.media.key !== mediaKey(g)) loadMedia(g);
  const panel = S.stagePanel;
  const v = S.video, vid = S.stageVideo && v.id, front = vid && S.videoMode === "front";
  const videoLabel = S.stageVideo && v.candidates && !v.id ? _("stage.video_none") : _("stage.video");
  const ytLink = vid ? `https://www.youtube.com/watch?v=${v.id}` : `https://www.youtube.com/results?search_query=${encodeURIComponent(`${t.artist} ${t.title}`)}`;
  const gvol = override(`gv:${g.coordinator}`, g.volume), gmute = override(`gm:${g.coordinator}`, g.mute);
  const pill = (id, label) => `<button class="pill ${panel === id ? "active" : ""}" data-act="stagepanel" data-panel="${id}">${label}</button>`;
  const before = content._html;
  setHTML(content, `
    <div class="stage-bg"${t.art ? ` style="background-image:url(&quot;${esc(t.art)}&quot;)"` : ""}></div>
    <div class="stage-shade"></div>
    <div class="stage-top chrome">
      <div class="stage-room ellipsis">${esc(g.name)}${sourceLabel(g) ? " · " + esc(sourceLabel(g)) : ""}</div>
      <div class="stage-tools">
        ${pill("lyrics", _("stage.lyrics"))}${pill("artist", _("stage.artist"))}${pill("queue", _("stage.up_next"))}
        ${t.title && t.artist ? `<button class="pill ${S.stageVideo ? "active" : ""}" data-act="stagevideo" title="${_("stage.video_title")}">${videoLabel}</button>` : ""}
        ${vid ? `<span class="seg" title="${_("stage.video_mode_title")}">
          <button class="${S.videoMode === "bg" ? "active" : ""}" data-act="videomode" data-mode="bg">${_("stage.video_bg")}</button><button class="${front ? "active" : ""}" data-act="videomode" data-mode="front">${_("stage.video_front")}</button></span>` : ""}
        ${vid ? `<span class="vid-offset" title="${_("stage.offset_title")}">
          <button class="icon-btn sm" data-act="vidoffset" data-d="-1">−</button><span>${v.offset > 0 ? "+" : ""}${v.offset} s</span><button class="icon-btn sm" data-act="vidoffset" data-d="1">+</button></span>` : ""}
        ${t.title && t.artist ? `<a class="icon-btn" title="${_("stage.open_youtube")}" target="_blank" rel="noopener" href="${esc(ytLink)}">${icon("video")}</a>` : ""}
        <button class="icon-btn" data-act="fullscreen" title="${_("stage.fullscreen")}">${icon(document.fullscreenElement ? "shrink" : "expand")}</button>
        <button class="icon-btn" data-act="stageclose" title="${_("stage.close")}">${icon("close")}</button>
      </div>
    </div>
    <div class="stage-main${front ? " has-video" : ""}">
      ${front ? `<div class="stage-video-slot" id="videoSlot"></div>` : thumb(t.art, "stage-cover")}
      ${panel ? `<div class="stage-panel" id="stagePanel">${stagePanelHTML(g)}</div>` : ""}
    </div>
    <div class="stage-bottom">
      <div class="stage-title">
        <div class="t">${esc(trackTitle(g) || _("now.no_music"))}</div>
        <div class="s ellipsis">${esc([t.artist, t.album].filter(Boolean).join(" · "))}</div>
      </div>
      <div class="stage-controls chrome">
        <div class="controls">
          <button class="icon-btn" data-act="transport" data-arg="previous" title="${_("ctl.previous")}" ${canSkip(g) ? "" : "disabled"}>${icon("prev")}</button>
          <button class="icon-btn play-btn" data-act="toggle" title="${_("ctl.play_pause")}">${playIcon(g)}</button>
          <button class="icon-btn" data-act="transport" data-arg="next" title="${_("ctl.next")}" ${canSkip(g) ? "" : "disabled"}>${icon("next")}</button>
        </div>
        ${t.duration ? `<div class="p-progress"><span data-pos>0:00</span><input type="range" class="seek" data-prog min="0" max="${t.duration}" value="0" aria-label="${_("ctl.position")}"><span>${fmt(t.duration)}</span></div>` : `<div class="grow"></div>`}
        <div class="stage-vol">
          <button class="icon-btn sm" data-act="gmute" title="${_("ctl.mute")}">${icon(gmute ? "mute" : "vol")}</button>
          <input type="range" min="0" max="100" value="${gvol}" data-vol="group" aria-label="${_("ctl.volume")}">
        </div>
      </div>
    </div>`);
  if (content._html !== before) S.lyricIdx = -1;
  placeVideo();
}

/* ---------------------------------------------------------------- Musikvideo (stumm, synchron zu Sonos) */
S.stageVideo = store.get("stageVideo", "on") === "on";
S.videoMode = store.get("videoMode", "bg");  // bg: unscharf im Hintergrund, front: statt des Covers
S.video = { key: null };
let ytApi = null;
function loadYouTubeApi() {
  if (window.YT?.Player) return Promise.resolve();
  return ytApi ||= new Promise((resolve, reject) => {
    window.onYouTubeIframeAPIReady = resolve;
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.onerror = () => { ytApi = null; reject(new Error(_("stage.youtube_unreachable"))); };
    document.head.append(s);
  });
}

function currentPos() {
  const g = S.group, t = g?.track || {};
  return (t.position || 0) + (g?.state === "PLAYING" ? (performance.now() - S.stateAt) / 1000 : 0);
}

async function loadVideo(g) {
  const t = g.track || {}, key = mediaKey(g);
  S.video = { key, candidates: null, idx: 0, id: null, offset: 0 };
  if (!S.stageVideo || !t.artist || !t.title || ["TV", "LINE_IN"].includes(g.source)) { S.video.candidates = []; stopVideo(); return; }
  try {
    const q = `artist=${encodeURIComponent(t.artist)}&title=${encodeURIComponent(t.title)}&duration=${t.duration || 0}`;
    const list = await api(`/api/media/video?${q}`);
    if (S.video.key !== key) return;
    S.video.candidates = list;
    startVideo();
  } catch { if (S.video.key === key) { S.video.candidates = []; stopVideo(); renderStage(); } }
}

function startVideo() {
  const v = S.video, c = v.candidates?.[v.idx];
  if (!c) { v.id = null; stopVideo(); renderStage(); return; }
  v.id = c.id;
  renderStage();
  loadYouTubeApi().then(() => {
    if (S.video !== v || !$("#stageVideo")) return;
    const start = Math.max(0, currentPos() + v.offset);
    if (S.yt && S.ytReady) { S.yt.loadVideoById({ videoId: c.id, startSeconds: start }); S.yt.mute(); return; }
    $("#stageVideo").innerHTML = '<div id="ytPlayer"></div>';
    S.yt = new YT.Player("ytPlayer", {
      host: "https://www.youtube-nocookie.com",
      videoId: c.id,
      playerVars: { autoplay: 1, mute: 1, controls: 0, disablekb: 1, fs: 0, iv_load_policy: 3, playsinline: 1, rel: 0, start: Math.floor(start) },
      events: {
        onReady: (e) => { S.ytReady = true; e.target.mute(); e.target.playVideo(); },
        // Einbetten nicht erlaubt o. Ä. → nächsten Treffer probieren
        onError: () => { S.video.idx++; startVideo(); },
      },
    });
  }).catch(() => { v.candidates = []; v.id = null; renderStage(); });
}

function stopVideo() {
  try { S.yt?.destroy(); } catch {}
  S.yt = null;
  S.ytReady = false;
  const host = $("#stageVideo");
  if (host) { host.innerHTML = ""; host.hidden = true; }
}

/* Video-Ebene: ganzflächig hinter dem Inhalt oder genau über dem Platzhalter */
function placeVideo() {
  const host = $("#stageVideo"), slot = $("#videoSlot");
  if (!host) return;
  const bg = S.videoMode === "bg";
  host.classList.toggle("bg", bg);
  if (!S.video.id || (!bg && !slot)) { host.hidden = true; return; }
  if (bg) { host.removeAttribute("style"); host.hidden = false; return; }
  const r = slot.getBoundingClientRect(), s = $("#stage").getBoundingClientRect();
  Object.assign(host.style, { left: `${r.left - s.left}px`, top: `${r.top - s.top}px`, width: `${r.width}px`, height: `${r.height}px` });
  host.hidden = false;
}
addEventListener("resize", placeVideo);

/* Video folgt Sonos: Play/Pause, Position (mit Versatz), immer stumm */
function syncVideo() {
  placeVideo();
  const p = S.yt;
  if (!p || !S.ytReady || !S.video.id || typeof p.getPlayerState !== "function") return;
  if (!p.isMuted()) p.mute();
  const want = currentPos() + S.video.offset, st = p.getPlayerState();
  if (S.group?.state === "PLAYING") {
    const dur = p.getDuration() || 0;
    if (want < 0 || (dur && want > dur - 0.3)) { if (st === 1) p.pauseVideo(); return; }
    if (st !== 1 && st !== 3) p.playVideo();
    if (Math.abs(p.getCurrentTime() - want) > 1.2 && Date.now() - (S.lastSeek || 0) > 2500) { p.seekTo(want, true); S.lastSeek = Date.now(); }
  } else if (st === 1) p.pauseVideo();
}

function parseLrc(text) {
  return text.split("\n").map((line) => {
    const m = line.match(/^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$/);
    return m ? { t: +m[1] * 60 + +m[2], text: m[3] } : null;
  }).filter(Boolean);
}

function stagePanelHTML(g) {
  const m = S.media, t = g.track || {};
  const loading = `<div class="stage-note">${_("common.loading")}</div>`;
  if (S.stagePanel === "lyrics") {
    if (!t.artist || !t.title) return `<div class="stage-note">${_("stage.lyrics_no_source")}</div>`;
    if (m.lyrics === undefined) return loading;
    if (!m.lyrics) return `<div class="stage-note">${_("stage.lyrics_none")}</div>`;
    if (m.lyrics.instrumental) return `<div class="stage-note">${_("stage.instrumental")}</div>`;
    const lines = m.lyrics.synced ? parseLrc(m.lyrics.synced) : null;
    const body = lines?.length
      ? lines.map((l) => `<p class="line" data-t="${l.t}">${esc(l.text) || "♪"}</p>`).join("")
      : `<div class="plain">${esc(m.lyrics.plain || "")}</div>`;
    return `<div class="lyrics">${body}</div><div class="stage-source">${esc(_("stage.lyrics_source", { source: m.lyrics.source || "LRCLIB" }))}</div>`;
  }
  if (S.stagePanel === "artist") {
    if (!t.artist) return `<div class="stage-note">${_("stage.artist_none")}</div>`;
    if (m.artist === undefined) return loading;
    if (!m.artist) return `<div class="stage-note">${esc(_("stage.artist_not_found", { name: t.artist }))}</div>`;
    const a = m.artist;
    return `<div class="artist-card">
      ${a.image ? `<img src="${esc(a.image)}" alt="" loading="lazy">` : ""}
      <h3>${esc(a.name)}</h3>${a.description ? `<div class="muted">${esc(a.description)}</div>` : ""}
      <p>${esc(a.extract || "")}</p>
      ${a.url ? `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(_("stage.read_more", { source: a.source }))}</a>` : ""}
    </div>`;
  }
  if (S.stagePanel === "queue") {
    if (m.queue === undefined) return loading;
    if (!m.queue.length) return `<div class="stage-note">${_("stage.queue_empty")}</div>`;
    return `<div class="list">${m.queue.map((it) => `<div class="row clickable" data-act="qplay" data-index="${it.index}">
      ${thumb(it.art)}<div class="meta"><div class="t ellipsis">${esc(it.title)}</div><div class="s ellipsis">${esc(it.subtitle)}</div></div></div>`).join("")}</div>`;
  }
  return "";
}

async function loadMedia(g) {
  const key = mediaKey(g), t = g.track || {};
  S.media = { key };
  const skip = !t.artist || !t.title || ["TV", "LINE_IN"].includes(g.source);
  const q = (o) => Object.entries(o).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  const done = (field, value) => { if (S.media.key === key) { S.media[field] = value; renderStage(); } };
  if (skip) { S.media.lyrics = null; S.media.artist = null; }
  else {
    api(`/api/media/lyrics?${q({ artist: t.artist, title: t.title, album: t.album || "", duration: t.duration || 0 })}`)
      .then((d) => done("lyrics", d && (d.synced || d.plain || d.instrumental) ? d : null)).catch(() => done("lyrics", null));
    api(`/api/media/artist?${q({ name: t.artist })}`).then((d) => done("artist", d?.name ? d : null)).catch(() => done("artist", null));
  }
  if (S.stagePanel === "queue") loadStageQueue();
  loadVideo(g);
}

async function loadStageQueue() {
  const g = S.group, key = S.media.key;
  try {
    const start = Math.max(0, g.track.queue_position || 0);
    const q = await api(`/api/zones/${encodeURIComponent(g.coordinator)}/queue?start=${start}&count=12`);
    if (S.media.key === key) { S.media.queue = q.items; renderStage(); }
  } catch { if (S.media.key === key) { S.media.queue = []; renderStage(); } }
}

/* aktuelle Songtext-Zeile hervorheben und mittig halten */
function followLyrics(pos) {
  const panel = $("#stagePanel");
  if (!panel) return;
  const lines = $$("p.line", panel);
  if (!lines.length) return;
  let idx = -1;
  for (let i = 0; i < lines.length; i++) { if (+lines[i].dataset.t <= pos + 0.25) idx = i; else break; }
  if (idx === S.lyricIdx) return;
  S.lyricIdx = idx;
  lines.forEach((l, i) => l.classList.toggle("active", i === idx));
  if (idx >= 0 && Date.now() > (S.lyricHold || 0)) {
    const l = lines[idx];
    panel.scrollTo({ top: l.offsetTop - panel.clientHeight / 2 + l.clientHeight / 2, behavior: "smooth" });
  }
}

/* Bedienelemente blenden sich nach kurzer Ruhe aus */
let stageIdleTimer;
function stageWake() {
  const el = $("#stage");
  el.classList.remove("idle");
  clearTimeout(stageIdleTimer);
  stageIdleTimer = setTimeout(() => { if (S.group?.state === "PLAYING" && !S.busy && !$("#menu").classList.contains("open")) el.classList.add("idle"); }, 3500);
}
["mousemove", "touchstart", "keydown", "pointerdown"].forEach((ev) => document.addEventListener(ev, () => { if ($("#stage").classList.contains("open")) stageWake(); }, { passive: true }));
document.addEventListener("wheel", (e) => { if (e.target.closest?.("#stagePanel")) S.lyricHold = Date.now() + 5000; }, { passive: true });
document.addEventListener("touchmove", (e) => { if (e.target.closest?.("#stagePanel")) S.lyricHold = Date.now() + 5000; }, { passive: true });
document.addEventListener("fullscreenchange", () => { if ($("#stageContent")) $("#stageContent")._html = null; renderStage(); });

/* ================================================================ Views */
const VIEWS = { now: () => viewNow(), queue: loadQueue, favorites: loadFavorites, playlists: loadPlaylists, library: loadLibrary, alarms: loadAlarms, rooms: loadRooms, connect: viewConnect };

function showView(v, push = true) {
  if (!VIEWS[v]) v = "now";
  S.view = v;
  if (v !== "connect") store.set("view", v);
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  const el = $("#view");
  el._html = null;
  el.scrollTop = 0;
  if (v === "now") setHTML(el, viewNow());
  else if (v === "connect") viewConnect();
  else { el.innerHTML = `<div class="skeleton">${_("common.loading")}</div>`; VIEWS[v](); }
  renderStage();
  if (push) tick();
}

function sourceLabel(g) {
  return _(`source.${g.source || "NONE"}`, {}, (g.source || "").replace(/_/g, " "));
}

function viewNow() {
  const g = S.group;
  if (!g) return `<div class="empty">${icon("speaker")}<div>${_("now.no_rooms")}</div></div>`;
  const t = g.track || {};
  const set = S.settings[g.coordinator];
  if (!set) loadSettings(g.coordinator).then(() => S.view === "now" && setHTML($("#view"), viewNow()));
  const sources = [];
  if (set?.is_soundbar) sources.push(`<button class="chip ${g.source === "TV" ? "active" : ""}" data-act="source" data-arg="tv">${_("source.TV")}</button>`);
  if (set?.line_in) sources.push(`<button class="chip ${g.source === "LINE_IN" ? "active" : ""}" data-act="source" data-arg="linein">${_("source.LINE_IN")}</button>`);
  const gvol = override(`gv:${g.coordinator}`, g.volume);
  const gmute = override(`gm:${g.coordinator}`, g.mute);
  const members = g.members.map((m) => {
    const v = override(`v:${m.uid}`, m.volume), mu = override(`m:${m.uid}`, m.mute);
    return `<div class="vol-row">
      <button class="icon-btn sm ${mu ? "off" : ""}" data-act="mute" data-uid="${esc(m.uid)}" title="${_("ctl.mute")}">${icon(mu ? "mute" : "vol")}</button>
      <span class="n ellipsis">${esc(m.name)}</span>
      <input type="range" min="0" max="100" value="${v}" data-vol="member" data-uid="${esc(m.uid)}" aria-label="${esc(_("ctl.volume_of", { name: m.name }))}" ${m.fixed_volume ? "disabled" : ""}>
      <span class="v" data-vlabel="${esc(m.uid)}">${v}</span></div>`;
  }).join("");
  return `<div class="now">
    ${thumb(t.art, "cover")}
    <div class="info">
      <div class="source">${esc(g.name)}${sourceLabel(g) ? " · " + esc(sourceLabel(g)) : ""}
        <button class="btn stage-open" data-act="stageopen" title="${_("stage.open_hint")}">${icon("stage")}${_("stage.button")}</button></div>
      <h1>${esc(trackTitle(g) || _("now.no_music"))}</h1>
      <div class="artist">${esc(t.artist || (trackTitle(g) ? "" : _("now.pick_hint")))}</div>
      <div class="album">${esc(t.album || "")}</div>
      ${t.duration ? `<div class="progress">
        <input type="range" class="seek" data-prog min="0" max="${t.duration}" value="0" aria-label="${_("ctl.position")}">
        <div class="times"><span data-pos>0:00</span><span>${fmt(t.duration)}</span></div>
      </div>` : trackTitle(g) ? `<div class="live">${_("now.live")}</div>` : `<div class="progress"></div>`}
      <div class="controls">
        <button class="icon-btn ${g.shuffle ? "" : "off"}" data-act="shuffle" title="${_("ctl.shuffle")}">${icon("shuffle")}</button>
        <button class="icon-btn" data-act="transport" data-arg="previous" title="${_("ctl.previous")}" ${canSkip(g) ? "" : "disabled"}>${icon("prev")}</button>
        <button class="icon-btn play-btn" data-act="toggle" title="${_("ctl.play_pause")}">${playIcon(g)}</button>
        <button class="icon-btn" data-act="transport" data-arg="next" title="${_("ctl.next")}" ${canSkip(g) ? "" : "disabled"}>${icon("next")}</button>
        ${repeatBtn(g)}
      </div>
      <div class="option-row">
        <button class="chip ${g.crossfade ? "active" : ""}" data-act="crossfade">${_("now.crossfade")}</button>
        <button class="chip ${g.sleep ? "active" : ""}" data-act="sleep" data-sleep>${_("sleep.label")}</button>
        ${sources.join("")}
        <button class="chip" data-act="view" data-view="rooms">${_("now.group")}</button>
      </div>
      <div class="panel">
        <h3><span>${_("now.volume")}</span></h3>
        ${g.members.length > 1 ? `<div class="vol-row master">
          <button class="icon-btn sm ${gmute ? "off" : ""}" data-act="gmute" title="${_("ctl.mute_group")}">${icon(gmute ? "mute" : "vol")}</button>
          <span class="n">${_("now.group_label")}</span>
          <input type="range" min="0" max="100" value="${gvol}" data-vol="group" aria-label="${_("ctl.group_volume")}">
          <span class="v" data-vlabel="group">${gvol}</span></div>` : ""}
        ${members}
      </div>
    </div>
  </div>`;
}

/* ---------------------------------------------------------------- Warteschlange */
async function loadQueue() {
  const g = S.group;
  if (!g) return;
  S.queueKey = `${g.coordinator}|${g.track.queue_position}|${g.track.title}`;
  try {
    const q = await api(`/api/zones/${encodeURIComponent(g.coordinator)}/queue?count=500`);
    if (S.view !== "queue") return;
    const cur = g.track.queue_position - 1;
    const rows = q.items.map((it) => `
      <div class="row clickable ${it.index === cur ? "current" : ""}" draggable="true" data-index="${it.index}" data-act="qplay">
        <span class="idx">${it.index === cur && g.state === "PLAYING" ? '<span class="eq"><i></i><i></i><i></i></span>' : it.index + 1}</span>
        ${thumb(it.art)}
        <div class="meta"><div class="t ellipsis">${esc(it.title)}</div><div class="s ellipsis">${esc(it.subtitle)}</div></div>
        <div class="actions">
          <button class="icon-btn sm" data-act="qremove" data-index="${it.index}" title="${_("common.remove")}">${icon("close")}</button>
          <span class="icon-btn sm drag" title="${_("queue.drag")}">${icon("drag")}</span>
        </div>
      </div>`).join("");
    setHTML($("#view"), `
      <div class="head-row">
        <div class="grow"><h1 class="title">${_("queue.title")}</h1><div class="muted">${_("common.tracks", { count: q.total })} · ${esc(g.name)}</div></div>
        <button class="btn" data-act="qsave" ${q.total ? "" : "disabled"}>${icon("save")}${_("queue.save")}</button>
        <button class="btn danger" data-act="qclear" ${q.total ? "" : "disabled"}>${icon("trash")}${_("queue.clear")}</button>
      </div>
      ${q.total ? `<div class="list" id="queueList">${rows}</div>${q.total > q.items.length ? `<div class="muted" style="padding:12px">${_("queue.more", { count: q.total - q.items.length })}</div>` : ""}`
        : `<div class="empty">${icon("queue")}<div>${_("queue.empty")}</div></div>`}`);
  } catch (e) { setHTML($("#view"), `<div class="empty">${esc(e.message)}</div>`); }
}

/* ---------------------------------------------------------------- Favoriten & Playlists */
function tile(it, opts = {}) {
  const act = opts.open || it.browse_id ? "open" : it.playable ? "playitem" : "unavailable";
  return `<div class="tile${act === "unavailable" ? " unplayable" : ""}" data-id="${esc(it.id)}">
    <button style="width:100%;text-align:left" data-act="${act}" data-id="${esc(it.browse_id || it.id)}" data-title="${esc(it.title)}" >
      ${it.arts?.length >= 4 ? mosaic(it.arts) : thumb(it.art, "", KIND_ICON[it.kind] || (it.stream ? "radio" : "music"))}
      <div class="t ellipsis">${esc(it.title)}</div><div class="s ellipsis">${esc(it.subtitle || (it.count != null ? _("common.tracks", { count: it.count }) : ""))}</div>
    </button>
    ${it.playable ? `<button class="play-fab" data-act="playitem" data-id="${esc(it.id)}" title="${_("common.play")}">${icon("play")}</button>` : ""}
    ${opts.menu !== false && !it.stream && it.playable ? `<button class="icon-btn sm" style="position:absolute;right:0;bottom:2px" data-act="itemmenu" data-id="${esc(it.id)}" data-title="${esc(it.title)}" ${opts.playlist ? 'data-playlist="1"' : ""} title="${_("common.options")}">${icon("more")}</button>` : ""}
  </div>`;
}

async function loadFavorites() {
  try {
    const items = await api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/favorites`);
    S.favs = items;
    if (S.view !== "favorites") return;
    setHTML($("#view"), `<div class="head-row"><div class="grow"><h1 class="title">${_("fav.title")}</h1><div class="muted">${_("common.entries", { count: items.length })}</div></div></div>
      ${items.length ? `<div class="grid">${items.map((i) => tile(i)).join("")}</div>`
        : `<div class="empty">${icon("star")}<div>${_("fav.empty")}</div></div>`}`);
  } catch (e) { setHTML($("#view"), `<div class="empty">${esc(e.message)}</div>`); }
}

async function loadPlaylists() {
  try {
    const items = await api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/playlists`);
    if (S.view !== "playlists") return;
    S.playlists = items;
    if (items.some((i) => i.covers_pending)) setTimeout(() => S.view === "playlists" && loadPlaylists(), 2500);
    setHTML($("#view"), `<div class="head-row"><div class="grow"><h1 class="title">${_("pl.title")}</h1><div class="muted">${_("pl.count", { count: items.length })}</div></div></div>
      ${items.length ? `<div class="grid">${items.map((i) => tile(i, { open: true, playlist: true })).join("")}</div>`
        : `<div class="empty">${icon("list")}<div>${_("pl.empty")}</div></div>`}`);
  } catch (e) { setHTML($("#view"), `<div class="empty">${esc(e.message)}</div>`); }
}

/* ---------------------------------------------------------------- Bibliothek */
const LIB_ROOTS = [
  ["A:ALBUMARTIST", "lib.artists"], ["A:ALBUM", "lib.albums"], ["A:TRACKS", "lib.tracks"], ["A:GENRE", "lib.genres"],
  ["A:COMPOSER", "lib.composers"], ["A:PLAYLISTS", "lib.imported"], ["S:", "lib.folders"],
];

async function loadLibrary(more = false) {
  const L = S.lib;
  const level = L.stack[L.stack.length - 1];
  const id = level ? level.id : L.root;
  const search = !level && L.search && searchable(L.root) ? L.search : "";
  if (!S.services) await loadServices();
  const start = more ? L.items.length : 0;
  try {
    const res = await api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/browse?id=${encodeURIComponent(id)}&start=${start}&count=120${search ? `&search=${encodeURIComponent(search)}` : ""}`);
    if (S.view !== "library") return;
    L.items = more ? L.items.concat(res.items) : res.items;
    L.total = res.total;
    renderLibrary();
  } catch (e) { setHTML($("#view"), libHeader() + `<div class="empty">${esc(e.message)}</div>`); }
}

const svcRoot = (id) => `svc:${id.split(":")[1]}:container:root`;
const searchable = (root) => root.startsWith("A:") || root.startsWith("svc:");
function rootLabel(root) {
  if (root === "SQ:") return _("pl.short");
  if (root.startsWith("svc:")) return (S.services || []).find((x) => x.root === root)?.name || _("lib.service");
  return _((LIB_ROOTS.find((r) => r[0] === root) || [, "lib.title"])[1]);
}
async function loadServices() {
  try { S.services = await api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/services`); } catch { S.services = []; }
  return S.services;
}

function libHeader() {
  const L = S.lib;
  const rootName = rootLabel(L.root);
  const roots = [...(S.services || []).filter((x) => x.linked).map((x) => [x.root, x.name]), ...LIB_ROOTS.map(([id, k]) => [id, _(k)])];
  const crumbs = L.stack.length ? `<div class="crumbs"><button data-act="crumb" data-depth="0">${esc(rootName)}</button>${L.stack.map((s, i) => i === L.stack.length - 1
    ? `<span>/</span><b>${esc(s.title)}</b>` : `<span>/</span><button data-act="crumb" data-depth="${i + 1}">${esc(s.title)}</button>`).join("")}</div>` : "";
  return `<div class="head-row">
      <div class="grow"><h1 class="title">${L.root === "SQ:" ? _("lib.playlist") : L.root.startsWith("svc:") ? esc(rootName) : _("lib.title")}</h1></div>
      ${searchable(L.root) && !L.stack.length ? `<label class="search">${icon("search")}<input id="libSearch" type="search" placeholder="${esc(_("lib.search_in", { name: rootName }))}" value="${esc(L.search)}"></label>` : ""}
      <button class="icon-btn" data-act="libupdate" title="${_("lib.reindex")}">${icon("refresh")}</button>
    </div>
    <div class="chips" style="margin-bottom:20px">${roots.map(([id, n]) => `<button class="chip ${L.root === id ? "active" : ""}" data-act="libroot" data-id="${id}">${n}</button>`).join("")}</div>
    ${crumbs}`;
}

/* Startseite eines Musikdienstes: jeder Bereich als Zeile mit horizontal scrollbaren Kacheln */
const shelves = {};
function orderedShelves() {
  const order = S.prefs?.shelfOrder?.[S.lib.root] || [];
  const pos = (id) => { const i = order.indexOf(id); return i < 0 ? order.length : i; };
  return S.lib.items.map((sec, i) => [sec, i]).sort((a, b) => pos(a[0].id) - pos(b[0].id) || a[1] - b[1]).map(([sec]) => sec);
}
function saveShelfOrder(ids) {
  S.prefs = S.prefs || {};
  const shelfOrder = { ...(S.prefs.shelfOrder || {}), [S.lib.root]: ids };
  S.prefs.shelfOrder = shelfOrder;
  renderServiceHome();
  // nacheinander speichern, damit sich schnelle Klicks nicht überholen
  savePrefs = savePrefs.then(() => api("/api/prefs", { method: "PUT", body: { shelfOrder } })).catch((e) => toast(e.message));
}
let savePrefs = Promise.resolve();

function renderServiceHome() {
  const L = S.lib;
  const el = $("#view");
  const secs = orderedShelves();
  const editing = !!S.shelfEdit;
  el._html = null;
  el.innerHTML = libHeader() + `<div class="shelf-toolbar">
      ${editing ? `<span class="muted">${matchMedia("(hover: hover)").matches ? _("shelf.hint_drag") : _("shelf.hint")}</span>
        <button class="btn" data-act="shelfreset">${_("shelf.reset")}</button><button class="btn primary" data-act="shelfedit">${_("common.done")}</button>`
      : `<button class="btn" data-act="shelfedit">${icon("drag")}${_("shelf.arrange")}</button>`}
    </div>` + secs.map((sec, i) => `<section class="shelf-sec${editing ? " editing" : ""}" data-sec="${esc(sec.id)}" ${editing ? 'draggable="true"' : ""}>
      <div class="shelf-head">
        ${editing ? `<span class="drag">${icon("drag")}</span>` : ""}
        <button data-act="open" data-id="${esc(sec.id)}" data-title="${esc(sec.title)}">${esc(sec.title)}${icon("chevron")}</button>
        ${editing ? `<span class="shelf-nav edit">
          <button class="icon-btn sm" data-act="shelfmove" data-dir="-1" title="${_("shelf.up")}" ${i === 0 ? "disabled" : ""}>${icon("chevron", "up")}</button>
          <button class="icon-btn sm" data-act="shelfmove" data-dir="1" title="${_("shelf.down")}" ${i === secs.length - 1 ? "disabled" : ""}>${icon("chevron", "down")}</button></span>` : `<span class="shelf-nav"><button class="icon-btn sm" data-act="shelfscroll" data-dir="-1" title="${_("ctl.previous")}">${icon("chevron", "flip")}</button><button class="icon-btn sm" data-act="shelfscroll" data-dir="1" title="${_("ctl.next")}">${icon("chevron")}</button></span>`}
      </div>
      <div class="shelf" id="shelf-${i}">${shelfBody(shelves[sec.id])}</div>
    </section>`).join("");
  secs.forEach(async (sec, i) => {
    if (shelves[sec.id]) return;
    try {
      const res = await api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/browse?id=${encodeURIComponent(sec.id)}&count=24`);
      shelves[sec.id] = res.items;
    } catch (e) { shelves[sec.id] = []; }
    const box = $(`#shelf-${i}`);
    if (box && S.view === "library" && S.lib.items === L.items) box.innerHTML = shelfBody(shelves[sec.id]);
  });
}
const shelfBody = (items) => items === undefined ? `<div class="skeleton">${_("common.loading")}</div>`
  : items.length ? items.map((i) => tile(i, { open: i.container })).join("") : `<div class="muted">${_("common.no_entries")}</div>`;

function renderLibrary() {
  const L = S.lib;
  const level = L.stack[L.stack.length - 1];
  if (!level && !L.search && L.root.startsWith("svc:") && (L.items || []).length) return renderServiceHome();
  const items = L.items || [];
  const asGrid = items.length && items.filter((i) => i.container && i.art).length > items.length * 0.6;
  let body;
  if (!items.length) body = `<div class="empty">${icon("music")}<div>${L.search ? _("common.no_results") : _("common.no_entries")}</div></div>`;
  else if (asGrid) body = `<div class="grid">${items.map((i) => tile(i, { open: true })).join("")}</div>`;
  else body = `<div class="list">${items.map((i) => itemRow(i)).join("")}</div>`;
  const levelActions = level && level.playable ? `<div class="head-row" style="margin-top:-4px">
      <button class="btn primary" data-act="playitem" data-id="${esc(level.id)}">${icon("play")}${_("common.play")}</button>
      <button class="btn" data-act="itemmenu" data-id="${esc(level.id)}" data-title="${esc(level.title)}" ${level.id.startsWith("SQ:") ? 'data-playlist="1"' : ""}>${icon("more")}${_("common.more")}</button></div>` : "";
  setHTML($("#view"), libHeader() + levelActions + body +
    (L.total > items.length ? `<div style="text-align:center;margin-top:20px"><button class="btn" data-act="libmore">${_("lib.load_more", { shown: items.length, total: L.total })}</button></div>` : ""));
}

function itemRow(it) {
  return `<div class="row ${it.container ? "clickable" : ""}" ${it.container ? `data-act="open" data-id="${esc(it.id)}" data-title="${esc(it.title)}"` : ""}>
    ${thumb(it.art, "", KIND_ICON[it.kind] || (it.container ? "folder" : "music"))}
    <div class="meta"><div class="t ellipsis">${esc(it.title)}</div><div class="s ellipsis">${esc(it.subtitle || "")}</div></div>
    <div class="actions">
      ${it.playable ? `<button class="icon-btn sm" data-act="playitem" data-id="${esc(it.id)}" title="${_("common.play")}">${icon("play")}</button>` : ""}
      ${it.playable ? `<button class="icon-btn sm" data-act="itemmenu" data-id="${esc(it.id)}" data-title="${esc(it.title)}" title="${_("common.options")}">${icon("more")}</button>` : ""}
    </div>
    ${it.container ? `<span class="muted">${icon("chevron")}</span>` : ""}
  </div>`;
}

/* ---------------------------------------------------------------- Wecker */
const dayNames = () => _("days.short");
function recurrenceText(r) {
  if (r === "DAILY") return _("alarm.daily");
  if (r === "WEEKDAYS") return _("alarm.weekdays_short");
  if (r === "WEEKENDS") return _("alarm.weekends_short");
  if (r === "ONCE") return _("alarm.once");
  if (r.startsWith("ON_")) return [1, 2, 3, 4, 5, 6, 0].filter((d) => r.includes(String(d))).map((d) => dayNames()[d]).join(", ");
  return r;
}

async function loadAlarms() {
  try {
    const list = await api("/api/alarms");
    S.alarms = list;
    if (S.view !== "alarms") return;
    setHTML($("#view"), `<div class="head-row"><div class="grow"><h1 class="title">${_("alarm.title")}</h1><div class="muted">${_("alarm.count", { count: list.length })}</div></div>
      <button class="btn primary" data-act="alarmedit">${icon("plus")}${_("alarm.new")}</button></div>
      ${list.length ? list.map((a) => `<div class="alarm ${a.enabled ? "" : "off"}">
          <div class="time">${esc(a.time)}</div>
          <div class="meta"><div><b>${esc(a.room)}</b> · ${esc(recurrenceText(a.recurrence))}</div>
            <div class="muted ellipsis">${esc(a.program || _("alarm.chime"))} · ${esc(_("alarm.volume_n", { n: a.volume }))}${a.duration ? ` · ${esc(_("alarm.minutes", { n: a.duration }))}` : ""}</div></div>
          <button class="icon-btn sm" data-act="alarmedit" data-id="${esc(a.id)}" title="${_("common.edit")}">${icon("edit")}</button>
          <label class="switch" title="${_("alarm.active")}"><input type="checkbox" data-alarm-toggle="${esc(a.id)}" ${a.enabled ? "checked" : ""}><i></i></label>
        </div>`).join("") : `<div class="empty">${icon("alarm")}<div>${_("alarm.empty")}</div></div>`}`);
  } catch (e) { setHTML($("#view"), `<div class="empty">${esc(e.message)}</div>`); }
}

/* ---------------------------------------------------------------- Räume & Einstellungen */
async function loadSettings(uid) {
  try { S.settings[uid] = await api(`/api/speakers/${encodeURIComponent(uid)}/settings`); } catch { S.settings[uid] = S.settings[uid] || null; }
  return S.settings[uid];
}

async function loadRooms() {
  try {
    [S.speakers, S.system] = await Promise.all([api("/api/speakers"), api("/api/system")]);
  } catch (e) { return setHTML($("#view"), `<div class="empty">${esc(e.message)}</div>`); }
  if (S.view !== "rooms") return;
  S.setUid = S.speakers.some((s) => s.uid === S.setUid) ? S.setUid : S.group?.coordinator || S.speakers[0]?.uid;
  const el = $("#view");
  el._html = null;
  el.innerHTML = `
    <div class="head-row"><div class="grow"><h1 class="title">${_("rooms.title")}</h1><div class="muted">${_("rooms.speakers", { count: S.speakers.length })}</div></div>
      <button class="btn" data-act="party">${icon("link")}${_("rooms.party")}</button>
      <button class="btn" data-act="ungroupall">${icon("unlink")}${_("rooms.ungroup_all")}</button></div>
    <h2>${_("rooms.groups")}</h2><div class="cards" id="groupCards"></div>
    <h2>${_("rooms.speaker_settings")}</h2>
    <div class="chips" style="margin-bottom:16px">${S.speakers.map((s) => `<button class="chip ${s.uid === S.setUid ? "active" : ""}" data-act="setuid" data-uid="${esc(s.uid)}">${esc(s.name)}</button>`).join("")}</div>
    <div id="speakerSettings"><div class="skeleton">${_("common.loading")}</div></div>
    <h2>${_("rooms.services")}</h2><div id="servicesPanel"><div class="skeleton">${_("common.loading")}</div></div>
    <h2>${_("rooms.language")}</h2><div id="langPanel"></div>
    <h2>${_("rooms.system")}</h2><div id="systemPanel"></div>`;
  renderGroupsSection();
  renderSystemPanel();
  renderLangPanel();
  renderServicesPanel();
  renderSpeakerSettings();
}

function renderGroupsSection() {
  const el = $("#groupCards");
  if (!el || !S.state?.groups) return;
  setHTML(el, S.state.groups.map((g) => `<div class="card">
    <div class="head-row" style="margin-bottom:8px"><div class="grow"><h4 class="ellipsis">${esc(g.name)}</h4><div class="sub ellipsis">${esc(nowLine(g))}</div></div>
      <button class="btn" data-act="groupedit" data-uid="${esc(g.coordinator)}">${icon("link")}${_("common.edit")}</button></div>
    ${g.members.map((m) => `<div class="member">${icon("speaker")}<span>${esc(m.name)}${m.uid === g.coordinator ? ` <span class="muted">${_("rooms.coordinator")}</span>` : ""}</span>
      ${g.members.length > 1 ? `<button class="icon-btn sm" data-act="unjoin" data-uid="${esc(m.uid)}" title="${_("rooms.unjoin")}">${icon("unlink")}</button>` : ""}</div>`).join("")}
  </div>`).join(""));
}

const eqLabel = (k) => _(`eq.${k}`, {}, k);

async function renderSpeakerSettings() {
  const uid = S.setUid;
  const el = $("#speakerSettings");
  if (!el || !uid) return;
  const s = await loadSettings(uid);
  if (S.view !== "rooms" || S.setUid !== uid) return;
  if (!s) return (el.innerHTML = `<div class="empty">${_("rooms.settings_unavailable")}</div>`);
  const sliders = Object.entries(s.eq).filter(([k]) => s.ranges[k]).map(([k, v]) => `<div class="setting">
      <span>${esc(eqLabel(k))}</span>
      <input type="range" min="${s.ranges[k][0]}" max="${s.ranges[k][1]}" value="${v}" data-setting="${k}" aria-label="${esc(eqLabel(k))}">
      <span class="v" data-svlabel="${k}">${v > 0 && k !== "audio_delay" ? "+" + v : v}</span></div>`).join("");
  const toggles = Object.entries(s.eq).filter(([k]) => !s.ranges[k]).map(([k, v]) => switchRow(eqLabel(k), k, v)).join("");
  el.innerHTML = `<div class="cards">
    <div class="card"><h4 style="margin-bottom:10px">${_("rooms.sound")}</h4>${sliders}${toggles}
      <div style="margin-top:12px"><button class="btn" data-act="eqreset">${_("rooms.sound_reset")}</button></div></div>
    <div class="card"><h4 style="margin-bottom:10px">${_("rooms.device")}</h4>
      <div class="setting toggle-row"><span>${_("rooms.name")}</span><button class="btn" data-act="rename">${icon("edit")}${esc(s.name)}</button></div>
      ${switchRow(_("rooms.status_light"), "status_light", s.status_light)}
      ${s.buttons_enabled !== null ? switchRow(_("rooms.buttons"), "buttons_enabled", s.buttons_enabled) : ""}
      ${s.battery ? `<div class="setting toggle-row"><span>${_("rooms.battery")}</span><span class="muted">${esc(s.battery.Level ?? "–")} % ${s.battery.PowerSource ? "· " + esc(s.battery.PowerSource) : ""}</span></div>` : ""}
      <dl class="info-grid" style="margin-top:14px">
        <dt>${_("rooms.model")}</dt><dd>${esc(s.model)}${s.model_number ? ` (${esc(s.model_number)})` : ""}</dd>
        <dt>${_("rooms.software")}</dt><dd>${esc(s.version || "–")}</dd>
        <dt>${_("rooms.ip")}</dt><dd>${esc(s.ip)}</dd>
        <dt>MAC</dt><dd>${esc(s.mac || "–")}</dd>
        <dt>${_("rooms.serial")}</dt><dd>${esc(s.serial || "–")}</dd>
      </dl></div></div>`;
  paintRanges(el);
}
const switchRow = (label, key, on) => `<div class="setting toggle-row"><span>${esc(label)}</span><label class="switch"><input type="checkbox" data-setting="${key}" ${on ? "checked" : ""}><i></i></label></div>`;

async function renderServicesPanel() {
  const el = $("#servicesPanel");
  if (!el) return;
  const list = await loadServices();
  if (S.view !== "rooms") return;
  el.innerHTML = `<div class="card">
    <div class="sub" style="margin-bottom:8px">${_("svc.hint")}</div>
    ${list.map((x) => `<div class="member"><span>${esc(x.name)} <span class="muted">· ${x.auth === "Anonymous" ? _("svc.anonymous") : x.linked ? _("svc.linked") : _("svc.not_linked")}</span></span>
      ${x.auth === "Anonymous" ? "" : x.linked
        ? `<button class="btn" data-act="svcunlink" data-sid="${esc(x.sid)}" data-name="${esc(x.name)}">${_("svc.unlink")}</button>`
        : `<button class="btn primary" data-act="svclink" data-sid="${esc(x.sid)}" data-name="${esc(x.name)}">${_("svc.link")}</button>`}</div>`).join("") || `<div class="muted">${_("svc.none")}</div>`}
  </div>`;
}

function renderSystemPanel() {
  const el = $("#systemPanel");
  if (!el || !S.system) return;
  el.innerHTML = `<div class="card">${S.system.demo ? `<p class="muted" style="margin:0">${_("system.demo")}</p>` : `
    <div class="sub" style="margin-bottom:8px">${_("system.hosts")}</div>
    ${S.system.hosts.map((h) => `<div class="member"><span>${esc(h)}</span><button class="icon-btn sm" data-act="rmhost" data-host="${esc(h)}" title="${_("common.remove")}">${icon("close")}</button></div>`).join("") || `<div class="muted">${_("system.auto")}</div>`}
    <div class="head-row" style="margin:12px 0 0"><button class="btn" data-act="addhost">${icon("plus")}${_("system.add_ip")}</button></div>`}</div>`;
}

function renderLangPanel() {
  const el = $("#langPanel");
  if (!el) return;
  el.innerHTML = `<div class="card">
    <div class="chips">${I18N.languages.map((l) => `<button class="chip ${l.code === I18N.lang ? "active" : ""}" data-act="setlang" data-code="${esc(l.code)}">${esc(l.name)}</button>`).join("")}</div>
    <div class="sub" style="margin-top:12px">${esc(_("system.language_hint"))}</div></div>`;
}

/* ---------------------------------------------------------------- Verbinden */
function viewConnect() {
  const el = $("#view");
  el._html = null;
  el.innerHTML = `<div class="connect">
    <h1 class="title">${_("connect.title")}</h1>
    <p>${_("connect.p1")}</p>
    <p>${_("connect.p2")}</p>
    <form class="line" id="hostForm"><input class="field" name="host" placeholder="${esc(_("connect.ip_placeholder"))}" inputmode="decimal" required><button class="btn primary">${_("connect.connect")}</button></form>
    <p>${_("connect.p3")}</p>
    <form class="line" id="scanForm"><input class="field" name="network" placeholder="${esc(_("connect.net_placeholder"))}"><button class="btn">${_("connect.search")}</button></form>
  </div>`;
}

/* ================================================================ Menüs & Dialoge */
function openMenu(anchor, html) {
  const m = $("#menu");
  m.innerHTML = html;
  m.classList.add("open");
  const r = anchor.getBoundingClientRect();
  const w = m.offsetWidth, h = m.offsetHeight;
  let x = Math.min(r.right - w, innerWidth - w - 8), y = r.bottom + 6;
  if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 6);
  m.style.left = `${Math.max(8, x)}px`;
  m.style.top = `${y}px`;
}
function closeMenu() { $("#menu").classList.remove("open"); }

function itemMenu(el) {
  const id = el.dataset.id;
  const pl = el.dataset.playlist;
  S.menuItem = { id, title: el.dataset.title };
  openMenu(el, `<div class="label ellipsis">${esc(el.dataset.title || "")}</div>
    <button data-act="mplay" data-mode="replace">${icon("play")}${_("menu.replace")}</button>
    <button data-act="mplay" data-mode="now">${icon("play")}${_("menu.now")}</button>
    <button data-act="mplay" data-mode="next">${icon("nextup")}${_("menu.next")}</button>
    <button data-act="mplay" data-mode="add">${icon("addq")}${_("menu.add")}</button>
    ${id.startsWith("FV:") || id.startsWith("svc:") ? "" : `<button data-act="mtoplaylist">${icon("list")}${_("menu.to_playlist")}</button>`}
    ${pl ? `<hr><button data-act="plrename">${icon("edit")}${_("menu.rename")}</button><button data-act="pldelete">${icon("trash")}${_("menu.delete_playlist")}</button>` : ""}`);
}

function dialog(html, onSubmit, onReady) {
  const d = $("#dialog");
  d.innerHTML = `<form method="dialog">${html}</form>`;
  const form = $("form", d);
  form.addEventListener("submit", async (e) => {
    if (e.submitter?.value === "cancel") return;
    e.preventDefault();
    try { await onSubmit(new FormData(form), form, e.submitter); d.close(); } catch (err) { toast(err.message); }
    refreshSoon();
  });
  d.showModal();
  onReady?.(form);
  paintRanges(d);
}
const cancelBtn = () => `<button class="btn" value="cancel" formnovalidate>${_("common.cancel")}</button>`;

function promptDialog(title, label, value, submitLabel, fn) {
  dialog(`<h3>${esc(title)}</h3><label>${esc(label)}<input class="field" name="v" value="${esc(value || "")}" required autofocus></label>
    <div class="dlg-actions">${cancelBtn()}<button class="btn primary">${esc(submitLabel)}</button></div>`, (fd) => fn(String(fd.get("v")).trim()));
}

function groupDialog(coordUid) {
  const g = S.state.groups.find((x) => x.coordinator === coordUid);
  const all = S.state.groups.flatMap((x) => x.members).sort((a, b) => a.name.localeCompare(b.name));
  dialog(`<h3>${esc(_("group.title", { name: g.name }))}</h3><div class="muted" style="font-size:13px">${_("group.hint")}</div>
    <div class="check-list">${all.map((m) => `<label><input type="checkbox" name="m" value="${esc(m.uid)}" ${g.members.some((x) => x.uid === m.uid) ? "checked" : ""} ${m.uid === coordUid ? "disabled checked" : ""}>${esc(m.name)}</label>`).join("")}</div>
    <div class="dlg-actions">${cancelBtn()}<button class="btn primary">${_("common.apply")}</button></div>`,
  (fd) => post(`/api/zones/${encodeURIComponent(coordUid)}/group`, { members: fd.getAll("m") }));
}

function durLabel(v) {
  return { 60: _("dur.h1"), 90: _("dur.h15"), 120: _("dur.h2") }[v] || _("dur.min", { count: v });
}

async function alarmDialog(id) {
  let favs = [], speakers = [];
  try { [favs, speakers] = await Promise.all([api(`/api/zones/${encodeURIComponent(S.group.coordinator)}/favorites`), api("/api/speakers")]); } catch (e) { return toast(e.message); }
  const a = id ? S.alarms.find((x) => x.id === id) : { time: "07:00", uid: S.group.coordinator, recurrence: "WEEKDAYS", volume: 20, enabled: true, duration: 60, play_mode: "NORMAL", include_linked: false };
  const preset = ["DAILY", "WEEKDAYS", "WEEKENDS", "ONCE"].includes(a.recurrence) ? a.recurrence : "CUSTOM";
  const custom = a.recurrence.startsWith("ON_") ? a.recurrence.slice(3) : "12345";
  dialog(`<h3>${id ? _("alarm.edit") : _("alarm.new")}</h3>
    <label>${_("alarm.time")}<input class="field" type="time" name="time" value="${esc(a.time)}" required style="font-size:28px;font-weight:300"></label>
    <label>${_("alarm.room")}<select class="field" name="uid">${speakers.map((s) => `<option value="${esc(s.uid)}" ${s.uid === a.uid ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></label>
    <label>${_("alarm.recurrence")}<select class="field" name="recurrence" id="recSel">
      ${[["DAILY", _("alarm.daily")], ["WEEKDAYS", _("alarm.weekdays")], ["WEEKENDS", _("alarm.weekends")], ["ONCE", _("alarm.once")], ["CUSTOM", _("alarm.custom")]].map(([v, n]) => `<option value="${v}" ${preset === v ? "selected" : ""}>${n}</option>`).join("")}</select></label>
    <div class="days" id="days" ${preset === "CUSTOM" ? "" : "hidden"}>${[1, 2, 3, 4, 5, 6, 0].map((d) => `<button type="button" data-day="${d}" class="${custom.includes(String(d)) ? "active" : ""}">${esc(dayNames()[d])}</button>`).join("")}</div>
    <label>${_("alarm.music")}<select class="field" name="program_id">
      ${id ? `<option value="keep" selected>${esc(_("alarm.keep", { name: a.program || _("alarm.chime") }))}</option>` : ""}
      <option value="buzzer">${_("alarm.chime")}</option>
      ${favs.map((f) => `<option value="${esc(f.id)}">${esc(f.title)}</option>`).join("")}</select></label>
    <label>${_("alarm.volume")} <span class="muted" id="avl">${a.volume}</span><input type="range" name="volume" min="0" max="100" value="${a.volume}"></label>
    <label>${_("alarm.duration")}<select class="field" name="duration">${[0, 15, 30, 45, 60, 90, 120].map((v) => [v, v ? durLabel(v) : _("alarm.until_off")]).map(([v, n]) => `<option value="${v}" ${(a.duration || 0) === v ? "selected" : ""}>${n}</option>`).join("")}</select></label>
    <label>${_("alarm.play_mode")}<select class="field" name="play_mode">${[["NORMAL", _("alarm.pm_normal")], ["SHUFFLE_NOREPEAT", _("alarm.pm_shuffle")], ["REPEAT_ALL", _("alarm.pm_repeat")], ["SHUFFLE", _("alarm.pm_shuffle_repeat")]].map(([v, n]) => `<option value="${v}" ${a.play_mode === v ? "selected" : ""}>${n}</option>`).join("")}</select></label>
    <label class="inline">${_("alarm.include_linked")}<span class="switch"><input type="checkbox" name="include_linked" ${a.include_linked ? "checked" : ""}><i></i></span></label>
    <label class="inline">${_("alarm.active")}<span class="switch"><input type="checkbox" name="enabled" ${a.enabled ? "checked" : ""}><i></i></span></label>
    <div class="dlg-actions">${id ? `<button class="btn danger" value="delete" style="margin-right:auto">${_("common.delete")}</button>` : ""}${cancelBtn()}<button class="btn primary" value="save">${_("common.save")}</button></div>`,
  async (fd, form, submitter) => {
    if (submitter?.value === "delete") {
      await api(`/api/alarms/${encodeURIComponent(id)}`, { method: "DELETE" });
    } else {
      let rec = fd.get("recurrence");
      if (rec === "CUSTOM") {
        const days = $$("#days .active", form).map((b) => b.dataset.day).sort().join("");
        if (!days) throw new Error(_("alarm.pick_day"));
        rec = `ON_${days}`;
      }
      const body = { time: fd.get("time"), uid: fd.get("uid"), recurrence: rec, program_id: fd.get("program_id"),
        volume: +fd.get("volume"), duration: +fd.get("duration"), play_mode: fd.get("play_mode"),
        include_linked: fd.get("include_linked") === "on", enabled: fd.get("enabled") === "on" };
      await api(id ? `/api/alarms/${encodeURIComponent(id)}` : "/api/alarms", { method: id ? "PUT" : "POST", body });
    }
    loadAlarms();
  },
  (form) => {
    $("#recSel", form).addEventListener("change", (e) => { $("#days", form).hidden = e.target.value !== "CUSTOM"; });
    $$("#days button", form).forEach((b) => b.addEventListener("click", () => b.classList.toggle("active")));
    $("input[name=volume]", form).addEventListener("input", (e) => { $("#avl", form).textContent = e.target.value; });
  });
}

/* ================================================================ Aktionen */
const enc = encodeURIComponent;
const ACTIONS = {
  room(el) { S.sel = el.dataset.uid; store.set("room", S.sel); pickGroup(); closeSheet(); renderLive(); if (S.view !== "now") showView(S.view); },
  view(el) { showView(el.dataset.view); },
  toggle() {
    const g = S.group;
    const playing = g.state === "PLAYING";
    g.state = playing ? "PAUSED_PLAYBACK" : "PLAYING";
    renderLive();
    act(() => zone(playing ? "pause" : "play"));
  },
  transport(el) { act(() => zone(el.dataset.arg)); },
  shuffle() { const g = S.group; act(() => zone("playmode", { shuffle: !g.shuffle, repeat: g.repeat })); },
  repeat() { const g = S.group; const next = { off: "all", all: "one", one: "off" }[g.repeat]; act(() => zone("playmode", { shuffle: g.shuffle, repeat: next })); },
  crossfade() { act(() => zone("crossfade", { enabled: !S.group.crossfade })); },
  sleep(el) {
    openMenu(el, `<div class="label">${_("sleep.label")}</div>${[0, 15, 30, 45, 60, 90, 120]
      .map((v) => `<button data-act="setsleep" data-min="${v}">${icon("sleep")}${v ? durLabel(v) : _("sleep.off")}</button>`).join("")}`);
  },
  setsleep(el) { closeMenu(); act(() => zone("sleep", { minutes: +el.dataset.min || null }), +el.dataset.min ? _("sleep.set") : _("sleep.cleared")); },
  source(el) { act(() => zone("source", { source: el.dataset.arg })); },
  mute(el) {
    const m = S.group.members.find((x) => x.uid === el.dataset.uid);
    const val = !override(`m:${m.uid}`, m.mute);
    setPending(`m:${m.uid}`, val);
    renderLive();
    act(() => post(`/api/zones/${enc(m.uid)}/volume`, { mute: val }));
  },
  gmute() {
    const g = S.group;
    const val = !override(`gm:${g.coordinator}`, g.mute);
    setPending(`gm:${g.coordinator}`, val);
    g.members.forEach((m) => setPending(`m:${m.uid}`, val));
    renderLive();
    act(() => zone("group-volume", { mute: val }));
  },
  qplay(el, ev) { if (ev.target.closest(".actions")) return; act(() => zone("queue", { action: "play", index: +el.dataset.index })); },
  qremove(el) { act(async () => { await zone("queue", { action: "remove", index: +el.dataset.index }); loadQueue(); }); },
  qclear() { if (confirm(_("queue.clear_confirm"))) act(async () => { await zone("queue", { action: "clear" }); loadQueue(); }); },
  qsave() { promptDialog(_("queue.save_title"), _("queue.save_name"), "", _("common.save"), async (title) => { await zone("queue", { action: "save", title }); toast(_("queue.saved")); }); },
  playitem(el) { act(() => zone("play-item", { id: el.dataset.id, mode: "replace", title: el.dataset.title || "" }), _("toast.playing")); },
  itemmenu(el) { itemMenu(el); },
  async svclink(el) {
    const { sid, name } = el.dataset;
    let url;
    try { ({ url } = await post(`/api/zones/${enc(S.group.coordinator)}/services/${enc(sid)}/begin`)); } catch (e) { return toast(e.message); }
    dialog(`<h3>${esc(_("svc.link_title", { name }))}</h3>
      <div class="muted" style="font-size:14px">${_("svc.link_steps", { name: esc(name) })}</div>
      <a class="btn primary" style="align-self:flex-start" href="${esc(url)}" target="_blank" rel="noopener">${esc(_("svc.open_login", { name }))}</a>
      <div class="dlg-actions">${cancelBtn()}<button class="btn primary">${_("common.done")}</button></div>`,
    async () => {
      await post(`/api/zones/${enc(S.group.coordinator)}/services/${enc(sid)}/complete`);
      toast(_("svc.linked_toast", { name }));
      S.services = null;
      renderServicesPanel();
    });
  },
  svcunlink(el) {
    const { sid, name } = el.dataset;
    if (!confirm(_("svc.unlink_confirm", { name }))) return;
    act(async () => { await post(`/api/zones/${enc(S.group.coordinator)}/services/${enc(sid)}/unlink`); S.services = null; renderServicesPanel(); }, _("svc.unlinked_toast", { name }));
  },
  unavailable(el) { toast(_("fav.unavailable", { title: el.dataset.title })); },
  setlang(el) { i18nSet(el.dataset.code); },
  mplay(el) { closeMenu(); const mode = el.dataset.mode; act(() => zone("play-item", { id: S.menuItem.id, mode, title: S.menuItem.title || "" }), { replace: _("toast.playing"), now: _("toast.playing"), next: _("toast.next"), add: _("toast.added") }[mode]); },
  async mtoplaylist(el) {
    let pls = [];
    try { pls = await api(`/api/zones/${enc(S.group.coordinator)}/playlists`); } catch (e) { return toast(e.message); }
    openMenu(el, `<div class="label">${_("menu.to_playlist_title")}</div>${pls.map((p) => `<button data-act="addtopl" data-pl="${esc(p.id)}">${icon("list")}${esc(p.title)}</button>`).join("") || `<div class="label">${_("menu.no_playlists")}</div>`}`);
  },
  addtopl(el) { closeMenu(); act(() => post(`/api/zones/${enc(S.group.coordinator)}/playlist-add`, { playlist: el.dataset.pl, item: S.menuItem.id }), _("toast.added_short")); },
  plrename() {
    closeMenu();
    const { id, title } = S.menuItem;
    promptDialog(_("pl.rename_title"), _("pl.new_name"), title, _("menu.rename"), async (t) => {
      await api(`/api/zones/${enc(S.group.coordinator)}/playlists/${enc(id)}`, { method: "PATCH", body: { title: t } });
      reloadContentView();
    });
  },
  pldelete() {
    closeMenu();
    const { id, title } = S.menuItem;
    if (!confirm(_("pl.delete_confirm", { title }))) return;
    act(async () => {
      await api(`/api/zones/${enc(S.group.coordinator)}/playlists/${enc(id)}`, { method: "DELETE" });
      if (S.view === "library") S.lib.stack = S.lib.stack.filter((s) => s.id !== id);
      reloadContentView();
    }, _("pl.deleted"));
  },
  open(el) {
    const id = el.dataset.id;
    const item = [...(S.lib.items || []), ...Object.values(shelves).flat(), ...(S.playlists || []), ...(S.favs || [])].find((i) => i.id === id || i.browse_id === id) || {};
    if (S.view !== "library") {
      S.lib.root = id.startsWith("svc:") ? svcRoot(id) : "SQ:";
      S.lib.stack = [];
      S.lib.search = "";
    }
    S.lib.stack.push({ id, title: el.dataset.title || item.title, playable: !item.browse_id && item.playable !== false });
    showView("library");
  },
  crumb(el) { S.lib.stack = S.lib.stack.slice(0, +el.dataset.depth); if (S.lib.root === "SQ:" && !S.lib.stack.length) return showView("playlists"); loadLibrary(); },
  libroot(el) { S.lib.root = el.dataset.id; S.lib.stack = []; S.lib.search = ""; loadLibrary(); },
  libmore() { loadLibrary(true); },
  stageopen() { S.nowMode = "stage"; store.set("nowMode", "stage"); if (S.view !== "now") showView("now"); else renderStage(); stageWake(); },
  stageclose() {
    S.nowMode = "classic";
    store.set("nowMode", "classic");
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    renderStage();
  },
  stagevideo() {
    S.stageVideo = !S.stageVideo;
    store.set("stageVideo", S.stageVideo ? "on" : "off");
    if (S.stageVideo) loadVideo(S.group); else { S.video = { key: S.video.key }; stopVideo(); }
    renderStage();
  },
  videomode(el) { S.videoMode = el.dataset.mode; store.set("videoMode", S.videoMode); renderStage(); },
  vidoffset(el) { S.video.offset += +el.dataset.d; S.lastSeek = 0; renderStage(); },
  stagepanel(el) {
    S.stagePanel = S.stagePanel === el.dataset.panel ? "" : el.dataset.panel;
    store.set("stagePanel", S.stagePanel);
    if (S.stagePanel === "queue") loadStageQueue();
    renderStage();
  },
  fullscreen() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else document.documentElement.requestFullscreen?.().catch(() => toast(_("stage.fullscreen_unsupported")));
  },
  shelfedit() { S.shelfEdit = !S.shelfEdit; renderServiceHome(); },
  shelfreset() { saveShelfOrder([]); },
  shelfmove(el) {
    const ids = orderedShelves().map((s) => s.id);
    const i = ids.indexOf(el.closest(".shelf-sec").dataset.sec), j = i + +el.dataset.dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    saveShelfOrder(ids);
  },
  shelfscroll(el) { const s = el.closest(".shelf-sec").querySelector(".shelf"); s.scrollBy({ left: +el.dataset.dir * s.clientWidth * 0.8, behavior: "smooth" }); },
  libupdate() { act(() => post(`/api/zones/${enc(S.group.coordinator)}/library-update`), _("lib.reindexing")); },
  alarmedit(el) { alarmDialog(el.dataset.id); },
  groupedit(el) { groupDialog(el.dataset.uid); },
  unjoin(el) { act(() => post(`/api/zones/${enc(el.dataset.uid)}/unjoin`)); },
  party() { act(() => zone("party"), _("rooms.partied")); },
  ungroupall() { act(() => post("/api/ungroup-all"), _("rooms.ungrouped")); },
  setuid(el) { S.setUid = el.dataset.uid; $$("[data-act=setuid]").forEach((b) => b.classList.toggle("active", b === el)); renderSpeakerSettings(); },
  rename() {
    const s = S.settings[S.setUid];
    promptDialog(_("rooms.rename_title"), _("rooms.name"), s.name, _("common.save"), async (name) => {
      await api(`/api/speakers/${enc(s.uid)}/settings`, { method: "PATCH", body: { name } });
      loadRooms();
    });
  },
  eqreset() {
    const s = S.settings[S.setUid];
    const body = {};
    for (const k of ["bass", "treble", "balance"]) if (k in s.eq) body[k] = 0;
    if ("loudness" in s.eq) body.loudness = true;
    act(async () => { await api(`/api/speakers/${enc(s.uid)}/settings`, { method: "PATCH", body }); renderSpeakerSettings(); }, _("rooms.sound_reset_done"));
  },
  addhost() {
    promptDialog(_("system.add_title"), _("rooms.ip"), "", _("common.add"), async (host) => { await post("/api/system/hosts", { host }); loadRooms(); });
  },
  rmhost(el) { act(async () => { await api(`/api/system/hosts/${enc(el.dataset.host)}`, { method: "DELETE" }); loadRooms(); }); },
};

function reloadContentView() { if (S.view === "library") loadLibrary(); else showView(S.view); }

/* ================================================================ Ereignisse */
document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-act]");
  if (!ev.target.closest("#menu") && !ev.target.closest("[data-act=itemmenu],[data-act=sleep],[data-act=mtoplaylist]")) closeMenu();
  if (!el) return;
  const fn = ACTIONS[el.dataset.act];
  if (fn) { ev.preventDefault(); fn(el, ev); }
});

$("#tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-view]");
  if (!b) return;
  if (b.dataset.view === "library" && S.lib.root === "SQ:") { S.lib.root = "A:ALBUMARTIST"; S.lib.stack = []; }
  showView(b.dataset.view);
});
$("#partyBtn").addEventListener("click", () => ACTIONS.party());
$("#ungroupBtn").addEventListener("click", () => ACTIONS.ungroupall());

/* Slider */
document.addEventListener("pointerdown", (e) => { if (e.target.matches("input[type=range]")) S.busy = true; });
document.addEventListener("pointerup", () => { setTimeout(() => { S.busy = false; }, 50); });
document.addEventListener("input", (e) => {
  const r = e.target;
  if (!r.matches("input[type=range]")) return;
  paintRanges(r.parentElement);
  if (r.dataset.vol === "member") {
    const uid = r.dataset.uid, v = +r.value;
    setPending(`v:${uid}`, v);
    $$(`[data-vlabel="${CSS.escape(uid)}"]`).forEach((l) => { l.textContent = v; });
    throttle(`v:${uid}`, () => post(`/api/zones/${enc(uid)}/volume`, { volume: v }).catch((x) => toast(x.message)));
  } else if (r.dataset.vol === "group") {
    const g = S.group, v = +r.value;
    setPending(`gv:${g.coordinator}`, v);
    $$("[data-vol=group]").forEach((x) => { if (x !== r) { x.value = v; paintRanges(x.parentElement); } });
    $$('[data-vlabel="group"]').forEach((l) => { l.textContent = v; });
    if (g.members.length === 1) setPending(`v:${g.members[0].uid}`, v);
    throttle(`gv:${g.coordinator}`, () => zone("group-volume", { volume: v }).catch((x) => toast(x.message)));
  } else if (r.hasAttribute("data-prog")) {
    S.seekUntil = Date.now() + 60000;
    $$("[data-pos]").forEach((el) => { el.textContent = fmt(+r.value); });
  } else if (r.dataset.setting) {
    const k = r.dataset.setting, v = +r.value;
    const l = $(`[data-svlabel="${k}"]`);
    if (l) l.textContent = v > 0 && k !== "audio_delay" ? `+${v}` : v;
  }
});
document.addEventListener("change", (e) => {
  const r = e.target;
  if (r.hasAttribute("data-prog")) {
    const pos = +r.value;
    S.seekUntil = Date.now() + 1500;
    S.group.track.position = pos;
    S.stateAt = performance.now();
    act(() => zone("seek", { position: pos }));
  } else if (r.dataset.setting) {
    const k = r.dataset.setting;
    const v = r.type === "checkbox" ? r.checked : +r.value;
    const uid = S.setUid;
    api(`/api/speakers/${enc(uid)}/settings`, { method: "PATCH", body: { [k]: v } })
      .then(() => { const s = S.settings[uid]; if (s) { if (k in s.eq) s.eq[k] = v; else s[k] = v; } })
      .catch((x) => { toast(x.message); renderSpeakerSettings(); });
  } else if (r.dataset.alarmToggle) {
    const a = S.alarms.find((x) => x.id === r.dataset.alarmToggle);
    act(async () => { await api(`/api/alarms/${enc(a.id)}`, { method: "PUT", body: { ...a, program_id: "keep", enabled: r.checked } }); loadAlarms(); });
  }
});

/* Formulare (Verbinden, Suche) */
document.addEventListener("submit", async (e) => {
  if (e.target.id === "hostForm") {
    e.preventDefault();
    const host = new FormData(e.target).get("host").trim();
    try { const r = await post("/api/system/hosts", { host }); toast(_("connect.connected", { name: r.name || host })); refreshSoon(0); } catch (x) { toast(x.message); }
  } else if (e.target.id === "scanForm") {
    e.preventDefault();
    const btn = $("button", e.target);
    btn.disabled = true; btn.textContent = _("connect.searching");
    try { const r = await post("/api/system/scan", { network: new FormData(e.target).get("network").trim() || null }); toast(r.found.length ? _("connect.found", { count: r.found.length }) : _("connect.none")); refreshSoon(0); }
    catch (x) { toast(x.message); }
    btn.disabled = false; btn.textContent = _("connect.search");
  }
});
let searchTimer;
document.addEventListener("input", (e) => {
  if (e.target.id !== "libSearch") return;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    S.lib.search = e.target.value.trim();
    const pos = e.target.selectionStart;
    loadLibrary().then(() => { const i = $("#libSearch"); if (i) { i.focus(); i.setSelectionRange(pos, pos); } });
  }, 300);
});

/* Warteschlange per Drag & Drop umsortieren */
let dragFrom = null;
document.addEventListener("dragstart", (e) => { const row = e.target.closest?.("#queueList .row"); if (!row) return; dragFrom = +row.dataset.index; row.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
document.addEventListener("dragover", (e) => {
  const row = e.target.closest?.("#queueList .row");
  if (dragFrom === null || !row) return;
  e.preventDefault();
  $$("#queueList .drop-before").forEach((r) => r.classList.remove("drop-before"));
  row.classList.add("drop-before");
});
document.addEventListener("drop", (e) => {
  const row = e.target.closest?.("#queueList .row");
  if (dragFrom === null || !row) return;
  e.preventDefault();
  let to = +row.dataset.index;
  if (to > dragFrom) to -= 1;
  const from = dragFrom;
  if (to !== from) act(async () => { await zone("queue", { action: "move", index: from, to }); loadQueue(); });
});
document.addEventListener("dragend", () => { dragFrom = null; $$("#queueList .dragging, #queueList .drop-before").forEach((r) => r.classList.remove("dragging", "drop-before")); });

/* Zeilen der Dienst-Startseite per Ziehen anordnen */
let dragSec = null;
document.addEventListener("dragstart", (e) => { const sec = e.target.closest?.(".shelf-sec.editing"); if (!sec) return; dragSec = sec.dataset.sec; sec.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
document.addEventListener("dragover", (e) => {
  const sec = e.target.closest?.(".shelf-sec.editing");
  if (!dragSec || !sec) return;
  e.preventDefault();
  $$(".shelf-sec.drop-before").forEach((s) => s.classList.remove("drop-before"));
  sec.classList.add("drop-before");
});
document.addEventListener("drop", (e) => {
  const sec = e.target.closest?.(".shelf-sec.editing");
  if (!dragSec || !sec) return;
  e.preventDefault();
  const ids = orderedShelves().map((s) => s.id).filter((id) => id !== dragSec);
  ids.splice(ids.indexOf(sec.dataset.sec), 0, dragSec);
  dragSec = null;
  saveShelfOrder(ids);
});
document.addEventListener("dragend", () => { dragSec = null; $$(".shelf-sec.dragging, .shelf-sec.drop-before").forEach((s) => s.classList.remove("dragging", "drop-before")); });

/* Tastatur: Leertaste = Play/Pause, Pfeile = Lautstärke */
document.addEventListener("keydown", (e) => {
  if (e.target.closest("input, select, textarea, dialog") || e.metaKey || e.ctrlKey || e.altKey || !S.group) return;
  if (e.code === "Space") { e.preventDefault(); ACTIONS.toggle(); }
  else if (e.key === "ArrowRight" && e.shiftKey) ACTIONS.transport({ dataset: { arg: "next" } });
  else if (e.key === "ArrowLeft" && e.shiftKey) ACTIONS.transport({ dataset: { arg: "previous" } });
  else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
    e.preventDefault();
    const g = S.group;
    const v = Math.max(0, Math.min(100, override(`gv:${g.coordinator}`, g.volume) + (e.key === "ArrowUp" ? 2 : -2)));
    setPending(`gv:${g.coordinator}`, v);
    renderLive();
    throttle(`gv:${g.coordinator}`, () => zone("group-volume", { volume: v }));
  }
  else if (e.key === "Escape") { closeMenu(); if (!document.fullscreenElement && $("#stage").classList.contains("open")) ACTIONS.stageclose(); }
});

/* Raumauswahl auf dem Handy */
function closeSheet() { $("#sidebar").classList.remove("open"); $("#sheetBackdrop").classList.remove("open"); }
$("#roomSwitch").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#sheetBackdrop").classList.add("open"); });
$("#sheetBackdrop").addEventListener("click", closeSheet);

/* Design: Automatisch → Hell → Dunkel */
function paintThemeBtn() {
  const t = document.documentElement.dataset.theme || "auto";
  $("#themeBtn").innerHTML = icon({ auto: "auto", light: "sun", dark: "moon" }[t]);
  $("#themeBtn").title = _("theme.title", { mode: _(`theme.${t}`) });
}
$("#themeBtn").addEventListener("click", () => {
  const next = { auto: "light", light: "dark", dark: "auto" }[document.documentElement.dataset.theme || "auto"];
  if (next === "auto") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = next;
  store.set("theme", next);
  paintThemeBtn();
});

document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshSoon(0); });

/* Start */
(async () => {
  await i18nInit();
  paintThemeBtn();
  try { S.system = await api("/api/system"); } catch {}
  try { S.prefs = await api("/api/prefs"); } catch { S.prefs = {}; }
  await poll();
  showView(S.state?.connected ? S.view : "connect");
})();
