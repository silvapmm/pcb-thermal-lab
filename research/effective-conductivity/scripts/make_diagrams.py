#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic diagrams of the effective-conductivity investigation: the test coupon and the definition of the solid-body resistance, the five layer orders, the source positions of the plate, and why one node through the thickness underestimates the surface of a thick plate.
@details Pure drawing, no data; the numbers are those of the tables of README.md. Writes figures/fig_01_coupon_and_definition.png, fig_02_five_layer_orders.png, fig_05_plate_source_positions.png, fig_09_through_thickness_gradient.png, fig_15_corrections_map.png, fig_16_source_edge_on_the_grid.png, fig_18_thick_plate_flux.png and fig_20_independent_solver_in_the_tests.png.
         The numbers written in the two last ones are those of README 4.5, 4.8 C and 4.11 and of docs/validation.md section 22 (74 block cases; tolerances of tests/test_layered_vs_3d.py).
         Run: .venv/bin/python research/effective-conductivity/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def coupon(path):
    """!
    @brief The coupon of Culham and Yovanovich with its boundary conditions, and the definition of the effective conductivity.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 5.2)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5.4)
    names = [("FR4 0.5263 mm, k 0.4", dk.FR4, 0.9), ("Cu 0.0356 mm, k 400", dk.COPPER, 0.18), ("FR4 0.5263 mm, k 0.4", dk.FR4, 0.9), ("Cu 0.0356 mm, k 400", dk.COPPER, 0.18), ("FR4 0.5263 mm, k 0.4", dk.FR4, 0.9)]
    y = 4.0
    for t, c, h in names:
        dk.layer(ax, 0.6, y - h, 5.2, h, c, t, size=7)
        y -= h
    ax.add_patch(Rectangle((2.0, 4.0), 2.4, 0.22, fc=dk.HEAT, ec="k"))
    ax.text(3.2, 4.45, "source 25 x 25 mm, 2.5 W\n(top face insulated under it)", ha="center", fontsize=7.5)
    dk.arrow(ax, 1.0, 4.6, 1.0, 4.05, color=dk.BLUE, label="")
    ax.text(0.4, 4.7, "h = 5 W/m2K", color=dk.BLUE, fontsize=7.5)
    dk.arrow(ax, 3.2, 0.6, 3.2, 0.05, color=dk.BLUE)
    ax.text(3.45, 0.2, "h = 5 W/m2K (whole bottom face)", color=dk.BLUE, fontsize=7.5)
    ax.text(5.95, 2.4, "sides\ninsulated\n(plane of\nsymmetry)", fontsize=7.5, va="center")
    ax.text(3.2, 5.1, "block 50 x 50 mm, 1.65 mm thick (the paper says 1.62)", ha="center", fontsize=8)
    dk.box(ax, 7.4, 3.5, 6.2, 1.3, "solid-body resistance\nR_solid = (mean source temperature - mean wall temperature) / Q\n= R_bulk + R_spread", "#cfe3f5", size=8)
    dk.box(ax, 7.4, 1.8, 6.2, 1.3, "effective conductivity k_e:\nthe single layer of the same thickness and\nboundary conditions that has the same R_solid", "#fbe3c2", size=8)
    dk.box(ax, 7.4, 0.2, 6.2, 1.2, "limits: in-plane (parallel) 17.6 W/mK, cross-plane (series) 0.42;\nmeans of the two: arithmetic 9.0, geometric 2.7, harmonic 0.82", "#e8e8e8", size=8)
    dk.arrow(ax, 10.5, 3.5, 10.5, 3.1)
    dk.arrow(ax, 10.5, 1.8, 10.5, 1.4)
    dk.save(fig, path, "The test coupon of Culham and Yovanovich (1998) and what the effective conductivity means")


def orders(path):
    """!
    @brief The five layer orders of the paper's Table 2 as stacks with the source on top.
    @param path Output file.
    @return None.
    """
    cases = {1: "CCFFF", 2: "CFFFC", 3: "FCFCF", 4: "FCCF", 5: "FFFCC"}
    fig, ax = dk.canvas(12.5, 3.6)
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 3.6)
    for k, (c, s) in enumerate(cases.items()):
        x = 0.4 + k * 2.4
        y = 2.7
        for ch in s:
            h = 0.075 if ch == "C" else (0.5 if len(s) == 5 else 0.75)
            h = max(h, 0.09) if ch == "C" else h
            dk.layer(ax, x, y - h, 1.8, h, dk.COPPER if ch == "C" else dk.FR4)
            y -= h
        ax.add_patch(Rectangle((x + 0.45, 2.7), 0.9, 0.12, fc=dk.HEAT, ec="k"))
        ax.text(x + 0.9, 3.05, f"case {c}", ha="center", fontsize=8, weight="bold")
        ax.text(x + 0.9, 0.25, "".join({"C": "Cu ", "F": "FR4 "}[ch] for ch in s).strip().replace(" ", "-"), ha="center", fontsize=6.5)
    dk.save(fig, path, "The five layer orders of the paper (same copper and FR4, source on the top face): the order changes the effective conductivity from 15.0 to 5.0 W/mK")


def positions(path):
    """!
    @brief The three source positions of the base plate of Seri Lee.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.6, nrows=1, ncols=3)
    rc = {"centre": (0.66, (37.5, 37.5)), "edge midpoint": (1.29, (37.5, 0)), "corner": (2.38, (0, 0))}
    for ax, (name, (val, (x0, y0))) in zip(axs, rc.items()):
        ax.set_xlim(-12, 112)
        ax.set_ylim(-12, 112)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 100, 100, fc=dk.METAL, ec="k"))
        ax.add_patch(Rectangle((x0, y0), 25, 25, fc=dk.HEAT, ec="k"))
        ax.set_title(f"{name}: Rc = {val} K/W", fontsize=9)
        ax.text(50, -9, "100 x 100 x 1.3 mm aluminium, source 25 x 25 mm", ha="center", fontsize=6.5)
    dk.save(fig, path, "Where the source sits on the plate (Seri Lee, 1998): the constriction resistance grows as the source moves to the edge and the corner")


