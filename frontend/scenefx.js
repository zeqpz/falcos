// The Falcos scene's life, laid exactly over the night plate (#bgwall's background, bonus_wall.webp):
// the canopy's FALCOS neon now and then stuttering off (sign_off), the woman by the Tahoe and the
// cashier in the window each blinking on a clock of their own (blink_woman / blink_cashier), and
// the two Blender loops - her cigarette smoke, ember and exhale (fx_woman); the window's glass
// reflection and the coin glints at the till (fx_cashier).
//
// Everything is described by assets/scene/scene.json in PLATE pixels (the plate is 3840x2160).
// The layer (#scenefx) is put inside #bgwall and sized to the plate exactly as the browser draws
// #bgwall's background - its computed background-size (cover / contain) and background-position
// read straight off the element, so it can never drift from the picture at any window size or
// orientation - and every overlay sits in it in percent of the plate. Being inside #bgwall it
// rides the wall's lean, hop and the camera with it.
//
// The loops ship as grid frame sheets ({w, h, cols, per_sheet, sheets[], frames, fps}); each is
// drawn on a canvas, one frame at a time at its own 30 fps, decoded once at the size the screen
// shows it (never above the sheet's own). A loop whose box is off the screen (a phone in portrait
// shows only part of the plate) is not fetched until it would show. Nothing runs while the tab is
// hidden; with reduced motion the loops hold their first frame and nothing flickers or blinks.
//
//   SceneFX.start(hostElement)   once, with #bgwall
//   SceneFX.surge()              a nervous stutter of the sign right now (a big win)
(function () {
  "use strict";
  const BASE = "assets/scene/";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // the neon: mostly on, now and then a stutter (art/falcos/previews/showcase reference)
  const NEON_GAP = [1800, 6000];                                  // ms between stutters
  const NEON_SHORT = [90, 70], NEON_LONG = [70, 60, 50, 120, 40, 260], NEON_LONG_ODDS = .3;
  const BLINK_MS = 130, BLINKS = { blink_woman: [2500, 5200], blink_cashier: [3000, 6000] };

  let host = null, root = null, cfg = null, rect = null;
  const els = {}, loops = [], timers = new Set();
  let raf = 0, live = false;

  const later = (ms, fn) => { const id = setTimeout(() => { timers.delete(id); fn(); }, ms); timers.add(id); return id; };
  const rand = (a, b) => a + Math.random() * (b - a);

  function pct(r) {
    const [W, H] = cfg.size;
    return { left: r[0] / W * 100 + "%", top: r[1] / H * 100 + "%", width: r[2] / W * 100 + "%", height: r[3] / H * 100 + "%" };
  }

  // where the plate is drawn inside host, in host px - from host's own computed background
  function plateBox() {
    const W = host.clientWidth, H = host.clientHeight, cs = getComputedStyle(host);
    const [pw0, ph0] = cfg.size;
    const size = (cs.backgroundSize || "cover").split(",").pop().trim();
    let s;
    if (size === "contain") s = Math.min(W / pw0, H / ph0);
    else if (size === "cover") s = Math.max(W / pw0, H / ph0);
    else {   // "<w> <h>" in px or % ("auto" for one of them): the plate keeps its shape
      const [w, h = "auto"] = size.split(/\s+/);
      const len = (v, box, nat) => v.endsWith("%") ? box * parseFloat(v) / 100 / nat : v.endsWith("px") ? parseFloat(v) / nat : null;
      s = len(w, W, pw0) ?? len(h, H, ph0) ?? Math.max(W / pw0, H / ph0);
    }
    const pw = pw0 * s, ph = ph0 * s;
    const pos = (cs.backgroundPosition || "50% 50%").split(",").pop().trim().split(/\s+/);
    const at = (v, free) => v.endsWith("%") ? free * parseFloat(v) / 100 : v.endsWith("px") ? parseFloat(v) : free / 2;
    return { x: at(pos[0] || "50%", W - pw), y: at(pos[1] || "50%", H - ph), w: pw, h: ph, s };
  }

  function layout() {
    if (!root || !cfg) return;
    rect = plateBox();
    Object.assign(root.style, { left: rect.x.toFixed(2) + "px", top: rect.y.toFixed(2) + "px",
                                width: rect.w.toFixed(2) + "px", height: rect.h.toFixed(2) + "px" });
    for (const L of loops) wantLoop(L);
  }

  /* ---------- the loops ---------- */
  function onScreen(el) {
    const r = el.getBoundingClientRect();
    return r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight && r.width > 0;
  }
  // fetch a loop's sheets once it would show, decoded at the size the screen draws it
  function wantLoop(L) {
    if (L.loading || !onScreen(L.cv)) return;
    const shown = L.cv.getBoundingClientRect().width * Math.min(window.devicePixelRatio || 1, 1.5);
    const k = Math.max(.35, Math.min(1, shown / L.d.w * 1.1));
    L.loading = Promise.all(L.d.sheets.map(async name => {
      const blob = await fetch(BASE + name).then(r => r.ok ? r.blob() : Promise.reject(new Error(name + " " + r.status)));
      const im = new Image();
      im.src = URL.createObjectURL(blob);
      await im.decode();
      if (k < .97 && typeof createImageBitmap === "function") {
        try {
          const bm = await createImageBitmap(im, { resizeWidth: Math.round(im.naturalWidth * k), resizeHeight: Math.round(im.naturalHeight * k), resizeQuality: "high" });
          URL.revokeObjectURL(im.src);
          return { src: bm, k };
        } catch (e) { /* no resize: the sheet as it is */ }
      }
      return { src: im, k: 1 };
    })).then(sheets => {
      L.sheets = sheets;
      const k = sheets[0].k;
      L.cv.width = Math.round(L.d.w * k); L.cv.height = Math.round(L.d.h * k);
      L.f = -1; L.t0 = performance.now() - Math.random() * L.d.frames / L.d.fps * 1000;   // each starts somewhere in its loop
      draw(L, 0);
      kick();
    }).catch(e => { console.warn("scene loop:", e.message); });
  }
  function draw(L, f) {
    if (!L.sheets || f === L.f) return;
    const d = L.d, si = Math.floor(f / d.per_sheet), i = f % d.per_sheet, sh = L.sheets[si];
    if (!sh) return;
    const k = sh.k, w = Math.round(d.w * k), h = Math.round(d.h * k);
    const g = L.ctx;
    g.clearRect(0, 0, L.cv.width, L.cv.height);
    g.drawImage(sh.src, (i % d.cols) * d.w * k, Math.floor(i / d.cols) * d.h * k, w, h, 0, 0, L.cv.width, L.cv.height);
    L.f = f;
  }
  function step(now) {
    raf = 0;
    if (!live || RM) return;
    for (const L of loops) if (L.sheets) draw(L, Math.floor((now - L.t0) / 1000 * L.d.fps) % L.d.frames);
    raf = requestAnimationFrame(step);
  }
  function kick() { if (live && !RM && !raf && loops.some(L => L.sheets)) raf = requestAnimationFrame(step); }

  /* ---------- the sign and the blinks ---------- */
  function stutter(seq) {
    const off = els.sign_off;
    if (!off) return 0;
    let t = 0;
    seq.forEach((ms, i) => { later(t, () => { off.style.opacity = i % 2 ? "0" : (.75 + Math.random() * .25).toFixed(2); }); t += ms; });
    later(t, () => { off.style.opacity = "0"; });
    return t;
  }
  function neon() {
    if (!live) return;
    const t = stutter(Math.random() < NEON_LONG_ODDS ? NEON_LONG : NEON_SHORT);
    later(t + rand(...NEON_GAP), neon);
  }
  function blink(name) {
    const el = els[name];
    if (!live || !el) return;
    el.style.opacity = "1";
    later(BLINK_MS, () => { el.style.opacity = "0"; });
    later(rand(...BLINKS[name]), () => blink(name));
  }

  function run() {
    if (live || RM || document.hidden) return;
    live = true;
    later(rand(600, 2400), neon);
    for (const name of Object.keys(BLINKS)) later(rand(400, BLINKS[name][0]), () => blink(name));
    for (const L of loops) if (L.sheets) L.t0 = performance.now() - (L.f > 0 ? L.f : 0) / L.d.fps * 1000;   // carry on where it was
    kick();
  }
  function halt() {
    live = false;
    for (const id of timers) clearTimeout(id);
    timers.clear();
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    for (const k of ["sign_off", ...Object.keys(BLINKS)]) if (els[k]) els[k].style.opacity = "0";
  }

  async function start(el) {
    if (host || !el) return;
    host = el;
    try {
      cfg = await fetch(BASE + "scene.json").then(r => r.ok ? r.json() : Promise.reject(new Error("scene.json " + r.status)));
    } catch (e) { console.warn("scene fx unavailable:", e.message); return; }
    root = document.createElement("div");
    root.id = "scenefx";
    root.setAttribute("aria-hidden", "true");
    root.style.cssText = "position:absolute;pointer-events:none;overflow:visible;z-index:0";
    // the loops under the stills: the sign's off state and the closed eyes paint over them
    for (const [name, d] of Object.entries(cfg.layers)) {
      if (!d.sheets) continue;
      const cv = document.createElement("canvas");
      cv.className = "sfxloop " + name;
      Object.assign(cv.style, { position: "absolute", display: "block" }, pct(d.rect));
      root.appendChild(cv);
      loops.push({ name, d, cv, ctx: cv.getContext("2d"), sheets: null, loading: null, f: -1, t0: 0 });
    }
    for (const [name, d] of Object.entries(cfg.layers)) {
      if (d.sheets) continue;
      const im = new Image();
      im.alt = ""; im.draggable = false; im.decoding = "async";
      im.className = "sfxstill " + name;
      im.src = BASE + name + ".webp";
      Object.assign(im.style, { position: "absolute", display: "block", opacity: "0" }, pct(d.rect));
      root.appendChild(im);
      els[name] = im;
    }
    host.prepend(root);
    layout();
    let pend = 0;   // re-laid on the next frame, never inside the observer's own pass
    if (window.ResizeObserver) new ResizeObserver(() => { if (!pend) pend = requestAnimationFrame(() => { pend = 0; layout(); }); }).observe(host);
    addEventListener("resize", layout);
    document.addEventListener("visibilitychange", () => (document.hidden ? halt() : run()));
    run();
  }

  window.SceneFX = {
    start,
    surge() { if (live) stutter(NEON_LONG); },
    layout,
  };
})();
