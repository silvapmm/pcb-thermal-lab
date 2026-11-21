#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_model.py
@brief The finite-element comparison model in the program (`fem.solve_steady`, key `fem` of `api.simulate`): the read-outs, the energy balance, the closed forms, the
       published case, the refusals, the options, the command line and the memory verdicts.
@details The small boards of this file stay under `femcore.FEM_DIRECT_MAX` unknowns, so they run without the optional package pyamg; a test of a larger mesh is skipped
         without it (`needs_pyamg`).
"""

import json
import math
import os

import numpy as np
import pytest

from pcbthermal import api, cli, femcore, femmesh, fem, memory
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.model import Materials, Problem

needs_pyamg = pytest.mark.skipif(not femcore.available(), reason="needs the optional package pyamg (pip install pyamg)")


def small(layers=4, power=1.0, h=10.0, width=40.0, height=30.0, side=None):
    """!
    @brief A small board with full copper on every layer and one 6 x 6 mm part.
    @param layers Layer count.
    @param power Power of the part in W.
    @param h Film coefficient of both faces in W/m2K.
    @param width Board width in mm.
    @param height Board height in mm.
    @param side Edge coefficient in W/m2K (None: insulated edges).
    @return Problem.
    """
    p = Problem.new(width_mm=width, height_mm=height, layers=layers, h_top=h, h_bottom=h, h_side=side)
    p.add_full_copper(list(range(1, layers + 1)))
    p.add_heater(1, power, rect=(width / 2 - 3, height / 2 - 3, width / 2 + 3, height / 2 + 3), name="U1")
    return p


def test_energy_balance_and_heat_paths():
    p = small(side=20.0)
    r = fem.solve_steady(p, cell_mm=2.0)
    assert abs(r.balance_error) < 1e-9
    assert set(r.power_out) == {"top", "bottom", "edge"} and sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-9)
    assert r.model == "fem" and r.grid == "cells" and r.T.shape == (4, 15, 20) and r.residual < 1e-9


def test_a_one_dimensional_column_is_exact_and_the_film_is_the_plain_h():
    # The source covers the whole board and the edges are insulated: the heat flow is one-dimensional. The face temperatures are T_amb + q_up / h with the PLAIN h
    # (the film is inherent in the finite elements: there is no half cell in series), and q_up follows from the series circuit of the stack (source in the top copper)
    p = Problem.new(width_mm=20, height_mm=20, layers=2, h_top=30.0, h_bottom=12.0, h_side=None)
    p.add_full_copper([1, 2])
    P = 4.0
    p.add_heater(1, P, rect=(0, 0, 20, 20), name="all")
    b, m = p.board, p.board.materials
    A, t, d = 0.02 * 0.02, b.copper_thickness[0], b.gap_thicknesses()[0]
    kz = b.gap_properties()[0][0]
    q = P / A
    ht, hb = b.h_top, b.h_bottom
    # The part enters through the top face of the copper (a face flux, any thickness: 2.9.0; before it was a volumetric source in the 35 um slab). q_up leaves by the top film
    # straight from the face, q_dn = q - q_up goes down through the copper, the gap and the bottom copper to the bottom film:
    # q_up / ht = q_dn (1 / hb + d / kz + 2 t / k)  =>  q_up = q B / (1 / ht + B),  B = 1 / hb + d / kz + 2 t / k
    k = m.k_copper
    B = 1.0 / hb + d / kz + 2.0 * t / k
    q_up = q * B / (1.0 / ht + B)
    q_dn = q - q_up
    th_top, th_bot = q_up / ht, q_dn / hb
    r = fem.solve_steady(p, cell_mm=5.0)
    amb = b.ambient
    assert np.allclose(r.arrays["T_surface"][0], amb + th_top, rtol=0, atol=1e-6 * th_top)
    assert np.allclose(r.arrays["T_surface"][1], amb + th_bot, rtol=0, atol=1e-6 * th_top)
    assert r.arrays["T_surface"][0].min() > r.arrays["T_surface"][1].max()
    assert np.isfinite(q_up) and 0 < q_up < q


def test_the_surface_and_the_column_agree_on_thin_copper_and_the_point_is_the_hottest_node():
    r = fem.solve_steady(small(), cell_mm=2.0)
    assert r.extras["surface_excess_k"] < 0.01 * (r.t_max - r.ambient)           # 35 um copper: the two read-outs differ by milli-kelvin (the 6 x 6 mm part: 0.76 mK, 2.9.0)
    assert r.extras["t_max_point"] >= r.t_max and r.extras["t_max_point"] >= r.extras["t_max_surface_top"] - 1e-9
    lines = api.surface_report_lines(r)                                            # The surface is always reported now: two lines, resolved; the top one carries the term of the part (+0.001 K), the bottom none
    assert len(lines) == 2 and all("resolved by the finite elements" in l for l in lines)
    assert "+0.001 K" in lines[0] and "+0.000 K" in lines[1]
    assert r.arrays["T_surface"].shape == (2,) + r.T.shape[1:] and not r.arrays["T_surface_flag"].any()
    assert r.t_max_location[0] == 0 and 0.0 < r.t_max_location[1] < 0.04


def test_a_plain_board_agrees_with_the_fvm_and_the_3d_solid():
    # Measured on these boards at the same 2 mm cell (rise of the hottest cell, K): 60 x 40 mm FEM 34.13, FVM 34.27, 3D solid 34.30; 40 x 30 mm FEM 54.28, FVM 54.76, 3D solid
    # 54.79: the FEM column read-out is 0.4 to 0.9 % below. The review traced it to the finite volumes: on a 40 x 30 mm two-layer board the FEM converges from below
    # (0.06 % under the converged heater mean at the default mesh) and the independent finite volumes from above (0.5 % over at 1 mm; REVIEW_BRANCH4.md 3)
    for w, h in ((60.0, 40.0), (40.0, 30.0)):
        p = small(width=w, height=h)
        rows = {m: simulate(p, SolverOptions(models=(m,), cell_mm=2.0)).results[m] for m in ("fvm", "solid3d")}
        r = fem.solve_steady(p, cell_mm=2.0)
        for name, x in rows.items():
            assert r.delta_t == pytest.approx(x.delta_t, rel=0.015), (name, w, h)
            assert r.delta_t < x.delta_t
        assert r.extras["t_max_point"] - r.ambient > r.delta_t                    # the hottest node is above the cell mean


def test_a_part_off_the_axes_of_the_plan_and_several_parts_conserve_the_heat():
    p = small()
    p.add_heater(4, 0.5, rect=(5.1, 4.3, 9.7, 8.2), name="U2")
    r = fem.solve_steady(p, cell_mm=2.0)
    assert r.power_in == pytest.approx(1.5, rel=1e-12) and abs(r.balance_error) < 1e-9
    from pcbthermal.analysis import heater_stats
    rows = heater_stats(r, p)
    assert len(rows) == 2 and rows[1]["layer"] == 4


def test_a_hollow_via_under_the_part_lowers_the_temperature_like_the_fvm():
    base = small(layers=2, width=30.0, height=24.0)
    withvia = small(layers=2, width=30.0, height=24.0)
    for dx in (-1.0, 0.0, 1.0):
        for dy in (-1.0, 0.0, 1.0):
            withvia.add_via(15.0 + dx, 12.0 + dy, diameter=0.3)
    f0, f1 = (fem.solve_steady(x, cell_mm=1.0) for x in (base, withvia))
    v0, v1 = (simulate(x, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"] for x in (base, withvia))
    eff_fem, eff_fvm = f0.delta_t - f1.delta_t, v0.delta_t - v1.delta_t
    assert eff_fem > 0.5 and eff_fvm > 0.5
    assert eff_fem == pytest.approx(eff_fvm, rel=0.12)


def test_refusals_say_why():
    p = small()
    p.board.set_outline_mm([(0, 0), (40, 0), (40, 20), (20, 30), (0, 30)]) if hasattr(p.board, "set_outline_mm") else None
    if not p.board.has_outline():
        p.board.outline = np.array([(0, 0), (0.04, 0), (0.04, 0.02), (0.02, 0.03), (0, 0.03)])
    with pytest.raises(ValueError, match="rectangular or axis-aligned outline"):
        fem.solve_steady(p, cell_mm=2.0)
    with pytest.raises(ValueError):
        simulate(p, SolverOptions(models=("fem",), cell_mm=2.0))                       # alone: raised
    sim = simulate(p, SolverOptions(models=("fvm", "fem"), cell_mm=2.0))                # with another model: skipped with the reason
    assert "fvm" in sim.results and "fem" not in sim.results
    assert any("the FEM was not run" in str(w) and "axis-aligned" in str(w) for w in sim.warnings)
    assert sum("FEM" in str(w) and ("not run" in str(w) or "left out" in str(w)) for w in sim.warnings) == 1       # said once (the live check is replaced by the run's statement)


def test_a_mesh_over_the_memory_limit_is_refused_by_the_guard(monkeypatch):
    # A machine with 0.5 GB of memory: the exact count of the mesh makes the verdict "refuse" before any 3D array exists
    monkeypatch.setattr(memory, "physical_memory", lambda: 5 * 10 ** 8, raising=False)
    p = small(width=100.0, height=80.0)
    v = memory.check(p, ("fem",), 0.5, refuse="return", ram=5 * 10 ** 8, available=5 * 10 ** 8)
    assert v[0].verdict == "refuse" and "finite elements" in v[0].message
    with pytest.raises(memory.MemoryGuardError):
        memory.check(p, ("fem",), 0.5, ram=5 * 10 ** 8, available=5 * 10 ** 8)


def test_without_pyamg_a_large_mesh_is_a_clean_unavailable_and_a_skipped_model(monkeypatch):
    monkeypatch.setattr(femcore, "available", lambda: False)
    p = small(width=60.0, height=40.0)
    assert femmesh.unknowns(p, 1.0)[0] > femcore.FEM_DIRECT_MAX
    with pytest.raises(femcore.FemUnavailable, match="pyamg"):
        fem.solve_steady(p, cell_mm=1.0)
    with pytest.raises(ValueError, match="pyamg"):
        simulate(p, SolverOptions(models=("fem",), cell_mm=1.0))
    sim = simulate(p, SolverOptions(models=("fvm", "fem"), cell_mm=1.0))
    assert "fem" not in sim.results and any("pyamg" in str(w) and "the FEM was not run" in str(w) for w in sim.warnings)
    assert sum("FEM" in str(w) and ("not run" in str(w) or "left out" in str(w)) for w in sim.warnings) == 1


def test_a_cancel_stops_the_assembly():
    with pytest.raises(femcore.FemCancelled):
        fem.solve_steady(small(), cell_mm=2.0, cancel=lambda: True)


@pytest.mark.parametrize("bad", [{"fem_gap_elements": 1}, {"fem_gap_elements": 25}, {"fem_gap_elements": True}, {"fem_gap_elements": 3.5}, {"fem_refine": 0.9},
                                 {"fem_refine": 4.5}, {"fem_refine": float("nan")}, {"fem_refine": True}, {"fem_refine": "2"}])
def test_hostile_options_are_refused(bad):
    with pytest.raises(ValueError):
        SolverOptions(models=("fem",), **bad).validate()


def test_the_options_change_the_mesh_and_stay_close():
    p = small()
    n6 = femmesh.unknowns(p, 2.0, 6, 2.0)[0]
    assert femmesh.unknowns(p, 2.0, 8, 2.0)[0] > n6 and femmesh.unknowns(p, 2.0, 6, 1.0)[0] < n6
    a = simulate(p, SolverOptions(models=("fem",), cell_mm=2.0)).results["fem"]
    b = simulate(p, SolverOptions(models=("fem",), cell_mm=2.0, fem_gap_elements=8, fem_refine=1.0)).results["fem"]
    assert a.delta_t == pytest.approx(b.delta_t, rel=0.02)


def test_the_api_returns_the_fem_beside_the_other_models_with_the_arrays_of_the_3d_solid():
    p = small()
    sim = simulate(p, SolverOptions(models=("fvm", "solid3d", "fem"), cell_mm=2.0))
    f, s = sim.results["fem"], sim.results["solid3d"]
    assert f.T.shape == s.T.shape and f.dx == pytest.approx(s.dx) and f.power_in == pytest.approx(s.power_in)
    assert sorted(r["model"] for r in sim.table()) == ["fem", "fvm", "solid3d"]
    text = sim.report()
    assert "FEM read-outs" in text and "column mean" in text
    assert sim.to_dict()["models"]["fem"]["t_max_c"] == pytest.approx(f.t_max)
    assert api.COMPARISON_MODELS == ("fdm", "solid3d", "fem") and "fem" not in api.TIME_MODELS


def test_the_computed_h_loop_and_the_top_path_wrap_the_fem_as_they_wrap_the_others():
    p = small()
    p.board.h_mode = "computed"
    sim = simulate(p, SolverOptions(models=("fvm", "fem"), cell_mm=2.0))
    assert sim.h_used["fem"][0] == pytest.approx(sim.h_used["fvm"][0], rel=0.05)
    q = small()
    q.heaters[0].theta, q.heaters[0].theta_sa = 3.0, 20.0
    sim = simulate(q, SolverOptions(models=("fem",), cell_mm=2.0))
    assert 0.0 < sim.heater_rows()[0]["power_top_w"] < 1.0


def test_a_block_is_read_like_the_other_models():
    p = small(layers=2)
    p.add_heatsink(2, 20.0, rect=(10, 8, 30, 22), name="block", thickness_mm=3.0, contact_r=5.0e-4)
    r = fem.solve_steady(p, cell_mm=2.0)
    assert abs(r.balance_error) < 1e-9 and "block_T" in r.arrays and "block_bottom_max" in r.extras
    assert r.extras["block_bottom_w_to_air"] == pytest.approx(r.extras["block_bottom_w_to_block"])
    assert 0.1 < r.extras["block_bottom_w_to_air"] <= r.power_in + 1e-9
    v = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    assert r.delta_t == pytest.approx(v.delta_t, rel=0.05)


def test_the_live_check_says_what_will_not_run(monkeypatch):
    from pcbthermal import checks
    p = small()
    assert not checks.check_fem(p, ("fvm",), 2.0)
    assert not checks.check_fem(p, ("fem",), 2.0)
    q = small()
    q.add_heater(1, 0.1, rect=(1, 1, 1.5, 1.5), name="tiny")
    assert any("narrower than two fine elements" in str(w) for w in checks.check_fem(q, ("fem",), 2.0))
    monkeypatch.setattr(femcore, "available", lambda: False)
    assert any("pyamg" in str(w) for w in checks.check_fem(small(width=60.0, height=40.0), ("fem",), 1.0))
    q.board.outline = np.array([(0, 0), (0.04, 0), (0.04, 0.02), (0.02, 0.03), (0, 0.03)])
    assert any("cannot be built" in str(w) for w in checks.check_fem(q, ("fem",), 2.0))
    assert any("cannot be built" in str(w) for w in checks.check_input(q, ("fem",), 2.0))


def test_the_command_line_runs_the_fem_on_a_small_project(tmp_path, capsys):
    from pcbthermal.project import Project, save_project
    path = tmp_path / "small.pcbt.json"
    save_project(path, Project(problem=small()))
    rc = cli.main(["run", str(path), "--model", "fem", "--cell-mm", "2", "--out", str(tmp_path / "out"), "--no-plots", "--fem-gap-elements", "4"])
    out = capsys.readouterr().out
    assert rc == 0 and "| FEM |" in out
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert "fem" in summary["models"] and summary["options"]["fem_gap_elements"] == 4 and summary["options"]["comparison_models"] == ["fem"]


@needs_pyamg
def test_the_command_line_runs_the_fem_on_the_example_board(tmp_path, capsys):
    from pcbthermal.examples import example_board
    from pcbthermal.project import Project, save_project
    path = tmp_path / "ex.pcbt.json"
    save_project(path, Project(problem=example_board()))
    assert cli.main(["run", str(path), "--model", "fem", "--cell-mm", "2", "--out", str(tmp_path / "out"), "--no-plots"]) == 0
    assert "| FEM |" in capsys.readouterr().out


def test_every_tuple_that_lists_the_3d_solid_as_a_comparison_model_lists_the_fem():
    assert "fem" in api.COMPARISON_MODELS and "fem" in api.SKIPPABLE_MODELS and "fem" in cli.RUN_MODELS
    from pcbthermal import results
    assert results.model_label("fem") == "FEM"


@needs_pyamg
def test_case_2_of_muzychka_the_resolved_surface_meets_the_paper():
    # Case 2 of Muzychka, Culham and Yovanovich (2003): a 50 x 50 x 10 mm plate (k 150), h 400 on the bottom face, top and sides adiabatic, four 10 x 10 mm sources of
    # 10 / 25 / 20 / 15 W. Paper Table 4 centroids (top surface): 97.40 / 103.82 / 101.28 / 99.94 degC; the independent 3D solver of research/muzychka-case2-analytic reads
    # 97.39 / 103.81 / 101.27 / 99.93 with 16 sub-slabs (its column mean 95.35 / 99.15 / 97.49 / 97.01). The FEM resolves the surface: it must sit on the surface values, the
    # column on the column means (docs/validation.md 55 and 56). Review of branch 4: the first version read a 2 x 2 cell window chosen with round(), which is off the
    # centroid by 0.5 mm (to even: down at 12.5, up at 37.5) and about 0.07 K below it, and met the paper to the printed digit only because that cancelled the 1 um FR-4 film
    # of this Problem (+0.09 K). The centred 1 mm cell reads 97.467 / 103.851 / 101.327 / 99.992 (column 95.436 / 99.231 / 97.571 / 97.095); the node test below, with the
    # film made conductive, is the clean comparison with the paper
    cen = [(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)]
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0))
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip(cen, [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    r = fem.solve_steady(p, cell_mm=1.0)
    paper, col3d = [97.40, 103.82, 101.28, 99.94], [95.35, 99.15, 97.49, 97.01]
    S, T = r.arrays["T_surface"][0], r.T[0]
    for (cx, cy), want, col in zip(cen, paper, col3d):
        i, j = int(cx // 1.0), int(cy // 1.0)                                       # the 1 mm cell whose centre IS the centroid (x.5 mm)
        s, c = S[j, i], T[j, i]
        print(f"case 2 at ({cx}, {cy}): FEM surface {s:.3f} (paper {want}), column {c:.3f} (3D column {col})")
        assert 0.0 < s - want < 0.09 and abs(c - col) < 0.1                        # the 1 um FR-4 film of this Problem puts the plate about 0.09 K up
    assert abs(r.balance_error) < 1e-9


def test_a_one_layer_board_reads_the_copper_face_not_the_laminate_bottom():
    # Review of branch 4: the bottom 'surface' of a one-layer board is the bottom face of its copper (the meaning of thickness.py), so an ordinary 35 um board reports a surface
    # equal to the column (no longer omitted: the surface is always shown); the bottom of the laminate (6.8 K cooler on this board) is bottom_face_mean, the film temperature of the computed-h loop
    p = Problem.new(width_mm=40, height_mm=30, layers=1, h_top=10.0, h_bottom=10.0)
    p.add_full_copper([1])
    p.add_heater(1, 1.0, rect=(17, 12, 23, 18), name="U1")
    r = fem.solve_steady(p, cell_mm=2.0)
    assert r.extras["surface_excess_k"] < 0.01 * (r.t_max - r.ambient)
    lines = api.surface_report_lines(r)                                            # always reported now (feature/surface-always-both), resolved; the part's face flux (2.9.0) puts the top face a milli-kelvin above the column mean and the bottom face a milli-kelvin below it
    assert len(lines) == 2 and all("resolved by the finite elements" in l for l in lines)
    assert "+0.001 K" in lines[0] and "-0.001 K" in lines[1]
    assert r.extras["t_max_surface_bottom"] == pytest.approx(r.t_max, abs=0.01)
    assert r.extras["bottom_face_mean"] < r.layer_mean[0] - 1.0                    # the laminate carries a drop of kelvins to the bottom face
    assert abs(r.balance_error) < 1e-9


def test_a_solve_that_does_not_converge_leaves_the_fem_out_and_the_other_models_answer(monkeypatch):
    # Review of branch 4: a RuntimeError of the conjugate gradients escaped the API and stopped every model of the run; it is now a refusal of the FEM with the reason
    def fail(self, **kw):
        raise RuntimeError("the conjugate-gradient solution has a relative residual of 1.12e-08")
    monkeypatch.setattr(femcore.Model, "solve", fail)
    p = small()
    with pytest.raises(ValueError, match="did not converge"):
        fem.solve_steady(p, cell_mm=2.0)
    sim = simulate(p, SolverOptions(models=("fvm", "fem"), cell_mm=2.0))
    assert "fvm" in sim.results and "fem" not in sim.results
    assert any("was not run" in str(w) and "did not converge" in str(w) for w in sim.warnings)
    with pytest.raises(ValueError, match="did not converge"):
        simulate(p, SolverOptions(models=("fem",), cell_mm=2.0))


@needs_pyamg
def test_case_2_the_converged_node_at_the_centroid_meets_the_paper_with_a_conductive_film():
    # Review of branch 4: the node at each source centroid on the top face, with the 1 um laminate film that a one-layer Problem must carry made as conductive as the
    # plate (k 150), reads 97.381 / 103.777 / 101.248 / 99.909 degC at a 1 mm cell (97.380 / 103.774 / 101.246 / 99.908 at 0.5 mm, refinement 4): 0.02 to 0.05 K below
    # Table 4 of the paper (97.40 / 103.82 / 101.28 / 99.94); with the FR-4 film the same nodes read 0.09 K higher (the film's resistance times the mean flux)
    cen = [(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)]
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None,
                    materials=Materials(k_copper=150.0, k_fr4_through=150.0, k_fr4_inplane=150.0))
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip(cen, [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    mesh = femmesh.build(p, 1.0, 6, 2.0)
    th = mesh.model.solve()["T"]
    s0 = [s for s, sl in enumerate(mesh.slabs) if sl["region"] == "board"][0]
    nodes = np.unique(mesh.model.elems[mesh.elem_slab == s0][:, :4])
    X = mesh.model.nodes[nodes]
    for (cx, cy), want in zip(cen, [97.40, 103.82, 101.28, 99.94]):
        d = np.hypot(X[:, 0] - cx * 1e-3, X[:, 1] - cy * 1e-3)
        assert d.min() < 1e-9                                                       # the centroid is a node of the mesh
        got = 25.0 + th[nodes[int(np.argmin(d))]]
        assert -0.07 < got - want < 0.0, (cx, cy, got)


def test_the_interface_pad_of_a_block_has_no_wall_film_one_dimensional_column():
    # The pad under a block is a fictitious layer (its height is the contact resistance times K_PAD): the film belongs on the walls of the metal only. A block over the whole
    # board with insulated board edges is a one-dimensional column; the only lateral loss is the film on the block walls (plain h of the face on the area perimeter x thickness),
    # which adds to the exposed film as h_eff = hb (1 + perimeter t / A). Measured: the FEM meets the closed form within 0.003 K; with the film on the pad walls it read 3.5 to 41 K low
    for rc, tb in ((5.0e-4, 1.0e-3), (5.0e-3, 1.0e-3), (5.0e-3, 3.0e-3)):
        p = Problem.new(width_mm=20, height_mm=20, layers=2, h_top=30.0, h_bottom=12.0, h_side=None)
        p.add_full_copper([1, 2])
        power = 4.0
        p.add_heater(1, power, rect=(0, 0, 20, 20), name="all")
        p.add_heatsink(2, 0.0, rect=(0, 0, 20, 20), name="b", thickness_mm=tb * 1e3, contact_r=rc)
        b = p.board
        area, t, d, k = 4.0e-4, b.copper_thickness[0], b.gap_thicknesses()[0], b.materials.k_copper
        kz = b.gap_properties()[0][0]
        h_eff = b.h_bottom * (1.0 + 0.08 * tb / area)
        big_b = 1.0 / h_eff + tb / p.heatsinks[0].k + rc + d / kz + t / k
        big_c = 1.0 / b.h_top + t / k
        q = power / area
        th_top = q * (big_b + t / (2 * k)) / (big_b + big_c) / b.h_top
        r = fem.solve_steady(p, cell_mm=5.0)
        assert r.arrays["T_surface"][0].max() - r.ambient == pytest.approx(th_top, abs=0.02), (rc, tb)


def test_the_interface_pad_of_a_block_has_no_wall_film_against_the_3d_solid():
    # The same boards with a small part: measured at the 2 mm cell, rise of the hottest cell: FEM 202.81 and 214.45 K for contact 5e-4 and 5e-3 m2K/W, 3D solid 205.77 and
    # 217.40 K, the FVM 204.79 and 216.51 K. The FEM is 1.4 % below the 3D solid, the column read-out bias of the 2 mm cell: the same board without the block reads 1.1 % below,
    # and both gaps fall together with the cell (0.6 and 0.5 % at 1 mm, 0.14 and 0.12 % at 0.5 mm). With the film on the pad walls the FEM read 199.29 and 186.56 K. The change
    # of the rise with the contact resistance is the clean figure: 11.63 K (FEM), 11.63 K (3D), 11.72 K (FVM); it was -12.7 K
    rise = {}
    for rc in (5.0e-4, 5.0e-3):
        p = small(layers=2, power=5.0)
        p.add_heatsink(2, 20.0, rect=(8, 6, 32, 24), name="b", thickness_mm=3.0, contact_r=rc)
        rise[rc] = (fem.solve_steady(p, cell_mm=2.0).delta_t, simulate(p, SolverOptions(models=("solid3d",), cell_mm=2.0)).results["solid3d"].delta_t)
        assert rise[rc][0] == pytest.approx(rise[rc][1], rel=0.02), rc
    d_fem = rise[5.0e-3][0] - rise[5.0e-4][0]
    d_3d = rise[5.0e-3][1] - rise[5.0e-4][1]
    assert d_fem == pytest.approx(d_3d, abs=0.15)


def test_the_interface_pad_of_a_block_does_not_spread_heat_sideways():
    # The pad is a contact resistance: it conducts across only (femmesh.K_PAD_INPLANE). With K_PAD in its plane, a pad of height rc x K_PAD (50 mm at 5e-2 m2K/W) over a part
    # on the top face spread its heat sideways: the FEM read 151.77 K against 169.59 K in the FVM (no pad slab) and 169.88 K in the 3D solid at 5e-2 (-10.5 %), 150.80 against
    # 154.64 K at 5e-3. Measured with the fix at the 2 mm cell: 168.26 and 153.49 K, 0.8 % below the FVM (the plain board without the block reads 0.8 % below the FVM too)
    for rc in (5.0e-3, 5.0e-2):
        p = small(layers=2, power=3.0)
        p.add_heatsink(1, 0.0, rect=(12, 9, 28, 21), name="b", thickness_mm=5.0, contact_r=rc)
        r = fem.solve_steady(p, cell_mm=2.0)
        ref = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"].delta_t
        assert abs(r.balance_error) < 1e-9
        assert r.delta_t == pytest.approx(ref, rel=0.015), rc
    m = femmesh.build(p, cell_mm=2.0)
    pad = np.isin(m.elem_slab, [s for s, sl in enumerate(m.slabs) if sl["kind"] == "pad"])
    assert np.all(m.model.k[pad, 0] == femmesh.K_PAD_INPLANE) and np.all(m.model.k[pad, 2] == femmesh.K_PAD)
