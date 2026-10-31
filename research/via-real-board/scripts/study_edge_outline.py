#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_outline.py
@brief S1 continued: a via next to an outline edge that does not fall on a grid line, and the footprint restricted to the cells on the board.
@details Same board as `study_edge_distance.py` but the outline cuts the box at x_cut (default 7.0 and 7.03125 mm: on the 1/16 mm reference grid, between grid lines at 1 and 0.5 mm).
         Variants: "mw" (the prototype: footprint kept on every cell inside the grid), "mw+board" (only cells with cover > 0, weighted by the cover), "mw+image" (board + image),
         "mw+fold" (board + fold). Reported for each: E against the resolved reference with the cut (cells beyond removed, the new edge cooled when --h-side > 0), the number of vias
         whose footprint was cut (`edge_patch.STATS`) and the number of wells that became infinite. Only axis-parallel walls are mirrored (a diagonal or curved outline edge gets
         no image: a documented limit, not measured here).
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_edge_outline.py`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import edge_patch as ep
import edge_reference as er
import runs

VARIANTS = (("program", runs.PROGRAM), ("mw", runs.MW_PROTOTYPE), ("mw+board", runs.MW_BOARD), ("mw+image", runs.MW_IMAGE), ("mw+fold", runs.MW_FOLD))


def main(argv=None):
    """!
    @brief Print E against the cell for every cut, distance and variant.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cuts", type=float, nargs="+", default=[7.0, 7.03125])
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.5, 1.0])
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25, 0.125])
    ap.add_argument("--h-side", type=float, default=0.0)
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    for cut in a.cuts:
        for d in a.distances:
            p = er.edge_board(d, True, cut, a.h_side or None)
            e_ref = er.via_effect_reference(p, 1.0 / 16.0, cut)
            print(f"\n## outline at x = {cut:g} mm, via {d:g} mm from it, reference E = {e_ref:.3f} K\n")
            print("| variant | " + " | ".join(f"{c:g} mm" for c in a.cells) + " | cut footprints / infinite wells (finest) |")
            print("| :-- | " + " | ".join("--:" for _ in a.cells) + " | :-- |")
            for name, var in VARIANTS:
                row = []
                for c in a.cells:
                    e = runs.via_effect(p, "fvm", c, var)
                    row.append(f"{e:.3f} ({100.0 * (e / e_ref - 1.0):+.1f} %)")
                note = f"{ep.STATS['dropped']} / {ep.STATS['inf_wells']}" if var != runs.PROGRAM else "-"
                print(f"| {name} | " + " | ".join(row) + f" | {note} |", flush=True)


if __name__ == "__main__":
    main()
