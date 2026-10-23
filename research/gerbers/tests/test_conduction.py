"""!
@file test_conduction.py
@brief Exact and limiting cases of the conduction solvers and of the mappings (no Gerber needed).
"""

import numpy as np
import pytest

import conduction as cd


def uniform(value, k=3, r=12, c=12):
    """!
    @brief K windows of uniform sheet conductance.
    @param value Sheet conductance (W/K).
    @param k Number of windows.
    @param r Rows.
    @param c Columns.
    @return Array (k, r, c).
    """
    return np.full((k, r, c), value)


@pytest.mark.parametrize("m", [0, 2, 3])
def test_uniform_window_gives_its_own_conductance(m):
    """!@brief A uniform sheet of any shape has the conductance of a square piece, whatever the oversampling margin. @param m Margin rows. @return None."""
    for s in (cd.S_CU, cd.S_LAM):
        assert np.allclose(cd.local_flux(uniform(s, r=12 + 2 * m, c=12), m), s, rtol=1e-9)


def test_stripes_along_the_flow_are_in_parallel():
    """!@brief Alternating copper and laminate rows (along the flow) conduct as the arithmetic mean: the lower bound is exact. @return None."""
    W = np.where(np.arange(12)[:, None] % 2 == 0, cd.S_CU, cd.S_LAM) * np.ones((1, 12))
    got = cd.local_flux(W[None], 0)[0]
    assert got == pytest.approx((cd.S_CU + cd.S_LAM) / 2, rel=1e-9)


def test_stripes_across_the_flow_are_in_series():
    """!@brief Alternating columns (across the flow) conduct as the harmonic mean (equal pixel counts): the upper bound is exact. @return None."""
    W = np.where(np.arange(12)[None, :] % 2 == 0, cd.S_CU, cd.S_LAM) * np.ones((12, 1))
    got = cd.local_flux(W[None], 0)[0]
    assert got == pytest.approx(1.0 / np.mean(1.0 / W[0, :]), rel=1e-9)


def test_bounds_bracket_the_local_problem():
    """!@brief low <= effective conductance <= up for random masks. @return None."""
    rng = np.random.default_rng(0)
    for _ in range(10):
        mask = rng.random((10, 10)) < rng.uniform(0.2, 0.8)
        S = cd.sheet_of(mask)
        low_x, low_y, up_x, up_y = cd.map_bounds(S[None, None])
        eff = cd.local_flux(S[None], 0)[0]
        assert low_x[0, 0] - 1e-12 <= eff <= up_x[0, 0] + 1e-12


def test_lambda_ends_are_the_bounds_and_half_is_their_geometric_mean():
    """!@brief map_lambda(0) is low, map_lambda(1) is up, map_lambda(0.5) is sqrt(low * up). @return None."""
    rng = np.random.default_rng(1)
    S = cd.sheet_of(rng.random((1, 1, 8, 8)) < 0.5)
    lx, ly, ux, uy = cd.map_bounds(S)
    assert np.allclose(cd.map_lambda(S, 0.0)[0], lx) and np.allclose(cd.map_lambda(S, 1.0)[1], uy)
    assert np.allclose(cd.map_lambda(S, 0.5)[0], np.sqrt(lx * ux))


def test_power_mean_special_cases_and_order():
    """!@brief p = 1 arithmetic, p = -1 harmonic, p = 0 geometric, and the mean grows with p. @return None."""
    f = np.array([0.0, 0.25, 0.5, 1.0])
    arith = f * cd.S_CU + (1 - f) * cd.S_LAM
    harmo = 1.0 / (f / cd.S_CU + (1 - f) / cd.S_LAM)
    assert np.allclose(cd.map_power(f, 1.0), arith) and np.allclose(cd.map_power(f, -1.0), harmo)
    assert np.allclose(cd.map_power(f, 0.0), cd.S_CU ** f * cd.S_LAM ** (1 - f))
    assert np.allclose(cd.map_power(f, 1e-9), cd.map_power(f, 0.0), rtol=1e-6)
    for a, b in ((-1.0, -0.5), (-0.5, 0.0), (0.0, 0.5), (0.5, 1.0)):
        assert np.all(cd.map_power(f, a) <= cd.map_power(f, b) + 1e-15)
    assert cd.map_power(np.array([1.0]), 0.3)[0] == pytest.approx(cd.S_CU) and cd.map_power(np.array([0.0]), -0.3)[0] == pytest.approx(cd.S_LAM)


