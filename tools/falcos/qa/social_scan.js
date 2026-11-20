// Social-mode (Stake.us) wording check:  node tools/falcos/qa/social_scan.js [--all]
// Every string the game passes through T() in frontend/index.html, the rules page (rules.js render) and the page's
// static text are converted with the social vocabulary and checked against Engine's restricted terms
// (RULES.restricted). Exit code 1 if any restricted word survives. --all prints every converted string, so the
// wording can be read for sense (the swap must keep each sentence's meaning).
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const FE = path.join(__dirname, "..", "..", "..", "frontend");
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(FE, "rules.js"), "utf8") + "\n;globalThis.RULES = RULES;", ctx);
const { RULES } = ctx;
const html = fs.readFileSync(path.join(FE, "index.html"), "utf8");
const all = process.argv.includes("--all");

const strings = new Set();
// T("..."), T('...'), T(`...`) - a template's ${...} stands in as a figure
const re = /\bT\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|`((?:[^`\\]|\\.)*)`)/g;
for (let m; (m = re.exec(html)); ) {
  let s = m[1] ?? m[2] ?? m[3];
  s = s.replace(/\$\{[^}]*\}/g, "1.00 SC").replace(/\\u00b7/g, "·").replace(/\\u00d7/g, "×").replace(/\\u2026/g, "…");
  strings.add(s);
}
// the static text of the page body (between tags), the way the walker in index.html sees it
const body = html.slice(html.indexOf("<body"), html.indexOf("<script", html.indexOf("<body")));
for (const t of body.replace(/<!--[\s\S]*?-->/g, "").split(/<[^>]+>/)) { const s = t.replace(/\s+/g, " ").trim(); if (/[a-z]/i.test(s)) strings.add(s); }
for (const m of body.matchAll(/(?:aria-label|title|alt)="([^"]+)"/g)) strings.add(m[1]);
// the rules page itself, in social mode
const rules = RULES.render({ bet: 1000000, fmt: v => (v / 1e6).toFixed(2) + " SC", social: true, modeCost: { base: 1, chance: 3, fillup: 100, premium: 300, nitro: 500, midnight: 500 } })
  .replace(/<[^>]+>/g, "\n").split("\n").map(s => s.trim()).filter(Boolean);

let bad = 0;
for (const s of strings) {
  const out = RULES.T(s, true);
  const left = RULES.restricted(out);
  if (left.length) { bad++; console.log(`RESTRICTED [${left.join(", ")}]: ${out}`); }
  else if (all && out !== s) console.log(`  ${s}\n  -> ${out}`);
}
for (const line of rules) {
  const left = RULES.restricted(line);
  if (left.length) { bad++; console.log(`RESTRICTED in rules [${left.join(", ")}]: ${line}`); }
  else if (all) console.log(`  rules: ${line}`);
}
console.log(bad ? `${bad} string(s) still carry a restricted word in social mode` : `social scan clean: ${strings.size} UI strings + ${rules.length} rules lines`);
process.exit(bad ? 1 : 0);
