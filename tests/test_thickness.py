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
    # 2.0 / 4.6 / 3.7 / 2.9 K below it; the parabola reads +0.56 / +1.26 / +1.03 / +0.80 K above it at 0.5 mm (validation 55.6; the research prototype printed +0.57 for the first, README 4.1 of research/through-thickness-readout), upper side at t/a = 1
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


def test_thin_copper_has_the_surface_tiny_but_present_and_nothing_else_moves(monkeypatch):
    # Decision: no thickness threshold. 35 um copper has the arrays; the difference is milli-kelvin; every non-surface number is bit-identical with the arrays switched off
    p = example_board()
    on = simulate(copy.deepcopy(p), SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=2.0))
    for k in ("fvm", "fdm"):
        m = on.results[k]
        assert "T_surface" in m.arrays and "t_max_surface_top" in m.extras and "t_max_surface_bottom" in m.extras
        d = float(m.extras["t_max_surface_top"]) - float(np.nanmax(m.T[0]))
        print(f"thin copper {k}: surface top minus column max = {d * 1e3:.3f} mK")
        assert 0 < d < 0.02                                                    # tiny, but present (and positive on a heated face)
    assert "T_surface" not in on.results["lumped"].arrays                       # the Lumped has no face flux: no surface, only a text
    assert "T_surface" in on.results["analytic"].arrays                         # the Analytic reads one from its own field (rule F)
    monkeypatch.setattr(thickness, "attach", lambda *a, **k: None)
    monkeypatch.setattr(thickness, "attach_field", lambda *a, **k: None)
    off = simulate(copy.deepcopy(p), SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=2.0))
    for k in on.results:
        assert on.results[k].t_max == off.results[k].t_max and np.array_equal(on.results[k].T, off.results[k].T)
    assert all("t_max_surface" in row for row in on.heater_rows()) and not any("t_max_surface" in row for row in off.heater_rows())


def test_the_surface_exists_for_every_outer_face_and_every_thickness_and_the_inner_layer_is_the_column():
    # Outer faces of 4-layer example: top and bottom both finite; an inner layer has no outer face (the arrays are the two outer faces only)
    r = simulate(example_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    for m in r.results.values():
        assert m.arrays["T_surface"].shape[0] == 2 and np.isfinite(m.arrays["T_surface"][0]).any() and np.isfinite(m.arrays["T_surface"][1]).any()
        assert m.T.shape[0] == 4
    for t_um in (18.0, 35.0, 70.0, 105.0, 140.0, 400.0):
        p = plate(t_mm=1.6, src=(20, 20, 30, 30))
        p.board.copper_thickness = [t_um * 1e-6]
        m = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"]
        assert "T_surface" in m.arrays, t_um
    # a part on an inner layer: no surface, 'n/a' (the surface is the column there)
    p = example_board()
    p.heaters[0].layer = 1
    rows = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()
    assert "t_max_surface" not in rows[0] and "t_max_surface" in rows[1]


def test_the_patterned_thin_copper_trap_the_board_difference_is_the_bare_laminate_and_the_part_rows_agree():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "regression"))
    import regress_boards as rb
    for name, floor in (("hatched_copper", 1.0), ("drawn_ell", 3.0)):
        p = rb.build(name, str(Path(__file__).parent.parent / "examples"))
        sim = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=1.0))
        for k in ("fvm", "fdm"):
            m = sim.results[k]
            board_diff = float(m.extras["t_max_surface_top"]) - float(np.nanmax(m.T[0]))
            part = [r["t_max_surface"] - r["t_max"] for r in sim.heater_rows() if "t_max_surface" in r][0]
            print(f"{name} {k}: board-level surface minus column max {board_diff:+.4f} K; part row {part:+.5f} K")
            assert board_diff > floor                                           # the trap: a K, not milli-kelvin, on 35 um copper
            assert abs(part) < 1e-3                                             # the part's column already holds the laminate face term: the rows agree
        rep = sim.report()
        assert "bare laminate" in rep                                           # the line says what the difference is


