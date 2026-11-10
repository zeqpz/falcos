# Falcos - game design (v1, 2026-11-09)

Night-time gas station cluster slot. Front end built on the base game's engine, HUD and
black-and-white intro (re-lettered to FALCOS). All art, names, numbers and wording are Falcos's own.
Art direction: art/falcos/STYLE.md.

RTP 96.50% in every mode. Max win 50,000x the bet.

## Board and ways to win

7x5: 7 reels (columns) wide and 5 rows tall, 35 cells (owner decision 2026-11-09). A cluster is 5 or more matching symbols joined up, down, left or right (diagonals don't count).
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
| FUEL CHANCE | 3x | one base spin with about 2.2x the chance of triggering any bonus |
| FILL UP | 100x | buys the collection bonus |
| PREMIUM | 300x | buys the sticky-multiplier free spins |
| NITRO SPIN | 500x | one spin with every cell preloaded with a multiplier from x16 to x2048 |
| LUCKY PUMP | 500x | a wheel spins first: PREMIUM (as bought), MIDNIGHT RUN, or nothing (split in Math notes) |

Max win 50,000x the bet in every mode (owner decision 2026-11-09). Every mode's RTP is 96.50%.

## Sound

Soft and short: every win and feature sound is musical and gentle, mixed under the music, nothing
harsh or loud.

## Open items

* Math phase 2 (7x5 retune, optimisation to 96.50%, RGS checks): see Math notes below.
* Front-end playback of cell multipliers, burns, Gas Pump grades, Fuel Drops and the fuel gauge.

## Math notes (phase 2, 2026-11-09)

Model: `math-sdk/games/falcos/` (`game_config.py`, `reels/gen_reels.py`, `game_optimization.py`,
`cap_books.py`). Event contract: `math-sdk/games/falcos/EVENTS.md`. Optimised with the Rust
optimiser; `rgs_verification` and `verify_books.py` run on the published files.

Books: base 100,000, FUEL CHANCE 50,000, FILL UP / PREMIUM / NITRO / LUCKY PUMP 20,000 each.

| mode | RTP | wins | max win (50,000x) | P(win > 100x) | heaviest book | etl10k | 3-star band |
|---|---|---|---|---|---|---|---|
| base | 96.50% | 1 in 2.97 | 1 in 8.0M | 1 in 513 | 1 in 52,700 | 0.02 | pass |
| FUEL CHANCE | 96.50% | 1 in 2.41 | 1 in 1.6M | 1 in 115 | 1 in 22,700 | 0.04 | **fails etl40b (1.93, limit 0.9)** |
| FILL UP | 96.50% | always | 1 in 250,000 | 1 in 3 | 1 in 2,000 | 0.54 | pass |
| PREMIUM | 96.50% | always | 1 in 200,000 | 1 in 2 | 1 in 2,000 | 0.60 | pass |
| NITRO SPIN | 96.50% | 1 in 1.25 | 1 in 200,000 | 1 in 2 | 1 in 2,000 | 0.60 | pass |
| LUCKY PUMP | 96.50% | 1 in 1.11 | 1 in 200,000 | 1 in 2 | 1 in 2,000 | 0.60 | pass |

Bonuses: base FILL UP 1 in 400 (avg 112x), PREMIUM 1 in 2,700 (avg 365x), MIDNIGHT RUN 1 in
14,000 (avg 968x); FUEL CHANCE 2.2x as often (1 in 182 / 1,227 / 6,364; 5x failed the 3-star etl40b limit, trim_chance_tail.py keeps it at 0.84). Bought FILL UP averages 96.5x,
PREMIUM 289.5x. LUCKY PUMP wheel: PREMIUM 55.9% (avg 316x), MIDNIGHT RUN 34.1% (avg 897x),
nothing 10.0%.

Base game as played: a winning spin 1 in 3; base-game wins 5-20x 1 in 75 spins, 20-100x 1 in
430, 100x+ 1 in 5,100; a Zippo fires 1 in 2.8 spins, a Scratch Ticket 1 in 5.1, a Gold Ticket
1 in 36, a Gas Pump REGULAR 1 in 6.9 / PLUS 1 in 20 / PREMIUM 1 in 123; two FALCOS Tokens (tease)
1 in 47, two Midnight Tokens 1 in 242.

7x5 retune (strips and tables):
* Paying-symbol weights skewed harder to the lows (H 3.5/4.5/5.5/6.5, L 12/14.5/17/19.5/23; 7x7
  had H 4.5-7.5, L 12-20); NITRO strip H 1.5-3, L 8-50.
* BR0: FALCOS Tokens 2/1/2/1/2/1/1 per reel (was 1 each), Midnight Tokens 2/1/2 on reels 2/4/6
  (was 1/1/1). Natural rates: FILL UP 1 in ~390, PREMIUM 1 in ~8,000, MIDNIGHT 1 in ~16,000 (the
  published rates are the optimiser's; a PREMIUM rate of 1 in 2,700 by density alone would make
  FILL UP ~1 in 150, so the PREMIUM rate is set by the table, not the strip).
* FR0 (PREMIUM): Zippos 3/3/4/3/4/3/3, Scratch Tickets 3 per reel (were 2 and 2).
* FRM (MIDNIGHT RUN): Zippos 3/2/3/2/3/2/3, Scratch Tickets 2 per reel (were 1 and 1), pumps 3.
* FILL UP: lands FD 45 / ST 3.1 / GT 0.5 / GP 3.7 / ZP 1.2 per 1,000 blanks (was 24 / 2.2 / 0.35
  / 1.6 / 1.4); amber drops a little more often, 250 / 500 drops 0.12 / 0.03 (were 0.25 / 0.08),
  x32 / x64 pumps 1.5 / 0.3 (were 2 / 0.6).
* NITRO cells x16 600, x32 300, x64 80, x128 20, x256 5, x512 1.5, x1024 0.4, x2048 0.1 (were
  680 / 230 / 60 / 20 / 7 / 2.5 / 1 / 0.4).

Tails: the buys' 50,000x and big wins sit in their own optimiser fences with fixed returns
(FILL UP: max win 0.2 bets, 4,000x+ 0.5; PREMIUM / NITRO / LUCKY PUMP: max win 0.25, 10,000x+
0.35; NITRO and LUCKY PUMP also hold 5,000-10,000x at 1.7% / 1.2% of rounds), which keeps etl10k,
etl40b and prob5k inside the 3-star band.
