#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the adoption study: the footprint cut into the rest A and the core C with the 2.4.5 wells, the network of two layers with the places where the cluster well and the A-C link could count the same heat twice, the strided decimation of the footprint potentials against blocks, and the raster cell against the core.
@details Figures 01 to 04 of figures/ (the data figures are drawn by make_figures.py). No study is run and nothing is imported from the program: only geometry is drawn.
         Files: fig_01_footprint_zones_and_wells.png, fig_02_network_two_layers_double_count.png, fig_03_decimation_stride_vs_blocks.png, fig_04_raster_against_core.png.
         Usage: python research/lumped-zones-adoption/scripts/make_diagrams.py   (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_footprint(path):
    """!
    @brief Section and plan of a footprint with a via core: the zones, the barrels with their micro wells, the cluster well of 2.4.5 and the paths of the heat.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(14, 5.4, 1, 2, ratios=[1.5, 1])
    a.set_xlim(0, 15)
    a.set_ylim(-1.6, 7.6)
    ys = [5.4, 3.5, 1.6]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 14, 0.25, dk.COPPER)
        a.text(14.7, y + 0.12, f"plane {k + 1}", fontsize=7, va="center", ha="right")
        if k < 2:
            dk.layer(a, 0.5, y - 1.65, 14, 1.65, dk.FR4)
    a.add_patch(Rectangle((3.0, 5.75), 9.0, 0.45, facecolor="#444444", edgecolor="k"))
    a.text(7.5, 5.98, "part: uniform power over the footprint", color="white", fontsize=7.5, ha="center", va="center")
    for x in (6.2, 6.9, 7.5, 8.1, 8.8):
        a.add_patch(Rectangle((x - 0.07, 1.6), 0.14, 4.05, facecolor=dk.COPPER, edgecolor="k", linewidth=0.6))
        a.add_patch(Circle((x, 5.5), 0.33, fill=False, edgecolor=dk.BLUE, linewidth=0.8, linestyle="--"))
    a.text(7.5, 6.62, "micro wells: one Krogh cell around each barrel (in series with the barrel, in every plane)", fontsize=7, ha="center", color=dk.BLUE)
    a.plot([5.7, 5.7], [0.9, 7.2], "k:", lw=0.8)
    a.plot([9.3, 9.3], [0.9, 7.2], "k:", lw=0.8)
    a.plot([5.7, 9.3], [0.9, 0.9], color="#7a0000", lw=1.2)
    a.text(7.5, 1.05, "cluster (macro) well: the group as one disc, radius capped at 0.75 fin lengths", fontsize=7, ha="center", color="#7a0000", va="bottom")
    a.text(7.5, 7.15, "core C", ha="center", fontsize=8, fontweight="bold")
    a.text(3.9, 7.15, "rest A", ha="center", fontsize=8, fontweight="bold")
    a.text(11.1, 7.15, "rest A", ha="center", fontsize=8, fontweight="bold")
    for x0, x1 in ((3.3, 5.5), (11.7, 9.5)):
        dk.arrow(a, x0, 5.15, x1, 5.15, color=dk.HEAT, width=1.5)
    # the label sits under the sideways arrows on a white box, so that the arrows down through the dielectric do not run through the text
    a.text(4.1, 4.6, "link A-C\n(sideways)", fontsize=7, color=dk.HEAT, ha="center", va="center", bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    a.text(10.9, 4.6, "link A-C\n(sideways)", fontsize=7, color=dk.HEAT, ha="center", va="center", bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    for x in (3.6, 4.6, 10.4, 11.4):
        dk.arrow(a, x, 5.3, x, 4.0, color=dk.BLUE, width=1.3)
    a.text(1.7, 4.2, "straight down\nthrough the\ndielectric of A", fontsize=7, color=dk.BLUE, ha="center")
    a.text(7.5, -0.5, "the question of the study: the macro well and the link A-C both describe heat converging on the core", fontsize=7.5, ha="center", color="#7a0000")
    a.text(7.5, -1.2, "inside the zones the macro well is dropped (Z_none) or kept (Z_cap); the study measures which one fits", fontsize=7.5, ha="center", color="#7a0000")
    b.set_xlim(0, 10)
    b.set_ylim(0, 10)
    b.set_aspect("equal")
    b.add_patch(Rectangle((0.5, 0.5), 9.0, 9.0, facecolor="#f4f4f4", edgecolor="k"))
    b.add_patch(Rectangle((1.5, 1.5), 7.0, 7.0, facecolor="#ffd9d0", edgecolor="k", linewidth=1.4))
    b.add_patch(Rectangle((3.4, 3.4), 3.2, 3.2, facecolor="#f2b27a", edgecolor="k", linewidth=1.4))
    for i in range(5):
        for j in range(5):
            b.add_patch(Circle((3.7 + 0.6 * i, 3.7 + 0.6 * j), 0.12, facecolor="#7a4b13", edgecolor="k", linewidth=0.5))
    b.text(5.0, 2.45, "A", fontsize=12, ha="center", fontweight="bold")
    b.text(5.0, 7.55, "A", fontsize=12, ha="center", fontweight="bold")
    b.text(5.0, 0.95, "rings outside the footprint (as in the program)", fontsize=7.5, ha="center")
    b.text(5.0, 9.0, "plan: footprint, core (0.7071 d_nn around the vias), rings", fontsize=8, ha="center")
    dk.save(fig, path)


def _node(ax, x, y, text, color="#cfe3f5"):
    """!
    @brief A circular node with a label.
    @param ax Axes.
    @param x Centre x.
    @param y Centre y.
    @param text Label.
    @param color Fill.
    @return None.
    """
    ax.add_patch(Circle((x, y), 0.32, facecolor=color, edgecolor="k", linewidth=1.0))
    ax.text(x, y, text, ha="center", va="center", fontsize=7.5)


def fig_network(path):
    """!
    @brief The network of two layers with the zones: nodes A, C and ring 1 in each layer, the link A-C, the dielectric, the barrel with its wells (micro, and the macro well that may count twice).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(11, 5.6)
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.8, 5.8)
    xs = {"A": 2.0, "C": 5.4, "r1": 8.6}
    for l, y in ((1, 4.0), (2, 1.2)):
        for k, x in xs.items():
            _node(ax, x, y, f"{k}{l}" if k != "r1" else f"R{l}", color="#f8d9c8" if k == "A" else "#f2b27a" if k == "C" else "#cfe3f5")
        dk.resistor(ax, 2.35, 5.05, y, "R_AC (logarithmic potential)" if l == 1 else "", color=dk.HEAT)
        dk.resistor(ax, 5.75, 8.25, y, "ring-to-ring (as program)" if l == 1 else "")
        ax.plot([2.0, 2.0], [y + 0.32, y + 0.7], "k", lw=1)
        ax.plot([2.0, 8.6], [y + 0.7, y + 0.7], "k", lw=0.8, alpha=0.5)
        ax.text(0.1, y, f"layer {l}", fontsize=8)
    ax.text(3.5, 4.75, "A to ring 1 also: annulus resistance + half ring (arc over C)", fontsize=7, ha="center")
    # dielectric under A and under ring 1, barrels under C
    ax.plot([2.0, 2.0], [3.68, 1.52], "k", lw=1.2)
    ax.text(2.1, 2.6, "dielectric\n(A)", fontsize=7)
    ax.plot([8.6, 8.6], [3.68, 1.52], "k", lw=1.2)
    ax.text(8.7, 2.6, "dielectric\n(ring 1)", fontsize=7)
    # core: dielectric + wells in series with the barrel
    ax.plot([5.4, 5.4], [3.68, 3.2], "k", lw=1.2)
    ax.add_patch(Rectangle((5.25, 2.1), 0.3, 1.1, facecolor=dk.COPPER, edgecolor="k"))
    ax.text(5.7, 2.65, "barrel\n(Kron reduced)", fontsize=7)
    ax.plot([5.4, 5.4], [2.1, 1.52], "k", lw=1.2)
    ax.text(4.3, 3.0, "micro wells (plane to barrel,\nin series with the barrel)", fontsize=7, color=dk.BLUE, ha="center")
    ax.text(5.4, 0.1, "macro well of the cluster: in series with the barrel, in every plane of C only if Z_cap", fontsize=7.5, ha="center", color="#7a0000")
    ax.text(5.4, -0.45, "R_AC already holds the convergence of the heat of A on the mean of C (its core-internal 1/(8 pi S))", fontsize=7.5, ha="center", color="#7a0000")
    ax.text(5.5, 5.55, "two layers: footprint nodes A and C, ring 1 and the rest as in the program", fontsize=9, ha="center", fontweight="bold")
    dk.save(fig, path)


