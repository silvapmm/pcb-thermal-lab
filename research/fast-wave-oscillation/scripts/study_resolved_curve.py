#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_resolved_curve.py
@brief Review question 6: when the decision says 'resolve', is the ripple of the program's resolved curve also too small, what would a resolved fast wave cost, and which
       correction of the curve is the cheapest consistent one?

@details (a) The 20 Hz, 30 %, 10 W wave on a 10 mm part of a 2-layer full-copper board, resolved on purpose (budget 0), with profiles.run_fvm and run_fdm: the ripple of the
heater's curve in the last window against the decision's oscillation and the reviewer's 3D reference (lib/review_rect3d.py). (b) The plan of the run of the example board
when U1 (100 Hz) is resolved, as the E3 floor would make it (profiles.plan_run, limit 200 000 steps). (c) On a 1D column of the part's area (the reviewer's own chain, no
code of the author), the swing of the program's node structure with n graded laminate sub-gaps per gap against the resolved column, from 1 Hz to 1 kHz: the cost of a
correction of the curve by nodes. Run from the repository root (about 1 minute):
`QT_QPA_PLATFORM=offscreen .venv/bin/python research/fast-wave-oscillation/scripts/study_resolved_curve.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import numpy as np                                                   # noqa: E402
import scipy.sparse as sp                                            # noqa: E402

import review_rect3d as R                                            # noqa: E402
from pcbthermal import profiles                                      # noqa: E402
from pcbthermal.model import Problem, SquareWave                     # noqa: E402


class Chain:
    """!
    @brief A 1D column of nodes (capacities and links) with the transfer method that review_rect3d.Response needs.
    """

    def __init__(self, caps, links, g_top, g_bot, src=0):
        """!
        @brief Build K and C.
        @param caps Capacities (J/K) top down.
        @param links Conductances between consecutive nodes (W/K).
        @param g_top Conductance of the top node to the ambient (W/K).
        @param g_bot Conductance of the bottom node to the ambient (W/K).
        @param src Node that receives the power and is read.
        """
        n = len(caps)
        d = np.zeros(n)
        d[:-1] += links
        d[1:] += links
        d[0] += g_top
        d[-1] += g_bot
        self.K = (sp.diags(d) - sp.diags(links, 1) - sp.diags(links, -1)).tocsc()
        self.C = np.asarray(caps, dtype=float)
        self.q = np.zeros(n)
        self.q[src] = 1.0
        self.read = np.array([src])
        self.read_xy = np.zeros((1, 2))

    def transfer(self, freqs):
        """!
        @brief H(f) of the source node.
        @param freqs Frequencies (Hz).
        @return Array (len(freqs), 1).
        """
        out = np.empty((len(freqs), 1), dtype=complex)
        for i, f in enumerate(freqs):
            A = (self.K + 2j * np.pi * f * sp.diags(self.C)).toarray()
            out[i] = np.linalg.solve(A, self.q)[self.read]
        return out


def column(area, h, cells_cu, gap_cells, node_holds_half=True, t_cu=35e-6, thickness=1.6e-3):
    """!
    @brief A 2-layer column: the copper layers in cells_cu cells each, the gap in the given cells (widths, top down).
    @param area Area (m2).
    @param h Face coefficient of both faces.
    @param cells_cu Cells per copper layer (1 = one copper node).
    @param gap_cells Widths of the laminate cells of the gap (m).
    @param node_holds_half True: the program's rule, the copper node also holds half of the next laminate cell and is linked to the next node through it
           (laminate nodes at the cell boundaries); False: cell-centred laminate cells.
    @param t_cu Copper thickness (m).
    @param thickness Board thickness (m).
    @return Chain.
    """
    kcu, ccu, kz, cl = 385.0, 8960.0 * 385.0, 0.3, 1850.0 * 900.0
    g = np.asarray(gap_cells, dtype=float)
    if node_holds_half:
        # Nodes: copper(top) | laminate nodes at the inner boundaries | copper(bottom); every laminate cell splits its capacity between its two nodes
        nb = len(g) + 1
        caps = np.zeros(nb)
        caps[:-1] += 0.5 * g * cl * area
        caps[1:] += 0.5 * g * cl * area
        caps[0] += t_cu * ccu * area
        caps[-1] += t_cu * ccu * area
        links = kz * area / g
        return Chain(caps, links, h * area, h * area)
    dz = np.concatenate([[t_cu / cells_cu] * cells_cu, g, [t_cu / cells_cu] * cells_cu])
    k = np.concatenate([[kcu] * cells_cu, [kz] * len(g), [kcu] * cells_cu])
    c = np.concatenate([[ccu] * cells_cu, [cl] * len(g), [ccu] * cells_cu])
    caps = c * dz * area
    links = area / (0.5 * dz[:-1] / k[:-1] + 0.5 * dz[1:] / k[1:])
    return Chain(caps, links, h * area / (1 + h * 0.5 * dz[0] / k[0]), h * area / (1 + h * 0.5 * dz[-1] / k[-1]))


def graded(d, n, first):
    """!
    @brief n cells across a gap d, symmetric, growing geometrically from `first` at each face (n even), or equal cells when first is None.
    @param d Gap (m).
    @param n Cells.
    @param first First width (m) or None.
    @return Widths.
    """
    if first is None or n < 2:
        return np.full(n, d / n)
    m = n // 2
    lo, hi = 1.0 + 1e-12, 50.0
    for _ in range(200):
        r = 0.5 * (lo + hi)
        s = first * (r ** m - 1) / (r - 1)
        lo, hi = (r, hi) if s < 0.5 * d else (lo, r)
    half = first * r ** np.arange(m)
    half *= 0.5 * d / half.sum()
    return np.concatenate([half, half[::-1]])


def main():
    """!
    @brief Print the three parts.
    @return None.
    """
    # (a) The resolved run of the program
    p = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    p.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="fast", profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    opts = profiles.ProfileOptions(threshold_c=0.0)
    for model, step, run in (("fvm", profiles.step_response_fvm, profiles.run_fvm), ("fdm", profiles.step_response_fdm, profiles.run_fdm)):
        resp = step(p, 1.0)
        dec = profiles.decide(p, resp, 0.0)
        res = run(p, dec, opts, 1.0)
        th = np.asarray(res.t_heaters)[0]
        print(f"(a) {model}: decision {dec[0].regime}, oscillation {dec[0].oscillation:.3f} K; resolved curve ripple {th.max() - th.min():.3f} K "
              f"(dt {res.dt * 1e3:.2f} ms, {res.steps} steps, theta {opts.theta})")
        res2 = run(p, dec, profiles.ProfileOptions(threshold_c=0.0, theta=0.5), 1.0)
        th2 = np.asarray(res2.t_heaters)[0]
        print(f"    {model} Crank-Nicolson: ripple {th2.max() - th2.min():.3f} K")
    ref = R.Response(R.Reference(R.Board(layers=2), R.Case(part=(25e-3, 15e-3, 35e-3, 25e-3)), quarter=True))
    print(f"    reference: {10 * ref.swing(0.05, 0.3):.3f} K")
    # (b) The plan of the example board with U1 resolved
    import test_profiles as tp
    q = tp.example_with_profiles(100.0)
    resp = profiles.step_response_fvm(q, 2.0)
    dec = profiles.decide(q, resp, 1.0)
    for d in dec:
        d.regime = "resolved"
    try:
        plan = profiles.plan_run(q, dec, profiles.ProfileOptions())
        print(f"(b) example board, U1 and U2 resolved: window {plan['window']} s, {plan['n_per']} steps per window, {plan['steps']} steps")
    except profiles.ProfileError as exc:
        print(f"(b) example board, U1 and U2 resolved: refused: {exc}")
    # (c) The cost of a correction by nodes, 1D column of a 10 mm part, h 10, duty 30 %
    area, gap = 1e-4, 1.6e-3 - 2 * 35e-6
    exact = R.Response(column(area, 10.0, 6, graded(gap, 80, 0.3e-6), node_holds_half=False))
    freqs = (1.0, 10.0, 20.0, 100.0, 1000.0)
    ex = [exact.swing(1 / f, 0.3) for f in freqs]
    print("(c) 1D column, program structure with n laminate sub-gaps per gap (node holds half of the first): swing / resolved column at " + ", ".join(f"{f:g}" for f in freqs) + " Hz")
    print("    resolved column K/W: " + ", ".join(f"{v:.4f}" for v in ex))
    for n, first in ((1, None), (2, None), (4, None), (16, None), (4, 5e-6), (4, 20e-6), (6, 5e-6), (8, 2e-6), (8, 5e-6)):
        ch = R.Response(column(area, 10.0, 1, graded(gap, n, first)))
        print(f"    n={n:2d} first={'equal' if first is None else f'{first * 1e6:.0f} um':>6s}: " + ", ".join(f"{ch.swing(1 / f, 0.3) / e:.3f}" for f, e in zip(freqs, ex)))


if __name__ == "__main__":
    main()
