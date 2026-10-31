#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the laminate nodes (no data, no solver): the section of a board over a bare window with the heat paths, the node ladder with its grading, the mask of the cells that get the nodes, the laminate path of a one-layer board, and the five constructions side by side.
@details Figures 01 to 05 of figures/ (the data figures from 06 on are drawn by make_figures.py, one numbering). The geometry is the board of the sweeps (30 mm, 6 mm part, window under it); the vertical scale of the sections is exaggerated.
         The only numbers on the drawings are the ones the README quotes from earlier folders (section 1.2).
         Files: fig_01_section_over_a_window.png, fig_02_node_ladder_and_grading.png, fig_03_mask_of_the_cells.png, fig_04_one_layer_laminate_path.png, fig_05_five_constructions.png.
         Usage: .venv/bin/python research/laminate-nodes/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import diagram_kit as dk                                                    # noqa: E402
import rule as RU                                                           # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def section(ax, mode, title):
    """!
    @brief Section of a two-layer board with a part over a window of the top copper: how the layered model sees it (mode "layered") or what the laminate does (mode "real").
    @param ax Axes.
    @param mode "layered" or "real".
    @param title Title.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_title(title, fontsize=9)
    zt, zb, tcu = 4.6, 1.6, 0.25                          # top face, bottom of the gap, drawn copper thickness
    dk.layer(ax, 0.5, zb, 11, zt - tcu - zb, dk.FR4)
    dk.layer(ax, 0.5, zb - tcu, 11, tcu, dk.COPPER, "bottom plane")
    dk.layer(ax, 0.5, zt - tcu, 3.5, tcu, dk.COPPER)
    dk.layer(ax, 8, zt - tcu, 3.5, tcu, dk.COPPER)
    dk.layer(ax, 4, zt - tcu, 4, tcu, dk.FR4)             # the window: laminate where the copper is absent
    dk.layer(ax, 4, zt, 4, 0.7, "#888888", "part")
    ax.text(6, zt + 1.0, "window", ha="center", fontsize=7, color="#555555")
    for x in (4.8, 5.6, 6.4, 7.2):
        dk.arrow(ax, x, zt + 0.7, x, zt + 0.02, color=dk.HEAT, width=1.1)
    if mode == "layered":
        for z, txt in ((zt - tcu / 2, "node: copper + half gap"), (zb - tcu / 2, "node: copper + half gap")):
            for x in (2.2, 6.0, 9.8):
                ax.add_patch(Circle((x, z), 0.1, color="k"))
            ax.text(11.9, z + (0.45 if z > 3 else -0.5), txt, fontsize=6, ha="right", va="center")
        for x in (6.0,):
            dk.arrow(ax, x, zt - tcu / 2 - 0.1, x, zb - tcu / 2 + 0.1, color=dk.BLUE, label="one link k_z A / d", size=6)
        ax.text(6, 0.4, "the node under the window sits at the hot surface and carries the lateral\nconductance of half the gap: it bridges the window edge", ha="center", fontsize=6.5)
    else:
        for x in (4.8, 5.6, 6.4, 7.2):
            dk.arrow(ax, x, zt - tcu - 0.05, x, zb + 0.2, color=dk.BLUE, width=0.9)
        dk.arrow(ax, 5.2, zt - 0.6, 3.5, zt - 0.6, color=dk.BLUE, label="sideways in the laminate", size=6)
        dk.arrow(ax, 6.8, zt - 0.6, 8.6, zt - 0.6, color=dk.BLUE)
        dk.arrow(ax, 3.4, zt - 0.1, 1.3, zt - 0.1, color=dk.HEAT, width=0.9)
        ax.text(2.3, zt + 0.15, "into the copper", fontsize=6, ha="center", color=dk.HEAT)
        dk.arrow(ax, 8.6, zt - 0.1, 10.7, zt - 0.1, color=dk.HEAT, width=0.9)
        ax.text(6, 0.4, "the heat has to cross the laminate down from the surface before it reaches the copper\nedge: a vertical gradient that one node per layer cannot hold", ha="center", fontsize=6.5)


def fig_01():
    """!
    @brief Figure 01: a board over a window, as the layered model sees it and as the laminate behaves.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 4.2, 1, 2)
    section(axs[0], "layered", "Layered model today: one node per copper layer")
    section(axs[1], "real", "What the laminate does under a part over a window")
    dk.save(fig, OUT / "fig_01_section_over_a_window.png")


