#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: the via barrel with the heat paths and the constriction the models leave out, how the Lumped ring network and the Analytic tile mosaic see a via,
       the cells and clusters of a via lattice, and the resistance chains before and after.
@details Figures 01 to 05 of figures/ (data figures 06 and later are drawn by make_figures.py). Only the closed form of lib/constriction.py is evaluated (curves of the temperature
         of a plane around a via); no study is run.
         Files: fig_01_via_section_and_constriction.png, fig_02_lumped_rings_and_vias.png, fig_03_analytic_tiles_and_vias.png, fig_04_cells_clusters_macro_micro.png,
         fig_05_resistance_chains.png.
         Usage: python research/lumped-analytic-vias/scripts/make_diagrams.py   (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import constriction as cr                                                   # noqa: E402
import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_section(path):
    """!
    @brief Section of a four-plane board with a via, and the temperature of one plane against the distance to the barrel: the mean level that the models carry and the wall level.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 4.8, 1, 2, ratios=[1.3, 1])
    a.set_xlim(0, 13)
    a.set_ylim(-1.0, 7.0)
    ys = [5.6, 3.9, 2.2, 0.5]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 12, 0.22, dk.COPPER)
        a.text(12.75, y + 0.1, f"{k + 1}", fontsize=8, va="center")
        if k < 3:
            dk.layer(a, 0.5, y - 1.48, 12, 1.48, dk.FR4)
    a.add_patch(Rectangle((6.0, 0.5), 1.0, 5.32, facecolor="white", edgecolor="k", linewidth=0.8))
    a.add_patch(Rectangle((6.0, 0.5), 0.12, 5.32, facecolor=dk.COPPER, edgecolor="k"))
    a.add_patch(Rectangle((6.88, 0.5), 0.12, 5.32, facecolor=dk.COPPER, edgecolor="k"))
    for y in ys:
        for x0, x1 in ((1.0, 5.9), (12.0, 7.1)):
            dk.arrow(a, x0, y + 0.55, x1, y + 0.55, color=dk.HEAT, width=1.1)
    a.text(6.5, 6.5, "barrel, radius $r_v$", ha="center", fontsize=8)
    a.text(3.3, 6.4, "heat converges on the barrel in every plane", ha="center", fontsize=7.5, color=dk.HEAT)
    a.text(6.5, -0.5, "the models join the plane MEAN temperatures through the barrel conductance only", ha="center", fontsize=8)
    for y in (4.9, 3.2, 1.5):
        dk.arrow(a, 6.5, y + 0.55, 6.5, y - 0.35, color=dk.BLUE, width=1.3)
    # temperature of a plane around the via (Krogh cell, closed form)
    S, a_v, R = 0.0135, 0.1170e-3, 1.9e-3
    r = np.linspace(a_v, R, 200)
    t = (R * R * np.log(r / a_v) - (r * r - a_v * a_v) / 2) / (2 * math.pi * S * (R * R - a_v * a_v))
    mean = cr.krogh(S, R, a_v)
    b.axis("on")
    b.plot(r * 1e3, t, color=dk.HEAT, lw=2)
    b.axhline(mean, color="k", ls="--", lw=1)
    b.axhline(0, color=dk.BLUE, ls=":", lw=1.2)
    b.annotate("", (0.3, mean), (0.3, 0), arrowprops={"arrowstyle": "<->", "color": "k"})
    b.text(0.36, mean / 2, "constriction\n$R_c=\\frac{1}{2\\pi S}(\\ln\\frac{R}{r_t}-\\frac{3}{4})$", fontsize=8, va="center")
    b.text(R * 1e3, mean + 0.5, "mean of the cell: the node of the model", ha="right", fontsize=8)
    b.text(0.12, -0.9, "wall of the barrel", fontsize=8, color=dk.BLUE)
    b.set_xlabel("distance to the axis of the via (mm)")
    b.set_ylabel("temperature above the wall per watt of the via (K/W)")
    b.set_title("one plane, one via, uniform heat in the cell", fontsize=9)
    dk.save(fig, path)


def fig_lumped(path):
    """!
    @brief The Lumped ring network around a footprint with vias: the rings, the via sink seen from a ring node, and the patched chain.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 5.2, 1, 2, ratios=[1, 1.15])
    a.set_xlim(-8, 8)
    a.set_ylim(-8, 8)
    a.set_aspect("equal")
    for k, rr in enumerate((7.2, 5.6, 4.2, 3.0, 2.0)):
        a.add_patch(Circle((0, 0), rr, facecolor="none", edgecolor="0.6", linestyle="--", linewidth=0.8))
    a.add_patch(Rectangle((-1.6, -1.6), 3.2, 3.2, facecolor="#f4c6c0", edgecolor="k"))
    a.text(0, 0, "ring 0\n(footprint)", ha="center", va="center", fontsize=7)
    for i in (-0.8, 0, 0.8):
        for j in (-0.8, 0, 0.8):
            a.add_patch(Circle((i, j), 0.14, facecolor=dk.COPPER, edgecolor="k", linewidth=0.5))
    for i in range(5):
        a.add_patch(Circle((2.6 + 0.0, 0.0 - 0.9 + 0.0), 0.0))
    for k in range(5):
        a.add_patch(Circle((3.4 + 0.5 * k, 0.0), 0.14, facecolor=dk.COPPER, edgecolor="k", linewidth=0.5))
    a.text(5.1, 0.6, "row of vias:\none sector of the rings", fontsize=7.5, ha="center")
    a.text(0, -7.6, "each ring is ONE node per layer (its mean temperature)", ha="center", fontsize=8)
    a.text(0, 7.3, "offset contours of the footprint", ha="center", fontsize=8)
    b.set_xlim(0, 13)
    b.set_ylim(-0.5, 7.5)
    b.text(6.5, 7.1, "vertical link of ring $k$ between layers $l$ and $l+1$", ha="center", fontsize=8.5)
    dk.box(b, 0.3, 5.0, 2.0, 0.9, "ring $k$, layer $l$\n(mean $T$)", "#cfe3f5", size=7)
    dk.box(b, 9.2, 5.0, 2.2, 0.9, "ring $k$, layer $l+1$", "#cfe3f5", size=7)
    dk.resistor(b, 2.3, 9.2, 5.45)
    b.text(5.75, 6.0, "program: $G_z$ = dielectric + $N$ barrels", fontsize=7)
    b.text(5.75, 4.6, "(nothing for the heat that converges on each barrel)", fontsize=6.5, ha="center")
    dk.box(b, 0.3, 1.0, 2.0, 0.9, "ring $k$, layer $l$", "#cfe3f5", size=7)
    dk.box(b, 3.3, 1.0, 1.5, 0.9, "barrel $l$", dk.COPPER, size=7)
    dk.box(b, 6.3, 1.0, 1.5, 0.9, "barrel $l+1$", dk.COPPER, size=7)
    dk.box(b, 9.2, 1.0, 2.2, 0.9, "ring $k$, layer $l+1$", "#cfe3f5", size=7)
    dk.resistor(b, 2.3, 3.3, 1.45)
    dk.resistor(b, 4.8, 6.3, 1.45)
    dk.resistor(b, 7.8, 9.2, 1.45)
    b.text(2.8, 2.0, "$R_{micro}+N R_{macro}$", fontsize=6.5, ha="center")
    b.text(5.55, 2.0, "$1/G_v$", fontsize=7, ha="center")
    b.text(8.5, 2.0, "$R_{micro}+N R_{macro}$", fontsize=6.5, ha="center")
    b.text(6.5, 0.1, "patched: sheet - constriction - barrel - barrel conductance - barrel - constriction - sheet (Kron reduced)", ha="center", fontsize=7.5)
    dk.save(fig, path)


