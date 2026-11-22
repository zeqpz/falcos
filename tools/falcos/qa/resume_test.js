const pw = require(process.env.PLAYWRIGHT || "playwright");
(async () => {
  const b = await pw.webkit.launch(); const c = await b.newContext({ ...pw.devices["iPhone 12"] }); const p = await c.newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message.slice(0, 160)));
  const sid = "rs" + Date.now(), url = `http://localhost:8747/index.html?sessionID=${sid}&rgs_url=http://localhost:8747&lang=en&device=mobile`;
  const vp = { width: 390, height: 664 };
  const enter = async () => { await p.waitForTimeout(8000); for (let i = 0; i < 3; i++) { await p.touchscreen.tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2200); } };
  const st = () => p.evaluate(() => ({ card: !!document.getElementById("resumeWrap"), cardText: (document.getElementById("resumeWrap") || {}).innerText || "", playing: state.playing, balance: document.getElementById("balance").textContent, win: (document.getElementById("roundWin") || {}).textContent, notice: [...document.querySelectorAll(".notice, #notice, .toast")].map(e => e.textContent.trim()).filter(Boolean).join(" | "), total: !!document.querySelector(".totalwin:not([hidden]), .twamount") && [...document.querySelectorAll(".twamount")].map(e => e.textContent).join(""), open: !!(RGS.state.round && RGS.state.round.active) }));
  const buy = async () => { await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(1800);
    return p.evaluate(async () => { const w = ms => new Promise(r => setTimeout(r, ms)); const vis = sel => [...document.querySelectorAll(sel)].filter(b => b.getClientRects().length && !b.disabled); const go = vis("#bonusWrap button").filter(b => /^play/i.test(b.textContent.trim()))[1]; if (!go) return "no card"; go.click(); await w(900); const conf = vis("#bonusWrap button").find(b => /confirm/i.test(b.textContent)); if (conf) conf.click(); return go.textContent.trim() + (conf ? " + confirm" : ""); }); };
  await p.goto(url); await enter();
  console.log("bought:", await buy());
  await p.waitForTimeout(9000);
  console.log("mid-round before reload:", JSON.stringify(await st()));
  for (const pick of ["continue", "skip"]) {
    await p.reload(); await enter(); await p.waitForTimeout(1500);
    const s1 = await st(); console.log(`after reload (${pick}):`, JSON.stringify(s1));
    await p.screenshot({ path: `${__dirname}/resume_${pick}.png` });
    await p.evaluate(pick => document.getElementById(pick === "continue" ? "resumeGo" : "resumeSkip").click(), pick);
    await p.waitForTimeout(pick === "continue" ? 7000 : 2500);
    console.log(`  after ${pick}:`, JSON.stringify(await st()));
    if (pick === "continue") { await p.waitForTimeout(1000); }   // reload again mid-round for the skip case
  }
  await p.reload(); await enter(); await p.waitForTimeout(1500);
  console.log("final reload (nothing open):", JSON.stringify(await st()));
  console.log("errors", JSON.stringify(errs.slice(0, 5)));
  await b.close();
})().catch(e => console.log("FAIL", e.message));
