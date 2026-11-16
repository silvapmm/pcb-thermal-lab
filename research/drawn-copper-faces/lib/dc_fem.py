#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file dc_fem.py
@brief The finite-element reference of the boards of `dc_cases.py`: the copper RESOLVED (every rectangle edge a mesh line, not volume-mixed), 12 elements per laminate gap.
@details Uses the independent hexahedral solver of `research/independent-fem-edge/lib` (scikit-fem, pyamg: run it with the interpreter of the folder's git-ignored scratch environment, not
         with the program's `.venv`). Hatched copper (fill below 1) cannot be resolved and is refused.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import board                                                              # noqa: E402
import cases                                                              # noqa: E402
import mesh2d                                                             # noqa: E402
sys.path.insert(0, HERE)
import dc_cases as D                                                      # noqa: E402


def fem_board(c, hf):
    """!
    @brief The finite-element board of a case.
    @param c Case dict of `dc_cases.case`.
    @param hf Plan element size in mm, uniform over the whole board.
    @return board.Board.
    @throws ValueError For hatched copper.
    """
    if any(f < 1.0 for f in c["fill"]):
        raise ValueError("hatched copper cannot be resolved")
    brk = {0.0, D.A, 8.0, 12.0}
    for rs in c["copper"]:
        for (x0, y0, x1, y1) in rs:
            brk.update((x0, x1, y0, y1))
    brk = sorted(brk)
    xn = cases.axis(D.A, brk, [(0.0, D.A)], hf, 1.3, hf)
    plan = mesh2d.tensor(xn, xn)
    cu = []
    for rs in c["copper"]:
        if len(rs) == 1 and rs[0] == (0.0, 0.0, D.A, D.A):
            cu.append(None)                                              # full copper to the wall
        else:
            cu.append([cases.rect(*r) for r in rs])
    return board.Board(plan, c["layers"], board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=12, h_top=10.0, h_bottom=10.0, h_side=c["h_side"], copper=cu,
                       heaters=[(cases.rect(8, 8, 12, 12), 1.0)])


def solve(c, hf, direct_max=30000):
    """!
    @brief Solve a case (2 GB guard on the estimated memory).
    @param c Case.
    @param hf Plan size in mm.
    @param direct_max Largest node count for the direct solver.
    @return dict heater_mean, tmax, balance, n, solver, peak_gb or None if refused.
    """
    b = fem_board(c, hf)
    m, _ = b.build()
    n = m.nodes.shape[0]
    est = n * (46000.0 if n <= 30000 else 8500.0) / 1e9
    if est > 2.0:
        return None
    r = b.solve(direct_max=direct_max)
    return {k: r[k] for k in ("heater_mean", "tmax", "balance", "n", "solver", "peak_gb")}
