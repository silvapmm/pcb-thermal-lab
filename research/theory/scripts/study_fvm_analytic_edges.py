#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fvm_analytic_edges.py
@brief Why the Analytic model is 0.3 to 1 % above the FVM on the uniform boards: the FVM mesh error, or the edges the series leaves insulated?

The theory notes (topic 37) and `docs/validation.md` section 4 said that the two models agree "within the FVM's mesh error (0.2 to 1 %)".
This study measures it: the Analytic model against the FVM at 1, 0.5 and 0.25 mm on the uniform scenarios of `docs/validation.md` section 2,
once with the default edge coefficient (`h_side` 10 W/m2K, which the Analytic series cannot represent) and once with insulated edges in both.

Usage (from the repository root, under a minute): .venv/bin/python research/theory/scripts/study_fvm_analytic_edges.py
"""

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "models-comparison", "scripts"))

from pcbthermal import analytic, fvm  # noqa: E402
import accuracy_study                 # noqa: E402

CELLS = (1.0, 0.5, 0.25)              # FVM cell sizes in mm: 0.25 mm is the converged value of docs/validation.md 2.1


def uniform_cases():
    """!
    @brief The scenarios of docs/validation.md section 2 on which the Analytic model is exact apart from the edges (uniform copper, no vias, no heatsink).
    @return List of (name, Problem).
    """
    keep = ("reference board (centred", "example, uniform", "example, only U1, uniform", "reference board, 8 layers")
    return [(n, p) for n, p in accuracy_study.cases() if n.startswith(keep)]


def main():
    """!
    @brief Print the rise of the Analytic model and its difference from the FVM at three cell sizes, with and without the edge coefficient.
    @return None.
    """
    print("| Scenario | Edges | Analytic rise [K] | FVM 1 mm | FVM 0.5 mm | FVM 0.25 mm |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    for name, p in uniform_cases():
        for label in ("h_side 10 W/m2K", "insulated"):
            q = copy.deepcopy(p)
            if label == "insulated":
                q.board.h_side = None                       # Insulated edges: the boundary condition of the cosine series
            amb = q.board.ambient
            a = analytic.solve_steady(q).t_max - amb        # Rise of the hottest point in K
            cols = []
            for c in CELLS:
                f = fvm.solve_steady(q, c).t_max - amb
                cols.append(f"{f:.3f} ({100.0 * (a / f - 1.0):+.2f} %)")   # Analytic against this FVM, on the rise
            print(f"| {name} | {label} | {a:.3f} | " + " | ".join(cols) + " |", flush=True)


if __name__ == "__main__":
    main()
