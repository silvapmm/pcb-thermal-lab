#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: a footprint with a dense via core and the heat paths, the resistance networks of the three Lumped treatments, the cell problem of the link, and the unit cell of the published microspreading case.
@details Figures 01 to 05 of figures/ (the data figures 06 and later are drawn by make_figures.py). No study is run; only closed forms are evaluated for the curve of figure 03.
         Files: fig_01_footprint_core_section.png, fig_02_networks_program_series_zones.png, fig_03_cell_problem_link.png, fig_04_microspreading_unit_cell.png,
         fig_05_where_the_lateral_resistance_sits.png.
         Usage: python research/lumped-via-groups/scripts/make_diagrams.py   (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[1] / "lumped-analytic-vias" / "lib"))

import constriction as cr                                                   # noqa: E402
import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_section(path):
    """!
    @brief Section and top view of a footprint with a dense via core: the heat of the rest of the footprint has two ways down.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 5.2, 1, 2, ratios=[1.5, 1])
    a.set_xlim(0, 15)
    a.set_ylim(-1.4, 7.4)
    ys = [5.4, 3.5, 1.6]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 14, 0.25, dk.COPPER)
        a.text(14.7, y + 0.12, f"plane {k + 1}", fontsize=7, va="center", ha="right")
        if k < 2:
            dk.layer(a, 0.5, y - 1.65, 14, 1.65, dk.FR4)
    # source on the top plane over the footprint
    a.add_patch(Rectangle((3.0, 5.75), 9.0, 0.45, facecolor="#444444", edgecolor="k"))
    a.text(7.5, 5.98, "part: uniform power over the footprint", color="white", fontsize=7.5, ha="center", va="center")
    # barrels in the core
    for x in (6.2, 6.9, 7.5, 8.1, 8.8):
        a.add_patch(Rectangle((x - 0.07, 1.6), 0.14, 4.05, facecolor=dk.COPPER, edgecolor="k", linewidth=0.6))
    a.plot([5.7, 5.7], [1.0, 7.0], "k:", lw=0.8)
    a.plot([9.3, 9.3], [1.0, 7.0], "k:", lw=0.8)
    a.text(7.5, 6.9, "core C (dense vias)", ha="center", fontsize=8, fontweight="bold")
    a.text(4.3, 6.9, "rest of the footprint A", ha="center", fontsize=8, fontweight="bold")
    a.text(10.7, 6.9, "rest of the footprint A", ha="center", fontsize=8, fontweight="bold")
    # lateral flow in the top plane towards the core, vertical flow through the dielectric of A, barrels in C
    for x0, x1 in ((3.3, 5.5), (11.7, 9.5)):
        dk.arrow(a, x0, 5.15, x1, 5.15, color=dk.HEAT, width=1.5)
    a.text(4.4, 5.3, "sideways in the plane", fontsize=7, color=dk.HEAT, ha="center")
    for x in (3.6, 4.6, 10.4, 11.4):
        dk.arrow(a, x, 5.3, x, 4.0, color=dk.BLUE, width=1.3)
    a.text(1.7, 4.2,"straight down\nthrough the\ndielectric", fontsize=7, color=dk.BLUE, ha="center")
    for y in (4.6, 2.7):
        dk.arrow(a, 7.5, y + 0.3, 7.5, y - 0.45, color=dk.HEAT, width=1.8)
    a.text(7.5, 0.55, "barrels: all the heat of C and what comes sideways from A", fontsize=7.5, ha="center")
    a.text(7.5, -0.95, "in the earlier group term the sideways resistance sat in series with the barrel, as if A had no way down of its own", fontsize=7.5, ha="center", color="#7a0000")
    # top view
    b.set_xlim(0, 10)
    b.set_ylim(0, 10)
    b.set_aspect("equal")
    b.add_patch(Rectangle((0.5, 0.5), 9.0, 9.0, facecolor="#f4f4f4", edgecolor="k"))
    b.add_patch(Rectangle((1.5, 1.5), 7.0, 7.0, facecolor="#ffd9d0", edgecolor="k", linewidth=1.4))
    b.add_patch(Rectangle((3.4, 3.4), 3.2, 3.2, facecolor="#f2b27a", edgecolor="k", linewidth=1.4))
    for i in range(5):
        for j in range(5):
            b.add_patch(Circle((3.7 + 0.6 * i, 3.7 + 0.6 * j), 0.12, facecolor="#7a4b13", edgecolor="k", linewidth=0.5))
    b.text(5.0, 5.0, "C", fontsize=15, ha="center", va="center", alpha=0.0)
    b.text(5.0, 2.45, "A", fontsize=12, ha="center", fontweight="bold")
    b.text(5.0, 7.55, "A", fontsize=12, ha="center", fontweight="bold")
    b.text(5.0, 0.95, "rings outside the footprint (as in the program)", fontsize=7.5, ha="center")
    b.text(5.0, 9.0, "top view: footprint, core, outside rings", fontsize=8, ha="center")
    b.text(8.7, 5.0, "footprint", fontsize=7, rotation=90, va="center")
    dk.arrow(b, 6.9, 5.0, 6.65, 5.0, color=dk.HEAT)
    dk.arrow(b, 3.1, 5.0, 3.35, 5.0, color=dk.HEAT)
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


def fig_networks(path):
    """!
    @brief The network of two layers under a footprint in the program, with the series group term, and with the two zones.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.0, 1, 3)
    titles = ["program: one node per layer", "earlier group term: Krogh well of the cluster in series", "two zones: the link is lateral, in parallel with the dielectric"]
    for ax, t in zip(axs, titles):
        ax.set_xlim(0, 6)
        ax.set_ylim(-0.6, 5.6)
        ax.text(3, 5.4, t, ha="center", fontsize=8.5, fontweight="bold")
        ax.text(0.15, 4.0, "layer 1", fontsize=7)
        ax.text(0.15, 1.2, "layer 2", fontsize=7)
    # (a) program
    ax = axs[0]
    _node(ax, 3, 4, "F1")
    _node(ax, 3, 1.2, "F2")
    ax.plot([3, 3], [3.68, 1.52], "k", lw=1.2)
    ax.text(3.15, 2.6, "dielectric + barrels\n(gz, parallel)", fontsize=7)
    _node(ax, 5.2, 4, "r1")
    dk.resistor(ax, 3.32, 4.88, 4.0, "")
    ax.text(3, 0.2, "no lateral resistance inside the footprint:\nthe cluster sees the footprint mean", fontsize=7, ha="center")
    # (b) series macro
    ax = axs[1]
    _node(ax, 3, 4, "F1")
    _node(ax, 3, 1.2, "F2")
    _node(ax, 5.2, 4, "r1")
    dk.resistor(ax, 3.32, 4.88, 4.0, "")
    ax.plot([3, 3], [3.68, 3.35], "k", lw=1.2)
    ax.add_patch(Rectangle((2.82, 2.85), 0.36, 0.5, fill=False, edgecolor="#7a0000", linewidth=1.8))
    ax.text(3.35, 3.05, "$R_{macro}$", fontsize=8, color="#7a0000")
    ax.plot([3, 3], [2.85, 2.5], "k", lw=1.2)
    ax.add_patch(Rectangle((2.82, 1.95), 0.36, 0.5, fill=False, edgecolor="k", linewidth=1.2))
    ax.text(3.35, 2.15, "barrels", fontsize=7)
    ax.plot([3, 3], [1.95, 1.52], "k", lw=1.2)
    ax.text(3, 0.2, "all the heat of the footprint is taken to cross\nR_macro: the dielectric path of A is not in parallel", fontsize=7, ha="center", color="#7a0000")
    # (c) zones
    ax = axs[2]
    for (x, lab) in ((1.2, "A"), (3.2, "C")):
        _node(ax, x, 4, lab + "1", "#ffd9d0" if lab == "A" else "#f2b27a")
        _node(ax, x, 1.2, lab + "2", "#ffd9d0" if lab == "A" else "#f2b27a")
    ax.plot([1.2, 1.2], [3.68, 1.52], "k", lw=1.2)
    ax.text(0.2, 2.6, "dielectric\nof A", fontsize=7)
    ax.plot([3.2, 3.2], [3.68, 1.52], "k", lw=1.2)
    ax.text(3.35, 2.6, "barrels + wells\n+ dielectric of C", fontsize=7)
    dk.resistor(ax, 1.52, 2.88, 4.0, "$R_{AC}$", color="#7a0000")
    dk.resistor(ax, 1.52, 2.88, 1.2, "$R_{AC}$", color="#7a0000")
    _node(ax, 5.2, 4, "r1")
    dk.resistor(ax, 3.52, 4.88, 4.0, "")
    ax.text(3, 0.2, "A and C each have their own vertical path;\nthe lateral link joins them in every layer", fontsize=7, ha="center")
    dk.save(fig, path)


