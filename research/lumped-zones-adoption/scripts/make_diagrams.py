#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the adoption study: the footprint cut into the rest A and the core C with the 2.4.5 wells, the network of two layers with the places where the cluster well and the A-C link could count the same heat twice, the strided decimation of the footprint potentials against blocks, and the raster cell against the core.
@details Figures 01 to 04 and 11 to 13 of figures/ (the data figures are drawn by make_figures.py). No study is run and nothing is imported from the program: only geometry is drawn.
         Files: fig_01_footprint_zones_and_wells.png, fig_02_network_two_layers_double_count.png, fig_03_decimation_stride_vs_blocks.png, fig_04_raster_against_core.png, fig_11_shen_case_board_and_unit_cell.png, fig_12_profile_runner_with_zones.png, fig_13_3d_check_boards.png.
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


def fig_shen(path):
    """!
    @brief The published case of Shen and others: section of the 5.6 mm board with its vias and the heat paths, the plan with 12 x 12 vias, and the axisymmetric unit cell of the independent solver.
    @param path Output file.
    @return None.
    """
    fig, (a, b, c) = dk.canvas(15, 5.6, 1, 3, ratios=[1.35, 1.0, 1.0])
    # --- section (not to scale in the vertical): 4 copper layers, FR-4, vias, flux at the top, isothermal bottom
    a.set_xlim(0, 12)
    a.set_ylim(-1.7, 6.2)
    ys = [4.6, 3.1, 1.6, 0.1]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 11, 0.28, dk.COPPER)
        if k < 3:
            dk.layer(a, 0.5, y - 1.22, 11, 1.22, dk.FR4)
    for x in (2.0, 3.6, 5.2, 6.8, 8.4, 10.0):
        a.add_patch(Rectangle((x - 0.2, 0.1), 0.4, 4.78, facecolor="white", edgecolor="k", linewidth=0.6))
        a.add_patch(Rectangle((x - 0.2, 0.1), 0.06, 4.78, facecolor=dk.COPPER, edgecolor="none"))
        a.add_patch(Rectangle((x + 0.14, 0.1), 0.06, 4.78, facecolor=dk.COPPER, edgecolor="none"))
    for x in np.linspace(1.0, 11.0, 12):
        dk.arrow(a, x, 5.75, x, 5.05, color=dk.HEAT, width=1.1)
    a.text(6.0, 6.05, "1 W, uniform over the 5.6 mm top", fontsize=8, ha="center", color=dk.HEAT)
    a.plot([0.5, 11.5], [-0.15, -0.15], color=dk.BLUE, lw=3)
    a.text(6.0, -0.55, "bottom face fixed at the ambient (20 degC)", fontsize=8, ha="center", color=dk.BLUE)
    a.text(6.0, -1.25, "4 layers of 70 um (2 oz) in 1.6 mm; barrels 0.25 mm drill, 25 um plating, open (air)\nthe vertical flow runs in the barrel and in the FR-4 between the barrels", fontsize=7.5, ha="center")
    a.text(6.0, 2.35, "section (vertical scale stretched)", fontsize=7, ha="center", style="italic")
    # --- plan with 12 x 12 vias
    b.set_xlim(0, 10)
    b.set_ylim(0, 10)
    b.set_aspect("equal")
    b.add_patch(Rectangle((0.5, 0.5), 9.0, 9.0, facecolor="#f4f4f4", edgecolor="k"))
    for i in range(12):
        for j in range(12):
            b.add_patch(Circle((0.5 + 0.375 + 0.75 * i, 0.5 + 0.375 + 0.75 * j), 0.2, facecolor=dk.COPPER, edgecolor="k", linewidth=0.4))
    b.add_patch(Rectangle((0.5, 0.5), 0.75, 0.75, fill=False, edgecolor=dk.BLUE, linewidth=1.8))
    b.text(5.0, 9.75, "plan: 5.6 mm board, 12 x 12 vias at 0.45 mm (Fig. 17(c))", fontsize=8, ha="center")
    b.text(5.0, 0.12, "blue square: one via unit (phi + s)^2 = 0.45 x 0.45 mm", fontsize=7.5, ha="center", color=dk.BLUE)
    # --- axisymmetric unit cell: r to the right, z downwards
    c.set_xlim(0, 10)
    c.set_ylim(-1.3, 11.0)
    stack = [(0.0, 0.55, True), (0.55, 2.55, False), (2.55, 3.1, True), (3.1, 5.1, False), (5.1, 5.65, True), (5.65, 7.65, False), (7.65, 8.2, True)]
    top = 9.2
    for z0, z1, cu in stack:
        c.add_patch(Rectangle((1.0, top - z1), 8.0, z1 - z0, facecolor=dk.COPPER if cu else dk.FR4, edgecolor="k", linewidth=0.6))
    c.add_patch(Rectangle((1.0, top - 8.2), 1.0, 8.2, facecolor=dk.AIR, edgecolor="k", linewidth=0.6))
    c.add_patch(Rectangle((2.0, top - 8.2), 0.45, 8.2, facecolor=dk.COPPER, edgecolor="k", linewidth=0.6))
    c.text(1.5, top + 0.35, "air", fontsize=7, ha="center")
    c.text(2.9, top - 8.9, "barrel (25 um)", fontsize=7, ha="left", color="#8a5a00")
    c.plot([1.0, 1.0], [top - 8.2, top + 0.1], "k-.", lw=0.8)
    c.text(1.0, top - 8.7, "axis", fontsize=7, ha="center")
    for x in np.linspace(2.8, 8.8, 6):
        dk.arrow(c, x, top + 0.9, x, top + 0.2, color=dk.HEAT, width=1.1)
    c.plot([1.0, 9.0], [top - 8.2, top - 8.2], color=dk.BLUE, lw=3)
    c.text(5.0, top - 9.0, "isothermal bottom", fontsize=7.5, ha="center", color=dk.BLUE)
    c.text(5.0, top - 9.7, "(r, z) cell of the disc of equal area,\nside insulated; axisymmetric finite volumes", fontsize=7.5, ha="center")
    c.text(5.0, top + 1.5, "unit cell of the independent solver", fontsize=8, ha="center")
    dk.save(fig, path)


