#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situations of the two paper studies (no data, no solver): the via unit cell of the measured samples with the two boundary conditions, Shen's diode on a via array with its
       network, and the thick anisotropic laminate under a small source with the orthotropic transformation and the program's laminate nodes.
@details Figures 01 to 03 of figures/ (the data figure 04 is drawn by make_figures.py, one numbering). Only symbols and numbers that the README quotes from the sources appear.
         Files: fig_01_via_cell_and_boundary_conditions.png, fig_02_shen_diode_on_vias.png, fig_03_thick_laminate_and_nodes.png.
         Usage: .venv/bin/python research/paper-case-studies/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"
OUT.mkdir(exist_ok=True)


def curve(ax, x0, y0, x1, y1, color=dk.HEAT, rad=0.3, lw=1.4):
    """!
    @brief A curved heat-flow arrow.
    @param ax Axes.
    @param x0 Start x.
    @param y0 Start y.
    @param x1 End x.
    @param y1 End y.
    @param color Colour.
    @param rad Curvature of the arc.
    @param lw Line width.
    @return None.
    """
    ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "->", "color": color, "linewidth": lw, "connectionstyle": f"arc3,rad={rad}"})


def via_section(ax, mode, title):
    """!
    @brief Section of a sample (one via, FR-4, optional foil) with the heat paths of one boundary condition.
    @param ax Axes.
    @param mode "iso" (isothermal faces: the flux-meter test bed of the thesis, three parallel vertical paths) or "flux" (a uniform flux into the foil and a bottom held isothermal: the program).
    @param title Title.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.2, 8.2)
    ax.set_title(title, fontsize=9)
    dk.layer(ax, 1, 1, 8, 5, dk.FR4)
    ax.text(2.6, 3.5, "FR-4", ha="center", fontsize=7)
    foil = mode == "flux"
    if foil:
        dk.layer(ax, 1, 6, 8, 0.3, dk.COPPER)
        dk.layer(ax, 1, 0.7, 8, 0.3, dk.COPPER)
        ax.text(9.1, 6.15, "foil", fontsize=7, va="center")
    dk.layer(ax, 4.4, 0.7 if foil else 1, 0.25, 5.6 if foil else 5, dk.COPPER)              # the barrel wall (left)
    dk.layer(ax, 5.35, 0.7 if foil else 1, 0.25, 5.6 if foil else 5, dk.COPPER)             # the barrel wall (right)
    dk.layer(ax, 4.65, 1, 0.7, 5, dk.AIR)
    ax.text(5.0, 1.5, "air", ha="center", fontsize=6)
    ax.text(5.0, 3.5, "D_i", ha="center", fontsize=7, rotation=90, va="center", alpha=0.0)
    if mode == "iso":
        ax.add_patch(Rectangle((0.5, 6.0), 9, 0.7, facecolor=dk.METAL, edgecolor="k"))
        ax.add_patch(Rectangle((0.5, 0.3), 9, 0.7, facecolor=dk.METAL, edgecolor="k"))
        ax.text(5, 6.35, "flux meter, T top uniform", ha="center", va="center", fontsize=7)
        ax.text(5, 0.65, "flux meter, T bottom uniform", ha="center", va="center", fontsize=7)
        for x in (2.0, 3.2, 6.8, 8.0):
            dk.arrow(ax, x, 5.9, x, 1.1, color=dk.HEAT)
        for x in (4.5, 5.5):
            dk.arrow(ax, x, 5.9, x, 1.1, color=dk.HEAT, width=2.4)
        ax.text(5, 7.5, "three parallel paths: copper, FR-4, air; field one-dimensional", ha="center", fontsize=7)
    else:
        ax.text(5, 7.6, "heater: uniform flux over the foil", ha="center", fontsize=7)
        for x in (1.6, 2.6, 3.6, 6.4, 7.4, 8.4):
            dk.arrow(ax, x, 7.2, x, 6.4, color=dk.HEAT)
        for x0, x1 in ((1.6, 4.4), (3.6, 4.4), (8.4, 5.6), (6.4, 5.6)):
            curve(ax, x0, 6.15, x1, 6.15, rad=0.0, lw=1.0)
        ax.text(5, 5.0, "constriction of the heat\nin the foil on its way\ninto the barrel", ha="center", fontsize=7, color=dk.HEAT)
        dk.arrow(ax, 5.0, 0.7, 5.0, -0.5, color=dk.BLUE)
        ax.text(5.9, -0.6, "bottom held at T_amb (h large)", fontsize=7, color=dk.BLUE)


def fig_01():
    """!
    @brief Figure 1: the samples of Soleymani Koohbanani (2016) and the two boundary conditions.
    @return None.
    """
    fig, axs = dk.canvas(12.5, 4.6, 1, 3, ratios=[1, 1.1, 1.1])
    ax = axs[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_title("(a) plan of the unit cells (Fig. 28 of the thesis)", fontsize=9)
    ax.add_patch(Rectangle((0.5, 4.3), 3.6, 3.2, fill=False, edgecolor="k"))
    ax.add_patch(Circle((2.3, 5.9), 0.55, facecolor=dk.COPPER, edgecolor="k"))
    ax.text(2.3, 7.7, "straight: u x u, one via", ha="center", fontsize=7)
    ax.add_patch(Rectangle((5.3, 4.3), 3.6, 3.2, fill=False, edgecolor="k"))
    ax.add_patch(Circle((5.3 + 0.9, 4.3 + 0.8), 0.55, facecolor=dk.COPPER, edgecolor="k"))
    ax.add_patch(Circle((5.3 + 2.7, 4.3 + 2.4), 0.55, facecolor=dk.COPPER, edgecolor="k"))
    ax.text(7.1, 7.7, "staggered: v x v, two vias", ha="center", fontsize=7)
    ax.text(5, 3.5, "nine samples, four arrangements (spacing, pitch):\n(2.5, 2.5) (2.5, 1.25) (1.25, 1.25) (1, 1) mm\nD_o 0.65, 0.55, 0.40 mm; wall 0.02 mm (not 0.04)", ha="center", fontsize=7, va="top")
    ax.text(5, 1.0, "Fig. 33 shows one measured marker per\narrangement (4), not one per sample (9)", ha="center", fontsize=7, color=dk.HEAT)
    via_section(axs[1], "iso", "(b) the test bed: isothermal faces")
    via_section(axs[2], "flux", "(c) the program: a heater and a foil")
    dk.save(fig, OUT / "fig_01_via_cell_and_boundary_conditions.png", "Study S1: the measured through-plane via samples and the condition each side imposes")


def fig_02():
    """!
    @brief Figure 2: Shen's diode on a via array on a heatsink, the heat paths and the resistance network of Table II.
    @return None.
    """
    fig, axs = dk.canvas(12.0, 5.0, 1, 2, ratios=[1.05, 1])
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)
    ax.set_title("(a) section: DPAK on a via array over a heatsink", fontsize=9)
    dk.layer(ax, 1, 5.4, 10, 0.3, dk.COPPER)
    dk.layer(ax, 1, 3.0, 10, 2.4, dk.FR4, "FR-4, 1.6 mm")
    dk.layer(ax, 1, 2.7, 10, 0.3, dk.COPPER)
    dk.layer(ax, 1, 0.4, 10, 2.3, dk.METAL, "heatsink (TIM below the board)")
    for x in (4.4, 5.0, 5.6, 6.2, 6.8, 7.4):
        dk.layer(ax, x, 2.7, 0.2, 3.0, dk.COPPER)
    dk.layer(ax, 4.0, 5.7, 4.0, 0.5, dk.METAL, "tab (die pad)")
    dk.layer(ax, 4.0, 6.2, 4.0, 1.1, "#d9d9d9", "mould, die")
    dk.arrow(ax, 6.0, 6.0, 6.0, 5.3, color=dk.HEAT, width=2.0)
    for x in (4.8, 6.0, 7.2):
        dk.arrow(ax, x, 5.2, x, 2.5, color=dk.HEAT)
    for x in (3.2, 8.8):
        curve(ax, 5.0 if x < 6 else 7.0, 7.2, x, 7.9, rad=-0.3 if x < 6 else 0.3)
    ax.text(6.0, 8.2, "top case to ambient", ha="center", fontsize=7, color=dk.HEAT)
    ax.text(10.9, 1.5, "to ambient", fontsize=7, rotation=90, va="center")
    ax = axs[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)
    ax.set_title("(b) the network of Fig. 22 behind Table II", fontsize=9)
    ax.plot([0.5, 0.5], [1.5, 6.5], color="k")
    ax.text(0.2, 4.0, "junction P", rotation=90, va="center", fontsize=7)
    dk.resistor(ax, 0.5, 3.0, 6.5, "theta_jt (44.12)")
    dk.resistor(ax, 3.0, 5.5, 6.5, "theta_ta (300 to 450)")
    ax.text(5.6, 6.5, "T_amb", fontsize=7, va="center")
    dk.resistor(ax, 0.5, 2.5, 1.5, "theta_jc (2.47)")
    dk.resistor(ax, 2.5, 4.5, 1.5, "theta_via")
    dk.resistor(ax, 4.5, 6.5, 1.5, "solder, TIM, theta_ha")
    ax.text(6.6, 1.5, "T_amb", fontsize=7, va="center")
    ax.plot([3.0, 3.0], [6.5, 6.5], "ko")
    ax.text(3.0, 7.3, "top case T_t (measured by IR)", ha="center", fontsize=7, color=dk.HEAT)
    ax.text(6.0, 4.0, "psi_ta = (T_t - T_a) / P = theta_ta S / (theta_jt + theta_ta + S)\nS = theta_jc + theta_via + (the rest) = psi_ta (theta_jt + theta_ta) / (theta_ta - psi_ta)\n(the paper's eq. 42, psi_ta (1 + theta_jt / theta_ta), drops a term)\ntheta_ta from Fig. 20 (plot); the rest and the array extent are not given:\nonly CONTRASTS between rows are used", fontsize=7, va="center")
    dk.save(fig, OUT / "fig_02_shen_diode_on_vias.png", "Study S1 part D: Shen and others (2020), Table II as differences")


def fig_03():
    """!
    @brief Figure 3: the thick anisotropic laminate under a small source: the real heat paths, the orthotropic transformation of Muzychka and others (2004) and the program's laminate nodes.
    @return None.
    """
    fig, axs = dk.canvas(13.0, 4.8, 1, 3, ratios=[1.1, 1, 1.1])
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 7.5)
    ax.set_title("(a) the real laminate: heat spreads sideways\n(half of the symmetric board; source a, channel c, thickness t)", fontsize=9)
    dk.layer(ax, 0.5, 1.0, 10.5, 4.5, dk.FR4)
    dk.layer(ax, 0.5, 5.5, 2.5, 0.3, dk.HEAT)
    ax.text(1.7, 6.3, "source a", ha="center", fontsize=7)
    for k, (xe, ye, rad) in enumerate(((3.5, 1.6, -0.2), (5.5, 1.5, -0.25), (8.0, 1.4, -0.3), (10.5, 1.3, -0.3))):
        curve(ax, 1.0 + 0.5 * k, 5.4, xe, ye, rad=rad, lw=1.0)
    ax.text(5.5, 3.5, "k_xy (in plane) > k_z (through)", ha="center", fontsize=7)
    dk.arrow(ax, 6.0, 0.9, 6.0, 0.1, color=dk.BLUE)
    ax.text(6.3, 0.35, "base: film h", fontsize=7, color=dk.BLUE)
    ax.annotate("", (11.0, 1.0), (11.0, 5.5), arrowprops={"arrowstyle": "<->"})
    ax.text(11.2, 3.2, "t", fontsize=8)
    ax.annotate("", (0.5, 7.0), (11.0, 7.0), arrowprops={"arrowstyle": "<->"})
    ax.text(5.8, 7.1, "c (adiabatic side at x = c: symmetry)", ha="center", fontsize=7)
    ax = axs[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 9.5)
    ax.set_title("(b) equations 48-51: stretch z by 1 / gamma,\ngamma = sqrt(k_z / k_xy); k_eff = sqrt(k_xy k_z)", fontsize=9)
    dk.layer(ax, 0.5, 4.0, 5.0, 2.0, dk.FR4, "orthotropic\nt, k_xy, k_z")
    dk.layer(ax, 6.5, 2.0, 5.0, 6.0, "#c9dfb9", "isotropic\nt_eff = t / gamma\nk_eff")
    dk.arrow(ax, 5.6, 5.0, 6.4, 5.0, color="k", width=2.0)
    ax.text(3.0, 3.0, "gamma < 1 for FR-4\n(k_z < k_xy): the\nequivalent slab is thicker", ha="center", fontsize=7)
    ax.text(9.0, 1.0, "R_s from equation 50 (series), per watt of the source\nR_total = R_s + t / (4 k_z c d) + 1 / (4 h c d)", ha="center", fontsize=7)
    ax = axs[2]
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 8)
    ax.set_title("(c) the program: copper node + sub-gaps of the laminate\n(2.4.5: n = min(4, ceil(t / 0.4 mm)), only where copper is absent)", fontsize=9)
    dk.layer(ax, 0.5, 6.2, 2.5, 0.25, dk.COPPER)
    dk.layer(ax, 3.0, 6.2, 8.0, 0.25, dk.FR4)
    for i, y in enumerate((5.0, 3.8, 2.6, 1.4)):
        ax.plot([0.5, 11.0], [y, y], color="k", lw=0.8)
        for x in (1.5, 3.5, 5.5, 7.5, 9.5):
            ax.plot([x], [y], "ko", ms=3)
    for x in (1.5, 3.5, 5.5, 7.5, 9.5):
        ax.plot([x, x], [6.2, 1.4], color="grey", lw=0.6)
    ax.text(11.2, 5.0, "1", fontsize=7)
    ax.text(11.2, 1.4, "n", fontsize=7)
    ax.text(5.5, 0.4, "the sideways flow inside the laminate needs\nthe nodes in between: the reference resolves 16 slabs", ha="center", fontsize=7)
    ax.text(5.5, 7.3, "options: laminate_s_max_mm, laminate_n_max", ha="center", fontsize=7)
    dk.save(fig, OUT / "fig_03_thick_laminate_and_nodes.png", "Study S2: a source on a thick anisotropic laminate")


def main():
    """!
    @brief Draw the three figures.
    @return None.
    """
    fig_01()
    fig_02()
    fig_03()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
