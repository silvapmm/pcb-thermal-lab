#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_robustness.py
@brief Question 2.3: does the centroid film hold on other boards: drawn copper, striped copper with a pad, copper reaching the edge, the disc, and a 45 degree square at several cells?
@details Error of the mean heater rise against the program's own FRAME reference (the same board as an aligned rectangle with no outline, 0.1 mm cell, same laminate rule: no
         outline path, no cut cell, so the reference does not move with the film treatment), as a cell error at fixed idealisation. Candidates `c0` (the program: film on the node
         for imported copper, series film from the centre for drawn) and `c9` (series film from the centroid of the board part). Boards: ten turned and shifted squares as in
         `study_candidates.py`; the disc has no frame reference and is compared with `c0` at 0.1 mm.
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_robustness.py <h_side> <cells>`.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import cases                                                                   # noqa: E402
import study_outline_mask as sm                                                # noqa: E402
import variants                                                                # noqa: E402

ANGLES = (0.0, 11.25, 22.5, 33.75, 45.0)
SHIFTS = (0.0, 0.3)


def stats(errs):
    """!
    @brief Mean, spread and worst of a list of errors.
    @param errs Errors in percent.
    @return Tuple (mean, spread, worst).
    """
    e = np.asarray(errs)
    return float(e.mean()), float(np.ptp(e)), float(np.abs(e).max())


def main():
    """!
    @brief Run the cases and print the tables.
    @return None.
    """
    hs = float(sys.argv[1])
    cells = [float(c) for c in sys.argv[2].split(",")]
    sets = [("imported full copper inset 1.2", "imported", False, 1.2), ("drawn full copper inset 1.2", "drawn", False, 1.2),
            ("imported stripes+pad inset 1.2", "imported", True, 1.2), ("drawn stripes+pad inset 1.2", "drawn", True, 1.2),
            ("imported full copper to the edge (inset 0)", "imported", False, 0.0), ("imported full copper inset 3", "imported", False, 3.0)]
    for label, kind, pattern, inset in sets:
        cases.set_inset(inset)
        ref = cases.run(cases.build("rect", kind, hs, pattern=pattern), 0.1)[0]
        for film in ("node", "centroid"):
            for c in cells:
                errs = []
                for sh in SHIFTS:
                    sm.C = 15.0 + sh * c
                    for ang in ANGLES:
                        p = cases.build("square", kind, hs, ang=ang, pattern=pattern)
                        with variants.use(film=film):
                            errs.append(100 * (cases.run(p, c)[0] / ref - 1))
                sm.C = 15.0
                m, s, w = stats(errs)
                print(f"{label:46s} h_side {hs:g} film {film:8s} cell {c:4g}: mean {m:+.2f} spread {s:.2f} worst {w:.2f} (ref {ref:.3f})", flush=True)
    # disc: no frame reference, the program at 0.1 mm
    cases.set_inset(1.2)
    p = cases.build("disc", "imported", hs)
    ref = cases.run(p, 0.1)[0]
    for film in ("node", "centroid"):
        print("disc imported", film, [round(100 * (cases.run(p, c)[0] / ref - 1), 2) for c in cells] if film == "node" else
              [round(100 * (_run_c(p, c) / ref - 1), 2) for c in cells], "(error vs the node-film program at 0.1 mm; cells", cells, ")", flush=True)


def _run_c(p, c):
    """!
    @brief Heater rise with the centroid film.
    @param p Problem.
    @param c Cell in mm.
    @return Mean rise K.
    """
    with variants.use(film="centroid"):
        return cases.run(p, c)[0]


if __name__ == "__main__":
    main()
