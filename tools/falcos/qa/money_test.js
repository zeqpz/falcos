// Money formatting checks for frontend/rgs.js (no browser needed):  node tools/falcos/qa/money_test.js
// Loads rgs.js in a sandbox with a fake launch URL and checks the display rules reviewers test:
// exact sub-cent wins, the balance at the currency's usual decimals, Engine's symbols and placement,
// social coins never with a "$", and the XGC maxBet: 0 = "no cap" rule.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SRC = fs.readFileSync(path.join(__dirname, "..", "..", "..", "frontend", "rgs.js"), "utf8");
function load(search) {
  const ctx = { location: { search }, URLSearchParams, console, fetch: () => { throw new Error("no network"); }, setTimeout, BigInt, Math, Number, String };
  vm.createContext(ctx);
  vm.runInContext(SRC + "\n;globalThis.RGS = RGS;", ctx);
  return ctx.RGS;
}

let fails = 0, n = 0;
const eq = (got, want, what) => {
  n++;
  if (got !== want) { fails++; console.log(`FAIL ${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); }
};

const U = 1000000;
let R = load("?sessionID=t&rgs_url=x&currency=USD");
// wins: exact, the currency's 2 decimals at least
eq(R.money(1000), "$0.001", "0.1x of a 1-cent bet");
eq(R.money(1500), "$0.0015", "0.15x of a 1-cent bet");
eq(R.money(1250), "$0.00125", "0.125x of a 1-cent bet (5 dp)");
eq(R.money(1), "$0.000001", "one micro-unit");
eq(R.money(20000), "$0.02", "two cents");
eq(R.money(100000), "$0.10", "ten cents keeps 2 dp");
eq(R.money(1234567890), "$1,234.56789", "grouped, exact");
eq(R.money(0), "$0.00", "zero");
eq(R.money(5 * U), "$5.00", "a bet");
// count-ups: a fixed number of decimals
eq(R.money(1500, null, 4), "$0.0015", "fixed 4 dp");
eq(R.money(700, null, 4), "$0.0007", "fixed 4 dp mid-count");
eq(R.money(1499, null, 3), "$0.001", "fixed 3 dp rounds half up (down here)");
eq(R.money(1500, null, 3), "$0.002", "fixed 3 dp rounds half up");
// balance: always two decimals, rounded, in every currency
eq(R.moneyBalance(996200000), "$996.20", "balance 2 dp");
eq(R.moneyBalance(996204999), "$996.20", "balance rounds down under half a cent");
eq(R.moneyBalance(996205000), "$996.21", "balance rounds up from half a cent");
eq(R.moneyBalance(10000000000 * U, "ARS"), "10,000,000,000.00 ARS", "huge ARS balance");
eq(R.exactDp(1500), 4, "exactDp sub-cent");
eq(R.exactDp(5 * U), 2, "exactDp whole");
// Engine's table: symbols, decimals, placement
eq(R.money(10 * U, "JPY"), "¥10", "JPY 0 dp");
eq(R.money(200000, "JPY"), "¥0.2", "JPY sub-yen win is exact");
eq(R.moneyBalance(996200000, "JPY"), "¥996.20", "JPY balance 2 dp");
eq(R.moneyBalance(995000000, "JPY"), "¥995.00", "JPY whole balance still 2 dp");
eq(R.money(10 * U, "EUR"), "€10.00", "EUR");
eq(R.money(10 * U, "CAD"), "CA$10.00", "CAD");
eq(R.money(10 * U, "MXN"), "MX$10.00", "MXN");
eq(R.money(10 * U, "DKK"), "10.00 kr", "DKK after, lower-case kr");
eq(R.money(10 * U, "PEN"), "S/10.00", "PEN before");
eq(R.money(10 * U, "USDT"), "10.00 USDT", "USDT");
eq(R.money(10 * U, "BTC"), "10.000000 BTC", "BTC 6 dp");
eq(R.money(10 * U, "KWD"), "KD10.000", "KWD 3 dp");
eq(R.money(10 * U, "DOGE"), "10.0000 DOGE", "DOGE 4 dp");
eq(R.money(10 * U, "XYZ"), "10.00 XYZ", "unknown code: 2 dp, code after");
eq(R.money(-2500000), "-$2.50", "negative");
// social coins: never a $
eq(R.money(10 * U, "XSC"), "10.00 SC", "SC");
eq(R.money(10 * U, "XGC"), "10.00 GC", "GC");
eq(R.money(1000, "XSC"), "0.001 SC", "SC sub-cent");
eq(R.currencyName("XGC"), "GC", "GC label");
eq(R.currencyName("XRC"), "SC", "XRC label");
eq(R.social, false, "USD launch is not social");

R = load("?sessionID=t&rgs_url=x&currency=XGC");
eq(R.social, true, "an XGC launch is social even without social=true");
eq(R.money(10 * U), "10.00 GC", "GC before authenticate (the launch param)");
R = load("?sessionID=t&rgs_url=x&social=true&currency=USD");
eq(R.money(10 * U, "USD"), "10.00 USD", "social mode never shows $");

// XGC: every mode's maxBet is 0 = no per-mode cap
R = load("?sessionID=t&rgs_url=x&currency=XGC");
R.state.config = { maxBet: 1000 * U, gameModes: [{ mode: "base", costMultiplier: 1, maxBet: 0 }, { mode: "fillup", costMultiplier: 100, maxBet: 50 * U }] };
eq(R.modeMaxBet("base"), null, "maxBet 0 is no cap");
eq(R.modeMaxBet("fillup"), 50 * U, "a real per-mode cap stays");

// replay params
R = load("?replay=true&game=g&version=1&mode=base&event=5&amount=abc&currency=usd&lang=de");
const p = R.replayParams();
eq(p.amount, 0, "junk amount -> 0 (the game uses 1.00)");
eq(p.currency, "USD", "currency upper-cased");
eq(p.lang, "de", "lang passed through");

console.log(fails ? `${fails} of ${n} checks FAILED` : `all ${n} money checks pass`);
process.exit(fails ? 1 : 0);
