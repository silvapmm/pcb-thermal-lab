#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_distance.py
@brief S1: how wrong is a via next to a board edge in the recommended treatment, how does the error depend on the distance to the edge, the cell and the edge film, and does the image of the edge in the well remove it?
@details Board: 10 x 10 mm, four copper planes, 0.5 W in a 3 x 2 mm source, one 0.3 mm copper-filled via at distance d from the right edge (`edge_reference.edge_board`).
         Reference: the layered model of the program on a 1/16 mm grid with the barrel at its real size (`edge_reference`, independent solver `sheets2d`).
         Quantity: the via effect E = T_max(no via) - T_max(via) and its error against the reference, in per cent of E.
         Variants: "program" (develop, point via), "mw" (the treatment as the prototype has it), "mw+image" (the well with the edge term of `edge_image`), "mw+fold".
         Sweeps (arguments): --distances, --cells, --h-side (W/m2K; 0 = insulated), --corner (the via near the corner), --check-fine (reference at 1/32 mm too).
         Decision rule for the image (written before the run): adopt it only if the error at 1 mm and d <= 1 mm falls under 3 % of E for every distance and for h_side 0 and 10,
         the cost per via is under 1 ms, and the code is under 60 lines; otherwise document the +12 to +15 % as a limit.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_edge_distance.py [--h-side 0 10] [--corner]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import edge_reference as er
import runs

VARIANTS = (("program", runs.PROGRAM), ("mw", runs.MW_PROTOTYPE), ("mw+image", runs.MW_IMAGE), ("mw+fold", runs.MW_FOLD))


def main(argv=None):
    """!
    @brief Print the tables of E and of the error against the cell for every distance, edge film and variant.
    @param argv Command line (default sys.argv).
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.3, 0.5, 1.0, 2.0, 4.0])
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25, 0.125])
    ap.add_argument("--h-side", type=float, nargs="+", default=[0.0, 10.0])
    ap.add_argument("--corner", action="store_true", help="the via also near the top edge (corner)")
    ap.add_argument("--check-fine", action="store_true", help="also solve the reference at 1/32 mm for the first distance")
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    for hs in a.h_side:
        print(f"\n## h_side = {hs:g} W/m2K{', corner' if a.corner else ''}\n")
        print("| d (mm) | reference E (K) | variant | " + " | ".join(f"{c:g} mm" for c in a.cells) + " |")
        print("| --: | --: | :-- | " + " | ".join("--:" for _ in a.cells) + " |")
        for d in a.distances:
            p = er.edge_board(d, True, None, hs or None, corner=a.corner)
            e_ref = er.via_effect_reference(p, 1.0 / 16.0)
            if a.check_fine and d == a.distances[0]:
                print(f"<!-- reference at 1/32 mm: {er.via_effect_reference(p, 1.0 / 32.0):.4f} K against {e_ref:.4f} K at 1/16 mm -->")
            for name, var in VARIANTS:
                cells = []
                for c in a.cells:
                    e = runs.via_effect(p, "fvm", c, var)
                    cells.append(f"{e:.3f} ({100.0 * (e / e_ref - 1.0):+.1f} %)")
                print(f"| {d:g} | {e_ref:.3f} | {name} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
