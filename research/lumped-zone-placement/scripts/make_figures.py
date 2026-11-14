#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figure 2 from out/shift.json (run `study_shift.py` first): the zoned part-peak error of the Lumped against the placement on the raster, for three groups, the program at 0.5 mm, the candidate at 0.5 mm and the program at 0.125 mm.
Usage: python research/lumped-zone-placement/scripts/make_figures.py   (from the repository root)
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)


def main():
    """!
    @brief Draw figure 2.
    @return None.
    """
    d = json.load(open(os.path.join(BASE, "out", "shift.json")))
    groups = [g for g in d if g.startswith(("3x3", "5x5 @1.0", "8x8"))]
    fig, axs = plt.subplots(1, len(groups), figsize=(13, 4), sharey=False)
    for ax, g in zip(axs, groups):
        rows = [r for r in d[g] if r["axis"] in ("x",)]
        k = [r["dx"] / 0.5 for r in rows]
        for key, lab, st in (("program", "program 0.5 mm", "o-"), ("vote+tol", "candidate 0.5 mm", "s-"), ("program@0.125", "program 0.125 mm", "^--"), ("vote+tol@0.25", "candidate 0.25 mm", "d--")):
            ax.plot(k, [r[key]["peak"] for r in rows], st, ms=4, label=lab)
        ax.plot(k, [r["one_peak"] for r in rows], "k:", label="one node")
        ax.set_title(g, fontsize=9)
        ax.set_xlabel("shift along x, in cells of 0.5 mm")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("Lumped part peak against the FVM peak, % of the rise")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    out = os.path.join(BASE, "figures", "fig_02_error_against_shift.png")
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()