def test_checkerboard_is_nearest_to_the_geometric_mean():
    """!
    @brief A 50 % checkerboard conducts as the geometric mean of the two phases in an infinite medium (Dykhne). In a finite window with insulated sides
           it is a little lower (the sides cut paths), but it stays within 15 % of the geometric mean and at least twice as close to it as to the arithmetic and harmonic means.
    @return None.
    """
    n, sq = 48, 6
    mask = ((np.arange(n)[:, None] // sq + np.arange(n)[None, :] // sq) % 2 == 0)
    eff = cd.local_flux(cd.sheet_of(mask)[None], 0)[0]
    geo = np.sqrt(cd.S_CU * cd.S_LAM)
    arith, harmo = (cd.S_CU + cd.S_LAM) / 2, 2 * cd.S_CU * cd.S_LAM / (cd.S_CU + cd.S_LAM)
    assert eff == pytest.approx(geo, rel=0.15)
    assert abs(eff - geo) < 0.5 * abs(eff - arith) and abs(eff - geo) < 0.5 * abs(eff - harmo)


def test_dual_faces_of_a_uniform_sheet():
    """!@brief The flow-based faces of a uniform sheet equal the sheet conductance, with and without margin. @return None."""
    S = np.full((60, 80), cd.S_CU)
    for m in (0, 2, 5):
        gx, gy = cd.dual_faces(S, 10, m)
        assert gx.shape == (6, 7) and gy.shape == (5, 8)
        assert np.allclose(gx, cd.S_CU, rtol=1e-9) and np.allclose(gy, cd.S_CU, rtol=1e-9)


def test_cell_problem_of_a_uniform_sheet():
    """!@brief The numerical upscaling of a uniform cell returns its own conductance in both directions. @return None."""
    sx, sy = cd.map_cell_problem(cd.cell_blocks(np.full((40, 60), cd.S_LAM), 10))
    assert np.allclose(sx, cd.S_LAM) and np.allclose(sy, cd.S_LAM)


def test_solver_energy_balance_and_symmetry():
    """!@brief All the power leaves through the two faces, and a centred block gives a symmetric field. @return None."""
    ny = nx = 30
    S = np.full((ny, nx), cd.S_CU)
    gx, gy = cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :])
    T = cd.solve_faces(gx, gy, 1.0, 12, 18, 12, 18, power=2.0)
    assert (2 * cd.H_FACE * 1e-6 * T).sum() == pytest.approx(2.0, rel=1e-9)
    assert np.allclose(T, T[::-1, ::-1]) and np.allclose(T, T.T)


def test_two_layer_solver_energy_balance_and_coupling():
    """!@brief Two layers: the power leaves through the two outer faces; a stronger vertical link lowers the top and raises the bottom temperature. @return None."""
    ny = nx = 20
    S = np.full((ny, nx), cd.S_CU)
    gx = np.stack([cd.harm(S[:, :-1], S[:, 1:])] * 2)
    gy = np.stack([cd.harm(S[:-1, :], S[1:, :])] * 2)
    rows = np.arange(8, 12)
    out = []
    for g in (1e-5, 1e-2):
        T = cd.solve_two_layers(gx, gy, np.full((ny, nx), g), 1.0, rows, rows, power=1.0)
        assert (cd.H_FACE * 1e-6 * (T[0] + T[1])).sum() == pytest.approx(1.0, rel=1e-9)
        out.append((T[0].max(), T[1].max()))
    assert out[1][0] < out[0][0] and out[1][1] > out[0][1]


def test_geometric_mean_beats_the_fill_fraction_on_random_copper():
    """!@brief On random two-phase windows the geometric mean is closer to the resolved answer than the arithmetic fill fraction. @return None."""
    rng = np.random.default_rng(5)
    mask = rng.random((120, 120)) < 0.6
    S = cd.sheet_of(mask)
    ref = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), 0.1, 40, 80, 40, 80)[40:80, 40:80].mean()
    blk = cd.cell_blocks(S, 10)
    f = (blk == cd.S_CU).mean(axis=(2, 3))
    errs = {}
    for p in (1.0, 0.0):
        sc = cd.map_power(f, p)
        T = cd.solve_faces(*cd.faces_from_cells(sc, sc), 1.0, 4, 8, 4, 8)[4:8, 4:8].mean()
        errs[p] = abs(T / ref - 1)
    assert errs[0.0] < errs[1.0]


