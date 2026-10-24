"""!
@file make_diagrams.py
@brief Schematic diagrams of the effective-conductivity investigation: the test coupon and the definition of the solid-body resistance, the five layer orders, the source positions of the plate, and why one node through the thickness underestimates the surface of a thick plate.
@details Pure drawing, no data; the numbers are those of the tables of README.md. Writes figures/fig_01_coupon_and_definition.png, fig_02_five_layer_orders.png, fig_05_plate_source_positions.png, fig_09_through_thickness_gradient.png, fig_15_corrections_map.png and fig_16_source_edge_on_the_grid.png.
         Run: .venv/bin/python research/effective-conductivity/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

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
    dk.layer(ax, 0.5, 1.2, 4.0, 1.8, dk.METAL, "plate: thickness t, conductivity k", size=8)
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
    cols = [("documents only", 0.3, "#cfe3f5"), ("optional, in the program", 5.0, "#fbe3c2"), ("stays out of the program", 9.7, "#e8e8e8")]
    for title, x, c in cols:
        dk.box(ax, x, 4.7, 4.0, 0.7, title, c, bold=True, size=9)
    dk.box(ax, 0.3, 2.9, 4.0, 1.5, "plate check of the documents\nattribution to Seri Lee (1998)\n'+4.5 %' becomes +0.6, -0.8, -4.6 %\n(centre, edge, corner, aligned cells)", "#cfe3f5", size=8)
    dk.box(ax, 0.3, 0.8, 4.0, 1.7, "impact on results: none\nthe 1 mm check read +4.5 % because\nround() put the 25 mm source on\n24 cells (37.5 -> 38, 62.5 -> 62)", "#ffffff", size=8)
    dk.box(ax, 5.0, 3.5, 4.0, 0.9, "laminar form of Churchill and Chu\nvertical boards: -0.7 to +0.2 % of the rise", "#fbe3c2", size=8)
    dk.box(ax, 5.0, 2.3, 4.0, 0.9, "thick-plate check q'' t / 2k (an upper bound)\n74 block cases: at most 0.42 % (never fires)", "#fbe3c2", size=8)
    dk.box(ax, 5.0, 0.8, 4.0, 1.2, "independent solver as a test helper\n(checked against 6 published numbers\nand a closed form)", "#fbe3c2", size=8)
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


def main():
    """!
    @brief Draw the six diagrams.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    coupon(OUT / "fig_01_coupon_and_definition.png")
    orders(OUT / "fig_02_five_layer_orders.png")
    positions(OUT / "fig_05_plate_source_positions.png")
    gradient(OUT / "fig_09_through_thickness_gradient.png")
    corrections_map(OUT / "fig_15_corrections_map.png")
    source_edge(OUT / "fig_16_source_edge_on_the_grid.png")
    print("diagrams in", OUT)


if __name__ == "__main__":
    main()
