#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Pictures of the situations of research/theory-sources (no data, no program): the trace cell of Lemczyk, the coupon of Culham with its series, the duality of Keller and Dykhne, the Foster and Cauer networks, the Gerber region with a hole, the two spreading cases of Muzychka, the Peaceman well-block on a non-square, anisotropic grid with the via footprint, the evidence matrix of the models and the plan of a cheap measurement.
@details Numbers quoted are those printed in the sources (named in each caption) or in the README of this folder. Writes figures/fig_06 to fig_12, fig_14 and fig_15 (fig_01 to fig_05 and fig_13 are the data figures of make_figures.py).
         Run: .venv/bin/python research/theory-sources/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.patches import Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def lemczyk_cell(path):
    """!
    @brief The cells of Fig. 3 of Lemczyk et al. (1992): trace on the surface (a), mid-buried (b), with the paths of the heat.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.2, 1, 2)
    for ax, title, buried in ((axs[0], "(a) surface trace: film h2 on the rest of the top, h1 on the bottom", False), (axs[1], "(b) mid-buried trace: half cell, twice the flow", True)):
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-1.5, 5.5)
        ax.set_title(title, fontsize=8)
        top = 4.0 if not buried else 2.0
        ax.add_patch(Rectangle((0, 0), 10, top, facecolor=dk.FR4, edgecolor="k"))
        ax.add_patch(Rectangle((0, top), 2.5, 0.35, facecolor=dk.COPPER, edgecolor="k"))
        ax.text(1.25, top + 0.6, "trace, T = Tc", ha="center", fontsize=7)
        ax.text(5, top / 2, "k, adiabatic ends at x = 0 and x = L1", ha="center", fontsize=7)
        for x in (0.6, 1.25, 1.9):                         # heat leaves the trace and fans out below it
            dk.arrow(ax, x, top, x + 0.9 * (x - 1.25), top - 1.6, color=dk.HEAT)
        for x in (4, 6, 8):
            if not buried:
                dk.arrow(ax, x, top, x, top + 0.9, color=dk.BLUE)
        for x in (1.5, 4.5, 7.5):
            dk.arrow(ax, x, 0, x, -0.9, color=dk.BLUE)
        ax.text(5, -1.3, "film h1 (bottom)", ha="center", fontsize=7, color=dk.BLUE)
        dk.arrow(ax, 0, top + 1.0, 2.5, top + 1.0, color="k", style="<->", label="w", size=7)
    dk.save(fig, path)


def culham_coupon(path):
    """!
    @brief The coupon of Culham and Yovanovich (1998): five layers, the centred source, the films, and the first cosine modes that the series uses.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.2, 1, 2, ratios=[1.3, 1.0])
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(-1.5, 6)
    cols = [dk.FR4, dk.COPPER, dk.FR4, dk.COPPER, dk.FR4]
    labels = ["FR4 0.5263 mm", "Cu 0.0356 mm", "FR4 0.5263 mm", "Cu 0.0356 mm", "FR4 0.5263 mm"]
    h = [0.9, 0.3, 0.9, 0.3, 0.9]
    y = 4.0
    for c, lb, hh in zip(cols, labels, h):
        y -= hh
        dk.layer(ax, 1, y, 10, hh, c, lb, 7)
    ax.add_patch(Rectangle((4.5, 4.0), 3.0, 0.4, facecolor=dk.HEAT, edgecolor="k"))
    ax.text(6, 4.6, "source 25 x 25 mm, 2.5 W (board 50 x 50 mm)", ha="center", fontsize=7)
    dk.arrow(ax, 2, 4.0, 2, 4.8, color=dk.BLUE)
    dk.arrow(ax, 10, 4.0, 10, 4.8, color=dk.BLUE)
    ax.text(2, 5.0, "h on the free top face", fontsize=7, color=dk.BLUE)
    dk.arrow(ax, 6, 0, 6, -0.9, color=dk.BLUE)
    ax.text(6.3, -1.1, "h on the bottom face; sides adiabatic", fontsize=7, color=dk.BLUE)
    ax2 = axs[1]
    x = np.linspace(0, 1, 200)
    for m, col in ((0, "k"), (2, dk.BLUE), (4, dk.HEAT), (6, "#2ca02c")):
        ax2.plot(x, np.cos(m * np.pi * x) + 1.2 * m / 2, color=col, label=f"mode m = {m}")
    ax2.axvspan(0.25, 0.75, color="#f4cccc", alpha=0.6)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.axis("on")
    ax2.set_title("the source is a block of cosine modes (odd modes vanish for a centred source)", fontsize=7)
    ax2.set_xlabel("x / L (shaded: source)", fontsize=7)
    ax2.set_yticks([])
    dk.save(fig, path)