def fig_cell(path):
    """!
    @brief The cell problem that gives the link, and the lossless link against the exact one.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12, 4.6, 1, 2, ratios=[1, 1.15])
    a.set_xlim(-6, 6)
    a.set_ylim(-6, 6)
    a.set_aspect("equal")
    a.add_patch(Circle((0, 0), 5, facecolor="#ffd9d0", edgecolor="k"))
    a.add_patch(Circle((0, 0), 2.4, facecolor="#f2b27a", edgecolor="k"))
    a.annotate("", (2.4, 0), (0, 0), arrowprops={"arrowstyle": "<->"})
    a.text(1.2, -0.55, "$r_c$", ha="center", fontsize=10)
    a.annotate("", (0, 0), (-3.5, -3.5), arrowprops={"arrowstyle": "<->"})
    a.text(-2.5, -1.8, "$a$", ha="center", fontsize=10)
    a.text(0, 0.7, "core: ideal sink\n(vias)", ha="center", fontsize=7.5)
    a.text(0, 3.4, "annulus: uniform source q,\nsheet S, loss g to the plane below", ha="center", fontsize=7.5)
    a.text(0, -5.7, "$S(T''+T'/r) - gT + q = 0,\\ T(r_c)=0,\\ T'(a)=0$", ha="center", fontsize=8.5)
    for ang in np.linspace(0.3, 2 * math.pi, 7)[:-1]:
        dk.arrow(a, 4.3 * math.cos(ang), 4.3 * math.sin(ang), 3.0 * math.cos(ang), 3.0 * math.sin(ang), color=dk.HEAT, width=1.1)
    b.axis("on")
    x = np.linspace(0.01, 3.0, 60)
    for rho, c in ((0.15, "#1f77b4"), (0.3, "#2ca02c"), (0.6, "#d62728")):
        # lossless Krogh against the lossy closed form of the same cell (both from lib/constriction.py)
        S, aa = 0.0136, 5.6e-3
        ratio = [cr.krogh(S, aa, rho * aa) / cr.cell_with_loss(S, S * (xx / aa) ** 2, rho * aa, aa, 1.0)["R_c"] for xx in x]
        b.plot(x, ratio, color=c, label=f"$r_c/a$ = {rho}")
    b.axhline(1.0, color="k", lw=0.8)
    b.set_xlabel("$a / \\lambda$, with $\\lambda = \\sqrt{S/g}$ the fin length of the plane")
    b.set_ylabel("lossless link / lossy link")
    b.set_title("the lossless link overstates the resistance as the plane loses heat (closed forms)", fontsize=8)
    b.legend(fontsize=8)
    b.grid(alpha=0.3)
    dk.save(fig, path)


def fig_fish(path):
    """!
    @brief The published unit cell (Fish): the isothermal faces give the rule of mixtures; a flux or convection face makes the heat spread sideways in the weak material first.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.6, 1, 2)
    for ax, iso in zip(axs, (True, False)):
        ax.set_xlim(0, 8)
        ax.set_ylim(-1.2, 6.8)
        ax.add_patch(Rectangle((1, 0.5), 6, 4.6, facecolor="#dbe9f7", edgecolor="k"))
        ax.add_patch(Rectangle((3.4, 0.5), 1.2, 4.6, facecolor=dk.COPPER, edgecolor="k"))
        ax.text(4.0, 2.8, "via\n$k_v$ = 400", ha="center", fontsize=8)
        ax.text(1.9, 1.0, "glass $k_s$ = 1", fontsize=8)
        if iso:
            ax.plot([1, 7], [5.1, 5.1], color="#1f77b4", lw=4)
            ax.plot([1, 7], [0.5, 0.5], color="#1f77b4", lw=4)
            ax.text(4, 6.2, "isothermal faces: 1D, rule of mixtures", ha="center", fontsize=9, fontweight="bold")
            for x in (1.6, 2.4, 3.0, 5.0, 5.6, 6.4):
                dk.arrow(ax, x, 4.9, x, 0.8, color=dk.HEAT, width=1.1)
            for x in (3.7, 4.0, 4.3):
                dk.arrow(ax, x, 4.9, x, 0.8, color=dk.HEAT, width=2.2)
            ax.text(4, -0.6, "$k_{eff}=\\phi k_v+(1-\\phi)k_s$", ha="center", fontsize=9)
        else:
            ax.text(4, 6.2, "flux or convection on the face: microspreading", ha="center", fontsize=9, fontweight="bold")
            for x in (1.6, 2.4, 3.0, 5.0, 5.6, 6.4):
                dk.arrow(ax, x, 5.9, x, 5.15, color=dk.HEAT, width=1.1)
            for x0, x1 in ((1.6, 3.35), (6.4, 4.65)):
                dk.arrow(ax, x0, 4.7, x1, 4.35, color=dk.HEAT, width=1.1)
                dk.arrow(ax, x0, 3.9, x1, 3.5, color=dk.HEAT, width=1.0)
            for x in (3.7, 4.0, 4.3):
                dk.arrow(ax, x, 3.0, x, 0.8, color=dk.HEAT, width=2.2)
            ax.plot([1, 7], [0.5, 0.5], color="#1f77b4", lw=4)
            ax.text(4, -0.6, "$R_{msp}$ in series with $R_{1D}$; 1240 K/W (thick cell, flux face)", ha="center", fontsize=9)
    dk.save(fig, path)


