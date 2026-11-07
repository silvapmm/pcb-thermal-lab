#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_boards_unchanged.py
@brief Does the proposed first ring move the boards on which the Lumped was validated for vias (the family and the held-out boards of lumped-via-groups / lumped-zones-adoption)?
@details Builds every spec of `study_family.specs()` and `study_holdout.holdout_specs()` (research/lumped-via-groups), with and without vias, and runs the Lumped at 0.5 mm with the program and
         with the proposal. The via effect E = T_max(no vias) - T_max(vias) and T_max itself are compared: no reference is needed, the question is whether the proposal changes the numbers the earlier
         studies measured against their references (they are 30 mm boards with sources of at most 20 mm: 0.04 rho_max is under 1.5 cells there). Prints the largest differences.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_via_boards_unchanged.py (a minute).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "lib"))
for sub in ("lumped-via-groups/lib", "lumped-via-groups/scripts", "lumped-analytic-vias/lib", "lumped-analytic-vias/scripts", "point-via-convergence/lib"):
    sys.path.insert(0, str(RESEARCH / sub))

import runner as R  # noqa: E402
import refs  # noqa: E402
import harness as hz  # noqa: E402
import program_cases as pc  # noqa: E402
import study_family  # noqa: E402
import study_holdout  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402


def tmax(p, cand, cell=0.5):
    """!
    @brief Lumped maximum temperature with a candidate.
    @param p Problem.
    @param cand Key of runner.CANDIDATES.
    @param cell Cell in mm.
    @return float degC.
    """
    R.LL.configure(*R.CANDIDATES[cand])
    return simulate(p, SolverOptions(models=("lumped",), cell_mm=cell)).results["lumped"].t_max


def main():
    """!
    @brief Run and print the differences.
    @return None.
    """
    pc.load_libraries()
    specs = [(f"family {i}", s) for i, s in enumerate(study_family.specs(False))] + list(study_holdout.holdout_specs())
    worst_t, worst_e, n_changed = 0.0, 0.0, 0
    for label, spec in specs:
        p = refs.make_problem(spec)
        q0 = hz.no_vias(p)
        a1, b1 = tmax(p, "program"), tmax(p, R.PROPOSAL)
        a0, b0 = tmax(q0, "program"), tmax(q0, R.PROPOSAL)
        dt, de = max(abs(b1 - a1), abs(b0 - a0)), abs((a0 - a1) - (b0 - b1))
        worst_t, worst_e = max(worst_t, dt), max(worst_e, de)
        n_changed += dt > 1e-9
        if dt > 1e-9:
            print(f"{label}: T_max {a1:.4f} -> {b1:.4f} (no vias {a0:.4f} -> {b0:.4f})")
    print(f"{len(specs)} boards; boards whose number moves: {n_changed}; largest change of T_max {worst_t:.2e} K; largest change of the via effect {worst_e:.2e} K")


if __name__ == "__main__":
    main()
