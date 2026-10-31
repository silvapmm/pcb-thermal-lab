#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situations of this investigation (no studies run): the plated barrel through the planes with the heat paths, the point via as a Peaceman well on the grid, a via near the edge with its image, the footprint restricted to the cells on the board, and the colouring of the block SOR.
@details Figures 01 to 05 of figures/ (the data figures 06 and later are drawn by make_figures.py, one numbering). Only the lattice kernel and the footprint routines of
         `point-via-convergence/lib` are called (for the footprint maps); numbers written on the pictures are those of the README or are the geometry of the drawing itself.
         Files: fig_01_barrel_section_heat_paths.png, fig_02_point_via_peaceman_well.png, fig_03_via_near_edge_image.png, fig_04_footprint_on_board_cells.png, fig_05_block_sor_colouring.png.
         Usage: `.venv/bin/python research/via-real-board/scripts/make_diagrams.py` (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import math

import numpy as np
from matplotlib.patches import Circle, Rectangle

import diagram_kit as dk
import edge_image as ei
import paths
import viakernel as vk

OUT = paths.FIGURES


def fig_barrel_section(path):
    """!
    @brief Section of a plated barrel through four copper planes: the heat spreads in each plane towards the barrel and goes down the barrel and out through the films (illustration, no data).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(9.5, 5.2)
    ax.set_xlim(0, 14)
    ax.set_ylim(-1.2, 8.0)
    ys = [6.4, 4.4, 2.4, 0.4]
    for k, y in enumerate(ys):
        dk.layer(ax, 0.5, y, 13, 0.25, dk.COPPER)
        ax.text(13.8, y + 0.12, f"plane {k + 1}", fontsize=7, va="center", ha="right")
        if k < 3:
            dk.layer(ax, 0.5, y - 1.75, 13, 1.75, dk.FR4)
    ax.add_patch(Rectangle((6.4, 0.4), 1.2, 6.25, facecolor="white", edgecolor="k", linewidth=0.8))     # the bore
    ax.add_patch(Rectangle((6.4, 0.4), 0.14, 6.25, facecolor=dk.COPPER, edgecolor="k"))                  # the plating
    ax.add_patch(Rectangle((7.46, 0.4), 0.14, 6.25, facecolor=dk.COPPER, edgecolor="k"))
    for y in ys:
        for x0, x1 in ((1.0, 6.2), (13.0, 7.8)):
            dk.arrow(ax, x0, y + 0.55, x1, y + 0.55, color=dk.HEAT, width=1.1)
    for y in (5.7, 3.7, 1.7):
        dk.arrow(ax, 7.0, y + 0.3, 7.0, y - 0.9, color=dk.BLUE, width=1.4)
    for x in (2.0, 11.5):
        dk.arrow(ax, x, 7.0, x, 6.75, color="#555", width=1.0)
        dk.arrow(ax, x, 0.35, x, -0.35, color="#555", width=1.0)
    ax.text(7.0, 7.45, "plated barrel (drill radius $r_v$, plating 25 $\\mu$m)", ha="center", fontsize=8)
    ax.text(3.2, 7.3, "heat spreads sideways in a plane:\n$\\ln(r/r_v) / (2\\pi S)$ towards the barrel", ha="center", fontsize=7.5, color=dk.HEAT)
    ax.text(10.8, 7.3, "film $h_{top}$", ha="center", fontsize=7.5, color="#555")
    ax.text(10.8, -0.75, "film $h_{bottom}$", ha="center", fontsize=7.5, color="#555")
    ax.text(7.0, -0.9, "down the barrel: $G_v = k_{Cu} A_{via} / d$ in every gap", ha="center", fontsize=8, color=dk.BLUE)
    dk.save(fig, path, "A plated barrel through the planes: the heat paths that the model has to represent (illustration)")


def fig_peaceman_well(path):
    """!
    @brief The point via on the grid: the footprint of the barrel with its weights, the target radius 0.78 r_v and the well network (geometry of the drawing; weights from the footprint routine).
    @param path Output file.
    @return None.
    """
    dx, rv = 1.0, 0.45                                        # drawing units: a cell of 1, a via of radius 0.45 cells (0.3 mm via on a 0.67 mm cell)
    cx, cy = 3.35, 3.2
    w = vk.disc_target_weights(cx, cy, rv, math.exp(-0.25) * rv, dx, 0.0)
    r_eff = vk.effective_radius(w, dx)
    fig, (a, b) = dk.canvas(12.0, 5.2, 1, 2, ratios=[1.1, 1])
    a.set_xlim(0.8, 6.2)
    a.set_ylim(0.8, 5.6)
    a.set_aspect("equal")
    for i in range(1, 6):
        for j in range(1, 6):
            share = w.get((i, j), 0.0)
            a.add_patch(Rectangle((j, i), 1, 1, facecolor=(1.0, 1.0 - 0.8 * min(share * 2.2, 1.0), 1.0 - 0.8 * min(share * 2.2, 1.0)), edgecolor="#888", linewidth=0.6))
            if share > 0:
                a.text(j + 0.5, i + 0.5, f"{share:.2f}", ha="center", va="center", fontsize=7)
    a.add_patch(Circle((cx, cy), rv, fill=False, edgecolor="k", linewidth=1.4))
    a.add_patch(Circle((cx, cy), math.exp(-0.25) * rv, fill=False, edgecolor=dk.BLUE, linewidth=1.2, linestyle="--"))
    a.text(0.9, 5.45, f"weights $w_a$ of the footprint (sum 1)\nsolid: drill $r_v$, dashed: target $0.78\\,r_v$\nlattice effective radius $r_{{eff}}$ = {r_eff / rv:.2f} $r_v$", fontsize=7.5, va="top")
    # Right: the network of the coupling (the barrel nodes are eliminated in the matrix)
    b.set_xlim(0, 10)
    b.set_ylim(0, 8)
    for k, y in enumerate((6.8, 4.9, 3.0, 1.1)):
        dk.box(b, 0.3, y, 2.6, 0.8, f"mean of plane {k + 1}\n$\\bar T_{k + 1} = \\sum_a w_a T_{{{k + 1},a}}$", color="#f5e6c8", size=7)
        dk.resistor(b, 2.9, 5.4, y + 0.4, f"$G_c = 2\\pi S_{k + 1}/\\ln(r_{{eff}}/r_t)$", size=6.5)
        b.plot([5.4, 5.4], [y + 0.4, 1.5 if k == 3 else y + 0.4], color="k", linewidth=0.8)
    for y0, y1 in ((7.2, 5.3), (5.3, 3.4), (3.4, 1.5)):
        b.plot([5.4, 5.4], [y0, y1], color="k", linewidth=2.0)
        b.text(5.6, (y0 + y1) / 2, "$G_v$ (gap)", fontsize=7, va="center")
    b.text(5.0, 0.35, "barrel nodes eliminated (Kron): couplings $G_{lm}$ between the plane means,\nadded to the matrix as $G_{lm} (e_l\\otimes w - e_m\\otimes w)(\\cdot)^T$; no new unknown", ha="center", fontsize=7.5)
    dk.save(fig, path, "The point via as a Peaceman well: the footprint on the cells and the network it adds to the matrix")


def fig_edge_image(path):
    """!
    @brief A via 0.16 mm from an insulated edge on a 1 mm grid: its true image at 0.32 mm and the image the grid sees (cell centre mirrored) at 1.0 mm (geometry of the case of the study).
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12.0, 4.6, 1, 2, ratios=[1.3, 1])
    a.set_xlim(-0.5, 4.6)
    a.set_ylim(-0.2, 2.2)
    a.set_aspect("equal")
    for j in range(0, 4):
        for i in range(0, 2):
            a.add_patch(Rectangle((j, i), 1, 1, facecolor="#f4f4f4" if j < 3 else "#fde9d9", edgecolor="#888", linewidth=0.6))
    a.plot([3, 3], [-0.2, 2.2], color="k", linewidth=2.2)
    a.text(3.05, 2.05, "insulated edge", fontsize=7.5, ha="left")
    a.add_patch(Circle((2.84, 0.5), 0.15, facecolor=dk.COPPER, edgecolor="k"))                  # the true via, 0.16 mm from the edge
    a.add_patch(Circle((3.16, 0.5), 0.15, fill=False, edgecolor="k", linestyle="--"))               # its true image
    a.plot([2.5], [0.5], "s", color=dk.BLUE, markersize=6)                                          # the cell centre that holds the footprint
    a.plot([3.5], [0.5], "s", color=dk.BLUE, markerfacecolor="white", markersize=6)                 # the image of the cell centre the grid has
    dk.arrow(a, 2.84, 1.2, 3.16, 1.2, color=dk.HEAT, style="<->", width=1.2)
    a.text(3.0, 1.3, "$D_{true} = 2\\delta$", fontsize=8, color=dk.HEAT, ha="center")
    dk.arrow(a, 2.5, 1.7, 3.5, 1.7, color=dk.BLUE, style="<->", width=1.2)
    a.text(3.0, 1.8, "$D_{lat}$ (cell centres)", fontsize=8, color=dk.BLUE, ha="center")
    a.text(0.0, -0.1, "cell 1 mm; via $\\delta$ = 0.16 mm from the edge (study case)", fontsize=7.5)
    b.set_xlim(0, 10)
    b.set_ylim(0, 8)
    b.text(0.2, 7.2, "mean potential of the footprint", fontsize=9, fontweight="bold")
    b.text(0.2, 5.4, "lattice (what the matrix has):\n  $-\\frac{I}{2\\pi S}\\,[\\ln r_{eff} + \\ln D_{lat}]$", fontsize=8)
    b.text(0.2, 3.5, "true geometry (disc + image):\n  $-\\frac{I}{2\\pi S}\\,[\\ln r_t + \\ln D_{true}]$", fontsize=8)
    b.text(0.2, 1.4, "the well must carry the difference:\n  $G_c = 2\\pi S\\,/\\,[\\ln(r_{eff}/r_t) + c],\\;\\; c = \\ln(D_{lat}/D_{true})$", fontsize=8, color=dk.HEAT)
    dk.save(fig, path, "A via near an insulated edge: the grid mirrors the cell centre, not the via (the term c is tested in study S1)")


