# Falcos - game design (v1, 2026-11-09)

Night-time gas station cluster slot. Front end built on the base game's engine, HUD and
black-and-white intro (re-lettered to FALCOS). All art, names, numbers and wording are Falcos's own.
Art direction: art/falcos/STYLE.md.

RTP 96.50% in every mode. Max win 50,000x the bet.

## Board and ways to win

7x7. A cluster is 5 or more matching symbols joined up, down, left or right (diagonals don't count).
It pays by symbol and size (15+ pays the top rate), times its multiplier. After every win the board
tumbles: winners clear, survivors fall, new symbols drop in, and a spin can chain many tumbles.

### Cell multipliers

Every cell has its own multiplier. It starts at x1 and doubles each time a win or a feature hits
that cell, up to x2048. The multiplier belongs to the cell, not the symbol: whatever tumbles into the
cell takes it on. A cluster's multiplier is the sum of the multipliers of its cells that are at x2
or more; if none are, the cluster pays x1. Base game: cells reset every spin. PREMIUM and
MIDNIGHT RUN: cells keep their multipliers for the whole bonus.

## Paying symbols (9) - pays x bet by cluster size

| size | H1 Cash Drawer | H2 Gold Key | H3 Pump Nozzle | H4 Jerry Can | L1 Energy Drink | L2 Slushie | L3 Hot Dog | L4 Chips | L5 Donut |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 1 | 0.8 | 0.5 | 0.4 | 0.3 | 0.3 | 0.2 | 0.2 | 0.2 |
| 6 | 1.5 | 1 | 0.8 | 0.5 | 0.4 | 0.4 | 0.3 | 0.3 | 0.2 |
| 7 | 2 | 1.2 | 1 | 0.8 | 0.5 | 0.5 | 0.4 | 0.4 | 0.3 |
| 8 | 2.5 | 1.5 | 1.2 | 1 | 0.8 | 0.6 | 0.5 | 0.5 | 0.4 |
| 9 | 3 | 2 | 1.5 | 1.2 | 1 | 0.8 | 0.7 | 0.6 | 0.5 |
| 10 | 5 | 4 | 3 | 2 | 1.5 | 1.2 | 1.1 | 1 | 0.9 |
| 11 | 8 | 6 | 4.5 | 3 | 2.5 | 2 | 1.8 | 1.5 | 1.4 |
| 12 | 15 | 12 | 10 | 5 | 4 | 3 | 2.8 | 2.5 | 2.2 |
| 13 | 30 | 25 | 20 | 10 | 8 | 6 | 5.5 | 5 | 4.5 |
| 14 | 60 | 50 | 40 | 20 | 15 | 12 | 11 | 10 | 9 |
| 15+ | 150 | 100 | 60 | 40 | 30 | 25 | 22 | 20 | 18 |

Owner-approved table (2026-11-09). Every pay is in 0.1x steps (the RGS grid), so every win is exact
with no rounding. The RTP is set by the reel strips and the optimiser's weights, not by this table.

Each paying symbol has its own land, idle and win animation and its own soft win sound.

## Feature symbols

Each tumble resolves in order: cluster wins, then all Gas Pumps together, then Scratch Tickets and
Gold Tickets one at a time, then Zippos.

* **Zippo (ZP)** - lights up its 3x3 area: the 8 cells around it and its own cell double their
  multipliers; paying symbols there burn (clear, feeding their doubled multipliers into any cluster
  they were part of). Scatters keep their place but still double. FILL UP: burns every Fuel Drop
  in its 3x3 area (only drops) and disappears.
* **Scratch Ticket (ST)** - scratches off one paying symbol that is on the board; every cell holding
  it doubles and burns, and so does the ticket's cell. FILL UP: an area collector - it collects
  every Fuel Drop in its 8 neighbours (adding their values to its own) plus any collector there that
  activated on an earlier spin; with nothing to collect it is removed, otherwise it stays with its
  total.
* **Gold Scratch Ticket (GT)** - every paying symbol on the board doubles and burns, and so does the
  ticket's cell. FILL UP: a whole-board collector.
* **Gas Pump (GP)** - column feature and the biggest single event; at most one per column. Rolls a
  fuel grade: REGULAR x2 or x4, PLUS x8 or x16, PREMIUM x32 or x64, or **FULL TANK**. REGULAR to
  PREMIUM: every cell in its column gets the pump's multiplier applied and paying symbols in the
  column burn. FULL TANK: every cell in the column becomes a MAX cell, and any cluster touching a MAX
  cell pays the max win. Pumps in different columns fire together. FILL UP: rolls x2-x64 and
  multiplies every Fuel Drop in its column and any collector there that already collected; then it
  leaves.

## Scatters

* **FALCOS Token (BS)** - 3 in the base game -> FILL UP; 4 or more -> PREMIUM.
* **Midnight Token (DS)** - darker, rare. 3 in the base game (or in a FUEL CHANCE spin) -> MIDNIGHT
  RUN. Cannot be bought.

## Bonuses

* **FILL UP** (3 FALCOS Tokens, or buy 100x) - a Fuel Drop collection game with a 3-bar fuel gauge.
  No cell multipliers here. The gauge starts full (3). Every spin uses one bar; any spin that lands
  something new (a drop or a feature) refills it to 3. The bonus ends when the gauge is empty and
  nothing new lands. Fuel Drops are sticky: green x0.2/x0.5/x1/x2/x3, amber x5/x10/x15/x20, red
  x50/x100/x250/x500, and a drop that grows changes colour (green under x5, amber from x5, red from
  x50). Zippos burn drops, Scratch Tickets and Gold Tickets collect them, Gas Pumps multiply them.
  At the end you win the total of every drop left plus every collector's total, times the bet,
  capped at the max win.
* **PREMIUM** (4+ FALCOS Tokens, or buy 300x) - 10 free spins of the base game with sticky cell
  multipliers: a cell that reached x8 keeps x8 into the next spin and keeps growing.
* **MIDNIGHT RUN** (3 Midnight Tokens only) - 10 free spins with sticky cell multipliers, every cell
  starting at x4, and Gas Pumps landing far more often. The biggest bonus in the game.

## Bet modes

| mode | cost | what it is |
|---|---|---|
| base | 1x | normal spin |
| FUEL CHANCE | 3x | one base spin with about 5x the chance of triggering any bonus |
| FILL UP | 100x | buys the collection bonus |
| PREMIUM | 300x | buys the sticky-multiplier free spins |
| NITRO SPIN | 500x | one spin with every cell preloaded with a multiplier from x16 to x2048 |

## Sound

Soft and short: every win and feature sound is musical and gentle, mixed under the music, nothing
harsh or loud.

## Open items

* New math model in math-sdk for all of the above + optimisation to 96.50%: needs the Rust
  toolchain (`cargo`), which is not installed yet.
* Front-end playback of cell multipliers, burns, Gas Pump grades, Fuel Drops and the fuel gauge.
