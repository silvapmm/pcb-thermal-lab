#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: what the program's SOR iterates against the true matrix, the red-black colouring over a via footprint, and the sweep of each variant.
@details Figures 01 to 03 of figures/ (the data figures 04 and later are drawn by make_figures.py). No study is run and nothing of the program is imported; the footprint drawn is an
         illustrative 3 x 3 patch of cells (the real footprints of the studies are 1 to 4 cells at the 0.25 mm cell and larger at finer grids, see README section 2).
         Files: fig_01_what_the_program_iterates.png, fig_02_colouring_over_a_footprint.png, fig_03_sweeps_of_the_variants.png.
         Usage: python research/sor-with-via-couplings/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def _matrix(ax, M, title, cmap_pos="#d62728", cmap_neg="#1f77b4", stencil="#bbbbbb", dropped=None):
    """!
    @brief Draw a small matrix as coloured squares (stencil grey, via entries red for positive and blue for negative, dropped entries hatched).
    @param ax Axes.
    @param M Dict {(i, j): kind} with kind in "diag", "sten", "pos", "neg".
    @param title Title.
    @param cmap_pos Colour of positive via entries.
    @param cmap_neg Colour of negative via entries.
    @param stencil Colour of stencil entries.
    @param dropped Set of (i, j) drawn with a cross (entries the program's rule leaves out).
    @return None.
    """
    n = 1 + max(i for i, _ in M)
    col = {"diag": "#555555", "sten": stencil, "pos": cmap_pos, "neg": cmap_neg}
    for (i, j), k in M.items():
        ax.add_patch(Rectangle((j, n - 1 - i), 1, 1, facecolor=col[k], edgecolor="white", linewidth=0.8))
        if dropped and (i, j) in dropped:
            ax.plot([j + 0.15, j + 0.85], [n - 1 - i + 0.15, n - 1 - i + 0.85], color="k", linewidth=1.3)
            ax.plot([j + 0.15, j + 0.85], [n - 1 - i + 0.85, n - 1 - i + 0.15], color="k", linewidth=1.3)
    ax.add_patch(Rectangle((0, 0), n, n, fill=False, edgecolor="k", linewidth=1.0))
    ax.set_xlim(-0.2, n + 0.2)
    ax.set_ylim(-0.2, n + 0.2)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)


def fig_program_vs_true(path):
    """!
    @brief The 4 x 4 toy (two layers, two cells, one via over both cells): the matrix K, the matrix the program's SOR iterates, and the entries it drops.
    @param path Output file.
    @return None.
    """
    # Unknowns 0 top a, 1 top b, 2 bottom a, 3 bottom b. Stencil: (0,1), (2,3) in plane; (0,2), (1,3) vertical. Via part: all pairs; same layer positive, cross layer negative
    K, Kp = {}, {}
    for i in range(4):
        K[(i, i)] = "diag"
        Kp[(i, i)] = "diag"
    for i, j in ((0, 1), (1, 0), (2, 3), (3, 2), (0, 2), (2, 0), (1, 3), (3, 1)):
        K[(i, j)] = "sten"
        Kp[(i, j)] = "sten"
    same = {(0, 1), (1, 0), (2, 3), (3, 2)}
    cross = {(0, 2), (2, 0), (1, 3), (3, 1), (0, 3), (3, 0), (1, 2), (2, 1)}
    for (i, j) in same | cross:
        K[(i, j)] = "pos" if (i, j) in same else "neg"                     # the via part adds to the stencil position; colour shows the via sign
    dropped = same | cross
    fig, axs = dk.canvas(13, 4.6, 1, 4, ratios=[1, 1, 1, 1.15])
    for a in axs[:3]:
        a.axis("on"); a.set_xticks([]); a.set_yticks([])
    _matrix(axs[0], K, "true K = stencil + via part\n(grey diagonal; red = positive, blue = negative via entry)", dropped=None)
    Kdrop = {k: v for k, v in K.items() if v == "diag" or k in Kp and Kp[k] == "sten"}
    for k in Kdrop:
        if Kdrop[k] == "sten":
            Kdrop[k] = "sten"
    _matrix(axs[1], Kdrop, "what the program's rule iterates:\nstencil off-diagonals + diagonal of K", dropped=None)
    _matrix(axs[2], K, "entries it leaves out (crossed)", dropped=dropped)
    ax = axs[3]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.text(0.2, 9.2, "Consequence (toy of README 2.1)", fontsize=9, weight="bold")
    ax.text(0.2, 7.2, "kept: the diagonal g w$^2$ of the via\n(a leak to the ambient that was never there)", fontsize=8, color="#555555")
    ax.text(0.2, 5.0, "lost: the via path top to bottom,\nthe positive in-plane terms inside the footprint", fontsize=8, color=dk.BLUE)
    ax.text(0.2, 2.6, "the limit of the sweeps is the solution of\nthe dropped matrix: 0.21 against 1.09 (top),\nthe residual of the true K never falls", fontsize=8, color=dk.HEAT)
    dk.save(fig, path)


