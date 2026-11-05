#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the rotated square: the grid cells that the outline cuts (aligned, shifted by half a cell, turned), the section of an edge cell with the path of the heat, and the edge resistances of the program and of the cut-cell copy.
@details Figures 09 to 11 (the cut-cell link of the layered FVM, its ratio to the exact value, the links around the re-entrant corner of the small T) are in the
         same file. Figures 01 to 03 of figures/ (the data figures from 04 on are drawn by make_figures.py). No solver is run: the cut cells of figure 01 come from
         `lib/cutcell.py` (the same sampling the copy uses) and the proportions of figures 02 and 03 are those of the study boards (1 mm cells, 1.6 mm
         board, copper exaggerated). Files: fig_01_cut_cells.png, fig_02_section_of_an_edge_cell.png, fig_03_edge_resistances.png.
         Usage: python research/rotated-square-3d/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))

import diagram_kit as dk                                                    # noqa: E402
import cutcell                                                              # noqa: E402
import rotsq                                                                # noqa: E402
import fvm_cutcell                                                          # noqa: E402
import matplotlib.pyplot as plt                                             # noqa: E402
from matplotlib.patches import Polygon, Rectangle                          # noqa: E402

OUT = HERE.parent / "figures"


def cells_panel(ax, angle, shift, title):
    """!
    @brief Draw a corner region of a square board on a 1 mm grid: each cell shaded by its board fraction, the outline, and the lengths of the edge in the cells.
    @param ax Axes.
    @param angle Turn of the square in degrees.
    @param shift Shift of the board against the grid in cells (both directions).
    @param title Title.
    @return None.
    """
    n, c = 14, 1e-3
    side, box = 10.0, 14.0
    poly_mm = rotsq.turned_square(side, angle, (box / 2 + shift, box / 2 + shift))
    g = cutcell.cut_geometry(np.array(poly_mm) * 1e-3, n, n, c, c)
    for i in range(n):
        for j in range(n):
            cv = g["cover"][i, j]
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=(0.88, 0.64, 0.35, cv) if cv > 0 else "none", edgecolor="#bbbbbb", lw=0.5))
            if 0 < cv < 1:
                ax.plot(g["xc"][i, j] / c, g["yc"][i, j] / c, "k.", ms=3)           # Centroid of the board part of a cut cell
    ax.add_patch(Polygon(poly_mm, closed=True, fill=False, edgecolor="#1f77b4", lw=1.6))
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=8)


def fig_cut_cells():
    """!
    @brief Figure 01: the same square on the grid three ways.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.9, 1, 3)
    for ax in axs:
        ax.axis("on")
    cells_panel(axs[0], 0, 0.0, "aligned: every edge cell is whole\n(centre 0.5 cell from the edge)")
    cells_panel(axs[1], 0, 0.5, "shifted by half a cell: edge cells half board\n(centroid of the board part 0.25 cell from the edge)")
    cells_panel(axs[2], 27, 0.0, "turned 27 degrees: cells cut at every depth,\nfrom slivers to nearly whole (dots: centroids)")
    dk.save(fig, OUT / "fig_01_cut_cells.png")


def fig_section():
    """!
    @brief Figure 02: section through one edge cell (copper on both faces, four dielectric slabs) in three positions of the outline, with the heat paths and the distances the models use.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 4.2, 1, 3)
    cases = [("aligned: whole cell", 1.0), ("shifted: half board", 0.5), ("turned: thin sliver", 0.2)]
    for ax, (name, cov) in zip(axs, cases):
        ax.set_xlim(-0.1, 1.5)
        ax.set_ylim(-0.7, 3.9)
        ax.set_title(name, fontsize=9)
        xe = cov                                                  # The board fills the left part of the cell, width cov; the outline is at x = cov
        dk.layer(ax, 0.0, 2.75, xe, 0.18, dk.COPPER)
        for k in range(4):
            dk.layer(ax, 0.0, 0.55 + 0.55 * (3 - k), xe, 0.55, dk.FR4)
        dk.layer(ax, 0.0, 0.37, xe, 0.18, dk.COPPER)
        ax.add_patch(Rectangle((0, 0.37), 1.0, 2.56, fill=False, edgecolor="#777777", ls=":", lw=0.8))   # The grid cell
        ax.plot([0.5], [1.65], "o", color="#d62728", ms=6)                                              # Cell centre: the node of the program
        ax.text(0.5, 3.35, "red: node of the program\n(cell centre, d = 0.5 cell)", ha="center", va="bottom", fontsize=6.5, color="#d62728")
        cx = xe / 2.0
        ax.plot([cx], [1.65], "s", color="#2ca02c", ms=5)                                               # Centroid of the board part: the node of the copy
        ax.text(cx, 3.05, "green: centroid, d = " + f"{cov / 2:.2f} cell", ha="center", va="bottom", fontsize=6.5, color="#2ca02c")
        ax.annotate("", xy=(xe, 0.2), xytext=(0.5, 0.2), arrowprops=dict(arrowstyle="<->", color="#d62728", lw=1.0))
        ax.annotate("", xy=(xe, 0.0), xytext=(cx, 0.0), arrowprops=dict(arrowstyle="<->", color="#2ca02c", lw=1.0))
        for yy in (2.25, 1.7, 1.15, 0.65):
            dk.arrow(ax, xe + 0.02, yy, xe + 0.25, yy, color=dk.HEAT, width=1.2)
        ax.text(1.12, 1.45, "edge\nfilm h", fontsize=7, color=dk.HEAT, va="center")
        if cov < 1.0:
            ax.text(0.5, -0.45, "program: conducts with k x cover (path 1 / cover too long)", ha="center", fontsize=6.2, color="#d62728")
    dk.save(fig, OUT / "fig_02_section_of_an_edge_cell.png")


