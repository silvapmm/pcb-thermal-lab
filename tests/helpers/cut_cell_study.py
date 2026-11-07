#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cut_cell_study.py
@brief The numbers of docs/validation.md 31 (cut-cell links and the edge film of the layered FVM) and the comparisons that tests/test_cut_cell_links.py reuses.
@details Question: how far does the hottest temperature of the layered FVM depend on where the board outline falls on the grid, and how far is it from the same continuum problem
         written without a cut cell? The reference is independent of the program: the board in its own frame (an aligned rectangle with the part turned and shifted by the inverse
         transformation) solved by `two_sheet.py` (its own assembly, the edge film in series with half a cell, three fine cells and an extrapolation). The error of a position is the
         FVM peak of the board with the outline turned and shifted (the part and the vias stay on the grid) minus that reference; the spread is the range of the error over the
         positions. Subcommands (each prints Markdown tables):
         - `sliver`  the board whose left edge column has the cover c (0.01 .. 1) at h_side 10, 200, 2000 W/m2K, 1 mm: peak, jump from c = 0.01 to 0.02, error against the reference;
         - `frame`   the spreads over 17 positions (turns of 0 to 45 degrees and diagonal shifts of 1/8 to 7/8 cell) of the square with the part 3.5 mm off centre (1 mm) and of the
                     strip (0.5 mm), at h_side 10, 50, 200, 2000;
         - `recess`  the film floor: copper held back from the outline, h_side 200 to 5000: how many nodes sit at the floor and how far the peak depends on the floor value.
         Run from the repository root: `.venv/bin/python tests/helpers/cut_cell_study.py [sliver|frame|recess|all]` (sliver 1 min, frame 6 min, recess 2 min, below 1.5 GB). The
         environment variable PCBT_TREE names another checkout of the program (for the numbers "before": a tree without the change); the references are the same for both.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("PCBT_TREE"):
    sys.path.insert(0, os.environ["PCBT_TREE"])
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cut_cell_boards as bd          # noqa: E402
import two_sheet as ind               # noqa: E402
from pcbthermal import Problem, fvm   # noqa: E402

AMB = 25.0
FINE = (0.25e-3, 0.125e-3, 0.0625e-3)


def reference(kw):
    """!
    @brief Continuum peak of a board of `edge_board` (options `kw`) from its frame problem and the independent two-sheet solver.
    @param kw Options of `cut_cell_boards.frame_board` (angle, sx, sy, h_side, shape, off, pc, box).
    @return Peak temperature in degC (three cells of 1/4, 1/8, 1/16 mm extrapolated).
    """
    fb = bd.frame_board(**kw)
    poly = np.array(fb.heaters[0].polygon)
    return ind.richardson(lambda h: ind.solve(fb.board.width, fb.board.height, h, kw["h_side"], poly, poly=True)[0] + AMB, FINE)[0]


def positions(cell):
    """!
    @brief The 17 positions of the study: turns of 0 to 45 degrees in steps of 5 and diagonal shifts of 1/8 to 7/8 of a cell.
    @param cell Cell in mm.
    @return list of (label, options of edge_board).
    """
    pos = [(f"turn {a}", dict(angle=float(a))) for a in range(0, 50, 5)]
    pos += [(f"shift {k}/8", dict(sx=k / 8 * cell, sy=k / 8 * cell)) for k in range(1, 8)]
    return pos


def errors(shape, off, h_side, cell, pos, refs=None):
    """!
    @brief Error of the FVM peak against the frame reference at each position.
    @param shape "square" or "strip".
    @param off Offset of the part from the centre along x in mm.
    @param h_side Edge coefficient in W/m2K.
    @param cell Cell in mm.
    @param pos List of (label, options of edge_board).
    @param refs Optional dict label -> reference (degC) to avoid recomputing it.
    @return dict label -> error in K.
    """
    out = {}
    for label, pk in pos:
        kw = dict(h_side=h_side, shape=shape, off=off, pc=cell / 2, box=32.0, **pk)
        ref = refs[label] if refs and label in refs else reference(kw)
        if refs is not None:
            refs[label] = ref
        out[label] = fvm.solve_steady(bd.edge_board(**kw), cell_mm=cell).t_max - ref
    return out