def ladder(ax, n, ratio, x0, title):
    """!
    @brief The nodes through one gap: two copper nodes, n - 1 laminate nodes at the boundaries of n sub-gaps, the links between them.
    @param ax Axes.
    @param n Number of sub-gaps.
    @param ratio Grading ratio of rule.sub_gaps.
    @param x0 x of the ladder.
    @param title Label under the ladder.
    @return None.
    """
    d = 6.0
    s = RU.sub_gaps(d, n, ratio)
    z = d - np.concatenate([[0.0], np.cumsum(s)])                       # node heights from the top copper (d) to the bottom copper (0)
    dk.layer(ax, x0 - 0.6, d + 0.2, 1.2, 0.35, dk.COPPER, "")
    dk.layer(ax, x0 - 0.6, -0.55, 1.2, 0.35, dk.COPPER, "")
    for k in range(n):
        ax.plot([x0, x0], [z[k] - 0.0, z[k + 1] + 0.0], color="k", linewidth=0.8)
        ax.text(x0 + 0.25, (z[k] + z[k + 1]) / 2, f"s{k + 1}={s[k] / d * 6:.1f}", fontsize=6, va="center")
    for k, zz in enumerate(z):
        col = "k" if k in (0, n) else dk.BLUE
        ax.add_patch(Circle((x0, zz + (0.2 if k == 0 else (-0.2 if k == n else 0))), 0.13, color=col))
    ax.text(x0, -1.3, title, ha="center", fontsize=7)


def fig_02():
    """!
    @brief Figure 02: the ladder for n = 1, 2, 4 (equal) and n = 4 graded 2:1; the sub-gap thicknesses are in units of d / 6.
    @return None.
    """
    fig, ax = dk.canvas(8.5, 4.6)
    ax.set_xlim(0, 11)
    ax.set_ylim(-2, 7.2)
    for x0, n, r, t in ((1.2, 1, 1.0, "n = 1\n(the program)"), (3.7, 2, 1.0, "n = 2"), (6.2, 4, 1.0, "n = 4 equal"), (8.9, 4, 2.0, "n = 4 graded 2:1\n(thin at the copper)")):
        ladder(ax, n, r, x0, t)
    ax.text(5.5, 7.0, "Nodes through a gap of thickness d: copper nodes (black) and laminate nodes (blue) at the boundaries of the sub-gaps", ha="center", fontsize=8)
    dk.save(fig, OUT / "fig_02_node_ladder_and_grading.png")


def fig_03():
    """!
    @brief Figure 03: top view of a 30 x 30 mm board at 1 mm cells with a 6 mm window under a 6 mm part: bare cells, the margin of a gap thickness plus a cell (disc), and the cells that keep the single link.
    @return None.
    """
    n = 30
    fill = np.ones((n, n))
    fill[12:18, 12:18] = 0.0
    d, dx = 1.6e-3, 1.0e-3
    bare = fill < 1
    fig, axs = dk.canvas(9.5, 4.6, 1, 2)
    for ax, (label, rule) in zip(axs, (("margin none", RU.Rule(margin="none")), (f"margin = ceil(d/dx) + 1 = {RU.margin_cells(RU.Rule(), d, dx)} cells (disc)", RU.Rule()))):
        flag = RU.flag_cells(rule, fill, fill, d, dx)
        img = np.zeros((n, n))
        img[flag] = 1
        img[bare] = 2
        ax.axis("on")
        ax.imshow(img, origin="lower", cmap=__import__("matplotlib").colors.ListedColormap(["#e8e8e8", "#9bbf8a", "#f7d9a0"]), vmin=0, vmax=2)
        ax.add_patch(Rectangle((11.5, 11.5), 6, 6, fill=False, edgecolor="k", linewidth=1.4))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{label}: {int(flag.sum())} of {n * n} cells", fontsize=8)
    axs[1].text(0, -2.2, "light orange: no copper (window), green: margin with the nodes, grey: copper everywhere (single link); the black square is the part", fontsize=6.5)
    dk.save(fig, OUT / "fig_03_mask_of_the_cells.png")


