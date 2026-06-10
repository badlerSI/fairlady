"use strict";
/* FAIRLADY scenes — a sprite library + a fat set of POI scenes, all monochrome amber,
 * all animated. Each scene is draw(s, t). sceneFor(snap) resolves which one to show. */

const GROUND = 162;            // where the car's tires sit
const I = INK;

// =====================================================================
//  SPRITES — reusable, composable. (s = RetroScene, t = seconds)
// =====================================================================
const SPR = {

  // ---- THE HERO: Ace, the white 240Z (side profile, faces dir:+1 right) ----
  car(s, x, y, sc, t, o = {}) {
    const dir = o.dir || 1, speed = o.speed || 0;
    const bob = o.bob === false ? 0 : Math.round(s.wob(0.6 * sc, 1.7));
    y -= bob;
    const P = (ux, uy) => [x + (dir > 0 ? ux : 72 - ux) * sc, y - uy * sc];
    const seg = (a, b, c) => s.line(...P(...a), ...P(...b), c);

    // headlight beam (night)
    if (o.lights) {
      const n = P(71, 11), f = dir > 0 ? 1 : -1;
      s.poly([n, [n[0] + f * 90, n[1] - 18], [n[0] + f * 90, n[1] + 16]], I.d1);
      s.poly([n, [n[0] + f * 60, n[1] - 8], [n[0] + f * 60, n[1] + 9]], I.d2);
    }
    // speed lines behind
    if (speed > 0) {
      const m = (t * 220 * speed) % 18;
      for (let k = 0; k < 5; k++) {
        const lx = x - (dir > 0 ? 6 : -6) * sc - (dir > 0 ? 1 : -1) * (k * 14 + m) * sc * 0.5;
        s.rect(dir > 0 ? lx - 8 * sc : lx, y - (4 + k * 3) * sc, 8 * sc, Math.max(1, sc), I.d2);
      }
    }

    // body silhouette (the Z wedge: long hood, fastback)
    const hull = [[3,5],[4,14],[11,16],[22,25],[40,25],[49,19],[54,16],[70,12],[71,10],[71,5]];
    s.poly(hull.map(p => P(...p)), I.f);
    s.poly([[71,5],[3,5],[3,4],[71,4]].map(p => P(...p)), I.f); // rocker
    // overfenders (flared arches) sit slightly proud, darker edge
    [15, 57].forEach(wx => {
      s.poly([[wx-9,5],[wx-7,11],[wx,13],[wx+7,11],[wx+9,5]].map(p => P(...p)), I.f);
      s.poly([[wx-9,5],[wx-7,11],[wx,13],[wx+7,11],[wx+9,5]].map(p => P(...p)), I.d1, false);
    });
    // greenhouse glass (dark)
    s.poly([[24,24],[39,24],[46,18.5],[26,18.5]].map(p => P(...p)), I.d1);
    seg([33,24],[33,18.5], I.bg);                       // B-pillar
    // hood + ace-of-spades + the blue compute box glint
    seg([54,16],[70,12], I.hot);                         // hood crease
    if (sc >= 2) s.text("♠", ...P(58,14.5), I.bg, Math.max(1, sc-1));
    // chrome bumpers + nose
    seg([69,11.5],[71,9], I.hot); seg([71,9],[71,5.5], I.hot);
    seg([3,5.5],[3,13], I.hot);
    // round headlight + indicator
    s.disc(...P(68,10), Math.max(1, sc), I.hot);
    s.plot(...P(66,7), I.f);
    // door line + bullet mirror
    seg([40,5],[40,22], I.d2); seg([28,5],[28,16], I.d2);
    s.disc(...P(46,21), Math.max(1, sc-1), I.f);
    // taillight
    s.rect(...P(4,12), Math.max(1,sc), Math.max(1,sc), I.hot);
    // wheels: deep-dish polished multi-spoke (like the real Watanabe-style rims)
    [15, 57].forEach(wx => {
      const c = P(wx, 0.5), r = 6 * sc;
      s.disc(c[0], c[1], r, I.bg);             // tire
      s.ring(c[0], c[1], r, I.d2);             // sidewall
      s.ring(c[0], c[1], r - 1, I.hot);        // polished lip
      s.disc(c[0], c[1], r - 2 * sc, I.d3);    // dish face
      s.disc(c[0], c[1], 1.5 * sc, I.hot);     // center cap
      const a0 = t * (3 + speed * 8) * dir;
      for (let k = 0; k < 6; k++) {            // 6 spokes
        const a = a0 + k * Math.PI / 3;
        s.line(c[0], c[1], c[0] + Math.cos(a) * (r - 2), c[1] + Math.sin(a) * (r - 2), I.f);
      }
    });
    // plate: Ace really runs a Nevada "CARTALK" plate. Render it legibly only when big.
    if (o.plate !== false) {
      const big = sc >= 3.4;
      const txt = o.plate || "CARTALK";
      if (big) {
        const p = P(dir > 0 ? 4 : 68, 8); const w = s.textW(txt, 1) + 4;
        s.rect(p[0] - (dir>0?0:w) - 2, p[1] - 2, w, 11, I.hot);
        s.text(txt, p[0] - (dir>0?0:w), p[1] - 1, I.bg, 1);
      } else {
        const p = P(dir > 0 ? 4 : 67, 8.5);    // just the bright plate blank
        s.rect(p[0] - 1, p[1], 5 * sc, 3, I.hot);
      }
    }
    // exhaust puff
    if (o.exhaust) {
      const pe = (t * 1.3) % 1, ex = P(2, 4);
      s.dither(ex[0] - (dir>0?14:-2) - pe*8, ex[1] - 3 - pe*10, 10 + pe*14, 8 + pe*12, 8 - pe*6, I.d2);
    }
  },

  // ---- environment ----
  stars(s, t, n = 70, seed = 7, top = 0, bot = 120) {
    const r = s.rng(seed);
    for (let i = 0; i < n; i++) {
      const x = Math.floor(r() * s.W), y = top + Math.floor(r() * (bot - top));
      const ph = r() * 6.28;
      const tw = Math.sin(t * (1 + r() * 2) + ph);
      s.plot(x, y, tw > 0.3 ? I.hot : (tw > -0.4 ? I.f : I.d2));
    }
  },
  shootingStar(s, t, seed = 3, period = 6) {
    const k = Math.floor(t / period), r = s.rng(seed + k);
    const p = (t % period) / 1.2; if (p > 1) return;
    const sx = 20 + r() * 200, sy = 10 + r() * 50, len = 26;
    s.line(sx + p*120, sy + p*30, sx + p*120 - len, sy + p*30 - len*0.25, I.hot);
  },
  moon(s, x, y, r) {
    s.disc(x, y, r, I.f); s.disc(x + r*0.5, y - r*0.4, r*0.85, I.bg);
  },
  sun(s, x, y, r, t) {
    s.disc(x, y, r, I.f);
    for (let k = 0; k < 12; k++) {
      const a = k * Math.PI / 6 + s.wob(0.05, 3);
      s.line(x + Math.cos(a)*(r+2), y + Math.sin(a)*(r+2), x + Math.cos(a)*(r+6), y + Math.sin(a)*(r+6), I.d3);
    }
  },
  mountains(s, baseY, seed = 1, h = 50, c = I.d2, jag = 1) {
    const r = s.rng(seed), pts = [[0, baseY]]; let x = 0;
    while (x < s.W) { x += 14 + r()*26; pts.push([x, baseY - r()*h*jag - 8]); }
    pts.push([s.W, baseY], [s.W, s.H], [0, s.H]);
    s.poly(pts, c);
  },
  mesa(s, x, y, w, h, c = I.d2) {
    s.poly([[x, y], [x + w*0.12, y - h], [x + w*0.88, y - h], [x + w, y]], c);
  },
  ground(s, y, c = I.d3) { s.rect(0, y, s.W, s.H - y, I.bg); s.hline(0, s.W, y, c); },
  road(s, t, o = {}) {           // perspective road with marching dashes
    const horizon = o.horizon || 118, vx = o.vx || 160;
    s.poly([[vx - 4, horizon], [vx + 4, horizon], [s.W*0.92, s.H], [s.W*0.08, s.H]], I.d1);
    s.line(vx - 4, horizon, s.W*0.08, s.H, I.d3); s.line(vx + 4, horizon, s.W*0.92, s.H, I.d3);
    const m = (t * 1.3) % 1;
    for (let k = 0; k < 9; k++) {
      const f = ((k + m) / 9); const yy = horizon + f * f * (s.H - horizon);
      const w = 1 + f * 5; s.rect(vx - w/2, yy, w, Math.max(1, f*6), I.f);
    }
  },
  poles(s, t, y, c = I.d2) {     // roadside power/phone poles, scrolling
    const m = (t * 40) % 70;
    for (let k = -1; k < 6; k++) {
      const x = s.W - (k * 70 + m); const top = y - 34;
      s.vline(x, top, y, c); s.hline(x - 7, x + 7, top + 4, c);
    }
  },
  cactus(s, x, y, sc = 1, c = I.f) {
    s.rect(x - sc, y - 20*sc, 2*sc, 20*sc, c);
    s.rect(x - 7*sc, y - 14*sc, 2*sc, 7*sc, c); s.rect(x - 7*sc, y - 14*sc, 5*sc, 2*sc, c);
    s.rect(x + 5*sc, y - 17*sc, 2*sc, 8*sc, c); s.rect(x + 2*sc, y - 17*sc, 5*sc, 2*sc, c);
  },
  saguaro(s, x, y, sc, t, c = I.f) { SPR.cactus(s, x, y, sc, c); },
  joshua(s, x, y, sc, c = I.f) {
    s.rect(x-sc, y-16*sc, 2*sc, 16*sc, c);
    for (const a of [-0.8,-0.3,0.4,0.9]) {
      const ex = x + Math.cos(a-1.57)*10*sc, ey = y-16*sc + Math.sin(a-1.57)*10*sc;
      s.line(x, y-12*sc, ex, ey, c); s.disc(ex, ey, sc, c);
    }
  },
  pine(s, x, y, sc, c = I.f) {
    s.rect(x - sc/2, y - 4*sc, sc, 4*sc, I.d2);
    for (let k = 0; k < 3; k++) s.poly([[x-(8-k*2)*sc, y-(4+k*5)*sc],[x+(8-k*2)*sc, y-(4+k*5)*sc],[x, y-(11+k*5)*sc]], c);
  },
  palm(s, x, y, sc, t, c = I.f) {
    s.line(x, y, x - 2*sc, y - 22*sc, c); const tx = x - 2*sc, ty = y - 22*sc;
    for (const a of [-2.4,-1.9,-1.2,-0.6,0.0]) {
      const w = s.wob(0.12, 2.2, a*3);
      s.line(tx, ty, tx + Math.cos(a+w)*14*sc, ty + Math.sin(a+w)*10*sc, c);
    }
  },
  pump(s, x, y, t) {                 // gas pump w/ ticking digits
    s.rect(x, y - 30, 16, 30, I.f); s.rect(x + 2, y - 27, 12, 9, I.bg);
    const d = Math.floor((t * 7) % 1000).toString().padStart(3, "0");
    s.text(d, x + 2, y - 26, I.hot, 1);
    s.rect(x + 4, y - 14, 8, 6, I.d3);
    s.line(x + 16, y - 22, x + 22, y - 18, I.d3); s.disc(x + 23, y - 17, 1, I.f); // nozzle/hose
    s.rect(x - 2, y - 34, 20, 4, I.d3);            // topper
  },
  neon(s, x, y, txt, t, sc = 1) {
    const on = s.blink(1.1, 0.82);
    s.rectO(x - 3, y - 3, s.textW(txt, sc) + 6, 7*sc + 6, on ? I.f : I.d1);
    s.text(txt, x, y, on ? I.hot : I.d1, sc);
  },
  jet(s, x, y, sc, t, c = I.f) {     // fighter jet w/ afterburner
    s.poly([[x, y], [x + 34*sc, y - 2*sc], [x + 40*sc, y], [x + 34*sc, y + 2*sc]].map(p=>p), c); // fuselage
    s.poly([[x + 10*sc, y], [x + 22*sc, y + 9*sc], [x + 26*sc, y]], c);  // wing
    s.poly([[x + 4*sc, y], [x + 12*sc, y - 8*sc], [x + 14*sc, y]], c);   // tail
    const fl = s.blink(0.1) ? 8*sc : 5*sc;
    s.poly([[x, y - 1.5*sc], [x - fl, y], [x, y + 1.5*sc]], I.red);      // afterburner
  },
  ufo(s, x, y, t) {
    const yy = y + s.wob(3, 2.5);
    s.disc(x, yy, 12, I.d2); s.rect(x - 16, yy - 1, 32, 3, I.f); s.disc(x, yy - 5, 6, I.hot);
    if (s.blink(0.6)) s.poly([[x - 7, yy + 2], [x + 7, yy + 2], [x + 14, yy + 30], [x - 14, yy + 30]], I.d1);
    for (let k = 0; k < 3; k++) s.plot(x - 8 + s.cycle(16, 0.5) + k*8, yy + 1, I.hot);
  },
  ferris(s, x, y, r, t) {
    s.ring(x, y, r, I.f); s.line(x, y + r, x - 6, y + r + 12, I.d2); s.line(x, y + r, x + 6, y + r + 12, I.d2);
    for (let k = 0; k < 8; k++) {
      const a = t * 0.7 + k * Math.PI / 4;
      const cx = x + Math.cos(a)*r, cy = y + Math.sin(a)*r;
      s.line(x, y, cx, cy, I.d2); s.rect(cx - 2, cy - 1, 4, 3, I.hot);
    }
  },
  windturbine(s, x, y, h, t) {
    s.vline(x, y - h, y, I.d2);
    for (let k = 0; k < 3; k++) {
      const a = t * 1.6 + k * 2.094;
      s.line(x, y - h, x + Math.cos(a)*14, (y - h) + Math.sin(a)*14, I.f);
    }
  },
  coaster(s, x, y, t) {              // wooden coaster, a car cresting
    let px = x, py = y;
    const pts = [];
    for (let i = 0; i <= 60; i++) { const xx = x + i*3; const yy = y - Math.abs(Math.sin(i*0.2))*26 - (i<20?i:0)*0.3; pts.push([xx, yy]); }
    for (let i = 1; i < pts.length; i++) { s.line(...pts[i-1], ...pts[i], I.f); s.vline(pts[i][0], pts[i][1], y + 8, I.d1); }
    const ci = Math.floor((t * 0.18 % 1) * (pts.length - 1));
    s.rect(pts[ci][0] - 3, pts[ci][1] - 4, 8, 4, I.hot);
  },
  arch(s, cx, y, w, h, c = I.f) {    // a stone arch (Delicate / London)
    s.poly([[cx-w/2, y],[cx-w/2, y-h*0.5],[cx-w/4, y-h],[cx+w/4, y-h],[cx+w/2, y-h*0.5],[cx+w/2, y],
            [cx+w/4, y],[cx+w/5, y-h*0.55],[cx-w/5, y-h*0.55],[cx-w/4, y]], c);
  },
  hoodoo(s, x, y, h, c = I.f) {
    for (let j = 0; j < h; j += 4) { const w = 3 + Math.sin(j) * 2; s.rect(x - w/2, y - j - 4, w, 4, c); }
  },
  bridge(s, y, t) {                  // suspension bridge (golden gate / bay)
    const towers = [70, 250];
    s.hline(0, s.W, y, I.d3);
    towers.forEach(tx => { s.vline(tx, y - 60, y + 10, I.f); s.hline(tx - 6, tx + 6, y - 56, I.f); s.hline(tx-5,tx+5,y-48,I.f); });
    s.line(0, y - 20, towers[0], y - 60, I.d3); s.line(towers[0], y - 60, towers[1], y - 30, I.d3);
    s.line(towers[1], y - 60, s.W, y - 20, I.d3);
    // vertical suspender cables
    for (let x = 10; x < s.W; x += 10) {
      let cy;
      if (x < towers[0]) cy = (y-20) + (x/towers[0])*(-40);
      else if (x < towers[1]) { const f=(x-towers[0])/(towers[1]-towers[0]); cy = (y-60) + f*30; if (f>0.5) cy=(y-60)+ (1-f)*30; }
      else { const f=(x-towers[1])/(s.W-towers[1]); cy=(y-60)+f*40; }
      s.vline(x, cy, y, I.d1);
    }
  },
  pagoda(s, x, y, t) {               // 5-tier peace pagoda
    s.rect(x - 3, y - 8, 6, 8, I.d2);
    for (let k = 0; k < 5; k++) {
      const w = 26 - k*4, ty = y - 8 - k*9;
      s.rect(x - w/2 + 2, ty - 6, w - 4, 6, I.f);
      s.poly([[x - w/2, ty], [x + w/2, ty], [x + w/2 - 3, ty - 2], [x - w/2 + 3, ty - 2]], I.hot);
    }
    s.vline(x, y - 8 - 45, y - 8 - 38, I.f);
  },
  lantern(s, x, y, t, ph = 0) {
    const sw = s.wob(2, 2.4, ph); s.line(x, y, x + sw, y + 8, I.d2);
    s.disc(x + sw, y + 12, 3, s.blink(1.6, 0.7, ) ? I.hot : I.d3);
  },
  thermometer(s, x, y, t) {          // world's tallest thermometer (Baker)
    s.rect(x - 3, y - 70, 6, 70, I.d2); s.disc(x, y, 5, I.f);
    const h = 30 + s.wob(20, 4); s.rect(x - 1, y - h, 2, h, I.hot);
    s.text("134", x + 5, y - 64, I.f, 1);
  },
  condor(s, x, y, t) { const w = s.wob(3, 0.8); s.line(x-7, y+w, x, y-2, I.f); s.line(x, y-2, x+7, y+w, I.f); },
  tumbleweed(s, t, y) {
    const x = (t * 60) % (s.W + 40) - 20, rot = t * 5;
    s.ring(x, y - 5 + s.wob(2, 0.3), 5, I.d2);
    for (let k=0;k<3;k++){const a=rot+k*2;s.line(x,y-5,x+Math.cos(a)*5,y-5+Math.sin(a)*5,I.d3);}
  },
  nixie(s, x, y, txt) {              // glowing nixie tubes — always 5:37
    for (let i = 0; i < txt.length; i++) {
      s.rectO(x + i*10, y - 2, 9, 13, I.d1);
      s.text(txt[i], x + i*10 + 2, y, I.red, 1);
    }
  },
  cameraFlash(s, t, seed = 9, period = 9) {   // Larry Chen, somewhere in the dark
    const k = Math.floor(t / period); const p = t % period;
    if (p > 0.35) return; const r = s.rng(seed + k);
    const x = 30 + r()*240, y = 120 + r()*30;
    s.disc(x, y, p < 0.12 ? 7 : 2, I.hot); s.plot(x, y+2, I.f);
  },
};

