#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the point via: the section of a via with the heat entering each plane, the via on grids of different cell, the Peaceman well, the footprint of
       a via on the cells, and the network of the mean-potential coupling.
@details Figures 01 to 05 of figures/ (the data figures 06 and later are drawn by make_figures.py). Only the lattice kernel of lib/lattice.py is computed (for the footprint maps);
         no study is run.
         Files: fig_01_via_section_and_flux.png, fig_02_via_on_the_cell_grid.png, fig_03_peaceman_well.png, fig_04_footprint_of_the_barrel.png, fig_05_mean_potential_coupling.png.
         Usage: python research/point-via-convergence/scripts/make_diagrams.py   (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import diagram_kit as dk                                                    # noqa: E402
import lattice                                                              # noqa: E402
import viakernel as vk                                                      # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_section(path):
    """!
    @brief Section of a via through a four-layer board with the heat flowing sideways in the planes and into the barrel (the situation behind the sheet model).
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 4.8, 1, 2, ratios=[1.35, 1])
    a.set_xlim(0, 13)
    a.set_ylim(-1.0, 7.0)
    ys = [5.6, 3.9, 2.2, 0.5]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 12, 0.22, dk.COPPER, f"plane {k + 1}" if False else "", 7)
        a.text(12.7, y + 0.1, f"{k + 1}", fontsize=8, va="center")
        if k < 3:
            dk.layer(a, 0.5, y - 1.48, 12, 1.48, dk.FR4)
    # the barrel: a hollow copper tube through all the planes
    a.add_patch(Rectangle((6.0, 0.5), 1.0, 5.32, facecolor="white", edgecolor="k", linewidth=0.8))
    a.add_patch(Rectangle((6.0, 0.5), 0.12, 5.32, facecolor=dk.COPPER, edgecolor="k"))
    a.add_patch(Rectangle((6.88, 0.5), 0.12, 5.32, facecolor=dk.COPPER, edgecolor="k"))
    for y in ys:
        for x0, x1 in ((1.0, 5.9), (12.0, 7.1)):
            dk.arrow(a, x0, y + 0.55, x1, y + 0.55, color=dk.HEAT, width=1.1)
    a.text(6.5, 6.4, "barrel (drill radius $r_v$)", ha="center", fontsize=8)
    a.text(3.4, 6.35, "heat spreads sideways in each plane,\nfalling as $\\ln(r/r_v)/(2\\pi S)$ towards the barrel", ha="center", fontsize=7.5, color=dk.HEAT)
    a.text(6.5, -0.45, "and goes down the barrel: $G_v = k_{Cu} A / d$ per gap", ha="center", fontsize=8)
    for y in (4.9, 3.2, 1.5):
        dk.arrow(a, 6.5, y + 0.55, 6.5, y - 0.35, color=dk.BLUE, width=1.3)
    # top view: sheet around the via, rings of equal temperature
    b.set_xlim(-3, 3)
    b.set_ylim(-3.3, 3.3)
    b.set_aspect("equal")
    for r in (2.6, 1.9, 1.3, 0.8, 0.45):
        b.add_patch(Circle((0, 0), r, fill=False, edgecolor="#555", linestyle="--", linewidth=0.8))
    b.add_patch(Circle((0, 0), 0.18, facecolor="white", edgecolor="k"))
    b.add_patch(Circle((0, 0), 0.18, fill=False, edgecolor=dk.COPPER, linewidth=3))
    for t in np.linspace(0, 2 * math.pi, 9)[:-1]:
        dk.arrow(b, 2.8 * math.cos(t), 2.8 * math.sin(t), 0.45 * math.cos(t), 0.45 * math.sin(t), color=dk.HEAT, width=1.0)
    b.text(0, -3.25, "top view of one plane: radial flow into the barrel\n(isotherms dashed, flux per unit length $\\propto 1/r$)", ha="center", fontsize=7.5, va="top")
    dk.save(fig, path)


def fig_grid(path):
    """!
    @brief The same 0.3 mm via drawn to scale on grids of 1, 0.5, 0.25 and 0.125 mm cells, with the cell that the program gives the barrel and the equivalent radius of a point sink.
    @param path Output file.
    @return None.
    """
    cells = [1.0, 0.5, 0.25, 0.125]
    fig, axs = dk.canvas(14, 4.2, 1, 4)
    rv = 0.15
    for ax, dx in zip(axs, cells):
        ax.set_xlim(-0.8, 0.8)
        ax.set_ylim(-0.8, 0.8)
        ax.set_aspect("equal")
        n = int(math.ceil(0.8 / dx)) + 1
        # grid with a cell centred on the via (the FVM puts a via at the centre of a cell when it can)
        for i in range(-n, n + 1):
            e = (i + 0.5) * dx
            ax.plot([e, e], [-0.8, 0.8], color="#999", linewidth=0.5)
            ax.plot([-0.8, 0.8], [e, e], color="#999", linewidth=0.5)
        ax.add_patch(Rectangle((-dx / 2, -dx / 2), dx, dx, facecolor="#ffe9a8", edgecolor="#b8860b", alpha=0.7))
        ax.add_patch(Circle((0, 0), rv, facecolor=dk.COPPER, edgecolor="k", alpha=0.9))
        ax.add_patch(Circle((0, 0), lattice.R_EQ_EXACT * dx, fill=False, edgecolor=dk.BLUE, linestyle="--", linewidth=1.6))
        ax.plot([0], [0], "k.", markersize=3)
        ratio = lattice.R_EQ_EXACT * dx / rv
        ax.set_title(f"cell {dx} mm\n$r_{{eq}}$ / $r_v$ = {ratio:.2f}", fontsize=9)
        ax.axis("off")
    fig.text(0.5, 0.02, "copper = the via (drill 0.3 mm, radius 0.15 mm); yellow = the cell that holds the whole barrel in the program; dashed blue = the hole the stencil sees, "
             "$r_{eq} = 0.1985\\,\\Delta x$", ha="center", fontsize=8)
    dk.save(fig, path)


def fig_peaceman(path):
    """!
    @brief The potential around a point sink on a lattice against the continuum hole: where the node temperature sits, the equivalent radius and the well resistance.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.4))
    r = np.logspace(-1.0, 1.3, 200)
    dx = 1.0
    for rv, lab, col in ((0.4, "via larger than the equivalent radius ($r_v > r_{eq}$)", dk.BLUE), (0.1, "via smaller ($r_v < r_{eq}$)", dk.HEAT)):
        a.plot(r, np.log(r / rv) / (2 * np.pi), color=col, label=f"continuum, hole $r_v = {rv}\\,\\Delta x$: {lab}", linewidth=1.4)
    xs = np.arange(1, 21)
    pot = lattice.a_of(xs, 0) / 4
    a.plot(xs, pot, "ko", markersize=3.5, label="five-point stencil, sink at the node (nodes along an axis)")
    a.plot(r, np.log(r / lattice.R_EQ_EXACT) / (2 * np.pi), "k--", linewidth=0.9, label="continuum, $r_{eq} = 0.1985\\,\\Delta x$ (fits the nodes)")
    a.axhline(0, color="#999", linewidth=0.6)
    a.set_xscale("log")
    a.set_xlabel("distance from the sink / $\\Delta x$")
    a.set_ylabel("temperature above the reference point, in units of $q/S$")
    a.set_title("a unit sink in a sheet: nodes of the stencil (reference: the sink node) and holes of the continuum (reference: their rim)", fontsize=8)
    a.legend(fontsize=6.5, loc="upper left")
    a.set_ylim(-0.4, 0.6)
    # panel b: the resistance bookkeeping as a chain
    b.axis("off")
    b.set_xlim(0, 10)
    b.set_ylim(0, 6)
    dk.box(b, 0.2, 4.4, 2.2, 1.0, "far field\n$T_\\infty$", dk.AIR)
    dk.resistor(b, 2.6, 5.6, 4.9, "$\\ln(r/r_{eq})/(2\\pi S)$ (the grid has it)")
    dk.box(b, 5.7, 4.4, 2.0, 1.0, "node of the\nvia cell", "#cfe3f5")
    dk.resistor(b, 7.8, 10.0, 4.9, "well: $\\ln(r_{eq}/r_v)/(2\\pi S)$")
    b.text(5.0, 3.6, "$r_{eq} > r_v$: add the well in series (Peaceman): the node reaches the barrel\nthrough $G_c = 2\\pi S/\\ln(r_{eq}/r_v)$", ha="center", fontsize=8)
    dk.box(b, 0.2, 1.7, 2.2, 1.0, "far field\n$T_\\infty$", dk.AIR)
    dk.resistor(b, 2.6, 5.6, 2.2, "$\\ln(r/r_{eq})/(2\\pi S)$ (too much)")
    dk.box(b, 5.7, 1.7, 2.0, 1.0, "node = barrel\n(needs less)", "#f6d0d0")
    b.text(5.0, 0.7, "$r_{eq} < r_v$ (fine cells): the point is too constricted by\n$\\ln(r_v/r_{eq})/(2\\pi S)$: a negative well, so spread the barrel instead", ha="center", fontsize=8)
    dk.save(fig, path)


