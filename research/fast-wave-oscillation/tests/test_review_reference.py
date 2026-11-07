#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_review_reference.py
@brief Tests of the reviewer's reference lib/review_rect3d.py: energy balance, a 1D slab against its exact impedance, the series circuit, the time-domain check and the
       quarter model against the whole board.

@details Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/fast-wave-oscillation/tests`.
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import review_rect3d as R                                            # noqa: E402


def _uniform(board, top_first=None):
    """!
    @brief A source over the whole board (a 1D problem in z).
    @param board Board.
    @param top_first First cell of the top slot (m), see review_rect3d.Reference.
    @return Reference.
    """
    return R.Reference(board, R.Case(part=(0.0, 0.0, board.width, board.height)), fine=board.width / 4, margin=0.0, top_first=top_first)


def test_energy_balance_and_series_circuit():
    # Whole-board source on a two-layer board: the rise is the series-parallel circuit of the faces and the laminate, and the heat out is the power
    b = R.Board(width=10e-3, height=10e-3, layers=2, h_top=10.0, h_bottom=20.0)
    ref = _uniform(b)
    T = ref.steady()
    assert ref.heat_out(T) == pytest.approx(1.0, rel=1e-9)
    area = b.width * b.height
    gap = b.thickness - 2 * b.t_cu
    r_lam = gap / (b.kz * area) + b.t_cu / (b.k_cu * area)            # (the copper cells are in series too)
    r_top, r_bot = 1 / (b.h_top * area), 1 / (b.h_bottom * area)
    expect = r_top * (r_lam + r_bot) / (r_top + r_lam + r_bot)
    assert T[ref.read].max() == pytest.approx(expect, rel=2e-3)


def test_bare_slab_against_its_exact_impedance():
    # A bare FR-4 slab heated uniformly on its top face, both faces insulated: Z(w) = 1 / (A k gamma tanh(gamma d)), gamma = sqrt(j w rho c / k)
    # (the surface cell of bare laminate must be thin: top_first, see review_rect3d.Reference)
    b = R.Board(width=5e-3, height=5e-3, layers=1, copper=False, h_top=0.0, h_bottom=0.0, t_cu=10e-6)
    ref = _uniform(b, top_first=0.02e-6)
    f = np.array([1.0, 30.0, 1000.0])
    Hn = ref.transfer(f)[:, 0]
    d, area = b.thickness, b.width * b.height
    gam = np.sqrt(2j * np.pi * f * b.rc_lam / b.kz)
    exact = 1.0 / (area * b.kz * gam * np.tanh(gam * d))
    np.testing.assert_allclose(np.abs(Hn), np.abs(exact), rtol=0.02)


def test_harmonic_sum_matches_time_steps():
    # The 20 Hz, 30 % wave of a 10 mm part: harmonic sum of the interpolated transfer function against implicit-Euler steps on the same matrices
    b = R.Board(layers=2)
    ref = R.Reference(b, R.Case(part=(25e-3, 15e-3, 35e-3, 25e-3)), quarter=True, fine=2e-3, growth_z=1.4)
    s_f = R.Response(ref, per_decade=6).swing(0.05, 0.3)
    s_t = R.time_domain_swing(ref, 0.05, 0.3, steps_per_period=2000, cycles=4)
    assert s_t == pytest.approx(s_f, rel=0.02)


def test_quarter_equals_whole_board():
    # A centred part: the quarter model with adiabatic cut planes gives the same steady rise as the whole board
    b = R.Board(layers=2)
    case = R.Case(part=(25e-3, 15e-3, 35e-3, 25e-3))
    q = R.Reference(b, case, quarter=True, fine=2.5e-3, growth_z=1.6)
    w = R.Reference(b, case, quarter=False, fine=2.5e-3, growth_z=1.6)
    assert q.steady()[q.read].max() == pytest.approx(w.steady()[w.read].max(), rel=2e-3)


def test_temperature_wave_decays_as_lienhard_eq_5_62():
    # Lienhard (A Heat Transfer Textbook, 2024, eq. 5.62, PDF page 248, printed 234): in a semi-infinite solid with a harmonic boundary the wave is
    # e^(-xi) cos(Omega - xi), xi = x sqrt(w / (2 alpha)); in complex form the amplitude ratio between depth x and the surface is e^(-(1 + j) xi)
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    b = R.Board(width=5e-3, height=5e-3, layers=1, copper=False, h_top=0.0, h_bottom=0.0, t_cu=10e-6)
    ref = _uniform(b)
    f = 1000.0                                                        # penetration sqrt(alpha / (pi f)) = 7.6 um, the 1.6 mm slab is semi-infinite
    x = spla.spsolve((ref.K + 2j * np.pi * f * sp.diags(ref.C)).tocsc(), ref.q.astype(complex)).reshape(ref.shape)[:, 0, 0]
    zc = np.cumsum(ref.dz) - 0.5 * ref.dz                              # Depth of the cell centres
    alpha = b.kz / b.rc_lam
    xi = (zc - zc[0]) * np.sqrt(2 * np.pi * f / (2 * alpha))
    sel = (xi > 0.5) & (xi < 3.0)
    np.testing.assert_allclose(x[sel] / x[0], np.exp(-(1 + 1j) * xi[sel]), atol=0.01)
