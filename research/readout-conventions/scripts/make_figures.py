#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures: the Biot map and the thick-plate and stack comparison (numbers from study_biot_map.py and study_thick_cases.py).
@details Reads out/biot_map.npz and out/cases.npy (run study_biot_map.py first) and recomputes the plate rows of study_thick_cases.py part 1 from its stored printout values.
         Writes figures/fig_03_biot_map.png and figures/fig_04_plates_stacks.png.
         Usage: .venv/bin/python research/readout-conventions/scripts/make_figures.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402
import numpy as np                                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "figures")
DATA = os.path.join(HERE, "..", "out")

# Printed by study_thick_cases.py part 1 (3D surface, 3D column mean, program node, node + parabola in K above the ambient): kept here so that the figure needs no 1 minute run.
PLATES = [("2 mm Cu\nh 1000, a 4", 9.581, 8.554, 8.553, 9.643), ("1.5 mm Al\nh 2000, a 4", 17.589, 15.508, 15.476, 17.611), ("3 mm Cu, air\nh 20, a 20", 40.212, 40.198, 40.199, 40.213),
          ("10 mm Al\nh 5000, a 10", 16.457, 9.645, 9.606, 18.295), ("case 2\n10 mm k150, a 10", 33.434, 28.939, 28.962, 34.645), ("10 mm k50\nh 400, a 4", 37.831, 17.525, 17.495, 59.385)]
# Part 3 (K above the ambient): top surface, whole-stack mean, base mean.
STACKS = [("Al MCPCB\n35um/100um k2/1.5mm Al", 15.41, 6.72, 6.23), ("Al MCPCB\n35um/75um k1/1.5mm Al", 18.68, 6.64, 6.05), ("Al MCPCB\n70um/100um k2/3mm Al", 12.00, 4.00, 3.67), ("FR-4 1.6 mm\n2 layers", 201.16, 158.60, 118.80)]


def fig_map():
    """!
    @brief Figure 3: the Biot map with contours and the typical cases.
    @return None.
    """
    d = np.load(os.path.join(DATA, "biot_map.npz"))
    c = np.load(os.path.join(DATA, "cases.npy"))
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    levels = [0.001, 0.01, 0.05, 0.2, 0.4]
    cs = ax.contourf(d["BI"], d["TA"], d["g5"] * 100, levels=[0, 0.1, 1, 5, 20, 40, 80], cmap="YlOrRd", extend="neither")
    ax.contour(d["BI"], d["TA"], d["g5"], levels=[0.001, 0.01, 0.05, 0.2], colors="k", linewidths=0.6)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for i, (bi, ta, f) in enumerate(c):
        ax.plot(bi, ta, "o", color="#1b4965", ms=6)
        ax.annotate(str(i + 1), (bi, ta), xytext=(4, 4), textcoords="offset points", fontsize=9, color="#1b4965", weight="bold")
    ax.set_xlabel("Bi = h t / k   (film on the cooled face)")
    ax.set_ylabel("t / a   (thickness over source side)")
    fig.colorbar(cs, label="(surface - column mean) / surface rise, %")
    names = ["35 um Cu on FR-4", "105 um Cu on FR-4", "2 mm Cu core", "1.5 mm Al MCPCB base", "case 2 (10 mm k150)", "10 mm Al cold plate", "3 mm Cu spreader, air", "10 mm k50, 4 mm source"]
    ax.text(1.02, -0.18, "   ".join(f"{i + 1} {n}" for i, n in enumerate(names[:4])) + "\n" + "   ".join(f"{i + 5} {n}" for i, n in enumerate(names[4:])), transform=ax.transAxes, fontsize=7.5, ha="right")
    ax.set_title("When the surface differs from the mean: plate 5 a wide, centre of a square source")
    fig.savefig(os.path.join(OUT, "fig_03_biot_map.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_bars():
    """!
    @brief Figure 4: plates (surface, mean, node, node + parabola) and stacks (surface against the whole-stack mean).
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axs[0]
    x = np.arange(len(PLATES))
    for j, (lab, col) in enumerate([("3D surface", "#c1121f"), ("3D column mean", "#2a9d8f"), ("program node", "#1b4965"), ("node + parabola", "#e9c46a")]):
        ax.bar(x + (j - 1.5) * 0.2, [100 * p[1 + j] / p[1] for p in PLATES], 0.2, label=lab, color=col)
    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in PLATES], fontsize=8)
    ax.set_ylabel("temperature rise, % of the 3D surface rise")
    ax.legend(fontsize=8)
    ax.set_title("One-layer plates, source at the centre")
    ax = axs[1]
    x = np.arange(len(STACKS))
    for j, (lab, col) in enumerate([("top surface (probe)", "#c1121f"), ("mean of the whole stack", "#8d99ae"), ("mean of the base", "#2a9d8f")]):
        ax.bar(x + (j - 1) * 0.27, [100 * s[1 + j] / s[1] for s in STACKS], 0.27, label=lab, color=col)
    ax.set_xticks(x)
    ax.set_xticklabels([s[0] for s in STACKS], fontsize=7)
    ax.set_ylabel("% of the top surface rise")
    ax.legend(fontsize=8)
    ax.set_title("Stacks: a single 'effective board' mean is not the surface")
    fig.savefig(os.path.join(OUT, "fig_04_plates_stacks.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_map()
    fig_bars()
