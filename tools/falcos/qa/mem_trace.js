// Falcos on a phone profile: what the browser's own processes really hold, not a model. Chromium's memory-infra dumps
// (the allocator breakdown behind chrome://tracing: script heap, decoded pictures, GPU textures, compositor tiles,
// array buffers = decoded sound, ...) for the page's renderer and the GPU process, taken at each step, and the OS's
// private bytes for both sampled the whole way through (the transient peaks a dump between steps would miss).
//   PLAYWRIGHT=<path> node mem_trace.js [base] [steps: board,spin,shop,buy] [extra query]
//   env: DESKTOP=1 (a desktop profile, for comparison), BUY=<card index>, BUYSEL=<the buy buttons' selector, a sister game's>, OUT=<json>
const pw = require(process.env.PLAYWRIGHT || "playwright");
const { execFile } = require("child_process");
const [base = "http://localhost:8747", stepsArg = "board,spin,shop,buy", extra = ""] = process.argv.slice(2);
const steps = stepsArg.split(",");
const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1";
const hex = v => (typeof v === "string" ? parseInt(v, 16) : +v) || 0;
(async () => {
  const b = await pw.chromium.launch({ args: ["--enable-gpu-rasterization", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"] });
  const c = await b.newContext(process.env.DESKTOP ? { viewport: { width: 1440, height: 810 } } : { viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA });
  const p = await c.newPage();
  let crashed = false; const errs = [];
  p.on("crash", () => { crashed = true; console.log("*** CRASH"); });
  p.on("pageerror", e => errs.push(e.message.slice(0, 160)));
  const bs = await b.newBrowserCDPSession();
  await p.goto(`${base}/index.html?sessionID=m${Date.now()}&rgs_url=${base}&lang=en${process.env.DESKTOP ? "" : "&device=mobile"}${extra}`);
  // the processes: this page's renderer (the newest one) and the GPU process
  const info = (await bs.send("SystemInfo.getProcessInfo")).processInfo;
  const gpuPid = (info.find(x => x.type === "GPU") || {}).id;
  const rends = info.filter(x => x.type === "renderer").map(x => x.id);
  // --- OS private bytes, sampled every ~250 ms in one long-lived PowerShell ---
  const samples = [];   // [t, rendererMB, gpuMB]
  const t0 = Date.now();
  let mark = "load"; const marks = [];
  const ps = execFile("powershell", ["-NoProfile", "-Command",
    `$ids = @(${[...rends, gpuPid].filter(Boolean).join(",")}); while ($true) { $o = @(); foreach ($i in $ids) { try { $p = Get-Process -Id $i -ErrorAction Stop; $o += "$($i):$($p.PrivateMemorySize64)" } catch {} }; [Console]::Out.WriteLine(($o -join ' ')); Start-Sleep -Milliseconds 220 }`], { maxBuffer: 1 << 26 });
  ps.stdout.on("data", d => { for (const line of String(d).split(/\r?\n/)) { if (!line.trim()) continue; const m = {}; for (const kv of line.trim().split(" ")) { const [k, v] = kv.split(":"); m[k] = +v / 1e6; } const r = Math.max(0, ...rends.map(id => m[id] || 0)); samples.push([Date.now() - t0, r, m[gpuPid] || 0, mark]); } });
  // --- memory-infra dumps ---
  const dump = async tag => {
    mark = tag; marks.push([Date.now() - t0, tag]);
    const events = [];
    const on = e => events.push(...e.value);
    bs.on("Tracing.dataCollected", on);
    const done = new Promise(r => bs.once("Tracing.tracingComplete", r));
    await bs.send("Tracing.start", { transferMode: "ReportEvents", traceConfig: { includedCategories: ["disabled-by-default-memory-infra"], excludedCategories: ["*"], memoryDumpConfig: { triggers: [] } } });
    await bs.send("Tracing.requestMemoryDump", { levelOfDetail: "detailed" }).catch(e => console.log("dump:", e.message));
    await bs.send("Tracing.end"); await done; bs.off("Tracing.dataCollected", on);
    const byPid = {};
    for (const e of events) {
      if (e.ph !== "v" || !e.args || !e.args.dumps) continue;
      const P = byPid[e.pid] || (byPid[e.pid] = { alloc: {}, total: 0 });
      const d = e.args.dumps;
      if (d.process_totals && d.process_totals.private_footprint_bytes) P.total = hex(d.process_totals.private_footprint_bytes);
      for (const [name, a] of Object.entries(d.allocators || {})) { const s = a.attrs && (a.attrs.size || a.attrs.effective_size); if (s) P.alloc[name] = Math.max(P.alloc[name] || 0, hex(s.value)); }
      for (const [name, a] of Object.entries(d.allocators || {})) { const o = a.attrs && a.attrs.object_count; if (o && /^blink_objects/.test(name)) (P.objs || (P.objs = {}))[name.replace("blink_objects/", "")] = hex(o.value); }
    }
    const heap = await p.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : 0).catch(() => 0);
    const game = await p.evaluate(() => { let a = 0; const seen = new Set(); try { for (const x of Object.values(sfxBuf)) if (x && !seen.has(x)) { seen.add(x); a += x.length * x.numberOfChannels * 4; } } catch (e) {} return { sfxMB: +(a / 1e6).toFixed(1), nodes: document.querySelectorAll("*").length, anims: document.getAnimations().filter(x => x.playState === "running").length, imgs: document.images.length, cvs: document.querySelectorAll("canvas").length }; }).catch(() => ({}));
    const last = samples[samples.length - 1] || [0, 0, 0];
    const pick = (pid, keys) => { const A = (byPid[pid] || {}).alloc || {}; const o = {}; for (const k of keys) { let s = 0; for (const [n, v] of Object.entries(A)) if (n === k) s = v; o[k] = +(s / 1e6).toFixed(1); } return o; };
    const rpid = rends.find(id => byPid[id]) || rends[rends.length - 1];
    const R = (byPid[rpid] || {}).alloc || {}, G = (byPid[gpuPid] || {}).alloc || {};
    const top = (A, depth, n) => Object.entries(A).filter(([k]) => k.split("/").length <= depth && !/^(tracing|global)/.test(k)).sort((x, y) => y[1] - x[1]).slice(0, n).map(([k, v]) => `${k} ${(v / 1e6).toFixed(1)}`);
    const row = { tag, t: Date.now() - t0, osRenderer: +last[1].toFixed(0), osGpu: +last[2].toFixed(0), footR: +(((byPid[rpid] || {}).total || 0) / 1e6).toFixed(0), footG: +(((byPid[gpuPid] || {}).total || 0) / 1e6).toFixed(0), jsHeap: +(heap / 1e6).toFixed(1), game, rTop: top(R, 2, 16), gTop: top(G, 2, 8),
      detail: Object.fromEntries(Object.entries(R).filter(([k, v]) => v > 4e5 && /^(blink|canvas|skia|font|v8|web_cache|cc|discardable|malloc$|partition_alloc\/partitions\/[a-z_]+$|media|gpu|sync)/.test(k)).map(([k, v]) => [k, +(v / 1e6).toFixed(1)])),
      objects: Object.fromEntries(Object.entries((byPid[rpid] || {}).objs || {}).filter(([k, v]) => v > 20)) };
    console.log(`\n== ${tag}: renderer ${row.osRenderer} MB + GPU ${row.osGpu} MB = ${row.osRenderer + row.osGpu} MB private (OS)  | script heap ${row.jsHeap} | sfx held ${game.sfxMB} | nodes ${game.nodes} anims ${game.anims}`);
    console.log("   renderer:", row.rTop.join(" | "));
    console.log("   gpu:     ", row.gTop.join(" | "));
    return row;
  };
  const out = [];
  const vp = p.viewportSize();
  const tap = (x, y) => process.env.DESKTOP ? p.mouse.click(x, y) : p.touchscreen.tap(x, y);
  await p.waitForTimeout(9000); out.push(await dump("loaded (before any touch)"));
  for (let i = 0; i < 3; i++) { await tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2500); }
  await p.waitForTimeout(5000);
  if (steps.includes("board")) out.push(await dump("board (sound decoded)"));
  if (steps.includes("spin")) {
    for (let i = 0; i < +(process.env.SPINS || 4); i++) { await p.evaluate(() => { const s = document.getElementById("spinBtn"); if (s && !s.disabled) s.click(); }); await p.waitForTimeout(5500); }
    out.push(await dump("after spins"));
  }
  if (steps.includes("shop")) {
    mark = "menu opening";
    await p.evaluate(() => document.getElementById("bonusBtn").click());
    await p.waitForTimeout(3500); out.push(await dump("Buy Bonus menu open"));
    for (let k = 0; k < 4; k++) { await p.evaluate(() => document.getElementById("bonusClose").click()); await p.waitForTimeout(1400); await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(1600); }
    out.push(await dump("menu opened 5 times"));
  }
  if (steps.includes("buy")) {
    if (!steps.includes("shop")) { await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(1500); }
    mark = "bonus";
    const how = await p.evaluate(async ([i, sel]) => { const w = ms => new Promise(r => setTimeout(r, ms)); const vis = sel => [...document.querySelectorAll(sel)].filter(b => b.getClientRects().length && !b.disabled); const go = sel ? vis(sel)[i] : vis("#bonusWrap button").filter(b => /^play/i.test(b.textContent.trim()))[i]; if (!go) return "no card"; go.click(); await w(900); const conf = vis("button").filter(b => /confirm|yes|buy/i.test(b.textContent) && b.closest("#bonusWrap, #autoPop, .confirm, [role=dialog], [role=alertdialog]")).pop(); if (conf) conf.click(); return "bought card " + i + (conf ? "" : " (no confirm)"); }, [+(process.env.BUY || 2), process.env.BUYSEL || ""]);
    console.log("\n" + how);
    const tb = Date.now(); let idle = 0, n = 0;
    while (Date.now() - tb < 240000 && idle < 3 && !crashed) {
      await p.waitForTimeout(2000);
      await tap(vp.width / 2, vp.height * .5).catch(() => {});
      const playing = await p.evaluate(() => state.playing).catch(() => false);
      idle = playing ? 0 : idle + 1;
      if (++n === 6 || n === 20) out.push(await dump("in the bonus, " + Math.round((Date.now() - tb) / 1000) + " s")), (mark = "bonus");
    }
    out.push(await dump("after the bonus"));
    // what a collection gives back: the rest is held, not garbage
    const ps2 = await c.newCDPSession(p);
    await ps2.send("HeapProfiler.collectGarbage").catch(() => {}); await p.waitForTimeout(2500); await ps2.send("HeapProfiler.collectGarbage").catch(() => {}); await p.waitForTimeout(1500);
    out.push(await dump("after the bonus, collected"));
    if (process.env.BUY2) {   // a second bonus: does it climb again?
      mark = "bonus 2";
      await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(1500);
      await p.evaluate(async i => { const w = ms => new Promise(r => setTimeout(r, ms)); const vis = sel => [...document.querySelectorAll(sel)].filter(b => b.getClientRects().length && !b.disabled); const go = vis("#bonusWrap button").filter(b => /^play/i.test(b.textContent.trim()))[i]; if (!go) return; go.click(); await w(900); const conf = vis("#bonusWrap button").find(b => /confirm/i.test(b.textContent)); if (conf) conf.click(); }, +process.env.BUY2);
      const tb2 = Date.now(); let idle2 = 0;
      while (Date.now() - tb2 < 240000 && idle2 < 3 && !crashed) { await p.waitForTimeout(2000); await tap(vp.width / 2, vp.height * .5).catch(() => {}); idle2 = (await p.evaluate(() => state.playing).catch(() => false)) ? 0 : idle2 + 1; }
      out.push(await dump("after bonus 2"));
      await ps2.send("HeapProfiler.collectGarbage").catch(() => {}); await p.waitForTimeout(2500);
      out.push(await dump("after bonus 2, collected"));
    }
  }
  await p.waitForTimeout(600);
  ps.kill();
  // the sampled peaks, by step
  const peaks = {};
  for (const [t, r, g, m] of samples) { const s = r + g; if (!peaks[m] || s > peaks[m][0]) peaks[m] = [+s.toFixed(0), +r.toFixed(0), +g.toFixed(0), t]; }
  console.log("\n== OS private bytes, highest sample during each step (renderer + GPU):");
  for (const [m, v] of Object.entries(peaks)) console.log(`   ${String(v[0]).padStart(5)} MB  (renderer ${v[1]}, GPU ${v[2]})  ${m}`);
  const all = samples.map(s => s[1] + s[2]); console.log(`   overall peak ${Math.max(...all).toFixed(0)} MB over ${samples.length} samples`);
  console.log("errors", JSON.stringify(errs.slice(0, 5)), "crashed", crashed);
  require("fs").writeFileSync(process.env.OUT || "mem_trace_out.json", JSON.stringify({ out, peaks, samples }));
  await b.close();
})().catch(e => { console.log("FAIL", e.stack || e.message); process.exit(1); });
