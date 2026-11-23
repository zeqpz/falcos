// The burst canvas on a phone (bug, 2026-11-22: pieces of the last burst stayed drawn along the board's right and
// bottom edges - the canvas was wiped under its drawing scale, which is under 1 on a phone). Spins until tiles have
// burst: pieces are drawn while they fly, and once the round is over nothing is left on the canvas (it is let go).
//   PLAYWRIGHT=<path> node burst_canvas_test.js [base]
const pw = require(process.env.PLAYWRIGHT || "playwright");
const [base = "http://localhost:8747"] = process.argv.slice(2);
const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1";
(async () => {
  const b = await pw.chromium.launch();
  const c = await b.newContext({ viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA });
  const p = await c.newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message.slice(0, 160)));
  await p.goto(`${base}/index.html?sessionID=bc${Date.now()}&rgs_url=${base}&lang=en&device=mobile`);
  await p.waitForTimeout(8000);
  const vp = p.viewportSize();
  for (let i = 0; i < 3; i++) { await p.touchscreen.tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2200); }
  const ink = () => p.evaluate(() => { const cv = document.querySelector(".shardlayer"); if (!cv || !cv.width || !cv.height) return { w: cv ? cv.width : -1, inked: 0, edge: 0 }; const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data; let n = 0, edge = 0; const x1 = Math.floor(cv.width * .86), y1 = Math.floor(cv.height * .86); for (let y = 0; y < cv.height; y++) for (let x = 0; x < cv.width; x++) if (d[(y * cv.width + x) * 4 + 3] > 8) { n++; if (x >= x1 || y >= y1) edge++; } return { w: cv.width, inked: n, edge, scale: +(cv.width / parseFloat(cv.style.width)).toFixed(3) }; });
  let flew = 0, scale = 0, rounds = 0, left = null;
  for (let i = 0; i < 25 && rounds < 3; i++) {
    await p.evaluate(() => { const s = document.getElementById("spinBtn"); if (s && !s.disabled) s.click(); });
    let peak = 0;
    for (let k = 0; k < 40; k++) { await p.waitForTimeout(150); const r = await ink(); if (r.inked > peak) { peak = r.inked; scale = r.scale || scale; } if (k > 6 && !(await p.evaluate(() => state.playing))) break; }
    await p.waitForTimeout(2500);
    if (peak > 500) { rounds++; flew = Math.max(flew, peak); left = await ink(); if (left.inked) break; }
  }
  let fails = 0;
  const ok = (cond, what, got) => { console.log((cond ? "PASS " : "FAIL ") + what + "  [" + got + "]"); if (!cond) fails++; };
  ok(rounds > 0 && flew > 500, "tiles burst and their pieces were drawn", `${rounds} rounds, up to ${flew} px inked, canvas scale ${scale}`);
  ok(left && left.inked === 0, "nothing is left on the canvas once the round is over", left ? `${left.inked} px, ${left.edge} of them along the right/bottom edge` : "no burst seen");
  ok(left && left.w === 0, "and the canvas is let go between bursts", left ? left.w + " px wide" : "-");
  ok(!errs.length, "no page errors", errs.join(" | "));
  console.log(fails ? `\n${fails} FAILED` : "\nall passed");
  await b.close(); process.exit(fails ? 1 : 0);
})().catch(e => { console.log("FAIL", e.stack || e.message); process.exit(1); });
