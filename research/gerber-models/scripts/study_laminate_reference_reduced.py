#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_laminate_reference_reduced.py
@brief Review R2, isolation of the shift of the program's pixel run against the independent 3D solution when the 2.4.5 laminate rule came in: is it the rule, or the way the study feeds the pixel conductances to the program?
@details `study_laminate_reference.py` replaces the copper-node conductance of every pixel (`net.S[0] = S * cover`) with the unreduced two-phase sheet of `faces.phases` (copper plus half of the whole
         laminate gap). With the laminate rule the copper node no longer carries that laminate (the rule puts it into sub-gap nodes below), so the replaced sheet counts the laminate twice in the plane.
         This study runs the program's pixel run four ways on the same seven windows and compares each with the independent 3D solution (`solve3d`, 0.2 mm pixels): (1) rule on, unreduced sheet (the
         main mode of the other study); (2) rule on, sheet reduced by the amount the rule took off a bare cell (`b_full - S_rule`), the way `copper.py` builds an imported layer; (3) rule off, two laminate
         nodes (the program before the rule), unreduced sheet; (4) rule off, one node (the coarsest); (5) the program's own route, one zone per run of copper pixels at 0.2 mm cells (rule on, nothing overridden). Printed: the heater mean rise and the error against 3D per window and the mean.
         Run from the repository root: .venv-research/bin/python research/gerber-models/scripts/study_laminate_reference_reduced.py (about 2 minutes, 4.5 GB peak because of the 3D solves).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import numpy as np

import study_laminate_reference as sr
import conduction as cd  # noqa: F401
import faces
import windows
from pcbthermal import fvm, laminate


def reduction(p, n):
    """!
    @brief The sheet conductance (W/K per cell) that the laminate rule takes off the copper node of a bare cell.
    @param p Problem (one layer, no zones).
    @param n Cells per side.
    @return float W/K per cell.
    """
    a, b = faces.phases(p, 0)
    net = fvm.Network(p, n, n, assemble=False)
    # the rule reduces the cell by the laminate it moves into sub-gap nodes; the cell sheet before the rule is b_full of the whole slab
    full = p.board.layer_laminate()[0][0] * p.board.slab_thicknesses()[0]
    return float(full - net.S[0][n // 2, n // 2])


def zones_run(m):
    """!
    @brief The program's own route for a copper mask: one zone per run of copper pixels (fill 1), so that the cell fill goes through the laminate rule as in every drawn board.
    @param m Boolean copper mask at 0.2 mm, rows from the bottom.
    @return float Heater mean rise (K) of the program's FVM at 0.2 mm cells.
    """
    from pcbthermal import SolverOptions, simulate
    from pcbthermal.analysis import heater_stats
    p = sr.problem()
    pix = sr.PIX
    for i in range(m.shape[0]):
        edges = np.flatnonzero(np.diff(np.concatenate([[0], m[i].astype(int), [0]])))
        for a, b in zip(edges[::2], edges[1::2]):
            p.add_zone(1, rect=(a * pix, i * pix, b * pix, (i + 1) * pix), fill=1.0)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=pix))
    return heater_stats(sim.results["fvm"], p)[0]["t_mean"] - p.board.ambient


def main():
    """!
    @brief Run the four variants on the seven windows and print the errors against 3D.
    @return None.
    """
    masks, meta = windows.load()
    rows = []
    for bname in sr.BOARDS if hasattr(sr, "BOARDS") else ("storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz"):
        i = [k for k, mm in enumerate(meta) if mm[0] == bname][0]
        m01 = masks[i][::-1]
        m = m01.reshape(m01.shape[0] // 2, 2, m01.shape[1] // 2, 2).mean(axis=(1, 3)) >= 0.5
        t3 = sr.solve3d(m)
        p = sr.problem()
        a, b = faces.phases(p, 0)
        S = np.where(m, a, b)
        n = S.shape[0]
        dS = reduction(p, n)
        v1 = sr.program_fine(p, S)
        v2 = sr.program_fine(p, S - dS)
        keep, keep_n = laminate.uses_rule, laminate.LAMINATE_NODES
        laminate.uses_rule = lambda problem: False
        try:
            laminate.LAMINATE_NODES = 2
            p2 = sr.problem()
            a2, b2 = faces.phases(p2, 0)
            v3 = sr.program_fine(p2, np.where(m, a2, b2))
            laminate.LAMINATE_NODES = 1
            p1 = sr.problem()
            a1, b1 = faces.phases(p1, 0)
            v4 = sr.program_fine(p1, np.where(m, a1, b1))
        finally:
            laminate.uses_rule, laminate.LAMINATE_NODES = keep, keep_n
        v5 = zones_run(m)
        err = [100 * (v / t3 - 1) for v in (v1, v2, v3, v4, v5)]
        rows.append(err)
        print(f"{bname:8s} dS {dS:.3e} W/K | 3D {t3:.2f} K | rule/unreduced {v1:.2f} ({err[0]:+.1f} %) | rule/reduced {v2:.2f} ({err[1]:+.1f} %) | "
              f"2 nodes {v3:.2f} ({err[2]:+.1f} %) | 1 node {v4:.2f} ({err[3]:+.1f} %) | zones {v5:.2f} ({err[4]:+.1f} %)", flush=True)
    r = np.array(rows)
    print("mean error against 3D (percent): rule/unreduced %+.1f, rule/reduced %+.1f, 2 nodes %+.1f, 1 node %+.1f, zones %+.1f" % tuple(r.mean(axis=0)))


if __name__ == "__main__":
    main()