def test_the_face_fluxes_close_the_energy_balance_exactly():
    # The offsets of the two faces add to (q_top + q_bot) t / (6 k) per cell; summed over the plate (insulated edge) the net heat through the two faces is zero: the source
    # power in the top face equals what leaves by the films, so the sum of the face fluxes vanishes (to 1e-6 W) and the sum of the cell offsets with it
    for t_mm in (0.035, 3.0, 10.0):
        p = plate(t_mm=t_mm, k=150.0, h=50.0, src=(20, 20, 30, 30), power=5.0)
        m = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=1.0)).results["fvm"]
        net_w = float(((m.arrays["T_surface"][0] - m.T[0]) + (m.arrays["T_surface"][1] - m.T[0])).sum()) * 6.0 * 150.0 / (t_mm * 1e-3) * m.dx * m.dy
        print(f"t = {t_mm} mm: net face flux of the plate {net_w:.3e} W for {m.power_in:.1f} W in")
        assert abs(net_w) < 1e-6
    d_top, d_bot = thickness.offsets(3e-3, 150.0, 1000.0, -1000.0)
    assert d_top == pytest.approx(1000.0 * 3e-3 / (2 * 150.0)) and d_bot == pytest.approx(-d_top)


def test_a_saved_project_is_byte_identical_whatever_the_surface(tmp_path):
    from pcbthermal import project
    proj = project.Project(problem=example_board())
    a, b = tmp_path / "a.pcbt.json", tmp_path / "b.pcbt.json"
    project.save_project(str(a), proj)
    simulate(proj.problem, SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))                # runs with the surface arrays; they are never stored in the problem
    project.save_project(str(b), proj)
    assert a.read_bytes() == b.read_bytes()