def duality(path):
    """!
    @brief The 90-degree rotation of Dykhne, the checkerboard and the phase interchange.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 3.8, 1, 3)
    ax = axs[0]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 8)
    for i in range(4):
        for j in range(4):
            ax.add_patch(Rectangle((1 + 1.5 * i, 1 + 1.5 * j), 1.5, 1.5, facecolor="#e0a458" if (i + j) % 2 == 0 else "#9bbf8a", edgecolor="k"))
    ax.set_title("checkerboard: s* = sqrt(s1 s2)  (Milton 3.11)", fontsize=8)
    ax = axs[1]
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 8)
    ax.add_patch(Rectangle((1, 1), 6, 6, facecolor="#9bbf8a", edgecolor="k"))
    for i in range(3):
        for j in range(3):
            ax.add_patch(__import__("matplotlib.patches", fromlist=["Circle"]).Circle((2 + 2 * i, 2 + 2 * j), 0.7, facecolor="#e0a458", edgecolor="k"))
    ax.set_title("disks f = 0.3: s*(s1, s2) s*(s2, s1) = s1 s2  (3.9)", fontsize=8)
    ax = axs[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    dk.box(ax, 0.3, 3.5, 3.4, 1.4, "div j = 0\ncurl e = 0\nj = s e", "#cfe3f5")
    dk.box(ax, 6.2, 3.5, 3.4, 1.4, "j' = R e,  e' = R j\ndiv j' = 0, curl e' = 0\ns' = 1/s", "#cfe3f5")
    dk.arrow(ax, 3.8, 4.2, 6.1, 4.2, label="rotate by 90 degrees", size=7)
    ax.text(5, 1.8, "so s*' = 1/s* (Milton 3.6)", ha="center", fontsize=8)
    dk.save(fig, path)


def foster_cauer(path):
    """!
    @brief The Foster (Fig. 2 of AN11261) and Cauer (Fig. 4) networks with the five-stage values of the BUK7S1R0-40H.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 3.6, 2, 1)
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.set_title("Cauer: capacitors to the ambient, nodes inside the device (R sum 0.4000 K/W)", fontsize=8)
    for i, (r, c) in enumerate(zip((0.00272, 0.0220, 0.00713, 0.1857, 0.1824), (0.093, 0.515, 1.95, 3.05, 27.96))):
        x0 = 0.8 + 2.2 * i
        dk.resistor(ax, x0, x0 + 2.0, 2.2, f"R{i + 1} {r:g}")
        ax.plot([x0, x0], [2.2, 1.3], color="k")
        ax.plot([x0 - 0.2, x0 + 0.2], [1.3, 1.3], color="k", lw=2)
        ax.plot([x0 - 0.2, x0 + 0.2], [1.1, 1.1], color="k", lw=2)
        ax.text(x0 + 0.25, 1.2, f"C{i + 1} {c:g} mJ/K", fontsize=6)
    ax.text(0, 2.2, "Tj", fontsize=8)
    ax = axs[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.set_title("Foster: the same Zth(t) = sum R_i (1 - exp(-t / tau_i)), no physical nodes (R 0.254, 0.124, 0.0179, 0.0022, 0.0019 K/W)", fontsize=8)
    for i in range(5):
        x0 = 0.8 + 2.2 * i
        dk.resistor(ax, x0, x0 + 2.0, 2.2, f"R{i + 1}")
        ax.plot([x0 + 2.0, x0 + 2.0], [2.2, 1.3], color="k")
        ax.plot([x0 + 1.8, x0 + 2.2], [1.3, 1.3], color="k", lw=2)
        ax.plot([x0 + 1.8, x0 + 2.2], [1.1, 1.1], color="k", lw=2)
        ax.text(x0 + 0.9, 0.7, f"C{i + 1}", fontsize=7)
    dk.save(fig, path)


def gerber_hole(path):
    """!
    @brief The region with a hole and the two disjunct areas of section 4.10.4.8 of the Gerber specification (revision 2026.05), with the areas that follow from the coordinates.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(10, 4.0, 1, 2)
    sq = np.array([[0, 5], [0, 10], [10, 10], [10, 0], [0, 0], [0, 5]], float)
    dia = np.array([[1, 5], [5, 1], [9, 5], [5, 9], [1, 5]], float)
    dia_l = np.array([[-1, 5], [-5, 1], [-9, 5], [-5, 9], [-1, 5]], float)
    ax = axs[0]
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 11)
    ax.add_patch(Polygon(sq[:-1], facecolor=dk.COPPER, edgecolor="k"))
    ax.add_patch(Polygon(dia[:-1], facecolor="white", edgecolor="k"))
    ax.set_title("region with hole: 100 - 32 = 68 mm2", fontsize=8)
    ax = axs[1]
    ax.set_xlim(-10, 11)
    ax.set_ylim(-1, 11)
    ax.add_patch(Polygon(sq[:-1], facecolor=dk.COPPER, edgecolor="k"))
    ax.add_patch(Polygon(dia_l[:-1], facecolor=dk.COPPER, edgecolor="k"))
    ax.set_title("two disjunct areas: 100 + 32 = 132 mm2", fontsize=8)
    dk.save(fig, path)


def muzychka_cases(path):
    """!
    @brief Case 1 (b) (a spreader on a poorly conducting plate) and case 2 (the baseplate of a heat sink with four sources) of Muzychka et al. (2003), Tables 2 to 4.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(12, 4.2, 1, 2, ratios=[1.2, 1.0])
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(-1.5, 5)
    dk.layer(ax, 1, 1.5, 10, 0.6, dk.METAL, "k = 350 W/mK, 2 mm", 7)
    dk.layer(ax, 1, 0, 10, 1.5, dk.FR4, "k = 10 W/mK, 10 mm (300 x 300 mm)", 7)
    for x, p in ((3.5, "10 W"), (8.5, "15 W")):
        ax.add_patch(Rectangle((x - 0.45, 2.1), 0.9, 0.3, facecolor=dk.HEAT, edgecolor="k"))
        ax.text(x, 2.6, p, ha="center", fontsize=7)
    dk.arrow(ax, 6, 0, 6, -0.9, color=dk.BLUE)
    ax.text(6.3, -1.1, "h = 10 W/m2K, 25 C; centroids 56.55 and 59.94 C (paper)", fontsize=7, color=dk.BLUE)
    ax = axs[1]
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 50)
    ax.add_patch(Rectangle((0, 0), 50, 50, facecolor=dk.METAL, edgecolor="k"))
    for (x, y, p, t) in ((12.5, 12.5, 10, 97.40), (37.5, 12.5, 25, 103.82), (12.5, 37.5, 20, 101.28), (37.5, 37.5, 15, 99.94)):
        ax.add_patch(Rectangle((x - 5, y - 5), 10, 10, facecolor=dk.HEAT, edgecolor="k"))
        ax.text(x, y, f"{p} W\n{t} C", ha="center", va="center", fontsize=7)
    ax.set_title("case 2: 50 x 50 x 10 mm, k 150, h 400 on the bottom; centroids (paper)", fontsize=7)
    dk.save(fig, path)