def gradient(path):
    """!
    @brief Why one temperature per layer under-estimates the surface under a source on a thick plate, and why q'' t / (2 k) is only the upper bound of it.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(11, 4.4)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.4)
    dk.layer(ax, 0.5, 1.2, 4.0, 1.8, dk.METAL)
    # the label stays left of the flux arrow so that the arrow does not cross the text
    ax.text(0.65, 1.55, "plate: thickness t,\nconductivity k", fontsize=8, ha="left", va="center")
    ax.add_patch(Rectangle((1.5, 3.0), 2.0, 0.18, fc=dk.HEAT, ec="k"))
    ax.text(2.5, 3.4, "source, flux q'' = Q / area", ha="center", fontsize=8)
    dk.arrow(ax, 2.5, 3.0, 2.5, 1.2, color=dk.HEAT, label="")
    ax.plot([5.2, 5.2], [1.2, 3.0], "k-", lw=0.8)
    ax.plot([5.2, 6.8], [3.0, 3.0], "r-", lw=2)
    ax.plot([5.2, 5.9], [1.2, 1.2], "r-", lw=2)
    ax.plot([6.8, 5.9], [3.0, 1.2], "r--", lw=1.4)
    ax.plot([6.35, 6.35], [1.2, 3.0], "b:", lw=1)
    ax.plot([6.35], [2.1], "bo")
    zz = np.linspace(0.0, 1.0, 30)                               # flux falling linearly with depth (heat leaving sideways): T - T_bottom ~ (1 - z)^2
    ax.plot(5.9 + (6.8 - 5.9) * (1.0 - zz) ** 2, 3.0 - 1.8 * zz, color="#7c3aed", lw=1.4)   # illustrative shape, same top and bottom
    ax.text(5.25, 2.55, "heat leaving\nsideways", color="#7c3aed", fontsize=6.5)
    ax.text(5.1, 3.15, "top surface", fontsize=7, ha="right")
    ax.text(5.1, 1.0, "bottom", fontsize=7, ha="right")
    ax.text(7.0, 3.0, "T_top", color="r", fontsize=8, va="center")
    ax.text(7.0, 2.1, "T_mid: the one node of the layered model", color="b", fontsize=8, va="center")
    ax.text(6.0, 1.05, "T_bottom", color="r", fontsize=8, va="center")
    dk.box(ax, 7.2, 0.15, 3.6, 1.1, "surface under the source is hotter than the node by\nat most q'' t / (2 k) (all the heat crossing: red);\nless when it leaves sideways (violet)", "#fbe3c2", size=7.5)
    dk.box(ax, 0.5, 0.15, 6.2, 0.7, "measured (3D): 4.7 and 7.1 K against 8 and 12 K for the bound (t = 10 mm, k = 10); 0.91 K against 1.25 K (k = 50)", "#cfe3f5", size=7)
    dk.save(fig, path, "One temperature node through the thickness: the node is the mean; the surface under a source is hotter, by at most q'' t / 2k")


def corrections_map(path):
    """!
    @brief The corrections and proposals of this investigation with their measured impact and their status.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 5.6)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5.6)
    cols = [("documents only", 0.3, "#cfe3f5"), ("adopted in the program", 5.0, "#fbe3c2"), ("stays out of the program", 9.7, "#e8e8e8")]
    for title, x, c in cols:
        dk.box(ax, x, 4.7, 4.0, 0.7, title, c, bold=True, size=9)
    dk.box(ax, 0.3, 2.9, 4.0, 1.5, "plate check of the documents\nattribution to Seri Lee (1998)\n'+4.5 %' becomes +0.6, -0.8, -4.6 %\n(centre, edge, corner, aligned cells)", "#cfe3f5", size=8)
    dk.box(ax, 0.3, 0.8, 4.0, 1.7, "impact on results: none\nthe 1 mm check read +4.5 % because\nround() put the 25 mm source on\n24 cells (37.5 -> 38, 62.5 -> 62)", "#ffffff", size=8)
    dk.box(ax, 5.0, 3.5, 4.0, 0.9, "laminar form of Churchill and Chu\n(Board.natural_form option)\nvertical boards: -0.7 to +0.2 % of the rise", "#fbe3c2", size=8)
    dk.box(ax, 5.0, 2.3, 4.0, 0.9, "thick-plate check q'' t / 2k (an upper bound)\n74 block cases: pad flux at most 0.42 %,\nflux into the block (the program) 0.34 %", "#fbe3c2", size=8)
    dk.box(ax, 5.0, 0.8, 4.0, 1.2, "independent solver as a test helper\n(tests/test_layered_vs_3d.py; its own tests:\nthree published numbers, balances, a series circuit)", "#fbe3c2", size=8)
    dk.box(ax, 9.7, 3.0, 4.0, 1.4, "an effective conductivity of the stack\nk_e from 15 to 5 W/mK with the layer order;\nthe means can be 70 % off", "#e8e8e8", size=8)
    dk.box(ax, 9.7, 0.8, 4.0, 1.7, "the program keeps one node per copper\nlayer and a resistor per gap: the order\nis represented, nothing to homogenise", "#ffffff", size=8)
    dk.arrow(ax, 7.0, 3.5, 7.0, 3.2)
    dk.arrow(ax, 7.0, 2.3, 7.0, 2.0)
    dk.save(fig, path, "The corrections and proposals, with their measured impact (README 4.8)")


