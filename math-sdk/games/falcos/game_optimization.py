"""PROVISIONAL optimisation targets for Falcos (phase 2 tunes these with the Rust optimiser).

Every mode RTP 0.965 (inside the 96.00-96.70% band, the owner's 96.50%). rtp values are shares of
the MODE'S COST (as in the previous game): a criteria returning R base bets in a mode costing c is
asked as R / c. Each criteria's implied average win (rtp x hr x cost) sits near its simulated
pool mean (sim_stats.py, phase 1 raw pools):

    pool means (natural)        FILL UP ~99x | PREMIUM ~265x | MIDNIGHT RUN ~1,000x
                                NITRO ~525x a spin | base winning spin ~2.85x

    base     wincap .003 (1 in ~8.3M) | midnight .07 (1 in 15,000, ~1,050x) | premium .10
             (1 in 2,700, ~270x) | fillup .22 (1 in 450, ~99x) | basegame .572 (hr 2.8) | 0
    chance   (cost 3) the bonus criteria 5x as often at the same average win: rtp x 5 / 3;
             basegame takes the rest (its spins then average ~2.6x - inside the pool's 2.85x)
    fillup   wincap .002 | fillup .963
    premium  wincap .004 | premium .961
    nitro    wincap .02 | nitro .945 | 0

Max win must be reachable more often than ~1 in 10M (base .003 -> 1 in 8.3M). The risk/ETL
picture of the 500x NITRO buy needs a look in phase 2 (see EVENTS.md / the phase-1 report).
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)

CHANCE_BONUS = 5.0
CHANCE_COST = 3.0

BASE_SPLIT = {"wincap": 0.003, "midnight": 0.07, "premium": 0.10, "fillup": 0.22}
BASE_HR = {"midnight": 15000, "premium": 2700, "fillup": 450}


def _params(test_spins, test_weights):
    return ConstructParameters(
        num_show=1500, num_per_fence=2000, min_m2m=1, max_m2m=400, pmb_rtp=1.0,
        sim_trials=5000, test_spins=test_spins, test_weights=test_weights, score_type="rtp",
    ).return_dict()


class OptimizationSetup:
    """Handle all game mode optimisation parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        rtp = game_config.rtp
        cap = game_config.wincap

        def spin_conditions(k: float, c: float) -> dict:
            split = {name: round(v * k / c, 6) for name, v in BASE_SPLIT.items()}
            out = {
                "wincap": ConstructConditions(rtp=split["wincap"], av_win=cap, search_conditions=cap).return_dict(),
                "midnight": ConstructConditions(rtp=split["midnight"], hr=BASE_HR["midnight"] / k,
                                                search_conditions={"symbol": "midnight"}).return_dict(),
                "premium": ConstructConditions(rtp=split["premium"], hr=BASE_HR["premium"] / k,
                                               search_conditions={"symbol": "premium"}).return_dict(),
                "fillup": ConstructConditions(rtp=split["fillup"], hr=BASE_HR["fillup"] / k,
                                              search_conditions={"symbol": "fillup"}).return_dict(),
                "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                "basegame": ConstructConditions(hr=2.8, rtp=round(rtp - sum(split.values()), 6)).return_dict(),
            }
            return out

        buy = lambda cap_rtp, name: {  # noqa: E731
            "wincap": ConstructConditions(rtp=cap_rtp, av_win=cap, search_conditions=cap).return_dict(),
            name: ConstructConditions(rtp=round(rtp - cap_rtp, 6), hr="x").return_dict(),
        }
        nitro = buy(0.02, "nitro")
        nitro["0"] = ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict()

        self.game_config.opt_params = {
            "base": {"conditions": spin_conditions(1.0, 1.0), "scaling": ConstructScaling([]).return_dict(),
                     "parameters": _params([50, 100, 200], [0.3, 0.4, 0.3])},
            "chance": {"conditions": spin_conditions(CHANCE_BONUS, CHANCE_COST),
                       "scaling": ConstructScaling([]).return_dict(),
                       "parameters": _params([50, 100, 200], [0.3, 0.4, 0.3])},
            "fillup": {"conditions": buy(0.002, "fillup"), "scaling": ConstructScaling([]).return_dict(),
                       "parameters": _params([10, 20, 50], [0.6, 0.2, 0.2])},
            "premium": {"conditions": buy(0.004, "premium"), "scaling": ConstructScaling([]).return_dict(),
                        "parameters": _params([10, 20, 50], [0.6, 0.2, 0.2])},
            "nitro": {"conditions": nitro, "scaling": ConstructScaling([]).return_dict(),
                      "parameters": _params([10, 20, 50], [0.6, 0.2, 0.2])},
        }
        verify_optimization_input(self.game_config, self.game_config.opt_params)
