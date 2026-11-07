#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_small_cells.py
@brief The small-cell question for the steady and implicit layered FVM: what happens to the matrix, the energy balance and the answer when the edge cell has a tiny cover? (README 4)
@details A 20 mm board in a 30 mm box (1 mm cells) whose left edge is moved so that the edge column has the cover c from 0.002 to 1; the part (3 mm, 2 W, h_side 200) sits 2 mm
         from the edge. For every scheme: the hottest temperature, the energy balance (heat to the air over the power), the symmetry and the sign pattern of the matrix
         (positive off-diagonals, smallest diagonal dominance), the extreme eigenvalues of the Jacobi-scaled matrix (the conditioning the iterative solvers see), whether the
         symmetric LU of `fvm.lu_factor` accepted it (no warning logged), and the largest link relative to a whole pair. The error against the board at a cell of 1/32 mm
         (edge on a grid line) is printed for the covers that are a multiple of 1/32. A last table gives the difference program - aperture at c = 0.02, 0.05, 0.1 for
         h_side 10, 50, 200 and 2000 (the size of the sliver anomaly).
Usage: .venv/bin/python research/cut-cell-links/scripts/study_small_cells.py   (from the repository root; about 2 minutes, below 0.5 GB)
"""

import json
import logging
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)
OUT = os.path.join(os.path.dirname(HERE), "out")

import cutlinks as cl         # noqa: E402
from pcbthermal import Problem, fvm   # noqa: E402

COVERS = [0.002, 0.005, 0.01, 0.02, 1 / 32, 0.0625, 0.125, 0.25, 0.5, 0.75, 1.0]


def board(c, h_side=200.0):
    """!
    @brief The board with the edge column [5, 6] mm covered by the fraction c.
    @param c Cover of the edge column.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    e = 6.0 - c
    p = Problem.new(30, 30, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0, 13.5, 11.0, 16.5), name="U")
    p.set_outline([[e, 5], [25, 5], [25, 25], [e, 25]])
    return p


class _Count(logging.Handler):
    """!
    @brief Counts the warnings of `pcbthermal.fvm` (the fallback of the symmetric LU logs one).
    """

    def __init__(self):
        """!
        @brief Start at zero.
        @return None.
        """
        super().__init__(level=logging.WARNING)
        self.n = 0

    def emit(self, record):
        """!
        @brief Count a record.
        @param record Log record.
        @return None.
        """
        self.n += 1


def main():
    """!
    @brief Print the table and save `out/small_cells.json`.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    cnt = _Count()
    logging.getLogger("pcbthermal.fvm").addHandler(cnt)
    out = {}
    print("| cover c | scheme | T max (degC) | heat/power | asym | pos. off-diag | min dominance | lam_min | cond (Jacobi) | sym LU fallbacks | error vs 1/32 mm (K) |")
    print("| --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for c in COVERS:
        ref = None
        if abs(c * 32 - round(c * 32)) < 1e-9:
            ref = cl.tmax(board(c), 1 / 32, "program")
        for s in cl.SCHEMES:
            p = board(c)
            n0 = cnt.n
            r = cl.solve(p, 1.0, s)
            fall = cnt.n - n0
            q = sum(r.power_out.values()) / 2.0
            m = cl.matrix_checks(board(c), 1.0, s)
            err = f"{r.t_max - ref:+.3f}" if ref is not None else "-"
            out[f"{c:g}|{s}"] = dict(tmax=float(r.t_max), balance=q, **m, fallbacks=fall, err=None if ref is None else float(r.t_max - ref))
            print(f"| {c:g} | {s} | {r.t_max:.3f} | {q:.6f} | {m['asym']:.1e} | {m['pos_offdiag']} | {m['min_diag_dominance']:.2e} | {m['lam_min']:.2e} | {m['cond']:.1e} | {fall} | {err} |", flush=True)
    # The size of the sliver anomaly against h_side (README 4; added by the review: these numbers were quoted without a script)
    print("\n| c | " + " | ".join(f"program - aperture at h_side {h:g} (K)" for h in (10, 50, 200, 2000)) + " |\n| --: | --: | --: | --: | --: |")
    for c in (0.02, 0.05, 0.1):
        row = []
        for h in (10.0, 50.0, 200.0, 2000.0):
            d = cl.tmax(board(c, h), 1.0, "program") - cl.tmax(board(c, h), 1.0, "aperture")
            out[f"anomaly|{c:g}|{h:g}"] = float(d)
            row.append(f"{d:+.2f}")
        print(f"| {c:g} | " + " | ".join(row) + " |", flush=True)
    with open(os.path.join(OUT, "small_cells.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
