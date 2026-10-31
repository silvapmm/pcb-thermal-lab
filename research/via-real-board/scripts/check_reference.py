#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_reference.py
@brief How converged is the resolved reference of S1? The via effect E at 1/8, 1/16 and (for the nearest via only, as the memory allows) 1/32 mm, and the Richardson estimate of the limit.
@details The 1/32 mm grid has 410 000 unknowns; the solve is run only with --fine and only for one distance, because a direct solve of that size can pass 4 GB on a shared machine.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/check_reference.py [--fine]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import edge_reference as er


def main(argv=None):
    """!
    @brief Print E of the reference on finer and finer grids for several distances.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--fine", action="store_true", help="also solve 1/32 mm for the first distance")
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    print("| d (mm) | E at 1/8 mm | E at 1/16 mm | difference | first-order Richardson limit (if the error halves with the cell) |")
    print("| --: | --: | --: | --: | --: |")
    for d in (0.16, 0.5, 2.0):
        p = er.edge_board(d)
        e8, e16 = er.via_effect_reference(p, 1.0 / 8.0), er.via_effect_reference(p, 1.0 / 16.0)
        print(f"| {d:g} | {e8:.4f} | {e16:.4f} | {e16 - e8:+.4f} | {2 * e16 - e8:.4f} |", flush=True)
    if a.fine:
        p = er.edge_board(0.16)
        print(f"1/32 mm, d = 0.16: E = {er.via_effect_reference(p, 1.0 / 32.0):.4f}")


if __name__ == "__main__":
    main()
