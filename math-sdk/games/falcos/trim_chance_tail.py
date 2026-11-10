"""Keep FUEL CHANCE inside the 3-star etl40b limit (run after optimising chance; run.py does).

etl40b is the return, in base bets, from wins of 40 x the mode's cost or more (120x for a 3x
spin) and must stay <= 0.9. At 2.2x the bonus rate the bonuses alone put about 0.86 there; the
ordinary (`basegame`) spins paying 120x+ added another 0.27. This moves those ordinary boards'
weight down to ordinary boards paying 40x .. 119.9x:

* every basegame book paying >= the edge keeps weight 1 (it stays in the table, ~never drawn);
* the payout their weight carried goes to basegame books paying 40x .. edge, spread evenly by
  payout, so the table's RTP is unchanged (to integer rounding);
* the extra weight that needs comes from the zero-win books, so the total weight is unchanged
  (the hit rate rises by a hair);
* bonus, wincap and zero books keep their own weights apart from that. The books are not touched,
  so the verification sidecars stay valid. A second run changes nothing.

    python trim_chance_tail.py [--dry-run]
"""

import argparse
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "library")
LUT = os.path.join(LIB, "publish_files", "lookUpTable_chance_0.csv")
SEG = os.path.join(LIB, "lookup_tables", "lookUpTableSegmented_chance.csv")
COST = 3.0
EDGE = int(40 * COST * 100)          # payouts are in hundredths of the bet
LOW = 40 * 100


def etl40(rows, total):
    return sum(p / 100 * w for _, w, p in rows if p >= EDGE) / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    crit = {int(r[0]): r[1] for r in csv.reader(open(SEG))}
    rows = [[int(x) for x in r] for r in csv.reader(open(LUT)) if r]
    total = sum(w for _, w, _ in rows)
    rtp0 = sum(w * p for _, w, p in rows)
    print(f"before: etl40b {etl40(rows, total):.4f}  rtp {rtp0 / total / 100 / COST:.6f}")

    tail = [k for k, (i, w, p) in enumerate(rows) if crit.get(i) == "basegame" and p >= EDGE and w > 1]
    mid = [k for k, (i, w, p) in enumerate(rows) if crit.get(i) == "basegame" and LOW <= p < EDGE]
    zero = [k for k, (i, w, p) in enumerate(rows) if p == 0 and w > 1]
    if not tail:
        print("nothing to move"); return
    pay = sum((rows[k][1] - 1) * rows[k][2] for k in tail)      # payout mass to re-home
    for k in tail:
        rows[k][1] = 1
    # spread `pay` over the mid books evenly by payout: each gets the same payout mass
    per = pay / len(mid)
    added = 0
    for k in mid:
        dw = int(round(per / rows[k][2]))
        rows[k][1] += dw
        added += dw
    removed_tail = sum(1 for _ in tail)  # placeholder count
    # total weight: tail lost (w-1) each, mid gained `added`; balance from the zero books
    new_total = sum(w for _, w, _ in rows)
    diff = new_total - total
    zsum = sum(rows[k][1] for k in zero)
    assert zsum > diff, "not enough zero weight to balance"
    for k in zero:
        take = diff * rows[k][1] // zsum
        rows[k][1] -= take
    # integer remainder onto the heaviest zero book
    rem = sum(w for _, w, _ in rows) - total
    heavy = max(zero, key=lambda k: rows[k][1])
    rows[heavy][1] -= rem
    assert sum(w for _, w, _ in rows) == total and all(w >= 1 for _, w, _ in rows)
    rtp1 = sum(w * p for _, w, p in rows)
    print(f"after:  etl40b {etl40(rows, total):.4f}  rtp {rtp1 / total / 100 / COST:.6f}  "
          f"({len(tail)} tail books -> weight 1, {len(mid)} books 40x..{EDGE / 100:.0f}x lifted)")
    if not a.dry_run:
        with open(LUT, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(f"{i},{w},{p}\n" for i, w, p in rows))


if __name__ == "__main__":
    main()