def fig_resistances():
    """!
    @brief Figure 03: the edge element of one cell and slab in the program and in the cut-cell copy, as resistances.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.2, 1, 2)
    for ax, (title, lines) in zip(axs, [
            ("program (one cell, one slab)", ["node  --  d / (k c L dz)  --  1 / (h L dz)  --  air", "d = (dx + dy) / 4 always;  k c = conductivity x cover;",
                                              "L = outline length in the cell (moved to the nearest board cell if the cell is off)", "whole cell: c = 1, d = dx / 2: right",
                                              "half cell: c = 0.5: the conduction term doubles;  sliver: 1 / c times too long"]),
            ("cut-cell copy (one cell, one slab)", ["node  --  d / (k L dz)  --  1 / (h L dz)  --  air", "d = c dx dy / (2 L): half the depth of the board strip behind the outline",
                                                    "k = full conductivity;  links to the neighbours: aperture x dy x dz / (d1/k + d2/k)", "d1, d2 = distances from the face to the two centroids",
                                                    "whole cell: d = dx / 2 as before; half cell: d = dx / 4"])]):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.set_title(title, fontsize=9)
        dk.resistor(ax, 0.8, 3.6, 5.0, "conduction", color="#2ca02c" if "copy" in title else "#d62728")
        dk.resistor(ax, 4.4, 7.2, 5.0, "film", color=dk.BLUE)
        ax.text(0.5, 5.0, "node", ha="right", va="center", fontsize=7)
        ax.text(7.5, 5.0, "air", ha="left", va="center", fontsize=7)
        for k, t in enumerate(lines):
            ax.text(0.2, 3.7 - 0.75 * k, t, fontsize=6.8, va="center")
    dk.save(fig, OUT / "fig_03_edge_resistances.png")


def fig_cut_cell_links():
    """!
    @brief Figure 09: one cut cell of the layered FVM, the node of the program (cell centre) and of the cut-cell scheme (centroid of the board part), and the cross-section and distance of the link.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, mode in zip(axs, ("program", "cut")):
        # Three cells in a row: a whole cell, a cell cut at 0.4 of its width (board on the left, towards the whole cell) and the air beyond the outline
        c = 0.4
        for k in range(3):
            ax.add_patch(Rectangle((k, 0), 1, 1, fill=False, edgecolor="#999999", lw=0.8))
        ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=dk.COPPER, alpha=0.55))
        ax.add_patch(Rectangle((1, 0), c, 1, facecolor=dk.COPPER, alpha=0.55))
        ax.plot([1 + c, 1 + c], [-0.1, 1.1], color=dk.BLUE, lw=2.2)
        ax.text(1 + c + 0.03, 1.07, "outline", color=dk.BLUE, fontsize=8)
        ax.plot(0.5, 0.5, "ko", ms=6)
        ax.text(0.5, 0.6, "node of the\nwhole cell", ha="center", fontsize=7.5)
        if mode == "program":
            ax.plot(1.5, 0.5, "ro", ms=7)
            ax.text(1.5, 0.15, "node at the cell centre,\nconductivity x cover", ha="center", fontsize=7.5, color="#b22222")
            ax.annotate("", xy=(1.5, 0.5), xytext=(0.5, 0.5), arrowprops=dict(arrowstyle="<->", color="#b22222", lw=1.6))
            ax.text(1.0, 0.55, "one cell width", ha="center", fontsize=7.5, color="#b22222")
            ax.text(1.0, -0.3, "cross-section = cover x dy = %.1f dy;  distance = dx\ng = 2c/(1+c) S dy/dx = %.2f (S dy/dx)" % (c, 2 * c / (1 + c)),
                    ha="center", fontsize=8.5, color="#b22222")
            ax.set_title("program: the cover scales the conductivity, the distance is a cell", fontsize=9)
        else:
            xc = 1 + c / 2
            ax.plot(xc, 0.5, "go", ms=7)
            ax.text(xc + 0.02, 0.15, "node at the centroid\nof the board part", ha="center", fontsize=7.5, color="#1b7a1b")
            ax.annotate("", xy=(xc, 0.5), xytext=(0.5, 0.5), arrowprops=dict(arrowstyle="<->", color="#1b7a1b", lw=1.6))
            ax.text(0.5 + (xc - 0.5) / 2, 0.55, "d1 + d2", ha="center", fontsize=7.5, color="#1b7a1b")
            ax.annotate("", xy=(1.0, 0.1), xytext=(1.0, 0.9), arrowprops=dict(arrowstyle="<->", color="#1b7a1b", lw=1.2))
            ax.text(1.02, 0.12, "aperture = 1", fontsize=7, color="#1b7a1b")
            ax.text(1.0, -0.3, "cross-section = aperture x dy = 1.0 dy;  distance = (1 + c)/2 dx\ng = 2/(1+c) S dy/dx = %.2f (S dy/dx)" % (2 / (1 + c)),
                    ha="center", fontsize=8.5, color="#1b7a1b")
            ax.set_title("cut cell: the aperture is the cross-section, the distance runs between centroids", fontsize=9)
        ax.set_xlim(-0.1, 3.0)
        ax.set_ylim(-0.55, 1.3)
        ax.set_aspect("equal")
        ax.axis("off")
    dk.save(fig, OUT / "fig_09_cut_cell_link.png")