// =====================================================================
//  ACE — the digitized hero sprite (Ben's real 240Z), rolling down the road.
//  Drawn in the lower foreground over each location backdrop. Mirror glints.
// =====================================================================
const CAR_IMG = new Image();
if (typeof CAR_PNG !== "undefined") CAR_IMG.src = CAR_PNG;

function drawAce(s, t, o = {}) {
  const moving = o.moving !== false;
  const w = o.w || 150, h = Math.round(w * CAR_META.h / CAR_META.w);
  const x = Math.round((o.x != null ? o.x : s.W * 0.49) - w / 2);
  const baseY = (o.y != null ? o.y : 184);
  const bob = Math.round(moving ? s.wob(0.8, 0.45) : s.wob(0.4, 2.4));
  const y = baseY - h + bob;

  // ground shadow under the tires
  s.dither(x + Math.round(w * 0.10), baseY - 4, Math.round(w * 0.80), 5, 8, I.d1);
  // road-speed streaks flanking her when rolling
  if (moving) {
    const m = (t * 280) % 26;
    for (let k = 0; k < 4; k++) {
      const ly = baseY - 2 - k * 4, off = (m + k * 26) % 46;
      s.rect(x - 24 + off, ly, 9, 1, I.d2);
      s.rect(x + w + 16 - off, ly, 9, 1, I.d2);
    }
  }
  // the car — OPAQUE, on the top layer (the road never shows through her)
  if (CAR_IMG.complete && CAR_IMG.naturalWidth) {
    s.ctx.imageSmoothingEnabled = false;
    s.ctx.drawImage(CAR_IMG, x, y, w, h);
  } else {
    s.rect(x, y, w, h, I.d2);
  }
  // idle exhaust when stopped
  if (!moving && s.blink(2.4, 0.3))
    s.dither(x + Math.round(w * 0.46), y + h - 7, 13, 8, 6, I.d2);

  // rear-glass reflection — a bright sheen sweeps the back windshield as the world slides by
  const rg = CAR_META.anchors.rearGlass;
  if (rg) {
    const gx = x + rg[0] * w, gy = y + rg[1] * h, gw = rg[2] * w, gh = rg[3] * h;
    const sweep = (moving ? (t * 0.42) : (t * 0.16)) % 1;
    const sxx = gx - gh * 0.6 + sweep * (gw + gh * 0.8);   // diagonal, top-left → lower-right
    for (let i = 0; i < gh; i++) {
      const px = sxx + i * 0.55;
      if (px >= gx + 1 && px <= gx + gw - 1) { s.plot(px, gy + i, i & 1 ? I.hot : I.f); s.plot(px + 1, gy + i, I.f); }
    }
  }

  // driver-side fender bullet mirror — chrome housing on a stalk, a glisten travelling its face
  const ma = CAR_META.anchors.mirror;
  const mx = x + Math.round(ma[0] * w), my = y + Math.round(ma[1] * h);
  s.line(mx + 4, my + 6, mx, my, I.d3);            // stalk up off the fender
  s.disc(mx, my, 2, I.d1);                          // dark housing
  s.ring(mx, my, 2, I.f);                           // chrome rim
  const ga = (moving ? s.saw(1.1) : (s.now * 0.28) % 1) * 6.2832;
  s.plot(mx + Math.round(Math.cos(ga) * 1.3), my + Math.round(Math.sin(ga) * 1.3), I.hot);
  if (moving ? s.saw(1.1) < 0.12 : s.blink(3, 0.12)) { s.plot(mx, my, I.hot); s.plot(mx - 1, my - 1, I.hot); }
}

