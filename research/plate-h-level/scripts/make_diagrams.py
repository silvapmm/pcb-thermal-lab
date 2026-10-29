#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic figures of the plate level: the boundary layer of a heated vertical plate with the flow around it, the numerical domain of the 2D check, and where each level comes from.
@details No data is computed except the closed-form growth of a boundary layer (delta ~ x^(1/4), only to draw its shape).
         Writes figures/fig_01_boundary_layer_on_a_vertical_plate.png, figures/fig_02_where_the_levels_come_from.png and figures/fig_03_numerical_domain.png
         (the numbers 04 and above belong to `make_figures.py`, one numbering for both).
         Run: .venv/bin/python research/plate-h-level/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

from matplotlib.patches import Polygon, Rectangle                 # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
HOT = "#e07b6a"
HOT_LIGHT = "#f6c9c0"


def boundary_layer():
    """!
    @brief Figure 1: a heated vertical plate in still air: the layer that grows up the plate (delta ~ x^(1/4)), the velocity profile at three heights, the air drawn in from the sides, and the three places where a correlation has to do something.
    @return None.
    """
    fig, axs = dk.canvas(10.6, 5.2, 1, 2, ratios=[1.25, 1.0])
    ax = axs[0]
    ax.set_xlim(-3.2, 9.5)
    ax.set_ylim(-2.3, 10.8)
    L = 8.0
    ax.add_patch(Rectangle((-0.35, 0), 0.35, L, facecolor=HOT, edgecolor="k", linewidth=0.8))
    ax.text(-0.18, L + 0.35, "plate, T_w", ha="center", fontsize=7.5)
    xs = np.linspace(0.02, L, 200)
    d = 0.55 * xs ** 0.25                                              # thickness of the layer: delta ~ x^(1/4) (a drawing only)
    ax.add_patch(Polygon(np.vstack([[0, 0], [0, L], np.column_stack([d[::-1], xs[::-1]])]), closed=True, facecolor=HOT_LIGHT, edgecolor="none"))
    ax.plot(d, xs, color=dk.HEAT, linewidth=1.0)
    ax.text(1.3, 6.3, "thermal layer\n(pink), thickness\ndelta ~ x^(1/4)", fontsize=7, color=dk.HEAT)
    for xp in (1.5, 4.0, 7.0):
        di = 0.55 * xp ** 0.25
        eta = np.linspace(0, 1, 40)
        u = 2.2 * eta * (1 - eta) ** 2 / 0.148 * 0.35                  # shape of the velocity profile (a drawing only): zero at the wall and at the edge, peak at about a third
        ax.plot(eta * di * 1.45, xp + u * 0.8, color=dk.BLUE, linewidth=1.3)
        ax.plot([0, di * 1.45], [xp, xp], color=dk.BLUE, linewidth=0.5, linestyle=":")
    ax.text(-3.1, 9.3, "blue curves: speed u(y)\nin the layer, zero at the\nwall and at its edge", fontsize=6.6, color=dk.BLUE)
    for yy in (0.8, 3.0, 5.5):
        dk.arrow(ax, 2.9, yy, 1.4 + 0.12 * yy, yy, color=dk.BLUE, width=1.0)
    ax.text(3.2, 1.9, "air drawn in\nfrom the side", fontsize=6.6, color=dk.BLUE, va="center")
    dk.arrow(ax, 0.9, -1.9, 0.9, -0.5, color=dk.BLUE, width=1.0)
    ax.text(1.2, -1.8, "air from below", fontsize=7, color=dk.BLUE)
    dk.arrow(ax, 1.2, L + 0.4, 1.2, L + 1.8, color=dk.HEAT, width=1.6)
    ax.text(1.5, L + 1.6, "plume", fontsize=7, color=dk.HEAT)
    ax.annotate("", (-1.3, 0), (-1.3, L), arrowprops={"arrowstyle": "<->", "color": "k"})
    ax.text(-1.55, L / 2, "L", fontsize=10, ha="center")
    ax.text(-3.1, -0.9, "a. the thin-layer picture: local h falls as x^(-1/4)\n   and the mean over L is 4/3 of the local value at L", fontsize=7, va="top")
    ax.text(4.7, 0.0, "(1) leading edge: the layer is thicker than\n     x, heat is conducted: the 0.68 of\n     Churchill and Chu", fontsize=6.6, color="k")
    ax.text(4.7, 3.9, "(2) the layer: the exact solution,\n     Nu = 0.516 Ra^(1/4)", fontsize=6.6, color="k")
    ax.text(4.7, 7.2, "(3) the top: turbulence only\n     above Ra = 1e9", fontsize=6.6, color="k")
    for yy in (0.6, 4.4, 7.7):
        ax.plot([3.6, 4.6], [yy, yy], color="k", linewidth=0.6)

    ax = axs[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.3, 10.6)
    dk.box(ax, 0.3, 8.6, 9.4, 1.5, "mean Nusselt number Nu = h L / k as a function of Ra = g beta dT L^3 / (nu alpha)\nand Pr, for a vertical isothermal plate of height L", color="#eef2f7", size=7.2)
    rows = [("Ra < 1e3", "conduction and the leading edge\ndominate: no thin layer", "#f4e3c9"),
            ("1e4 < Ra < 1e8", "laminar thin layer + leading edge:\nthe range of PCBs (40 to 200 mm, 10 to 60 K:\nRa 6e4 to 3e7)", "#d7ecd2"),
            ("1e9 < Ra", "transition to turbulence at the top:\nh stops falling with height", "#e5d7ee")]
    y = 6.2
    for lab, txt, col in rows:
        dk.box(ax, 0.3, y, 2.5, 1.5, lab, color=col, size=7.5)
        dk.box(ax, 3.0, y, 6.7, 1.5, txt, color=col, size=7)
        y -= 2.0
    ax.text(0.3, 0.1, "b. the three regimes of the vertical plate", fontsize=7, va="top")
    dk.save(fig, OUT / "fig_01_boundary_layer_on_a_vertical_plate.png", "Heated vertical plate in still air: the layer, the flow and the range of Rayleigh numbers of a board")