def fig_link_ratio():
    """!
    @brief Figure 10: conductance of the link into a cut edge cell against the cover, program and cut-cell variants, relative to the exact straight-edge value.
    @details Closed forms for an edge parallel to a grid line (board on the side of the whole neighbour): exact 2/(1+c), program 2c/(1+c), aperture only 1.
             The heat that crosses the link is small in a dead end (insulated edge) and large when the cut cell is a path (a neck, a source in the cut cell).
    @return None.
    """
    c = np.linspace(0.02, 1.0, 100)
    exact = 2.0 / (1.0 + c)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(c, 2 * c / (1 + c) / exact, color="#b22222", lw=2, label="program: harmonic mean of S and c S over a cell width (ratio = c)")
    ax.plot(c, np.ones_like(c) / exact, color="#ff7f0e", lw=2, label="aperture only, nodes at the cell centres (ratio = (1 + c)/2)")
    ax.plot(c, np.ones_like(c), color="#1b7a1b", lw=2, ls="--", label="aperture over centroid distances (exact for a straight edge)")
    ax.set_xlabel("cover c of the cut cell")
    ax.set_ylabel("link conductance / exact value")
    ax.set_ylim(0, 1.1)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title("link across the cut: straight edge parallel to a grid line", fontsize=9)
    dk.save(fig, OUT / "fig_10_link_ratio.png")


