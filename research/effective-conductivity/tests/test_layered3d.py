"""!
@file test_layered3d.py
@brief The independent 3D solver against a series circuit, the energy balance, a uniform layer, and three published numbers (Seri Lee's plate, the cross of Muzychka et al., the coupon limits of Culham and Yovanovich).
"""

import numpy as np
import pytest

import layered3d as L
import study_culham_1998 as culham
import study_lee_spreading as lee
import study_muzychka_2003 as muz


def test_a_source_over_the_whole_face_is_a_series_circuit():
    dx, n = 1e-3, 8
    a = (n * dx) ** 2
    res = L.solve(dx, n, n, [(1e-3, 1.0, 4), (1e-3, 10.0, 4)], (0, 0, n * dx, n * dx), 2.0, 0.0, 100.0)
    exact = 2.0 * (1e-3 / (1.0 * a) + 1e-3 / (10.0 * a) + 1.0 / (100.0 * a))
    assert res["mean_source"] == pytest.approx(exact, rel=1e-9)


def test_the_heat_leaving_the_walls_equals_the_power():
    dx, n = 1e-3, 20
    res = L.solve(dx, n, n, [(2e-3, 5.0, 4), (0.05e-3, 400.0, 1), (1e-3, 0.4, 3)], [(5e-3, 5e-3, 12e-3, 15e-3), (14e-3, 2e-3, 18e-3, 6e-3)], [3.0, 1.5], 8.0, 20.0)
    assert res["heat_out"] == pytest.approx(4.5, rel=1e-9)
    assert len(res["per_source"]) == 2


def test_the_effective_conductivity_of_a_uniform_layer_is_its_own():
    dx, n = 2e-3, 20
    src = (10e-3, 10e-3, 20e-3, 20e-3)
    res = L.solve(dx, n, n, [(1.5e-3, 12.0, 6)], src, 1.0, 5.0, 5.0)
    r = L.solid_resistance(res, 1.0)
    ke = L.effective_conductivity(dx, n, n, 1.5e-3, src, 1.0, 5.0, 5.0, r, n_sub=6, lo=0.5, hi=200.0)
    assert ke == pytest.approx(12.0, rel=1e-3)


def test_the_limits_of_the_coupon_match_the_paper():
    lay = culham.LAYERS[3]
    total = sum(t for t, _ in lay)
    kp = sum(t * k for t, k in lay) / total
    ks = total / sum(t / k for t, k in lay)
    assert kp == pytest.approx(17.62, rel=0.005) and ks == pytest.approx(0.42, rel=0.01)
    assert np.sqrt(kp * ks) == pytest.approx(2.71, rel=0.01)


def test_lee_plate_centre_and_edge_within_a_few_percent_of_the_article():
    assert lee.rc_3d("centre") == pytest.approx(0.66, rel=0.03)
    assert lee.rc_3d("edge midpoint") == pytest.approx(1.29, rel=0.03)


def test_muzychka_cross_maximum_and_mean_source_temperature():
    case = muz.CASES["3"]
    out = muz.independent(case)
    assert out["max"] == pytest.approx(80.61, abs=0.15)
    weighted = np.mean(out["mean"])                                       # the five sources have the same area
    assert weighted == pytest.approx(78.87, abs=0.15)


def test_channel_correlations_have_the_right_limits_and_agree():
    import study_channel_correlations as ch
    assert ch.nu_elenbaas(1e-3) == pytest.approx(1e-3 / 24.0, rel=1e-3)          # fully developed: Nu_S = El / 24
    assert ch.nu_blend(1e-3) == pytest.approx(1e-3 / 24.0, rel=1e-2)
    el = np.logspace(-1, 4, 60)
    assert np.abs(ch.nu_blend(el) / ch.nu_elenbaas(el) - 1.0).max() < 0.06      # the two correlations agree within 6 %
    grid = np.logspace(0, 3, 3000)
    opt = grid[np.argmax(ch.nu_elenbaas(grid) / np.sqrt(grid))], grid[np.argmax(ch.nu_blend(grid) / np.sqrt(grid))]
    assert opt[0] < 54.3 < opt[1]                                                # the optimum of the quoted correlation lies between


def test_the_plate_model_converges_to_seri_lee_when_the_source_edges_fall_on_cell_edges():
    assert lee.rc_2d("centre", n=200) == pytest.approx(0.66, rel=0.02)
    assert lee.rc_2d("edge midpoint", n=200) == pytest.approx(1.29, rel=0.02)
    assert lee.rc_2d("corner", n=200) == pytest.approx(2.38, rel=0.06)


def test_the_mean_of_the_top_face_explains_the_base_temperature_of_the_paper():
    c = muz.CASES["1a"]
    n = int(round(c["w"] / c["dx"]))
    rects = [tuple(v * 1e-3 for v in r) for r, _ in c["sources"]]
    res = L.solve(c["dx"] * 1e-3, n, n, [(c["t"] * 1e-3, c["k"], 6)], rects, [p for _, p in c["sources"]], 0.0, c["h"])
    assert 25.0 + res["top_surface_mean"] == pytest.approx(53.06, abs=0.01)
    assert 25.0 + res["mean_wall"] == pytest.approx(25.0 + 25.0 / (10.0 * 0.09), abs=1e-6)
