"use strict";
const $ = (s) => document.querySelector(s);
const scroll = $("#scroll"), dash = $("#dash");
const locName = $("#locName"), locTime = $("#locTime");
const cmd = $("#cmd"), player = $("#player"), muteBtn = $("#mute"), micBtn = $("#mic");

let muted = localStorage.getItem("fairlady_muted") === "1";
let typing = null;
const history = [];
let histIdx = 0;
let lastLoc = null;

// ----------------------------------------------------------------- retro scene panel
const screen = new RetroScene(document.querySelector("#screen"));
screen.start();
let lastSceneKey = null;
function showScene(snap) {
  if (!snap) return;
  const id = sceneIdFor(snap);
  const key = id + "|" + (snap.location || "") + "|" + snap.status;
  if (key === lastSceneKey) return;
  lastSceneKey = key;
  screen.set(id, sceneFor(snap));
}

// ----------------------------------------------------------------- api
async function api(path, body) {
  const r = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

// ----------------------------------------------------------------- transcript
function add(cls, html) {
  const d = document.createElement("div");
  d.className = "block " + cls;
  d.innerHTML = html;
  scroll.appendChild(d);
  scroll.scrollTop = scroll.scrollHeight;
  return d;
}
function esc(s) { return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

function typeOn(el, text) {
  return new Promise((resolve) => {
    let i = 0; const full = text;
    const finish = () => { el.textContent = full; clearInterval(timer); typing = null; scroll.scrollTop = scroll.scrollHeight; resolve(); };
    typing = { finish };
    const timer = setInterval(() => { i += 2; el.textContent = full.slice(0, i); scroll.scrollTop = scroll.scrollHeight; if (i >= full.length) finish(); }, 14);
  });
}
async function her(text) { const el = add("her", ""); await typeOn(el, text || ""); }
function you(text) { add("you", esc(text)); }
function events(list) { if (list && list.length) add("events", list.map(esc).join("\n")); }
function info(text) { if (text) add("info", esc(text)); }
function ending(text) { if (text) add("ending", esc(text)); }

function welcomeBlock(text) {
  if (!text) return;
  const [head, ...rest] = text.split("\n");
  add("welcome", `<div class="w-head">${esc(head)}</div><div class="w-body">${esc(rest.join(" "))}</div>`);
}
function placeCard(snap) {           // Carmen-style descriptive paragraph on arrival
  if (!snap || !snap.blurb) return;
  if (snap.location === lastLoc) return;
  lastLoc = snap.location;
  add("place", esc(snap.blurb));
}

function npcBlock(n) {
  if (!n) return;
  const audio = n.audio_url ? resolveAudio(n.audio_url) : null;
  const btn = audio ? `<button class="play" data-src="${audio}">▶ hear it (${esc(n.label || n.language)})</button>` : "";
  add("npc", `<div class="who">${esc(n.who || "a local")} — ${esc(n.label || n.language)}</div>
     <div class="native">${esc(n.native)}</div><div class="english">${esc(n.english || "")}</div>${btn}`);
  if (audio && !muted) playAudio(audio);
}

// ----------------------------------------------------------------- chips + dash
function seg(on, low) { return `<span class="seg ${on ? (low ? "low" : "on") : ""}"></span>`; }

function parseTime(t) {
  const wd = (t.match(/\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b/) || [])[1] || "";
  const m = t.match(/(\d{1,2}:\d{2})\s*([AP])M/i);
  const clock = m ? m[1] + (m[2].toLowerCase() === "a" ? "a" : "p") : "";
  return { wd, clock };
}

function updateDash(s) {
  if (!s) return;
  locName.textContent = (s.location || "—").split(",")[0];
  const ti = parseTime(s.time || "");
  locTime.innerHTML = `<b>${ti.wd}</b><span>${ti.clock}</span>`;
  const lit = Math.round(s.fuel_l), low = s.range_mi < 30;
  let gauge = ""; for (let i = 0; i < 40; i++) gauge += seg(i < lit, low);
  const heatW = Math.max(2, Math.min(100, s.heat));
  dash.innerHTML = `
    <div class="d-row"><span class="d-k">FUEL</span><span class="gauge">${gauge}</span></div>
    <div class="d-row"><span class="d-k">RANGE</span><span class="d-v">~${s.range_mi} mi · ${s.fuel_l}/${s.tank_l} L</span></div>
    <div class="d-row"><span class="d-k">CASH</span><span class="d-v">$${s.cash} · $${s.credit_available} card (${esc(s.pay_method)})</span></div>
    <div class="d-row"><span class="d-k">HEAT</span><span class="bar heat"><i style="width:${heatW}%"></i></span><span class="d-v dim">${esc(s.heat_label)}</span></div>
    <div class="d-row"><span class="d-k">RIZ</span><span class="d-v">♠ ${s.riz ?? 0}</span><span class="d-v dim">style, banked</span></div>`;
}

// ----------------------------------------------------------------- audio
function resolveAudio(u) { return /^https?:\/\//.test(u) ? u : location.origin + u; }
function playAudio(u) { try { player.src = u; player.play().catch(() => {}); } catch (e) {} }
function playVoice(res) { if (!muted && res.voice) playAudio(resolveAudio(res.voice)); }
function setMute(m) {
  muted = m; localStorage.setItem("fairlady_muted", m ? "1" : "0");
  muteBtn.classList.toggle("on", !m);
  muteBtn.textContent = m ? "♪̸" : "♪";
  if (m) player.pause();
}

// ----------------------------------------------------------------- flow
async function render(res) {
  if (res.intro) add("intro", esc(res.intro));
  updateDash(res.snapshot);
  showScene(res.snapshot);
  welcomeBlock(res.welcome);
  placeCard(res.snapshot);
  if (res.events && res.events.length) events(res.events);
  if (res.scene) { await her(res.scene); playVoice(res); }
  npcBlock(res.npc);
  info(res.info);
  if (res.status && res.status !== "playing") ending(res.ending);
  setSys(res);
}
function setSys(res) {
  const s = res.snapshot || {};
  $("#sys").innerHTML = `<span class="dot">●</span> day ${s.day || 1} · ${s.adventures ? s.adventures.length : 0} seen · ${s.odometer_mi || 0} mi`;
}

let busy = false;
async function submit(text) {
  text = (text || "").trim();
  if (!text || busy) return;
  if (typing) { typing.finish(); return; }
  cmd.value = ""; history.push(text); histIdx = history.length;
  you(text); busy = true;
  const note = add("info", '<span class="spin"></span>');
  try {
    const low = text.toLowerCase();
    const res = (low === "new" || low === "restart")
      ? await api("/api/new", {}) : await api("/api/command", { input: text });
    note.remove(); await render(res);
  } catch (e) { note.remove(); add("info", "…the line went dead."); }
  busy = false; cmd.focus();
}

// ----------------------------------------------------------------- input + voice
cmd.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); submit(cmd.value); }
  else if (e.key === "ArrowUp") { if (histIdx > 0) { histIdx--; cmd.value = history[histIdx] || ""; } e.preventDefault(); }
  else if (e.key === "ArrowDown") { if (histIdx < history.length) { histIdx++; cmd.value = history[histIdx] || ""; } e.preventDefault(); }
});
scroll.addEventListener("click", () => { if (typing) typing.finish(); });
muteBtn.onclick = () => setMute(!muted);
document.body.addEventListener("click", (e) => {
  if (e.target.classList && e.target.classList.contains("play")) playAudio(e.target.dataset.src);
});

