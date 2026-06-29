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
async function her(text, tone) { const el = add("her" + toneCls(tone), ""); await typeOn(el, text || ""); }
// an arrival encounter carries a mood (spooky/sketchy/weird/awe/charming) — tint that turn's block
const _TONES = { spooky: 1, sketchy: 1, weird: 1, awe: 1, charming: 1 };
function toneCls(t) { return (t && _TONES[t]) ? " tone-" + t : ""; }
function you(text) { add("you", esc(text)); }
function events(list, tone) { if (list && list.length) add("events" + toneCls(tone), list.map(esc).join("\n")); }
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
    <div class="d-row"><span class="d-k">RIZ</span><span class="d-v">♠ ${s.riz ?? 0}</span><span class="d-v dim">style, banked</span></div>` +
    (s.bought ? `<div class="d-row owned"><span class="d-k">♥</span><span class="d-v">YOURS</span><span class="d-v dim">legal · race · show</span></div>` : ``) +
    (s.self_driving ? `<div class="d-row selfdrive"><span class="d-k">◉</span><span class="d-v">SELF-DRIVING</span><span class="d-v dim">'let her drive to …'</span></div>` : ``) +
    (s.desperado ? `<div class="d-row desperado"><span class="d-k">⚠</span><span class="d-v">DESPERADO</span><span class="d-v dim">armed &amp; dangerous · 'draw'</span></div>` : ``) +
    (s.camo ? `<div class="d-row camo"><span class="d-k">▒</span><span class="d-v">CAMO</span><span class="d-v dim">dressed down · 'uncamo'</span></div>` : ``) +
    (s.bond_armed
      ? `<div class="d-row coldarmed"><span class="d-k">☎</span><span class="d-v">SHE'S COLD</span><span class="d-v dim">anti-theft armed — sleep off-grid · 'how does she feel'</span></div>`
      : (s.bond_band === 'COOL'
        ? `<div class="d-row cooling"><span class="d-k">♡</span><span class="d-v">COOLING</span><span class="d-v dim">she's pulling away · warm her back</span></div>` : ``)) +
    (s.snow_line != null && s.snow_line <= 1.25
      ? `<div class="d-row snow"><span class="d-k">❄</span><span class="d-v">WINTER</span><span class="d-v dim">passes closing · 'passes'</span></div>` : ``) +
    weatherRows(s) + carRows(s) + surveillanceRows(s) + companionRows(s);
}

// ---- the sky: a temp readout + cold-start / dead-battery cues -------------------------
const WX_GLYPH = { snow: "❄", storm: "🌧", rain: "🌧", wind: "🌬", clear: "☀", cloudy: "☁" };
function weatherRows(s) {
  const w = s.weather; if (!w) return "";
  const g = WX_GLYPH[w.weather_code] || "·";
  let out = `<div class="d-row wx"><span class="d-k">${g}</span><span class="d-v">${Math.round(w.temp_high_f)}°/${Math.round(w.temp_low_f)}°</span><span class="d-v dim">${esc(w.condition)}${w.wind_mph >= 25 ? " · wind " + Math.round(w.wind_mph) : ""} · 'weather'</span></div>`;
  if (w.battery_dead)
    out += `<div class="d-row alert"><span class="d-k">🔋</span><span class="d-v">DEAD BATTERY</span><span class="d-v dim">cranked her flat · 'charge the battery'</span></div>`;
  else if (w.cold_start_needed)
    out += `<div class="d-row cold"><span class="d-k">❄</span><span class="d-v">COLD START</span><span class="d-v dim">she won't catch cold · 'cold start'</span></div>`;
  if (w.storm)
    out += `<div class="d-row snow"><span class="d-k">⚠</span><span class="d-v">STORM</span><span class="d-v dim">chains / closures ahead · 'forecast'</span></div>`;
  return out;
}

// ---- the car: knock, breakdown, fuel grade, stick skill, the loaner ------------------
function carRows(s) {
  let out = "";
  if (s.active_car === "bob")
    out += `<div class="d-row bob"><span class="d-k">🚙</span><span class="d-v">${esc(s.car_name || "BOB")}</span><span class="d-v dim">the loaner${s.bob_days_left != null ? " · " + s.bob_days_left + "d left" : ""}</span></div>`;
  if (s.broken_down)
    out += `<div class="d-row alert"><span class="d-k">✖</span><span class="d-v">BROKEN</span><span class="d-v dim">${s.breakdown_cause === "flat" ? "flat, no jack" : "holed a piston"} · 'tow'</span></div>`;
  else if (s.knocking)
    out += `<div class="d-row warn"><span class="d-k">⚠</span><span class="d-v">KNOCK</span><span class="d-v dim">running ${esc(s.fuel_grade || "regular")} · fill PREMIUM</span></div>`;
  else if (s.fuel_grade)
    out += `<div class="d-row"><span class="d-k">⛽</span><span class="d-v">${s.fuel_grade === "premium" ? "PREMIUM" : "REGULAR"}</span><span class="d-v dim">${s.fuel_grade === "premium" ? "the good stuff" : "she takes 91+ · knock risk"}</span></div>`;
  if (s.stick_skill != null && s.stick_skill < 100)
    out += `<div class="d-row"><span class="d-k">⚙</span><span class="d-v">STICK ${s.stick_skill}%</span><span class="d-v dim">green clutch · stalls in town/SF</span></div>`;
  if (s.damage && s.damage !== "clean")
    out += `<div class="d-row warn"><span class="d-k">▤</span><span class="d-v">${esc(s.damage.toUpperCase())}</span><span class="d-v dim">body damage ${s.damage_pct || 0}% · body shop</span></div>`;
  return out;
}

