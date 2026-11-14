#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_transient.py
@brief Checks (i) to (v) of the transient addition to the finite-element tool: one lumped node against the exact exponential, a 1D slab against its eigenseries, the plateau
       against the steady solve, the energy in time, and the second order of Crank-Nicolson in the step.
@details Run with `research/independent-fem-edge/.venv-research/bin/python -m pytest -q research/independent-fem-extensions/tests` (NumPy and SciPy only).
         The slab series is the separation-of-variables solution (derived here, not quoted from a source): flux `q` into x = 0, `T = 0` at x = L,
         `T(0, t) = q L / k [1 - 8 / pi^2 sum_n exp(-(2n+1)^2 pi^2 alpha t / 4 L^2) / (2n+1)^2]`.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import fem                                                              # noqa: E402
import mesh2d                                                           # noqa: E402
import transient                                                        # noqa: E402


def column(nz, L, k, rho_c, flux=0.0, h_top=0.0, h_bottom=0.0, q=0.0, w=1e-3):
    """!
    @brief A column of `nz` hexahedra of plan w x w and total height L.
    @param nz Elements.
    @param L Height in m.
    @param k Conductivity.
    @param rho_c Volumetric heat capacity.
    @param flux Heat flux into the top face, W/m2.
    @param h_top Film on the top face.
    @param h_bottom Film on the bottom face.
    @param q Volumetric source W/m3.
    @param w Plan side in m.
    @return Tuple (Transient, plan nodes count).
    """
    plan = mesh2d.tensor(np.array([0.0, w]), np.array([0.0, w]))
    zn = np.linspace(0.0, L, nz + 1)
    Np = 4
    nodes = np.column_stack([np.tile(plan.xy, (nz + 1, 1)), np.repeat(zn, Np)])
    elems = np.concatenate([np.tile(plan.quads, (nz, 1)) + (np.arange(nz) * Np)[:, None], np.tile(plan.quads, (nz, 1)) + ((np.arange(nz) + 1) * Np)[:, None]], axis=1)
    m = fem.Model(nodes, elems)
    m.k[:] = k
    m.q[:] = q
    if flux or h_top:
        m.add_faces(plan.quads, h=h_top, flux=flux)
    if h_bottom:
        m.add_faces(plan.quads + nz * Np, h=h_bottom)
    return transient.Transient(m, np.full(nz, rho_c)), Np


def test_one_node_against_the_exact_exponential():
    """!
    @brief A thin copper plate with a film on its top and a uniform source: the discrete system has the time constant rho c V / (h A) of the lumped node to the Biot error.
    @return None.
    """
    L, w, h = 0.1e-3, 1e-3, 1000.0
    tr, Np = column(1, L, 385.0, 3.45e6, h_top=h, q=1e6)
    tau = 3.45e6 * L / h
    P_over_hA = 1e6 * L / h
    w_top = np.zeros(tr.n)
    w_top[:Np] = 0.25
    r = tr.step_response({"top": w_top}, 5 * tau, dt0=tau / 40, per_level=40, factor=1.0)
    exact = P_over_hA * (1.0 - np.exp(-r["t"] / tau))
    assert np.max(np.abs(r["series"]["top"] - exact)) / P_over_hA < 2e-3


def slab_series(t, q, k, alpha, L, nterms=400):
    """!
    @brief Top temperature of a slab with flux q into x = 0 and T = 0 at x = L.
    @param t Times in s.
    @param q Flux W/m2.
    @param k Conductivity.
    @param alpha Diffusivity.
    @param L Thickness m.
    @param nterms Series terms.
    @return numpy.ndarray.
    """
    n = np.arange(nterms)[:, None]
    s = np.sum(np.exp(-((2 * n + 1) ** 2) * np.pi ** 2 * alpha * np.asarray(t)[None, :] / (4 * L ** 2)) / (2 * n + 1) ** 2, axis=0)
    return q * L / k * (1.0 - 8.0 / np.pi ** 2 * s)


def test_slab_against_its_eigenseries_and_plateau_and_energy():
    """!
    @brief A 1D slab heated on its top face and held at 0 K below (a very large film): the top temperature follows the eigenseries; the end value is the steady solve; the energy balances.
    @return None.
    """
    L, k, rc, q = 1e-3, 1.0, 1e6, 1e4
    tr, Np = column(80, L, k, rc, flux=q, h_bottom=1e12)
    w_top = np.zeros(tr.n)
    w_top[:Np] = 0.25
    alpha = k / rc
    r = tr.step_response({"top": w_top}, 3 * L ** 2 / alpha, dt0=1e-5, per_level=10, factor=1.5)
    t = r["t"][5:]
    err = np.abs(r["series"]["top"][5:] - slab_series(t, q, k, alpha, L)) / (q * L / k)
    assert err.max() < 5e-3
    steady = float(w_top @ tr.steady())
    assert abs(r["series"]["top"][-1] - steady) / steady < 1e-3 and abs(steady - q * L / k) / (q * L / k) < 1e-6
    e_in, e_store, e_lost = r["energy"]
    assert abs(e_in - e_store - e_lost) / e_in < 1e-9


def test_crank_nicolson_is_second_order():
    """!
    @brief Against a very fine step the error of a Rannacher-started Crank-Nicolson falls by 3.4 or more when the step is halved.
    @return None.
    """
    L, k, rc, q = 1e-3, 1.0, 1e6, 1e4
    tr, Np = column(40, L, k, rc, flux=q, h_bottom=1e12)
    w_top = np.zeros(tr.n)
    w_top[:Np] = 0.25

    def run(n):
        """!
        @brief One uniform-step run to t = 2 ms (the stretch in n steps), the top temperature at the end.
        @param n Steps.
        @return float.
        """
        r = tr.march(np.zeros(tr.n), [(0.0, 2e-3, n)], lambda t: 1.0, {"top": w_top}, rannacher=True)
        return r["series"]["top"][-1]
    ref = run(2048)
    e = [abs(run(n) - ref) for n in (16, 32, 64)]
    assert e[0] / e[1] > 3.4 and e[1] / e[2] > 3.4