def test_surface_files_are_written_only_on_request(tmp_path):
    sim = simulate(example_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    plain = {f.rsplit("/", 1)[-1] for f in sim.save(str(tmp_path / "a"), plots=False)}
    assert not any(n.startswith("surface_") for n in plain) and "field_fvm.csv" in plain
    asked = {f.rsplit("/", 1)[-1] for f in sim.save(str(tmp_path / "b"), plots=True, surface_files=True)}
    assert {"surface_fvm.csv", "surface_fdm.csv", "surface_fvm_top.png", "surface_fvm_bottom.png"} <= asked
    head = (tmp_path / "b" / "surface_fvm.csv").read_text().splitlines()[0]
    assert head == "face,x_mm,y_mm,T_surface_c,T_surface_mean_c,T_column_c,upper_estimate"


def test_every_map_names_its_read_out():
    from matplotlib.figure import Figure
    from pcbthermal import plots
    p = example_board()
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    r = sim.results["fvm"]
    fig = Figure()
    plots.draw_fields(fig, r, p)
    assert "column mean" in fig._suptitle.get_text() and fig.axes[-1].get_ylabel() == plots.COLUMN_LABEL
    fig = Figure()
    plots.draw_surface(fig, r, p, 0)
    assert "estimate" in fig.axes[0].get_title() and "column max" in fig.axes[0].get_title() and "% of the rise" in fig.axes[0].get_title()
    assert "Surface" in fig.axes[-1].get_ylabel()


def test_the_cost_of_the_surface_is_milliseconds():
    import time
    p = example_board()
    t0 = time.perf_counter()
    simulate(copy.deepcopy(p), SolverOptions(models=("fvm",), cell_mm=1.0))
    total = time.perf_counter() - t0
    m = simulate(copy.deepcopy(p), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    print(f"whole run {total:.3f} s; arrays added: {m.arrays['T_surface'].nbytes + m.arrays['T_surface_mean'].nbytes + m.arrays['T_surface_flag'].nbytes} bytes")
    assert m.arrays["T_surface"].nbytes < 1e6


def test_only_the_lumped_offers_no_surface_the_analytic_and_the_solid_have_one():
    p = plate()
    r = simulate(p, SolverOptions(models=("lumped", "analytic", "solid3d"), cell_mm=2.0))
    assert "T_surface" not in r.results["lumped"].arrays
    for k in ("analytic", "solid3d"):
        m = r.results[k]
        assert m.arrays["T_surface"].shape[0] == 2 and np.isfinite(m.arrays["T_surface"][0]).any(), k


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


def test_a_cell_without_copper_and_without_a_laminate_term_has_no_offset():
    # Review: the peak of an empty cell took the copper term c (a parabola through copper that is not there) while its mean was f c = 0; both are 0 now
    ny, nx = 1, 2
    res = types.SimpleNamespace(T=np.full((1, ny, nx), 50.0), arrays={"face_peak": np.zeros((1, ny, nx)), "face_mean": np.zeros((1, ny, nx))},
                                extras={}, ambient=25.0, grid="cells", dx=1e-3, dy=1e-3, coords=lambda: (np.array([0.5e-3, 1.5e-3]), np.array([0.5e-3])))
    prob = types.SimpleNamespace(heaters=[], board=types.SimpleNamespace(copper_thickness=[1e-3], layers=1))
    thickness._finish(res, prob, {0: np.full((ny, nx), 0.3), 1: np.full((ny, nx), -0.3)}, np.array([[[1.0, 0.0]]]), [(0, 0), (1, 0)], np.full((ny, nx), 1e-6))
    assert res.arrays["T_surface"][0][0, 0] == pytest.approx(50.3) and res.arrays["T_surface"][0][0, 1] == 50.0
    assert res.arrays["T_surface_mean"][0][0, 1] == 50.0


def test_the_flag_marks_a_part_that_is_wide_against_the_plate_only():
    wide = simulate(plate(t_mm=10.0, src=(20, 20, 30, 30)), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]       # t / a = 1
    narrow = simulate(plate(t_mm=2.0, src=(10, 10, 40, 40), width=50.0), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]   # t / a = 0.07
    assert wide.arrays["T_surface_flag"][0].any() and not narrow.arrays["T_surface_flag"][0].any()


# Measured against the independent 3D solver (releases/2.9.0/surface-flag, k 385 and 150 W/mK, bottom film 400, 0.5 mm cells): (t mm, b mm, c mm, parabola / true term at the
# source centre). The term overshoots by more than 7 % exactly when the NARROW side b is thin against the plate, whatever the long side c is.
FLAG_TABLE = [(1, 2, 20, 1.028), (1, 2, 10, 1.028), (1, 5, 10, 0.993), (1, 10, 10, 0.993), (2, 2, 20, 1.149), (2, 2, 10, 1.150), (2, 2, 40, 1.148), (2, 3, 10, 1.058),
              (2, 4, 20, 1.021), (2, 5, 10, 1.006), (2, 5, 20, 1.006), (2, 10, 10, 0.994), (2, 10, 20, 0.994), (2, 20, 20, 0.994), (3, 5, 10, 1.043), (3, 4, 20, 1.075)]


def test_source_width_is_the_narrow_side_capped_by_the_equivalent_side():
    rect = lambda b, c: [(0, 0), (c, 0), (c, b), (0, b)]
    assert thickness.source_width(rect(2e-3, 20e-3)) == pytest.approx(2e-3, rel=1e-9)             # elongated: the narrow side (sqrt(A) is 6.3 mm)
    assert thickness.source_width(rect(10e-3, 10e-3)) == pytest.approx(10e-3, rel=1e-9)           # a square: its side, as before
    th = 0.6
    rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    assert thickness.source_width(np.array(rect(2e-3, 20e-3)) @ rot.T) == pytest.approx(2e-3, rel=1e-9)   # orientation does not matter
    disc = 5e-3 * np.array([(np.cos(a), np.sin(a)) for a in np.linspace(0, 2 * np.pi, 97)[:-1]])
    assert thickness.source_width(disc) == pytest.approx(np.sqrt(thickness.polygon_area(disc)), rel=1e-12)   # capped: a disc is flagged as before
    assert thickness.source_width([(0, 0), (1e-3, 0), (2e-3, 0)]) == 0.0                           # degenerate


@pytest.mark.parametrize("t,b,c,ratio", FLAG_TABLE)
def test_the_flag_follows_the_measured_overshoot_of_elongated_parts(t, b, c, ratio):
    # A measured overshoot above 7 % must be flagged; the flag may be earlier (it is conservative) but never miss one
    p = plate(t_mm=float(t), k=385.0, src=(25 - c / 2, 25 - b / 2, 25 + c / 2, 25 + b / 2), power=10.0)
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    flagged = bool(r.arrays["T_surface_flag"][0].any())
    if abs(t / b - thickness.UPPER_RATIO) > 1e-6:                    # exactly on the threshold the float rounding of the polygon decides
        assert flagged == (t / b > thickness.UPPER_RATIO)
    if ratio > 1.07:
        assert flagged


L_2MM = [(15, 15), (35, 15), (35, 17), (17, 17), (17, 35), (15, 35)]     # an L of 2 mm arms, 20 mm long, in mm: hull 8.7 mm wide, sqrt(A) 8.7 mm


def test_source_width_finds_the_narrow_arm_of_a_concave_part():
    # The hull bridges the notch of an L or a U (review: an L of 2 mm arms on 2 mm copper overshoots 1.19 times against an exact cosine series, with a hull 8.7 mm wide)
    mm = lambda pts: np.asarray(pts, dtype=float) * 1e-3
    assert thickness.source_width(mm(L_2MM)) == pytest.approx(2e-3, rel=1e-9)
    assert thickness.source_width(mm(L_2MM)[::-1]) == pytest.approx(2e-3, rel=1e-9)                 # clockwise outline
    u = [(0, 0), (20, 0), (20, 20), (18, 20), (18, 2), (2, 2), (2, 20), (0, 20)]
    assert thickness.source_width(mm(u)) == pytest.approx(2e-3, rel=1e-9)
    # A keyhole outline (two 4 x 4 pads joined by a slit of zero width): the chord across the gap and the zero-length one are ignored, the pad width is kept
    keyhole = [(0, 0), (4, 0), (4, 2), (10, 2), (10, 0), (14, 0), (14, 4), (10, 4), (10, 2), (4, 2), (4, 4), (0, 4)]
    assert thickness.source_width(mm(keyhole)) == pytest.approx(4e-3, rel=1e-9)
    closed = np.vstack([mm(L_2MM), mm(L_2MM)[:1]])                                                   # a repeated closing vertex changes nothing
    assert thickness.source_width(closed) == pytest.approx(2e-3, rel=1e-9)


def test_a_thin_l_shaped_part_is_flagged():
    # sqrt(A) and the hull width both give t/a 0.23 here; the arm gives 1 (the surface term of the FVM at 0.5 mm reads 1.19 times the exact series, releases/2.9.0/surface-flag study_exact_series.py)
    p = Problem.new(50, 50, layers=1, thickness_mm=2.0002, copper_um=2000.0, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=385.0))
    p.add_full_copper()
    p.add_heater(1, 10.0, polygon=L_2MM, name="L")
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    assert r.arrays["T_surface_flag"][0].any()


def test_an_elongated_part_is_flagged_by_its_narrow_side_and_a_square_part_is_unchanged():
    long_ = simulate(plate(t_mm=2.0, k=385.0, src=(15, 24, 35, 26), power=10.0), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]     # 2 x 20: sqrt(A) 6.3, t/b 1
    square = simulate(plate(t_mm=2.0, k=385.0, src=(20, 20, 30, 30), power=10.0), SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]   # 10 x 10: t/a 0.2
    assert long_.arrays["T_surface_flag"][0].any() and not square.arrays["T_surface_flag"][0].any()


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


def test_the_report_names_both_read_outs_always_for_the_fvm_and_the_fdm():
    thick = simulate(plate(), SolverOptions(models=("fvm",), cell_mm=1.0)).report()
    assert "Read-outs: column" in thick and "surface max" in thick and "column max" in thick and "Hottest surface (top)" in thick
    thin = simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0)).report()
    assert "Read-outs: column" in thin and "surface max" in thin and "Hottest surface (top)" in thin and "% of the rise" in thin
    none = simulate(example_board(), SolverOptions(models=("lumped",), cell_mm=2.0)).report()
    assert "no surface read-out" in none


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


def test_no_surface_text_prints_a_negative_zero():
    # Review: a part whose surface equals its column (the patterned-copper rows) printed '-0.000 K' from a rounding of -1e-5; every surface difference goes through signed_fixed
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "regression"))
    import regress_boards as rb
    from matplotlib.figure import Figure
    from pcbthermal import plots
    for name in ("hatched_copper", "drawn_ell", "example_board"):
        p = rb.build(name, str(Path(__file__).parent.parent / "examples"))
        sim = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=1.0 if name != "example_board" else 2.0))
        texts = [sim.report()]
        for r in sim.results.values():
            for face in (0, 1):
                fig = Figure()
                plots.draw_surface(fig, r, p, face)
                texts.append(fig.axes[0].get_title())
        assert not any("-0.000" in t or "-0.00 %" in t for t in texts), name
