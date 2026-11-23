// Falcos on an iPhone profile: canvases, WebGL textures, shown pictures and the layers WebKit must make (animating or
// 3D elements at LAYOUT size x DPR^2 under the transform-scaled #app), through load -> board -> spins.
// node probe.js <base> [spins] [engine: chromium|webkit]
const pw = require(process.env.PLAYWRIGHT || "playwright");
const [base = "http://localhost:8747", spins = "2", eng = "chromium", extra = ""] = process.argv.slice(2);
const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1";
(async () => {
  const b = await pw[eng].launch();
  const c = await b.newContext(eng === "webkit" ? { ...pw.devices["iPhone 12"] } : { viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA });
  await c.addInitScript(() => {
    const T = window.__tex = { live: new Map(), bytes: 0, ctx: 0, bmp: 0 };
    const A = window.__aud = { bytes: 0, n: 0, list: [] };
    for (const C of [window.AudioContext, window.webkitAudioContext, window.OfflineAudioContext]) {
      if (!C || C.prototype.__hooked) continue; C.prototype.__hooked = true;
      const dec = C.prototype.decodeAudioData;
      C.prototype.decodeAudioData = function (buf, ok, bad) {
        const inLen = buf && buf.byteLength;
        const note = b => { if (b) { const by = b.length * b.numberOfChannels * 4; A.bytes += by; A.n++; A.list.push([+(by / 1e6).toFixed(1), +b.duration.toFixed(1), inLen]); } return b; };
        const p = dec.call(this, buf, b => { note(b); ok && ok(b); }, bad);
        return p && p.then ? (ok ? p : p.then(note)) : p;
      };
    }
    const hook = P => {
      if (!P) return;
      const gc = HTMLCanvasElement.prototype.getContext;
      const bind = P.bindTexture, ti = P.texImage2D, ts = P.texStorage2D, del = P.deleteTexture;
      P.bindTexture = function (t, tex) { this.__cur = tex; return bind.apply(this, arguments); };
      const set = (gl, w, h) => { const tex = gl.__cur; if (!tex) return; const old = T.live.get(tex) || 0, n = w * h * 4; T.live.set(tex, Math.max(old, n)); T.bytes += Math.max(old, n) - old; };
      P.texImage2D = function (...a) { try { if (a.length >= 9) set(this, a[3], a[4]); else { const s = a[5]; if (s) set(this, s.width || s.videoWidth || s.naturalWidth || 0, s.height || s.videoHeight || s.naturalHeight || 0); } } catch (e) {} return ti.apply(this, a); };
      if (ts) P.texStorage2D = function (...a) { try { set(this, a[3], a[4]); } catch (e) {} return ts.apply(this, a); };
      P.deleteTexture = function (tex) { const o = T.live.get(tex); if (o) { T.bytes -= o; T.live.delete(tex); } return del.apply(this, arguments); };
    };
    hook(window.WebGLRenderingContext && WebGLRenderingContext.prototype); hook(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
    const gc = HTMLCanvasElement.prototype.getContext; const seen = new WeakSet();
    HTMLCanvasElement.prototype.getContext = function (t) { const r = gc.apply(this, arguments); if (r && /webgl/.test(t) && !seen.has(this)) { seen.add(this); T.ctx++; } if (r) (window.__cvs = window.__cvs || new Set()).add(this); return r; };
  });
  const p = await c.newPage();
  const errs = []; let crashed = false;
  p.on("pageerror", e => errs.push(e.message.slice(0, 160))); p.on("console", m => { if (m.type() === "error" || m.type() === "warning") errs.push(m.type() + " " + m.text().slice(0, 140)); }); p.on("crash", () => { crashed = true; console.log("*** CRASH"); });
  await p.goto(`${base}/index.html?sessionID=p${Date.now()}&rgs_url=${base}&lang=en&device=mobile${extra}`);
  const census = tag => p.evaluate(async tag => {
    const name = el => (el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + String(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className).split(" ").slice(0, 2).join("."));
    const all = [...(window.__cvs || [])];
    const cv = all.filter(c => c.width * c.height > 4).map(c => [name(c), c.width, c.height, +(c.width * c.height * 4 / 1e6).toFixed(1), c.isConnected ? "" : "off-page"]).sort((a, b) => b[3] - a[3]);
    const app = document.getElementById("app"), z = +getComputedStyle(app).zoom || 1;
    const pics = new Map(), layers = [], filt = [];
    const size = u => new Promise(res => { const i = new Image(); i.onload = () => res(i.naturalWidth * i.naturalHeight * 4 / 1e6); i.onerror = () => res(0); i.src = u; });
    const L = (el, why) => { const w = el.offsetWidth * z * 3, h = el.offsetHeight * z * 3; layers.push([+Math.min(156, w * h * 4 / 1e6).toFixed(1), name(el) + ":" + why]); };
    for (const el of document.querySelectorAll("*")) {
      if (!el.getClientRects().length) continue;
      const s = getComputedStyle(el);
      if (el.tagName === "IMG" && el.currentSrc) pics.set(el.currentSrc, name(el));
      for (const m of String(s.backgroundImage + " " + (s.maskImage || s.webkitMaskImage || "")).matchAll(/url\("?([^")]+)"?\)/g)) pics.set(m[1], name(el));
      if (s.filter !== "none") filt.push(name(el));
      if (el.offsetWidth === undefined) continue;
      if (/matrix3d/.test(s.transform) || s.perspective !== "none" || s.willChange !== "auto" || (s.backfaceVisibility === "hidden")) L(el, "3d/will-change");
      else if (s.mixBlendMode !== "normal") L(el, "blend");
    }
    const seenA = new Set();
    for (const a of document.getAnimations()) { if (a.playState !== "running" || !a.effect || !a.effect.target) continue; const t = a.effect.target; if (seenA.has(t) || !t.getClientRects || !t.getClientRects().length || t.offsetWidth === undefined) continue; seenA.add(t); L(t, a.animationName || a.transitionProperty || "anim"); }
    let picMB = 0; const plist = [];
    for (const [u, n] of pics) { if (u.startsWith("data:")) continue; const mb = await size(u); picMB += mb; plist.push([+mb.toFixed(1), (u.split("/assets/")[1] || u.slice(-30)), n]); }
    plist.sort((a, b) => b[0] - a[0]); layers.sort((a, b) => b[0] - a[0]);
    const cvMB = cv.reduce((s, c) => s + c[3], 0), layMB = layers.reduce((s, l) => s + l[0], 0), texMB = window.__tex.bytes / 1e6;
    let audMB = 0, rate = 0; const heldSet = new Set(), tracks = [];
    try { for (const b of Object.values(sfxBuf)) if (b) heldSet.add(b); } catch (e) {}
    try { for (const [n, pr] of Object.entries(musicTrack)) { const t = await Promise.race([pr, new Promise(r => setTimeout(() => r(null), 50))]); if (t && t.buf) { heldSet.add(t.buf); tracks.push(n); } } } catch (e) {}
    for (const b of heldSet) audMB += b.length * b.numberOfChannels * 4 / 1e6;
    try { rate = actx ? actx.sampleRate : 0; } catch (e) {}
    window.__aud.n = heldSet.size; window.__aud.list = [[rate, tracks.join("+")]];
    return { tag, audMB: +audMB.toFixed(1), audN: window.__aud.n, audTop: window.__aud.list.slice().sort((x, y) => y[0] - x[0]).slice(0, 8), total: +(cvMB + layMB + texMB + picMB + audMB).toFixed(0), cvMB: +cvMB.toFixed(1), cvN: cv.length, cvTop: cv.slice(0, 6), texMB: +texMB.toFixed(1), texN: window.__tex.live.size, gl: window.__tex.ctx, picMB: +picMB.toFixed(1), picTop: plist.slice(0, 8), layMB: +layMB.toFixed(1), layN: layers.length, layTop: layers.slice(0, 8), filt: filt.length, transform: getComputedStyle(app).transform.slice(0, 30), zoom: z, mob: document.documentElement.className };
  }, tag).catch(e => ({ tag, err: e.message.slice(0, 100) }));
  const out = [];
  const snap = async tag => { const r = await census(tag); out.push(r); console.log(`${r.tag}: TOTAL ${r.total} MB | canvases ${r.cvN} = ${r.cvMB} | textures ${r.texN} = ${r.texMB} (gl ${r.gl}) | pictures ${r.picMB} | layers ${r.layN} = ${r.layMB} | AUDIO ${r.audN} = ${r.audMB} | filters ${r.filt} | ${r.transform} zoom ${r.zoom} ${r.mob} ${r.err || ""}`); return r; };
  await p.waitForTimeout(8000); await snap("load");
  const vp = p.viewportSize();
  for (let i = 0; i < 3; i++) { await p.touchscreen.tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2500); }
  const bd = await snap("board");
  let peak = bd;
  if (process.env.SHOP) {
    for (let k = 0; k < 3; k++) {
      await p.evaluate(() => document.getElementById("bonusBtn").click());
      for (const t of [300, 900, 2500]) { await p.waitForTimeout(t === 300 ? 300 : t - 300); const r = await snap("shop" + k + "@" + t); if ((r.total || 0) > (peak.total || 0)) peak = r; }
      await p.evaluate(() => { const x = document.getElementById("bonusClose") || document.querySelector("#bonusWrap .bshopx"); if (x) x.click(); });
      await p.waitForTimeout(1500); await snap("closed" + k);
    }
  } else
  if (process.env.BUY) {
    await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(1800);
    const how = await p.evaluate(async i => { const w = ms => new Promise(r => setTimeout(r, ms)); const vis = sel => [...document.querySelectorAll(sel)].filter(b => b.getClientRects().length && !b.disabled); const go = vis("#bonusWrap button").filter(b => /^play/i.test(b.textContent.trim()))[i]; if (!go) return "no card"; go.click(); await w(900); const conf = vis("#bonusWrap button").find(b => /confirm/i.test(b.textContent)); if (conf) conf.click(); return "bought card " + i; }, +process.env.BUY);
    console.log(how);
    const t0 = Date.now(); let idle = 0, n = 0;
    while (Date.now() - t0 < 240000 && idle < 3 && !crashed) {
      await p.waitForTimeout(2200);
      await p.touchscreen.tap(vp.width / 2, vp.height * .5).catch(() => {});
      const playing = await p.evaluate(() => state.playing).catch(() => false);
      idle = playing ? 0 : idle + 1;
      const r = await census("b" + Math.round((Date.now() - t0) / 1000));
      const extra = await p.evaluate(() => ({ nodes: document.querySelectorAll("*").length, anims: document.getAnimations().length, fs: (document.querySelector(".fsplate, #fsLeft, .spinsleft") || {}).textContent || "" })).catch(() => ({}));
      if (n++ % 6 === 0 || (r.total || 0) > (peak.total || 0)) console.log(`${r.tag}: TOTAL ${r.total} | cv ${r.cvN}=${r.cvMB} | tex ${r.texN}=${r.texMB} | pics ${r.picMB} | layers ${r.layN}=${r.layMB} | nodes ${extra.nodes} anims ${extra.anims}`);
      if ((r.total || 0) > (peak.total || 0)) peak = r;
    }
    console.log("bonus ran", Math.round((Date.now() - t0) / 1000), "s");
  } else
  for (let i = 0; i < +spins && !crashed; i++) {
    await p.evaluate(() => { const s = document.getElementById("spinBtn"); if (s && !s.disabled) s.click(); }).catch(() => {});
    for (let k = 0; k < 5; k++) { await p.waitForTimeout(700); const r = await snap(`spin${i + 1}.${k}`); if ((r.total || 0) > (peak.total || 0)) peak = r; }
  }
  console.log("PEAK", peak.tag, peak.total, "MB");
  console.log("  audio (MB, seconds, file bytes):", JSON.stringify(peak.audTop));
  console.log("  canvases:", JSON.stringify(peak.cvTop)); console.log("  pictures:", JSON.stringify(peak.picTop)); console.log("  layers:", JSON.stringify(peak.layTop));
  console.log("errors", JSON.stringify(errs.slice(0, 5)), "crashed", crashed);
  require("fs").writeFileSync(process.env.OUT || "probe_out.json", JSON.stringify(out));
  await b.close();
})().catch(e => console.log("FAIL", e.message));
