#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_sheets2d_lattice.py
@brief Tests of the independent pieces of research/point-via-convergence/lib: the lattice kernel, the fine-grid sheet solver and the via weights.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import lattice                                                              # noqa: E402
import sheets2d                                                             # noqa: E402
import viakernel as vk                                                      # noqa: E402


def test_kernel_exact_values():
    """!
    @brief The table reproduces the known values a(1,0)=1, a(1,1)=4/pi, a(2,0)=4-8/pi, a(2,1)=8/pi-1 and the diagonal sum.
    @return None.
    """
    a = lattice.kernel_table(6)
    assert a[1, 0] == 1.0
    assert abs(a[1, 1] - 4 / math.pi) < 1e-12
    assert abs(a[2, 0] - (4 - 8 / math.pi)) < 1e-12
    assert abs(a[2, 1] - (8 / math.pi - 1)) < 1e-12
    assert abs(a[3, 3] - 4 / math.pi * (1 + 1 / 3 + 1 / 5)) < 1e-12


def test_kernel_matches_finite_solve_and_asymptote():
    """!
    @brief The point-sink radius from a finite lattice solve equals exp(-(gamma + 1.5 ln 2)) and the kernel is harmonic away from the origin.
    @return None.
    """
    r = lattice.point_sink_solve(150)["r_eq"]
    assert abs(r - lattice.R_EQ_EXACT) < 5e-4                                # 0.19851
    assert abs(lattice.R_EQ_EXACT - 0.19851) < 1e-5
    a = lattice.kernel_table(12)
    for x, y in ((3, 2), (5, 5), (8, 3), (11, 4)):
        assert abs(a[x + 1, y] + a[x - 1, y] + a[x, y + 1] + a[x, y - 1] - 4 * a[x, y]) < 1e-6
    assert abs(lattice.a_of(12, 0) - ((2 / math.pi) * math.log(12) + lattice.KAPPA)) < 2e-3


def test_effective_radius_of_a_point_and_of_a_ring():
    """!
    @brief A point has the radius 0.1985 dx; four equal quarters on the corners of a cell have 0.72 dx (computed by hand: E = 0.818).
    @return None.
    """
    assert abs(lattice.effective_radius([(0, 0)], [1.0]) - lattice.R_EQ_EXACT) < 1e-12
    r4 = lattice.effective_radius([(0, 0), (1, 0), (0, 1), (1, 1)], [0.25] * 4)
    e = (8 * 1.0 + 4 * 4 / math.pi) / 16
    assert abs(r4 - math.exp(math.pi / 2 * (e - lattice.KAPPA))) < 1e-12
    assert abs(r4 - 0.718) < 2e-3


def test_disc_fraction_area():
    """!
    @brief The area of the disc on the grid is pi a^2 within the sampling error.
    @return None.
    """
    f = sheets2d.disc_fraction(1.0, 1.0, 0.3, 0.05, 40, 40, sub=16)
    assert abs(f.sum() * 0.05 ** 2 - math.pi * 0.3 ** 2) / (math.pi * 0.09) < 5e-3


def test_sheet_solver_series_circuit_and_energy():
    """!
    @brief Three sheets with uniform temperature across the cell: the series circuit top to ambient, and the energy balance.
    @return None.
    """
    n = 6
    S = np.full((3, n, n), 1.0)
    gz = np.full((2, n, n), 0.5)
    g_amb = np.zeros((3, n, n))
    g_amb[2] = 0.25
    Q = np.zeros((3, n, n))
    Q[0] = 1.0 / n ** 2
    T = sheets2d.solve(S, gz, g_amb, Q, 1.0)
    r_cell = 1 / 0.5 + 1 / 0.5 + 1 / 0.25                                     # per cell: two vertical links and the film
    assert np.allclose(T[0], T[0].mean())
    assert abs(T[0].mean() - r_cell * 1.0 / n ** 2) < 1e-9
    assert abs((g_amb * T).sum() - Q.sum()) < 1e-9


def test_lone_via_against_bessel_closed_form():
    """!
    @brief A fixed-temperature via of radius 0.4 mm in a sheet with loss (lambda = 2 mm): the heat it takes, fine grid against the K0 closed form (quarter domain, via at the corner).
    @return None.
    """
    s, h, a, q = 0.04, 1.0e4, 0.4e-3, 1000.0
    ex = sheets2d.lone_via_exact(s, h, a, q)
    errs = []
    for dx in (0.05e-3, 0.025e-3):
        n = int(round(10 * ex["lam"] / dx))                                  # the field has decayed by e^-10 at the far border
        S = np.full((1, n, n), s)
        g = np.full((1, n, n), h * dx * dx)
        # cells whose centre is inside the circle are held at the ambient (the via is a cylinder at the ambient temperature)
        xs = (np.arange(n) + 0.5) * dx
        fixed = ((xs[None, :] ** 2 + xs[:, None] ** 2) <= a ** 2)[None]
        Q = np.full((1, n, n), q * dx * dx)
        T = sheets2d.solve(S, np.zeros((0, n, n)), g, Q, dx, fixed=fixed)
        i_quarter = float(q * dx * dx * (~fixed).sum() - (h * dx * dx * T[0]).sum())    # heat that reaches the via: source of the sheet minus loss
        errs.append(abs(4 * i_quarter - ex["I"]) / ex["I"])
    assert errs[-1] < 0.02 and errs[-1] <= errs[0] + 1e-3, errs


def test_kron_barrel_series_and_parallel():
    """!
    @brief Two layers, one gap: the reduced link is the series 1/(1/Gc + 1/Gv + 1/Gc); a copper-like barrel (huge Gv) leaves Gc/2.
    @return None.
    """
    g = vk.kron_barrel([2.0], [4.0, 4.0])
    assert abs(g[0, 1] - 1.0 / (1 / 4 + 1 / 2 + 1 / 4)) < 1e-9
    g = vk.kron_barrel([1e12], [4.0, 4.0])
    assert abs(g[0, 1] - 2.0) < 1e-4
    g3 = vk.kron_barrel([1e12, 1e12], [1.0, 2.0, 3.0])                        # equipotential barrel: star-mesh G_ab = Ga Gb / sum
    assert abs(g3[0, 2] - 1.0 * 3.0 / 6.0) < 1e-4 and abs(g3[0, 1] - 1.0 * 2.0 / 6.0) < 1e-4


def test_tuned_weights_reach_the_via_radius():
    """!
    @brief The tuned weights have the effective radius of the via, for a via on a cell centre, on an edge and on a corner, and a well is requested for a small via on a coarse grid.
    @return None.
    """
    r_via = 0.15e-3
    for dx in (0.5e-3, 0.25e-3, 0.125e-3, 0.0625e-3):
        for (cx, cy) in ((10.25e-3, 10.25e-3), (10.5e-3, 10.25e-3), (10.5e-3, 10.5e-3), (10.37e-3, 10.11e-3)):
            w = vk.tuned_weights(cx, cy, r_via, dx)
            assert w is not None
            assert abs(vk.effective_radius(w, dx) - r_via) / r_via < 0.02, (dx, cx, cy)
    assert vk.tuned_weights(10e-3, 10e-3, 0.15e-3, 1.0e-3) is None
