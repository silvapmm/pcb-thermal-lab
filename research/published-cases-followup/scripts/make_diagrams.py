#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic drawings of the published-cases follow-up: the strip cell and the four trace cases, the coupon stack and how the program represents it, the via unit of Shen and the two idealisations, and the plate with a source near an edge and its images.
@details Pure drawing, no data; the numbers written in the drawings are those of README.md. Writes figures/fig_01_strip_cell_and_trace_cases.png, fig_02_coupon_stack_in_the_program.png,
         fig_03_via_unit_idealisations.png and fig_04_plate_source_images.png (the next numbers, 05 to 10, are written by make_figures.py).
         Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/make_diagrams.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def strip_cell(path):
    """!
    @brief The half cell of the papers (a strip at the corner of a slab with insulated ends) and the four trace cases (a) to (d) of Lemczyk and others.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.4, 1, 2, ratios=[1.0, 1.35])
    ax = axs[0]
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 5.6)
    ax.add_patch(Rectangle((0.8, 1.2), 5.2, 2.4, fc=dk.FR4, ec="k"))
    ax.add_patch(Rectangle((0.8, 3.6), 1.4, 0.22, fc=dk.HEAT, ec="k"))
    ax.text(1.5, 4.1, "strip, half-width a\n(isoflux or isothermal)", ha="center", fontsize=8)
    ax.annotate("", xy=(0.8, 0.8), xytext=(6.0, 0.8), arrowprops=dict(arrowstyle="<->"))
    ax.text(3.4, 0.45, "c = half-width of the channel (ends insulated: planes of symmetry)", ha="center", fontsize=7.5)
    ax.annotate("", xy=(6.3, 1.2), xytext=(6.3, 3.6), arrowprops=dict(arrowstyle="<->"))
    ax.text(6.4, 2.4, "t", fontsize=9)
    ax.text(3.4, 2.4, "slab of conductivity k\n(isotropic)", ha="center", fontsize=8)
    for x in (1.0, 2.0, 3.0, 4.0, 5.0):
        dk.arrow(ax, x, 1.2, x, 0.85, color=dk.BLUE)
    ax.text(3.4, 0.05, "film h at the base (Bi = h c / k; Bi large = isothermal base)", ha="center", fontsize=7.5, color=dk.BLUE)
    ax.set_title("Cell of Yovanovich, Muzychka and Culham (1999) and Lemczyk and others (1992)", fontsize=9)
    ax.text(0.2, 5.2, "psi = k R_s (strip, per unit depth); R_s = R_total - R_1D", fontsize=7.5)
    ax2 = axs[1]
    ax2.set_xlim(0, 12)
    ax2.set_ylim(0, 5.6)
    cases = [("(a) trace on top, films h1 = h2", 0.2, True, True, True, "film over the trace too"),
             ("(b) trace mid-way (half cell t/2, doubled)", 6.2, False, True, False, "top insulated"),
             ("(c) as (a) with h1 = 0 in the text; the numbers need Bi1 = 0.001", 0.2, True, True, False, "bottom 'insulated'"),
             ("(d) trace on the face z = 0, film h2 on the far face", 6.2, False, True, False, "strip face has no film")]
    for i, (title, x0, film_top, film_bot, _, note) in enumerate(cases):
        row = 0 if i < 2 else 1
        y0 = 3.2 if row == 0 else 0.5
        ax2.add_patch(Rectangle((x0 + 0.3, y0), 4.8, 1.2, fc=dk.FR4, ec="k"))
        top = (i in (0, 1, 2))
        ax2.add_patch(Rectangle((x0 + 0.3, y0 + 1.2 if top else y0 - 0.12), 1.2, 0.12, fc=dk.HEAT, ec="k"))
        ax2.text(x0 + 2.7, y0 + 1.5, title, ha="center", fontsize=6.6)
        if i in (0, 1):
            ax2.text(x0 + 2.7, y0 - 0.35, "film h at the base", ha="center", fontsize=6.8, color=dk.BLUE)
        if i == 2:
            ax2.text(x0 + 2.7, y0 - 0.35, "bottom film: h1 = 0.001 k / L1 in the printed numbers", ha="center", fontsize=6.4, color=dk.HEAT)
        if i == 3:
            ax2.text(x0 + 2.7, y0 + 1.3, "film h2 on the face opposite the trace", ha="center", fontsize=6.4, color=dk.BLUE)
    ax2.set_title("The four trace cases of Lemczyk and others (1992), Fig. 3 and equations 25 to 36", fontsize=9)
    dk.save(fig, path)


def coupon_stack(path):
    """!
    @brief The coupon of Culham and Yovanovich and its representation in the program: outer FR-4 layers as undrawn 'copper' slots of 36 um.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(13, 5.6, 1, 2, ratios=[1, 1])
    for ax in axs:
        ax.set_xlim(0, 7)
        ax.set_ylim(0, 6.2)
    ax = axs[0]
    ax.set_title("The paper's base stack (50 x 50 mm, h = 5 W/m2K, source 25 x 25 mm)", fontsize=9)
    stack = [("FR-4 0.5263 mm (k 0.4)", dk.FR4, 1.1), ("Cu 0.0356 mm (k 400)", dk.COPPER, 0.22), ("FR-4 0.5263 mm", dk.FR4, 1.1), ("Cu 0.0356 mm", dk.COPPER, 0.22), ("FR-4 0.5263 mm", dk.FR4, 1.1)]
    y = 5.2
    for text, color, h in stack:
        dk.layer(ax, 0.8, y - h, 5.4, h, color, text, size=7)
        y -= h
    ax.add_patch(Rectangle((2.2, 5.2), 2.6, 0.18, fc=dk.HEAT, ec="k"))
    ax.text(3.5, 5.6, "source on the FR-4 face", ha="center", fontsize=8)
    ax.text(3.5, 0.3, "the outer faces are FR-4: the layered models expect copper there", ha="center", fontsize=7.5)
    ax = axs[1]
    ax.set_title("In the program: four layers, the two outer ones left undrawn (laminate)", fontsize=9)
    stack = [("layer 1: 36 um, nothing drawn", dk.FR4, 0.2), ("gap 0.4903 mm (advanced stack-up)", dk.AIR, 0.9), ("layer 2: Cu 35.6 um, full copper", dk.COPPER, 0.22), ("gap 0.5263 mm", dk.AIR, 1.0),
             ("layer 3: Cu 35.6 um, full copper", dk.COPPER, 0.22), ("gap 0.4903 mm", dk.AIR, 0.9), ("layer 4: 36 um, nothing drawn", dk.FR4, 0.2)]
    y = 5.2
    for text, color, h in stack:
        dk.layer(ax, 0.8, y - h, 5.4, h, color, text, size=7)
        y -= h
    ax.add_patch(Rectangle((2.2, 5.2), 2.6, 0.18, fc=dk.HEAT, ec="k"))
    ax.text(3.5, 5.6, "heater on layer 1 (face value reported)", ha="center", fontsize=8)
    ax.text(3.5, 0.3, "top face -> plane 2 centre = 0.036 + 0.4903 + 0.0178 = 0.5441 mm, as in the paper", ha="center", fontsize=7.2)
    dk.save(fig, path)


