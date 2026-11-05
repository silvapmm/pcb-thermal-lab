#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the memory guard: the flow from the board to the verdict, the board section with the nodes that the unknown count must include, and the two numberings of the unknowns with the matrix pattern each gives.
@details Figures 01 to 03 of figures/ (no data, no program run; the data figures are drawn by make_figures.py once out/fit.json exists, with the numbers after 03).
         Files: fig_01_guard_flow.png, fig_02_board_section_and_unknowns.png, fig_03_numbering_and_matrix_pattern.png.
         Usage: python research/memory-guard/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                   # noqa: E402
import matplotlib.pyplot as plt                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_guard_flow():
    """!
    @brief Figure 01: board -> cell -> unknown count and class -> estimate -> verdict, with the limit and the three places that use it.
    @return None.
    """
    fig, ax = dk.canvas(11, 4.6)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    dk.box(ax, 0.1, 3.3, 1.8, 0.9, "Problem\n(board, parts,\nvias, blocks)")
    dk.box(ax, 2.3, 3.3, 1.6, 0.9, "cell (mm)\nmodels chosen")
    dk.box(ax, 4.3, 3.3, 2.2, 0.9, "unknowns N and class\nfvm.unknowns, fdm.unknowns,\nsolid3d.unknowns")
    dk.box(ax, 6.9, 3.3, 2.0, 0.9, "estimate\nbase + k N (N/Nref)^(p-1)\nper class", color="#f6e3b4")
    dk.box(ax, 9.2, 3.3, 1.6, 0.9, "verdict\nok / slow / refuse", color="#f6e3b4", bold=True)
    for x0, x1 in ((1.9, 2.3), (3.9, 4.3), (6.5, 6.9), (8.9, 9.2)):
        dk.arrow(ax, x0, 3.75, x1, 3.75)
    dk.box(ax, 6.9, 1.9, 2.0, 0.8, "limit = fraction x RAM\n(Preferences, 70 %)", color="#d6ecd2")
    dk.arrow(ax, 7.9, 2.7, 7.9, 3.3)
    dk.box(ax, 4.3, 1.9, 2.2, 0.8, "physical RAM\nsysconf / sysctl / ctypes\n(fallback: fixed limit)", color="#d6ecd2")
    dk.arrow(ax, 6.5, 2.3, 6.9, 2.3)
    for i, (txt, x) in enumerate((("api.simulate\nrefuse before building", 0.1), ("jobs (process)\nsame check", 2.7), ("interface\ncount + colour in the panel,\nAuto cell that fits", 5.3), ("CLI\nmessage and exit code", 8.4))):
        dk.box(ax, x, 0.15, 2.4, 0.9, txt, color="#e8e8e8")
        dk.arrow(ax, 10.0, 3.3, x + 1.2, 1.05, color="#999999", style="-|>", width=0.8)
    ax.text(10.0, 4.4, "same function for all four", ha="center", fontsize=7, style="italic")
    dk.save(fig, OUT / "fig_01_guard_flow.png", "The memory guard: from the board to the verdict")


def fig_section_and_unknowns():
    """!
    @brief Figure 02: a section of a two-layer board with copper absent in one region: the node layers, the laminate nodes that exist only in the flagged cells, and why the count is not layers x cells.
    @return None.
    """
    fig, ax = dk.canvas(10, 4.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.2)
    # Board section: top copper on the left 7 cells, bottom copper on the right 7 cells (cells 1..12)
    for i in range(12):
        x = 0.5 + i * 0.9
        top_cu, bot_cu = i < 7, i >= 5
        dk.layer(ax, x, 3.3, 0.9, 0.18, dk.COPPER if top_cu else "#ffffff")
        dk.layer(ax, x, 1.4, 0.9, 0.18, dk.COPPER if bot_cu else "#ffffff")
        dk.layer(ax, x, 1.58, 0.9, 1.72, dk.FR4)
        ax.text(x + 0.45, 0.95, str(i + 1), ha="center", fontsize=7)
        # Nodes: one per copper layer in every cell; laminate nodes only next to absent copper
        ax.plot(x + 0.45, 3.39, "o", color="k", ms=4)
        ax.plot(x + 0.45, 1.49, "o", color="k", ms=4)
        if not top_cu or not bot_cu:
            for yy in (2.9, 2.45, 2.0):
                ax.plot(x + 0.45, yy, "s", color=dk.HEAT, ms=4)
    ax.text(6.5, 4.15, "top copper: cells 1-7", ha="center", fontsize=8)
    ax.text(6.5, 0.4, "bottom copper: cells 6-12 (cells 6 and 7 have both)", ha="center", fontsize=8)
    ax.text(11.5, 3.75, "black dot: copper node (every cell)", fontsize=7, va="center", ha="right")
    ax.text(11.5, 0.72, "red squares: laminate nodes of the rule (only where a copper layer is absent)", fontsize=7, va="center", ha="right", color=dk.HEAT)
    ax.text(0.5, 4.9, "unknowns = (copper layers x cells) + laminate nodes, so the count shown must come from fvm.unknowns, not from layers x cells", fontsize=8.5)
    dk.save(fig, OUT / "fig_02_board_section_and_unknowns.png")


def _pattern(nl, ny, nx, cell_major):
    """!
    @brief Sparsity pattern of the 7-point stencil of nl layers on an ny x nx grid in a numbering.
    @param nl Layers.
    @param ny Rows.
    @param nx Columns.
    @param cell_major True: index = cell * nl + layer; False: index = layer * cells + cell.
    @return Boolean square matrix.
    """
    n_c = ny * nx
    idx = (lambda l, j, i: (j * nx + i) * nl + l) if cell_major else (lambda l, j, i: l * n_c + j * nx + i)
    A = np.zeros((nl * n_c,) * 2, dtype=bool)
    for l in range(nl):
        for j in range(ny):
            for i in range(nx):
                a = idx(l, j, i)
                A[a, a] = True
                for dl, dj, di in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
                    if l + dl < nl and j + dj < ny and i + di < nx:
                        b = idx(l + dl, j + dj, i + di)
                        A[a, b] = A[b, a] = True
    return A


def fig_numbering():
    """!
    @brief Figure 03: two layers on a 4 x 5 grid numbered layer by layer and cell by cell, with the matrix pattern of each (the nodes of one cell sit next to each other in the second).
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.6))
    for ax, cm, title in zip(axs, (False, True), ("layer-major (today): index = layer x cells + cell", "cell-major: index = cell x layers + layer")):
        A = _pattern(3, 4, 5, cm)
        ax.spy(A, markersize=2.5, color="k")
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel(f"{A.sum()} non-zeros of a 3-layer 4 x 5 board; the band width is {np.max(np.abs(np.nonzero(A)[0] - np.nonzero(A)[1]))}", fontsize=7.5)
    dk.save(fig, OUT / "fig_03_numbering_and_matrix_pattern.png", "The same matrix in two numberings (the ordering of the factorisation starts from this pattern)")


def main():
    """!
    @brief Draw all the diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_guard_flow()
    fig_section_and_unknowns()
    fig_numbering()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
