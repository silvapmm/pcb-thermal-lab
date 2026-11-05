#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d_real.py
@brief S2: the 3D solid with the single footprint rule (`disc_eta` of solid_patch: the centred disc enlarged to 0.78 r_v, a point when the cell is coarser) against the program's rule on
       boards with 100 or more vias, and against the FVM with the recommended treatment.
@details The 3D solid is limited to `LIMIT_3D` unknowns, so the boards are cut to a window around the source (--window mm square, default 40) with the holes inside it kept;
         the same window is used for every model. For each board and cell of --cells: the via effect E (FVM program, FVM recommended, 3D program rule, 3D `disc_eta`), and the copper
         fill gain of the 3D solid with both rules (the quantity whose cell dependence the single rule is meant to remove: -4.77 / -4.35 / -5.65 K against -4.77 / -4.51 / -4.54 K on
         the 3 x 3 board of point-via-convergence 6). Configurations above the limit are skipped and printed.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_solid3d_real.py [--window 40] [--cells 1 0.5 0.25]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import real_board as rbd
import runs
from pcbthermal import solid3d

LIMIT_3D = 250_000                       # Unknowns the study accepts for the 3D solid (the fixed limit the program used before the memory guard replaced it)


def window(holes, width, height, size, centre):
    """!
    @brief Cut the hole list to a square window and shift it to a new origin.
    @param holes List of (x, y, d).
    @param width Board width in mm.
    @param height Board height in mm.
    @param size Side of the window in mm (limited to the board).
    @param centre Window centre (x, y) in mm.
    @return tuple (holes, width, height) of the window.
    """
    sx, sy = min(size, width), min(size, height)
    x0 = min(max(centre[0] - sx / 2.0, 0.0), width - sx)
    y0 = min(max(centre[1] - sy / 2.0, 0.0), height - sy)
    out = [(x - x0, y - y0, d) for x, y, d in holes if x0 <= x < x0 + sx and y0 <= y < y0 + sy]
    return out, sx, sy


def main(argv=None):
    """!
    @brief Print the 3D table.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=float, default=40.0)
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25])
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    sets = []
    for name, spec in rbd.BOARDS.items():
        try:
            holes, w, h = rbd.holes_of(name)
            sets.append((name, holes, w, h, spec["layers"]))
        except FileNotFoundError as e:
            print("skipped:", e)
    holes, w, h = rbd.own_via_field(10)
    sets.append(("own 100", holes, w, h, 4))
    print("| board (window) | holes | cell (mm) | E FVM program | E FVM recommended | E 3D program rule | E 3D single rule | fill gain 3D program rule | fill gain 3D single rule |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for name, holes, w, h, layers in sets:
        cx, cy, _ = rbd.densest_window(holes, 8.0, w, h)
        hw, ww, hh = window(holes, w, h, a.window, (cx, cy))
        if not hw:
            continue
        p = rbd.problem_from_holes(hw, ww, hh, layers=layers)             # the source goes on the densest window of the cut board
        pf = rbd.problem_from_holes(hw, ww, hh, layers=layers, fill_k=385.0)
        for c in a.cells:
            n = solid3d.unknowns(p, c)[0]
            if n > LIMIT_3D:
                print(f"| {name} ({ww:g} x {hh:g}) | {len(hw)} | {c:g} | skipped: {n:,} unknowns > {LIMIT_3D:,} | | | | | |", flush=True)
                continue
            e_prog = runs.via_effect(p, "fvm", c)
            e_mw = runs.via_effect(p, "fvm", c, runs.MW_BOARD)
            e3_old = runs.via_effect(p, "solid3d", c)
            e3_new = runs.via_effect(p, "solid3d", c, solid_rule="disc_eta")
            g_old = runs.rise(pf, "solid3d", c) - runs.rise(p, "solid3d", c)
            g_new = runs.rise(pf, "solid3d", c, solid_rule="disc_eta") - runs.rise(p, "solid3d", c, solid_rule="disc_eta")
            print(f"| {name} ({ww:g} x {hh:g}) | {len(hw)} | {c:g} | {e_prog:.2f} | {e_mw:.2f} | {e3_old:.2f} | {e3_new:.2f} | {g_old:.2f} | {g_new:.2f} |", flush=True)


if __name__ == "__main__":
    main()
