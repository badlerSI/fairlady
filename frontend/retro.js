"use strict";
/* FAIRLADY retro scene engine — Apple II / C64-class monochrome vector animation.
 * Logical screen is 320x200 (C64 hi-res), upscaled with chunky pixels. One hue: amber
 * phosphor, drawn in a few tints so it reads monochrome. Scenes are draw(s,t) functions. */

const RETRO_W = 320, RETRO_H = 200;

// SOUL Interface cyan phosphor — values lifted byte-exact from the brand (#38d6ec on #0e0c0a).
// Monotone by design: one hot cyan blooming out of warm near-black, like the koi-CRT posterization.
const INK = {
  bg:  "#0e0c0a",   // warm near-black background (brand --bg)
  d1:  "#13262a",   // darkest dim cyan — shadow / scanline floor
  d2:  "#1f6f7d",   // mid-dim cyan — secondary, dithered fills
  d3:  "#2ba8bf",   // mid cyan — borders, hatching
  f:   "#38d6ec",   // PRIMARY cyan phosphor (brand --accent)
  hot: "#b8f4ff",   // near-white cyan highlight — hot pixels, stars, glints
  red: "#e23b2e",   // sparing brand hazard accent (afterburner / hazards only)
};

// 4x4 Bayer matrix for ordered dithering (classic mono shading)
const BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]];

// 5x7 bitmap font — authentic chunky glyphs. Each glyph = 7 rows of 5 chars ('#'/' ').
const FONT = (() => {
  const G = {};
  const def = (ch, rows) => { G[ch] = rows; };
  def("A",["  #  "," # # ","#   #","#####","#   #","#   #","#   #"]);
  def("B",["#### ","#   #","#### ","#   #","#   #","#   #","#### "]);
  def("C",[" ####","#    ","#    ","#    ","#    ","#    "," ####"]);
  def("D",["#### ","#   #","#   #","#   #","#   #","#   #","#### "]);
  def("E",["#####","#    ","#### ","#    ","#    ","#    ","#####"]);
  def("F",["#####","#    ","#### ","#    ","#    ","#    ","#    "]);
  def("G",[" ####","#    ","#    ","#  ##","#   #","#   #"," ####"]);
  def("H",["#   #","#   #","#####","#   #","#   #","#   #","#   #"]);
  def("I",["#####","  #  ","  #  ","  #  ","  #  ","  #  ","#####"]);
  def("J",["#####","   # ","   # ","   # ","#  # ","#  # "," ##  "]);
  def("K",["#   #","#  # ","###  ","# #  ","#  # ","#  # ","#   #"]);
  def("L",["#    ","#    ","#    ","#    ","#    ","#    ","#####"]);
  def("M",["#   #","## ##","# # #","#   #","#   #","#   #","#   #"]);
  def("N",["#   #","##  #","# # #","#  ##","#   #","#   #","#   #"]);
  def("O",[" ### ","#   #","#   #","#   #","#   #","#   #"," ### "]);
  def("P",["#### ","#   #","#   #","#### ","#    ","#    ","#    "]);
  def("Q",[" ### ","#   #","#   #","#   #","# # #","#  # "," ## #"]);
  def("R",["#### ","#   #","#   #","#### ","# #  ","#  # ","#   #"]);
  def("S",[" ####","#    ","#    "," ### ","    #","    #","#### "]);
  def("T",["#####","  #  ","  #  ","  #  ","  #  ","  #  ","  #  "]);
  def("U",["#   #","#   #","#   #","#   #","#   #","#   #"," ### "]);
  def("V",["#   #","#   #","#   #","#   #","#   #"," # # ","  #  "]);
  def("W",["#   #","#   #","#   #","# # #","# # #","## ##","#   #"]);
  def("X",["#   #","#   #"," # # ","  #  "," # # ","#   #","#   #"]);
  def("Y",["#   #","#   #"," # # ","  #  ","  #  ","  #  ","  #  "]);
  def("Z",["#####","   # ","  #  "," #   ","#    ","#    ","#####"]);
  def("0",[" ### ","#   #","#  ##","# # #","##  #","#   #"," ### "]);
  def("1",["  #  "," ##  ","  #  ","  #  ","  #  ","  #  "," ### "]);
  def("2",[" ### ","#   #","   # ","  #  "," #   ","#    ","#####"]);
  def("3",["#####","   # ","  #  ","   # ","    #","#   #"," ### "]);
  def("4",["   # ","  ## "," # # ","#  # ","#####","   # ","   # "]);
  def("5",["#####","#    ","#### ","    #","    #","#   #"," ### "]);
  def("6",[" ### ","#    ","#    ","#### ","#   #","#   #"," ### "]);
  def("7",["#####","    #","   # ","  #  "," #   "," #   "," #   "]);
  def("8",[" ### ","#   #","#   #"," ### ","#   #","#   #"," ### "]);
  def("9",[" ### ","#   #","#   #"," ####","    #","    #"," ### "]);
  def(" ",["     ","     ","     ","     ","     ","     ","     "]);
  def(".",["     ","     ","     ","     ","     ","  ## ","  ## "]);
  def(",",["     ","     ","     ","     ","  ## ","  ## "," #   "]);
  def(":",["     ","  ## ","  ## ","     ","  ## ","  ## ","     "]);
  def("'",["  #  ","  #  "," #   ","     ","     ","     ","     "]);
  def("!",["  #  ","  #  ","  #  ","  #  ","  #  ","     ","  #  "]);
  def("?",[" ### ","#   #","   # ","  #  ","  #  ","     ","  #  "]);
  def("-",["     ","     ","     ","#####","     ","     ","     "]);
  def("/",["    #","    #","   # ","  #  "," #   ","#    ","#    "]);
  def("+",["     ","  #  ","  #  ","#####","  #  ","  #  ","     "]);
  def("*",["     ","# # #"," ### ","#####"," ### ","# # #","     "]);
  def("@",[" ### ","#   #","# ###","# # #","# ###","#    "," ### "]);
  def("$",["  #  "," ####","# #  "," ### ","  # #","#### ","  #  "]);
  def("#",[" # # ","#####"," # # ","#####"," # # ","     ","     "]);
  def("(",["   # ","  #  "," #   "," #   "," #   ","  #  ","   # "]);
  def(")",[" #   ","  #  ","   # ","   # ","   # ","  #  "," #   "]);
  def("►",["#    ","##   ","### #","#####","### #","##   ","#    "]); // ►
  def("★",["  #  ","  #  ","#####"," ### ","## ##","#   #","     "]); // ★
  def("♠",["  #  "," ### ","#####","#####","## ##","  #  "," ### "]); // ♠
  def("♥",[" # # ","#####","#####","#####"," ### ","  #  ","     "]); // ♥
  def("♣",[" ### "," ### ","## ##","#####","## ##","  #  "," ### "]); // ♣
  return G;
})();

