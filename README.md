# Falcos

A night gas-station cluster slot for Stake Engine: 7x5 board, cluster pays, RTP 96.50% in every mode, max win
50,000x. Rules and design: [FALCOS_DESIGN.md](FALCOS_DESIGN.md).

## Layout

| Part | Where | What |
| --- | --- | --- |
| Front end | `frontend/` | visuals, UI, animation, sound (`index.html`, `rgs.js`, `rules.js`, `scenefx.js`, `boardgl.js`, `assets/`). No outcome math. |
| Math | `math-sdk/games/falcos/` | game config, reel strips, simulation, optimisation, published books and lookup tables (`library/publish_files`). Event contract: `EVENTS.md`. |
| Local RGS | `rgs/mock_rgs.py` | a stand-in for the Stake Engine RGS, for testing only: draws a weighted book per bet and serves `frontend/`. |
| Art and build tools | `tools/falcos/`, `art/falcos/` | the art pipeline (OpenRouter generation, Blender animation, packing, compression). |

Every bet is stateless: one `/play` returns the whole, already-resolved round and `/end-round` pays it.

## Play it locally

Double-click `Play Falcos.command`, or:

```bash
.venv/bin/python rgs/mock_rgs.py
```

then open http://localhost:8733/index.html?sessionID=test&rgs_url=http://localhost:8733&lang=en&device=desktop
