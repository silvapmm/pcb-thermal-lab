"""!
@file study_via_fill.py
@brief What fills a via barrel and how much it matters for heat: open, epoxy resin, conductive paste, electroplated copper.

@details A via is a copper barrel (plating, 25 um by default) around a core that is either open or filled. The conduction along the axis of the barrel is
         k_copper A_equivalent / L with A_equivalent = A_plating + (k_fill / k_copper) pi r_in^2 (`Via.thermal_area`); a copper fill is the whole disc.
         The fabricator's usual "filled via" is an epoxy resin plug (IPC-4761 types V to VII, often capped with plated copper to be solderable), which is almost a heat-wise nothing.
         Part 1 prints the resistance of one via through 1.6 mm; part 2 the maximum temperature of the example board (3 x 3 vias of 0.3 mm under U1) for every fill.

Usage: python research/via-fill/study_via_fill.py   (from the repository root; about 1 minute)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))      # repository root: research/via-fill/ is two levels down

from pcbthermal import SolverOptions, simulate                           # noqa: E402
from pcbthermal.examples import example_board                            # noqa: E402
from pcbthermal.model import VIA_FILLS, Via                              # noqa: E402


def main():
    """!
    @brief Print the resistance of one via and the effect on the example board for every fill.
    """
    k_cu, plating, length = 385.0, 25e-6, 1.6e-3
    print("| Fill | k of the fill (W/mK) | A equivalent (mm²) | R of one 0.3 mm via, 1.6 mm long (K/W) | vs open |")
    print("| :-- | --: | --: | --: | --: |")
    base = None
    for label, k, _note in VIA_FILLS:
        v = Via(0.0, 0.0, 0.3e-3, False, "", k)
        a = v.thermal_area(plating, k_cu)
        r = length / (k_cu * a)
        base = base or r
        print(f"| {label} | {f'{k:g}' if k else '-'} | {a * 1e6:.4f} | {r:.1f} | {100 * (r / base - 1):+.0f} % |")
    print("\n| Fill | example board Tmax (°C) | change vs open (K) |")
    print("| :-- | --: | --: |")
    t0 = None
    for label, k, _note in VIA_FILLS:
        p = example_board()
        for v in p.vias:
            v.filled, v.fill_k = False, k
        t = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max
        t0 = t0 or t
        print(f"| {label} | {t:.2f} | {t - t0:+.2f} |", flush=True)


if __name__ == "__main__":
    main()
