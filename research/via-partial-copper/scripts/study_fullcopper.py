#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fullcopper.py
@brief Do the candidate via treatments keep what the program's via already gets right on full copper (grid convergence of a lone via, of a 3 x 3 array, copper-fill gain)?
@details The program's via (`viawell.py`) was tuned and checked on full-copper boards (research/point-via-convergence): a lone via beside a source, the 3 x 3 array with its copper-fill
         gain (-4.51 K resolved) and the lattice of unit cells. This script runs the same boards (their builders are read from research/point-via-convergence/lib) with the FVM and the FDM
         and every variant at 1, 0.5, 0.25 and 0.125 mm and prints the maximum rise and the gain of a copper fill (fill_k = 385 against open); `sheet` and `plane` must equal `current`
         bit for bit (a full-copper footprint is uniform), `star` is a different coupling and is judged by how it changes the convergence.
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_fullcopper.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "point-via-convergence", "lib"))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import program_cases as pc                                                    # noqa: E402

import viavariants as vv                                                      # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    pc.load_libraries()
    print(f"{'board':14s} {'model':5s} {'variant':8s} " + " ".join(f"{c:>8.3f}" for c in (1.0, 0.5, 0.25, 0.125)))
    for model in ("fvm", "fdm"):
        for label, make in (("array open", lambda: pc.array_board(0.0)), ("array Cu fill", lambda: pc.array_board(385.0)), ("lone via", lambda: pc.lone_via_board())):
            for variant in ("current", "sheet", "plane", "star"):
                vals = []
                for cell in (1.0, 0.5, 0.25, 0.125):
                    with vv.patched(variant):
                        vals.append(pc.max_rise(make(), model, cell))
                print(f"{label:14s} {model:5s} {variant:8s} " + " ".join(f"{v:8.3f}" for v in vals), flush=True)
        for variant in ("current", "sheet", "plane", "star"):
            gains = []
            for cell in (1.0, 0.5, 0.25, 0.125):
                with vv.patched(variant):
                    gains.append(pc.max_rise(pc.array_board(385.0), model, cell) - pc.max_rise(pc.array_board(0.0), model, cell))
            print(f"{'copper-fill gain':14s} {model:5s} {variant:8s} " + " ".join(f"{v:8.3f}" for v in gains), flush=True)


if __name__ == "__main__":
    main()
