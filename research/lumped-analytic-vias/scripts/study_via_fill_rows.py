#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_fill_rows.py
@brief The rows of research/via-fill section 4.5 (the example board, every fill and the two limits) for the Lumped and Analytic models of the program and of the patches.
@details Change of the maximum temperature against the open via, in K, as in via-fill 4.5: epoxy resin, conductive paste, copper and no vias (the nine vias removed); the perfect-via limit of via-fill is not repeated. The FVM at 0.5 and 1 mm and the FVM with the corrected via treatment (`FVM_fix`, 0.25 mm) are printed for scale. Also the maximum temperature of
         the example board with open vias for every model, before and after: what the validation tables would show.
Usage: python research/lumped-analytic-vias/scripts/study_via_fill_rows.py   (from the repository root; about 2 minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
from pcbthermal.examples import example_board                                # noqa: E402

COLUMNS = [("FVM 1", "FVM", 1.0), ("FVM 0.5", "FVM", 0.5), ("FVM_fix 0.25", "FVM_fix", 0.25), ("Lumped program", "L_prog", 0.5), ("Lumped patched", "L_grp0", 0.5),
           ("Analytic program", "A_prog", 0.5), ("Analytic patched", "A_fin", 0.5)]


def board(fill=None, none=False):
    """!
    @brief The example board with its vias changed.
    @param fill Fill conductivity of every via in W/mK (None keeps open).
    @param none True removes the vias.
    @return Problem.
    """
    prob = example_board()
    if none:
        prob.vias = []
        return prob
    for v in prob.vias:
        if fill is not None:
            v.fill_k = fill
    return prob


def t_max(prob, key, cell):
    """!
    @brief Maximum temperature of a variant on a problem.
    @param prob Problem.
    @param key Variant key of harness.VARIANTS.
    @param cell Cell in mm.
    @return float Maximum temperature in degC.
    """
    model, ctx = hz.VARIANTS[key]
    with ctx():
        return pc.max_rise(prob, model, cell) + prob.board.ambient


def main():
    """!
    @brief Print the table.
    @return None.
    """
    pc.load_libraries()
    rows = [("open", board()), ("epoxy resin", board(0.3)), ("conductive paste", board(8.0)), ("copper", board(385.0)), ("no vias", board(none=True))]
    base = {c[0]: t_max(rows[0][1], c[1], c[2]) for c in COLUMNS}
    print("Maximum temperature of the example board with open vias (degC):\n")
    print("| " + " | ".join(c[0] for c in COLUMNS) + " |\n|" + " --: |" * len(COLUMNS))
    print("| " + " | ".join(f"{base[c[0]]:.2f}" for c in COLUMNS) + " |\n")
    print("Change against the open via (K):\n")
    print("| case | " + " | ".join(c[0] for c in COLUMNS) + " |\n| :-- |" + " --: |" * len(COLUMNS))
    for name, prob in rows[1:]:
        print(f"| {name} | " + " | ".join(f"{t_max(prob, c[1], c[2]) - base[c[0]]:+.2f}" for c in COLUMNS) + " |")


if __name__ == "__main__":
    main()