def fig_analytic(path):
    """!
    @brief The tile mosaic of the Analytic model with a via at the centre of a tile, at a corner, and spread over four tiles.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(13, 4.6, 1, 3)
    titles = ["via at the centre of its tile", "via at a corner of the tiles (program: all in one tile)", "patched: bilinear spread over four tiles"]
    pos = [(1.5, 1.5), (2.0, 2.0), (2.0, 2.0)]
    for ax, title, (vx, vy) in zip(axs, titles, pos):
        ax.set_xlim(-0.3, 4.3)
        ax.set_ylim(-0.3, 4.3)
        ax.set_aspect("equal")
        for i in range(4):
            for j in range(4):
                ax.add_patch(Rectangle((i, j), 1, 1, facecolor="none", edgecolor="0.6", linewidth=0.8))
        ax.add_patch(Circle((vx, vy), 0.06, facecolor=dk.COPPER, edgecolor="k"))
        ax.set_title(title, fontsize=8.5)
    # sink drawn as uniform over the tile(s) that carry it
    axs[0].add_patch(Rectangle((1, 1), 1, 1, facecolor=dk.HEAT, alpha=0.35))
    axs[1].add_patch(Rectangle((2, 2), 1, 1, facecolor=dk.HEAT, alpha=0.35))
    axs[2].add_patch(Rectangle((1, 1), 2, 2, facecolor=dk.HEAT, alpha=0.35))
    axs[0].text(2.0, -0.2, "sink spread over one tile; true sink at a point:\nself-term $D=(\\ln\\frac{R}{r_t}-\\frac{1}{4})/2\\pi S$", fontsize=7.5, ha="center", va="top")
    axs[1].text(2.0, -0.2, "the sink sits half a tile away from the via\n(position error of the tile means)", fontsize=7.5, ha="center", va="top")
    axs[2].text(2.0, -0.2, "first moment kept; $D$ of the 2 x 2 block\non each of the four tiles", fontsize=7.5, ha="center", va="top")
    dk.save(fig, path)


def fig_cells(path):
    """!
    @brief The micro cell of a via, the cluster as a larger disc and the macro cell of the ring or tile.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12, 5.2, 1, 2)
    a.set_xlim(-1, 7)
    a.set_ylim(-1, 7)
    a.set_aspect("equal")
    for i in range(6):
        for j in range(6):
            a.add_patch(Rectangle((i - 0.5 + 0.5, j - 0.5 + 0.5), 1, 1, facecolor="none", edgecolor="0.7", linewidth=0.5))
            a.add_patch(Circle((i + 0.5 + 0.0, j + 0.5), 0.12, facecolor=dk.COPPER, edgecolor="k", linewidth=0.4))
    a.add_patch(Circle((3.0, 3.0), 3.4, facecolor="none", edgecolor=dk.BLUE, linewidth=1.5, linestyle="--"))
    a.add_patch(Circle((3.0, 3.0), 0.564 * 1.0, facecolor="none", edgecolor=dk.HEAT, linewidth=1.2))
    a.text(3.0, 6.8, "macro cell: ring / tile (radius R)", ha="center", fontsize=8, color=dk.BLUE)
    a.text(3.0, -0.8, "micro cell: Wigner-Seitz disc of one via, $r_c = d_{nn}/\\sqrt{\\pi}$ (red)", ha="center", fontsize=8, color=dk.HEAT)
    a.set_title("a cluster of vias in a footprint", fontsize=9)
    b.set_xlim(0, 10)
    b.set_ylim(0, 8)
    dk.box(b, 0.5, 6.2, 9, 1.0, "$R_{wall} = \\frac{1}{2\\pi S}\\ln\\frac{R}{r_{cl}}$ (macro: cluster as one disc) $+\\ \\frac{1}{N}\\mathrm{Krogh}(S, r_c, r_t)$ (micro: one cell)", "#fff3d6", size=8.5)
    b.text(5, 5.2, "$r_{cl}=\\sqrt{N}\\,r_c$ (cluster disc), $r_t=e^{-1/4}r_v$ (target radius of a barrel)", ha="center", fontsize=8.5)
    b.text(5, 4.3, "$N=1$: macro only, with the constant 1/4 of a point sink read against the tile mean", ha="center", fontsize=8)
    b.text(5, 3.5, "lattice limit ($r_{cl}\\to R$): the macro term vanishes, micro = Krogh cell", ha="center", fontsize=8)
    b.text(5, 2.5, "Lumped: macro disc = the rings that the cluster touches", ha="center", fontsize=8)
    b.text(5, 1.7, "Analytic: macro disc = the tile (the mosaic already treats larger scales)", ha="center", fontsize=8)
    dk.save(fig, path)


