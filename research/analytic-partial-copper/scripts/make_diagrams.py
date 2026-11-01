#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: a part on a copper pad over bare laminate (the section with the paths of the heat, the nodes of the program and the candidate), the uniform sheet the Analytic model puts in its place, and the tiles of the candidate.
@details Figures 01 to 03 and 09 of figures/ (the data figures 04 to 08 are drawn by make_figures.py). No study is run; the geometry is the board of the baseline (60 mm board, 1.6 mm, 6 mm part,
         pads of 6 to 40 mm; the vertical scale of the sections is exaggerated). Every number written on a drawing is one the README holds.
         Files: fig_01_part_on_a_pad_section.png, fig_02_uniform_sheet_against_the_pad.png, fig_03_nodes_and_tiles_of_the_candidate.png, fig_09_copper_edge_inside_a_tile.png (review).
         Usage: python research/analytic-partial-copper/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def section(ax, title, nodes):
    """!
    @brief Section of a one-layer board: the part on a copper pad, the laminate, the films and the paths of the heat.
    @param ax Axes.
    @param title Panel title.
    @param nodes None (the real board), "program" (one node and a film in series) or "candidate" (laminate nodes).
    @return None.
    """
    ax.set_xlim(0, 14)
    ax.set_ylim(-1.9, 6.4)
    ax.set_title(title, fontsize=9)
    zt, lam, tcu = 4.4, 2.6, 0.22
    dk.layer(ax, 0.4, zt - tcu - lam, 13.2, lam, dk.FR4)
    dk.layer(ax, 4.2, zt - tcu, 5.6, tcu, dk.COPPER)                        # the pad
    ax.add_patch(Rectangle((5.6, zt + 0.3), 2.8, 0.8, facecolor="#555555", edgecolor="k"))
    ax.text(7, zt + 0.7, "part", color="white", ha="center", va="center", fontsize=8)
    for x in (6.0, 7.0, 8.0):
        dk.arrow(ax, x, zt + 0.3, x, zt + 0.02, color=dk.HEAT, width=1.0)
    ax.text(2.2, zt + 0.15, "bare laminate", fontsize=7, ha="center")
    ax.text(7, zt - 0.62, "pad", fontsize=7, ha="center")
    if nodes is None:
        for sgn in (-1, 1):
            dk.arrow(ax, 7 + sgn * 1.0, zt - tcu / 2, 7 + sgn * 2.6, zt - tcu / 2, color=dk.BLUE, width=1.4)       # spreading in the copper
            dk.arrow(ax, 7 + sgn * 2.8, zt - tcu - 0.05, 7 + sgn * 4.4, zt - tcu - 0.05, color=dk.BLUE, width=0.8)  # weak spreading in the laminate
        for x in (5.0, 7.0, 9.0, 2.2, 11.8):
            dk.arrow(ax, x, zt - tcu - 0.1, x, zt - tcu - lam + 0.25, color=dk.HEAT, width=0.9)
        ax.text(7, zt - lam - 0.35, "heat goes down through the laminate over the pad\nand over the bare board, spreading in it sideways:\nthe laminate is a poor spreader", ha="center", va="top", fontsize=7)
    else:
        # The program has a single node (the copper layer, holding the whole laminate sideways); the laminate is a series film to the bottom face, not a second node (review fix)
        ys = [zt - tcu / 2] if nodes == "program" else np.linspace(zt - tcu / 2, zt - tcu - lam, 5)
        xs = [1.2, 4.0, 7.0, 10.0, 12.8]
        for x in xs:
            for j, y in enumerate(ys):
                ax.add_patch(Circle((x, y), 0.11, facecolor=dk.COPPER if j == 0 and 4.2 < x < 9.8 else ("#f1e3c9" if j == 0 else "#7aa86d"), edgecolor="k", zorder=5))
            ax.plot([x, x], [ys[0], zt - tcu - lam], color="k", linewidth=0.6, linestyle="-" if nodes != "program" else ":", zorder=4)
        if nodes == "program":
            ax.text(13.4, zt - tcu - lam / 2, "series film\nt_lam / k_z\n+ 1 / h_b", fontsize=6, va="center", ha="right")
        for y0, y1 in zip(ys[:-1], ys[1:]):
            ax.text(13.4, (y0 + y1) / 2, "k_z A / g", fontsize=6, va="center", ha="right")
        if nodes == "program":
            ax.text(7, zt - lam - 0.35, "one node under the copper;\nthe laminate is a film in series\nwith the bottom film (laminate.py)", ha="center", va="top", fontsize=7)
        else:
            ax.text(7, zt - lam - 0.35, "n laminate nodes (4 drawn): the heat\ncan spread in the laminate on its way down", ha="center", va="top", fontsize=7)
    ax.text(7, -1.75, "ambient (film on each face)", ha="center", fontsize=7)
    ax.annotate("", (13.8, zt - tcu), (13.8, zt - tcu - lam), arrowprops={"arrowstyle": "<->", "linewidth": 0.8})


