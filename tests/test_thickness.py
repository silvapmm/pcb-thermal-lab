#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_thickness.py
@brief The surface read-out of thick outer copper (pcbthermal/thickness.py): closed forms, thin copper unchanged, the partial-cell rule, the t/a flag, the models that offer it,
       and the rule that nothing which decides a number reads it.
"""

import copy
import types

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate, thickness
from pcbthermal.examples import example_board
from pcbthermal.gui import layerchoice
from pcbthermal.model import Materials


def plate(t_mm=10.0, k=150.0, h=400.0, src=(20, 20, 30, 30), power=25.0, width=50.0):
    """!
    @brief A one-layer plate of the papers (full copper of thickness t, top and edges insulated, film h below) with one square source.
    @param t_mm Plate thickness in mm.
    @param k Plate conductivity in W/mK.
    @param h Bottom film in W/m2K.
    @param src Source rectangle in mm.
    @param power Source power in W.
    @param width Plate side in mm.
    @return Problem.
    """
    p = Problem.new(width, width, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=25.0, h_top=1e-6, h_bottom=h, h_side=None, materials=Materials(k_copper=k))
    p.add_full_copper()
    p.add_heater(1, power, rect=src, name="S")
    return p


def test_offsets_closed_forms():
    # A column fed on top and cooled below gives q t / 2k; heat that only spreads gives q t / 3k; the two faces add up to (q_top + q_bot) t / 6k
    t, k, q = 1e-2, 150.0, 1e5
    d_top, d_bot = thickness.offsets(t, k, q, -q)
    assert d_top == pytest.approx(q * t / (2 * k), rel=1e-12) and d_bot == pytest.approx(-q * t / (2 * k), rel=1e-12)
    assert thickness.offsets(t, k, q, 0.0)[0] == pytest.approx(q * t / (3 * k), rel=1e-12)
    a, b = thickness.offsets(t, k, 3e4, -1e4)
    assert a + b == pytest.approx((3e4 - 1e4) * t / (6 * k), rel=1e-12)


def test_a_one_dimensional_column_reads_q_t_over_2k_exactly():
    # The source covers the whole board: the flow is one-dimensional, the surface is the column mean plus q t / (2 k) (the top film is 1e-6 W/m2K)
    p = plate(t_mm=4.0, k=100.0, h=300.0, src=(0, 0, 50, 50), power=10.0)
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=5.0)).results["fvm"]
    q = 10.0 / (0.05 * 0.05)
    d = r.arrays["T_surface"][0] - r.T[0]
    assert np.allclose(d, q * 4e-3 / (2 * 100.0), rtol=1e-5)
    assert np.allclose(r.arrays["T_surface_mean"][0], r.arrays["T_surface"][0])           # full copper: mean and peak are the same
    assert not np.isnan(r.arrays["T_surface"][1]).any()                                # a one-layer plate has the bottom face too
    assert (r.arrays["T_surface"][1] < r.T[0]).all()                                       # the cooled face is below the column mean


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_case_2_of_muzychka_the_surface_is_within_the_stated_range_of_the_3d_surface(model):
    # Independent 3D surface (research/muzychka-case2-analytic, layered3d with 8 sub-slabs, 0.5 mm): 97.41 / 103.85 / 101.31 / 99.95 degC. The program's column mean reads
    # 2.0 / 4.6 / 3.7 / 2.9 K below it; the parabola reads +0.57 / +1.26 / +1.03 / +0.80 K above it (README 4.1 of research/through-thickness-readout), upper side at t/a = 1
    ref = [97.41, 103.85, 101.31, 99.95]
    cen = [(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)]
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0))
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip(cen, [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    r = simulate(p, SolverOptions(models=(model,), cell_mm=0.5)).results[model]
    S, T = r.arrays["T_surface"][0], r.T[0]
    for (cx, cy), want in zip(cen, ref):
        if r.grid == "nodes":
            i, j = int(round(cx / 0.5)), int(round(cy / 0.5))
            s, c = S[j, i], T[j, i]
        else:
            i, j = int(round(cx / 0.5)), int(round(cy / 0.5))
            s, c = S[j - 1:j + 1, i - 1:i + 1].mean(), T[j - 1:j + 1, i - 1:i + 1].mean()
        assert 0.3 < s - want < 1.6              # hot side, as documented, inside the stated range
        assert want - c > 1.5                    # the column mean is the lower number
        assert s - c < 6.0                       # and the surface stays under the bound q t / 2k
    assert r.arrays["T_surface_flag"][0].any()   # t / a = 1: an upper estimate


def test_thin_copper_has_no_surface_and_the_results_are_unchanged():
    p = example_board()
    r = simulate(p, SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=2.0))
    for m in r.results.values():
        assert "T_surface" not in m.arrays and "t_max_surface_top" not in m.extras
    assert all("t_max_surface" not in row for row in r.heater_rows())


def test_lumped_analytic_and_the_solid_offer_no_surface():
    p = plate()
    r = simulate(p, SolverOptions(models=("lumped", "analytic", "solid3d"), cell_mm=2.0))
    for m in r.results.values():
        assert "T_surface" not in m.arrays


def test_nothing_that_decides_a_number_reads_the_surface(monkeypatch):
    # Tj, the margin, the power limit, the top-path split and the power coefficient run inside the solve: with the surface arrays switched off every number is bit-identical
    p = plate(t_mm=3.0, k=150.0, h=50.0, src=(20, 20, 30, 30), power=5.0)
    h = p.heaters[0]
    h.theta, h.tj_max, h.theta_sa, h.power_tc = 3.0, 120.0, 20.0, 0.002
    on = simulate(copy.deepcopy(p), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    monkeypatch.setattr(thickness, "attach", lambda *a, **k: None)
    off = simulate(copy.deepcopy(p), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    assert "T_surface" in on.results["fvm"].arrays and "T_surface" not in off.results["fvm"].arrays
    for m in ("fvm", "fdm"):
        assert on.results[m].t_max == off.results[m].t_max and np.array_equal(on.results[m].T, off.results[m].T)
        assert on.power_used[m] == off.power_used[m]
    rows_on, rows_off = on.heater_rows(), off.heater_rows()
    for a, b in zip(rows_on, rows_off):
        assert {k: v for k, v in a.items() if "surface" not in k} == b
    assert rows_on[0]["t_max_surface"] > rows_on[0]["t_max"]


def test_the_partial_cell_peak_is_the_larger_of_the_two_terms_not_their_sum():
    ny = nx = 2
    res = types.SimpleNamespace(T=np.full((1, ny, nx), 100.0), arrays={"face_peak": np.array([[[0.0, 0.5], [0.0, 0.5]]]), "face_mean": np.array([[[0.0, 0.25], [0.0, 0.25]]])},
                                extras={}, ambient=25.0, grid="cells", dx=1e-3, dy=1e-3, coords=lambda: (np.array([0.5e-3, 1.5e-3]), np.array([0.5e-3, 1.5e-3])))
    fill = np.array([[[1.0, 0.5], [1.0, 0.5]]])
    prob = types.SimpleNamespace(heaters=[], board=types.SimpleNamespace(copper_thickness=[1e-3], layers=1))
    d = {0: np.full((ny, nx), 0.2), 1: np.full((ny, nx), -0.2)}
    thickness._finish(res, prob, d, fill, [(0, 0), (1, 0)], np.full((ny, nx), 1e-6))
    top, mean = res.arrays["T_surface"][0], res.arrays["T_surface_mean"][0]
    assert top[0, 0] == pytest.approx(100.2) and mean[0, 0] == pytest.approx(100.2)          # full copper: the copper term
    assert top[0, 1] == pytest.approx(100.5)                                                   # f = 0.5: the larger of 0.2 and 0.5, not 0.7
    assert mean[0, 1] == pytest.approx(100.0 + 0.5 * 0.2 + 0.25)                               # the mean is f c plus the laminate mean term


def test_the_flag_marks_a_part_that_is_wide_against_the_plate_only():
    wide = simulate(plate(t_mm=10.0, src=(20, 20, 30, 30)), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]       # t / a = 1
    narrow = simulate(plate(t_mm=2.0, src=(10, 10, 40, 40), width=50.0), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]   # t / a = 0.07
    assert wide.arrays["T_surface_flag"][0].any() and not narrow.arrays["T_surface_flag"][0].any()


def test_the_layer_box_lists_the_surface_only_with_it_and_only_in_temperature():
    assert [t for t, _ in layerchoice.items("temperature", 2, (), (0, 1))][-2:] == ["Surface (top)", "Surface (bottom)"]
    assert not any("Surface" in t for t, _ in layerchoice.items("temperature", 2, (), ()))
    assert not any("Surface" in t for t, _ in layerchoice.items("single", 2, (), (0, 1)))
    c = layerchoice.LayerChoice()
    c.pick(layerchoice.SURFACE_BASE)
    assert c.effective("temperature", 2, (), (0, 1))[0] == layerchoice.SURFACE_BASE
    assert c.effective("temperature", 2, (), ())[0] == 0                                     # a result without it: the layer
    v, note = c.effective("animation", 2, (), (0, 1))
    assert v == 0 and "Surface (top)" in note                                               # steady only: the page shows the column and says so


def test_the_report_names_both_read_outs_only_when_they_exist():
    thick = simulate(plate(), SolverOptions(models=("fvm",), cell_mm=1.0)).report()
    assert "Read-outs: column" in thick and "surface max" in thick and "column max" in thick and "Hottest surface (top)" in thick
    thin = simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0)).report()
    assert "surface" not in thin.lower().replace("surface of", "")


def test_the_surface_map_draws():
    from matplotlib.figure import Figure
    from pcbthermal import plots
    p = plate()
    r = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    fig = Figure()
    plots.draw_surface(fig, r.results["fvm"], p, 0)
    assert "surface (top)" in fig.axes[0].get_title()
    fig2 = Figure()
    plots.draw_surface(fig2, r.results["lumped"], p, 0)
    assert fig2.axes[0].texts


def test_the_thick_plate_warning_quotes_the_estimate():
    sim = simulate(plate(), SolverOptions(models=("fvm",), cell_mm=1.0))
    w = [x for x in sim.warnings if "thick and poorly conducting" in x]
    assert len(w) == 1 and "surface estimate of this model" in w[0] and "upper side" in w[0]
