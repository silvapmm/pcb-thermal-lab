"""!
@file make_diagrams.py
@brief Schematic diagrams of the effective-conductivity investigation: the test coupon and the definition of the solid-body resistance, the five layer orders, the source positions of the plate, and why one node through the thickness underestimates the surface of a thick plate.
@details Pure drawing, no data; the numbers are those of the tables of README.md. Writes figures/fig_01_coupon_and_definition.png, fig_02_five_layer_orders.png, fig_05_plate_source_positions.png and fig_09_through_thickness_gradient.png.
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
    @brief Why one temperature per layer under-estimates the surface under a source on a thick plate.
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
    ax.text(5.1, 3.15, "top surface", fontsize=7, ha="right")
    ax.text(5.1, 1.0, "bottom", fontsize=7, ha="right")
    ax.text(7.0, 3.0, "T_top", color="r", fontsize=8, va="center")
    ax.text(7.0, 2.1, "T_mid: the one node of the layered model", color="b", fontsize=8, va="center")
    ax.text(6.0, 1.05, "T_bottom", color="r", fontsize=8, va="center")
    dk.box(ax, 7.2, 0.15, 3.6, 1.1, "surface under the source is hotter than the node by\nq'' t / (2 k)", "#fbe3c2", size=8.5)
    dk.box(ax, 0.5, 0.15, 6.2, 0.7, "test: error of the rise ~ q'' t / (2 k) / rise: 2.3 % at t = 10 mm, k = 50; 12.8 % at t = 10 mm, k = 10", "#cfe3f5", size=7.5)
    dk.save(fig, path, "One temperature node through the thickness: exact for a thin or highly conducting layer, low by q'' t / 2k at the surface under a source otherwise")


def main():
    """!
    @brief Draw the four diagrams.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    coupon(OUT / "fig_01_coupon_and_definition.png")
    orders(OUT / "fig_02_five_layer_orders.png")
    positions(OUT / "fig_05_plate_source_positions.png")
    gradient(OUT / "fig_09_through_thickness_gradient.png")
    print("diagrams in", OUT)


if __name__ == "__main__":
    main()
