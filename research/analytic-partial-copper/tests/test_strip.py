#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_strip.py
@brief The independent resolved 3D solver at a pad edge against the closed form of a heated strip with a step in the sheet conductance.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))

import pads as P                                                             # noqa: E402,F401  (puts the bare-spot lib on the path)
import resolved3d as r3                                                      # noqa: E402
import strip                                                                 # noqa: E402


def numeric_vs_closed(dx_mm):
    """!
    @brief The strip in the 3D solver (a one-cell-wide column, copper in |x| < a, thin laminate with a large through conductivity) and the closed form at the same point.
    @param dx_mm Cell size in mm.
    @return Tuple (rise of the cell next to the centre in the solver, closed form at that cell centre).
    """
    dx = dx_mm * 1e-3
    a, half = 5e-3, 40e-3                       # half width of the strip, half length of the quadrant
    nx = int(round(half / dx))
    xs = (np.arange(nx) + 0.5) * dx
    t_cu, t_lam, kcu, kxy, kz = 35e-6, 50e-6, 385.0, 0.9, 100.0
    f = (xs < a).astype(float)[None, :]
    slabs = [(t_cu, kxy + f * (kcu - kxy), kz + f * (kcu - kz), 1), (t_lam, kxy, kz, 4)]
    h, q = 20.0, 1.0e4                          # film on each face, flux over the strip
    res = r3.solve(dx, nx, 1, slabs, (0.0, 0.0, a, dx), q * a * dx, h, h)
    S1, S2 = kcu * t_cu + kxy * t_lam, kxy * (t_cu + t_lam)
    return float(res["surf"][0, 0]), float(strip.strip_profile(xs[0], q, a, S1, S2, 2 * h))


def test_resolved_solver_reproduces_the_strip_with_a_step_in_the_sheet():
    """!
    @brief The rise next to the centre of the 3D solver is within 0.5 % of the closed form of the strip with a step in the sheet conductance, and the error falls with the cell.
    @return None.
    """
    errs = []
    for dx in (0.2, 0.1):
        num, ref = numeric_vs_closed(dx)
        errs.append(abs(num / ref - 1))
    assert errs[1] < 5e-3
    assert errs[1] < errs[0]


def test_strip_limits():
    """!
    @brief The closed form tends to the infinite fin when the two sheets are equal and to q / h when the strip is wide and the outside weak.
    @return None.
    """
    q, h, S = 1.0e4, 40.0, 0.01
    m = np.sqrt(h / S)
    assert abs(strip.strip_peak(q, 0.05, S, S, h) / ((q / h) * (1 - np.exp(-m * 0.05))) - 1) < 1e-9
    assert abs(strip.strip_peak(q, 2.0, S, 0.1 * S, h) / (q / h) - 1) < 1e-6
