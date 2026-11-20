/* Stake Engine RGS client.
 *
 * The game is served from
 *   https://{team}.cdn.stake-engine.com/{gameID}/{version}/index.html
 *       ?sessionID=..&lang=..&device=..&rgs_url=..
 * so every connection detail arrives in the query string. rgs_url is explicitly
 * documented as "should not be hardcoded, as it may change dynamically" — it is read
 * from the URL on every load and never baked into the bundle.
 *
 * Money is an integer with six decimal places: 1_000_000 == 1.00 of the currency.
 * Keep it in integers everywhere and only divide at the display layer, or rounding
 * drift shows up in the balance.
 */
const RGS = (() => {
  const UNIT = 1000000;

  // Engine's currency table (studio.engine.io/docs/rgs "Supported currencies", read 2026-11-19): symbol,
  // the currency's usual decimals, and whether the symbol goes after the amount. A code that is not here
  // (the RGS may send new ones) shows 2 decimals with the code after the amount.
  const CURRENCY = {};
  for (const [codes, symbol, decimals, after] of [
    ["USD", "$", 2], ["CAD", "CA$", 2], ["JPY", "¥", 0], ["EUR", "€", 2], ["RUB", "₽", 2], ["CNY", "CN¥", 2],
    ["PHP", "₱", 2], ["INR", "₹", 2], ["IDR", "Rp", 0], ["KRW", "₩", 0], ["BRL", "R$", 2], ["MXN", "MX$", 2],
    ["DKK NOK", "kr", 2, 1], ["PLN", "zł", 2, 1], ["VND", "₫", 0, 1], ["TRY", "₺", 2], ["CLP", "CLP", 0, 1],
    ["ARS", "ARS", 2, 1], ["PEN", "S/", 2], ["NGN", "₦", 2], ["SAR", "SAR", 2, 1], ["ILS", "₪", 2],
    ["AED", "AED", 2, 1], ["TWD", "NT$", 2], ["KWD", "KD", 3], ["JOD", "JD", 3], ["CRC", "₡", 2],
    ["TND", "TND", 3, 1], ["SGD", "SG$", 2], ["MYR", "RM", 2], ["OMR", "OMR", 3, 1], ["QAR", "QAR", 2, 1],
    ["BHD", "BD", 3], ["PKR", "₨", 2], ["EGP", "EGP", 2, 1], ["NZD", "NZ$", 2], ["BOB", "Bs", 2], ["GHS", "GH₵", 2],
    ["KES", "KSh", 2], ["MAD", "MAD", 2, 1], ["BAM", "KM", 2], ["ISK", "kr", 0, 1], ["TZS", "TSh", 2],
    ["UGX", "USh", 0], ["XOF", "CFA", 0, 1], ["AUD", "A$", 2], ["BWP", "P", 2], ["GEL", "₾", 2], ["HNL", "L", 2],
    ["JMD", "J$", 2], ["KGS", "KGS", 2, 1], ["MZN", "MZN", 2, 1], ["PGK", "K", 2], ["TMT", "TMT", 2, 1],
    ["TTD", "TT$", 2], ["UAH", "₴", 2], ["XCD", "EC$", 2],
    // crypto: the code after the amount, at the coin's own decimals
    ["APE CRO DOGE EOS LINK POL SAND TRUMP TRX UNI XRP", null, 4, 1], ["BCH BNB BTC ETH LTC SOL", null, 6, 1],
    ["BUSD DAI USDC USDT", null, 2, 1], ["SHIB", null, 0, 1],
    // the social-casino coins read "10.00 SC" / "10.00 GC" - never with a $ in front
    ["XGC", "GC", 2, 1], ["XSC XEC XRC WRW", "SC", 2, 1],
  ]) for (const code of codes.split(" ")) CURRENCY[code] = { symbol: symbol || code, decimals, after: !!after };
  const CURRENCY_SOCIAL = new Set(["XGC", "XSC", "XEC", "XRC", "WRW"]);
  const metaOf = code => CURRENCY[code] || { symbol: code || "", decimals: 2, after: true };
  // thousands grouped: 1,000,000.00 - the integer part only
  const group = s => s.replace(/^(\d+)/, d => d.replace(/\B(?=(\d{3})+(?!\d))/g, ","));
  // Money is formatted from the integer itself, never through a float: 0.0015 stays 0.0015 (toFixed on a
  // double can turn it into 0.0014), and a VND balance past 2^53 keeps its last digits as the RGS sent them.
  const big = a => { try { return BigInt(typeof a === "bigint" ? a : Math.round(Number(a) || 0)); } catch (e) { return 0n; } };
  const P10 = n => 10n ** BigInt(n);
  // amount (6dp integer) as text with exactly dp decimals, rounded half up (away from zero)
  function digits(amount, dp) {
    let n = big(amount);
    const neg = n < 0n;
    if (neg) n = -n;
    dp = Math.max(0, Math.min(6, dp | 0));
    const unit = P10(6 - dp);
    const q = dp < 6 ? (n + unit / 2n) / unit : n;
    const s = q.toString().padStart(dp + 1, "0");
    const out = dp ? s.slice(0, -dp) + "." + s.slice(-dp) : s;
    return (neg && q > 0n ? "-" : "") + out;
  }
  // the fewest decimals (at least min) that show the amount exactly - 6 at most, the RGS's own precision
  function exactDp(amount, min) {
    const n = big(amount) < 0n ? -big(amount) : big(amount);
    let dp = Math.max(0, min | 0);
    while (dp < 6 && n % P10(6 - dp) !== 0n) dp++;
    return dp;
  }
  // The display layer's only money formatter.
  //   how omitted  -> exact: the currency's usual decimals, more when the amount needs them (a 0.1x win on a
  //                   1-cent bet is 0.001) - wins, bets, prices, payouts
  //   "balance"    -> always two decimals, rounded, whatever the currency (Engine, 2026-11-20: JPY 995 -> 995.00)
  //   a number dp  -> exactly that many decimals (a count-up holds one width the whole way to its exact figure)
  function formatMoney(amount, currency, how) {
    const code = currency || state.currency;
    const meta = metaOf(code);
    const dp = typeof how === "number" ? Math.max(0, Math.min(6, how | 0))
             : how === "balance" ? 2   // (Engine, 2026-11-20) the balance: always two decimals, in every currency
             : exactDp(amount, meta.decimals);
    let s = digits(amount, dp);
    const neg = s[0] === "-";
    if (neg) s = s.slice(1);
    s = group(s);
    const sign = neg ? "-" : "";
    // social mode never shows a $ / € sign: a real-money code (a replay link without the coin, say) goes as a code
    if (social && !CURRENCY_SOCIAL.has(code)) return `${sign}${s} ${code}`;
    return meta.after ? `${sign}${s} ${meta.symbol}` : `${sign}${meta.symbol}${s}`;
  }

  const q = new URLSearchParams(location.search);
  const sessionID = q.get("sessionID") || "";
  const lang = q.get("lang") || "en";
  const device = q.get("device") || "desktop";
  const raw = (q.get("rgs_url") || "").trim().replace(/\/+$/, "");
  const root = raw ? (/^https?:\/\//i.test(raw) ? raw : "https://" + raw) : "";
  // social=true means the game is loaded on a social casino (Stake.us): restricted gambling
  // vocabulary must not appear anywhere in the UI. The jurisdiction flag (socialCasino) says the
  // same thing after authenticate, and the social coins (XSC / XGC ...) only exist there: any of
  // the three turns it on. The URL and the currency param are there before authenticate.
  const urlCurrency = (q.get("currency") || "").trim().toUpperCase();
  let social = /^(true|1)$/i.test(q.get("social") || "") || CURRENCY_SOCIAL.has(urlCurrency);

  const state = {
    currency: urlCurrency || "USD",   // authenticate's balance.currency replaces it; the lobby's param until then
    balance: 0,          // integer, 6dp
    config: null,        // minBet / maxBet / stepBet / betLevels / jurisdiction
    round: null,         // active or last-completed round from authenticate
    authenticated: false,
  };

  class RgsError extends Error {
    constructor(code, message, status) {
      super(message || code);
      this.code = code;
      this.status = status;
    }
  }

  // The docs specify error *codes* (ERR_IS, ERR_IPB, ...) but not the envelope they
  // arrive in, so pull the code from any of the shapes a JSON error body might use.
  function errorCode(data, status) {
    const c = data && (data.statusCode || data.code || data.error ||
                       (data.status && data.status.code));
    // A server that lost the session (a restarted local server, say) may call it ERR_VAL; it is a session
    // problem, not the bet's, so don't send the player off trying other amounts.
    if (data && /unknown session|session not authenticated|session .* does not exist/i.test(String(data.message || ""))) return "ERR_IS";
    if (typeof c === "string" && /^ERR_/.test(c)) return c;
    // The RGS rate-limits bursts of requests ("Slow down"); a 429 body is sometimes plain text.
    if (status === 429 || (data && /slow down|too many/i.test(String(data.message || "")))) return "ERR_ACT";
    if (status === 423) return "ERR_MAINTENANCE";   // /wallet/play: new rounds paused (maintenance); settling still works
    return status >= 500 ? "ERR_GEN" : "ERR_VAL";
  }

  async function call(path, body) {
    if (!root) throw new RgsError("ERR_VAL", "rgs_url missing from the game URL");
    if (!sessionID) throw new RgsError("ERR_IS", "sessionID missing from the game URL");
    let res;
    try {
      res = await fetch(root + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({ sessionID }, body || {})),
      });
    } catch (e) {
      throw new RgsError("ERR_GEN", "network error contacting the RGS");
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* empty or non-JSON body */ }
    if (!res.ok) throw new RgsError(errorCode(data, res.status), (data && data.message) || res.statusText, res.status);
    return data || {};
  }

  // /authenticate, /balance and /play wrap the wallet as { balance: { amount, currency } };
  // /end-round answers with the bare { amount, currency }. Accept either.
  function absorb(data) {
    if (!data) return data;
    const b = (data.balance && typeof data.balance === "object") ? data.balance
            : (typeof data.amount === "number" && data.currency) ? data
            : null;
    if (b) {
      if (typeof b.amount === "number") state.balance = b.amount;
      if (b.currency) state.currency = b.currency;
    }
    return data;
  }

  // The RGS calls a round's event stream `state`; the math books call the same array
  // `events`. Alias it once here so the presentation layer only ever reads one name.
  function normalizeRound(r) {
    if (!r || typeof r !== "object") return null;
    if (!Array.isArray(r.events) && Array.isArray(r.state)) r.events = r.state;
    return r;
  }

  return {
    UNIT, sessionID, lang, device, rgsUrl: root, urlCurrency,
    get social() { return social; },
    /** Social mode on after the fact: authenticate's jurisdiction.socialCasino, or a social coin as the wallet. */
    get socialFromSession() {
      const j = (state.config && state.config.jurisdiction) || {};
      return j.socialCasino === true || CURRENCY_SOCIAL.has(state.currency);
    },
    setSocial(on) { social = !!on; },
    isSocialCurrency: code => CURRENCY_SOCIAL.has(code || state.currency),
    get state() { return state; },
    RgsError,

    /** Must succeed before any other wallet call, or the rest return ERR_IS. A launch can
     *  meet a passing server error or a dropped connection on this very first call, so a
     *  general error or a rate-limit is tried again - four tries over about 3.5 s - before
     *  the player is told the game can't connect. Anything else (an expired session...) is
     *  final at once. */
    async authenticate() {
      let d = null, lastErr = null;
      for (let attempt = 0; attempt < 4; attempt++) {
        if (attempt) await new Promise(res => setTimeout(res, 500 * 2 ** (attempt - 1)));
        try { d = absorb(await call("/wallet/authenticate", {})); lastErr = null; break; }
        catch (e) {
          lastErr = e;
          console.warn(`authenticate try ${attempt + 1}: ${e.code}${e.status ? " (HTTP " + e.status + ")" : ""} ${e.message}`);
          if (e.code !== "ERR_GEN" && e.code !== "ERR_ACT") throw e;
        }
      }
      if (lastErr) throw lastErr;
      if (d.config) state.config = d.config;
      state.round = normalizeRound(d.round);
      state.authenticated = true;
      return d;
    },

    async balance() { return absorb(await call("/wallet/balance", {})); },

    /** amount is the BASE bet; the RGS debits amount x the mode's cost multiplier. The request is
     *  exactly the documented { sessionID, amount, mode }: the session already fixes the wallet's
     *  currency (an extra field risks a plain 400 "Bad Request" on the live RGS). */
    async play(amount, mode) {
      const d = absorb(await call("/wallet/play", { amount, mode }));
      state.round = normalizeRound(d.round);
      return d;
    },

    /** Settles the round and pays out. Nothing else may happen on the round after this.
     *  A round that paid nothing is closed by the RGS on /play already and comes back
     *  active:false — calling end-round on one answers ERR_VAL. The balance the /play
     *  response carried is the settled one, so leave those rounds alone. */
    async endRound() {
      const open = state.round;
      state.round = null;
      if (open && open.active === false) return null;
      // Developers on the engine.io server see a sporadic 500 from end-round even though
      // the round settles fine — retry briefly, then confirm with authenticate rather
      // than tell the player their win failed when it didn't.
      let lastErr = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        try { return absorb(await call("/wallet/end-round", {})); }
        catch (e) {
          lastErr = e;
          if (e.code !== "ERR_GEN" && e.code !== "ERR_ACT") throw e;
          await new Promise(res => setTimeout(res, 350 * (attempt + 1)));
        }
      }
      try {
        const d = absorb(await call("/wallet/authenticate", {}));
        const still = d.round && d.round.active === true;
        if (!still) return d;                     // settled on their side after all
        state.round = normalizeRound(d.round);    // genuinely still open — surface it
      } catch (e) { /* fall through to the original error */ }
      throw lastErr;
    },

    /** Bet Replay: the lobby opens the game with replay=true plus the round's coordinates.
     *  No session is involved — anyone with the link can watch the round. */
    replayParams() {
      // the optional params may be missing or junk: the replay still plays (amount -> 1.00, currency -> the
      // default) rather than failing (approval guideline: "keep working when they are missing or invalid")
      const amt = Number(q.get("amount"));
      return {
        replay: q.get("replay") === "true",
        game: q.get("game") || "",
        version: q.get("version") || "",
        mode: q.get("mode") || "",
        event: q.get("event") || "",
        amount: Number.isFinite(amt) && amt > 0 ? Math.round(amt) : 0,
        currency: /^[A-Z0-9]{2,6}$/.test(urlCurrency) ? urlCurrency : "",
        lang,
      };
    },

    /** GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event} ->
     *  { state: [events], payoutMultiplier, costMultiplier }. Unauthenticated by design. */
    async replay(p) {
      if (!root) throw new RgsError("ERR_VAL", "rgs_url missing from the game URL");
      const path = ["bet", "replay", p.game, p.version, p.mode, p.event].map(encodeURIComponent).join("/");
      let res;
      try { res = await fetch(root + "/" + path); }
      catch (e) { throw new RgsError("ERR_GEN", "network error contacting the RGS"); }
      let data = null;
      try { data = await res.json(); } catch (e) { /* empty */ }
      if (!res.ok || !data || !Array.isArray(data.state)) throw new RgsError(errorCode(data, res.status), "replay not found", res.status);
      return data;
    },

    /** Cost multiplier for a mode, from the RGS config when it supplies one. */
    costOf(mode) {
      const modes = (state.config && state.config.gameModes) || [];
      const m = modes.find(x => x.mode === mode);
      return (m && typeof m.costMultiplier === "number") ? m.costMultiplier : null;
    },

    /** A mode's own bet cap (gameModes[].maxBet, micro-units), or null when there is none. The live
     *  RGS sends maxBet: 0 for EVERY mode under XGC (Gold Coins): 0 means "no per-mode cap" - fall back
     *  to config.maxBet. Reading it as "mode off" locked the whole game under GC (2026-11 rejection). */
    modeMaxBet(mode) {
      const modes = (state.config && state.config.gameModes) || [];
      const m = modes.find(x => x.mode === mode);
      return (m && typeof m.maxBet === "number" && m.maxBet > 0) ? m.maxBet : null;
    },

    /** The token the player is playing with, as the balance label names it. The social
     *  coins go by their short codes: their long names carry words social mode forbids. */
    currencyName(code) {
      const c = code || state.currency;
      return CURRENCY_SOCIAL.has(c) ? metaOf(c).symbol : c;
    },

    /** Money for the screen - see formatMoney: money(a) exact (wins, bets, prices), money(a, null,
     *  "balance") at the currency's usual decimals, money(a, null, dp) at exactly dp decimals. */
    money: formatMoney,
    /** The balance: always two decimals, rounded, in every currency. */
    moneyBalance(amount, currency) { return formatMoney(amount, currency, "balance"); },
    /** How many decimals the exact form of an amount takes (at least the currency's usual ones). */
    exactDp(amount, currency) { return exactDp(amount, metaOf(currency || state.currency).decimals); },
    /** The currency's usual decimals. */
    decimalsOf(currency) { return metaOf(currency || state.currency).decimals; },

    /** Bet must sit within min/max and land on a step boundary. */
    validBet(amount) {
      const c = state.config;
      if (!c) return true;
      if (amount < c.minBet || amount > c.maxBet) return false;
      if (c.stepBet && amount % c.stepBet !== 0) return false;
      return true;
    },

    betLevels() {
      const c = state.config;
      if (c && Array.isArray(c.betLevels) && c.betLevels.length) return c.betLevels.slice();
      if (c && c.minBet) return [c.minBet];
      return [UNIT];
    },

    jurisdiction() { return (state.config && state.config.jurisdiction) || {}; },
  };
})();