def sliver_board(c, h_side):
    """!
    @brief The board whose left edge column [5, 6] mm is covered by the fraction c (two layers, 2 W part 2 mm from the edge).
    @param c Cover of the edge column.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    e = 6.0 - c
    p = Problem.new(30, 30, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0, 13.5, 11.0, 16.5), name="U")
    p.set_outline([[e, 5], [25, 5], [25, 25], [e, 25]])
    return p


def sliver_reference(c, h_side):
    """!
    @brief Continuum peak of `sliver_board` from the aligned rectangle in the independent solver.
    @param c Cover of the edge column.
    @param h_side Edge coefficient in W/m2K.
    @return Peak in degC.
    """
    e = 6.0 - c
    W, H = (25 - e) * 1e-3, 20e-3
    src = ((8 - e) * 1e-3, 8.5e-3, (11 - e) * 1e-3, 11.5e-3)
    return ind.richardson(lambda h: ind.solve(W, H, h, h_side, src)[0] + AMB, FINE)[0]


def study_sliver():
    """!
    @brief Table of the sliver curve: peak, jump from c = 0.01 to 0.02 and the error against the independent reference.
    @return None (prints).
    """
    print("| h_side | c | peak (degC) | reference (degC) | error (K) |\n| --: | --: | --: | --: | --: |")
    for hs in (10.0, 200.0, 2000.0):
        first = None
        for c in (0.01, 0.02, 0.05, 0.1, 1.0):
            t = fvm.solve_steady(sliver_board(c, hs), cell_mm=1.0).t_max
            ref = sliver_reference(c, hs)
            first = t if first is None else first
            print(f"| {hs:g} | {c:g} | {t:.3f} | {ref:.3f} | {t - ref:+.3f} |", flush=True)
            if c == 0.02:
                print(f"| {hs:g} | jump 0.01 to 0.02 | {t - first:+.3f} | | |", flush=True)


def study_frame():
    """!
    @brief Spreads over the positions of the outline against the frame reference.
    @return None (prints).
    """
    print("| case | cell | h_side | bias (K) | spread (K) | worst (K) |\n| :-- | --: | --: | --: | --: | --: |")
    for (shape, off, cell), hss in ((("square", 3.5, 1.0), (10.0, 50.0, 200.0, 2000.0)), (("strip", 0.0, 0.5), (10.0, 200.0, 2000.0))):
        for hs in hss:
            e = np.array(list(errors(shape, off, hs, cell, positions(cell)).values()))
            print(f"| {shape} off {off:g} | {cell:g} | {hs:g} | {e.mean():+.2f} | {np.ptp(e):.2f} | {np.abs(e).max():.2f} |", flush=True)


def recessed_board(h_side, angle=20.0):
    """!
    @brief The turned 20 mm square whose top copper stops 1.2 mm inside the outline (bare-laminate nodes in the cut cells).
    @param h_side Edge coefficient in W/m2K.
    @param angle Turn of the board in degrees.
    @return Problem.
    """
    return bd.edge_board(angle=angle, h_side=h_side, pattern=True, pc=0.5, box=32.0)


def study_recess():
    """!
    @brief The film floor with the copper held off the edge: nodes at the floor and the dependence of the peak on the floor value.
    @return None (prints).
    """
    print("| h_side | nodes at the floor | peak, floor 0.25 | floor 0.5 | floor 0.1 | floor 0.05 |\n| --: | --: | --: | --: | --: | --: |")
    keep = fvm.EDGE_FILM_FLOOR
    try:
        for hs in (200.0, 1000.0, 2000.0, 5000.0):
            p = recessed_board(hs)
            row = []
            for fl in (0.25, 0.5, 0.1, 0.05):
                fvm.EDGE_FILM_FLOOR = fl
                row.append(fvm.solve_steady(recessed_board(hs), cell_mm=1.0).t_max)
            fvm.EDGE_FILM_FLOOR = keep
            n_at = count_at_floor(p, 1.0)                      # (with the default floor, set back above)
            print(f"| {hs:g} | {n_at} | " + " | ".join(f"{v:.3f}" for v in row) + " |", flush=True)
    finally:
        fvm.EDGE_FILM_FLOOR = keep


def count_at_floor(problem, cell_mm):
    """!
    @brief Number of node cells whose film denominator 1 + H d / S is at or below the floor.
    @param problem Problem with an outline.
    @param cell_mm Cell in mm.
    @return int.
    """
    b = problem.board
    nx, ny = int(round(b.width * 1000 / cell_mm)), int(round(b.height * 1000 / cell_mm))
    net = fvm.Network(problem, nx, ny, assemble=False, cut_cells=False)        # (the edge conductance before the series term)
    L = net._edge_lengths()
    from pcbthermal.geometry import signed_distance_to_outline
    cells = np.argwhere(L > 0)
    d = np.zeros((ny, nx))
    d[cells[:, 0], cells[:, 1]] = signed_distance_to_outline(b.outline, (cells[:, 1] + 0.5) * net.dx, (cells[:, 0] + 0.5) * net.dy)
    sp_ = net._physical_sheet()
    H = np.zeros_like(net.g_side)
    np.divide(net.g_side, L[None], out=H, where=L[None] > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        fac = np.where((sp_ > 0) & (H > 0), 1.0 + H * d[None] / sp_, 1.0)
    return int((fac <= fvm.EDGE_FILM_FLOOR * (1 + 1e-12)).sum())


def main():
    """!
    @brief Run the subcommand named on the command line.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("sliver", study_sliver), ("frame", study_frame), ("recess", study_recess)):
        if which in (name, "all"):
            print(f"\n## {name}\n")
            fn()


if __name__ == "__main__":
    main()