def fig_colouring(path):
    """!
    @brief Red-black colouring of the cells of two layers with a via footprint of 3 x 3 cells: which couplings the colouring cannot separate.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12.5, 5.2, 1, 2, ratios=[1, 1])
    for ax in (a, b):
        ax.set_xlim(-0.3, 9.3); ax.set_ylim(-0.3, 5.3); ax.set_aspect("equal")
    # (a) plan view of one layer, 5 x 5 cells, checkerboard; footprint = central 3 x 3 cells
    n = 5
    for i in range(n):
        for j in range(n):
            red = (i + j) % 2 == 0
            foot = 1 <= i <= 3 and 1 <= j <= 3
            a.add_patch(Rectangle((j + 2.0, i), 1, 1, facecolor="#f4b6b6" if red else "#cfcfcf", edgecolor="k", linewidth=0.6))
            if foot:
                a.add_patch(Rectangle((j + 2.0, i), 1, 1, fill=False, edgecolor=dk.HEAT if False else "#2c7a2c", linewidth=2.2))
    cx = lambda j: j + 2.5                                                     # noqa: E731
    cy = lambda i: i + 0.5                                                     # noqa: E731
    # same-colour pairs inside the footprint (diagonal neighbours are the same colour): the via part couples them with a positive entry
    for (i0, j0, i1, j1) in ((1, 1, 2, 2), (1, 3, 2, 2), (3, 1, 2, 2), (3, 3, 2, 2), (1, 1, 1, 3), (1, 1, 3, 1), (3, 1, 3, 3), (1, 3, 3, 3)):
        a.plot([cx(j0), cx(j1)], [cy(i0), cy(i1)], color=dk.HEAT, linewidth=1.5)
    a.text(4.5, -0.25, "plan of one plane: pink = red cells, grey = black cells; green frame = via footprint\n"
           "red lines = couplings of the via part between cells of the same colour", ha="center", va="top", fontsize=8)
    a.set_title("(a) the stencil couples a cell only to the other colour;\nthe via part couples the whole footprint", fontsize=9)
    # (b) side view of two layers; the footprint cells of both layers are joined to each other
    for L, y in ((0, 3.0), (1, 0.6)):
        for j in range(n):
            red = (j + L) % 2 == 0
            b.add_patch(Rectangle((j + 2.0, y), 1, 0.8, facecolor="#f4b6b6" if red else "#cfcfcf", edgecolor="k", linewidth=0.6))
            if 1 <= j <= 3:
                b.add_patch(Rectangle((j + 2.0, y), 1, 0.8, fill=False, edgecolor="#2c7a2c", linewidth=2.2))
    b.text(1.7, 3.4, "layer 1", ha="right", va="center", fontsize=8); b.text(1.7, 1.0, "layer 2", ha="right", va="center", fontsize=8)
    for j0 in (3, 4, 5):
        for j1 in (3, 4, 5):
            col = "#2c7a2c" if j0 == j1 else dk.BLUE
            b.plot([j0 + 0.5, j1 + 0.5], [3.0, 1.4], color=col, linewidth=1.0 if j0 != j1 else 1.8, alpha=0.9)
    b.text(4.5, 0.1, "section through the footprint: every cell of plane 1 is joined to every cell of plane 2\n"
           "(green: the vertical link of the point treatment; blue: the extra cross terms of the mean-potential coupling)", ha="center", va="top", fontsize=8)
    b.set_title("(b) the same coupling across the layers", fontsize=9)
    fig.subplots_adjust(bottom=0.2)
    dk.save(fig, path)


def fig_variants(path):
    """!
    @brief One sweep of each variant, as boxes: the colours, the via term, the block solve, the capacitance matrix, the SSOR preconditioner.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(13, 6.4)
    ax.set_xlim(0, 13); ax.set_ylim(0, 6.4)
    rows = [("program (fails)", ["red cells", "black cells"], "#f4c7c7", "uses stencil off-diagonals only"),
            ("(a) lagged", ["red cells\n- K$_{via}\\theta$", "black cells\n- K$_{via}\\theta$"], "#cfe3f5", "via part in the residual, old values inside a colour"),
            ("(c) block", ["red cells\n(not via)", "black cells\n(not via)", "via blocks:\ndense solve"], "#d5ecd0", "footprint x layers = one block per via"),
            ("(b) Woodbury", ["SOR on A\n(m + 1 solves)", "capacitance\nm x m, direct"], "#fdebc8", "A = K - K$_{via}$ is an M-matrix; m = layers x vias"),
            ("(d) SSOR-CG", ["forward sweep", "diagonal", "backward sweep", "CG step"], "#e6d8f0", "SSOR is the preconditioner; K is the true matrix")]
    for r, (name, steps, color, note) in enumerate(rows):
        y = 5.2 - r * 1.2
        ax.text(0.1, y + 0.4, name, fontsize=9, weight="bold", va="center")
        x = 2.2
        for k, s in enumerate(steps):
            dk.box(ax, x, y, 1.8, 0.8, s, color, size=7.5)
            if k < len(steps) - 1:
                dk.arrow(ax, x + 1.8, y + 0.4, x + 2.1, y + 0.4)
            x += 2.1
        ax.text(x + 0.3, y + 0.4, note, fontsize=8, va="center", style="italic")
    ax.text(0.1, 6.15, "One iteration of every variant; the residual is always measured on the true K", fontsize=9)
    dk.save(fig, path)


def main():
    """!
    @brief Draw the three diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_program_vs_true(OUT / "fig_01_what_the_program_iterates.png")
    fig_colouring(OUT / "fig_02_colouring_over_a_footprint.png")
    fig_variants(OUT / "fig_03_sweeps_of_the_variants.png")


if __name__ == "__main__":
    main()
