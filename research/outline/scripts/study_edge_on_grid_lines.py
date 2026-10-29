"""!
@file study_edge_on_grid_lines.py
@brief Does the program count the whole edge of a board with an outline, also when a side of the outline lies on a grid line or leaves a thin slice of board in a cell?

@details Two defects of the edge loss were found by the review of this folder and are corrected in the program (`geometry.edge_length_per_cell`
         nudges every sample inward; `geometry.edge_length_on_board` moves the edge of cells taken as off the board to the nearest cell on the board):
         (1) a side that lies on a grid line with the board on the other side of it was given to a cell off the board and its edge loss was
         dropped (a T of 60 mm kept 170 of 240 mm); (2) a slanted or curved side left slivers of board in cells taken as off the board, and 2 to 6 %
         of the perimeter of a disc, an ellipse or a turned square was lost at every cell size. The script runs on the current program and prints:
         the perimeter counted by the FVM (from its `g_side` array) and by the 3D solid (from the sum of its side conductances, against the same
         outline mirrored) against the shoelace perimeter; the board time constant against the closed form C/G; the T against its mirror image; and
         the study rows of `outline_rectangle_study.py` that depend on the edge. The behaviour before the correction is reproduced by `edge_before`,
         a local copy of the old assignment (samples given to the cell that contains them, no nudge, no relocation, multiplied by the active
         mask); the program is not patched. The temperatures of the old program are not recomputed (that would need the old code).

Usage: .venv/bin/python research/outline/scripts/study_edge_on_grid_lines.py (from the repository root; about a minute)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

from pcbthermal import Problem, SolverOptions, fvm, geometry, simulate, solid3d   # noqa: E402
import outline_rectangle_study as st                                             # noqa: E402

T60 = [[0, 30], [20, 30], [20, 0], [40, 0], [40, 30], [60, 30], [60, 60], [0, 60]]   # A T on a 60 mm box, sides on the 1 and 2 mm grid lines


def edge_before(poly, nx, ny, dx, dy, active):
    """!
    @brief The old assignment of the outline to the cells (before the correction): every sample goes to the cell that contains it, no nudge,
           and the cells off the board lose their share.
    @param poly Closed polygon (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param active Boolean array (ny, nx), True for the cells on the board.
    @return Array (ny, nx) of lengths in metres, zero off the board.
    """
    p = np.asarray(poly, dtype=float)
    out = np.zeros((ny, nx))
    step = min(dx, dy) / 10.0
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        length = float(np.hypot(*(b - a)))
        if length <= 0:
            continue
        n = max(int(np.ceil(length / step)), 1)
        t = (np.arange(n) + 0.5) / n                                  # Midpoints of the n pieces
        j = np.clip(((a[0] + t * (b[0] - a[0])) // dx).astype(int), 0, nx - 1)
        i = np.clip(((a[1] + t * (b[1] - a[1])) // dy).astype(int), 0, ny - 1)
        np.add.at(out, (i, j), length / n)
    return out * np.asarray(active, dtype=bool)                       # The callers kept only the cells on the board


def perimeter(poly):
    """!
    @brief Perimeter of a closed polygon (shoelace sides).
    @param poly Closed polygon (n, 2), any unit.
    @return Perimeter in the unit of the polygon.
    """
    o = np.asarray(poly, dtype=float)
    return float(np.sum(np.hypot(*(np.roll(o, -1, axis=0) - o).T)))


def t_board(outline, heater):
    """!
    @brief A 60 x 60 mm two-layer board with full copper, cut to an outline, with a 6 mm part of 2 W.
    @param outline Outline in mm.
    @param heater Rectangle (x0, y0, x1, y1) of the part in mm.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, 2).add_full_copper()
    p.add_heater(1, 2.0, rect=heater, name="U")
    p.set_outline(outline)
    return p


def closed_tau(p):
    """!
    @brief Closed-form C/G of a full-copper board with an outline: face films over the area, edge film over the perimeter.
    @param p Problem.
    @return Time constant in seconds.
    """
    b = p.board
    m = b.materials
    area = geometry.polygon_area(b.outline)
    t_cu = float(np.sum(b.copper_thickness))
    c_area = m.rho_copper * m.cp_copper * t_cu + (b.thickness - t_cu) * float(np.mean(b.layer_laminate()[1]))
    return c_area * area / ((b.h_top + b.h_bottom) * area + b.h_side * b.thickness * perimeter(b.outline))


def counted_by_fvm(net, p):
    """!
    @brief Perimeter that the FVM network actually exposes to the edge film, read back from its side conductances.
    @param net fvm.Network of the problem.
    @param p Problem (for the edge coefficient and the board thickness).
    @return Perimeter in metres (sum of g_side over the cells divided by h_side times the board thickness).
    """
    return float(net.g_side.sum() / (p.board.h_side * p.board.thickness))