def fig_tee_links():
    """!
    @brief Figure 11: the cells and links around the re-entrant corner of the small T board (neck edge at 10.5 mm, 1 mm cells), program and cut-cell links.
    @details Cells shaded by cover, dots at the nodes (cell centres in the program, centroids in the cut-cell scheme), the width of every line drawn between
             two nodes proportional to the lateral conductance of the top layer (numbers of the network of the program and of the prototype; no solve).
    @return None.
    """
    import study_cut_cells_fvm as st
    from pcbthermal import fvm
    p = st.small_t(10.5)
    nx, ny = 30, 24
    net0 = fvm.Network(p, nx, ny, assemble=False)
    fvm_cutcell.CutCellNetwork.mode = "links"
    net1 = fvm_cutcell.CutCellNetwork(p, nx, ny, assemble=False)
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.2))
    x0, x1, y0, y1 = 6, 15, 7, 16
    for ax, net, title in ((axs[0], net0, "program: nodes at the cell centres, links scaled by the cover"),
                           (axs[1], net1, "cut-cell links: nodes at the centroids, links by aperture and distance")):
        for i in range(y0, y1):
            for j in range(x0, x1):
                cv = net.cover[i, j]
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=(0.88, 0.64, 0.35, cv) if cv > 0 else "none", edgecolor="#cccccc", lw=0.5))
        if net is net1:
            gx, gy = net._lateral_links()
            xc, yc = net.geo["xc"] / net.dx, net.geo["yc"] / net.dy
        else:
            gx = net._harmonic(net.S[:, :, :-1], net.S[:, :, 1:]) * net.dy / net.dx
            gy = net._harmonic(net.S[:, :-1, :], net.S[:, 1:, :]) * net.dx / net.dy
            xc, yc = np.tile(np.arange(nx) + 0.5, (ny, 1)), np.tile((np.arange(ny) + 0.5)[:, None], (1, nx))
        ref = net.S[0].max() * net.dy / net.dx
        for i in range(y0, y1):
            for j in range(x0, x1):
                if j + 1 < nx and gx[0, i, j] > 0:
                    ax.plot([xc[i, j], xc[i, j + 1]], [yc[i, j], yc[i, j + 1]], color="#444444", lw=4.0 * gx[0, i, j] / ref, solid_capstyle="butt")
                if i + 1 < ny and gy[0, i, j] > 0:
                    ax.plot([xc[i, j], xc[i + 1, j]], [yc[i, j], yc[i + 1, j]], color="#444444", lw=4.0 * gy[0, i, j] / ref, solid_capstyle="butt")
        sel = net.active[y0:y1, x0:x1]
        ax.plot(xc[y0:y1, x0:x1][sel], yc[y0:y1, x0:x1][sel], "r." if net is net0 else "g.", ms=6)
        ax.add_patch(Polygon(np.array(p.board.outline) * 1000.0, closed=True, fill=False, edgecolor=dk.BLUE, lw=1.8))
        ax.add_patch(Rectangle((9, 10), 3, 4, fill=False, edgecolor="#c1440e", lw=1.6, ls="--"))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=9)
    fig.suptitle("Small T board, neck edge at 10.5 mm: line width = lateral conductance of the top layer (dashed: the part)", fontsize=10)
    dk.save(fig, OUT / "fig_11_tee_links.png")


