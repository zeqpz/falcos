"""Replay every Falcos book the way the client must, and check the event contract (EVENTS.md).

    python verify_books.py                  # all modes in library/publish_files
    python verify_books.py --modes base     # a subset
    python verify_books.py --write-index    # also write library/test_books.json (book ids per feature)

It tracks the board (reveal + tumbleBoard), the cell-multiplier grid (cellMults / featureFire),
MAX cells, the FILL UP board and gauge, and checks that every number the events carry follows
from the ones before it: cluster pays and multipliers, doublings, pump multipliers, collector
totals, board totals, setWin/setTotalWin/finalWin and the book's payoutMultiplier. Any failure is
a math bug (or a contract change EVENTS.md has to follow).
"""

import argparse
import io
import json
import os
import sys
from collections import defaultdict

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from game_config import GameConfig, PAYING  # noqa: E402

PUBLISH = os.path.join(HERE, "library", "publish_files")
CAP = 2048
_CFG = GameConfig()
WINCAP = int(round(_CFG.wincap * 100))   # hundredths (max win 50,000x = 5,000,000)
NR, NC = _CFG.num_reels, _CFG.num_rows[0]   # 7 reels x 5 rows


class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def read_books(mode):
    path = os.path.join(PUBLISH, f"books_{mode}.jsonl.zst")
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    for line in io.BytesIO(data):
        if line.strip():
            yield json.loads(line)


