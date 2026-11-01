#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_sweep.py
@brief Error of the via effect of a via near a board edge on the current develop: program, mirror image and Robin image, against the resolved layered reference, for edge films from insulated to isothermal.
@details Board of `edge_reference.edge_board` (10 x 10 mm, four copper planes, 0.5 W in 3 x 2 mm, one 0.3 mm copper-filled via at distance d from the right edge); reference
         = the same layered model on a 1/16 mm grid by the independent solver `sheets2d`. Quantity E = T_max(no via) - T_max(via), error in per cent of E.
         Run from the repository root: `.venv/bin/python research/via-edge-image/scripts/study_edge_sweep.py [--h-side 0 10 ...] [--cells 1 0.5 0.25] [--distances ...] [--modes ...]`.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import paths  # noqa: E402,F401
import edge_hook as eh  # noqa: E402
import edge_reference as er  # noqa: E402
import program_cases as pc  # noqa: E402


def effect(p, mode, cell):
    """!
    @brief Via effect of the FVM with an edge treatment.
    @param p Problem with the via.
    @param mode "program", "mirror" or "robin".
    @param cell Cell in mm.
    @return float E in K.
    """
    q = er.deepcopy_without_via(p)
    with eh.patched(mode):
        return pc.max_rise(q, "fvm", cell) - pc.max_rise(p, "fvm", cell)


def main(argv=None):
    """!
    @brief Print the tables.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--h-side", type=float, nargs="+", default=[0.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6])
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25])
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.3, 0.5, 1.0, 2.0, 4.0])
    ap.add_argument("--modes", nargs="+", default=["program", "mirror", "robin"])
    ap.add_argument("--corner", action="store_true")
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    pc.load_libraries()
    for hs in a.h_side:
        print(f"\n## h_side = {hs:g} W/m2K{', corner' if a.corner else ''}\n")
        print("| d (mm) | reference E (K) | mode | " + " | ".join(f"{c:g} mm" for c in a.cells) + " |")
        print("| --: | --: | :-- | " + " | ".join("--:" for _ in a.cells) + " |")
        for d in a.distances:
            p = er.edge_board(d, True, None, hs or None, corner=a.corner)
            ref = er.via_effect_reference(p, 1.0 / 16.0)
            for m in a.modes:
                row = [f"{100.0 * (effect(p, m, c) / ref - 1.0):+.1f} %" for c in a.cells]
                print(f"| {d:g} | {ref:.3f} | {m} | " + " | ".join(row) + " |", flush=True)


if __name__ == "__main__":
    main()
