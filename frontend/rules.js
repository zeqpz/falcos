/* Game rules, paytable and UI guide — the content behind the (i) button.
 *
 * Falcos (FALCOS_DESIGN.md). Every number here must mirror the math's game_config.py in
 * math-sdk/games/falcos once it is published; the reviewer checks wins against this page, so it must
 * never drift from the paytable the books were generated with. The paytable is ONE table (PAYS,
 * with its cluster sizes in TIERS) - update it there and the page follows. The numbers below are the
 * design's draft. Pays are multiples of the TOTAL bet, per cluster, by cluster size.
 *
 * Social mode (Stake.us) forbids a list of gambling terms. Copy is written once in the
 * normal vocabulary and passed through T() which swaps the restricted words when the game
 * is loaded with social=true — see the jurisdiction-requirements guideline.
 */
const RULES = (() => {
  // Cluster sizes, one column each; the last is "15 or more".
  const TIERS = ["5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15+"];
  const PAYS = {   // symbol: one pay per TIERS column (x the total bet) - owner-approved table (FALCOS_DESIGN.md, config_fe_falcos.json)
    H1: [1, 1.5, 2, 2.5, 3, 5, 8, 15, 30, 60, 150],
    H2: [0.8, 1, 1.2, 1.5, 2, 4, 6, 12, 25, 50, 100],
    H3: [0.5, 0.8, 1, 1.2, 1.5, 3, 4.5, 10, 20, 40, 60],
    H4: [0.4, 0.5, 0.8, 1, 1.2, 2, 3, 5, 10, 20, 40],
    L1: [0.3, 0.4, 0.5, 0.8, 1, 1.5, 2.5, 4, 8, 15, 30],
    L2: [0.3, 0.4, 0.5, 0.6, 0.8, 1.2, 2, 3, 6, 12, 25],
    L3: [0.2, 0.3, 0.4, 0.5, 0.7, 1.1, 1.8, 2.8, 5.5, 11, 22],
    L4: [0.2, 0.3, 0.4, 0.5, 0.6, 1, 1.5, 2.5, 5, 10, 20],
    L5: [0.2, 0.2, 0.3, 0.4, 0.5, 0.9, 1.4, 2.2, 4.5, 9, 18],
  };
  const NAMES = {
    H1: "Cash Drawer", H2: "Gold Key", H3: "Pump Nozzle", H4: "Jerry Can",
    L1: "Energy Drink", L2: "Slushie", L3: "Hot Dog", L4: "Chips", L5: "Donut",
    ZP: "Lighter", ST: "Scratch Ticket", GT: "Gold Scratch Ticket", GP: "Gas Pump",
    FDG: "Fuel Drop (green)", FDA: "Fuel Drop (amber)", FDR: "Fuel Drop (red)",
    BS: "FALCOS Token", DS: "Midnight Token",
  };
  const ORDER = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "L5"];
  const RTP = "96.50%", MAX_WIN = 50000;
  const CELL_MAX = 2048;
  // Gas Pump grades and Fuel Drop values (FALCOS_DESIGN.md)
  const PUMP = { REGULAR: [2, 4], PLUS: [8, 16], PREMIUM: [32, 64] };
  const DROPS = { green: [0.2, 0.5, 1, 2, 3], amber: [5, 10, 15, 20], red: [50, 100, 250, 500] };
  // the bet modes (the math's mode keys), as the Bonus panel sells them
  const MODES = [
    { keys: ["chance"], name: "FUEL CHANCE", what: "Base spins with about 2.2 times the chance of triggering any bonus. Once activated it stays on for every spin until you turn it off." },
    { keys: ["fillup"], name: "Buy FILL UP", what: "Starts the FILL UP bonus." },
    { keys: ["premium"], name: "Buy PREMIUM", what: "Starts PREMIUM: 10 free spins with sticky cell multipliers." },
    { keys: ["nitro"], name: "NITRO SPIN", what: "Spins with every cell preloaded with a multiplier from x16 to x2048. Once activated it stays on for every spin until you turn it off." },
    { keys: ["midnight"], name: "Buy MIDNIGHT RUN", what: "Starts MIDNIGHT RUN: 10 free spins with sticky cell multipliers, every cell starting at x4." },
  ];

  // Restricted phrase -> replacement, from Stake's jurisdiction-requirements table. Longer
  // phrases first so "buy bonus" is swapped before "buy" gets a chance at it.
  const SWEEPS = [
    ["pay table", "win table"], ["paytable", "win table"], ["payouts", "wins"], ["payout", "win"],
    ["buying", "getting"], ["gambling", "play"],
    ["buy bonus", "get bonus"], ["bonus buy", "bonus"], ["total bet", "total play"],
    ["at the cost of", "for"], ["cost of", "can be played for"], ["pays out", "wins"],
    ["paid out", "won"], ["pay out", "win"], ["win feature", "play feature"],
    ["place your bets", "come and play"], ["betting", "playing"], ["bets", "plays"], ["bet", "play"],
    ["bought", "instantly triggered"], ["buy", "get"], ["purchase", "play"],
    ["cash", "coins"], ["money", "coins"], ["currency", "token"], ["credit", "balance"],
    ["wager", "play"], ["gamble", "play"], ["stake", "play amount"],
    ["pays", "wins"], ["paid", "won"], ["pay", "win"], ["costs", "is played for"], ["cost", "amount"],
  ];
  // Each replacement word borrows the case of the word it replaces ("Buy Bonus" -> "Get
  // Bonus", "BET" -> "PLAY"), so headings and buttons keep their look.
  function recase(from, to) {
    const src = from.split(" "), out = to.split(" ");
    return out.map((w, i) => {
      const s = src[Math.min(i, src.length - 1)];
      if (s === s.toUpperCase() && /[A-Z]/.test(s)) return w.toUpperCase();
      if (s[0] === s[0].toUpperCase()) return w[0].toUpperCase() + w.slice(1);
      return w;
    }).join(" ");
  }
  function T(text, social) {
    if (!social) return text;
    let out = text;
    for (const [from, to] of SWEEPS) {
      out = out.replace(new RegExp("\\b" + from + "\\b", "gi"), m => recase(m, to));
    }
    return out;
  }

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const x = v => "x" + (Number.isInteger(v) ? v : String(v));
  const list = a => a.map(x).join(" / ");

  function tile(sym, social) {
    return `<img class="ptile" src="assets/flat/${sym}.webp" alt="${esc(T(NAMES[sym], social))}" draggable="false">`;
  }
  // a special symbol's row: its tile, its name and id, and what it does
  const special = (sym, title, text, social, t) =>
    `<div class="prow">${tile(sym, social)}<div class="pname">${t(title)}<small>${sym}</small></div><div class="ptext">${t(text)}</div></div>`;

  /**
   * opts: { bet: integer 6dp, fmt(amount) -> string, social: bool, modeCost: { <mode key>: cost } }
   */
  function render(opts) {
    const { bet, fmt, social } = opts;
    const cost = opts.modeCost || {};
    const t = s => T(s, social);
    const money = mult => fmt(Math.round(mult * bet));

    const payRows = ORDER.map(sym => {
      const p = PAYS[sym];
      return `<div class="prow">
        ${tile(sym, social)}
        <div class="pname">${esc(t(NAMES[sym]))}<small>${sym}</small></div>
        <div class="pvals">
          ${TIERS.map((tier, i) => `<div><b>${tier}</b> ${x(p[i])} <em>${money(p[i])}</em></div>`).join("")}
        </div>
      </div>`;
    }).join("");

    const modeRows = MODES.map(m => {
      const key = m.keys.find(k => cost[k] > 0);
      if (!key) return "";
      return `<tr><td>${t(m.name)}</td><td>${x(cost[key])} <em>${money(cost[key])}</em></td><td>${t(m.what)} ${t("RTP ")}${RTP}.</td></tr>`;
    }).join("");

    const html = `
<section>
  <h4>${t("About the game")}</h4>
  <p>${t(`Falcos is a 7-reel, 5-row video slot with cluster pays and tumbling reels. A cluster is 5 or more matching symbols touching horizontally or vertically (diagonals do not count), anywhere on the board. Every cluster pays by its symbol and size (15 or more pays the top rate), times its multiplier; then the winning symbols clear, the symbols above fall, new ones drop in, and the new board is paid again. The values below are multiples of the total bet, shown at your current bet of ${fmt(bet)}.`)}</p>
  <div class="kvgrid">
    <div><span>RTP</span><b>${RTP}</b><small>${t("every mode")}</small></div>
    <div><span>${t("Max win")}</span><b>${x(MAX_WIN)}</b><small>${t("of the total bet")} · ${money(MAX_WIN)}</small></div>
    <div><span>${t("Volatility")}</span><b>${t("High")}</b><small>${t("the cell multipliers carry the big wins")}</small></div>
  </div>
  <p class="fine">${t("The expected return is calculated over many plays. A round's total win is capped at the max win; once the cap is reached the round ends and any remaining feature is void.")}</p>
</section>

<section>
  <h4>${t("Game modes")}</h4>
  <table class="modes">
    <tr><th>${t("Mode")}</th><th>${t("Cost")}</th><th>${t("What you get")}</th></tr>
    <tr><td>${t("Base game")}</td><td>${x(1)} <em>${money(1)}</em></td><td>${t("One spin. FILL UP, PREMIUM and MIDNIGHT RUN trigger naturally from FALCOS Tokens and Midnight Tokens.")}</td></tr>
    ${modeRows}
  </table>
  <p class="fine">${t("All are chosen from the Bonus panel, which shows the exact price at your bet before anything is charged; a buy asks you to confirm. FUEL CHANCE and NITRO SPIN, once activated, stay on until you turn them off. The max win applies to every mode.")}</p>
</section>

<section>
  <h4>${t("Paytable")}</h4>
  <p class="fine">${t("Pays by cluster size: 5 to 14, and 15 or more matching symbols touching horizontally or vertically. Multiples of the total bet and the amount at your current bet, before the cluster's multiplier. There is no wild symbol.")}</p>
  <div class="paytable">${payRows}</div>
</section>

<section>
  <h4>${t("Cell multipliers")}</h4>
  <div class="prow"><div class="ptile multi"><span>x8</span><small>CELL</small></div><div class="pname">${t("Cell multipliers")}</div>
    <div class="ptext">${t(`Every cell has its own multiplier. It starts at x1 and doubles each time a win or a feature hits that cell, up to ${x(CELL_MAX)}. The multiplier belongs to the cell, not the symbol: whatever tumbles into the cell takes it on. A cluster's multiplier is the SUM of the multipliers of its cells that are at x2 or more; if none are, the cluster pays x1. In the base game the cells reset every spin; in PREMIUM and MIDNIGHT RUN they keep their multipliers for the whole bonus.`)}</div></div>
</section>

<section>
  <h4>${t("Feature symbols")}</h4>
  <p class="fine">${t("Each tumble resolves in order: cluster wins, then all Gas Pumps together, then Scratch Tickets and Gold Scratch Tickets one at a time, then Lighters - and the board refills after each of them, so a later feature acts on the refilled board. A feature that drops in during a refill fires in the next step. Feature symbols do not form clusters.")}</p>
  ${special("ZP", "Lighter", "Lights up its 3x3 area: its own cell and the 8 around it double their multipliers, and the paying symbols there burn - they clear, feeding their doubled multipliers into any cluster they were part of. Tokens keep their place but their cells still double. In FILL UP it burns every Fuel Drop in its 3x3 area and disappears.", social, t)}
  ${special("ST", "Scratch Ticket", "Scratches off one paying symbol that is on the board: every cell holding it doubles and burns, and so does the ticket's own cell. In FILL UP it collects every Fuel Drop in its 8 neighbours, adding their values to its own, plus any collector there that activated on an earlier spin; with nothing to collect it is removed, otherwise it stays with its total.", social, t)}
  ${special("GT", "Gold Scratch Ticket", "Every paying symbol on the board doubles and burns, and so does the ticket's own cell. In FILL UP it collects every Fuel Drop on the whole board.", social, t)}
  ${special("GP", "Gas Pump", `The biggest single event - at most one per column. It rolls a fuel grade: REGULAR ${list(PUMP.REGULAR)}, PLUS ${list(PUMP.PLUS)}, PREMIUM ${list(PUMP.PREMIUM)}, or FULL TANK. REGULAR to PREMIUM: every cell in its column gets the pump's multiplier and the paying symbols in the column burn. FULL TANK: every cell in the column becomes a MAX cell, and any cluster touching a MAX cell pays the max win. Pumps in different columns fire together. In FILL UP it rolls ${x(2)} to ${x(64)} and multiplies every Fuel Drop in its column and any collector there that has already collected; then it leaves.`, social, t)}
  ${special("FDA", "Fuel Drops", `FILL UP only. Sticky: green ${list(DROPS.green)}, amber ${list(DROPS.amber)}, red ${list(DROPS.red)}. A drop that grows changes colour: green under x5, amber from x5, red from x50.`, social, t)}
</section>

<section>
  <h4>${t("Scatters")}</h4>
  ${special("BS", "FALCOS Token", "Appears anywhere. 3 in the base game start FILL UP; 4 or more start PREMIUM. It does not form clusters and has no value of its own.", social, t)}
  ${special("DS", "Midnight Token", "Darker and rare. 3 in the base game (or in a FUEL CHANCE spin) start MIDNIGHT RUN. It does not form clusters and has no value of its own.", social, t)}
</section>

<section>
  <h4>${t("Bonuses")}</h4>
  <p><b>FILL UP</b> — ${t("3 FALCOS Tokens, or bought. A Fuel Drop collection game with a 3-bar fuel gauge; no cell multipliers. The gauge starts full. Every spin uses one bar, and any spin that lands something new (a drop or a feature) refills it to 3. The bonus ends when the gauge is empty and nothing new lands. At the end you win the total of every drop left plus every collector's total, times the bet, capped at the max win.")}</p>
  <p><b>PREMIUM</b> — ${t("4 or more FALCOS Tokens, or bought. 10 free spins of the base game with sticky cell multipliers: a cell that reached x8 keeps x8 into the next spin and keeps growing.")}</p>
  <p><b>MIDNIGHT RUN</b> — ${t("3 Midnight Tokens, or bought. 10 free spins with sticky cell multipliers, every cell starting at x4, and Gas Pumps landing far more often. The biggest bonus in the game.")}</p>
  <p class="fine">${t("Bonuses are played at the bet of the triggering spin. Every round is decided in full the moment it is placed: if the connection drops, reload the game and the round is settled and paid.")}</p>
</section>

<section>
  <h4>${t("How to play")}</h4>
  <table class="guide">
    <tr><td><b>${t("Spin")}</b></td><td>${t("Plays one round at the current bet. The spacebar does the same. While the reels are turning the button reads Skip and lands them at once (clicking the board also skips); every winning cluster is always shown in full.")}</td></tr>
    <tr><td><b>− / +</b></td><td>${t("Lowers or raises the bet through every level offered by the server.")}</td></tr>
    <tr><td><b>${t("Bonus")}</b></td><td>${t("Opens the Bonus panel: buy a bonus (FILL UP, PREMIUM, MIDNIGHT RUN) or turn on a special spin (FUEL CHANCE, NITRO SPIN). The total charge is shown before you confirm; a special spin stays on - the bar shows its price a spin - until you turn it off on its card or the pill over the bar.")}</td></tr>
    <tr><td><b>${t("Auto")}</b></td><td>${t("Plays a chosen number of rounds one after another at the current bet. You confirm the number before it starts; press it again to stop. It also stops when the balance can't cover the next round.")}</td></tr>
    <tr><td><b>${t("Rapid")}</b></td><td>${t("Shortens the reel spin and win animations. Results are unaffected.")}</td></tr>
    <tr><td><b>${t("Info")}</b></td><td>${t("Opens this page: the rules, the paytable and your recent rounds.")}</td></tr>
    <tr><td><b>${t("Audio")}</b></td><td>${t("Opens the Sound and Music volume sliders. Slide one all the way left to silence it; with both at zero every sound in the game is off. Levels are remembered on this device.")}</td></tr>
    <tr><td><b>${t("Win / Balance")}</b></td><td>${t("The bar shows your balance in the token you are playing with, and the current round's win while there is one. The balance is always the amount the server reports.")}</td></tr>
  </table>
</section>

<section>
  <p class="legal">${t("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.")}</p>
</section>`;
    return html;
  }

  return { render, T, PAYS, TIERS, NAMES, RTP, MAX_WIN };
})();
