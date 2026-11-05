#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the investigation: the footprint weights on the cells, the temperature of the top layer around the via (program against the candidates) and the via effect against the cell.
@details Figures 04 to 06 of figures/ (01 to 03 are drawn by make_diagrams.py). Runs the program on the documented 30 x 30 mm board (about 10 s) and reads `out/variants.json`
         (written by study_variants.py) for figure 06.
         Files: fig_04_footprint_weights.png, fig_05_top_layer_around_the_via.png, fig_06_via_effect_against_cell.png.
         Usage: python research/via-partial-copper/scripts/make_figures.py   (from the repository root, after study_variants.py).
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib                                                            # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402
import numpy as np                                                           # noqa: E402

import viavariants as vv                                                     # noqa: E402
from test_maximum_principle import copper_edge_board, network                # noqa: E402

OUT = HERE.parent / "figures"


def fig_weights(path):
    """!
    @brief Footprint weights of the via of the documented board on the 0.25 mm cells: the program (equal) and the sheet-weighted (copper only), over the copper map.
    @param path Output file.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    for ax, variant in zip(axs, ("current", "sheet")):
        p = copper_edge_board()
        with vv.patched(variant):
            net = network(p, "fvm", 0.25)
        j0, i0 = 56, 56
        sl = (slice(i0, i0 + 8), slice(j0, j0 + 8))
        fill = (net.S[0] / net.cover > 0.2 * net.S[1, 60, 60] / net.cover[60, 60]).astype(float)       # copper where the sheet conductance is above 20 % of the full-copper value
        ax.imshow(fill[sl], origin="lower", cmap="Oranges", vmin=0, vmax=1.6, extent=(j0, j0 + 8, i0, i0 + 8))
        from pcbthermal import viawell as vw
        v = p.vias[0]
        if variant == "current":
            w, _, _ = vw.footprint(v.x, v.y, v.diameter / 2, net.dx, 0.0, net.cover, net.dy, 0.0)
        else:
            rel = net.S[0] / net.cover
            w, _, _ = vv._layer_weights(v, net.dx, net.dy, 0.0, 0.0, net.cover, rel, "sheet", v.diameter / 2)
        for (i, j), x in w.items():
            ax.text(j + 0.5, i + 0.5, f"{x:.2f}", ha="center", va="center", fontsize=11, color="k", fontweight="bold")
            ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=False, edgecolor="k", linewidth=1.5))
        ax.plot([v.x / net.dx], [v.y / net.dy], "o", color="#7a4b12", markersize=5)
        ax.set_title(("program: equal weights on the 4 cells" if variant == "current" else "sheet-weighted: weights follow the copper") + "\n(top layer, 0.25 mm cells, orange = copper)", fontsize=9)
        ax.set_xticks(range(j0, j0 + 9))
        ax.set_yticks(range(i0, i0 + 9))
        ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_field(path):
    """!
    @brief Temperature of the top copper layer near the via at 0.25 mm: the program (cold column through the footprint), the sheet-weighted weights and the star; and a row profile through the via.
    @param path Output file.
    @return None.
    """
    fig, axs = plt.subplots(1, 4, figsize=(17, 4.4), gridspec_kw={"width_ratios": [1, 1, 1, 1.4]}, layout="constrained")
    prof = {}
    for ax, variant in zip(axs[:3], ("current", "sheet", "star")):
        p = copper_edge_board()
        with vv.patched(variant):
            net = network(p, "fvm", 0.25)
            th, _ = net.solve_steady()
        sl = (slice(52, 68), slice(50, 70))
        im = ax.imshow(th[0][sl] + p.board.ambient, origin="lower", cmap="inferno", extent=(50 * 0.25, 70 * 0.25, 52 * 0.25, 68 * 0.25), vmin=100, vmax=180)
        ax.set_title(f"{variant}: top copper layer, T in degC\n(a column of cells 40 to 60 K colder than both sides)" if variant == "current" else f"{variant}: top copper layer, T in degC", fontsize=8.5)
        ax.set_xlabel("x in mm", fontsize=8)
        ax.axvline(15.0, color="w", linewidth=0.6, linestyle=":")
        prof[variant] = th[0][59, 40:80] + p.board.ambient
    xs = (np.arange(40, 80) + 0.5) * 0.25
    for k, v in prof.items():
        axs[3].plot(xs, v, label=k, linewidth=1.8)
    axs[3].axvline(15.0, color="k", linewidth=0.6, linestyle=":")
    axs[3].set_xlabel("x in mm (row through the via, copper ends at the dotted line)", fontsize=8)
    axs[3].set_ylabel("T in degC", fontsize=8)
    axs[3].legend(fontsize=8)
    axs[3].set_title("profile through the via centre", fontsize=8.5)
    fig.colorbar(im, ax=axs[:3], fraction=0.03, label="T in degC")
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_effect(path):
    """!
    @brief The via effect against the cell: the documented board (variants and the 3D solid) and the error of the program on the 10 mm cases.
    @param path Output file.
    @return None.
    """
    cells = [1.0, 0.5, 0.25, 0.125]
    eff = {}
    for variant in ("current", "sheet", "plane", "star"):
        row = []
        for c in cells:
            vals = []
            for wv in (True, False):
                p = copper_edge_board()
                if not wv:
                    p.vias = []
                with vv.patched(variant):
                    net = network(p, "fvm", c)
                    th, _ = net.solve_steady()
                vals.append(float(th[:2].max()))
            row.append(vals[1] - vals[0])
        eff[variant] = row
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    for k, v in eff.items():
        axs[0].plot(cells, v, "o-", label=f"FVM {k}")
    axs[0].plot(cells, [0.70, 2.86, 7.20, 10.74], "ks--", label="3D solid (not converged)")
    axs[0].set_xscale("log")
    axs[0].invert_xaxis()
    axs[0].set_xlabel("cell in mm")
    axs[0].set_ylabel("via effect on the maximum temperature in K")
    axs[0].set_title("Documented board (30 x 30 mm, 2 W): via effect against the cell", fontsize=9)
    axs[0].legend(fontsize=8)
    data = json.load(open(HERE.parent / "out" / "variants.json"))
    names = ["edge delta=0.0", "edge delta=0.3", "track width=0.4", "track width=1.0", "island side=1.2", "bare"]
    width = 0.2
    for k, variant in enumerate(("current", "sheet", "plane", "star")):
        vals = [data[f"{n}|fvm|{variant}|0.25"]["err_pct"] for n in names]
        axs[1].bar(np.arange(len(names)) + (k - 1.5) * width, vals, width, label=variant)
    axs[1].set_xticks(np.arange(len(names)))
    axs[1].set_xticklabels([n.replace(" ", "\n", 1) for n in names], fontsize=7)
    axs[1].axhline(0, color="k", linewidth=0.7)
    axs[1].set_ylabel("error of the via effect against the 3D solid at 1/20 mm, %")
    axs[1].set_title("10 x 10 mm cases at 0.25 mm (FVM)", fontsize=9)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the data figures.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_weights(OUT / "fig_04_footprint_weights.png")
    fig_field(OUT / "fig_05_top_layer_around_the_via.png")
    fig_effect(OUT / "fig_06_via_effect_against_cell.png")


if __name__ == "__main__":
    main()