def fig_ingredients():
    """!
    @brief Figure 15: what the cut-cell links need from one corner cell (cover for the capacity and the films, apertures of the four faces for the links, centroid for the distances), and the section of an edge cell with the paths of the heat.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.9), gridspec_kw={"width_ratios": [1, 1.15]})
    ax = axs[0]
    # Plan view: a corner cell of a turned square, board in the lower left, the outline a straight cut across the cell
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, edgecolor="#777777", lw=1.0))
    tri = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 0.35], [0.45, 1.0], [0.0, 1.0]])
    ax.add_patch(Polygon(tri, closed=True, facecolor=dk.COPPER, alpha=0.55, edgecolor="none"))
    ax.plot([1.0, 0.45], [0.35, 1.0], color=dk.BLUE, lw=2.4)
    ax.text(0.78, 0.8, "outline", color=dk.BLUE, fontsize=8, rotation=-49)
    cx, cy = tri[:, 0].mean() * 0.93, tri[:, 1].mean() * 0.93
    ax.plot(cx, cy, "go", ms=8)
    ax.plot(0.5, 0.5, "ko", ms=4)
    ax.text(cx - 0.02, cy - 0.12, "node = centroid\nof the board part", color="#1b7a1b", fontsize=7.5, ha="center")
    ax.text(0.52, 0.56, "cell centre", fontsize=7, ha="left")
    ax.annotate("", xy=(1.0, 0.02), xytext=(1.0, 0.35), arrowprops=dict(arrowstyle="<->", color="#c1440e", lw=1.4))
    ax.text(1.03, 0.08, "aperture of the\neast face\na_E = 0.33", fontsize=7.5, color="#c1440e")
    ax.annotate("", xy=(0.02, 1.0), xytext=(0.45, 1.0), arrowprops=dict(arrowstyle="<->", color="#c1440e", lw=1.4))
    ax.text(0.1, 1.04, "a_N = 0.45", fontsize=7.5, color="#c1440e")
    ax.text(-0.05, 0.5, "a_W = 1", fontsize=7.5, color="#c1440e", ha="right")
    ax.text(0.5, -0.07, "a_S = 1", fontsize=7.5, color="#c1440e", ha="center")
    ax.text(0.5, -0.30, "cover c = board area / cell area: capacity C = c C0, films to the air c h dx dy,\nsheet S = c S0 (program); links g = a L_face / (d1/S0 + d2/S0)\n(S0 = sheet conductance of a whole cell)", fontsize=7.8, ha="center", va="top")
    ax.set_xlim(-0.35, 1.45)
    ax.set_ylim(-0.75, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("plan: a corner cell of the board outline", fontsize=9)
    ax = axs[1]
    # Section: top copper, laminate, bottom copper; the board ends at the outline inside the cell; films on the end face and on both faces
    x_cell0, x_out, x_cell1 = 2.0, 2.45, 3.0
    ax.add_patch(Rectangle((0, 1.8), x_out, 0.22, facecolor=dk.COPPER, edgecolor="k", lw=0.6))
    ax.add_patch(Rectangle((0, 0.0), x_out, 0.22, facecolor=dk.COPPER, edgecolor="k", lw=0.6))
    ax.add_patch(Rectangle((0, 0.22), x_out, 1.58, facecolor="#e4d7a6", edgecolor="k", lw=0.6))
    ax.plot([x_cell0, x_cell0], [-0.35, 2.45], color="#777777", lw=1.0, ls="--")
    ax.plot([x_cell1, x_cell1], [-0.35, 2.45], color="#777777", lw=1.0, ls="--")
    ax.text(x_cell0 + 0.5, 2.55, "edge cell (width dx)", fontsize=7.5, ha="center")
    ax.plot(x_cell0 + (x_out - x_cell0) / 2, 1.91, "go", ms=7)
    ax.plot(x_cell0 + (x_out - x_cell0) / 2, 0.11, "go", ms=7)
    ax.text(0.1, -0.3, "green: node at the centroid\nof the board part of the cell", fontsize=7.2, color="#1b7a1b")
    dk.arrow(ax, 0.6, 1.91, 2.15, 1.91, color=dk.HEAT)
    ax.text(0.2, 2.45, "lateral flow through the aperture,\ndistance d1 + d2", fontsize=7.3, color=dk.HEAT)
    dk.arrow(ax, 1.2, 1.7, 1.2, 0.35, color=dk.HEAT)
    ax.text(1.25, 1.0, "through the\nlaminate", fontsize=7.2, color=dk.HEAT)
    dk.arrow(ax, 2.25, 2.04, 2.25, 2.35, color=dk.BLUE)
    dk.arrow(ax, 2.25, -0.02, 2.25, -0.33, color=dk.BLUE)
    dk.arrow(ax, x_out, 1.0, x_out + 0.45, 1.0, color=dk.BLUE)
    ax.text(x_out + 0.05, 1.12, "edge film\nh t L", fontsize=7.2, color=dk.BLUE)
    ax.text(2.2, -0.62, "section along x through the edge cell: the node lives at the centroid of the board part and the film acts on the node (the program's\nconvention); the variant links+strip also puts half the depth of the strip, c dx dy / (2 L), of conduction in series with the edge film", fontsize=7.2, ha="center", va="top")
    ax.set_xlim(-0.1, 3.4)
    ax.set_ylim(-1.0, 2.9)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("section: the edge cell and the paths of the heat", fontsize=9)
    dk.save(fig, OUT / "fig_15_cut_cell_ingredients.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_cut_cells()
    fig_section()
    fig_resistances()
    fig_cut_cell_links()
    fig_link_ratio()
    fig_tee_links()
    fig_ingredients()
