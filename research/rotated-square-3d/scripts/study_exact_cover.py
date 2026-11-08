#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_exact_cover.py
@brief What does the exact board cover (`fix/exact-board-cover`, `geometry.exact_coverage`) change against the 8 x 8 sampled cover it replaced?
@details Four measurements on one tree, the sampled rule being put back by a context manager (`sampled_rule`, a copy of the code of 2.5.1):
         (1) the area of the cover of a 20 mm square turned 0 to 45 degrees at 1 and 0.5 mm, against the polygon area;
         (2) the turn spread of the hottest temperature of that square (3 mm, 2 W part, h_side 10) against the frame reference of
             `study_turn_frame_reference.py` (the board solved in its own frame, no cut cell: 1/8 and 1/16 mm and a second-order Richardson step);
         (3) the edge-shift scatter of the small T (neck edge moved over one cell in twelfths) in the FVM and FDM at 1 and 0.5 mm, against the same board at
             1/12 mm (the edge is on grid lines there);
         (4) the heat balance of the turned square and the invariance of the total power of the part.
         Usage: .venv/bin/python research/rotated-square-3d/scripts/study_exact_cover.py [area|turn|tee|balance|all]   (from the repository root;
         about 3 minutes and 1 GB; the frame references are cached in research/rotated-square-3d/out/exact_cover_frame.json).
