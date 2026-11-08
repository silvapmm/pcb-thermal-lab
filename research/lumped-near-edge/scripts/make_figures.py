#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the near-edge study from the JSON files of out/ (run the studies first).
@details Figures 3 to 6 of figures/: error against gap, ring means, sub-cell footprint, warning rule rates. Run from the repository root.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "out", ROOT / "figures"
COL = {"program": "#d6342c", "image": "#e0a030", "potlinks": "#2a6fb0"}


def fig_gap():
    """!
    @brief Figure 3: error of the hottest node against the gap, edge and corner, 100 x 80 board, part 5 and 10 mm, edge film 10 and 200.
    @return None.
    """
    r = json.loads((OUT / "edge_sweep.json").read_text())
    fig, ax = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for i, place in enumerate(("edge", "corner")):
        for j, hs in enumerate((10.0, 200.0)):
            a = ax[i][j]
            for side, ls in ((5.0, "-"), (10.0, "--")):
                rows = sorted([x for x in r if x["W"] == 100 and x["place"] == place and x["side"] == side and x["h_side"] == hs], key=lambda x: x["d"])
                for v in ("program", "image", "potlinks"):
                    a.plot([x["d"] for x in rows], [x[v][1] for x in rows], ls, marker="o", ms=3, color=COL[v], label=f"{v}, {side:g} mm")
            a.axhline(0, color="k", lw=0.6)
            a.set_title(f"{place}, edge film {hs:g} W/m2K", fontsize=9)
            a.set_xlabel("gap source - side (mm)")
    ax[0][0].set_ylabel("hottest node, Lumped / FVM - 1 (%)")
    ax[1][0].set_ylabel("hottest node, Lumped / FVM - 1 (%)")
    ax[0][0].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "fig_03_error_against_gap.png", dpi=130)


def fig_rings():
    """!
    @brief Figure 4: ring means, FVM against the Lumped, for the gaps of study_ring_diagnostic.py.
    @return None.
    """
    d = json.loads((OUT / "ring_diagnostic.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    for a, blk in zip(ax, d):
        rows = blk["rows"]
        rho = [x["rho_mm"] for x in rows]
        for v in ("program", "potlinks"):
            a.plot(rho, [100 * (x[v] / x["fvm"] - 1) for x in rows], "o-", color=COL[v], label=v)
        a.axhline(0, color="k", lw=0.6)
        a.set_xscale("symlog", linthresh=1)
        a.set_title(f"gap {blk['gap']:g} mm", fontsize=9)
        a.set_xlabel("mean distance of the ring to the part (mm)")
    ax[0].set_ylabel("ring mean, Lumped / FVM - 1 (%)")
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_ring_means.png", dpi=130)


def fig_subcell():
    """!
    @brief Figure 5: sub-cell footprint, error of the hottest node against the part side for the rasters of study_subcell_raster.py (text table out/subcell_raster.txt).
    @return None.
    """
    rows = []
    for line in (OUT / "subcell_raster.txt").read_text().splitlines()[2:]:
        c = [x.strip() for x in line.strip("|").split("|")]
        rows.append([float(x) for x in c[:6]])
    a = np.array(rows)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for k, (lab, col) in enumerate((("0.5 mm raster", "#d6342c"), ("0.25 mm", "#e0a030"), ("0.125 mm", "#2a6fb0"))):
        for sh, mk in ((0.0, "o"), (0.25, "s")):
            m = a[:, 1] == sh
            ax.plot(a[m, 0], a[m, 2 + k], mk + "-", color=col, ms=4, label=f"{lab}, shift {sh:g}")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("side of the part (mm)")
    ax.set_ylabel("hottest rise, Lumped / FVM 0.0625 - 1 (%)")
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_subcell_raster.png", dpi=130)


def main():
    """!
    @brief Draw the data figures.
    @return None.
    """
    FIG.mkdir(exist_ok=True)
    fig_gap()
    fig_rings()
    fig_subcell()


if __name__ == "__main__":
    main()
