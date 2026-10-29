#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_air_data.py
@brief The published measurements of the average Nusselt number of an isothermal vertical plate in air against each level: which level do the data support, and can they tell the levels apart?

@details The points are the three air data sets of Churchill and Chu (1975) (King, Cheesewright, Jakob) as redrawn in Figure 6 of A. G. Jaffer, "Natural Convection Heat
         Transfer From an Isothermal Plate", arXiv:2201.02612v6 (2023), page 15. Jaffer captured them from the graphs of Churchill and Chu with a digitising program (his Section 2, page 4); the numbers
         below are the centres of the markers read from the **vector drawing of that figure** (so the second step adds no more than the 0.3 % of the axis reading), and they are
         therefore **plot values** of a secondary source, not the measured tables of King (1932), Cheesewright (1968) or Jakob. Pr 0.70 (the figure's value). Counts agree with the
         Table 6 of Jaffer (8, 6 and 5 points). The mercury set of Saunders (Pr 0.024) is not used.

         For each level the ratio data / level is formed point by point; the mean ratio (bias), the standard deviation of the ratios (scatter) and the root mean square of (ratio - 1) are
         printed for the points with Ra < 1e9 (laminar range) and for the points between 1e4 and 1e8 (the range of PCBs and finned blocks, Ra 6e4 to 3e7 for 40 to 200 mm).

         Run: .venv/bin/python research/plate-h-level/scripts/study_air_data.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                        # noqa: E402

# (Ra, Nu) plot values of Figure 6 of Jaffer (arXiv:2201.02612v6, page 15), air, Pr 0.70
KING = [(3647.7, 4.908), (10449.3, 6.106), (11552.2, 6.675), (304073.9, 14.596), (2527350.0, 23.005), (25838561.4, 40.814), (133419961.4, 80.883), (147187622.1, 70.433)]
CHEESEWRIGHT = [(7025.1, 4.145), (42936.7, 6.543), (672777.5, 14.153), (74175502.2, 49.307), (774712310.2, 91.045), (1537217745.8, 109.825)]
JAKOB = [(21186181.9, 39.275), (4201477821.5, 189.527), (35598798534.9, 390.907), (353232167258.4, 845.636), (1022714416142.7, 1207.98)]
SETS = {"King": KING, "Cheesewright": CHEESEWRIGHT, "Jakob": JAKOB}
PR = 0.70
LEVELS = ("general", "laminar", "bl", "bl_le", "mcadams")


def stats(points, level):
    """!
    @brief Bias, scatter and RMSRE of data / level.
    @param points List of (Ra, Nu).
    @param level A level of levels.LEVELS.
    @return tuple (n, mean ratio, standard deviation of the ratio, root mean square of (ratio - 1)).
    """
    if not points:
        return 0, float("nan"), float("nan"), float("nan")
    r = np.array([nu / float(L.nu_level(level, ra, PR)) for ra, nu in points])
    return len(r), float(r.mean()), float(r.std()), float(np.sqrt(np.mean((r - 1.0) ** 2)))


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    allp = [p for s in SETS.values() for p in s]
    windows = (("Ra < 1e9 (laminar range)", lambda ra: ra < 1e9), ("1e4 <= Ra <= 1e8 (PCB range)", lambda ra: 1e4 <= ra <= 1e8), ("Ra < 1e4", lambda ra: ra < 1e4))
    for title, sel in windows:
        print(f"\nData / level, air, {title}: n, mean ratio (bias), std (scatter), RMSRE")
        print("| set | n | " + " | ".join(L.LABELS[k] for k in LEVELS) + " |")
        print("| :-- | --: | " + " | ".join("--:" for _ in LEVELS) + " |")
        for name, pts in list(SETS.items()) + [("all air", allp)]:
            sub = [p for p in pts if sel(p[0])]
            if not sub:
                continue
            cells = []
            for k in LEVELS:
                n, m, s, e = stats(sub, k)
                cells.append(f"{m:.3f} / {s:.3f} / {100 * e:.1f} %")
            print(f"| {name} | {len(sub)} | " + " | ".join(cells) + " |")
    print("\nPoint by point, air, Ra < 1e9: ratio data / level")
    print("| set | Ra | Nu data | " + " | ".join(L.LABELS[k] for k in LEVELS) + " |")
    print("| :-- | --: | --: | " + " | ".join("--:" for _ in LEVELS) + " |")
    for name, pts in SETS.items():
        for ra, nu in pts:
            if ra < 1e9:
                print(f"| {name} | {ra:.3g} | {nu:.2f} | " + " | ".join(f"{nu / float(L.nu_level(k, ra, PR)):.3f}" for k in LEVELS) + " |")
    # How many points would it take to tell 0.59 from the laminar form? The two differ by 1.3 to 13 % over the range; the scatter of a set is a few to 10 %.
    print("\nSpread between sets (mean ratio to the laminar form, 1e4 <= Ra <= 1e8): " + ", ".join(
        f"{name} {stats([p for p in pts if 1e4 <= p[0] <= 1e8], 'laminar')[1]:.3f}" for name, pts in SETS.items() if any(1e4 <= p[0] <= 1e8 for p in pts)))


if __name__ == "__main__":
    main()
