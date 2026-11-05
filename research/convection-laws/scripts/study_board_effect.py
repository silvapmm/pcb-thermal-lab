#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_board_effect.py
@brief How far would the hottest temperature move if the program used Raithby-Hollands above and a 1/5 law below? The 17 boards of the regression harness, computed h, horizontal.
@details The program is not edited: `convection.h_natural_horizontal` is replaced in memory (lib/laws.py -> research/horizontal-plate-h/lib/correlations.py `use_horizontal`) by each
         candidate pair of lib/laws.PAIRS for the duration of a run. FVM only, cell 2 mm, h_mode "computed", emissivity as the board has it (0.9 default), orientation "horizontal"
         (layer 1 looks up). The rise is the hottest point minus the ambient. Also run with the emissivity at zero (convection alone) to show the upper bound of the effect.
         A second table repeats the boards with the part power doubled and halved (the Ra of the faces moves with the rise). Output: out/board_effect.json.
Usage: .venv/bin/python research/convection-laws/scripts/study_board_effect.py   (a few minutes; one process)
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(0, ROOT)

import laws  # noqa: E402
import regress_boards  # noqa: E402
from pcbthermal import api  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
LEVELS = ["program", "RH+program-down", "RH+GL", "RH+FI", "Jaffer"]


def rise(problem, level, eps0=False, scale=1.0, cell=2.0):
    """!
    @brief Hottest rise of a board with the program's FVM at one level of the horizontal laws.
    @param problem Problem (modified: computed h, horizontal).
    @param level Key of laws.PAIRS.
    @param eps0 True to set the emissivities to zero (convection only).
    @param scale Factor on the power of every heater.
    @param cell Cell size in mm.
    @return dict with rise (K), the face coefficients h_top, h_bottom (W/m2K, convection plus radiation) and the Rayleigh numbers of the faces.
    """
    b = problem.board
    b.h_mode, b.orientation = "computed", "horizontal"
    if eps0:
        b.emissivity_top = b.emissivity_bottom = 0.0
    for h in problem.heaters:
        h.power *= scale
    with laws.C.use_horizontal(*laws.PAIRS[level]):
        sim = api.simulate(problem, api.SolverOptions(models=("fvm",), cell_mm=cell))
    r = sim.results["fvm"]
    hh = sim.h_used.get("fvm")
    return {"rise": float(r.delta_t), "h": [float(x) for x in hh[:2]] if hh is not None else None}


def main():
    """!
    @brief Run every board at every level and print the table.
    @return None.
    """
    rows = []
    t0 = time.time()
    for name in regress_boards.board_names():
        row = {"board": name}
        for tag, kw in (("rad", {}), ("conv", {"eps0": True}), ("p2", {"scale": 2.0}), ("p05", {"scale": 0.5})):
            for lv in LEVELS:
                try:
                    row[f"{tag}|{lv}"] = rise(regress_boards.build(name), lv, **kw)
                except Exception as exc:                            # a board the program refuses is recorded, not hidden
                    row[f"{tag}|{lv}"] = {"error": str(exc)[:80]}
        rows.append(row)
        base = row["rad|program"].get("rise")
        cells = []
        for lv in LEVELS[1:]:
            v = row[f"rad|{lv}"].get("rise")
            cells.append("   n/a" if v is None or base is None else f"{100 * (v / base - 1):+6.1f}")
        print(f"{name:22s} rise {base if base is None else round(base, 2)!s:>8} K  " + " ".join(cells), flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "board_effect.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"levels in order: {LEVELS[1:]} (percent change of the rise against the program); {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