def test_bruggeman_and_hashin_shtrikman_limits():
    """!@brief The effective-medium formulas return the phases at f = 0 and 1, the geometric mean at f = 1/2, and the Hashin-Shtrikman bounds bracket them. @return None."""
    f = np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    br, lo, up = cd.map_bruggeman(f), cd.map_hashin_shtrikman(f, "lower"), cd.map_hashin_shtrikman(f, "upper")
    assert br[0] == pytest.approx(cd.S_LAM) and br[-1] == pytest.approx(cd.S_CU)
    assert lo[0] == pytest.approx(cd.S_LAM) and lo[-1] == pytest.approx(cd.S_CU) and up[0] == pytest.approx(cd.S_LAM) and up[-1] == pytest.approx(cd.S_CU)
    assert br[3] == pytest.approx(np.sqrt(cd.S_CU * cd.S_LAM))
    assert np.all(lo <= br + 1e-15) and np.all(br <= up + 1e-15)
    assert np.all(cd.map_power(f, -1.0) <= lo + 1e-15) and np.all(up <= cd.map_power(f, 1.0) + 1e-15)      # and inside the Wiener bounds


def test_stack_solver_matches_the_two_layer_solver_and_balances_energy():
    """!@brief solve_stack with two layers reproduces solve_two_layers; with four layers all the power leaves through the two outer faces. @return None."""
    rng = np.random.default_rng(2)
    ny = nx = 16
    S = [cd.sheet_of(rng.random((ny, nx)) < 0.6) for _ in range(4)]
    gx = np.stack([cd.harm(s[:, :-1], s[:, 1:]) for s in S])
    gy = np.stack([cd.harm(s[:-1, :], s[1:, :]) for s in S])
    gz = np.full((3, ny, nx), 2e-4)
    rows = np.arange(6, 10)
    two = cd.solve_two_layers(gx[:2], gy[:2], gz[0], 1.0, rows, rows, h_face=cd.H_FACE)
    # solve_two_layers puts the face loss on both layers' outer faces, like the stack with h_top = h_bottom
    stk2 = cd.solve_stack(gx[:2], gy[:2], gz[:1], 1.0, rows, rows)
    assert np.allclose(two, stk2, rtol=1e-9)
    T = cd.solve_stack(gx, gy, gz, 1.0, rows, rows, power=3.0)
    assert (cd.H_FACE * 1e-6 * (T[0] + T[3])).sum() == pytest.approx(3.0, rel=1e-9)


def test_dual_faces_do_not_depend_on_the_batch_size():
    """!@brief Solving the local windows in small batches gives the same faces as in one go. @return None."""
    rng = np.random.default_rng(4)
    S = cd.sheet_of(rng.random((80, 100)) < 0.5)
    a = cd.dual_faces(S, 10, 2, batch_pixels=10 ** 9)
    b = cd.dual_faces(S, 10, 2, batch_pixels=3000)
    assert np.allclose(a[0], b[0], rtol=1e-9) and np.allclose(a[1], b[1], rtol=1e-9)


def test_published_parallel_and_series_example():
    """!@brief The worked example of Sampson (Electronics Cooling, 2017): 10 % copper (391 W/m K) and 90 % board (0.59 W/m K) gives about 40 W/m K when the traces run along the flow and 0.65 W/m K across it. @return None."""
    blk = np.full((1, 1, 10, 10), 0.59)
    blk[:, :, :, 0] = 391.0                                                # one column of ten is copper: a stripe along y
    low_x, low_y, up_x, up_y = (v[0, 0] for v in cd.map_bounds(blk))
    assert low_y == pytest.approx(0.1 * 391 + 0.9 * 0.59, rel=1e-9)         # along the stripe: parallel, volume weighted (the article rounds 39.6 to 40)
    assert up_y == pytest.approx(low_y, rel=1e-9)                           # a stripe pattern has no cross flow: both bounds agree
    assert low_x == pytest.approx(1.0 / (0.1 / 391 + 0.9 / 0.59), rel=1e-9)  # across the stripe: series
    assert low_x == pytest.approx(0.65, abs=0.01)                           # the article's value
    assert up_x == pytest.approx(low_x, rel=1e-9)


def test_blackmore_tile_formulas_are_the_lower_bound_and_the_arithmetic_mean():
    """!@brief Blackmore's tile method (2010): kz = area-weighted mean, kx = rows in parallel of series chains. The first is the arithmetic fraction mapping, the second the `low` bound. @return None."""
    rng = np.random.default_rng(5)
    mask = rng.random((1, 1, 8, 8)) < 0.4
    blk = np.where(mask, 391.0, 0.59)
    kz = blk.mean()
    kx_rows = np.mean([1.0 / np.sum(1.0 / blk[0, 0, r, :] / 8.0) for r in range(8)])    # each row: series chain of 8 pixels; rows in parallel (mean of the row conductances)
    low_x = cd.map_bounds(blk)[0][0, 0]
    assert low_x == pytest.approx(kx_rows, rel=1e-9)
    f = mask.mean()
    assert kz == pytest.approx(cd.map_power(np.array(f), 1.0, 391.0, 0.59), rel=1e-9)
