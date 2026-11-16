#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_block_exact_cover.py
@brief What does the exact cover of a metal block (`fix/block-exact-cover`, `blocks.block_cover`) change against the 4 x 4 sampled cover times the board cover?
@details The board of `docs/validation.md` 54: a 60 x 40 mm two-layer full-copper board, a 3 W part (35, 15) to (45, 25) mm on top, a 3 mm aluminium block of
         29.8 x 23.7 mm centred at (25, 19.6) mm on the bottom, turned 0 or 20 degrees, 15 W/m2K extra on the block; three boards (no outline, cut at x = 20.4 mm,
         an ellipse of 54 x 34.6 mm centred on the board, a 96-gon); cells of 2, 1 and 0.5 mm. For every case it writes the area of the block on the FVM grid
         (the network's cover), the area of the older rule (4 x 4 samples times the board cover, computed here), the exact area of the block clipped to the board
         (an own clip of the polygon by the half-plane or by the 96-gon, Sutherland-Hodgman, outside the program), the hottest point and the heat balance of the
         FVM and FDM. The temperatures before the change come from running the same script on a tree of `development` before the merge (option --tree).
         Usage (from the repository root): .venv/bin/python research/rotated-square-3d/scripts/study_block_exact_cover.py run OUT.json [--tree PATH]
         and .venv/bin/python research/rotated-square-3d/scripts/study_block_exact_cover.py diff BEFORE.json AFTER.json   (about 1 minute and 0.3 GB per run).
"""

import json
import logging
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def turned_rect(cx, cy, w, h, deg):
    """!
    @brief Corners of a rectangle turned about its centre.
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param w Width in mm.
    @param h Height in mm.
    @param deg Angle in degrees.
    @return numpy.ndarray (4, 2) corners in mm.
    """
    a = np.radians(deg)
    r = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.array([[-w, -h], [w, -h], [w, h], [-w, h]]) / 2.0) @ r.T + [cx, cy]


def ellipse(cx, cy, a, b, n=96):
    """!
    @brief A polygon of n vertices on an ellipse.
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param a Half axis along x in mm.
    @param b Half axis along y in mm.
    @param n Number of vertices.
    @return numpy.ndarray (n, 2) in mm, counter-clockwise.
    """
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.c_[cx + a * np.cos(t), cy + b * np.sin(t)]


def clip(subject, clipper):
    """!
    @brief Sutherland-Hodgman clip of a polygon by a convex counter-clockwise polygon (an own implementation, independent of the program).
    @param subject Vertices (n, 2).
    @param clipper Convex counter-clockwise vertices (m, 2).
    @return numpy.ndarray Vertices of the intersection (k, 2).
    """
    out = [tuple(v) for v in subject]
    cl = [tuple(v) for v in clipper]
    for i in range(len(cl)):
        a, b = cl[i - 1], cl[i]
        inside = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0.0   # noqa: E731
        src, out = out, []
        for j in range(len(src)):
            cur, prev = src[j], src[j - 1]
            if inside(cur) != inside(prev):
                d = (b[0] - a[0]) * (cur[1] - prev[1]) - (b[1] - a[1]) * (cur[0] - prev[0])
                t = ((b[0] - a[0]) * (a[1] - prev[1]) - (b[1] - a[1]) * (a[0] - prev[0])) / d
                out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            if inside(cur):
                out.append(cur)
    return np.array(out)


def area(poly):
    """!
    @brief Shoelace area of a polygon.
    @param poly Vertices (n, 2).
    @return Area in the squared unit.
    """
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


OUTLINES = {"none": [[0, 0], [60, 0], [60, 40], [0, 40]], "cut": [[20.4, 0], [60, 0], [60, 40], [20.4, 40]], "ellipse": ellipse(30.0, 20.0, 27.0, 17.3).tolist()}


def run(out_path):
    """!
    @brief Run the 18 cases on the program found first on sys.path and write the numbers.
    @param out_path JSON file to write.
    @return None.
    """
    from pcbthermal import Problem, SolverOptions, fvm, simulate
    from pcbthermal.geometry import coverage_fraction
    logging.disable(logging.WARNING)
    res = {}
    for name, outl in OUTLINES.items():
        for deg in (0.0, 20.0):
            poly = turned_rect(25.0, 19.6, 29.8, 23.7, deg)
            exact = area(clip(poly, np.asarray(outl, dtype=float)))
            for cell in (2.0, 1.0, 0.5):
                p = Problem.new(60, 40, 2).add_full_copper()
                if name != "none":
                    p.set_outline(outl)
                p.add_heater(1, 3.0, rect=(35, 15, 45, 25), name="U")
                p.add_heatsink(2, 15.0, polygon=poly.tolist(), thickness_mm=3.0, k=205.0, name="Al")
                nx, ny = int(round(60 / cell)), int(round(40 / cell))
                net = fvm.Network(p, nx, ny)
                grid = sum(i["cov"].sum() for i in net.block_info) * net.dx * net.dy * 1e6
                old = (coverage_fraction(p.heatsinks[0].polygon, nx, ny, net.dx, net.dy, samples=4) * net.cover).sum() * net.dx * net.dy * 1e6
                row = {"exact_mm2": exact, "grid_mm2": grid, "sampled_mm2": old}
                for m in ("fvm", "fdm"):
                    r = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m]
                    row[m] = float(r.t_max)
                    row[m + "_balance"] = float(r.balance_error)
                res[f"{name}|{deg:g}|{cell:g}"] = row
                print(name, deg, cell, {k: round(v, 6) for k, v in row.items()}, flush=True)
    with open(out_path, "w") as fh:
        json.dump(res, fh, indent=1)


def diff(before_path, after_path):
    """!
    @brief Print the table of validation 54: area error of the sampled rule, area error of the grid after, and the change of the hottest point.
    @param before_path JSON of a run on the tree before the change.
    @param after_path JSON of a run on the tree after the change.
    @return None.
    """
    b, a = json.load(open(before_path)), json.load(open(after_path))
    print("| outline | angle (deg) | cell (mm) | block area error before (%) | after | FVM (K) | FDM (K) |")
    for k in a:
        o, deg, cell = k.split("|")
        e = a[k]["exact_mm2"]
        print(f"| {o} | {deg} | {cell} | {100 * (b[k]['grid_mm2'] / e - 1):+.4f} | {a[k]['grid_mm2'] / e - 1:+.0e} | "
              f"{a[k]['fvm'] - b[k]['fvm']:+.3f} | {a[k]['fdm'] - b[k]['fdm']:+.3f} |")


if __name__ == "__main__":
    args = sys.argv[1:]
    tree = ROOT
    if "--tree" in args:
        i = args.index("--tree")
        tree = args[i + 1]
        del args[i:i + 2]
    sys.path.insert(0, tree)
    if args and args[0] == "run":
        run(args[1])
    elif args and args[0] == "diff":
        diff(args[1], args[2])
    else:
        print(__doc__)
