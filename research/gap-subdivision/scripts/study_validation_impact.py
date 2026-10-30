#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_validation_impact.py
@brief Impact of cutting every gap into more nodes on the validation scenarios of docs/validation.md and on the three example projects (FVM copy, 1 mm cells).
@details Question: if the layered model used n nodes through every dielectric gap (every cell, or only the cells that show laminate plus a margin), how much would the peak of the boards that the
         program is validated on move, against the 3D solid (the program's own resolved comparison), and what would it cost in unknowns? The scenarios are those of
         research/models-comparison (accuracy_study.cases(), stress_study.cases(), read only) plus the example projects. Boards with a metal block are skipped (the copy does not model blocks).
         Columns: the program's FVM peak, the copy with n = 1 (check: equal), the change in percent of the rise for n = 2 and 4 in every cell, and n = 4 only in bare cells plus a margin, the
         3D solid, and the unknowns of a local implementation. Output: out/validation_impact.json and baseline/validation_impact.csv.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_validation_impact.py   (from the repository root).
"""

import csv
import sys

import _bootstrap as BS

sys.path.append(str(BS.REPO / "research" / "models-comparison" / "scripts"))

import gapnodes as G                                                        # noqa: E402
import layered as LY                                                        # noqa: E402

CELL = 1.0


def boards():
    """!
    @brief The scenarios and the example projects.
    @return list of (name, Problem).
    """
    import accuracy_study
    import stress_study
    from pcbthermal.project import load_project
    out = list(accuracy_study.cases()) + list(stress_study.cases())
    for f in ("example_board", "profile_board", "reference_board"):
        out.append((f"project {f}", load_project(str(BS.REPO / "examples" / f"{f}.pcbt.json")).problem))
    return out


def main():
    """!
    @brief Run every board and print and write the table.
    @return None.
    """
    from pcbthermal import SolverOptions, simulate
    rows = []
    print(f"{'board':52s} {'L':>2s} {'FVM K':>8s} {'copy n=1':>9s} {'n=2 all':>8s} {'n=4 all':>8s} {'n=4 gr':>8s} {'n=4 bare':>9s} {'3D solid':>9s} {'unk x all4':>10s} {'unk x bare4':>11s}")
    for name, p in boards():
        net = LY.network(p, CELL)
        if net.nl != p.board.layers:
            print(f"{name:52s} skipped (metal block)")
            continue
        amb = p.board.ambient
        net.K = net._assemble()
        th, _ = net.solve_steady()
        base = float(th.max())
        r1 = G.run(p, CELL, 1, "none")
        out = {"name": name, "layers": p.board.layers, "fvm_K": base, "copy1_K": r1["peak_all"]}
        for key, kw in (("n2_all", dict(n=2, where="all")), ("n4_all", dict(n=4, where="all")), ("n4_graded", dict(n=4, where="all", grading="graded")), ("n4_bare", dict(n=4, where="bare"))):
            r = G.run(p, CELL, **kw)
            out[key] = r["peak_all"]
            out[key + "_unk"] = r["unknowns"]
        try:
            out["solid3d_K"] = float(simulate(p, SolverOptions(models=("solid3d",), cell_mm=CELL)).results["solid3d"].t_max - amb)
        except Exception as e:                                               # reported, not hidden
            out["solid3d_K"] = float("nan")
            print("  solid3d:", type(e).__name__)
        n0 = r1["unknowns"]
        out["unk_all4"] = out["n4_all_unk"] / n0
        out["unk_bare4"] = out["n4_bare_unk"] / n0
        rows.append(out)

        def d(k):
            """!
            @brief Change of a copy peak against the program's, percent of the rise.
            @param k Key of the copy.
            @return float.
            """
            return 100.0 * (out[k] / base - 1.0)

        print(f"{name:52s} {p.board.layers:2d} {base:8.2f} {out['copy1_K']:9.2f} {d('n2_all'):+8.2f} {d('n4_all'):+8.2f} {d('n4_graded'):+8.2f} {d('n4_bare'):+9.2f} {out['solid3d_K']:9.2f} {out['unk_all4']:10.2f} {out['unk_bare4']:11.2f}")
    with open(BS.BASELINE / "validation_impact.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