"""

import contextlib
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import Problem, fdm, fvm, geometry, model, solid3d      # noqa: E402
from pcbthermal.geometry import coverage_fraction, polygon_area           # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def _old_part_weights(poly, outline, nx, ny, dx, dy, samples=8, cover=None):
    """!
    @brief The part weights of 2.5.1 (sampled 8 x 8 on the part and the outline, scaled to the model's cover).
    @param poly Part polygon vertices (n, 2) in metres.
    @param outline Board outline vertices in metres, or None.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @param cover Board cover used by the model, or None.
    @return Array (ny, nx).
    """
    if outline is None:
        return coverage_fraction(poly, nx, ny, dx, dy, samples)
    out = np.zeros((ny, nx))
    got = geometry._sample_mask(poly, nx, ny, dx, dy, samples, clip=outline)
    if got is None:
        return out
    i0, i1, j0, j1, part, board = got
    both = (part & board).sum(axis=(1, 3)).astype(float)
    if cover is None:
        out[i0:i1, j0:j1] = both / (samples * samples)
        return out
    n_board = board.sum(axis=(1, 3))
    share = np.divide(both, n_board, out=np.zeros_like(both), where=n_board > 0)
    out[i0:i1, j0:j1] = share * np.asarray(cover, dtype=float)[i0:i1, j0:j1]
    return out


def _old_cover(self, nx, ny, dx, dy, minimum=0.01):
    """!
    @brief Board.cover of 2.5.1 (8 x 8 samples).
    @param self The Board.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param minimum Smallest coverage kept.
    @return Array (ny, nx).
    """
    if self.outline is None:
        return np.ones((ny, nx))
    c = coverage_fraction(self.outline, nx, ny, dx, dy, 8)
    return np.where(c >= minimum, c, 0.0)


def _old_exact_coverage(poly, nx, ny, dx, dy):
    """!
    @brief The 8 x 8 coverage in place of the exact one (FDM node cover and the read-out mask of 2.5.1).
    @param poly Polygon vertices in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Array (ny, nx).
    """
    return coverage_fraction(poly, nx, ny, dx, dy, 8)


@contextlib.contextmanager
def sampled_rule(on):
    """!
    @brief Put the sampled 8 x 8 rule of 2.5.1 back for the duration of a block (or leave the exact one).
    @param on True for the sampled rule, False for the program as it is.
    @return Context manager.
    """
    if not on:
        yield
        return
    saved = [(model.Board, "cover", model.Board.cover)]
    for mod in (fvm, fdm, solid3d):
        saved.append((mod, "part_weights", mod.part_weights))
    saved.append((fdm, "exact_coverage", fdm.exact_coverage))
    model.Board.cover = _old_cover
    for mod in (fvm, fdm, solid3d):
        mod.part_weights = _old_part_weights
    fdm.exact_coverage = _old_exact_coverage
    try:
        yield
    finally:
        for obj, name, val in saved:
            setattr(obj, name, val)


def turned_square(angle, h_side=10.0, pc=0.5, side=20.0):
    """!
    @brief A square board turned about the centre of a 30 mm box, 2 layers of copper, a 3 mm 2 W part on the axes of the grid.
    @param angle Turn of the board in degrees.
    @param h_side Edge coefficient in W/m2K.
    @param pc Shift of the part from the box centre on both axes in mm.
    @param side Side of the square in mm.
    @return Problem.
    """
    a, h = math.radians(angle), side / 2.0
    pts = [[15.0 + x * math.cos(a) - y * math.sin(a), 15.0 + x * math.sin(a) + y * math.cos(a)] for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]
    p = Problem.new(30.0, 30.0, 2, h_side=h_side).add_full_copper()
    p.set_outline(pts)
    p.add_heater(1, 2.0, rect=(15 + pc - 1.5, 15 + pc - 1.5, 15 + pc + 1.5, 15 + pc + 1.5), name="U")
    return p


def frame_board(angle, h_side=10.0, pc=0.5):
    """!
    @brief The same board in its own frame: the 20 mm square aligned with the grid and the part turned by the opposite angle (no cut cell by the outline).
    @param angle Turn of the board in degrees.
    @param h_side Edge coefficient in W/m2K.
    @param pc Shift of the part from the box centre on both axes in mm.
    @return Problem.
    """
    a = math.radians(-angle)
    cx = 10.0 + pc * math.cos(a) - pc * math.sin(a)
    cy = 10.0 + pc * math.sin(a) + pc * math.cos(a)
    pts = [[cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)] for x, y in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5))]
    p = Problem.new(20.0, 20.0, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, polygon=pts, name="U")
    return p


def small_t(a_mm, h_side=10.0):
    """!
    @brief The small T board (30 x 24 mm, 2 W part over the re-entrant corner) with the neck edges at x = a and 30 - a.
    @param a_mm Position of the left neck edge in mm.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    b = 30.0 - a_mm
    p = Problem.new(30.0, 24.0, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(9, 10, 12, 14), name="U")
    p.set_outline([[0, 12], [a_mm, 12], [a_mm, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    return p


def study_area():
    """!
    @brief Area of the cover of the turned 20 mm square, sampled and exact, against the polygon.
    @return None.
    """
    print("\n### area of the board cover of the 20 mm square (relative error against the polygon area; minimum=0, i.e. before the 0.01 cut-off of Board.cover)\n")
    print("| angle (deg) | cell (mm) | sampled 8 x 8 | exact |\n| --: | --: | --: | --: |")
    for angle in (0, 5, 10, 18.435, 30, 45):
        b = turned_square(angle).board
        exact_area = polygon_area(b.outline)
        for cell in (1.0, 0.5):
            n = int(round(30.0 / cell))
            d = 0.03 / n
            row = []
            for sampled in (True, False):
                with sampled_rule(sampled):
                    row.append(b.cover(n, n, d, d, minimum=0.0).sum() * d * d / exact_area - 1.0)
            print(f"| {angle:g} | {cell:g} | {row[0]:+.2e} | {row[1]:+.2e} |")


def frame_reference(angle, h_side=10.0, pc=0.5):
    """!
    @brief Hottest temperature of the frame board at 1/8 and 1/16 mm and the second-order Richardson value.
    @param angle Turn in degrees.
    @param h_side Edge coefficient in W/m2K.
    @param pc Shift of the part in mm.
    @return float Reference temperature in degC.
    """
    t8 = fvm.solve_steady(frame_board(angle, h_side, pc), cell_mm=0.125).t_max
    t16 = fvm.solve_steady(frame_board(angle, h_side, pc), cell_mm=0.0625).t_max
    return t16 + (t16 - t8) / 3.0


def study_turn():
    """!
    @brief Turn spread of the hottest temperature of the turned square, sampled and exact, against the frame reference.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    cache = os.path.join(OUT, "exact_cover_frame.json")
    refs = json.load(open(cache)) if os.path.exists(cache) else {}
    angles = list(range(0, 50, 5))
    for ang in angles:
        if str(ang) not in refs:
            refs[str(ang)] = frame_reference(ang)
            json.dump(refs, open(cache, "w"))
    print("\n### turn spread: hottest temperature of the turned 20 mm square against the frame reference (K), FVM, h_side 10\n")
    print("| cell (mm) | rule | " + " | ".join(f"{a}" for a in angles) + " | spread |\n| --: | :-- | " + " | ".join("--:" for _ in angles) + " | --: |")
    for cell in (1.0, 0.5):
        for sampled in (True, False):
            with sampled_rule(sampled):
                err = [fvm.solve_steady(turned_square(a), cell_mm=cell).t_max - refs[str(a)] for a in angles]
            print(f"| {cell:g} | {'sampled' if sampled else 'exact'} | " + " | ".join(f"{e:+.3f}" for e in err) + f" | {max(err) - min(err):.3f} |", flush=True)


def study_tee():
    """!
    @brief Edge-shift scatter of the small T (FVM and FDM) at 1 and 0.5 mm, sampled and exact, against the 1/12 mm run.
    @return None.
    """
    print("\n### small T: scatter of the error of the hottest point over twelve neck positions (K)\n")
    print("| model | cell (mm) | sampled | exact |\n| :-- | --: | --: | --: |")
    for mod in (fvm, fdm):
        refs = [mod.solve_steady(small_t(10.0 + k / 12.0), cell_mm=1.0 / 12.0).t_max for k in range(12)]
        for cell in (1.0, 0.5):
            row = []
            for sampled in (True, False):
                with sampled_rule(sampled):
                    err = [mod.solve_steady(small_t(10.0 + k / 12.0), cell_mm=cell).t_max - refs[k] for k in range(12)]
                row.append((max(err) - min(err), float(np.mean(err))))
            print(f"| {mod.__name__.split('.')[-1]} | {cell:g} | {row[0][0]:.2f} (mean {row[0][1]:+.2f}) | {row[1][0]:.2f} (mean {row[1][1]:+.2f}) |", flush=True)


def study_balance():
    """!
    @brief Heat balance of the turned square and the invariance of the total power of the part (the weights sum to one for every turn).
    @return None.
    """
    print("\n### heat balance and the power of the part (FVM, FDM, 3D solid; turned square, 1 mm)\n")
    print("| angle (deg) | FVM balance | FDM balance | 3D balance | area of the part on the board / 9 mm2 |\n| --: | --: | --: | --: | --: |")
    for angle in (0, 17, 45):
        row = []
        for mod in (fvm, fdm, solid3d):
            row.append(abs(mod.solve_steady(turned_square(angle), cell_mm=1.0).balance_error))
        p = turned_square(angle)
        w = geometry.part_weights(p.heaters[0].polygon, p.board.outline, 30, 30, 1e-3, 1e-3)
        print(f"| {angle} | {row[0]:.1e} | {row[1]:.1e} | {row[2]:.1e} | {w.sum() * 1e-6 / 9e-6:.12f} |", flush=True)


STUDIES = {"area": study_area, "turn": study_turn, "tee": study_tee, "balance": study_balance}


def main():
    """!
    @brief Run the named study (default: all).
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in STUDIES.items():
        if which in ("all", name):
            fn()


if __name__ == "__main__":
    main()
