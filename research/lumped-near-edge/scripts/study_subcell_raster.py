#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_subcell_raster.py
@brief Does a finer Lumped raster remove the sub-cell footprint error?
@details Same boards as study_subcell.py (24 x 24 mm, 1 W source of 0.1 to 2 mm, shifts 0 and 0.25 mm). The program's Lumped is called directly (lumped.solve_steady) at a raster of
         0.5, 0.25 and 0.125 mm (the API keeps the raster between 0.5 and 1 mm for the Lumped); the reference is the cached FVM at 0.0625 mm of study_subcell.py (run it first).
         Prints the error of the hottest rise, the cost in seconds. Run from the repository root with PCBT_TREE set as for the other studies.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import pcbthermal.lumped as lumped  # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| side mm | shift mm | raster 0.5 % | 0.25 % | 0.125 % | 0.0625 % | s at 0.125 |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for side in (0.2, 0.3, 0.5, 0.75, 1.0, 2.0):
        for sh in (0.0, 0.25):
            pos = (12.0 + sh, 12.0 + sh)
            p = B.board(24.0, 24.0, side, pos, h_side=10.0)
            ref = B.fvm(f"sub|{side}|{sh}", p, 0.0625, side, pos)[1]
            e = []
            t125 = 0.0
            for cell in (0.5, 0.25, 0.125, 0.0625):
                t0 = time.time()
                r = lumped.solve_steady(p, rings=10, cell_mm=cell)
                if cell == 0.125:
                    t125 = time.time() - t0
                e.append(100 * ((r.t_max - p.board.ambient) / ref - 1))
            print(f"| {side:g} | {sh:g} | " + " | ".join(f"{x:+.1f}" for x in e) + f" | {t125:.1f} |", flush=True)


if __name__ == "__main__":
    main()