class RetroScene {
  constructor(canvas) {
    this.cv = canvas;
    // supersample the backing store: scenes are authored in 320x200 logical space, but the
    // canvas renders at SSx that — so the high-res digitized car keeps its detail (cleaner),
    // while hand-drawn pixels stay the same chunky size relative to the display.
    this.SS = 3;
    this.cv.width = RETRO_W * this.SS; this.cv.height = RETRO_H * this.SS;
    this.ctx = canvas.getContext("2d");
    this.ctx.imageSmoothingEnabled = false;
    this.W = RETRO_W; this.H = RETRO_H; this.INK = INK;
    this.scene = null; this.t0 = 0; this.now = 0; this.id = null;
    this.opts = {};
    this._raf = null;
    this._last = 0;
  }

  set(id, scene, opts = {}) {
    this.id = id; this.scene = scene; this.opts = opts;
    this.t0 = this.now;        // reset scene clock
  }

  start() {
    if (this._raf) return;
    const loop = (ts) => {
      if (!this._last) this._last = ts;
      this.now = ts / 1000;
      this.ctx.setTransform(this.SS, 0, 0, this.SS, 0, 0);  // draw in logical space, render at SSx
      this.ctx.imageSmoothingEnabled = false;
      this.clear();
      if (this.scene) {
        try { this.scene(this, this.now - this.t0); } catch (e) {}
      }
      this._raf = requestAnimationFrame(loop);
    };
    this._raf = requestAnimationFrame(loop);
  }

  // ---- core drawing (snaps to integer pixels) ----
  clear() { this.ctx.clearRect(0, 0, this.W, this.H); }
  color(c) { this.ctx.fillStyle = c || INK.f; }

  plot(x, y, c) { this.color(c); this.ctx.fillRect(x | 0, y | 0, 1, 1); }

