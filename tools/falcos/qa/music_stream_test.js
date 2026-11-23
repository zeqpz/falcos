// Phones stream the music (one <audio> element) and never decode a cue: checked on a phone profile in Chromium.
// The cue follows the game (base -> the Buy Bonus menu -> base again, picking up where it left off), the element is
// playing and its time moves, no cue is ever handed to decodeAudioData, and every effect ends up decoded in mono.
//   PLAYWRIGHT=<path> node music_stream_test.js [base]
//   env: Q='&musicaac=1' CHANNEL=msedge - the AAC copies (Playwright's own Chromium has no AAC decoder: use Edge or Chrome)
const pw = require(process.env.PLAYWRIGHT || "playwright");
const [base = "http://localhost:8747"] = process.argv.slice(2);
const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1";
let fails = 0;
const ok = (c, what, got) => { console.log((c ? "PASS " : "FAIL ") + what + (got !== undefined ? "  [" + got + "]" : "")); if (!c) fails++; };
(async () => {
  const b = await pw.chromium.launch({ channel: process.env.CHANNEL || undefined, args: ["--autoplay-policy=user-gesture-required"] });
  const c = await b.newContext({ viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA });
  await c.addInitScript(() => {
    window.__dec = [];
    for (const C of [window.AudioContext, window.webkitAudioContext]) {
      if (!C || C.prototype.__h) continue; C.prototype.__h = true;
      const d = C.prototype.decodeAudioData;
      C.prototype.decodeAudioData = function (buf, ...r) { window.__dec.push(buf ? buf.byteLength : 0); return d.call(this, buf, ...r); };
    }
    window.__octx = 0;
    const O = window.OfflineAudioContext; if (O) window.OfflineAudioContext = function (...a) { window.__octx++; return new O(...a); };
  });
  const p = await c.newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message.slice(0, 160)));
  await p.goto(`${base}/index.html?sessionID=s${Date.now()}&rgs_url=${base}&lang=en&device=mobile${process.env.Q || ""}`);
  await p.waitForTimeout(8000);
  const vp = p.viewportSize();
  for (let i = 0; i < 3; i++) { await p.touchscreen.tap(vp.width / 2, vp.height * .62); await p.waitForTimeout(2200); }
  const st = () => p.evaluate(() => ({ stream: !!stream.el, name: stream.name, paused: stream.el && stream.el.paused, t: stream.el ? +stream.el.currentTime.toFixed(2) : -1, src: stream.el ? stream.el.src.split("/").pop() : "", gain: stream.g ? +stream.g.gain.value.toFixed(3) : -1, rate: actx ? actx.sampleRate : 0, tracks: Object.keys(musicTrack).length, playing: Object.keys(music.playing).length, raw: Object.keys(musicRaw).length }));
  await p.waitForTimeout(3000);
  const a = await st();
  ok(a.stream, "the music runs through one <audio> element");
  ok(a.name === "base" && /music_base\./.test(a.src), "the base loop is the cue", a.name + " " + a.src);
  ok(!a.paused && a.t > .5, "it is playing", "t=" + a.t + " paused=" + a.paused);
  ok(a.gain > .05, "and audible on the music bus", a.gain);
  ok(a.rate === 32000, "the phone's context runs at 32 kHz", a.rate);
  ok(a.tracks === 0 && a.playing === 0 && a.raw === 0, "no cue fetched as bytes, decoded or held", `${a.raw}/${a.tracks}/${a.playing}`);
  await p.waitForTimeout(1500);
  const a2 = await st(); ok(a2.t > a.t, "its time moves", a.t + " -> " + a2.t);
  await p.evaluate(() => document.getElementById("bonusBtn").click()); await p.waitForTimeout(2500);
  const m = await st();
  ok(m.name === "menu" && /music_menu\./.test(m.src) && !m.paused && m.t > .3, "the Buy Bonus menu plays its own loop, streamed", `${m.name} t=${m.t}`);
  ok(m.tracks === 0, "opening the menu decodes no music", m.tracks);
  await p.evaluate(() => document.getElementById("bonusClose").click()); await p.waitForTimeout(2500);
  const z = await st();
  ok(z.name === "base" && !z.paused, "closing it brings the base loop back", z.name);
  // (a raw .aac stream cannot be sought into: under ?musicaac=1 the loop starts from its top again)
  if (!/musicaac=1/.test(process.env.Q || "")) ok(z.t > a2.t - .5, "from where it left off", `left at ~${a2.t}, back at ${z.t}`);
  else ok(z.t > .3, "playing again (AAC: from its top)", z.t);
  ok(await p.evaluate(() => document.getElementById("bonusWrap").hidden && !document.getElementById("bonusWrap").classList.contains("leaving")), "the menu cuts out (no exit animation on a phone)");
  // every effect decoded, in mono, one decode per file
  await p.waitForFunction(() => { const u = new Set(Object.values(SFX)); return new Set(Object.values(sfxBuf)).size >= u.size - 2; }, null, { timeout: 60000 }).catch(() => {});
  const s = await p.evaluate(() => { const bufs = new Set(Object.values(sfxBuf)); let mb = 0, stereo = 0; for (const x of bufs) { mb += x.length * x.numberOfChannels * 4 / 1e6; if (x.numberOfChannels > 1) stereo++; } return { files: new Set(Object.values(SFX)).size, bufs: bufs.size, names: Object.keys(sfxBuf).length, all: Object.keys(SFX).length, mb: +mb.toFixed(1), stereo, dec: window.__dec.length, big: Math.max(0, ...window.__dec), octx: window.__octx, raw: Object.keys(sfxRaw).length }; });
  ok(s.names === s.all, "every effect is decoded", `${s.names}/${s.all} names, ${s.bufs}/${s.files} files`);
  ok(s.stereo === 0, "all in mono", s.stereo + " stereo");
  ok(s.mb < 20, "held effects under 20 MB", s.mb + " MB");
  ok(s.big < 400000, "nothing as big as a music cue was ever decoded", "largest file decoded " + s.big + " bytes");
  ok(s.octx === 0, "no second audio context was made", s.octx);
  ok(s.raw === 0, "the effects' file bytes were let go", s.raw);
  ok(!errs.length, "no page errors", errs.join(" | "));
  console.log(fails ? `\n${fails} FAILED` : "\nall passed");
  await b.close(); process.exit(fails ? 1 : 0);
})().catch(e => { console.log("FAIL", e.stack || e.message); process.exit(1); });