def fig_04():
    """!
    @brief Figure 04: the laminate under the copper of a one-layer board: two nodes in every cell (laminate.py) against the nodes only next to the copper edge, the single link under solid copper.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 4.2, 1, 2)
    for ax, mode in zip(axs, ("old", "rule")):
        ax.set_xlim(0, 12)
        ax.set_ylim(-0.8, 6.2)
        ax.set_title("laminate.py: two nodes under the copper in every cell" if mode == "old" else "the rule: nodes where the copper is partly absent, plus a margin", fontsize=9)
        dk.layer(ax, 0.5, 1.0, 11, 3.0, dk.FR4)
        dk.layer(ax, 3.5, 4.0, 5, 0.25, dk.COPPER, "copper pad")
        dk.layer(ax, 4.5, 4.25, 3, 0.7, "#888888", "part")
        for x in range(1, 12):
            flagged = mode == "old" or x < 4 or x > 8                       # the rule: bare cells and the margin into the pad
            ax.add_patch(Circle((x, 4.1 if 3.5 <= x <= 8.5 else 3.95), 0.1, color="k"))
            ax.add_patch(Circle((x, 1.0), 0.1, color=dk.BLUE))              # the bottom node, always there
            if mode == "old":
                ax.add_patch(Circle((x, 2.6), 0.1, color=dk.BLUE))
            elif flagged:
                for z in (3.4, 2.7, 1.9):
                    ax.add_patch(Circle((x, z), 0.1, color=dk.BLUE))
            else:
                ax.plot([x, x], [1.0, 4.1], color="k", linewidth=0.7)       # the single link
        ax.text(6, -0.55, "bottom film acts on the last node of every cell" if mode == "old" else "under solid copper: one link through the laminate to the bottom node", ha="center", fontsize=7)
    dk.save(fig, OUT / "fig_04_one_layer_laminate_path.png")


def fig_05():
    """!
    @brief Figure 05: the four treatments of the program's investigations and the one rule, as a table of what each does.
    @return None.
    """
    fig, ax = dk.canvas(10.5, 3.6)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    heads = ["", "where", "nodes", "vertical path", "one-layer board"]
    rows = [("program", "none (multilayer); every cell (one layer)", "1 per gap; 2 under the copper", "d", "2 nodes everywhere"),
            ("gap-subdivision", "bare cells + margin", "3 to 4, graded 2:1", "d", "not treated"),
            ("bare-spot-under-source", "bare cells + margin, gaps from 0.5 mm", "1 / 2 / 4 by cuts", "d + (1-f) t/2 per side + face term", "not treated"),
            ("gerber-models R2", "every cell (one layer)", "2 gave -5.5 to -13.6 %; 8 gave -1.9 and -5.3 %", "-", "more nodes"),
            ("one rule (this folder)", "bare cells + margin, every gap incl. the laminate of a one-layer board", "n = min(n_max, ceil(d / s_max))", "as bare-spot, decided here", "same rule, single link under solid copper")]
    xs = [0.1, 2.0, 4.3, 6.4, 8.2]
    for x, h in zip(xs, heads):
        ax.text(x, 5.6, h, fontsize=8, fontweight="bold")
    for i, r in enumerate(rows):
        y = 4.6 - i * 0.95
        ax.add_patch(Rectangle((0.05, y - 0.35), 9.9, 0.85, facecolor="#f4f4f4" if i < 4 else "#dff0d8", edgecolor="none"))
        for x, t in zip(xs, r):
            ax.text(x, y + 0.05, "\n".join(__import__("textwrap").wrap(t, 24)), fontsize=6.5, va="center")
    dk.save(fig, OUT / "fig_05_five_constructions.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for f in (fig_01, fig_02, fig_03, fig_04, fig_05):
        f()
        print("wrote", f.__name__)
