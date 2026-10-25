"""!
@file make_diagrams.py
@brief Schematic diagrams of the outline rule: a board with an outline, the bounding box, and the rectangle of the same area on which the Lumped and Analytic models are run, with the positions scaled and the field stretched back.
@details Pure drawing. Writes figures/fig_04_outline_to_rectangle_schematic.png.
         Also writes figures/fig_05_cells_on_an_outline.png (the grid on a T board and the cell cover).
         And figures/fig_07_edge_assignment.png: the boundary samples given to the cells before and after the edge fix, computed on real cells by `geometry.edge_length_per_cell` and `geometry.edge_length_on_board` of the program (the old rule is the local copy `edge_before` of `study_edge_on_grid_lines.py`).
         Run: .venv/bin/python research/outline/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
T_OUTLINE = [(0, 6), (10, 6), (10, 4), (6.5, 4), (6.5, 0), (3.5, 0), (3.5, 4), (0, 4)]


def area(poly):
    """!
    @brief Area of a polygon (shoelace).
    @param poly List of (x, y) vertices.
    @return float Area.
    """
    p = np.array(poly)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def draw_board(ax, title):
    """!
    @brief The board with its outline (a T), a heater near the edge and a heater in the stem, and the bounding box dashed.
    @param ax Axes.
    @param title Panel title.
    @return None.
    """
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 7)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, 0), 10, 6, fill=False, edgecolor="r", linestyle="--"))
    ax.text(5, 6.3, "bounding box: larger than the board", color="r", fontsize=7, ha="center")
    ax.add_patch(Polygon(T_OUTLINE, facecolor=dk.FR4, edgecolor="k", linewidth=1.5))
    ax.add_patch(Rectangle((1.0, 4.6), 1.2, 1.0, facecolor="#444444"))
    ax.add_patch(Rectangle((4.4, 0.8), 1.2, 1.0, facecolor="#444444"))
    ax.text(5, 3.0, "the board", ha="center", fontsize=8)
    ax.set_title(title, fontsize=9)


def blend(cover):
    """!
    @brief Colour of a cell from its cover fraction: ambient blue (0) to laminate green (1).
    @param cover Fraction of the cell on the board, 0 to 1.
    @return tuple RGB colour.
    """
    blue = np.array([0xcf, 0xe3, 0xf5]) / 255.0
    green = np.array([0x9b, 0xbf, 0x8a]) / 255.0
    return tuple(blue + (green - blue) * cover)


def cell_cover(path):
    """!
    @brief Draw the grid of the finite volumes on a T-shaped board: cells fully on the board, cells partly on it (cover fraction) and cells outside it, pinned to ambient.
    @param path Output file.
    @return None.
    """
    from matplotlib.path import Path as MPath
    poly = [(0, 6), (12, 6), (12, 9), (7.4, 9), (7.4, 14), (4.6, 14), (4.6, 9), (0, 9)]
    poly = [(x, y) for x, y in poly]
    mp = MPath(poly + [poly[0]])
    sub = np.linspace(0.125, 0.875, 4)
    fig, (a1, a2) = dk.canvas(12, 6.0, 1, 2, ratios=[1.5, 1])
    a1.set_xlim(-0.5, 13.5)
    a1.set_ylim(5.4, 15.9)
    a1.set_aspect("equal")
    # tilt the board outline by half a cell so that some cells are cut by the edge
    off = 0.35
    shifted = MPath([(x + off, y + off) for x, y in poly + [poly[0]]])
    for i in range(13):
        for j in range(6, 15):
            pts = [(i + a, j + b) for a in sub for b in sub]
            cover = shifted.contains_points(pts).mean()
            color = blend(cover)
            a1.add_patch(Rectangle((i, j), 1, 1, facecolor=color, edgecolor="#777777", linewidth=0.5))
            if 0 < cover < 1:
                a1.text(i + 0.5, j + 0.5, f"{cover:.2f}", ha="center", va="center", fontsize=5.5)
    a1.add_patch(Polygon([(x + off, y + off) for x, y in poly], fill=False, edgecolor="k", linewidth=2))
    a1.text(6, 15.5, "the grid on a T-shaped board", ha="center", fontsize=9, fontweight="bold")
    # legend
    a2.set_xlim(0, 8)
    a2.set_ylim(0, 8)
    for k, (c, t) in enumerate((("#cfe3f5", "cover 0: outside the board,\npinned to the ambient temperature"), (dk.FR4, "cover 1: a full cell of the board"), (blend(0.5), "0 < cover < 1: a cell cut by the edge,\nits conduction and its heat loss\nscale with the covered part"))):
        a2.add_patch(Rectangle((0.3, 6.0 - k * 2.0), 0.9, 0.9, facecolor=c, edgecolor="k"))
        a2.text(1.5, 6.45 - k * 2.0, t, va="center", fontsize=7.5)
    a2.text(4, 1.0, "the FVM, the FDM and the 3D solid use this cover;\nthe Lumped and Analytic models cannot (rings, cosine\nseries), so they run on the rectangle of the same area", ha="center", va="top", fontsize=7.5, style="italic")
    dk.save(fig, path, "A board outline on the grid of the finite volumes: the cell cover")


def draw_cells(ax, active, lengths, d, poly, title, lost=None, moves=None):
    """!
    @brief Draw a grid of cells (grey = off the board) with the outline length given to every cell, in mm.
    @param ax Axes.
    @param active Boolean array (ny, nx), True for the cells on the board.
    @param lengths Array (ny, nx) of outline length per cell (m).
    @param d Cell side (m).
    @param poly Outline (n, 2) in metres.
    @param title Panel title.
    @param lost Optional boolean array (ny, nx): cells whose edge is dropped (drawn in red).
    @param moves Optional list of ((i, j), (i2, j2)) cell pairs joined by an arrow (an edge moved to another cell).
    @return None.
    """
    ny, nx = active.shape
    mm = d * 1000.0
    for i in range(ny):
        for j in range(nx):
            face = "#9bbf8a" if active[i, j] else "#e5e7eb"
            if lost is not None and lost[i, j]:
                face = "#f4a6a6"
            ax.add_patch(Rectangle((j * mm, i * mm), mm, mm, facecolor=face, edgecolor="#9ca3af", linewidth=0.4))
            if lengths[i, j] > 1e-9:
                ax.text((j + 0.5) * mm, (i + 0.5) * mm, f"{lengths[i, j] * 1000:.1f}".rstrip("0").rstrip("."), ha="center", va="center", fontsize=5.5)
    for (i, j), (i2, j2) in (moves or []):
        ax.annotate("", ((j2 + 0.5) * mm, (i2 + 0.5) * mm), ((j + 0.5) * mm, (i + 0.5) * mm), arrowprops={"arrowstyle": "->", "color": "#b91c1c", "linewidth": 1.2})
    ax.add_patch(Polygon(np.asarray(poly) * 1000.0, fill=False, edgecolor="k", linewidth=1.6))
    ax.set_xlim(-1, nx * mm + 1)
    ax.set_ylim(-1, ny * mm + 1)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=8.5)


def edge_assignment(path):
    """!
    @brief The outline given to the cells before and after the edge fix, on real cells of the program: a T whose sides lie on grid lines (5 mm cells) and a square turned by 20 degrees (5 mm cells), whose slanted sides leave slivers of board in cells taken as off the board.
    @param path Output file.
    @return None.
    """
    import math
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pcbthermal import fvm, geometry
    import study_edge_on_grid_lines as st
    n, d = 12, 0.005
    fig, axs = dk.canvas(16, 5.6, 1, 3)
    # Panels 1 and 2: the T of the study (sides at 0, 20, 30, 40 and 60 mm, all on grid lines)
    p = st.t_board(st.T60, (27, 40, 33, 46))
    net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
    poly = np.array(p.board.outline)
    old = st.edge_before(poly, n, n, d, d, net.active)
    raw = geometry.edge_length_per_cell(poly, n, n, d, d)
    new = geometry.edge_length_on_board(poly, n, n, d, d, net.active)
    # Cells that the old rule gave an edge on the wrong side of a grid line: the sample falls in a cell off the board
    lost_t = (raw > 0) & ~net.active
    real = st.perimeter(poly) * 1000
    draw_cells(axs[0], net.active, old, d, poly, f"1. before: each sample goes to the cell that contains it\n{old.sum() * 1000:.0f} of {real:.0f} mm counted (a side on a grid line\nfalls in the cell off the board)")
    # In panel 1 the dropped lengths are drawn in red with their length (the old rule gave them to cells that the callers discarded)
    old_raw = np.zeros((n, n))
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        length = float(np.hypot(*(b - a)))
        k = max(int(np.ceil(length / (d / 10))), 1)
        t = (np.arange(k) + 0.5) / k
        j = np.clip(((a[0] + t * (b[0] - a[0])) // d).astype(int), 0, n - 1)
        i = np.clip(((a[1] + t * (b[1] - a[1])) // d).astype(int), 0, n - 1)
        np.add.at(old_raw, (i, j), length / k)
    dropped = (old_raw > 0) & ~net.active
    for i, j in zip(*np.nonzero(dropped)):
        axs[0].add_patch(Rectangle((j * d * 1000, i * d * 1000), d * 1000, d * 1000, facecolor="#f4a6a6", edgecolor="#9ca3af", linewidth=0.4))
        axs[0].text((j + 0.5) * d * 1000, (i + 0.5) * d * 1000, f"{old_raw[i, j] * 1000:.0f}", ha="center", va="center", fontsize=5.5, color="#7f1d1d")
    draw_cells(axs[1], net.active, new, d, poly, f"2. now: every sample is nudged inward by a thousandth of a cell\n{new.sum() * 1000:.0f} of {real:.0f} mm counted")
    # Panel 3: a turned square; the edge of cells taken as off the board goes to the nearest cell on the board
    th, c, h = math.radians(20.0), 30.0, 20.0
    sq = [[c + x * math.cos(th) - y * math.sin(th), c + x * math.sin(th) + y * math.cos(th)] for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]
    p2 = st.t_board(sq, (27, 27, 33, 33))
    net2 = fvm.Network(p2, n, n, assemble=False, with_blocks=False)
    poly2 = np.array(p2.board.outline)
    raw2 = geometry.edge_length_per_cell(poly2, n, n, d, d)
    new2 = geometry.edge_length_on_board(poly2, n, n, d, d, net2.active)
    old2 = st.edge_before(poly2, n, n, d, d, net2.active)
    lost = (raw2 > 0) & ~net2.active
    gained = new2 - raw2 * net2.active
    moves = []
    for i, j in zip(*np.nonzero(lost)):
        cand = np.argwhere(gained > 1e-12)
        dist = np.hypot(cand[:, 0] - i, cand[:, 1] - j)
        for k in np.nonzero(dist <= dist.min() + 1e-9)[0]:
            moves.append(((i, j), tuple(cand[k])))
    real2 = st.perimeter(poly2) * 1000
    draw_cells(axs[2], net2.active, new2, d, poly2, f"3. a turned square (20 deg): slivers of board in cells taken as off\nthe board (red) give their edge to the nearest board cell\nnow {new2.sum() * 1000:.0f} of {real2:.0f} mm; old rule {old2.sum() * 1000:.1f} mm", lost=lost, moves=moves)
    dk.save(fig, path, "The outline given to the cells before and after the edge fix (lengths in mm per cell, 5 mm cells for legibility)")
    print(f"T: old {old.sum() * 1000:.1f}, now {new.sum() * 1000:.1f}, real {real:.1f} mm; square: old {old2.sum() * 1000:.1f}, now {new2.sum() * 1000:.1f}, real {real2:.1f} mm; lost cells {int(lost.sum())}, dropped by the old rule in the T {int(dropped.sum())} cells")


def main():
    """!
    @brief Draw the three panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(16, 5.2, 1, 3)
    draw_board(axs[0], "1. a board with an outline (a T), two heaters")
    ax = axs[1]
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 7)
    ax.set_aspect("equal")
    f = np.sqrt(area(T_OUTLINE) / 60.0)                                     # the bounding box is 10 x 6 = 60
    w, h = 10 * f, 6 * f
    ax.add_patch(Rectangle((0, 0), 10, 6, fill=False, edgecolor="r", linestyle="--"))
    ax.add_patch(Rectangle((0, 0), w, h, facecolor=dk.FR4, edgecolor="k", linewidth=1.5))
    ax.add_patch(Rectangle((1.0 * f, 4.6 * f), 1.2, 1.0, facecolor="#444444"))
    ax.add_patch(Rectangle((4.4 * f, 0.8 * f), 1.2, 1.0, facecolor="#444444"))
    ax.text(w / 2, h / 2, f"rectangle of the same area\nsides scaled by sqrt(A / A_box) = {f:.2f}", ha="center", fontsize=8)
    ax.set_title("2. what the Lumped and Analytic models run on:\nbox and positions scaled, the parts keep their size", fontsize=9)
    ax = axs[2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.3, 5.7, 9.4, 1.6, "1. scale the box and the positions of the parts by sqrt(area ratio)", "#cfe3f5")
    dk.box(ax, 0.3, 3.6, 9.4, 1.6, "2. run the model on that rectangle; the parts keep their size", "#cfe3f5")
    dk.box(ax, 0.3, 1.5, 9.4, 1.6, "3. stretch the field back to the board; warn about the cooler edge", "#cfe3f5")
    dk.arrow(ax, 5, 5.7, 5, 5.2)
    dk.arrow(ax, 5, 3.6, 5, 3.1)
    ax.text(5, 0.5, "same-area rectangle: within 0.4 to 2.9 % away from the edge;\nnear the edge or in a T arm up to 18 % cool (documented, warned);\nthe bounding box alone is 6 to 10 % cool on an ellipse", ha="center", fontsize=7.5, style="italic")
    ax.set_title("3. the rule, and how well it works", fontsize=9)
    dk.save(fig, OUT / "fig_04_outline_to_rectangle_schematic.png", "Lumped and Analytic on a board with an outline: the equivalent rectangle")
    cell_cover(OUT / "fig_05_cells_on_an_outline.png")
    edge_assignment(OUT / "fig_07_edge_assignment.png")


if __name__ == "__main__":
    main()
