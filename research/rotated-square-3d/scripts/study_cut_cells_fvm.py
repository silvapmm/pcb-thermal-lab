#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cut_cells_fvm.py
@brief Option P1 for the layered FVM: does treating a cut cell by its real shape (aperture and centroid distances) remove the dependence of the answer on where the outline cuts the grid?
@details The prototype `lib/fvm_cutcell.py` replaces the lateral links of the program's FVM (and optionally the edge film) on a copy; the program is not edited.
         Variants (`scheme`): "program" (the unmodified FVM), "aperture" (nodes at the cell centres, link cross-section = aperture), "links" (nodes at the
         centroids of the board parts, aperture over the centroid distances), "links+strip" ("links" plus the conduction from the centroid to the outline in
         series with the edge film). Studies (each prints a markdown table and writes `out/cutfvm_<name>.json`):

         rect   - an insulated rectangle whose right edge moves over one cell, hot-cell value against the closed form of `lib/sheetmodes.py` (point at the cell centre)
         disc   - a round two-layer board against the axisymmetric reduction of the same layered model (`lib/layered_disc.py`): peak at the cell centre and rim loss
         tee    - the example board cut to the T preset (aligned references at 2/3 and 1/3 mm) and the small T with the neck edge moved over a cell, error against
                  the program at 1/12 mm cells (in which the edge lies on grid lines)
         square - a square of 20 mm turned and shifted, `h_side` 2000, board and part moved together; invariance against the aligned board and the finest cell
         cost   - set-up time of the geometry and the small-cell diagnostics (cover below 0.1, the largest link ratio) of a turned square and the T

         Tiers: `light` (default; every case below 0.6 GB resident and a few seconds; measured peak 0.55 GB) and `heavy` (cells down to 1/24 mm and a 16-step sweep:
         up to about 3 GB; wait for a quiet machine).
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_cut_cells_fvm.py [rect|disc|tee|square|cost|all] [--tier light|heavy]   (from the repository root)
"""

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "outline", "scripts"))

import fvm_cutcell as fc          # noqa: E402
import layered_disc               # noqa: E402
import rotsq                      # noqa: E402
import runs                       # noqa: E402
import sheetmodes                 # noqa: E402
from outline_rectangle_study import outlines   # noqa: E402
from pcbthermal import Problem, fvm            # noqa: E402
from pcbthermal.examples import example_board  # noqa: E402

SCHEMES = ("program", "aperture", "links", "links+strip")


def rect_board(s_mm, h_side=0.0):
    """!
    @brief An insulated 20 mm x 20 mm board in a 30 mm box with its right edge at 25 + s mm and a 4 x 4 mm part 2 mm from it.
    @param s_mm Extra width of the board in mm (0 to one cell moves the edge across a cell).
    @param h_side Edge coefficient (0: insulated, the case with a closed form).
    @return Problem.
    """
    p = Problem.new(30.0, 30.0, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(19, 13, 23, 17), name="U")
    p.set_outline([[5, 5], [25 + s_mm, 5], [25 + s_mm, 25], [5, 25]])
    return p


def exact_point(p, s_mm, x_m, y_m, n_modes=300):
    """!
    @brief Closed-form rise of the top layer at a point of `rect_board`.
    @param p Problem from `rect_board`.
    @param s_mm Extra width in mm.
    @param x_m x of the point in the box (m).
    @param y_m y of the point in the box (m).
    @param n_modes Modes per direction.
    @return Rise in K (a 2 micrometre square stands for the point).
    """
    c = sheetmodes.layer_constants(p)
    e = 1e-6
    return sheetmodes.rectangle_mean(c, (0.020 + s_mm * 1e-3, 0.020), 0, 2.0, (0.014, 0.008, 0.018, 0.012),
                                     (x_m - 0.005 - e, y_m - 0.005 - e, x_m - 0.005 + e, y_m - 0.005 + e), 0, n_modes)


def study_rect(tier):
    """!
    @brief Insulated rectangle, right edge moved over one cell, hot-cell value minus the closed form at the centre of that cell.
    @param tier "light" or "heavy".
    @return dict of the numbers.
    """
    cells = (1.0, 0.5) if tier == "light" else (1.0, 0.5, 0.25)
    out = {}
    print("\n### rect: error of the hot cell against the closed form (K), insulated edges\n")
    print("| cell (mm) | right edge at 25 + s | " + " | ".join(SCHEMES) + " |\n| --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for cell in cells:
        for k in range(0, 9):
            s = cell * k / 8
            p = rect_board(s)
            amb = p.board.ambient
            row = []
            for sch in SCHEMES:
                r = fc.solve(p, cell, sch)
                _, x, y = r.t_max_location
                ex = exact_point(p, s, x, y)
                row.append(r.t_max - amb - ex)
            out[f"{cell:g}|{s:.4f}"] = row
            print(f"| {cell:g} | {s:.3f} | " + " | ".join(f"{v:+.3f}" for v in row) + " |", flush=True)
    return out


def study_disc(tier):
    """!
    @brief Round board against the axisymmetric reduction: the peak at the centre of the hot cell and the heat leaving by the rim.
    @param tier "light" or "heavy".
    @return dict of the numbers.
    """
    d, a = 40.0, 3.0
    cells = (1.0, 0.5, 0.25) if tier == "light" else (1.0, 0.5, 0.25, 0.125)
    out = {}
    print("\n### disc: peak at the cell centre and rim loss against the axisymmetric reduction (per cent of the rise / of the rim loss)\n")
    print("| h_side | rise at the centre of the hot cell (K) | cell (mm) | " + " | ".join(f"{s}: peak / rim" for s in SCHEMES) + " |\n| --: | --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for hs in (10.0, 100.0, 1000.0, 5000.0):
        p = rotsq.disc_board(d, a, hs)
        amb = p.board.ambient
        sol = layered_disc.solve(p, d / 2000.0, a / 1000.0)
        for c in cells:
            ref = float(np.interp(c / 1000.0 * 0.5 * np.sqrt(2.0), sol["r"], sol["top"]))     # the cell-centred unknown is a point value at the cell centre
            row, rec = [], []
            for sch in SCHEMES:
                r = fc.solve(p, c, sch)
                peak = 100.0 * (r.t_max - amb - ref) / ref
                rim = 100.0 * (r.power_out["sides"] / sol["heat_rim"] - 1.0)
                row.append(f"{peak:+.2f} / {rim:+.2f}")
                rec.append([peak, rim])
            out[f"{hs:g}|{c:g}"] = rec
            print(f"| {hs:g} | {ref:.3f} | {c:g} | " + " | ".join(row) + " |", flush=True)
    return out


def example_t(h_side):
    """!
    @brief The example board cut to the T preset.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    p = example_board()
    p.board.h_side = h_side
    p.board.outline = np.array(outlines(100.0, 80.0)["T"]) / 1000.0
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