def main():
    """!
    @brief Print the perimeter, time-constant, mirror and study-row tables on the current program.
    @return None.
    """
    upright = t_board(T60, (27, 40, 33, 46))
    mirrored = t_board([[x, 60 - y] for x, y in T60], (27, 14, 33, 20))
    print("| board | cell (mm) | real perimeter (mm) | counted by the FVM now (mm) | counted by the old rule (mm) | tau closed form (s) | tau FVM now (s) | tau with the old rule (s) |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
    for name, p in (("T, 60 mm", upright), ("T upside down", mirrored)):
        for c in (2.0, 1.0):
            n = int(round(60.0 / c))
            net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
            real = perimeter(p.board.outline)
            now = counted_by_fvm(net, p)
            old = float(edge_before(p.board.outline, n, n, c / 1000, c / 1000, net.active).sum())
            # tau of the old program: the same capacity over the same conductance with the old edge length instead of the one now
            g_old = fvm.board_time_constant(net) ** -1 * net.C.sum() - net.g_side.sum() + p.board.h_side * p.board.thickness * old
            print(f"| {name} | {c:g} | {real * 1000:.1f} | {now * 1000:.1f} | {old * 1000:.1f} | {closed_tau(p):.2f} | {fvm.board_time_constant(net):.2f} | {net.C.sum() / g_old:.2f} |")

    print("\n| shape (cells of 1 mm unless said) | real perimeter (mm) | counted by the FVM now (mm) | counted by the old rule (mm) | slice lost before (%) |")
    print("| :-- | --: | --: | --: | --: |")
    shapes = {"disc 59.8 mm (128-gon), 2 mm": (st_disc(), 2.0), "disc 59.8 mm (128-gon), 1 mm": (st_disc(), 1.0),
              "ellipse 60 x 40 mm, 1 mm": (st_ellipse(), 1.0), "square 40 mm turned 20 deg, 1 mm": (st_turned(), 1.0)}
    for name, (poly, c) in shapes.items():
        p = Problem.new(60.0, 60.0, 2).add_full_copper()
        p.set_outline(poly)
        n = int(round(60.0 / c))
        net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
        real = perimeter(p.board.outline)
        now = counted_by_fvm(net, p)
        old = float(edge_before(p.board.outline, n, n, c / 1000, c / 1000, net.active).sum())
        print(f"| {name} | {real * 1000:.1f} | {now * 1000:.1f} | {old * 1000:.1f} | {100 * (1 - old / real):.1f} |")

    print("\n| board, 1 mm | FVM Tmax (C) | FDM | 3D solid | 3D solid, sum of the side conductances (W/K) |")
    print("| :-- | --: | --: | --: | --: |")
    for name, p in (("T, 60 mm", upright), ("T upside down", mirrored)):
        r = simulate(p, SolverOptions(models=("fvm", "fdm", "solid3d"), cell_mm=1.0)).results
        sol = solid3d.Solid(p, 1.0)
        print(f"| {name} | {r['fvm'].t_max:.3f} | {r['fdm'].t_max:.3f} | {r['solid3d'].t_max:.3f} | {sol.g['sides'].sum():.6f} |")

    print("\n| outline study row | FVM Tmax (C) | same-area L / A, error against the FVM |")
    print("| :-- | --: | --: |")
    opt = lambda m: SolverOptions(models=(m,), cell_mm=1.0)                    # noqa: E731
    for name, lay in (("L", "near the edge"), ("T", "example"), ("T", "centre")):
        real = st.with_parts(st.LAYOUTS[lay])
        real.board.outline = np.array(st.outlines(100.0, 80.0)[name]) / 1000.0
        ref = simulate(real, opt("fvm")).results["fvm"]
        e = [(simulate(real, opt(m)).results[m].t_max - ref.t_max) / ref.delta_t * 100.0 for m in ("lumped", "analytic")]
        print(f"| {name}, {lay} | {ref.t_max:.2f} | {e[0]:+.1f} / {e[1]:+.1f} |", flush=True)


def st_disc():
    """!
    @brief A 128-gon of 59.8 mm across centred on the 60 mm box.
    @return Polygon (n, 2) in mm.
    """
    a = np.linspace(0, 2 * np.pi, 128, endpoint=False)
    return np.c_[30 + 29.9 * np.cos(a), 30 + 29.9 * np.sin(a)]


def st_ellipse():
    """!
    @brief A 128-gon ellipse of 60 x 40 mm centred on the 60 mm box.
    @return Polygon (n, 2) in mm.
    """
    a = np.linspace(0, 2 * np.pi, 128, endpoint=False)
    return np.c_[30 + 29.9 * np.cos(a), 30 + 19.9 * np.sin(a)]


def st_turned():
    """!
    @brief A 40 mm square turned by 20 degrees about the centre of the 60 mm box.
    @return Polygon (n, 2) in mm.
    """
    c, s = np.cos(np.radians(20)), np.sin(np.radians(20))
    q = np.array([[-20, -20], [20, -20], [20, 20], [-20, 20]], dtype=float)
    return np.c_[30 + q[:, 0] * c - q[:, 1] * s, 30 + q[:, 0] * s + q[:, 1] * c]


if __name__ == "__main__":
    main()