// =====================================================================
//  SCROLLING HIGHWAY — pseudo-3D chase view (the world goes by; one reused car sprite).
//  The "we only had 16MB" driving loop: city / desert / mountain skins.
// =====================================================================
function _roadHalf(p, top, bot) { return top + p * (bot - top); }
function _roadY(p, hy, H) { return hy + p * p * (H - hy); }

const ENV_OBJ = {
  desert(s, x, y, sc, t, side) {
    if ((Math.floor(x) + side) & 1) SPR.cactus(s, x, y, Math.max(0.4, sc), I.f);
    else { s.vline(x, y - 30 * sc, y, I.d3); s.hline(x - 7 * sc, x + 7 * sc, y - 26 * sc, I.d3); } // pole
  },
  city(s, x, y, sc, t, side) {
    if ((Math.floor(x) + side) & 1) {              // lit building
      const w = 18 * sc, h = (40 + (Math.floor(x) % 30)) * sc;
      s.rect(x - (side > 0 ? 0 : w), y - h, w, h, I.d2);
      for (let wy = y - h + 5 * sc; wy < y - 4 * sc; wy += 7 * sc)
        for (let wx = 0; wx < w; wx += 6 * sc)
          if (((Math.floor(wx + wy + x)) & 3) === 0) s.rect(x - (side > 0 ? 0 : w) + wx, wy, 2 * sc, 3 * sc, I.hot);
    } else { s.vline(x, y - 34 * sc, y, I.d3); s.disc(x, y - 34 * sc, Math.max(1, 1.5 * sc), s.blink(0.9) ? I.hot : I.f); } // streetlight
  },
  mountain(s, x, y, sc, t, side) {
    if ((Math.floor(x) + side) & 1) SPR.pine(s, x, y, Math.max(0.4, sc * 1.1), I.f);
    else { s.disc(x, y - 2 * sc, Math.max(1, 3 * sc), I.d3); s.disc(x + 4 * sc, y - 1, Math.max(1, 2 * sc), I.d2); } // boulder
  },
};