def study_tee(tier):
    """!
    @brief The example board cut to a T at several cells, and the small T with the neck edge moved over a cell.
    @param tier "light" or "heavy".
    @return dict of the numbers.
    """
    out = {}
    print("\n### tee (a): example board cut to the T, hottest point (degC); at 2/3 and 1/3 mm no cell is cut\n")
    print("| h_side | cell (mm) | " + " | ".join(SCHEMES) + " |\n| --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    cells = [2 / 3, 1 / 3, 1.0, 0.8, 0.5, 0.4, 0.25] if tier == "light" else [2 / 3, 1 / 3, 1.0, 0.8, 0.5, 0.4, 0.25, 0.2]
    for hs in (10.0, 100.0):
        for c in cells:
            row = [fc.tmax(example_t(hs), c, s) for s in SCHEMES]
            out[f"example|{hs:g}|{c:.4f}"] = row
            print(f"| {hs:g} | {c:.3f} | " + " | ".join(f"{v:.3f}" for v in row) + " |", flush=True)
    ref_cell = 1 / 12 if tier == "light" else 1 / 24
    steps = range(0, 12, 2) if tier == "light" else range(0, 12)
    print(f"\n### tee (b): small T, error of the hottest point against the program at {ref_cell:.4f} mm (neck edge on grid lines there), K\n")
    print("| a (mm) | cell (mm) | " + " | ".join(SCHEMES) + " |\n| --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    table = {}
    for k in steps:
        a = 10.0 + k / 12.0
        ref = fc.tmax(small_t(a), ref_cell, "program")
        for c in (1.0, 0.5):
            row = [fc.tmax(small_t(a), c, s) - ref for s in SCHEMES]
            table.setdefault(c, []).append(row)
            out[f"small|{a:.4f}|{c:g}"] = row
            print(f"| {a:.3f} | {c:g} | " + " | ".join(f"{v:+.3f}" for v in row) + " |", flush=True)
    print("\nScatter (max minus min of the error over the positions), K:\n")
    print("| cell (mm) | " + " | ".join(SCHEMES) + " |\n| --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for c, rows in table.items():
        arr = np.array(rows)
        sc = arr.max(axis=0) - arr.min(axis=0)
        out[f"scatter|{c:g}"] = sc.tolist()
        print(f"| {c:g} | " + " | ".join(f"{v:.2f}" for v in sc) + " |")
    return out


def study_square(tier):
    """!
    @brief 20 mm square at h_side 2000 shifted by half a cell and turned 20 and 45 degrees: invariance against the aligned board of the same scheme and cell.
    @param tier "light" or "heavy".
    @return dict of the numbers.
    """
    out = {}
    cells = (0.5, 0.25) if tier == "light" else (0.5, 0.25, 0.125)
    print("\n### square: 20 mm board, h_side 2000, maximum temperature minus the aligned board of the same scheme (K)\n")
    print("| cell (mm) | layout | " + " | ".join(SCHEMES) + " |\n| --: | :-- | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for c in cells:
        base = None
        for tag, ang, sh in (("aligned", 0.0, 0.0), ("shift 1/2 cell", 0.0, c / 2), ("turned 20", 20.0, 0.0), ("turned 45", 45.0, 0.0)):
            p = rotsq.board(ang, 2000.0, side_mm=20.0, box_mm=30.0, part_mm=3.0, shift_mm=(sh, sh))
            vals = [fc.tmax(p, c, s) for s in SCHEMES]
            if base is None:
                base = vals
            d = [v - b for v, b in zip(vals, base)]
            out[f"{c:g}|{tag}"] = vals
            print(f"| {c:g} | {tag} | " + " | ".join(f"{v:.2f} ({x:+.2f})" for v, x in zip(vals, d)) + " |", flush=True)
    return out


def study_cost(tier):
    """!
    @brief Set-up cost of the geometry sampling and the small-cell diagnostics.
    @param tier "light" or "heavy".
    @return dict of the numbers.
    """
    out = {}
    print("\n### cost: network build with and without the cut-cell geometry, and the small cells\n")
    print("| board | cell (mm) | cells | build, program (s) | build, links (s) | cut cells | cover < 0.1 | largest x-link ratio vs a whole pair |\n| :-- | --: | --: | --: | --: | --: | --: | --: |")
    cases = [("T, example", example_t(10.0), (1.0, 0.5)), ("turned square 40 mm", rotsq.board(20.0, 100.0), (1.0, 0.5))]
    if tier == "heavy":
        cases = [(n, p, cs + (0.25,)) for n, p, cs in cases]
    for name, p, cs in cases:
        b = p.board
        for c in cs:
            nx, ny = int(round(b.width * 1000 / c)), int(round(b.height * 1000 / c))
            t0 = time.time()
            fvm.Network(p, nx, ny)
            t_prog = time.time() - t0
            fc.CutCellNetwork.mode = "links"
            t0 = time.time()
            net = fc.CutCellNetwork(p, nx, ny)
            t_cut = time.time() - t0
            cut = (net.cover > 0) & (net.cover < 1)
            gx, _ = net._lateral_links()
            whole = float(net.S[0].max() * net.dy / net.dx)
            ratio = float(gx.max() / whole)
            out[f"{name}|{c:g}"] = [nx * ny, t_prog, t_cut, int(cut.sum()), int((cut & (net.cover < 0.1)).sum()), ratio]
            print(f"| {name} | {c:g} | {nx * ny} | {t_prog:.2f} | {t_cut:.2f} | {int(cut.sum())} | {int((cut & (net.cover < 0.1)).sum())} | {ratio:.2f} |", flush=True)
    return out


def part_mean(problem, cell_mm, scheme):
    """!
    @brief Mean temperature of the top layer under the first part (weights of the part on the board), for a scheme.
    @param problem Problem.
    @param cell_mm Cell size in mm.
    @param scheme "program", "aperture", "links" or "links+strip".
    @return Mean temperature in degC.
    """
    b = problem.board
    r = fc.solve(problem, cell_mm, scheme)
    w = fvm.Network(problem, int(round(b.width * 1000 / cell_mm)), int(round(b.height * 1000 / cell_mm)), assemble=False).Qw[0][problem.heaters[0].layer]
    return float((w * r.T[problem.heaters[0].layer]).sum() / w.sum())


def study_sens(tier):
    """!
    @brief Robustness of the small-T residual: the sampling of the geometry (8, 16, 64), the smallest face-to-centroid distance, a cut of the small apertures,
           and the mean under the part instead of the hottest point.
    @param tier "light" or "heavy" (the same positions; the reference is 1/12 mm in both).
    @return dict of the numbers.
    """
    out = {}
    print("\n### sens: small T, 1 mm, error of the hottest point against the program at 1/12 mm (K), variant links with another sampling or limit; last columns the mean under the part\n")
    print("| a (mm) | samples 8 | samples 16 | samples 64 | d_min 0.25 | ap_min 0.1 | mean: program | mean: links |\n| --: | --: | --: | --: | --: | --: | --: | --: |")
    for k in range(0, 12, 2):
        a = 10.0 + k / 12.0
        ref = fc.tmax(small_t(a), 1 / 12, "program")
        ref_m = part_mean(small_t(a), 1 / 12, "program")
        row = [fc.tmax(small_t(a), 1.0, "links", samples=m) - ref for m in (8, 16, 64)]
        row += [fc.tmax(small_t(a), 1.0, "links", d_min=0.25) - ref, fc.tmax(small_t(a), 1.0, "links", ap_min=0.1) - ref]
        row += [part_mean(small_t(a), 1.0, "program") - ref_m, part_mean(small_t(a), 1.0, "links") - ref_m]
        out[f"{a:.4f}"] = row
        print(f"| {a:.3f} | " + " | ".join(f"{v:+.3f}" for v in row) + " |", flush=True)
    return out


STUDIES = {"rect": study_rect, "disc": study_disc, "tee": study_tee, "square": study_square, "cost": study_cost, "sens": study_sens}


def main():
    """!
    @brief Run the chosen studies.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("Usage:")[0])
    ap.add_argument("which", nargs="?", default="all", choices=list(STUDIES) + ["all"])
    ap.add_argument("--tier", choices=("light", "heavy"), default="light")
    a = ap.parse_args()
    for name, fn in STUDIES.items():
        if a.which in (name, "all"):
            runs.save(f"cutfvm_{name}_{a.tier}.json", fn(a.tier))


if __name__ == "__main__":
    main()
