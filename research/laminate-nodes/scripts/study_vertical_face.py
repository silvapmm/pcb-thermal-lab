#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_vertical_face.py
@brief The two undecided points of bare-spot-under-source: the face term on a partly covered cell (1.2 K on the hatched case) and the quantity the 3D solid reports (slab centre or face).
@details Question answered: how should the reported peak of a part on a layer with partly absent copper be corrected for the half layer of laminate between the node and the face? Variants of
         the exponent p of Q (1 - f)^p t / (2 k_z A): off, p = 0 (the full term on every cell with f < 1), p = 1 (bare-spot P1), p = 2, and with the vertical correction of the link on or off.
         Part A: windows 2 to 12 mm under a 6 mm part on a 2-layer 1.6 mm, the typical 4- and 6-layer boards (f = 0 under the window, 1 outside): the term is exact there. Part B: a copper pad whose
         edge is moved from the cell edge by 0, 1/4, 1/2 and 3/4 of the program's cell (0.5 mm), so that the cells under the part are partly covered; the reference has the edge where it is
         (cell 0.125 mm). Part C: a fine hatch (pitch 0.5, 1, 2 mm, duty 0.3 and 0.5) over the part; the program sees the fill as `Zone.fill` = 1 - (1 - duty)^2, the reference the lines, so
         the question is which p matches the arithmetic mixture. Part D: the 3D solid of the program on the windows of part A, its `t_max` against the reference at the centre of the top slab and at the face.
         Output: out/vertical_face.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_vertical_face.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import report as RP
import rule as RU
import runner as RN

VARIANTS = {"off": dict(vert=False, face=-1.0), "vert only": dict(vert=True, face=-1.0), "vert + p=0": dict(vert=True, face=0.0), "vert + p=1": dict(vert=True, face=1.0),
            "vert + p=2": dict(vert=True, face=2.0), "p=1 only": dict(vert=False, face=1.0)}


def run_specs(specs, cell, ref_dx, ref_nsub):
    """!
    @brief Errors of the variants (n = 1, so that only the vertical path and the reading differ) on a list of specs.
    @param specs List of boards.Spec.
    @param cell Cell of the program in mm.
    @param ref_dx Cell of the reference in mm.
    @param ref_nsub Sub-slabs of the reference.
    @return list of row dicts.
    """
    rows = []
    for s in specs:
        ref = RN.reference(s, ref_dx, ref_nsub)
        row = {"board": s.name, "ref K": (".2f", ref["max"]), "ref centre vs face %": 100 * (ref["max_centre"] / ref["max"] - 1)}
        for k, kw in VARIANTS.items():
            row[k] = RN.err(RN.fvm_peak(s, RU.with_(RU.Rule(), n_fixed=1, **kw), cell)["peak"], ref["max"])
        rows.append(row)
    return rows


def main():
    """!
    @brief Parts A to D.
    @return None.
    """
    A = [BD.Spec(f"{n}L {w} mm window", layers=n, stack=("simple" if n == 2 else "template"), shapes=[("window", w)] + [("full",)] * (n - 1)) for n in (2, 4, 6) for w in (2, 4, 6, 12)]
    B = [BD.Spec(f"pad edge {d:+.3f} mm", layers=2, shapes=[("pad", 10.0 + 2 * d), ("full",)]) for d in (0.0, 0.125, 0.25, 0.375)]
    C = [BD.Spec(f"hatch {p_} duty {du}", layers=2, size=20.0, shapes=[("hatch", p_, du), ("full",)]) for p_ in (0.5, 1.0, 2.0) for du in (0.3, 0.5)]
    out = {}
    for tag, specs, rdx in (("A windows", A, 0.25), ("B pad edge off the grid", B, 0.125), ("C hatch", C, 0.125)):
        rows = run_specs(specs, 0.5, rdx, 8)
        RP.table(rows, list(rows[0]), title=f"Part {tag}: error of the peak, percent (n = 1)")
        out[tag] = rows
    # Part D: the 3D solid of the program on the windows of part A
    from pcbthermal import SolverOptions, simulate
    rows = []
    for s in A:
        p = BD.problem(s)
        ref = RN.reference(s)
        t3 = float(simulate(p, SolverOptions(models=("solid3d",), cell_mm=0.5)).results["solid3d"].t_max - p.board.ambient)
        rows.append({"board": s.name, "solid3d vs face %": RN.err(t3, ref["max"]), "solid3d vs centre %": RN.err(t3, ref["max_centre"])})
    RP.table(rows, list(rows[0]), title="Part D: the program's 3D solid against the face value and the slab-centre value of the reference, percent")
    out["D solid3d"] = rows
    RP.save("vertical_face", out)


if __name__ == "__main__":
    main()
