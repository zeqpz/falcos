"""Falcos custom events. The contract is documented in EVENTS.md - keep the two in step.

Conventions (same as the previous game on this engine):
  * every {reel,row} position carries the +1 padding offset on the row (row 1..5 are visible);
  * gridMults is the whole 7x5 grid (7 reels x 5 rows), reel-major (gridMults[reel][row]), visible rows only,
    NO padding offset, plain multipliers (1, 2, 4 ... 2048);
  * money amounts (win, amount, totalWin) are integer hundredths of the bet (100 = 1x);
  * Fuel Drop / collector values and cell multipliers are plain multiples (0.2 = x0.2).
"""

PAD = 1


def _pos(r, c):
    return {"reel": r, "row": c + PAD}


def _grid(gs):
    return [[int(v) for v in column] for column in gs.grid_mults]


def _max_cells(gs):
    return [_pos(r, c) for r, c in sorted(gs.max_cells)]


def cell_mults_event(gs, reason: str, changed: list) -> None:
    """The cell multiplier grid changed. reason: "win" (cells of the clusters just paid
    doubled), "nitro" (NITRO SPIN preload), "bonusStart" (PREMIUM / MIDNIGHT RUN grid)."""
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "cellMults",
        "reason": reason,
        "changed": [{"reel": r, "row": c + PAD, "from": a, "to": b} for r, c, a, b in changed],
        "gridMults": _grid(gs),
        "maxCells": _max_cells(gs),
    })


def feature_fire_event(gs, detail: dict) -> None:
    """One feature symbol fired (base game / PREMIUM / MIDNIGHT RUN / NITRO)."""
    r, c = detail["cell"]
    event = {
        "index": len(gs.book.events),
        "type": "featureFire",
        "step": detail["step"],
        "kind": detail["kind"],
        "reel": r,
        "row": c + PAD,
    }
    if detail["kind"] == "scratch":
        event["target"] = detail.get("target")
    if detail["kind"] == "pump":
        event["grade"] = detail["grade"]
        event["mult"] = detail["mult"]
    event["cells"] = [{"reel": a, "row": b + PAD, "from": f, "to": t} for a, b, f, t in detail["cells"]]
    event["burned"] = [{"reel": a, "row": b + PAD, "symbol": s} for a, b, s in detail["burned"]]
    event["gridMults"] = _grid(gs)
    gs.book.add_event(event)


def max_cells_event(gs, added: list) -> None:
    """A FULL TANK just turned a column into MAX cells. `cells` is every MAX cell now live."""
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "maxCells",
        "added": [_pos(r, c) for r, c in added],
        "cells": _max_cells(gs),
    })


def freespin_trigger_event(gs, positions: list, symbol: str) -> None:
    """PREMIUM / MIDNIGHT RUN awarded: scatter cells that triggered it (empty when bought)."""
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "freeSpinTrigger",
        "totalFs": gs.tot_fs,
        "symbol": symbol,
        "positions": [_pos(r, c) for r, c in positions],
    })


def enter_bonus_event(gs, reason: str, positions: list, bought: bool) -> None:
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "enterBonus",
        "reason": reason,
        "bought": bought,
        "positions": [_pos(r, c) for r, c in positions],
    })


# ------------------------------------------------------------------------------ FILL UP
def _cell(r, c, item):
    out = {"reel": r, "row": c + PAD, "name": item["name"] if item else "X"}
    if item and item["name"] in ("FD", "ST", "GT"):
        out["value"] = item["value"]
    return out


def gauge_event(gs, fuel: int, reason: str) -> None:
    """The 3-bar fuel gauge. reason: start | use | refill."""
    gs.book.add_event({"index": len(gs.book.events), "type": "gauge", "fuel": fuel, "reason": reason})


def fillup_land_event(gs, spin: int, cells: list) -> None:
    """What every empty cell landed on this FILL UP spin (spin 0 = the opening drops).
    `cells` lists each cell that was empty before the spin, X included."""
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "fillUpLand",
        "spin": spin,
        "cells": [_cell(r, c, item) for r, c, item in cells],
        "boardTotal": gs.fill_total(),
    })


def pump_boost_event(gs, cell, mult: int, boosted: list) -> None:
    r, c = cell
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "pumpBoost",
        "reel": r,
        "row": c + PAD,
        "mult": mult,
        "boosted": [{"reel": a, "row": b + PAD, "name": n, "from": f, "to": t} for a, b, n, f, t in boosted],
        "boardTotal": gs.fill_total(),
    })


def collect_event(gs, cell, kind: str, collected: list, total: float, removed: bool) -> None:
    r, c = cell
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "collect",
        "kind": kind,
        "reel": r,
        "row": c + PAD,
        "collected": [{"reel": a, "row": b + PAD, "name": n, "value": v} for a, b, n, v in collected],
        "total": total,
        "removed": removed,
        "boardTotal": gs.fill_total(),
    })


def zippo_burn_event(gs, cell, burned: list) -> None:
    r, c = cell
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "zippoBurn",
        "reel": r,
        "row": c + PAD,
        "burned": [{"reel": a, "row": b + PAD, "value": v} for a, b, v in burned],
        "boardTotal": gs.fill_total(),
    })


def fillup_end_event(gs, reason: str, spins: int, total: float, win: float) -> None:
    drops, collectors = [], []
    for (r, c), item in sorted(gs.fill_board.items()):
        if item["name"] == "FD":
            drops.append({"reel": r, "row": c + PAD, "value": item["value"]})
        else:
            collectors.append({"reel": r, "row": c + PAD, "name": item["name"], "value": item["value"]})
    gs.book.add_event({
        "index": len(gs.book.events),
        "type": "fillUpEnd",
        "reason": reason,
        "spins": spins,
        "drops": drops,
        "collectors": collectors,
        "boardTotal": total,
        "win": int(round(win * 100)),
    })


# ------------------------------------------------------------------------------ buy modes
def lucky_wheel_event(gs, result: str) -> None:
    """LUCKY PUMP: the wheel's result, first event of the book. "premium" / "midnight": the
    bonus follows (enterBonus bought=true); "none": nothing follows but finalWin 0."""
    gs.book.add_event({"index": len(gs.book.events), "type": "luckyWheel", "result": result})