// voice-first: the mic is the main way in. Browser speech here; Ace /asr is the production path.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null, listening = false;
if (SR) {
  recog = new SR(); recog.lang = "en-US"; recog.interimResults = false; recog.maxAlternatives = 1;
  recog.onresult = (e) => { const t = e.results[0][0].transcript; cmd.value = t; submit(t); };
  recog.onend = () => { listening = false; micBtn.classList.remove("on"); };
  recog.onerror = () => { listening = false; micBtn.classList.remove("on"); };
}
micBtn.onclick = () => {
  if (!recog) { add("info", "voice input needs a mic + Chrome here (production talks to Ace's ASR). Type to her in the meantime."); return; }
  if (listening) { recog.stop(); return; }
  try { recog.start(); listening = true; micBtn.classList.add("on"); } catch (e) {}
};

// ----------------------------------------------------------------- boot
async function boot() {
  setMute(muted);
  try { const h = await api("/api/health"); $("#sys").innerHTML = `<span class="dot">●</span> ${h.adapter} · ${h.routing}`; } catch (e) {}
  const res = await api("/api/state");
  if (res.snapshot && res.snapshot.turn > 0 && !res.intro) {
    updateDash(res.snapshot); showScene(res.snapshot);
    add("info", "…resuming. say 'look' to take stock, or 'new' to start over.");
  } else { await render(res); }
  cmd.focus();
}
boot();

// ----------------------------------------------------------------- power-on splash
(function () {
  const b = document.getElementById("boot");
  if (!b) return;
  let done = false;
  const go = () => { if (done) return; done = true; b.classList.add("gone"); setTimeout(() => { b.remove(); cmd.focus(); }, 600); window.removeEventListener("keydown", go); };
  setTimeout(go, 8000);                 // the koiNOya art deserves a beat — click/key skips
  b.addEventListener("click", go);
  window.addEventListener("keydown", go);
})();