// ---- surveillance: the BOLO floor, your phone, frozen cards, a fake ID ----------------
function surveillanceRows(s) {
  let out = "";
  if (s.bolo_floor > 0 && !s.bought)
    out += `<div class="d-row bolo"><span class="d-k">▣</span><span class="d-v">BOLO FLOOR ${s.bolo_floor}</span><span class="d-v dim">heat can't fade below it · change the car</span></div>`;
  if (s.cards_frozen)
    out += `<div class="d-row alert"><span class="d-k">🚫</span><span class="d-v">CARDS FROZEN</span><span class="d-v dim">cash only · they're closing in</span></div>`;
  if (s.phone === false)
    out += `<div class="d-row dark"><span class="d-k">📵</span><span class="d-v">DARK</span><span class="d-v dim">phone ditched · off the cell net</span></div>`;
  if (s.has_fake_id)
    out += `<div class="d-row"><span class="d-k">🪪</span><span class="d-v">FAKE ID</span><span class="d-v dim">no-questions check-ins</span></div>`;
  return out;
}

// ---- what's riding with you: finds + Lucky the dog -----------------------------------
function companionRows(s) {
  let out = "";
  if (s.find_score > 0)
    out += `<div class="d-row"><span class="d-k">★</span><span class="d-v">${s.find_score} finds</span><span class="d-v dim">roadside haul · 'inventory'</span></div>`;
  if (s.has_dog)
    out += `<div class="d-row dog"><span class="d-k">🐕</span><span class="d-v">LUCKY</span><span class="d-v dim">road dog, asleep on the tunnel</span></div>`;
  return out;
}

// the one big diegetic button: after you agree, she waits for you to turn the key all the way
function turnKeyButton(snap) {
  const old = document.getElementById("turnkeywrap");
  if (old) old.remove();
  if (!snap || !snap.pending_turnkey) return;
  const wrap = document.createElement("div");
  wrap.id = "turnkeywrap"; wrap.className = "block";
  const b = document.createElement("button");
  b.className = "keybtn";
  b.textContent = "🔑  Turn the key — all the way";
  b.onclick = () => { wrap.remove(); submit("turn the key all the way"); };
  wrap.appendChild(b);
  $("#scroll").appendChild(wrap);
  $("#scroll").scrollTop = $("#scroll").scrollHeight;
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
// ----------------------------------------------------------------- the visual map (Codex plates)
function closeMap() {
  const o = document.getElementById("mapOverlay");
  if (o) o.remove();
  document.removeEventListener("keydown", _mapEsc);
}
function _mapEsc(e) { if (e.key === "Escape") closeMap(); }
function openMap(map) {
  closeMap();
  if (!map || !map.pois || !map.pois.length) return;
  const tiles = map.pois.map((p) => {
    const svc = (p.services || []).map((c) => c[0].toUpperCase()).join("");
    const meta = `${p.dist_mi} mi · ${esc(p.region)}${svc ? " · " + svc : ""}${p.reachable ? "" : " · ⛽"}`;
    return `<button class="maptile${p.reachable ? "" : " mt-far"}" data-dest="${esc(p.id)}"
        style="--cy:url('scenes_wm/${esc(p.id)}.png');--hv:url('scenes_wm/${esc(p.id)}_4c.png')"
        title="drive to ${esc(p.name)}">
        <span class="mt-grad"></span>
        <span class="mt-name">${esc(p.name)}</span>
        <span class="mt-meta">${meta}</span></button>`;
  }).join("");
  const o = document.createElement("div");
  o.id = "mapOverlay";
  o.innerHTML = `<div id="mapPanel">
      <div id="mapHead"><span>◇ THE MAP — around ${esc(map.here_name || "here")}</span>
        <span class="mh-range">range ~${map.range_mi} mi · ⛽ beyond it · hover for detail · click to drive</span>
        <button id="mapClose" title="close (Esc)">✕</button></div>
      <div id="mapGrid">${tiles}</div></div>`;
  ($("#deck") || document.body).appendChild(o);
  o.addEventListener("click", (e) => {
    if (e.target.id === "mapOverlay" || e.target.id === "mapClose") { closeMap(); return; }
    const btn = e.target.closest(".maptile");
    if (btn) { const dest = btn.getAttribute("data-dest"); closeMap(); submit("drive to " + dest); }
  });
  document.addEventListener("keydown", _mapEsc);
}

async function render(res) {
  if (res.intro) add("intro", esc(res.intro));
  updateDash(res.snapshot);
  showScene(res.snapshot);
  welcomeBlock(res.welcome);
  placeCard(res.snapshot);
  if (res.events && res.events.length) events(res.events, res.tone);
  if (res.scene) { await her(res.scene, res.tone); playVoice(res); }
  npcBlock(res.npc);
  info(res.info);
  if (res.map) openMap(res.map);           // the 'map' command → a visual overlay of nearby plates
  turnKeyButton(res.snapshot);
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
    turnKeyButton(res.snapshot);     // a resumed game can be mid-commit — keep the big button
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