function _drawFar(s, env, hy, t) {
  const drift = (t * 7) % 48;
  if (env === "desert") {
    SPR.sun(s, 252, 34, 12, t);
    for (let i = -1; i < 8; i++) { const x = i * 48 - drift; SPR.mesa(s, x, hy + 2, 40, 16 + (i & 1) * 10, I.d1); }
  } else if (env === "city") {
    SPR.stars(s, t, 50, 5, 0, hy - 6);
    const r = s.rng(3);
    for (let i = -1; i < 14; i++) { const x = i * 26 - drift; const h = 14 + ((i * 7) % 22); s.rect(x, hy - h, 22, h, I.d1);
      for (let wy = hy - h + 3; wy < hy - 3; wy += 6) if (((i + wy) & 3) === 0) s.plot(x + 4 + ((i * 3) % 12), wy, I.d3); }
  } else { // mountain
    SPR.stars(s, t, 22, 5, 0, hy - 8);
    for (let i = -1; i < 7; i++) { const x = i * 56 - drift * 0.6; s.poly([[x, hy + 2], [x + 28, hy - 30 - (i & 1) * 12], [x + 56, hy + 2]], I.d1); }
  }
}

function drawHighway(s, t, env) {
  // DIAGONAL road: the car (rear-3/4) is heading up-and-to-the-left, so the vanishing point
  // sits left of centre and the band sweeps from the lower-right foreground up to it.
  const hy = 66, H = s.H, topW = 9, botW = s.W * 0.66;
  const vpx = s.W * 0.36, nearCx = s.W * 0.60;
  const frac = (p) => (_roadY(p, hy, H) - hy) / (H - hy);       // screen fraction at depth p
  const cx = (p) => vpx + frac(p) * (nearCx - vpx);             // road centre slides right as it nears
  s.rect(0, 0, s.W, hy, I.bg);
  _drawFar(s, env, hy, t);
  // the road wedge
  s.poly([[vpx, hy], [nearCx - botW, H], [nearCx + botW, H]], I.d1);
  s.line(vpx, hy, nearCx - botW, H, I.d3); s.line(vpx, hy, nearCx + botW, H, I.d3);
  const ph = (t * 0.85) % 1;
  // centre dashes rushing toward camera along the diagonal
  for (let k = 0; k < 10; k++) { const p = ((k / 10) + ph) % 1; const y = _roadY(p, hy, H); const w = 1 + p * 7; s.rect(cx(p) - w / 2, y, w, 2 + p * 16, I.f); }
  // rumble strips
  for (let k = 0; k < 14; k++) {
    const p = ((k / 14) + ph) % 1; const y = _roadY(p, hy, H); const hw = _roadHalf(p, topW, botW);
    const lit = (k + Math.floor(ph * 14)) & 1, c = lit ? I.f : I.d2, tk = 1 + p * 4;
    s.rect(cx(p) - hw, y, tk, Math.max(1, p * 9), c); s.rect(cx(p) + hw - tk, y, tk, Math.max(1, p * 9), c);
  }
  // roadside objects spawning at the horizon, sweeping past on the diagonal
  const obj = ENV_OBJ[env] || ENV_OBJ.desert;
  for (let i = 0; i < 6; i++) {
    const p = ((i / 6) + ph * 0.9) % 1; if (p < 0.05) continue;
    const side = (i & 1) ? 1 : -1, hw = _roadHalf(p, topW, botW);
    obj(s, cx(p) + side * (hw + 4 + p * 46), _roadY(p, hy, H), 0.2 + p * 2.0, t, side);
  }
}

// =====================================================================
//  SCENES  (each = a location BACKDROP; drawAce() composites the hero on top)
// =====================================================================
function bgNight(s, t, seed) { SPR.stars(s, t, 80, seed || 7); SPR.shootingStar(s, t, (seed||7)+1); }