def via_unit(path):
    """!
    @brief The via unit of Shen and others (equation 3: three parallel paths), the unit cell of the paper and the cell of the layered models.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.4, 1, 3, ratios=[1, 1.1, 1.1])
    ax = axs[0]
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.4)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((-1, -1), 2, 2, fc=dk.FR4, ec="k"))
    ax.add_patch(Circle((0, 0), 0.55, fc=dk.COPPER, ec="k"))
    ax.add_patch(Circle((0, 0), 0.42, fc=dk.AIR, ec="k"))
    ax.add_patch(Circle((0, 0), 1.0 / np.sqrt(np.pi) * 1.0, fc="none", ec=dk.BLUE, ls="--"))
    ax.text(0, 1.2, "plan: Pattern I unit (phi + s)^2", ha="center", fontsize=8)
    ax.text(0, -1.15, "dashed: the equal-area disc of the axisymmetric cell", ha="center", fontsize=7, color=dk.BLUE)
    ax.axis("on")
    ax.set_xticks([])
    ax.set_yticks([])
    for name, ax, over in (("The paper's cell (hole through the planes, heat on the solid top)", axs[1], False), ("The layered models (planes continuous over the drill, heat over the whole top)", axs[2], True)):
        ax.set_xlim(0, 7)
        ax.set_ylim(0, 6)
        ax.set_title(name, fontsize=8)
        z = 5.0
        for i in range(4):
            ax.add_patch(Rectangle((0.5, z - 0.12), 5.8, 0.24, fc=dk.COPPER, ec="k"))
            z -= 1.4 if i < 3 else 0
        ax.add_patch(Rectangle((0.5, 0.5), 5.8, 4.6, fc=dk.FR4, ec="none", alpha=0.35, zorder=0))
        ax.add_patch(Rectangle((2.9, 0.5), 1.0, 4.6, fc="white", ec="k", zorder=1))
        ax.add_patch(Rectangle((2.9, 0.5), 0.12, 4.6, fc=dk.COPPER, ec="k", zorder=2))
        ax.add_patch(Rectangle((3.78, 0.5), 0.12, 4.6, fc=dk.COPPER, ec="k", zorder=2))
        if over:
            for zz in (5.0, 3.6, 2.2, 0.8):
                ax.add_patch(Rectangle((2.9, zz - 0.12), 1.0, 0.24, fc=dk.COPPER, ec="k", zorder=3))
        for x in (1.0, 2.0, 5.2, 5.8):
            dk.arrow(ax, x, 5.9, x, 5.3, color=dk.HEAT)
        if over:
            dk.arrow(ax, 3.4, 5.9, 3.4, 5.3, color=dk.HEAT)
        ax.text(3.4, 0.1, "isothermal bottom", ha="center", fontsize=7.5)
    dk.save(fig, path)


def plate_images(path):
    """!
    @brief The plate of Seri Lee with the source at the centre, the edge midpoint and the corner, and the images of an insulated edge and corner.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.8, 1, 3)
    titles = ["centre: no image within the source's reach", "edge midpoint: one image (mirror in the edge)", "corner: three images (mirrors in both edges and the diagonal)"]
    for k, ax in enumerate(axs):
        ax.set_xlim(-0.6, 1.8)
        ax.set_ylim(-0.6, 1.8)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 1, 1, fc="#eef2f5", ec="k", lw=1.5))
        s = 0.25
        pos = [(0.375, 0.375), (0.375, 0.0), (0.0, 0.0)][k]
        ax.add_patch(Rectangle(pos, s, s, fc=dk.HEAT, ec="k"))
        if k >= 1:
            imgs = [(pos[0], -s)] if k == 1 else [(-s, pos[1]), (pos[0], -s), (-s, -s)]
            for ip in imgs:
                ax.add_patch(Rectangle(ip, s, s, fc="none", ec=dk.HEAT, ls="--"))
        ax.set_title(titles[k], fontsize=8)
        ax.text(0.5, 1.12, "plate 100 x 100 mm, 1.3 mm Al, source 25 x 25 mm", ha="center", fontsize=6.8)
        ax.text(0.5, -0.45, ["Rc 0.66 (printed)  0.664 (exact thin plate)", "Rc 1.29 (printed)  1.280 (exact)", "Rc 2.38 (printed)  2.270 (exact)"][k], ha="center", fontsize=7.5)
        ax.axis("on")
        ax.set_xticks([])
        ax.set_yticks([])
    dk.save(fig, path)


def main():
    """!
    @brief Draw the four schematics.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    strip_cell(OUT / "fig_01_strip_cell_and_trace_cases.png")
    coupon_stack(OUT / "fig_02_coupon_stack_in_the_program.png")
    via_unit(OUT / "fig_03_via_unit_idealisations.png")
    plate_images(OUT / "fig_04_plate_source_images.png")


if __name__ == "__main__":
    main()