def fig_section(path):
    """!
    @brief Figure 01: the board and the two ways the nodes can represent it.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 4.6, 1, 3)
    section(axs[0], "The board: part on a copper pad", None)
    section(axs[1], "Program: one node per copper layer", "program")
    section(axs[2], "Candidate: nodes through the laminate", "candidate")
    dk.save(fig, path)


def fig_uniform(path):
    """!
    @brief Figure 02: top view of the pad and the part, the weights of the fill average, and the uniform sheet that results.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.8, 1, 3)
    titles = ["The board: pad (copper) on bare laminate", "The program: fill averaged with weights K0(r / lambda)", "The uniform sheet it solves"]
    for ax, t in zip(axs, titles):
        ax.set_xlim(0, 60)
        ax.set_ylim(0, 60)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=9)
        ax.add_patch(Rectangle((0, 0), 60, 60, facecolor=dk.FR4, edgecolor="k", zorder=1))
    axs[0].add_patch(Rectangle((20, 20), 20, 20, facecolor=dk.COPPER, edgecolor="k"))
    axs[0].add_patch(Rectangle((27, 27), 6, 6, facecolor="#555555", edgecolor="k"))
    axs[0].text(30, 16.5, "pad 20 mm: sheet S_cu", ha="center", fontsize=7)
    axs[0].text(30, 4, "bare: sheet S_lam about 10 times lower", ha="center", fontsize=7)
    # weights
    g = np.linspace(0, 60, 241)
    X, Y = np.meshgrid(g, g)
    R = np.hypot(X - 30, Y - 30)
    from scipy.special import k0
    w = k0(np.maximum(R, 3.0) / 12.0)
    axs[1].imshow(w / w.max(), extent=(0, 60, 0, 60), origin="lower", cmap="Blues", alpha=0.85, zorder=2)
    axs[1].add_patch(Rectangle((20, 20), 20, 20, fill=False, edgecolor=dk.COPPER, linewidth=2, zorder=3))
    axs[1].add_patch(Rectangle((27, 27), 6, 6, facecolor="#555555", edgecolor="k", zorder=3))
    axs[1].text(30, 4, "fill = sum(fill x w) / sum(w)", ha="center", fontsize=7)
    axs[2].add_patch(Rectangle((0, 0), 60, 60, facecolor="#d9c08e", edgecolor="k"))
    axs[2].add_patch(Rectangle((27, 27), 6, 6, facecolor="#555555", edgecolor="k"))
    axs[2].text(30, 50, "one sheet, S = fill S_cu + (1 - fill) S_lam\neverywhere (fill 0.44 for the 20 mm pad)", ha="center", fontsize=7)
    axs[2].text(30, 4, "no edge: the pad has disappeared", ha="center", fontsize=7)
    dk.save(fig, path)


