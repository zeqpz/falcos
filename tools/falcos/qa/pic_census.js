// Every picture the page FETCHED on a phone profile (not only the ones on screen) and what each costs decoded
// (width x height x 4), by step: load, board, spins, the Buy Bonus menu. A fetched picture held by script or drawn to
// a canvas / texture is decoded whether or not an element shows it.
//   PLAYWRIGHT=<path> node pic_census.js [base] [extra query]
const pw = require(process.env.PLAYWRIGHT || "playwright");
const [base = "http://localhost:8747", extra = ""] = process.argv.slice(2);
const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1";
(async () => {
  const b = await pw.chromium.launch();
  const c = await b.newContext(process.env.DESKTOP ? { viewport: { width: 1440, height: 810 } } : { viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA });
  const p = await c.newPage();
  const seen = new Map();   // url -> { bytes, step }
  let step = "load";
  p.on("response", r => { const u = r.url(); if (/\.(webp|png|jpe?g|avif|gif|svg)(\?|$)/i.test(u) && !seen.has(u)) seen.set(u, { step }); });
  await p.goto(`${base}/index.html?sessionID=c${Date.now()}&rgs_url=${base}&lang=en${process.env.DESKTOP ? "" : "&device=mobile"}${extra}`);
  const vp = p.viewportSize();
  await p.waitForTimeout(9000);
  step = "board"; for (let i = 0; i < 3; i++) { await p.touchscreen.tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2500); }
  step = "spins"; for (let i = 0; i < 4; i++) { await p.evaluate(() => { const s = document.getElementById("spinBtn"); if (s && !s.disabled) s.click(); }); await p.waitForTimeout(5500); }
  step = "menu"; await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(3000);
  if (process.env.BUY) {   // a bought bonus played to its end: what is still on the page afterwards
    step = "bonus";
    await p.evaluate(async i => { const w = ms => new Promise(r => setTimeout(r, ms)); const vis = sel => [...document.querySelectorAll(sel)].filter(b => b.getClientRects().length && !b.disabled); const go = vis("#bonusWrap button").filter(b => /^play/i.test(b.textContent.trim()))[i]; if (!go) return; go.click(); await w(900); const conf = vis("#bonusWrap button").find(b => /confirm/i.test(b.textContent)); if (conf) conf.click(); }, +process.env.BUY);
    const tb = Date.now(); let idle = 0;
    while (Date.now() - tb < 240000 && idle < 3) { await p.waitForTimeout(2000); await p.touchscreen.tap(vp.width / 2, vp.height * .5).catch(() => {}); idle = (await p.evaluate(() => state.playing).catch(() => false)) ? 0 : idle + 1; }
    await p.waitForTimeout(3000);
  }
  const urls = [...seen.keys()];
  const sizes = await p.evaluate(async urls => { const o = {}; for (const u of urls) o[u] = await new Promise(res => { const i = new Image(); i.onload = () => res([i.naturalWidth, i.naturalHeight]); i.onerror = () => res([0, 0]); i.src = u; }); return o; }, urls);
  const shown = await p.evaluate(() => { const s = new Set(); for (const el of document.querySelectorAll("*")) { if (!el.getClientRects().length) continue; const cs = getComputedStyle(el); if (el.tagName === "IMG" && el.currentSrc) s.add(el.currentSrc); for (const pe of [null, "::before", "::after"]) { const st = pe ? getComputedStyle(el, pe) : cs; for (const m of String(st.backgroundImage + " " + (st.maskImage || st.webkitMaskImage || "") + " " + (st.borderImageSource || "")).matchAll(/url\("?([^")]+)"?\)/g)) s.add(new URL(m[1], location.href).href); } } return [...s]; });
  const rows = urls.map(u => { const [w, h] = sizes[u]; return { mb: w * h * 4 / 1e6, w, h, u: u.split("/assets/")[1] || u.slice(-40), step: seen.get(u).step, on: shown.includes(u) }; }).sort((a, b) => b.mb - a.mb);
  const by = {}; for (const r of rows) by[r.step] = (by[r.step] || 0) + r.mb;
  console.log(`${rows.length} pictures fetched, ${rows.reduce((s, r) => s + r.mb, 0).toFixed(0)} MB if all decoded; on the page at the end: ${rows.filter(r => r.on).reduce((s, r) => s + r.mb, 0).toFixed(0)} MB`);
  console.log("fetched during:", Object.entries(by).map(([k, v]) => `${k} ${v.toFixed(0)} MB`).join(" | "));
  for (const r of rows.slice(0, +(process.env.TOP || 45))) console.log(`  ${r.mb.toFixed(1).padStart(6)} MB ${String(r.w).padStart(5)} x ${String(r.h).padEnd(5)} ${r.step.padEnd(6)} ${r.on ? "ON " : "   "} ${r.u}`);
  require("fs").writeFileSync(process.env.OUT || "pic_census_out.json", JSON.stringify(rows));
  await b.close();
})().catch(e => { console.log("FAIL", e.stack || e.message); process.exit(1); });