def fig_profile_runner(path):
    """!
    @brief The square-wave run with the zones: the wave, the source split between A and C, the network and the peak operator, and the control in which the program's adapter puts the whole power on A.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 5.2)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.4)
    # the wave
    ax.plot([0.4, 0.4, 1.4, 1.4, 2.4, 2.4, 3.4, 3.4], [4.6, 5.8, 5.8, 4.6, 4.6, 5.8, 5.8, 4.6], color="k", lw=1.6)
    ax.plot([0.4, 3.8], [4.6, 4.6], color="k", lw=0.6)
    ax.text(2.0, 6.15, "P(t): square wave, p_on = P / duty", fontsize=8, ha="center")
    dk.arrow(ax, 3.9, 5.2, 4.9, 5.2, width=1.4)
    dk.box(ax, 5.0, 4.5, 2.4, 1.4, "source split by area\ns = (1 - f_C, f_C)\non the nodes A and C\n(the zone `source` vector)", color="#ffe9b3", size=7.5)
    dk.arrow(ax, 7.5, 5.2, 8.5, 5.2, width=1.4)
    dk.box(ax, 8.6, 4.5, 2.8, 1.4, "C dtheta/dt + K theta = P(t) s\nimplicit step per window\n(zone capacities = cell sums)", color="#cfe3f5", size=7.5)
    dk.arrow(ax, 11.5, 5.2, 12.2, 5.2, width=1.4)
    dk.box(ax, 12.3, 4.5, 1.5, 1.4, "peak operator\nZonePeak(theta)", color="#d9f0d3", size=7.5)
    ax.text(7.0, 3.55, "hottest temperature of the footprint at every step; peak, valley and mean of the last window", fontsize=8, ha="center", color="#1a5d1a")
    # the control
    ax.plot([0.3, 13.7], [3.1, 3.1], "k:", lw=0.8)
    ax.text(7.0, 2.8, "what `lumped._LumpedAdapter.advance` does in 2.4.5, and what the patch changes", fontsize=8, ha="center", style="italic")
    dk.box(ax, 1.0, 0.7, 5.2, 1.5, "program: src[layer * R] = P\nthe whole power enters node 0 = A\n(right for one node; with zones the core C\nreceives nothing: up to 25 % of the rise too hot)", color="#f2c0c0", size=7.5)
    dk.box(ax, 7.8, 0.7, 5.2, 1.5, "zones: src = P * system[\"source\"]\nA gets 1 - f_C and C gets f_C of the power\n(INTEGRATION.md: `advance` and\n`step_responses` read `source` and `peak`)", color="#cfe9d4", size=7.5)
    dk.arrow(ax, 6.3, 1.45, 7.7, 1.45, width=1.4, label="patch")
    dk.save(fig, path)


def fig_boards_3d(path):
    """!
    @brief The three 16 mm boards of the 3D check (plans) and the way the independent 3D solver draws a barrel on its grid.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 4, ratios=[1, 1, 1, 1.1])
    specs = [("dense: 5 x 5 at 1.2 mm\nunder an 8 x 8 mm part", 5, 1.2, (0.0, 0.0), (8.0, 8.0)),
             ("sparse: 3 x 3 at 3.0 mm\nunder a 10 x 10 mm part", 3, 3.0, (0.0, 0.0), (10.0, 10.0)),
             ("off centre: 5 x 5 at 1.2 mm,\n1.5 mm off the centre of a 10 x 6 mm part", 5, 1.2, (1.5, 0.0), (10.0, 6.0))]
    for ax, (title, n, pitch, off, wh) in zip(axs[:3], specs):
        ax.set_xlim(0, 16)
        ax.set_ylim(-2.2, 17.2)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 16, 16, facecolor="#f4f4f4", edgecolor="k"))
        ax.add_patch(Rectangle((8 - wh[0] / 2, 8 - wh[1] / 2), wh[0], wh[1], facecolor="#ffd9d0", edgecolor="k", linewidth=1.2))
        h = (n - 1) / 2
        for i in range(n):
            for j in range(n):
                ax.add_patch(Circle((8 + off[0] + (i - h) * pitch, 8 + off[1] + (j - h) * pitch), 0.15, facecolor="#7a4b13", edgecolor="k", linewidth=0.3))
        ax.text(8, 16.6, title, fontsize=7.5, ha="center", va="bottom")
        ax.text(8, -0.6, "16 x 16 mm, 4 planes of 35 um", fontsize=7, ha="center", va="top")
    d = axs[3]
    d.set_xlim(0, 10)
    d.set_ylim(0, 10)
    d.set_aspect("equal")
    # a barrel of 0.3 mm on the 0.125 mm grid of the solver: 2.4 cells across; the ring and the fill drawn by area share
    cell = 10.0 / 8.0
    for i in range(8):
        for j in range(8):
            d.add_patch(Rectangle((i * cell, j * cell), cell, cell, fill=False, edgecolor="#999999", linewidth=0.5))
    d.add_patch(Circle((5.0, 5.0), 10.0 * 0.15 / 1.0, fill=False, edgecolor=dk.COPPER, linewidth=3))
    d.add_patch(Circle((5.0, 5.0), 10.0 * 0.15 / 1.0 - 0.9, fill=False, edgecolor="k", linewidth=0.6, linestyle="--"))
    d.text(5, 9.3, "a 0.3 mm barrel on the 0.125 mm grid", fontsize=7.5, ha="center")
    d.text(5, 0.35, "the gap cells hold the area share of the ring and the fill\n(the planes are whole, as in the program)", fontsize=7, ha="center")
    dk.save(fig, path)


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
    fig_shen(OUT / "fig_11_shen_case_board_and_unit_cell.png")
    fig_profile_runner(OUT / "fig_12_profile_runner_with_zones.png")
    fig_boards_3d(OUT / "fig_13_3d_check_boards.png")
    print("wrote 7 figures to", OUT)


if __name__ == "__main__":
    main()
