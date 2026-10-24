"""!
@file study_edge_on_grid_lines.py
@brief Does the FVM (and the 3D solid) count the whole edge of a board with an outline when a side of the outline lies on a grid line?

@details `geometry.edge_length_per_cell` gives every sample of the outline to the cell that contains it, and a point on a cell border goes to the
         cell above or to the right (or, after floating-point rounding, to either side). The FVM and the 3D solid then multiply by `active`, so a
         side that lies on a grid line with the board below it or to its left is given to a cell off the board and its edge loss is dropped. The
         FDM shifts the outline by half a cell (its nodes sit on the grid lines) and is not affected. The script prints the perimeter counted by the
         FVM against the real one, the board time constant against the closed form C/G, the mirror-image test (a T and the same T upside down
         must give the same answer), and the effect on the boards of `outline_rectangle_study.py`, by running the FVM on a copy of the rule that
         nudges every sample a micrometre towards the inside of the board.

Usage: .venv/bin/python research/outline/scripts/study_edge_on_grid_lines.py (from the repository root; about a minute)
"""

import os
import sys
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

from pcbthermal import Problem, SolverOptions, fvm, geometry, simulate, solid3d   # noqa: E402
import outline_rectangle_study as st                                             # noqa: E402

T60 = [[0, 30], [20, 30], [20, 0], [40, 0], [40, 30], [60, 30], [60, 60], [0, 60]]   # A T on a 60 mm box, sides on the 1 and 2 mm grid lines


def edge_inward(poly, nx, ny, dx, dy):
    """!
    @brief Copy of `geometry.edge_length_per_cell` whose samples are nudged towards the inside of the polygon before they are given to a cell.
    @param poly Closed polygon (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Array (ny, nx) of lengths in metres.
    """
    p = np.asarray(poly, dtype=float)
    # Orientation: positive signed area = counter-clockwise, the inside is on the left of every side
    x0, y0 = p[:, 0], p[:, 1]
    sign = 1.0 if np.sum(x0 * np.roll(y0, -1) - np.roll(x0, -1) * y0) > 0 else -1.0
    nudge = 1e-3 * min(dx, dy)                                    # Far above rounding, far below a cell
    out = np.zeros((ny, nx))
    step = min(dx, dy) / 10.0
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        e = b - a
        length = float(np.hypot(*e))
        if length <= 0:
            continue
        inward = sign * np.array([-e[1], e[0]]) / length
        n = max(int(np.ceil(length / step)), 1)
        t = (np.arange(n) + 0.5) / n
        x = a[0] + t * e[0] + nudge * inward[0]
        y = a[1] + t * e[1] + nudge * inward[1]
        j = np.clip((x // dx).astype(int), 0, nx - 1)
        i = np.clip((y // dy).astype(int), 0, ny - 1)
        np.add.at(out, (i, j), length / n)
    return out


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
    o = b.outline
    area = geometry.polygon_area(o)
    perim = float(np.sum(np.hypot(*(np.roll(o, -1, axis=0) - o).T)))
    t_cu = float(np.sum(b.copper_thickness))
    c_area = m.rho_copper * m.cp_copper * t_cu + (b.thickness - t_cu) * float(np.mean(b.layer_laminate()[1]))
    return c_area * area / ((b.h_top + b.h_bottom) * area + b.h_side * b.thickness * perim)


def main():
    """!
    @brief Print the perimeter, time-constant and mirror tables and the effect on the outline study.
    @return None.
    """
    upright = t_board(T60, (27, 40, 33, 46))
    mirrored = t_board([[x, 60 - y] for x, y in T60], (27, 14, 33, 20))
    print("| board | cell (mm) | real perimeter (mm) | counted by the FVM (mm) | tau closed form (s) | tau FVM (s) | tau FVM, inward rule (s) |")
    print("| :-- | --: | --: | --: | --: | --: | --: |")
    for name, p in (("T, 60 mm", upright), ("T upside down", mirrored)):
        for c in (2.0, 1.0):
            n = int(round(60.0 / c))
            net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
            counted = (geometry.edge_length_per_cell(p.board.outline, n, n, c / 1000, c / 1000) * net.active).sum()
            with mock.patch.object(fvm, "edge_length_per_cell", edge_inward):
                fixed = fvm.board_time_constant(fvm.Network(p, n, n, assemble=False, with_blocks=False))
            o = p.board.outline
            perim = float(np.sum(np.hypot(*(np.roll(o, -1, axis=0) - o).T)))
            print(f"| {name} | {c:g} | {perim * 1000:.1f} | {counted * 1000:.1f} | {closed_tau(p):.2f} | {fvm.board_time_constant(net):.2f} | {fixed:.2f} |")

    print("\n| board | FVM Tmax (C) | FVM, inward rule | FDM | 3D solid | 3D solid, inward rule |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, p in (("T, 60 mm", upright), ("T upside down", mirrored)):
        o = SolverOptions(models=("fvm", "fdm", "solid3d"), cell_mm=1.0)
        r = simulate(p, o).results
        with mock.patch.object(fvm, "edge_length_per_cell", edge_inward), mock.patch.object(solid3d, "edge_length_per_cell", edge_inward):
            rf = simulate(p, o).results
        print(f"| {name} | {r['fvm'].t_max:.3f} | {rf['fvm'].t_max:.3f} | {r['fdm'].t_max:.3f} | {r['solid3d'].t_max:.3f} | {rf['solid3d'].t_max:.3f} |")

    print("\n| outline study row | FVM Tmax (C) | FVM, inward rule | same-area L / A, error against the FVM | against the FVM with the inward rule |")
    print("| :-- | --: | --: | --: | --: |")
    opt = lambda m: SolverOptions(models=(m,), cell_mm=1.0)                    # noqa: E731
    for name, lay in (("L", "near the edge"), ("T", "example"), ("T", "centre")):
        real = st.with_parts(st.LAYOUTS[lay])
        real.board.outline = np.array(st.outlines(100.0, 80.0)[name]) / 1000.0
        ref = simulate(real, opt("fvm")).results["fvm"]
        with mock.patch.object(fvm, "edge_length_per_cell", edge_inward):
            ref2 = simulate(real, opt("fvm")).results["fvm"]
        cols = []
        for r0 in (ref, ref2):
            e = [(simulate(real, opt(m)).results[m].t_max - r0.t_max) / r0.delta_t * 100.0 for m in ("lumped", "analytic")]
            cols.append(f"{e[0]:+.1f} / {e[1]:+.1f}")
        print(f"| {name}, {lay} | {ref.t_max:.2f} | {ref2.t_max:.2f} | {cols[0]} | {cols[1]} |", flush=True)


if __name__ == "__main__":
    main()