class Replay:
    def __init__(self, paytable):
        self.pay = paytable

    def run(self, book, tags):
        ev = book["events"]
        for i, e in enumerate(ev):
            check(e["index"] == i, f"event index {e['index']} != {i}")
        self.grid = [[1] * NC for _ in range(NR)]
        self.maxc = set()
        self.board = None
        self.pad = None
        self.paid = 0               # hundredths paid by winInfo + fillUpEnd
        self.last_total = 0
        self.last_wins = []
        self.fs_seen = 0
        self.fill = None
        self.fuel = None
        self.wheel = None
        self.bonuses = []
        final = None
        for e in ev:
            t = e["type"]
            getattr(self, "on_" + t, self.on_unknown)(e, tags)
            if t == "setTotalWin":
                self.last_total = e["amount"]
            if t == "finalWin":
                final = e["amount"]
        check(final is not None, "no finalWin")
        check(final == book["payoutMultiplier"], f"finalWin {final} != payoutMultiplier {book['payoutMultiplier']}")
        check(final == min(self.paid, WINCAP), f"finalWin {final} != paid {self.paid}")
        check(self.last_total == final, f"last setTotalWin {self.last_total} != finalWin {final}")
        check(final % 10 == 0, f"payout {final} not a 0.1x step")
        if self.wheel is not None:
            check(ev[0]["type"] == "luckyWheel", "luckyWheel must be the first event")
            if self.wheel == "none":
                check([e["type"] for e in ev] == ["luckyWheel", "finalWin"] and final == 0,
                      "a 'none' wheel is followed by finalWin 0 only")
            else:
                check(self.bonuses == [self.wheel], f"wheel {self.wheel} but bonuses {self.bonuses}")
                check(ev[1]["type"] in ("freeSpinTrigger", "enterBonus"), "the bonus follows the wheel")
        if final >= WINCAP:
            tags.add("wincap")
        if final == 0:
            tags.add("loss")

    def on_luckyWheel(self, e, tags):
        check(e["result"] in ("premium", "midnight", "none"), "luckyWheel result")
        check(self.wheel is None, "one wheel per book")
        self.wheel = e["result"]
        tags.add(f"wheel_{e['result']}")

    def on_unknown(self, e, tags):
        raise Fail(f"unknown event type {e['type']}")

    # -------------------------------------------------------------- board games
    def on_reveal(self, e, tags):
        b = e["board"]
        check(len(b) == NR and all(len(col) == NC + 2 for col in b), f"reveal must be {NR} reels x {NC + 2} (padded) rows")
        self.pad = [col[0]["name"] for col in b]
        self.board = [[s["name"] for s in col[1:NC + 1]] for col in b]
        names = [n for col in self.board for n in col]
        if names.count("DS") == 2:
            tags.add("ds_tease")
        if names.count("BS") == 2:
            tags.add("bs_tease")
        if e["gameType"] == "freegame":
            check(self.fs_seen > 0, "freegame reveal before updateFreeSpin")
        for r, col in enumerate(self.board):
            for c, n in enumerate(col):
                if n in ("ZP", "ST", "GT", "GP"):
                    check(b[r][c + 1].get("feature") is True, "feature symbol missing feature flag")
                if n in ("BS", "DS"):
                    check(b[r][c + 1].get("scatter") is True, "scatter missing scatter flag")

    def on_winInfo(self, e, tags):
        total = 0
        self.last_wins = []
        for w in e["wins"]:
            pos = [(p["reel"], p["row"] - 1) for p in w["positions"]]
            check(all(0 <= c < NC for _, c in pos), f"win position row out of 1..{NC}")
            check(all(self.board[r][c] == w["symbol"] for r, c in pos), "win positions do not hold the symbol")
            check(w["kind"] == len(pos) == w["meta"]["clusterSize"], "cluster size mismatch")
            cm = [self.grid[r][c] for r, c in pos]
            check(cm == w["meta"]["cellMults"], f"cellMults {w['meta']['cellMults']} != grid {cm}")
            boosted = [m for m in cm if m >= 2]
            mult = sum(boosted) if boosted else 1
            check(mult == w["meta"]["multiplier"], "multiplier is not the sum of the x2+ cells")
            pay = int(round(self.pay[(len(pos), w["symbol"])] * 100))
            check(pay == w["meta"]["winWithoutMult"], "winWithoutMult != paytable")
            touches = any(p in self.maxc for p in pos)
            check(bool(w["meta"].get("maxWin")) == touches, "maxWin flag vs MAX cells mismatch")
            if touches:
                tags.add("max_cluster")
            else:
                check(w["win"] <= pay * mult, "win above pay x multiplier")
                if w["win"] != pay * mult:
                    check(self.paid + total + w["win"] <= WINCAP, "trimmed win below cap")
            if mult >= 2:
                tags.add("multiplied_win")
            total += w["win"]
            self.last_wins.extend(pos)
        check(total == e["totalWin"], "winInfo totalWin != sum of wins")
        self.paid += total
        tags.add("cluster_win")

    def on_updateTumbleWin(self, e, tags):
        pass

    def on_setWin(self, e, tags):
        pass

    def on_setTotalWin(self, e, tags):
        check(e["amount"] == min(self.paid, WINCAP), f"setTotalWin {e['amount']} != paid {self.paid}")

    def on_wincap(self, e, tags):
        check(e["amount"] == WINCAP, "wincap amount")

    def on_finalWin(self, e, tags):
        pass

    def _apply_grid(self, e, changed):
        g = [row[:] for row in self.grid]
        for r, c, a, b in changed:
            check(g[r][c] == a, f"cell ({r},{c}) from {a} but grid holds {g[r][c]}")
            g[r][c] = b
        check(g == e["gridMults"], "gridMults does not match the changes listed")
        self.grid = g

    def on_cellMults(self, e, tags):
        ch = [(x["reel"], x["row"] - 1, x["from"], x["to"]) for x in e["changed"]]
        if e["reason"] == "win":
            check(sorted((r, c) for r, c, _, _ in ch) == sorted(set(self.last_wins)), "doubled cells != cluster cells")
            check(all(b == min(a * 2, CAP) for _, _, a, b in ch), "win doubling wrong")
            self._apply_grid(e, ch)
        else:
            self.grid = [row[:] for row in e["gridMults"]]
            tags.add(f"cellmults_{e['reason']}")
            if e["reason"] == "bonusStart":
                self.maxc = set()
        check({(p["reel"], p["row"] - 1) for p in e["maxCells"]} == self.maxc, "cellMults maxCells mismatch")

    def on_featureFire(self, e, tags):
        r, c = e["reel"], e["row"] - 1
        kind = e["kind"]
        sym = {"zippo": "ZP", "scratch": "ST", "gold": "GT", "pump": "GP"}[kind]
        check(self.board[r][c] == sym, f"featureFire {kind} at a cell holding {self.board[r][c]}")
        ch = [(x["reel"], x["row"] - 1, x["from"], x["to"]) for x in e["cells"]]
        burned = [(x["reel"], x["row"] - 1, x["symbol"]) for x in e["burned"]]
        for a, b, s in burned:
            check(self.board[a][b] == s and s in PAYING, "burned cell does not hold that paying symbol")
        if kind == "pump":
            tags.add(f"pump_{e['grade']}")
            check(sorted((a, b) for a, b, _, _ in ch) == [(r, y) for y in range(NC)], "pump cells != its column")
            if e["grade"] == "fulltank":
                check(e["mult"] is None and all(f == t for _, _, f, t in ch), "fulltank changes no multiplier")
            else:
                check(all(t == min(f * e["mult"], CAP) for _, _, f, t in ch), "pump multiplier wrong")
            check(all(a == r for a, _, _ in burned), "pump burned outside its column")
        else:
            check(all(t == min(f * 2, CAP) for _, _, f, t in ch), f"{kind} doubling wrong")
            tags.add(kind)
            if kind == "zippo":
                area = {(x, y) for x in range(r - 1, r + 2) for y in range(c - 1, c + 2) if 0 <= x < NR and 0 <= y < NC}
                check({(a, b) for a, b, _, _ in ch} == area, "zippo cells != its 3x3")
            if kind == "scratch" and e.get("target"):
                check(all(s == e["target"] for _, _, s in burned), "scratch burned another symbol")
        # sequential: a cell may appear more than once in one event only if listed in order
        g = [row[:] for row in self.grid]
        for a, b, f, t in ch:
            check(g[a][b] == f, f"{kind}: cell ({a},{b}) from {f} but grid holds {g[a][b]}")
            g[a][b] = t
        check(g == e["gridMults"], f"{kind}: gridMults mismatch")
        self.grid = g

    def on_maxCells(self, e, tags):
        added = {(p["reel"], p["row"] - 1) for p in e["added"]}
        self.maxc |= added
        check({(p["reel"], p["row"] - 1) for p in e["cells"]} == self.maxc, "maxCells.cells mismatch")
        tags.add("max_cells")

    def on_tumbleBoard(self, e, tags):
        expl = defaultdict(list)
        for p in e["explodingSymbols"]:
            expl[p["reel"]].append(p["row"] - 1)
        for r in range(NR):
            k = len(expl[r])
            new = [s["name"] for s in e["newSymbols"][r]]
            # SDK convention: newSymbols[reel] = [new top padding, new visible symbols top->bottom];
            # the old top padding drops into view under them, so k exploding -> k entries
            check(len(new) == k, f"reel {r}: {k} exploding but {len(new)} new symbols")
            if k:
                survivors = [n for c, n in enumerate(self.board[r]) if c not in expl[r]]
                self.board[r] = new[1:] + [self.pad[r]] + survivors
                self.pad[r] = new[0]
                check(len(self.board[r]) == NC, "column length after tumble")

    # -------------------------------------------------------------- bonuses
    def on_freeSpinTrigger(self, e, tags):
        check(e["totalFs"] == 10, "totalFs")
        for p in e["positions"]:
            check(self.board[p["reel"]][p["row"] - 1] == e["symbol"], "trigger position does not hold the scatter")

    def on_enterBonus(self, e, tags):
        tags.add(f"bonus_{e['reason']}" + ("_bought" if e["bought"] else ""))
        self.bonuses.append(e["reason"])
        self.fs_seen = 0

    def on_updateFreeSpin(self, e, tags):
        self.fs_seen += 1
        check(e["amount"] == self.fs_seen and e["total"] == 10, "updateFreeSpin numbering")

    def on_freeSpinEnd(self, e, tags):
        pass

    # -------------------------------------------------------------- FILL UP
    def ftotal(self):
        return round(sum(v.get("value", 0) for v in self.fill.values()), 2)

    def on_gauge(self, e, tags):
        if e["reason"] == "start":
            check(e["fuel"] == 3, "gauge starts full")
            self.fill = {}
        elif e["reason"] == "use":
            check(e["fuel"] == self.fuel - 1, "gauge use must drop one bar")
            self._fresh_clear()     # a collector is "fresh" only on the spin it lands
        else:
            check(e["fuel"] == 3, "refill to 3")
            check(self.landed, "refill without anything new")
        self.fuel = e["fuel"]

    def on_fillUpLand(self, e, tags):
        self.landed = False
        for x in e["cells"]:
            pos = (x["reel"], x["row"] - 1)
            check(pos not in self.fill, "landed on an occupied cell")
            if x["name"] != "X":
                item = {"name": x["name"]}
                if "value" in x:
                    item["value"] = x["value"]
                if x["name"] in ("ST", "GT"):
                    item["fresh"] = True
                self.fill[pos] = item
                if e["spin"] > 0:
                    self.landed = True
                tags.add(f"fill_land_{x['name']}")
                if x["name"] == "FD":
                    v = x["value"]
                    tags.add("fd_green" if v < 5 else "fd_amber" if v < 50 else "fd_red")
        if e["spin"] > 0:
            check(self.fuel is not None, "spin before gauge")
            empty = NR * NC - len([1 for p in self.fill if p not in {(c["reel"], c["row"] - 1) for c in e["cells"]}])
            check(len(e["cells"]) == empty, "fillUpLand must list every empty cell")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "fillUpLand boardTotal")

    def on_pumpBoost(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        check(self.fill.get(pos, {}).get("name") == "GP", "pumpBoost from a non-pump cell")
        for x in e["boosted"]:
            item = self.fill[(x["reel"], x["row"] - 1)]
            check(x["reel"] == e["reel"], "pump boosted outside its column")
            check(abs(item["value"] - x["from"]) < 1e-6, "pump from value")
            check(abs(round(x["from"] * e["mult"], 2) - x["to"]) < 1e-6, "pump to value")
            item["value"] = x["to"]
        del self.fill[pos]
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "pumpBoost boardTotal")
        tags.add("fill_pump")

    def on_collect(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        me = self.fill.get(pos)
        check(me and me["name"] == ("ST" if e["kind"] == "scratch" else "GT"), "collector cell")
        got = 0
        for x in e["collected"]:
            p = (x["reel"], x["row"] - 1)
            item = self.fill.get(p)
            check(item and abs(item["value"] - x["value"]) < 1e-6 and not item.get("fresh"), "collected item mismatch")
            if e["kind"] == "scratch":
                check(max(abs(p[0] - pos[0]), abs(p[1] - pos[1])) == 1, "scratch collected beyond its neighbours")
            got += x["value"]
            del self.fill[p]
        check(abs(round(me["value"] + got, 2) - e["total"]) < 1e-6, "collector total")
        check(e["removed"] == (not e["collected"]), "removed flag")
        if e["removed"]:
            del self.fill[pos]
        else:
            me["value"] = e["total"]
            tags.add(f"fill_collect_{e['kind']}")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "collect boardTotal")

    def on_zippoBurn(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        check(self.fill.get(pos, {}).get("name") == "ZP", "zippoBurn from a non-zippo cell")
        for x in e["burned"]:
            p = (x["reel"], x["row"] - 1)
            check(max(abs(p[0] - pos[0]), abs(p[1] - pos[1])) <= 1, "zippo burned beyond its 3x3")
            check(self.fill[p]["name"] == "FD", "zippo burned a non-drop")
            del self.fill[p]
        del self.fill[pos]
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "zippoBurn boardTotal")
        if e["burned"]:
            tags.add("fill_zippo_burn")

    def on_fillUpEnd(self, e, tags):
        for item in self.fill.values():
            item.pop("fresh", None)
        check(all(v["name"] in ("FD", "ST", "GT") for v in self.fill.values()), "leftover pump/zippo on the board")
        drops = sorted((x["reel"], x["row"] - 1, x["value"]) for x in e["drops"])
        mine = sorted((p[0], p[1], v["value"]) for p, v in self.fill.items() if v["name"] == "FD")
        check(drops == mine, "fillUpEnd drops mismatch")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "fillUpEnd boardTotal")
        expect = min(int(round(e["boardTotal"] * 100)), WINCAP - self.paid)
        check(e["win"] == expect, f"fillUpEnd win {e['win']} != {expect}")
        self.paid += e["win"]
        tags.add(f"fillup_end_{e['reason']}")
        if e["collectors"]:
            tags.add("fillup_end_with_collector")

    def _fresh_clear(self):
        for item in self.fill.values():
            item.pop("fresh", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=None)
    ap.add_argument("--write-index", action="store_true")
    args = ap.parse_args()
    cfg = GameConfig()
    with open(os.path.join(PUBLISH, "index.json"), encoding="utf-8") as fh:
        modes = [m["name"] for m in json.load(fh)["modes"]]
    if args.modes:
        modes = [m for m in modes if m in args.modes]
    rp = Replay(cfg.paytable)
    index = {}
    bad = 0
    for mode in modes:
        coverage = defaultdict(list)
        n = 0
        lut = {}
        with open(os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv"), encoding="utf-8") as fh:
            for line in fh:
                i, w, p = line.strip().split(",")
                lut[int(i)] = int(p)
        for book in read_books(mode):
            n += 1
            tags = set()
            try:
                rp.run(book, tags)
                check(lut.get(book["id"]) == book["payoutMultiplier"], "LUT payout != book payout")
                # collectors that collected stay fresh only for the spin they land on
            except Fail as exc:
                bad += 1
                if bad <= 20:
                    print(f"[{mode}] book {book['id']} ({book.get('criteria')}): {exc}")
                continue
            tags.add(f"criteria_{book.get('criteria')}")
            for t in tags:
                coverage[t].append(book["id"])
        print(f"\n{mode}: {n} books, {len(lut)} LUT rows")
        for t in sorted(coverage):
            ids = coverage[t]
            print(f"   {t:<28} {len(ids):>6}   e.g. {ids[:5]}")
        index[mode] = {t: ids[:10] for t, ids in sorted(coverage.items())}
    print(f"\n{'FAILED: ' + str(bad) + ' books' if bad else 'all books replay cleanly'}")
    if args.write_index:
        out = os.path.join(HERE, "library", "test_books.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=1)
        print(f"wrote {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