def fig_decimation(path):
    """!
    @brief The cells kept by the program's stride and by blocks on a 30 mm square at 0.5 mm (3600 cells), and why the stride aliases.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.6, 1, 2)
    n = 60
    cells = [(i, j) for i in range(n) for j in range(n)]
    step = math.ceil(len(cells) / 900)
    kept = cells[::step]
    for ax, title in zip(axs, ("program: every 4th cell in row order (900 of 3600)", "blocks of 2 x 2 cells (900 blocks, centroid and weight)")):
        ax.set_xlim(-1, n + 1)
        ax.set_ylim(-9, n + 3)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), n, n, fill=False, edgecolor="k"))
        ax.text(n / 2, n + 1.2, title, ha="center", fontsize=8.5, fontweight="bold")
    xs, ys = np.array([c[1] for c in kept]) + 0.5, np.array([c[0] for c in kept]) + 0.5
    axs[0].plot(xs, ys, "s", ms=2.3, color=dk.BLUE)
    # the boundary cells that the stride keeps: the left column and every 4th cell of the top and bottom rows; the right column (59) is never kept
    kb = [(i, j) for i, j in kept if i in (0, n - 1) or j in (0, n - 1)]
    axs[0].plot(np.array([c[1] for c in kb]) + 0.5, np.array([c[0] for c in kb]) + 0.5, "o", ms=3.2, mfc="none", mec="#d62728", mew=0.9)
    axs[0].text(n / 2, -2.5, "every row keeps cells at the same columns: columns of points, empty columns between them;\nred: the boundary cells kept (the right side is never sampled); the link term is 10.8 % short", fontsize=7, ha="center", va="top")
    bx, by = np.meshgrid(np.arange(1, n, 2), np.arange(1, n, 2))
    axs[1].plot(bx.ravel(), by.ravel(), "s", ms=3.6, color=dk.HEAT)
    axs[1].text(n / 2, -2.5, "every block keeps its centroid, its weight and its own self distance:\nno stripes; the boundary cells keep their own positions (link term within 0.0 %)", fontsize=7, ha="center", va="top")
    dk.save(fig, path)


def fig_raster(path):
    """!
    @brief The cells of the Lumped raster over a 5 x 5 via array at 1.2 mm pitch: cell 1.0 and 0.5 mm against the core, and the number of cells across the core.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.8, 1, 3)
    pitch, n_v = 1.2, 5
    half = 0.7071 * pitch
    c0 = (n_v - 1) / 2 * pitch + half
    for ax, cell in zip(axs, (1.0, 0.5, 0.25)):
        ax.set_xlim(-1, 2 * c0 + 1)
        ax.set_ylim(-1.8, 2 * c0 + 1.2)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((-0.5, -0.5), 2 * c0 + 1, 2 * c0 + 1, facecolor="#ffd9d0", edgecolor="k"))
        ax.add_patch(Rectangle((c0 - c0, c0 - c0), 2 * c0, 2 * c0, facecolor="#f2b27a", edgecolor="k", linewidth=1.2))
        for i in range(n_v):
            for j in range(n_v):
                ax.add_patch(Circle((half + i * pitch, half + j * pitch), 0.15, facecolor="#7a4b13", edgecolor="k", linewidth=0.4))
        g = -0.5
        while g <= 2 * c0 + 0.5 + 1e-9:
            ax.plot([g, g], [-0.5, 2 * c0 + 0.5], color="k", lw=0.3, alpha=0.5)
            ax.plot([-0.5, 2 * c0 + 0.5], [g, g], color="k", lw=0.3, alpha=0.5)
            g += cell
        ax.set_title(f"cell {cell:g} mm: {2 * c0 / cell:.0f} cells across the core", fontsize=9)
        ax.text(c0, -1.4, "core width 2 x (2.4 + 0.85) = %.1f mm" % (2 * c0) if cell == 1.0 else "", ha="center", fontsize=7)
    dk.save(fig, path, "the raster against the core of a 5 x 5 array at 1.2 mm (the warning is below ten cells across)")


def main():
    """!
    @brief Draw the four figures.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_footprint(OUT / "fig_01_footprint_zones_and_wells.png")
    fig_network(OUT / "fig_02_network_two_layers_double_count.png")
    fig_decimation(OUT / "fig_03_decimation_stride_vs_blocks.png")
    fig_raster(OUT / "fig_04_raster_against_core.png")
    print("wrote 4 figures to", OUT)


if __name__ == "__main__":
    main()