def where_levels_come_from():
    """!
    @brief Figure 2: the genealogy of the coefficients: the exact similarity solution, its fits, the leading-edge term and the empirical 0.59.
    @return None.
    """
    fig, ax = dk.canvas(10.6, 5.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    dk.box(ax, 0.2, 5.4, 3.6, 1.3, "boundary-layer equations\n(Boussinesq, plate at Tw)", color="#eef2f7", size=7.5)
    dk.box(ax, 4.4, 5.4, 3.6, 1.3, "similarity solution\nOstrach 1953 (tables), Sparrow\nand Gregg, LeFevre", color="#cfe3f5", size=7.2, bold=True)
    dk.box(ax, 8.6, 5.4, 3.2, 1.3, "local: Nu_x = 0.387 Ra_x^(1/4)\nmean: x 4/3 = 0.5157 Ra^(1/4)\n(air, Pr 0.71)", color="#cfe3f5", size=7)
    dk.arrow(ax, 3.8, 6.05, 4.4, 6.05)
    dk.arrow(ax, 8.0, 6.05, 8.6, 6.05)
    dk.box(ax, 0.2, 3.3, 3.6, 1.3, "fit in Prandtl number\n0.670/[1+(0.492/Pr)^(9/16)]^(4/9)\n(LeFevre; Churchill and Usagi)", color="#d7ecd2", size=7)
    dk.box(ax, 4.4, 3.3, 3.6, 1.3, "Churchill and Chu laminar form\n0.68 + 0.670 Ra^(1/4)/[...]\n= exact layer + leading edge\n(the program: natural_form laminar)", color="#d7ecd2", size=7, bold=True)
    dk.box(ax, 8.6, 3.3, 3.2, 1.3, "Churchill and Chu general form\n(0.825 + 0.387 Ra^(1/6)/[...])^2\nall Ra to 1e12\n(the program's default)", color="#d7ecd2", size=7, bold=True)
    dk.arrow(ax, 10.2, 5.4, 2.0, 4.6, label="")
    dk.arrow(ax, 3.8, 3.95, 4.4, 3.95)
    dk.arrow(ax, 8.0, 3.95, 8.6, 3.95, label="")
    ax.text(8.0, 4.0, "blend with turbulent", fontsize=6, ha="center", va="bottom")
    dk.box(ax, 0.2, 1.1, 3.6, 1.3, "Squire integral method\n0.508 [Pr/(0.952+Pr)]^(1/4)\n6 % above the exact value", color="#f4e3c9", size=7)
    dk.box(ax, 4.4, 1.1, 3.6, 1.3, "0.59 Ra^(1/4) (McAdams, empirical,\n1e4 < Ra < 1e9)", color="#f4e3c9", size=7)
    dk.box(ax, 8.6, 1.1, 3.2, 1.3, "plate limit of the composite of\nBar-Cohen and Rohsenow:\nNu_b = [(24/Ra_b)^2 + (1/(0.59 Ra_b^(1/4)))^2]^(-1/2)", color="#f4e3c9", size=6.6)
    dk.arrow(ax, 8.0, 1.75, 8.6, 1.75)
    ax.text(0.2, 0.55, "pink: approximation or empirical level; blue: the exact result; green: the levels of the program. 0.59 is 14 % above the exact 0.5157; it is an empirical constant (the original paper of the composite was not obtained).", fontsize=6.5)
    dk.save(fig, OUT / "fig_02_where_the_levels_come_from.png", "Where each coefficient of the vertical plate comes from")


def numerical_domain():
    """!
    @brief Figure 3: the domain of the 2D numerical check: half plane, plate on the symmetry line, entrainment from the side and below, free outflow above.
    @return None.
    """
    fig, ax = dk.canvas(7.2, 5.6)
    ax.set_xlim(-0.6, 9)
    ax.set_ylim(-0.6, 10.2)
    ax.add_patch(Rectangle((0, 0), 8, 9.5, facecolor="#f7fbff", edgecolor="k", linewidth=0.9))
    ax.add_patch(Rectangle((-0.12, 2.0), 0.12, 3.0, facecolor=HOT, edgecolor="k", linewidth=0.8))
    ax.text(-0.35, 3.5, "plate", rotation=90, ha="center", va="center", fontsize=8)
    ax.text(0.2, 1.0, "symmetry line (psi = 0, dT/dx = 0)", fontsize=7, rotation=90, va="center")
    ax.text(0.2, 7.2, "symmetry line (psi = 0, dT/dx = 0)", fontsize=7, rotation=90, va="center")
    ax.text(4.0, 9.0, "top: outflow, d/dy of T, omega and psi = 0", fontsize=7.5, ha="center")
    ax.text(4.0, 0.3, "bottom: inflow at T = 0, omega = 0, dpsi/dy = 0", fontsize=7.5, ha="center")
    ax.text(7.9, 4.7, "side: T = 0, omega = 0,\ndpsi/dx = 0 (air drawn in)", fontsize=7.5, ha="right", va="center")
    for yy in (1.2, 3.0, 4.8, 6.5):
        dk.arrow(ax, 7.6, yy, 6.6, yy, color=dk.BLUE, width=1.1)
    for xx in (2.0, 4.0, 6.0):
        dk.arrow(ax, xx, 0.7, xx, 1.7, color=dk.BLUE, width=1.1)
    for xx in (1.0, 2.5):
        dk.arrow(ax, xx, 6.0, xx, 8.0, color=dk.HEAT, width=1.5)
    xs = np.linspace(0.02, 3.0, 80)
    ax.fill_betweenx(2.0 + xs, 0, 0.55 * xs ** 0.25 * 0.5, color=HOT_LIGHT)
    ax.text(3.0, 5.5, "plate height L = 1 (3 L wide, 1.5 L below,\n3 L above in the base runs; 6 L wide, 3 L below,\n6 L above in the check)", fontsize=6.8)
    ax.text(-0.5, -0.45, "grid clustered at the plate and at its two ends; steady state by pseudo-time marching", fontsize=6.8)
    dk.save(fig, OUT / "fig_03_numerical_domain.png", "Domain of the 2D numerical check of a thin isothermal plate in open air")


if __name__ == "__main__":
    boundary_layer()
    where_levels_come_from()
    numerical_domain()