def fig_where(path):
    """!
    @brief Top views of one footprint with a core: where each treatment puts the lateral resistance between the rest of the footprint and the core.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.6, 1, 3)
    titles = ["program: none inside the footprint", "group term: in series with the barrel", "two zones: a link, in parallel"]
    for k, ax in enumerate(axs):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal")
        ax.text(5, 9.4, titles[k], ha="center", fontsize=9, fontweight="bold")
        ax.add_patch(Rectangle((1, 1.4), 8, 7.2, facecolor="#ffd9d0", edgecolor="k", linewidth=1.3))
        ax.add_patch(Rectangle((3.4, 3.2), 3.2, 3.6, facecolor="#f2b27a", edgecolor="k", linewidth=1.3))
        if k == 0:
            ax.text(5, 5, "one node\n(mean of the\nfootprint)", ha="center", va="center", fontsize=8)
        if k == 1:
            for ang in np.linspace(0, 2 * math.pi, 9)[:-1]:
                dk.arrow(ax, 5 + 3.9 * math.cos(ang), 5 + 3.3 * math.sin(ang), 5 + 1.9 * math.cos(ang), 5 + 1.9 * math.sin(ang), color="#7a0000", width=1.3)
            ax.text(5, 0.6, "$R_{macro}$ added to every barrel path", ha="center", fontsize=8, color="#7a0000")
            ax.text(5, 5, "C", ha="center", va="center", fontsize=12, fontweight="bold")
        if k == 2:
            for ang in np.linspace(0, 2 * math.pi, 9)[:-1]:
                dk.arrow(ax, 5 + 3.9 * math.cos(ang), 5 + 3.3 * math.sin(ang), 5 + 1.9 * math.cos(ang), 5 + 1.9 * math.sin(ang), color=dk.HEAT, width=1.3)
            ax.text(5, 0.6, "$R_{AC}$ between the two nodes of each layer", ha="center", fontsize=8, color=dk.HEAT)
            ax.text(5, 5, "C", ha="center", va="center", fontsize=12, fontweight="bold")
            ax.text(2.2, 7.8, "A", fontsize=12, fontweight="bold")
    dk.save(fig, path)


def main():
    """!
    @brief Draw the five figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_section(OUT / "fig_01_footprint_core_section.png")
    fig_networks(OUT / "fig_02_networks_program_series_zones.png")
    fig_cell(OUT / "fig_03_cell_problem_link.png")
    fig_fish(OUT / "fig_04_microspreading_unit_cell.png")
    fig_where(OUT / "fig_05_where_the_lateral_resistance_sits.png")


if __name__ == "__main__":
    main()