const SCENES = {

  // ---------- the opening cinematic + every gas station ----------
  gas(s, t) {
    SPR.stars(s, t, 40, 5, 0, 56);
    SPR.mountains(s, 120, 4, 30, I.d1);
    // station canopy + pump
    s.rect(20, 40, 120, 6, I.d3); s.vline(28, 46, GROUND, I.d2); s.vline(132, 46, GROUND, I.d2);
    s.textC("FUEL", 30, I.f, 2);
    // the SEMA-booth checkerboard apron (nod to the real show floor + her checkered seats)
    s.rect(0, GROUND, s.W, s.H - GROUND, I.bg); s.hline(0, s.W, GROUND, I.d3);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 21; c++)
      if ((r + c) & 1) s.rect(c * 16, GROUND + 2 + r * 12, 15, 11, r === 0 ? I.d2 : I.d1);
    SPR.pump(s, 44, GROUND, t);              // pump beside where she parks
    SPR.nixie(s, 250, 18, "5:37");           // egg: always 5:37
    drawAce(s, t, { moving: false });        // parked at the island, idling
  },

  // ---------- out of gas on the shoulder ----------
  stranded(s, t) {
    bgNight(s, t, 11); SPR.mountains(s, 130, 6, 40, I.d1);
    SPR.ground(s, GROUND);
    SPR.tumbleweed(s, t, GROUND);
    drawAce(s, t, { moving: false });
    if (s.blink(0.5)) { s.plot(s.W*0.43, 176, I.red); s.plot(s.W*0.56, 176, I.red); } // hazards
    SPR.cameraFlash(s, t, 13);               // egg: Larry, somewhere out there
    s.textC("OUT OF GAS", 40, s.blink(0.8) ? I.f : I.d2, 2);
  },

  // ---------- generic between-towns ----------
  // the three scrolling driving loops — same car sprite, the world goes by
  drive_desert(s, t) { drawHighway(s, t, "desert"); drawAce(s, t, { moving: true }); },
  drive_city(s, t)   { drawHighway(s, t, "city");   drawAce(s, t, { moving: true }); },
  drive_mountain(s, t){ drawHighway(s, t, "mountain"); drawAce(s, t, { moving: true }); },
  night_drive(s, t)  { drawHighway(s, t, "desert"); drawAce(s, t, { moving: true }); },
  roadside(s, t)     { drawHighway(s, t, "desert"); drawAce(s, t, { moving: true }); },
  motel(s, t) {
    bgNight(s, t, 31); SPR.ground(s, GROUND);
    s.rect(40, 96, 150, GROUND - 96, I.d2);  // building
    for (let k = 0; k < 4; k++) s.rect(52 + k*34, 120, 14, 18, s.rng(k+1)() > 0.5 ? I.hot : I.d1);
    SPR.neon(s, 210, 70, "MOTEL", t, 2);
    SPR.neon(s, 214, 96, "VACANCY", t, 1);
    drawAce(s, t);
    SPR.moon(s, 40, 30, 10);
  },

  // ---------- national parks & nature ----------
  grand_canyon(s, t) {
    SPR.stars(s, t, 14, 5, 0, 24); SPR.sun(s, 250, 36, 13, t);
    // layered canyon walls receding
    for (let k = 0; k < 6; k++) {
      const y = 70 + k*16; const c = [I.d1,I.d1,I.d2,I.d2,I.d3,I.f][k];
      const r = s.rng(k+2); const pts = [[0, y+20]];
      let x=0; while (x < s.W){x+=18+r()*22; pts.push([x, y+ r()*10]);} pts.push([s.W,y+20],[s.W,y+40],[0,y+40]);
      s.poly(pts, c);
    }
    SPR.condor(s, 90 + s.wob(40, 6), 40 + s.wob(8, 3), t);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  zion(s, t) {
    SPR.stars(s, t, 10, 5, 0, 20);
    // towering walls converging
    s.poly([[0,0],[120,0],[80,GROUND],[0,GROUND]], I.d2);
    s.poly([[s.W,0],[200,0],[240,GROUND],[s.W,GROUND]], I.d3);
    for (let y=20;y<GROUND;y+=12){ s.hline(0, 80 + (GROUND-y)*0.0, y, I.d1); }
    SPR.condor(s, 160 + s.wob(30,7), 30, t);
    SPR.ground(s, GROUND, I.f);
    SPR.road(s, t, { vx: 160, horizon: 40 });
    drawAce(s, t);
  },
  bryce(s, t) {
    SPR.stars(s, t, 12, 5, 0, 26);
    SPR.mountains(s, 60, 4, 18, I.d1);
    const r = s.rng(4);
    for (let k = 0; k < 16; k++) SPR.hoodoo(s, 12 + k*20, GROUND, 30 + r()*46, k%2?I.f:I.d3);
    SPR.ground(s, GROUND);
    // snow dots
    for (let k=0;k<20;k++){const x=(s.rng(k+9)()*s.W); s.plot((x+t*6)%s.W, (s.rng(k+1)()*GROUND), I.hot);}
    drawAce(s, t);
  },
  arches(s, t) {
    bgNight(s, t, 41); SPR.mountains(s, 120, 7, 30, I.d2);
    SPR.arch(s, 110, GROUND, 70, 70, I.f);
    SPR.ground(s, GROUND, I.d3);
    drawAce(s, t);
  },
  canyonlands(s, t) {
    SPR.sun(s, 60, 40, 12, t);
    SPR.mesa(s, 30, GROUND, 70, 40, I.d2); SPR.mesa(s, 150, GROUND, 110, 56, I.d3); SPR.mesa(s, 250, GROUND, 60, 34, I.d1);
    SPR.ground(s, GROUND, I.f); drawAce(s, t);
  },
  death_valley(s, t) {
    SPR.sun(s, 160, 40, 16, t);
    // heat shimmer
    for (let y = 60; y < GROUND; y += 3) s.hline(0 + s.wob(4, 1.2, y), s.W, y, I.d1);
    SPR.mountains(s, GROUND, 5, 26, I.d2);
    SPR.thermometer(s, 280, GROUND, t);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  joshua_tree(s, t) {
    bgNight(s, t, 51); SPR.mountains(s, GROUND, 6, 22, I.d1);
    SPR.ground(s, GROUND);
    SPR.joshua(s, 60, GROUND, 1.4); SPR.joshua(s, 250, GROUND, 1.1); SPR.joshua(s, 300, GROUND, 0.9);
    s.disc(40, 36, 9, I.f); drawAce(s, t);
  },
  yosemite(s, t) {
    SPR.stars(s, t, 12, 5, 0, 20);
    s.poly([[150,0],[150,40],[210,40],[230,GROUND],[150,GROUND]], I.d3); // half dome
    s.poly([[150,40],[180,20],[210,40]], I.f);
    s.rect(40, 30, 50, GROUND-30, I.d2);   // el cap
    s.vline(120, 40, GROUND, I.hot);       // waterfall
    SPR.ground(s, GROUND, I.f); SPR.pine(s, 280, GROUND, 1.3); SPR.pine(s, 300, GROUND, 1);
    drawAce(s, t);
  },
  sequoia(s, t) {
    SPR.stars(s, t, 8, 5, 0, 18);
    s.rect(120, 0, 70, GROUND, I.d3); s.rect(120, 0, 6, GROUND, I.f); s.rect(184, 0, 6, GROUND, I.d2);
    SPR.pine(s, 40, GROUND, 2); SPR.pine(s, 280, GROUND, 2.4);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);  // tiny for scale
    s.textC("BIGGEST LIVING THINGS", 8, I.d3, 1);
  },
  great_basin(s, t) {                       // under the stars (Ben asked)
    SPR.stars(s, t, 150, 5, 0, 110);
    // milky way band
    for (let k = 0; k < 60; k++) { const x = (k*6 + t*2) % s.W; s.plot(x, 50 + Math.sin(x*0.05)*10 + s.rng(k+1)()*8, I.d3); }
    SPR.shootingStar(s, t, 6, 4); SPR.shootingStar(s, t, 19, 7);
    SPR.mountains(s, 130, 3, 50, I.d1, 1.4);   // wheeler peak
    SPR.ground(s, GROUND);
    // bristlecone pine (gnarled)
    s.line(70, GROUND, 66, GROUND-26, I.f); s.line(66, GROUND-26, 78, GROUND-30, I.f); s.line(66, GROUND-26, 58, GROUND-32, I.f);
    drawAce(s, t);
  },
  monument_valley(s, t) {
    SPR.sun(s, 270, 38, 12, t);
    SPR.mesa(s, 20, 120, 36, 64, I.d3); SPR.mesa(s, 70, 120, 30, 70, I.d3);   // the mittens
    SPR.mesa(s, 220, 120, 50, 50, I.d2);
    SPR.ground(s, 120, I.f); SPR.road(s, t, { horizon: 118 });
    drawAce(s, t);
  },
  saguaro(s, t) {
    SPR.sun(s, 160, 50, 18, t); SPR.mountains(s, GROUND, 5, 20, I.d2);
    SPR.ground(s, GROUND, I.f);
    [30,70,250,290].forEach((x,i)=>SPR.cactus(s, x, GROUND - (i%2)*4, 1.6 + (i%2)*0.4));
    drawAce(s, t);
  },
  petrified_forest(s, t) {
    SPR.sun(s, 60, 36, 12, t);
    for (let k = 0; k < 5; k++) s.dither(0, 60 + k*14, s.W, 14, 4 + k*2, [I.d1,I.d2,I.d2,I.d3,I.d3][k]); // painted desert bands
    SPR.ground(s, GROUND, I.f);
    for (let k=0;k<4;k++) s.rect(20 + k*30, GROUND-3, 24, 3, I.d3);  // petrified logs
    drawAce(s, t);
  },
  sedona(s, t) {
    SPR.sun(s, 280, 40, 12, t);
    s.poly([[40,GROUND],[60,40],[80,GROUND]], I.f); s.poly([[100,GROUND],[130,30],[160,GROUND]], I.d3);
    s.poly([[200,GROUND],[220,60],[240,GROUND]], I.d2);
    SPR.ground(s, GROUND, I.f); drawAce(s, t);
  },
  meteor_crater(s, t) {
    SPR.stars(s, t, 14, 5, 0, 30);
    s.poly([[0,120],[110,90],[210,90],[s.W,120],[s.W,GROUND],[0,GROUND]], I.d2);
    s.poly([[110,90],[150,150],[170,150],[210,90]], I.bg); s.line(110,90,150,150,I.f); s.line(210,90,170,150,I.f);
    SPR.ground(s, GROUND, I.f); drawAce(s, t);
  },
  goblin_valley(s, t) {
    SPR.stars(s, t, 12, 5, 0, 26);
    const r = s.rng(7);
    for (let k=0;k<12;k++){const x=18+k*26,h=12+r()*16; s.disc(x, GROUND-h-4, 4, I.d3); s.rect(x-2, GROUND-h, 4, h, I.d3);}
    SPR.ground(s, GROUND, I.f); drawAce(s, t);
  },
  capitol_reef(s, t) {
    SPR.sun(s, 60, 36, 11, t);
    s.poly([[0,GROUND],[40,70],[120,90],[200,60],[280,90],[s.W,70],[s.W,GROUND]], I.d3);
    SPR.ground(s, GROUND, I.f);
    for (let k=0;k<4;k++) SPR.pine(s, 30+k*16, GROUND, 0.8);  // orchard
    drawAce(s, t);
  },

  // ---------- iconic landmarks & EASTER EGGS ----------
  hollywood(s, t) {
    bgNight(s, t, 61);
    // searchlights sweeping
    for (let k=0;k<2;k++){const a=-1.2 + s.wob(0.5, 4, k*2); s.poly([[60+k*200, GROUND],[60+k*200+Math.cos(a)*200, GROUND+Math.sin(a)*200],[60+k*200+Math.cos(a-0.1)*200, GROUND+Math.sin(a-0.1)*200]], I.d1);}
    SPR.mountains(s, 120, 6, 30, I.d2);
    s.textC("HOLLYWOOD", 70, I.hot, 2);       // the sign
    for (let k=0;k<9;k++) s.vline(40 + k*30, 78, 92, I.d1);
    SPR.palm(s, 30, GROUND, 1.4, t); SPR.palm(s, 300, GROUND, 1.2, t);
    SPR.ground(s, GROUND, I.f);
    s.text("★", 150, 150, I.hot, 1);          // a star on the walk
    drawAce(s, t);
  },
  bay_bridge(s, t) {                          // Ben asked
    bgNight(s, t, 71, 0, 80);
    SPR.bridge(s, 96, t);
    // bay lights shimmer on water
    s.rect(0, 130, s.W, s.H-130, I.bg);
    for (let k=0;k<40;k++){const x=s.rng(k+2)()*s.W; s.plot(x, 134 + s.rng(k+3)()*20, s.blink(0.7+s.rng(k)()*0.6) ? I.hot : I.d1);}
    s.hline(0, s.W, 130, I.d3);
    drawAce(s, t);
  },
  golden_gate(s, t) {
    // fog
    for (let y=40;y<GROUND;y+=4) s.dither(0, y, s.W, 4, 6, I.d1);
    SPR.bridge(s, 100, t);
    SPR.ground(s, 138, I.d3);
    drawAce(s, t);
  },
  vegas_strip(s, t) {
    bgNight(s, t, 81, 0, 70);
    // Luxor pyramid + sky beam
    s.poly([[20,GROUND],[55,90],[90,GROUND]], I.d3); s.vline(55, 0, 90, s.blink(0.3)?I.hot:I.f);
    // Stratosphere tower
    s.vline(150, 40, GROUND, I.d2); s.disc(150, 40, 6, I.f);
    // High Roller wheel
    SPR.ferris(s, 250, 90, 34, t);
    // marquee
    for (let k=0;k<3;k++) s.rect(100+k*16, 130, 12, 20, s.blink(0.4+k*0.2)?I.hot:I.d1);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  sphere(s, t) {                              // the Vegas Sphere — egg: animated face
    bgNight(s, t, 91, 0, 70);
    s.disc(160, 96, 56, I.d2);
    // dithered globe shading
    for (let yy=-56; yy<56; yy+=2){ const w=Math.floor(Math.sqrt(56*56-yy*yy)); s.dither(160-w, 96+yy, 2*w, 2, 6, I.d3); }
    // giant blinking eye / emoji
    if (s.blink(3.5, 0.92)) { s.disc(160, 96, 30, I.hot); s.disc(160 + s.wob(8,3), 96, 12, I.bg); s.disc(160 + s.wob(8,3), 96, 6, I.f); }
    else { s.hline(140, 180, 96, I.bg); }     // blink!
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  fallon(s, t) {                              // NAS Fallon — Top Gun jets (Ben asked)
    SPR.stars(s, t, 10, 5, 0, 24); SPR.sun(s, 40, 30, 10, t);
    SPR.mountains(s, GROUND, 5, 22, I.d2);
    // jets screaming across
    const jx = (t * 260) % (s.W + 120) - 60;
    SPR.jet(s, jx, 50, 1.4, t); SPR.jet(s, jx - 70, 64, 1.1, t);
    SPR.ground(s, GROUND, I.f);
    s.rectO(200, 120, 90, 22, I.f); s.text("DANGER", 206, 124, I.hot, 1); s.text("MIL OPS", 206, 132, I.f, 1);
    drawAce(s, t);
  },
  area51(s, t) {                              // Rachel / ET Highway
    bgNight(s, t, 14); SPR.mountains(s, GROUND, 6, 24, I.d1);
    SPR.ufo(s, 200 + s.wob(40, 8), 50, t);
    SPR.ground(s, GROUND);
    s.rect(40, GROUND-2, 6, 2, I.d2); s.rect(43, GROUND-12, 1, 10, I.d2);  // black mailbox
    s.rectO(60, 118, 120, 18, I.f); s.text("EXTRATERRESTRIAL HWY", 64, 122, I.hot, 1);
    drawAce(s, t);
  },
  hoover_dam(s, t) {
    SPR.stars(s, t, 8, 5, 0, 20);
    s.rect(0, 40, s.W, 18, I.d2);            // lake mead behind
    s.poly([[110, 40],[210, 40],[200, GROUND],[120, GROUND]], I.f);  // dam curve
    for (let y=50;y<GROUND;y+=8) s.hline(120 + (y-40)*0.06, 200 - (y-40)*0.06, y, I.d2);
    s.vline(90, 40, 80, I.d3); s.vline(230, 40, 80, I.d3);  // transmission towers
    SPR.ground(s, GROUND, I.d3);
    drawAce(s, t);
  },
  bonneville(s, t) {                          // salt flats land-speed (Ace flat out)
    SPR.mountains(s, 110, 5, 14, I.d1);
    s.hline(0, s.W, 112, I.d3);
    s.rect(0, 112, s.W, s.H-112, I.d1);       // dead-flat salt
    for (let k=0;k<6;k++) s.hline(0, s.W, 120+k*8, I.d1);
    drawAce(s, t);
    const mph = 180 + Math.floor(s.saw(2)*120);
    s.text(mph + " MPH", 200, 30, s.blink(0.3)?I.hot:I.f, 2);
  },
  laguna_seca(s, t) {                         // the Corkscrew
    SPR.mountains(s, 90, 4, 24, I.d1);
    // the famous dropping esses
    s.line(20, 60, 120, 70, I.d3); s.line(120, 70, 150, 110, I.d3); s.line(150, 110, 110, 140, I.d3); s.line(110,140, 200, GROUND, I.d3);
    s.line(24, 64, 124, 74, I.f); s.line(124,74,154,114,I.f); s.line(154,114,114,144,I.f); s.line(114,144,204,GROUND,I.f);
    SPR.ground(s, GROUND, I.f);
    // a car carving the corkscrew
    const f = s.saw(4); let cx, cy;
    if (f<0.33){cx=20+f*3*100;cy=60+f*3*10;} else if(f<0.66){const g=(f-0.33)*3;cx=120+g*30;cy=70+g*40;} else {const g=(f-0.66)*3;cx=150-g*40;cy=110+g*30;}
    drawAce(s, t);
  },
  track(s, t) {                               // generic road course
    SPR.stars(s, t, 8, 5, 0, 20); SPR.mountains(s, 110, 4, 20, I.d1);
    s.ring(160, 130, 70, I.d3); s.ring(160, 130, 56, I.d1);  // oval
    SPR.ground(s, GROUND, I.f);
    // checkered start/finish
    for (let k=0;k<8;k++) s.rect(140+k*5, 60, 5, 5, k%2?I.f:I.d1);
    const a = t*1.2; drawAce(s, t);
  },
  disneyland(s, t) {
    bgNight(s, t, 24, 0, 70);
    // fireworks
    for (let k=0;k<3;k++){const fk=Math.floor(t/2+k)%3; const fx=80+k*90, fy=40; if((t%2)<1){for(let j=0;j<10;j++){const a=j*0.63; const p=(t%2); s.plot(fx+Math.cos(a)*p*24, fy+Math.sin(a)*p*24, I.hot);}}}
    // castle
    s.rect(120, 90, 80, GROUND-90, I.d3);
    [124,150,176].forEach((x,i)=>{ s.rect(x, 70-i%2*8, 16, 30, I.f); s.poly([[x,70-i%2*8],[x+8,55-i%2*8],[x+16,70-i%2*8]], I.hot); });
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  amusement(s, t) {                           // generic park: coaster + ferris
    bgNight(s, t, 34, 0, 70);
    SPR.coaster(s, 20, 110, t); SPR.ferris(s, 250, 100, 30, t);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  santa_monica(s, t) {
    SPR.stars(s, t, 10, 5, 0, 30); SPR.sun(s, 280, 60, 14, t);
    s.rect(0, 132, s.W, s.H-132, I.d1);       // ocean
    for (let y=134;y<s.H;y+=5) s.hline(0, s.W, y + s.wob(1,1,y), I.d2);
    s.rect(40, 110, 180, 4, I.d3);            // pier deck
    for (let x=50;x<210;x+=14) s.vline(x, 114, 132, I.d2);
    SPR.ferris(s, 100, 90, 22, t);
    SPR.ground(s, 110, I.f);
    drawAce(s, t);
  },
  lake_havasu(s, t) {                          // London Bridge, shipped to AZ (egg)
    SPR.sun(s, 60, 40, 12, t); SPR.mountains(s, 96, 5, 16, I.d1);
    s.rect(0, 130, s.W, s.H-130, I.d1);
    SPR.arch(s, 100, 130, 60, 40, I.f); SPR.arch(s, 170, 130, 60, 40, I.f);
    s.rect(50, 96, 180, 8, I.d3);
    for (let k=0;k<30;k++){const x=s.rng(k+1)()*s.W; s.plot(x, 132+s.rng(k+2)()*16, s.blink(0.8)?I.hot:I.d1);}
    s.textC("LONDON BRIDGE", 8, I.d3, 1);
    drawAce(s, t);
  },
  sf_japantown(s, t) {                         // encounter scene
    bgNight(s, t, 44, 0, 70);
    SPR.pagoda(s, 90, GROUND, t);
    // torii gate
    s.vline(220, GROUND-40, GROUND, I.f); s.vline(250, GROUND-40, GROUND, I.f);
    s.rect(212, GROUND-44, 46, 4, I.hot); s.rect(216, GROUND-37, 38, 3, I.f);
    SPR.lantern(s, 180, GROUND-50, t, 0); SPR.lantern(s, 270, GROUND-50, t, 1.5);
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },

  // ---------- LIFE OF A SHOW CAR: where she was born / grew up ----------
  koinoya(s, t) {                              // Richmond — the Edo relic shop (born)
    s.rect(0, 0, s.W, s.H, I.bg);
    for (let y = 8; y < 122; y += 12) s.hline(0, s.W, y, I.d1);   // tiled back wall
    for (let x = 0; x < s.W; x += 24) s.vline(x, 0, 120, I.d1);
    // crowded relic shelves, left & right
    for (let r = 0; r < 5; r++) {
      s.hline(0, 72, 22 + r*20, I.d2); s.hline(248, s.W, 22 + r*20, I.d2);
      for (let k = 0; k < 5; k++) s.rect(4 + k*13, 14 + r*20, 9, 7, s.rng(r*9+k)() > 0.5 ? I.d2 : I.d3);
      for (let k = 0; k < 4; k++) s.rect(252 + k*15, 14 + r*20, 10, 7, s.rng(r+k+3)() > 0.5 ? I.d2 : I.d3);
    }
    // a rack of naginata / ceremonial blades, each topped with a playing-card suit
    const suits = ["♠", "♥", "♣", "★", "♠"];
    for (let i = 0; i < 5; i++) {
      const x = 108 + i*22, top = 20 + (i % 2) * 8;
      s.vline(x, top, GROUND - 4, I.d3);
      s.poly([[x-3, top], [x, top-16], [x+3, top]], I.f);        // blade
      s.text(suits[i], x-2, top-27, s.blink(1.5 + i*0.3) ? I.hot : I.d2, 1);
    }
    // hanging paper lantern + a koi arcing in a low tank
    s.vline(72, 0, 42, I.d2); s.disc(72, 48, 7, s.blink(2.4, 0.7) ? I.hot : I.d3);
    for (let k = 0; k < 3; k++) { const fx = 196 + k*10 + s.wob(16, 4, k*2); s.line(fx, 152, fx+9, 150, I.d3); s.poly([[fx+9,148],[fx+13,150],[fx+9,152]], I.d3); }
    SPR.ground(s, GROUND, I.d3);
    drawAce(s, t, { moving: false });
  },
  oakland_aisha(s, t) {                        // downtown Oakland — the AiSha garage (grew up)
    SPR.stars(s, t, 18, 5, 0, 40);
    // downtown skyline rising behind
    const r = s.rng(7);
    for (let x = 0; x < s.W; x += 18) {
      const h = 30 + r()*46; s.rect(x, 70 - 0, 15, -0 + 1, I.bg);
      s.rect(x, 84 - h, 15, h, I.d1);
      for (let wy = 86 - h; wy < 80; wy += 7) if (r() > 0.55) s.plot(x + 3 + (r()*8|0), wy, I.d3);
    }
    // the 1926 red-brick garage facade
    s.rect(18, 84, 284, GROUND - 84, I.d2);
    s.dither(18, 84, 284, GROUND - 84, 3, I.d3);                  // brick texture
    s.text("AISHALLC", 116, 74, s.blink(2.0, 0.85) ? I.hot : I.d3, 1);   // painted roofline
    // arched doorway + 1926 keystone
    s.rect(120, 104, 80, GROUND - 104, I.bg);
    s.poly([[120, 104], [160, 92], [200, 104]], I.bg);
    s.text("1926", 146, 96, I.f, 1);
    // roll-up door with a bold kanji cut into it
    s.rect(126, 110, 68, GROUND - 110, I.d3);
    for (let yy = 112; yy < GROUND; yy += 5) s.hline(126, 194, yy, I.d1);
    const kx = 160, ky = 132;                                    // abstract bold kanji strokes
    s.rect(kx-16, ky-12, 32, 3, I.bg); s.rect(kx-2, ky-18, 4, 12, I.bg);
    s.line(kx, ky-6, kx-15, ky+16, I.bg); s.line(kx, ky-6, kx+15, ky+16, I.bg);
    s.rect(kx-10, ky+6, 20, 3, I.bg); s.vline(kx, ky-6, ky+18, I.bg);
    // graffiti-tagged side windows
    [40, 250].forEach(wx => { s.rect(wx, 110, 40, 30, I.d1);
      for (let k = 0; k < 5; k++) s.line(wx + r()*40, 110 + r()*30, wx + r()*40, 110 + r()*30, I.d3); });
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t, { moving: false });
  },
  museum(s, t) {                               // any museum the driver & Ace visit
    SPR.stars(s, t, 16, 5, 0, 40);
    // a neoclassical facade: steps, columns, pediment, a banner
    s.rect(40, 70, 240, GROUND - 70, I.d2);
    s.poly([[36, 70], [160, 40], [284, 70]], I.d3);          // pediment
    for (let cx = 64; cx <= 256; cx += 24) { s.rect(cx, 78, 8, GROUND - 86, I.bg); s.rect(cx, 78, 8, GROUND - 86, I.d3, ); s.rect(cx + 2, 80, 4, GROUND - 90, I.bg); } // columns
    s.rect(150, GROUND - 26, 20, 26, I.bg);                  // doorway
    // hanging banner
    s.rect(120, 44, 80, 16, s.blink(2.4, 0.85) ? I.f : I.d3); s.text("MUSEUM", 130, 48, I.bg, 1);
    for (let k = 0; k < 4; k++) s.hline(40, 280, GROUND - 2 - k * 2, I.d3);  // steps
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t, { moving: false });
  },
  aquarium(s, t) {                             // Monterey — Cannery Row, the kelp tank
    for (let y = 0; y < 56; y += 4) s.dither(0, y, s.W, 4, 5, I.d1);          // fog
    s.rect(0, 150, s.W, s.H - 150, I.d1);                                      // bay
    for (let y = 152; y < s.H; y += 5) s.hline(0, s.W, y + s.wob(1, 1.2, y), I.d2);
    s.rect(40, 84, 240, GROUND - 84, I.d2);                                    // building
    s.rect(110, 96, 100, GROUND - 100, I.bg); s.rectO(110, 96, 100, GROUND - 100, I.f);  // tank glass
    for (let k = 0; k < 6; k++) { const kx = 120 + k * 15; for (let yy = GROUND - 6; yy > 104; yy -= 4) s.plot(kx + s.wob(3, 2.2, kx + yy * 0.1), yy, I.d3); } // kelp
    for (let k = 0; k < 5; k++) { const fx = 116 + ((k * 37 + t * 18) % 80); s.plot(fx, 120 + (k * 9) % 38, s.blink(0.8) ? I.hot : I.f); } // fish
    s.text("AQUARIUM", 128, 86, I.bg, 1);
    s.rect(300, GROUND - 30, 3, 30, I.d2); s.disc(301, GROUND - 34, 8, I.d3);  // a cypress
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t, { moving: false });
  },
  storage(s, t) {                              // Livermore — the storage row, unit 137 lit & open
    SPR.stars(s, t, 12, 5, 0, 50);
    s.rect(0, 74, s.W, GROUND - 74, I.d1);
    for (let i = 0; i < 8; i++) {
      const dx = 12 + i * 38;
      s.rectO(dx, 96, 32, GROUND - 96, I.d3);
      for (let yy = 100; yy < GROUND; yy += 5) s.hline(dx + 2, dx + 30, yy, I.d2);
      s.text(String(130 + i), dx + 6, 86, I.d2, 1);
    }
    const ux = 12 + 7 * 38;                                                    // unit "137" — open, lit
    s.rect(ux, 96, 32, GROUND - 96, I.bg);
    s.rectO(ux, 96, 32, GROUND - 96, s.blink(1.4) ? I.hot : I.f);
    s.text("137", ux + 6, 86, s.blink(1.4) ? I.hot : I.f, 1);
    s.disc(ux + 16, 112, 2, s.blink(0.9) ? I.hot : I.d3);                      // a bare bulb inside
    SPR.ground(s, GROUND, I.d3);
    drawAce(s, t, { moving: false });
  },

  mojave(s, t) {
    SPR.sun(s, 280, 36, 11, t); SPR.mountains(s, GROUND, 5, 16, I.d1);
    for (let k=0;k<5;k++) SPR.windturbine(s, 30+k*30, GROUND-10, 30+ (k%2)*8, t);
    // airliner boneyard fuselages
    for (let k=0;k<3;k++){const x=180+k*40; s.rect(x, GROUND-8, 30, 6, I.d2); s.poly([[x+30,GROUND-5],[x+38,GROUND-8],[x+38,GROUND-2]], I.d2);}
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  lone_pine(s, t) {                            // Mt Whitney + western movie egg
    SPR.stars(s, t, 8, 5, 0, 18);
    SPR.mountains(s, 110, 2, 60, I.f, 1.6); SPR.mountains(s, 120, 7, 40, I.d2);
    // alabama hills boulders
    for (let k=0;k<6;k++) s.disc(20+k*30, GROUND-4, 5+k%3*2, I.d3);
    SPR.ground(s, GROUND, I.f);
    s.rectO(220, 120, 70, 24, I.d2); s.line(220, 120, 211, 112, I.d2); s.rect(211, 108, 14, 6, I.f); // clapperboard
    drawAce(s, t);
  },
  reno(s, t) {
    bgNight(s, t, 54, 0, 70);
    s.vline(80, 70, 110, I.f); s.vline(240, 70, 110, I.f); s.rect(80, 66, 161, 6, I.d3);
    SPR.neon(s, 96, 80, "RENO", t, 2);
    s.text("BIGGEST LITTLE CITY", 92, 100, s.blink(0.9)?I.hot:I.d1, 1);
    SPR.ground(s, 110, I.f);
    drawAce(s, t);
  },
  salt_lake(s, t) {
    SPR.stars(s, t, 10, 5, 0, 20);
    SPR.mountains(s, 110, 3, 44, I.d1, 1.3);     // wasatch
    // temple spires
    [150,170,190].forEach((x,i)=>{ s.rect(x, 80, 8, GROUND-80, I.d3); s.poly([[x,80],[x+4,64],[x+8,80]], I.f); });
    s.rect(60, 130, s.W-60, 6, I.d1);            // great salt lake gleam
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  city(s, t) {                                  // generic city skyline at night
    bgNight(s, t, 64, 0, 64);
    const r = s.rng(3);
    for (let x=0;x<s.W;x+=18){ const h=30+r()*70; s.rect(x, GROUND-h, 16, h, I.d2);
      for (let wy=GROUND-h+4; wy<GROUND-4; wy+=8) for (let wx=x+2; wx<x+14; wx+=5) if (r()>0.5) s.plot(wx, wy, I.hot); }
    SPR.ground(s, GROUND, I.f);
    drawAce(s, t);
  },
  park(s, t) {                                  // generic park fallback
    SPR.stars(s, t, 10, 5, 0, 24); SPR.sun(s, 270, 40, 12, t);
    SPR.mountains(s, 116, 5, 40, I.d2, 1.2); SPR.mountains(s, 130, 9, 24, I.d3);
    SPR.ground(s, GROUND, I.f); SPR.pine(s, 36, GROUND, 1.4); SPR.pine(s, 290, GROUND, 1.2);
    drawAce(s, t);
  },
  encounter(s, t) {                             // generic encounter (non-JP)
    bgNight(s, t, 74, 0, 70);
    SPR.city(s, t);
    s.textC("HOLA  你好  BONJOUR", 14, s.blink(1.2)?I.hot:I.d2, 1);
  },
};

// kind → fallback scene id (geocoded addresses / minor POIs)
const KIND_SCENE = { gas: "gas", park: "park", track: "track", amusement: "amusement",
  city: "drive_city", encounter: "encounter", museum: "museum" };

// which scrolling-drive skin fits a region when there's no bespoke scene
function _driveEnv(snap) {
  if (snap.kind === "city") return "drive_city";
  if (snap.region === "UT") return "drive_mountain";   // red-rock & high plateau country
  return "drive_desert";                                 // NV/AZ/CA basin & range
}

function sceneIdFor(snap) {
  if (!snap) return "drive_desert";
  if (snap.status === "stranded") return "stranded";
  if (snap.scene && SCENES[snap.scene]) return snap.scene;
  const k = KIND_SCENE[snap.kind];
  if (k && SCENES[k]) return k;
  return _driveEnv(snap);                                 // generic spots → the world goes by
}
function sceneFor(snap) { return SCENES[sceneIdFor(snap)] || SCENES.drive_desert; }