  rect(x, y, w, h, c) { this.color(c); this.ctx.fillRect(x | 0, y | 0, w | 0, h | 0); }

  rectO(x, y, w, h, c) {
    this.color(c); x|=0; y|=0; w|=0; h|=0;
    this.ctx.fillRect(x, y, w, 1); this.ctx.fillRect(x, y + h - 1, w, 1);
    this.ctx.fillRect(x, y, 1, h); this.ctx.fillRect(x + w - 1, y, 1, h);
  }

  hline(x0, x1, y, c) { if (x1 < x0) [x0, x1] = [x1, x0]; this.rect(x0, y, x1 - x0 + 1, 1, c); }
  vline(x, y0, y1, c) { if (y1 < y0) [y0, y1] = [y1, y0]; this.rect(x, y0, 1, y1 - y0 + 1, c); }

  line(x0, y0, x1, y1, c) {            // Bresenham
    x0|=0; y0|=0; x1|=0; y1|=0;
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      this.plot(x0, y0, c);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }

  poly(pts, c, fill = true) {
    const ct = this.ctx; ct.beginPath();
    ct.moveTo(pts[0][0] | 0, pts[0][1] | 0);
    for (let i = 1; i < pts.length; i++) ct.lineTo(pts[i][0] | 0, pts[i][1] | 0);
    ct.closePath();
    if (fill) { ct.fillStyle = c || INK.f; ct.fill(); }
    else { ct.strokeStyle = c || INK.f; ct.lineWidth = 1; ct.stroke(); }
  }

  disc(cx, cy, r, c) {
    this.color(c); cx|=0; cy|=0;
    for (let y = -r; y <= r; y++) {
      const w = Math.floor(Math.sqrt(r * r - y * y));
      this.ctx.fillRect(cx - w, cy + y, 2 * w + 1, 1);
    }
  }
  ring(cx, cy, r, c) {
    this.color(c);
    let x = r, y = 0, err = 1 - r;
    const p = (a, b) => this.ctx.fillRect(a, b, 1, 1);
    while (x >= y) {
      p(cx+x,cy+y); p(cx+y,cy+x); p(cx-y,cy+x); p(cx-x,cy+y);
      p(cx-x,cy-y); p(cx-y,cy-x); p(cx+y,cy-x); p(cx+x,cy-y);
      y++; if (err < 0) err += 2*y+1; else { x--; err += 2*(y-x)+1; }
    }
  }

  // ordered-dither fill: level 0..16 controls density. great for mono shading.
  dither(x, y, w, h, level, c) {
    this.color(c); x|=0; y|=0; w|=0; h|=0;
    const ct = this.ctx;
    for (let j = 0; j < h; j++)
      for (let i = 0; i < w; i++)
        if (BAYER[(y + j) & 3][(x + i) & 3] < level) ct.fillRect(x + i, y + j, 1, 1);
  }

  // text in the 5x7 font. scale = pixel size. returns width drawn.
  text(str, x, y, c, scale = 1, spacing = 1) {
    this.color(c); str = (str || "").toUpperCase();
    let cx = x | 0;
    for (const ch of str) {
      const g = FONT[ch] || FONT[" "];   // unsupported glyphs (CJK etc.) render blank, not "?"
      for (let r = 0; r < 7; r++)
        for (let col = 0; col < 5; col++)
          if (g[r][col] === "#")
            this.ctx.fillRect(cx + col * scale, (y | 0) + r * scale, scale, scale);
      cx += (5 + spacing) * scale;
    }
    return cx - x;
  }
  textW(str, scale = 1, spacing = 1) { return (str || "").length * (5 + spacing) * scale - spacing * scale; }
  textC(str, y, c, scale = 1) { this.text(str, (this.W - this.textW(str, scale)) / 2, y, c, scale); }

  // ---- seeded rng (deterministic per scene seed) ----
  rng(seed) {
    let s = (seed | 0) || 1;
    return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  }

  // ---- animation helpers ----
  blink(period = 1, duty = 0.5) { return ((this.now / period) % 1) < duty; }
  cycle(n, period = 1) { return Math.floor(((this.now / period) % 1) * n) % n; }
  wob(amp, period = 1, phase = 0) { return amp * Math.sin((this.now / period) * Math.PI * 2 + phase); }
  saw(period = 1) { return (this.now / period) % 1; }
}
