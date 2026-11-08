#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_seri_lee.py
@brief The published plate of Seri Lee (aluminium 100 x 100 x 1.3 mm, 25 mm source, 1 K/W film) with the Lumped as the program has it and with the candidate, against the exact thin-plate series.
@details The exact series (research/published-cases-followup/lib/plate_series.py, read from the checkout PCBT_TREE) is the independent reference; the printed values are 0.66 (centre), 1.29 (edge
         midpoint) and 2.38 K/W (corner), Seri Lee, Electronics Cooling, January 1998 (as quoted by research/published-cases-followup 7; the article was not re-opened here). Rc = hottest or mean source
         temperature minus the mean film-face temperature, per watt. Run from the repository root with PCBT_TREE set.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402
sys.path.insert(0, str(B.tree.ROOT / "research" / "published-cases-followup" / "lib"))
sys.path.insert(0, str(B.tree.ROOT / "research" / "published-cases-followup" / "scripts"))
import plate_series as PS  # noqa: E402
from pcbthermal import Problem, SolverOptions, analysis, simulate  # noqa: E402
from pcbthermal.model import Materials  # noqa: E402

SIDE, THICK, K, R0 = 0.1, 1.3e-3, 200.0, 1.0
H = 1.0 / (R0 * SIDE * SIDE)


def lumped_rc(gx, gy, variant, cell=1.0):
    """!
    @brief Rc of the Lumped variant for a source at gaps gx, gy.
    @param gx Gap to the left side in mm.
    @param gy Gap to the bottom side in mm.
    @param variant Variant name.
    @param cell Cell in mm.
    @return (Rc on the hottest point, Rc on the footprint mean) in K/W.
    """
    p = Problem.new(100.0, 100.0, layers=2, thickness_mm=1.301, copper_um=650.0, ambient=0.0, h_top=0.0, h_bottom=H, h_side=0.0,
                    materials=Materials(k_copper=K, k_fr4_through=0.3, k_fr4_inplane=0.9))
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(gx, gy, gx + 25.0, gy + 25.0), name="U")
    V.install(variant)
    res = simulate(p, SolverOptions(models=("lumped",), cell_mm=cell)).results["lumped"]
    st = analysis.heater_stats(res, p)[0]
    film = float(np.asarray(res.T)[-1].mean())
    return float(st["t_max"] - film), float(st["t_mean"] - film)


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| position | printed | exact series (max / mean) | program: max % / mean % | image % | potlinks: max % / mean % |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, gx, gy, pr in (("centre", 37.5, 37.5, 0.66), ("edge midpoint", 0.0, 37.5, 1.29), ("edge, gap 6 mm", 6.0, 37.5, None), ("edge, gap 12 mm", 12.0, 37.5, None), ("corner", 0.0, 0.0, 2.38), ("corner, gap 6 mm", 6.0, 6.0, None)):
        r = tuple(v * 1e-3 for v in (gx, gy, gx + 25.0, gy + 25.0))
        o = PS.source_rise(SIDE, K * THICK, H, r, 1.0)
        ex = (o["rc"], o["rc_mean"])
        v = {n: lumped_rc(gx, gy, n) for n in ("program", "image", "potlinks")}
        f = lambda a: f"{100 * (a[0] / ex[0] - 1):+.1f} / {100 * (a[1] / ex[1] - 1):+.1f}"
        print(f"| {name} | {pr if pr else '-'} | {ex[0]:.3f} / {ex[1]:.3f} | {f(v['program'])} | {f(v['image'])} | {f(v['potlinks'])} |", flush=True)


if __name__ == "__main__":
    main()
