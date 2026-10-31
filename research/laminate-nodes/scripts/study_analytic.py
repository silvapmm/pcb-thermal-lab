#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_analytic.py
@brief How the Analytic (and the Lumped) model enter the one rule: the Analytic takes the rule's passive cell everywhere (one link, the series film on a one-layer board); the Lumped takes the construction through the FVM network it aggregates.
@details Question answered: the Analytic has no cells, so no mask: it sees one uniform sheet per layer. Is its one-layer treatment (the laminate in series with the bottom film, laminate.series_bottom_problem)
         the same as the rule's passive cell (n = 1)? Part A, uniform boards (full copper, where the mask is empty): Analytic, FVM with the rule (identical to the program) and the 3D reference on the one-layer
         board and two- and four-layer boards; the Analytic should agree with the FVM within the 0.3 to 1.3 % that `laminate.py` documents. Part B, partial copper (pads and windows of study_n_law):
         the Analytic of the program, the FVM with the rule, the reference, and (if the worktree of research/analytic-partial-copper is present at ANALYTIC_DEFECT, its lib/defect.py candidate with n =
         the rule's n and 4) so that the decision "the Analytic does not carry the nodes; it is warned" can be judged: how far the FVM with the rule moves from the Analytic once it is right, and
         whether the candidate still adds anything. Part C, the Lumped: lumped.Network is replaced by the rule's network (lumped aggregates the per-cell arrays and the extra links into rings), the
         error of the peak against the reference with the program's network and with the rule's. Output: out/analytic.json.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_analytic.py
"""

import _bootstrap  # noqa: F401  (import paths)

import os
import sys

import boards as BD
import gapnet as GN
import report as RP
import rule as RU
import runner as RN
from pcbthermal import SolverOptions, lumped, simulate

# The candidate of research/analytic-partial-copper is on another branch: its lib/defect.py is used when this path exists (not required)
ANALYTIC_DEFECT = os.environ.get("ANALYTIC_DEFECT", "")


def analytic_peak(spec, p, cell=1.0):
    """!
    @brief Peak rise of the program's Analytic model.
    @param spec A boards.Spec.
    @param p The Problem.
    @param cell Cell of the Analytic sampling grid in mm.
    @return float in K.
    """
    return float(simulate(p, SolverOptions(models=("analytic",), cell_mm=cell)).results["analytic"].t_max - p.board.ambient)


def lumped_peak(p, rule, cell=0.5):
    """!
    @brief Peak rise of the Lumped model on the network of a rule (the module's Network name is replaced for the call only).
    @param p The Problem.
    @param rule A rule.Rule.
    @param cell Cell in mm.
    @return float in K.
    """
    old = lumped.Network
    lumped.Network = lambda problem, nx, ny, assemble=False, with_blocks=True: GN.build(problem, 1e3 * problem.board.width / nx, rule, assemble=False)
    try:
        r = lumped.solve_steady(p, cell_mm=cell)
    finally:
        lumped.Network = old
    return float(r.t_max - p.board.ambient)


def main():
    """!
    @brief Parts A, B and C.
    @return None.
    """
    uniform = [BD.Spec("1L full", layers=1, shapes=[("full",)]), BD.Spec("2L 1.6 full", layers=2), BD.Spec("4L typical full", layers=4, stack="template")]
    partial = [s for s in BD.simple_set() if ("window 6" in s.name or "pad 10" in s.name) and "uniform" not in s.name]
    cand = None
    if ANALYTIC_DEFECT and os.path.isdir(ANALYTIC_DEFECT):
        sys.path.insert(0, ANALYTIC_DEFECT)
        import defect as cand                                                     # noqa: E402,F811  (optional, other branch)
    rows = []
    for tag, specs in (("A uniform", uniform), ("B partial", partial)):
        out = []
        for s in specs:
            p = BD.problem(s)
            ref = RN.reference(s)["max"]
            row = {"board": s.name, "Analytic": RN.err(analytic_peak(s, p), ref), "FVM program": RN.err(RN.fvm_peak(s, RU.PRESETS["program"], 0.5, p)["peak"], ref),
                   "FVM rule": RN.err(RN.fvm_peak(s, RU.Rule(), 0.5, p)["peak"], ref)}
            row["Analytic vs FVM rule"] = RN.err(analytic_peak(s, p), RN.fvm_peak(s, RU.Rule(), 0.5, p)["peak"])
            if cand is not None and tag.startswith("B"):
                try:
                    r4 = cand.solve(p, n_sub=4)                                    # the return value is read at the first run (a dict with the peak, or the peak)
                    row["candidate n=4"] = RN.err(float(r4["peak"] if isinstance(r4, dict) else r4), ref)
                except Exception as e:                                           # reported, not hidden
                    row["candidate n=4"] = type(e).__name__
            out.append(row)
        RP.table(out, list(out[0]), title=f"Part {tag}: error of the peak against the resolved face value, percent")
        rows.append((tag, out))
    out = []
    for s in partial:
        p = BD.problem(s)
        ref = RN.reference(s)["max"]
        out.append({"board": s.name, "Lumped program": RN.err(lumped_peak(p, RU.PRESETS["program"]), ref), "Lumped rule network": RN.err(lumped_peak(p, RU.Rule()), ref),
                    "FVM rule": RN.err(RN.fvm_peak(s, RU.Rule(), 0.5, p)["peak"], ref)})
    RP.table(out, list(out[0]), title="Part C: the Lumped model on the rule's network, percent")
    rows.append(("C lumped", out))
    RP.save("analytic", dict(rows))


if __name__ == "__main__":
    main()