def source_edge(path):
    """!
    @brief The 25 mm source edge on 1 mm and on 0.5 mm cells: round() moves the edge at 37.5 mm to 38 (and the one at 62.5 mm to 62), the 0.5 mm grid keeps it.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(11, 3.6, nrows=1, ncols=2)
    for ax, d, start, title in zip(axs, (1.0, 0.5), (38.0, 37.5), ("1 mm cells, round(37.5) = 38: the heated cells start at 38 mm\n(and round(62.5) = 62: the source has 24 cells)",
                                                                   "0.5 mm cells: the edge falls on a cell edge (25 mm)")):
        ax.set_xlim(34, 42)
        ax.set_ylim(0, 4)
        ax.set_aspect("equal")
        for x in np.arange(34, 42.01, d):
            ax.plot([x, x], [0, 4], color="#9ca3af", lw=0.6)
        for y in np.arange(0, 4.01, d):
            ax.plot([34, 42], [y, y], color="#9ca3af", lw=0.6)
        ax.add_patch(Rectangle((start, 0.0), 42.0 - start, 4.0, fc=dk.HEAT, alpha=0.35, ec="none"))
        ax.plot([37.5, 37.5], [0, 4], color=dk.HEAT, lw=2, ls="--" if start != 37.5 else "-")
        ax.text(37.4, 3.6, "true edge", color=dk.HEAT, fontsize=8, ha="right")
        ax.set_title(title, fontsize=8.5)
    dk.save(fig, path, "Why the plate check of the documents read +4.5 %: round() rounds halves to even and shrank the source")


def thick_plate_flux(path):
    """!
    @brief The thick-plate check of the program: a part on a thin board with a metal block under it, the bound q'' t / (2 k), and the three fluxes that could stand for q'' with the criterion each gives over the 74 metal-block cases.
    @details The ratios are those printed by `study_corrections_impact.py` (pad flux, README 4.8 C) and by docs/validation.md section 22 (footprint flux and flux into the block; median and maximum over the same 74 cases).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.6, nrows=1, ncols=2, ratios=[1.25, 1])
    ax = axs[0]
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 6)
    ax.text(4.5, 5.75, "Cross-section (not to scale): where does the heat enter the block?", ha="center", fontsize=9)
    dk.layer(ax, 0.3, 3.3, 8.4, 0.12, dk.COPPER, "")
    dk.layer(ax, 0.3, 2.85, 8.4, 0.45, dk.FR4, "thin board (laminate and copper)", size=7)
    dk.layer(ax, 2.2, 3.42, 2.4, 0.4, "#444444", "")
    ax.text(3.4, 3.62, "part, power P", fontsize=7.5, va="center", ha="center", color="white")
    dk.layer(ax, 1.4, 1.2, 4.2, 1.1, dk.METAL, "metal block: thickness t, conductivity k", size=7.5)
    dk.layer(ax, 1.4, 2.3, 4.2, 0.12, dk.COPPER, "")
    # footprint flux: the narrowest, the largest flux
    dk.arrow(ax, 2.5, 4.9, 2.5, 3.85, color=dk.HEAT)
    ax.text(2.35, 5.0, "footprint flux P / A_fp", fontsize=7, color=dk.HEAT, ha="left")
    # pad flux: wider
    ax.annotate("", (1.4, 2.62), (5.6, 2.62), arrowprops={"arrowstyle": "<->", "color": "#d97706"})
    # the label sits left of the arrow: above it the board would cover the text
    ax.text(1.3, 2.62, "copper pad A_pad", fontsize=7, color="#d97706", ha="right", va="center")
    # flux into the block: spread, drawn as several arrows
    for xx in (1.8, 2.6, 3.4, 4.2, 5.0):
        dk.arrow(ax, xx, 2.38, xx, 1.9, color=dk.BLUE)
    ax.text(3.5, 0.9, "flux q'' that really enters the block\n(laminate and copper spread the heat first)", fontsize=7, color=dk.BLUE, ha="center", va="top")
    dk.arrow(ax, 6.0, 3.6, 7.0, 3.1, color=dk.HEAT)
    ax.text(6.0, 4.0, "the heat spreads sideways\nbefore it reaches the block", fontsize=7, color="k")
    dk.box(ax, 6.0, 0.4, 2.8, 2.0, "surface under the part is hotter\nthan the block node by at most\n\nq'' t / (2 k)\n\n(bound; the program warns when\nit exceeds 5 % of the rise)", "#fbe3c2", size=7.5)
    ax = axs[1]
    ax.axis("on")
    labels = ["power over the\nfootprint\n(first version)", "power over the\ncopper pad\n(research, 90 K)", "flux into the block\n(the program)"]
    med = [0.50, 0.04, 0.07]
    mx = [1.78, 0.42, 0.34]
    x = np.arange(3)
    ax.bar(x - 0.18, med, 0.36, color="#6b7280", label="median")
    ax.bar(x + 0.18, mx, 0.36, color="#1d4ed8", label="maximum")
    for xi, m1, m2 in zip(x, med, mx):
        ax.text(xi - 0.18, m1 * 1.1, f"{m1:.2f}", ha="center", fontsize=7)
        ax.text(xi + 0.18, m2 * 1.1, f"{m2:.2f}", ha="center", fontsize=7)
    ax.axhline(5.0, color="#dc2626", ls="--")
    ax.text(2.45, 5.3, "threshold 5 %", color="#dc2626", fontsize=7, ha="right")
    ax.set_yscale("log")
    ax.set_ylim(0.01, 12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("q'' t / (2 k) over the rise (%)")
    ax.set_title("Which flux? Over the 74 metal-block cases none exceeds 5 %,\nbut the footprint flux fires on ordinary designs", fontsize=8.5)
    ax.legend(fontsize=7.5, loc="lower left")
    dk.save(fig, path, "The thick-plate check (checks.check_thick_plates): the flux that enters the block is used, not the footprint or pad flux")


def independent_solver_in_the_tests(path):
    """!
    @brief What tests/test_layered_vs_3d.py compares: the independent solver (tests/helpers/layered3d.py, no import from the program) against the five layered models on a Cu / FR-4 / Cu coupon and a one-layer board, with the measured error and the tolerance of the test for each.
    @details The measured values and the tolerances are copied from the test file and from docs/validation.md section 22 (1 mm cells): coupon 16 mm source, tolerance 0.2 % (FVM, 3D solid, Analytic), 0.3 % (Lumped), 1.2 % (FDM); one-layer board full copper (0.2 % for FVM, FDM and 3D solid; Lumped +1.20 +-0.5 and Analytic -0.83 +-0.5) and with a 20 mm pad (FVM -3.0 +-1, 3D solid +0.1 +-0.5, FDM -12.6 +-2, Lumped -17.0 +-2, Analytic -30.2 +-3).
    @param path Output file.
    @return None.
    """
    fig = plt.figure(figsize=(14, 5.6))
    ax = fig.add_axes((0.0, 0.0, 0.42, 0.93))
    ax.axis("off")
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 6)
    dk.box(ax, 0.2, 4.2, 3.0, 1.4, "independent 3D solver\ntests/helpers/layered3d.py\n(SciPy only; imports nothing\nfrom the program)", "#cfe3f5", size=7.5)
    dk.box(ax, 3.9, 4.2, 3.0, 1.4, "the five layered models\nFVM, FDM, 3D solid,\nLumped, Analytic", "#fbe3c2", size=7.5)
    dk.box(ax, 0.2, 2.2, 3.0, 1.4, "board 1: Cu / FR-4 / Cu coupon\n50 x 50 mm, 16 mm source, 2.5 W\n(Culham and Yovanovich case 2)", "#ffffff", size=7)
    dk.box(ax, 3.9, 2.2, 3.0, 1.4, "board 2: one-layer board\n60 x 60 mm, 6 mm part, 1 W\nfull copper, and a 20 mm pad", "#ffffff", size=7)
    dk.arrow(ax, 1.7, 4.2, 1.7, 3.65)
    dk.arrow(ax, 5.4, 4.2, 5.4, 3.65)
    dk.box(ax, 0.2, 0.3, 6.7, 1.3, "same cells (1 mm), same conditions; the test asserts the rise of each model\nwithin a tolerance of the independent rise: tight where the models agree,\na range where the error is a documented limit (pad: FDM, Lumped, Analytic)", "#e8e8e8", size=7.5)
    dk.arrow(ax, 1.7, 2.2, 1.7, 1.65)
    dk.arrow(ax, 5.4, 2.2, 5.4, 1.65)
    ax.set_title("What the test compares", fontsize=9)
    ax2 = fig.add_axes((0.52, 0.12, 0.46, 0.78))
    rows = [("coupon", "FVM", -0.02, 0.2), ("coupon", "3D solid", 0.00, 0.2), ("coupon", "Analytic", -0.06, 0.2), ("coupon", "Lumped", 0.27, 0.3), ("coupon", "FDM", -0.59, 1.2),
            ("one layer, full copper", "FVM", -0.01, 0.2), ("one layer, full copper", "FDM", -0.01, 0.2), ("one layer, full copper", "3D solid", 0.00, 0.2),
            ("one layer, full copper", "Lumped", 1.20, 0.5), ("one layer, full copper", "Analytic", -0.83, 0.5),
            ("one layer, 20 mm pad", "FVM", -3.0, 1.0), ("one layer, 20 mm pad", "3D solid", 0.1, 0.5), ("one layer, 20 mm pad", "FDM", -12.6, 2.0),
            ("one layer, 20 mm pad", "Lumped", -17.0, 2.0), ("one layer, 20 mm pad", "Analytic", -30.2, 3.0)]
    centres = {}
    for k, (board, model, val, tol) in enumerate(rows):
        y = len(rows) - 1 - k
        # The pad rows are tested around the measured value (a documented limit); the others around zero (a match to the stated tolerance), except the two fast models with full copper
        centre = val if board.endswith("pad") or (board.endswith("copper") and model in ("Lumped", "Analytic")) else 0.0
        centres[k] = centre
        ax2.barh(y, 2 * tol, left=centre - tol, height=0.55, color="#cfe3f5", edgecolor="#1d4ed8")
        ax2.plot([val], [y], "o", color="#dc2626", ms=4)
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels([f"{b}: {m}" for b, m, _, _ in rows][::-1], fontsize=7)
    ax2.axvline(0, color="k", lw=0.8)
    ax2.set_xlabel("model minus independent solver (%): measured (red) and the range the test accepts (blue)")
    ax2.set_title("Measured on 1 mm cells and the tolerances of the test", fontsize=9)
    fig.suptitle("The independent 3D solver in the test suite (tests/test_layered_vs_3d.py)", fontsize=10)
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the eight diagrams.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    coupon(OUT / "fig_01_coupon_and_definition.png")
    orders(OUT / "fig_02_five_layer_orders.png")
    positions(OUT / "fig_05_plate_source_positions.png")
    gradient(OUT / "fig_09_through_thickness_gradient.png")
    corrections_map(OUT / "fig_15_corrections_map.png")
    source_edge(OUT / "fig_16_source_edge_on_the_grid.png")
    thick_plate_flux(OUT / "fig_18_thick_plate_flux.png")
    independent_solver_in_the_tests(OUT / "fig_20_independent_solver_in_the_tests.png")
    print("diagrams in", OUT)


if __name__ == "__main__":
    main()