def fig_footprint(path):
    """!
    @brief Footprints of a 0.3 mm via on 0.25 mm cells at three positions (centre, edge, corner of a cell): point, area weights of the disc and tuned weights, with the effective radius of each.
    @param path Output file.
    @return None.
    """
    dx, rv = 0.25e-3, 0.15e-3
    eta = math.exp(-0.25)
    pos = {"cell centre": (0.125e-3, 0.125e-3), "cell edge": (0.25e-3, 0.125e-3), "cell corner": (0.25e-3, 0.25e-3)}
    rules = {"point (program)": lambda x, y: vk.disc_weights(x, y, 0.0, dx), "area of the disc": lambda x, y: vk.disc_weights(x, y, rv, dx, 0.0, 24, "area"),
             "tuned, $r_{eff} = 0.78\\,r_v$": lambda x, y: vk.tuned_weights(x, y, eta * rv, dx) or vk.disc_weights(x, y, 0.0, dx)}
    fig, axs = dk.canvas(12, 11, 3, 3)
    for i, (rname, rule) in enumerate(rules.items()):
        for j, (pname, (x, y)) in enumerate(pos.items()):
            ax = axs[i][j]
            w = rule(x, y)
            ax.set_xlim(-1.3, 2.3)
            ax.set_ylim(-1.3, 2.3)
            ax.set_aspect("equal")
            for (ci, cj), v in w.items():
                ax.add_patch(Rectangle((cj - 0, ci - 0), 1, 1, facecolor=dk.HEAT, alpha=min(1.0, 0.15 + 2.2 * v), edgecolor="#999", linewidth=0.5))
                ax.text(cj + 0.5, ci + 0.5, f"{100 * v:.0f}", ha="center", va="center", fontsize=6)
            ax.add_patch(Circle((x / dx, y / dx), rv / dx, fill=False, edgecolor="k", linewidth=1.3))
            re = vk.effective_radius(w, dx) / rv
            ax.set_title(f"{rname}, {pname}\n$r_{{eff}}/r_v$ = {re:.2f}", fontsize=7.5)
            ax.axis("off")
    fig.text(0.5, 0.01, "share of the barrel conductance in each 0.25 mm cell (percent); circle = the via; $r_{eff}$ from the lattice potential kernel (README 2)", ha="center", fontsize=8)
    dk.save(fig, path)


