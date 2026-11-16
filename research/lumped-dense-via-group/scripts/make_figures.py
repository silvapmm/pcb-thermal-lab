#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures from the data of study 2 (out/sweep.json): the errors of the zoned and the one-node Lumped part peak against the core share and against the via pitch.
@details fig_03: left, error of the part peak against the FVM (percent of its rise) versus the share of the footprint the core covers, zoned and one node, for the cases where the zones apply;
         right, the same versus the mean nearest-neighbour distance of the vias in the footprint. Open symbols are four-layer boards.
Usage: python research/lumped-dense-via-group/scripts/make_figures.py   (from the repository root; run study_sweep.py --grid first)
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    """!
    @brief Draw fig_03.
    @return None.
    """
    rows = [r for r in json.load(open(os.path.join(ROOT, "out", "sweep.json"))) if r["zoned"][0]]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, key, lab in ((axs[0], "share", "core share of the footprint (cells, 0.5 mm raster)"), (axs[1], "d_nn", "mean nearest-neighbour distance of the vias in the footprint (mm)")):
        for four, mk in ((False, "o"), (True, "s")):
            sel = [r for r in rows if (r["kw"].get("layers", 2) == 4) == four]
            x = [r["core"][key] for r in sel]
            ax.scatter(x, [r["zoned_peak"][0] for r in sel], marker=mk, color="#2c6fb0", label=f"zoned Lumped, {'4' if four else '2'} layers", facecolors='none' if four else '#2c6fb0')
            ax.scatter(x, [r["one_peak"][0] for r in sel], marker=mk, color="#c0392b", label=f"one-node Lumped, {'4' if four else '2'} layers", facecolors='none' if four else '#c0392b')
        ax.axhline(0, c="k", lw=0.6)
        ax.set_xlabel(lab); ax.set_ylabel("part peak against the FVM (% of its rise)"); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.suptitle("Part over a via group on 100 x 80 mm boards, 3 W, FVM at 0.5 mm as the reference (the no-via board reads -0.2 to -2.7 % in the same units)", fontsize=9)
    fig.savefig(os.path.join(ROOT, "figures", "fig_03_error_against_core_share_and_pitch.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
