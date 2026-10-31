#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference.py
@brief Is the resolved reference good enough to judge a node count? Grid convergence (cell and sub-slabs separately), Richardson limit, the order, the GCI, the grading of the reference slabs, the face against the slab centre.
@details Question answered: how far is the reference used by every other study (0.25 mm cell, 8 sub-slabs per gap, equal) from its own converged limit, on the boards that matter (one-layer pad
         and window, two-layer window on a thin and a thick gap, 4- and 6-layer typical windows, a hatched board)? The cell sequence is 0.5, 0.25, 0.125 mm at 8 sub-slabs and the sub-slab sequence 4, 8, 16 at 0.25 mm (the joint sequence needs 1.2 million unknowns on a 6-layer board and was dropped; 4 or more layers use 1, 0.5, 0.25 mm and 2, 4, 8); the
         Richardson limit and the observed order come from ref3d.richardson (three grids, ratio 2); the GCI is the Roache estimate with a safety factor of 1.25. A window edge is a singular
         line, so the observed order is below 2 and the limit is quoted with its GCI, never as exact. Also printed: the energy balance of the reference, the graded reference (ratio 2,
         8 sub-slabs) against the equal one (16), and the difference between the face value and the value at the centre of the top slab (the quantity the 3D solid reports).
         Output: out/reference.json. Run from the repository root: .venv/bin/python research/laminate-nodes/scripts/study_reference.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import ref3d as R3
import report as RP


def main():
    """!
    @brief Run the convergence sequences.
    @return None.
    """
    specs = [BD.Spec("1L pad 10", layers=1, shapes=[("pad", 10)]), BD.Spec("1L window 6", layers=1, shapes=[("window", 6)]),
             BD.Spec("2L 0.8 window 6", layers=2, thickness=0.8, shapes=[("window", 6), ("full",)]), BD.Spec("2L 1.6 window 6", layers=2, shapes=[("window", 6), ("full",)]),
             BD.Spec("2L 1.6 pad 10 bare bottom", layers=2, shapes=[("pad", 10), ("none",)]), BD.Spec("4L typical window 6", layers=4, stack="template", shapes=[("window", 6)] + [("full",)] * 3),
             BD.Spec("6L typical window 6", layers=6, stack="template", shapes=[("window", 6)] + [("full",)] * 5)]
    import sys
    if "--deep" in sys.argv:
        specs = [s for s in specs if s.layers >= 4]
    rows = []
    for s in specs:
        p = BD.problem(s)
        c = R3.converged_split(s, p, deep=s.layers >= 4)
        gr8 = R3.solve_spec(s, p, 0.25, 4 if s.layers >= 4 else 8, 2.0)["max"]
        eq = R3.solve_spec(s, p, 0.25, 4 if s.layers >= 4 else 8, 1.0)
        eq16 = R3.solve_spec(s, p, 0.25, 8 if s.layers >= 4 else 16, 1.0)["max"]
        print("done", s.name, flush=True)
        rows.append({"board": s.name, "production K": (".2f", c["production"]), "cell: limit/prod %": 100 * c["corr_dx"], "cell order": (".2f", c["dx_rich"]["order"]), "cell GCI %": (".2f", 100 * c["dx_rich"]["gci_fine"]),
                     "slabs: limit/prod %": 100 * c["corr_nz"], "slab order": (".2f", c["nz_rich"]["order"]), "slab GCI %": (".2f", 100 * c["nz_rich"]["gci_fine"]), "total %": 100 * c["corr_total"],
                     "graded vs equal (same n) %": 100 * (gr8 / eq["max"] - 1), "equal 2n vs n %": 100 * (eq16 / eq["max"] - 1), "centre vs face %": 100 * (eq["max_centre"] / eq["max"] - 1), "balance": (".6f", eq["balance"])})
    RP.table(rows, list(rows[0]), title="Reference convergence (face peak in K; percent where marked)")
    RP.save("reference", rows)


if __name__ == "__main__":
    main()
