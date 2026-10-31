#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_validation_rows.py
@brief What the one rule moves in docs/validation.md: the scenarios of the models-comparison study and the example projects, FVM, FDM and Lumped, before and after, with the 3D solid for scale.
@details Question answered: which numbers of the validation tables change when the program adopts the rule, by how much, and do boards with copper in every cell stay exactly as they are? Boards: the
         scenarios of research/models-comparison (accuracy_study.cases(), stress_study.cases(), read only; the rows of docs/validation.md section 2), the three example projects, and the one-layer
         boards of the validation (sections 11 and 14 are two-layer and multilayer). For each: the program's peak (the preset "program"), the rule's peak (default; the face term in the reported
         value as in the proposal), the change in K and in percent, the flagged cells and the unknown ratio; the same for the FDM (rectangular boards without an edge coefficient) and the Lumped (the
         network of the rule); the 3D solid (unchanged) as the scale. Boards with a metal block or an outline are listed as "skipped" with the reason (README 8). Cell 1 mm as in the tables of
         docs/validation.md. Output: out/validation_rows.json (the movement column feeds INTEGRATION.md's table).
         Run: .venv/bin/python research/laminate-nodes/scripts/study_validation_rows.py
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

from _bootstrap import HERE

sys.path.append(str(HERE.parent / "models-comparison" / "scripts"))

import fdmnet as FN                                                         # noqa: E402
import gapnet as GN                                                         # noqa: E402
import report as RP                                                         # noqa: E402
import rule as RU                                                           # noqa: E402
from study_analytic import lumped_peak                                      # noqa: E402
from pcbthermal import SolverOptions, simulate                              # noqa: E402


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
        out.append((f"project {f}", load_project(str(HERE.parents[1] / "examples" / f"{f}.pcbt.json")).problem))
    return out


def peak(net, p, rule):
    """!
    @brief Peak with the face term of a solved network.
    @param net Network.
    @param p Problem.
    @param rule Rule.
    @return float rise in K.
    """
    th, _ = net.solve_steady()
    return GN.peak_under_parts(net, th, p, rule)[0]


def main():
    """!
    @brief Run every board.
    @return None.
    """
    rows = []
    prog, new = RU.PRESETS["program"], RU.Rule()
    for name, p in boards():
        cell = 1.0
        amb = p.board.ambient
        row = {"board": name}
        try:
            a = GN.build(p, cell, prog)
            b = GN.build(p, cell, new)
        except NotImplementedError as e:
            row["note"] = f"skipped: {e}"
            rows.append(row)
            print(row, flush=True)
            continue
        pa, pb = peak(a, p, prog), peak(b, p, new)
        row.update({"FVM program C": (".2f", pa + amb), "FVM rule C": (".2f", pb + amb), "FVM change K": (".2f", pb - pa), "FVM change %": 100 * (pb / pa - 1),
                    "flagged": [int(g.flagged.sum()) for g in b.ladder.gaps], "unk x": (".2f", b.ladder.counts(p.board.layers == 1)["ratio_ragged"])})
        try:
            fa, fb = FN.build(p, cell, prog), FN.build(p, cell, new)
            row["FDM change K"] = (".2f", peak(fb, p, new) - peak(fa, p, prog))
        except NotImplementedError:
            row["FDM change K"] = "n/a"
        try:
            row["Lumped change K"] = (".2f", lumped_peak(p, new, cell) - lumped_peak(p, prog, cell))
        except Exception as e:                                               # reported, not hidden
            row["Lumped change K"] = type(e).__name__
        try:
            row["3D solid C"] = (".2f", float(simulate(p, SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max))
        except Exception as e:
            row["3D solid C"] = type(e).__name__
        rows.append(row)
        print(row, flush=True)
    cols = ["board", "FVM program C", "FVM rule C", "FVM change K", "FVM change %", "flagged", "unk x", "FDM change K", "Lumped change K", "3D solid C"]
    RP.table([r for r in rows if "note" not in r], cols, title="Validation scenarios and examples: the program and the rule, 1 mm cell")
    RP.save("validation_rows", rows)


if __name__ == "__main__":
    main()