def peaceman_well(path):
    """!
    @brief The Peaceman well-block: a non-square cell with its equivalent radius, the anisotropic stretching of a circular well, and a via footprint of cells on the grid (README 7.1).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(13, 4.4, 1, 3)
    # (a) isotropic non-square cell: the well sits in the middle of a 2 x 1 cell, the equivalent radius is 0.31387 (infinite lattice)
    ax = axs[0]
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-2.2, 2.4)
    ax.set_aspect("equal")
    for i in range(-1, 2):
        for j in range(-2, 3):
            ax.add_patch(Rectangle((2 * i - 1, j - 0.5), 2, 1, fill=False, edgecolor="#888", linewidth=0.8))
    ax.add_patch(Rectangle((-1, -0.5), 2, 1, facecolor=dk.FR4, edgecolor="k", alpha=0.6))
    t = np.linspace(0, 2 * np.pi, 100)
    ax.plot(0.31387 * np.cos(t), 0.31387 * np.sin(t), color=dk.HEAT, linewidth=1.6)
    ax.plot(0, 0, "o", color=dk.HEAT, markersize=3)
    ax.text(0, -1.05, "dx = 2, dy = 1: r0 = 0.31387\n(circle drawn, unit sink in the centre)", ha="center", fontsize=7)
    ax.set_title("a. non-square cell, isotropic", fontsize=8)
    # (b) anisotropy: a circle in the plane is an ellipse after x/sqrt(Kx), y/sqrt(Ky); its equivalent circle has the mean semi-axis
    ax = axs[1]
    ax.set_xlim(-3, 7.2)
    ax.set_ylim(-2.4, 2.6)
    ax.set_aspect("equal")
    ax.plot(-1.5 + 1.2 * np.cos(t), 1.2 * np.sin(t), color=dk.HEAT, linewidth=1.6)
    ax.text(-1.5, -1.7, "physical well, radius r_w", ha="center", fontsize=7)
    dk.arrow(ax, 0.1, 0, 1.6, 0, label="x/sqrt(Kx), y/sqrt(Ky)", size=7)
    ax.plot(4.5 + 0.6 * np.cos(t), 1.2 * np.sin(t), color=dk.HEAT, linewidth=1.6)
    ax.plot(4.5 + 0.9 * np.cos(t), 0.9 * np.sin(t), "--", color=dk.BLUE, linewidth=1.2)
    ax.text(4.5, -1.7, "ellipse and its equivalent circle\n(mean semi-axis): factor\n2 sqrt(KxKy)/(sqrt(Kx)+sqrt(Ky))", ha="center", fontsize=7)
    ax.set_title("b. anisotropy by stretching (Kx = 4, Ky = 1: r0 = 0.20924)", fontsize=8)
    # (c) the program's treatment: footprint of cells, mean potential, well of radius 0.78 r_v, barrel nodes reduced into couplings
    ax = axs[2]
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.5, 3.5)
    ax.set_aspect("equal")
    for i in range(-3, 3):
        for j in range(-3, 3):
            inside = (i + 0.5) ** 2 + (j + 0.5) ** 2 <= 2.3 ** 2
            ax.add_patch(Rectangle((i, j), 1, 1, facecolor=dk.COPPER if inside else "none", edgecolor="#888", linewidth=0.8, alpha=0.8))
    ax.plot(1.1 * np.cos(t), 1.1 * np.sin(t), color=dk.HEAT, linewidth=1.6)
    ax.plot(2.3 * np.cos(t), 2.3 * np.sin(t), ":", color="k", linewidth=1)
    ax.text(0, -3.3, "footprint of cells (shaded) on one plane;\nits mean potential is the via node;\nwell radius 0.78 r_v; barrel nodes Kron-reduced", ha="center", fontsize=7)
    ax.set_title("c. the via footprint on the grid", fontsize=8)
    dk.save(fig, path)


# Evidence levels of docs/models-evidence-and-gaps.md section 4: 2 strong (reproduced within a few per cent),
# 1 partial or indirect (a limit, a bracket, a plot reading, an assumed layout), 0 none. The rows and the levels are
# the table of that document; no number is drawn, only the level.
EVIDENCE_COLUMNS = ("closed form /\nexact case", "published case\nreproduced", "independent\nsolver (3D, 2D)", "physical\nmeasurement")
EVIDENCE_ROWS = (
    ("laminate and spreading (layered board)", (2, 2, 2, 1)),
    ("patterned copper (fill, laminate nodes)", (1, 1, 2, 0)),
    ("vias (well, Kron, constriction)", (2, 1, 2, 1)),
    ("metal block and fins", (2, 1, 2, 0)),
    ("natural convection, vertical face", (2, 2, 1, 1)),
    ("natural convection, horizontal faces", (1, 1, 1, 0)),
    ("forced convection", (2, 2, 0, 0)),
    ("radiation (view factor 1)", (2, 0, 0, 0)),
    ("mixed convection blend", (1, 0, 0, 0)),
    ("board edge (h_side)", (2, 2, 1, 0)),
    ("outline (cut cells, equal-area rectangle)", (0, 1, 2, 0)),
    ("parts: junction, theta, datasheet RthJA", (1, 2, 1, 1)),
    ("top path (heatsink on the package)", (1, 0, 0, 0)),
    ("transient and power profiles", (2, 0, 0, 0)),
    ("imported copper (Gerber mapping)", (0, 0, 2, 0)),
)


def evidence_matrix(path):
    """!
    @brief The evidence behind each physical ingredient of the models, by kind of reference (section 4 of docs/models-evidence-and-gaps.md).
    @details Green: reproduced within a few per cent; amber: partial or indirect (a bracket, a plot, an assumed layout, outside the published range);
             grey: none. The last column is the main risk: no copper printed-circuit board has been compared with a measurement of its own.
    @param path Output file.
    @return None.
    """
    colours = {2: "#7fc97f", 1: "#fdc086", 0: "#d9d9d9"}
    words = {2: "yes", 1: "partial", 0: "none"}
    fig, ax = dk.canvas(11, 7.2)
    n = len(EVIDENCE_ROWS)
    ax.set_xlim(-6.2, len(EVIDENCE_COLUMNS) * 1.6 + 0.2)
    ax.set_ylim(-0.6, n + 1.6)
    # Column headers above the grid
    for j, name in enumerate(EVIDENCE_COLUMNS):
        ax.text(j * 1.6 + 0.8, n + 0.75, name, ha="center", va="center", fontsize=8, weight="bold")
    # One row per ingredient, top to bottom in the order of the table
    for i, (name, levels) in enumerate(EVIDENCE_ROWS):
        y = n - 1 - i
        ax.text(-0.15, y + 0.45, name, ha="right", va="center", fontsize=8)
        for j, lev in enumerate(levels):
            ax.add_patch(Rectangle((j * 1.6 + 0.05, y + 0.05), 1.5, 0.8, facecolor=colours[lev], edgecolor="k", linewidth=0.6))
            ax.text(j * 1.6 + 0.8, y + 0.45, words[lev], ha="center", va="center", fontsize=7)
    # Mark the measurement column: the main risk of the program
    ax.add_patch(Rectangle((3 * 1.6 + 0.0, -0.05), 1.6, n + 0.05, fill=False, edgecolor="#c0392b", linewidth=2.0))
    ax.text(3 * 1.6 + 0.8, -0.4, "main risk: no copper board measured", ha="center", va="center", fontsize=7, color="#c0392b")
    dk.save(fig, path, "Evidence behind each ingredient of the five models")


def test_board_plan(path):
    """!
    @brief The cheap measurement proposed in section 6 of docs/models-evidence-and-gaps.md: a two-layer board with a resistor of known power, thermocouples and an infrared view.
    @details (a) plan: the 100 x 80 mm board, a power resistor (or a MOSFET used as a heater) at the centre and one near an edge, thermocouples at the source, on a ring and at a corner;
             (b) section: the heat paths (into the copper, across the laminate, to the air by convection and radiation) and where each sensor sits;
             (c) the comparison: the measured rise against the five models at three powers, so that the convection law (which grows with the rise) and the conduction (which does not) are separated.
             Illustrative: no measured number is drawn.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(13, 4.4, 1, 3, ratios=[1.1, 1.2, 1.0])
    # (a) plan of the test board
    ax = axs[0]
    ax.set_xlim(-5, 105)
    ax.set_ylim(-12, 90)
    ax.add_patch(Rectangle((0, 0), 100, 80, facecolor="#e8c07a", edgecolor="k"))
    ax.add_patch(Rectangle((45, 37), 10, 6, facecolor="#555555", edgecolor="k"))
    ax.add_patch(Rectangle((84, 37), 10, 6, facecolor="#555555", edgecolor="k"))
    for (x, y, lab) in ((50, 40, "TC1"), (65, 40, "TC2"), (50, 60, "TC3"), (8, 8, "TC4"), (89, 46, "TC5")):
        ax.plot(x, y, "o", color="#c0392b", ms=5)
        ax.text(x + 2, y + 2, lab, fontsize=7, color="#c0392b")
    ax.text(50, 84, "100 x 80 mm, 2 layers, 1.6 mm, full copper or a pad", ha="center", fontsize=7)
    ax.text(50, -7, "heater at the centre and near the edge, power V x I", ha="center", fontsize=7)
    ax.set_title("(a) plan: known power, five thermocouples", fontsize=8)
    # (b) section with the heat paths
    ax = axs[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    dk.layer(ax, 0.5, 2.6, 9, 0.15, "#b87333")
    dk.layer(ax, 0.5, 1.4, 9, 1.2, "#cfe8a9", "FR-4 laminate", 7)
    dk.layer(ax, 0.5, 1.25, 9, 0.15, "#b87333")
    dk.layer(ax, 4.2, 2.75, 1.6, 0.5, "#555555")
    ax.text(5.0, 3.0, "heater", ha="center", va="center", fontsize=7, color="w")
    dk.arrow(ax, 5.0, 2.7, 7.6, 2.7, "#c0392b", label="spreading in copper")
    dk.arrow(ax, 5.0, 2.6, 5.0, 1.45, "#c0392b")
    dk.arrow(ax, 7.5, 2.85, 8.2, 4.2, "#2c7fb8", label="convection + radiation")
    dk.arrow(ax, 7.5, 1.2, 8.2, 0.3, "#2c7fb8")
    ax.plot(5.0, 3.35, "v", color="#c0392b")
    ax.text(5.0, 3.75, "TC on the part / IR", ha="center", fontsize=7, color="#c0392b")
    ax.set_title("(b) section: where the heat goes and what is read", fontsize=8)
    # (c) what is compared (illustrative shape, no data)
    ax = axs[2]
    ax.axis("on")
    p = np.linspace(0, 1, 50)
    ax.plot(p, 60 * p ** 0.85, color="k", label="measured rise (TC1)")
    ax.plot(p, 60 * p, "--", color="#2c7fb8", label="model, fixed h")
    ax.plot(p, 62 * p ** 0.86, ":", color="#c0392b", label="model, computed h")
    ax.set_xlabel("power (relative)", fontsize=7)
    ax.set_ylabel("rise above ambient (illustrative)", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6, loc="upper left")
    ax.set_title("(c) compared at three powers (illustrative)", fontsize=8)
    dk.save(fig, path, "A cheap measurement to close the main gap")


def main():
    """!
    @brief Draw every diagram.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    lemczyk_cell(OUT / "fig_06_lemczyk_trace_cells.png")
    culham_coupon(OUT / "fig_07_culham_coupon_and_modes.png")
    duality(OUT / "fig_08_duality_and_effective_medium.png")
    foster_cauer(OUT / "fig_09_foster_and_cauer_networks.png")
    gerber_hole(OUT / "fig_10_gerber_spec_regions.png")
    muzychka_cases(OUT / "fig_11_muzychka_cases.png")
    peaceman_well(OUT / "fig_12_peaceman_well_block.png")
    evidence_matrix(OUT / "fig_14_evidence_matrix.png")
    test_board_plan(OUT / "fig_15_measurement_test_board.png")


if __name__ == "__main__":
    main()