def fig_network(path):
    """!
    @brief The network of the mean-potential coupling: three planes, the footprint cells averaged into one mean temperature per plane, the wells and the barrel, reduced to couplings.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 5.0, 1, 2, ratios=[1.2, 1])
    a.set_xlim(0, 12)
    a.set_ylim(0, 6)
    for k, y in enumerate((4.6, 2.9, 1.2)):
        for c in range(4):
            dk.box(a, 0.4 + 0.75 * c, y, 0.6, 0.6, "", "#cfe3f5")
        a.text(3.8, y + 0.2, f"plane {k + 1}: cells of the footprint", fontsize=7.5, va="center")
        dk.box(a, 6.2, y, 1.1, 0.6, f"$\\bar T_{k + 1}$", "#ffe9a8")
        for c in range(4):
            dk.arrow(a, 0.4 + 0.75 * c + 0.3, y + 0.62, 6.2, y + 0.35, color="#aaa", width=0.6, style="-")
        dk.resistor(a, 7.4, 9.2, y + 0.3, "$G_c$", size=7)
        dk.box(a, 9.3, y, 1.0, 0.6, f"barrel {k + 1}", dk.COPPER)
    for y in (4.6, 2.9):
        dk.resistor(a, 9.3, 10.3, y - 0.55 - 0.0, "", size=6)
    a.text(9.8, 3.95, "$G_v$", fontsize=7)
    a.text(9.8, 2.2, "$G_v$", fontsize=7)
    a.text(6.0, 0.35, "$\\bar T_k = \\sum_a w_a T_{k,a}$: the flux of plane $k$ into the barrel is spread over its cells by the weights $w_a$", ha="center", fontsize=8)
    b.set_xlim(0, 8)
    b.set_ylim(0, 6)
    b.text(4.0, 5.4, "eliminate the barrel nodes (Kron reduction)", ha="center", fontsize=9, fontweight="bold")
    for k, y in enumerate((4.2, 2.6, 1.0)):
        dk.box(b, 0.5, y, 1.5, 0.7, f"$\\bar T_{k + 1}$", "#ffe9a8")
    dk.arrow(b, 1.25, 4.15, 1.25, 3.35, style="<->", label="")
    dk.arrow(b, 1.25, 2.55, 1.25, 1.75, style="<->")
    b.annotate("", (1.9, 1.4), (1.9, 4.5), arrowprops={"arrowstyle": "<->", "connectionstyle": "arc3,rad=-0.4", "color": "k"})
    b.text(3.0, 3.1, "$G_{lm}$ between every pair\nof planes the barrel joins", fontsize=8, va="center")
    b.text(4.0, 0.2, "added to the matrix as $G_{lm}\\,(e_l\\otimes w - e_m\\otimes w)(\\cdot)^T$:\nsymmetric, zero row sum, no new unknown", ha="center", fontsize=8)
    dk.save(fig, path)


def main():
    """!
    @brief Draw the five diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_via_section_and_flux.png")
    fig_grid(OUT / "fig_02_via_on_the_cell_grid.png")
    fig_peaceman(OUT / "fig_03_peaceman_well.png")
    fig_footprint(OUT / "fig_04_footprint_of_the_barrel.png")
    fig_network(OUT / "fig_05_mean_potential_coupling.png")
    print("written", sorted(p.name for p in OUT.glob("fig_0[1-5]*.png")))


if __name__ == "__main__":
    main()