def fig_board_cells(path):
    """!
    @brief The footprint of a via near an outline that cuts the grid: cells off the board (pinned), partial cells (weight by cover), and the folded alternative (geometry of the drawing).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12.5, 4.4, 1, 3)
    titles = ("prototype: every cell inside the grid", "restricted to the cells on the board (weight x cover)", "folded at a grid edge: the weight outside moves to the mirror cell")
    for k, ax in enumerate(axs):
        cover = np.ones((4, 6))
        if k < 2:                                                # an outline that cuts column 4 (cover 0.35) and leaves column 5 off the board
            cover[:, 4] = 0.35
            cover[:, 5] = 0.0
            cx, cy, rv = 3.95, 2.0, 0.9
        else:                                                    # a via at the border of the grid: the disc leaves it
            cx, cy, rv = 5.8, 2.0, 0.9
        w = vk.disc_weights(cx, cy, rv, 1.0, 0.0, 24, "area")
        ax.set_xlim(-0.2, 7.2)
        ax.set_ylim(-0.2, 4.2)
        ax.set_aspect("equal")
        ax.set_title(titles[k], fontsize=8)
        for i in range(4):
            for j in range(6):
                col = "#dddddd" if cover[i, j] == 0 else ("#f7e3c4" if cover[i, j] < 1 else "#ffffff")
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=col, edgecolor="#888", linewidth=0.6))
        if k < 2:
            ax.plot([4.35, 4.35], [-0.2, 4.2], color="k", linewidth=2.0)               # the outline edge cuts column 4
        else:
            ax.plot([6.0, 6.0], [-0.2, 4.2], color="k", linewidth=2.0)                 # the edge of the grid
        ax.add_patch(Circle((cx, cy), rv, fill=False, edgecolor="k", linewidth=1.2))
        if k == 0:
            use = {key: x for key, x in w.items() if 0 <= key[0] < 4 and 0 <= key[1] < 6}
        elif k == 1:
            use = ei.restrict_to_board(w, cover, 4, 6)
        else:
            use = ei.fold_into_grid(w, 4, 6)
        tot = sum(use.values())
        for (i, j), x in use.items():
            ax.text(j + 0.5, i + 0.5, f"{x / tot:.2f}", ha="center", va="center", fontsize=7, color=dk.HEAT if cover[i, j] < 1 else "k")
        if k == 0:
            ax.text(0.0, 4.15, "grey: off the board, pinned to the ambient: weight\non them would couple the barrel to the pin", fontsize=6.5, va="top")
    dk.save(fig, path, "The footprint of a via next to an outline: three ways to treat the cells the outline cuts (illustration of the options of study S1)")


def fig_block_colouring(path):
    """!
    @brief Block SOR (c'): the red-black colours of the stencil, the via cells skipped by the colours, and the via blocks coloured so that blocks of one group are not coupled (geometry of the drawing).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12.5, 4.4, 1, 3)
    n = 12
    vias = [(2, 2), (2, 4), (5, 3), (8, 8), (9, 6), (4, 9)]
    owner = {}
    for k, (i, j) in enumerate(vias):
        for di in (0, 1):
            for dj in (0, 1):
                owner[(i + di, j + dj)] = k
    colours = {}
    for k, (i, j) in enumerate(vias):                           # greedy colouring: blocks are neighbours when a cell of one touches a cell of the other
        used = set()
        for (ci, cj), o in owner.items():
            if o != k:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = owner.get((ci + di, cj + dj))
                if m is not None and m != k and m in colours:
                    used.add(colours[m])
        colours[k] = min(c for c in range(10) if c not in used)
    palette = ["#4c78a8", "#f58518", "#54a24b", "#b279a2"]
    titles = ("1. the two colours of the stencil (red-black)", "2. via cells skipped by the colours", "3. blocks: group by group, solved exactly, relaxed by $\\omega$")
    for k, ax in enumerate(axs):
        ax.set_xlim(-0.2, n + 0.2)
        ax.set_ylim(-0.2, n + 0.2)
        ax.set_aspect("equal")
        ax.set_title(titles[k], fontsize=8)
        for i in range(n):
            for j in range(n):
                face = "#f4b6b6" if (i + j) % 2 == 0 else "#444444"
                if k == 0:
                    pass
                elif (i, j) in owner:
                    face = "white" if k == 1 else palette[colours[owner[(i, j)]] % 4]
                elif k == 2:
                    face = "#eeeeee"
                if k == 1 and (i, j) not in owner:
                    face = "#f4b6b6" if (i + j) % 2 == 0 else "#444444"
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=face, edgecolor="#999", linewidth=0.4))
        if k == 2:
            for g in sorted(set(colours.values())):
                ax.text(0.1, n - 0.7 - g * 0.8, f"group {g + 1}", color=palette[g % 4], fontsize=7, fontweight="bold")
    dk.save(fig, path, "Block SOR (c'): colours for the stencil, blocks for the vias (illustration; the sweeps are in README 4)")


def main():
    """!
    @brief Draw the five diagrams into figures/.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_barrel_section(OUT / "fig_01_barrel_section_heat_paths.png")
    fig_peaceman_well(OUT / "fig_02_point_via_peaceman_well.png")
    fig_edge_image(OUT / "fig_03_via_near_edge_image.png")
    fig_board_cells(OUT / "fig_04_footprint_on_board_cells.png")
    fig_block_colouring(OUT / "fig_05_block_sor_colouring.png")


if __name__ == "__main__":
    main()