def fig_chains(path):
    """!
    @brief Resistance chains of a two-plane board with a via: the program and the patch, and the effect on the copper-fill gain.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(12, 4.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.text(0.2, 6.5, "program (Lumped, Analytic)", fontsize=9, weight="bold")
    dk.box(ax, 0.3, 5.0, 1.8, 0.8, "top plane\nmean", "#cfe3f5", size=7)
    dk.resistor(ax, 2.1, 5.1, 5.4, "$1/G_v$ (copper fill: 3.3 x smaller)")
    dk.box(ax, 5.1, 5.0, 1.8, 0.8, "bottom plane\nmean", "#cfe3f5", size=7)
    ax.text(7.3, 5.4, "all the weight on the barrel: a copper fill\nchanges the total resistance 3.3 times", fontsize=8, va="center")
    ax.text(0.2, 3.7, "with the constriction", fontsize=9, weight="bold")
    dk.box(ax, 0.3, 2.2, 1.8, 0.8, "top plane\nmean", "#cfe3f5", size=7)
    dk.resistor(ax, 2.1, 3.7, 2.6, "$R_c$ (top)")
    dk.resistor(ax, 3.7, 5.3, 2.6, "$1/G_v$")
    dk.resistor(ax, 5.3, 6.9, 2.6, "$R_c$ (bottom)")
    dk.box(ax, 6.9, 2.2, 1.8, 0.8, "bottom plane\nmean", "#cfe3f5", size=7)
    ax.text(9.0, 2.6, "the two $R_c$ do not change with the fill:\nthe fill is only part of the chain", fontsize=8, va="center")
    ax.text(0.2, 0.7, "example of the 3 x 3 board: $1/G_v$ = 175 K/W open and 53 K/W copper over three gaps; $R_c$ of a 0.3 mm via in 35 um copper in a 1.9 mm cell ~ 24 K/W per plane", fontsize=8)
    dk.save(fig, path)


def main():
    """!
    @brief Draw the five diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_via_section_and_constriction.png")
    fig_lumped(OUT / "fig_02_lumped_rings_and_vias.png")
    fig_analytic(OUT / "fig_03_analytic_tiles_and_vias.png")
    fig_cells(OUT / "fig_04_cells_clusters_macro_micro.png")
    fig_chains(OUT / "fig_05_resistance_chains.png")


if __name__ == "__main__":
    main()