def fig_tiles(path):
    """!
    @brief Figure 03: the candidate: a bare base board and the copper put back as extra conductance on the links between tiles.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.8, 1, 3)
    titles = ["1. Base: every node bare (series solution)", "2. Tiles: copper links (harmonic mean of the tile sheets)", "3. Defect: dS = S_link - S_bare on the links, (I + G C) y = y0"]
    for ax, t in zip(axs, titles):
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 20)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=8)
        ax.add_patch(Rectangle((0, 0), 20, 20, facecolor=dk.FR4, edgecolor="k"))
    axs[0].add_patch(Rectangle((8, 8), 4, 4, facecolor="#555555", edgecolor="k"))
    axs[0].text(10, 3, "uniform bare board,\nexact for the laminate", ha="center", fontsize=7)
    for ax in axs[1:]:
        for i in range(21):
            ax.plot([i, i], [0, 20], color="k", linewidth=0.25)
            ax.plot([0, 20], [i, i], color="k", linewidth=0.25)
        ax.add_patch(Rectangle((5, 5), 10, 10, facecolor=dk.COPPER, edgecolor="k", alpha=0.9))
        ax.add_patch(Rectangle((8, 8), 4, 4, facecolor="#555555", edgecolor="k"))
    for i in range(5, 15):
        for j in range(5, 14):
            axs[2].plot([i + 0.5, i + 0.5], [j + 0.5, j + 1.5], color=dk.HEAT, linewidth=1.4)
            axs[2].plot([j + 0.5, j + 1.5], [i + 0.5, i + 0.5], color=dk.HEAT, linewidth=1.4)
    axs[1].text(10, 2.2, "tiles of 1 mm (coarser here)", ha="center", fontsize=7)
    axs[2].text(10, 2.2, "only links inside the copper carry a defect", ha="center", fontsize=7)
    dk.save(fig, path)


def fig_edge_in_tile(path):
    """!
    @brief Figure 09 (review): a copper edge on a tile edge and inside a tile; the partly covered tile conducts like copper, so the pad acts as if it reached the far side of the tile.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.2, 1, 3)
    cases = [("pad edge on a tile edge", 10.0), ("pad edge in the middle of a tile", 10.5), ("what the tiles see (fill 0.5 ~ copper)", None)]
    for ax, (title, edge) in zip(axs, cases):
        ax.set_xlim(6, 14)
        ax.set_ylim(0, 6)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=8)
        ax.add_patch(Rectangle((6, 0), 8, 6, facecolor=dk.FR4, edgecolor="k"))
        if edge is not None:
            ax.add_patch(Rectangle((6, 0), edge - 6, 6, facecolor=dk.COPPER, edgecolor="none"))
        else:
            ax.add_patch(Rectangle((6, 0), 4, 6, facecolor=dk.COPPER, edgecolor="none"))
            ax.add_patch(Rectangle((10, 0), 1, 6, facecolor=dk.COPPER, alpha=0.6, edgecolor="none"))
            ax.text(10.5, 5.5, "f = 0.5", ha="center", fontsize=7, backgroundcolor="white")
            dk.arrow(ax, 10.6, 3, 11.9, 3, color=dk.HEAT, width=1.2)
        for x in range(6, 15):
            ax.plot([x, x], [0, 6], color="k", linewidth=0.4)
        for y in range(0, 7):
            ax.plot([6, 14], [y, y], color="k", linewidth=0.4)
    axs[0].text(10, -0.6, "edge on a tile edge: within 0.3 % of the FVM", ha="center", fontsize=7)
    axs[1].text(10, -0.6, "edge 0.5 mm inside a 1 mm tile", ha="center", fontsize=7)
    axs[2].text(10, -0.6, "the copper reaches the far side: -5.8 to -7.7 %", ha="center", fontsize=7)
    dk.save(fig, path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_part_on_a_pad_section.png")
    fig_uniform(OUT / "fig_02_uniform_sheet_against_the_pad.png")
    fig_tiles(OUT / "fig_03_nodes_and_tiles_of_the_candidate.png")
    fig_edge_in_tile(OUT / "fig_09_copper_edge_inside_a_tile.png")
    print("figures written to", OUT)
