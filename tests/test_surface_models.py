#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_surface_models.py
@brief The surface read-out of the Analytic (rule F), the 3D solid (the half slab above 105 um, rule S on one slab) and the text of the Lumped (feature/surface-readout-models): closed forms, the
       plates of research/surface-readout-models against the independent 3D solver (tests/helpers/layered3d.py) and the program's FVM parabola, a thick board with the part on the bottom face,
       the flags, the words, and that no column read-out moves by a bit.
"""

import copy
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "helpers"))
sys.path.insert(0, os.path.join(HERE, "..", "research", "surface-readout-models", "lib"))
import plates                                                  # noqa: E402

from pcbthermal import Problem, SolverOptions, analysis, simulate, thickness   # noqa: E402
from pcbthermal.examples import example_board                  # noqa: E402
from pcbthermal.model import Dielectric, Materials             # noqa: E402

CELL = 1.0     # mm: the source edges of the plates lie on cell edges


def term(res, prob, k=0):
    """!
    @brief Surface minus column under part k, the hottest cell of each (what the part row shows).
    @param res SteadyResult.
    @param prob Problem.
    @param k Index of the part.
    @return float, K.
    """
    row = analysis.heater_stats(res, prob)[0 + k]
    return row["t_max_surface"] - row["t_max"]


def run(prob, model, cell=CELL):
    """!
    @brief One model on one problem.
    @param prob Problem.
    @param model Model key.
    @param cell Plan cell in mm.
    @return SteadyResult.
    """
    return simulate(copy.deepcopy(prob), SolverOptions(models=(model,), cell_mm=cell)).results[model]


# ---------------------------------------------------------------- closed forms: a part over the whole face of an insulated column

def column(t_um, k=385.0, layers=1):
    """!
    @brief A 10 x 10 mm board whose top is entirely a part of 4 W, insulated at the top and the sides, cooled below: a one-dimensional column.
    @param t_um Copper thickness in um.
    @param k Copper conductivity in W/mK.
    @param layers Layers (1 or 2).
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, layers=layers, thickness_mm=1.6 + t_um * 1e-3, copper_um=t_um, ambient=25.0, h_top=1e-6, h_bottom=500.0, h_side=None, materials=Materials(k_copper=k))
    p.add_full_copper()
    p.add_heater(1, 4.0, rect=(0, 0, 10, 10), name="S")
    return p


@pytest.mark.parametrize("model,t_um", [("analytic", 1000.0), ("analytic", 35.0), ("solid3d", 1000.0), ("solid3d", 35.0), ("solid3d", 105.0)])
def test_a_part_over_the_whole_face_gives_q_t_over_2k(model, t_um):
    # Rule F, rule S (one slab) and the half slab (several slabs) all give q t / (2 k) on a one-dimensional column; the FVM parabola is the reference of the same number
    p = column(t_um)
    q = 4.0 / (10e-3 * 10e-3)
    exact = q * t_um * 1e-6 / (2.0 * 385.0)
    r = run(p, model, 2.0)
    d = float(np.nanmax(r.arrays["T_surface"][0] - r.T[0]))
    assert d == pytest.approx(exact, rel=2e-3), (model, t_um, d, exact)
    assert d == pytest.approx(float(np.nanmax(run(p, "fvm", 2.0).arrays["T_surface"][0] - run(p, "fvm", 2.0).T[0])), rel=2e-3)


# ---------------------------------------------------------------- the plates against the independent 3D solver and the FVM parabola

PLATE_IDS = [0, 3, 5, 7]            # case 2 of Muzychka and others, 10 mm Al (t/a = 1), 5 mm Al with a 2 mm source (t/a = 2.5), 2 mm Cu on FR-4 with a via
_REF = {}


def reference(i):
    """!
    @brief The independent 3D solution of plate i, computed once.
    @param i Index into plates.PLATES.
    @return dict of plates.reference.
    """
    if i not in _REF:
        _REF[i] = plates.reference(plates.PLATES[i])
    return _REF[i]


@pytest.mark.parametrize("i", PLATE_IDS)
def test_the_analytic_surface_term_equals_the_fvm_parabola(i):
    # Research 4.1 and 4.2: within 0.02 K of the FVM parabola on the one-layer plates, 0.056 K on the via plate (the Analytic has no via conductance in its fluxes)
    p = plates.problem(plates.PLATES[i])
    ta, tf = term(run(p, "analytic"), p), term(run(p, "fvm"), p)
    assert abs(ta - tf) < (0.06 if plates.PLATES[i][7] else 0.02), (plates.PLATES[i][0], ta, tf)


@pytest.mark.parametrize("i", PLATE_IDS)
def test_the_solid_surface_is_the_independent_surface_within_its_column_offset(i):
    # Research 4.5: eight slabs within -0.00 to +0.13 K of the independent surface on the eight plates (here at a 1 mm plan cell, observed -0.07 to +0.10 K)
    p = plates.problem(plates.PLATES[i])
    r = run(p, "solid3d")
    s = analysis.surface_stats(r, p.heaters[0].polygon, p.heaters[0].layer, p.board.outline)[0]
    assert abs(s - reference(i)["surf"]) < 0.15, (plates.PLATES[i][0], s, reference(i)["surf"])
    assert thickness.surface_kind(r) == "computed" and not np.asarray(r.arrays["T_surface_flag"]).any()


@pytest.mark.parametrize("i", [0, 3])
def test_the_flag_of_the_analytic_is_the_flag_of_the_fvm_and_the_parabola_is_an_upper_estimate(i):
    p = plates.problem(plates.PLATES[i])
    ra, rf = run(p, "analytic"), run(p, "fvm")
    assert np.array_equal(ra.arrays["T_surface_flag"], rf.arrays["T_surface_flag"]) and ra.arrays["T_surface_flag"].any()
    # at t/a = 1 the parabola is above the independent surface (the reason for the flag), by 1.1 to 3.6 K on these plates
    s = analysis.surface_stats(ra, p.heaters[0].polygon, 0, None)[0]
    assert s > reference(i)["surf"] and "upper side" in thickness.surface_how(ra, True)


def test_the_solid_on_one_copper_slab_reads_the_fvm_parabola():
    # 35 um copper: one slab, rule S from the links of the solid, against the FVM parabola of the same board (research 4.5: 1 mK on the one-layer plates)
    p = plates.problem(plates.PLATES[7])
    p.board.copper_thickness = [35e-6, 35e-6]
    p.board.thickness = 1.07e-3
    r, f = run(p, "solid3d"), run(p, "fvm")
    assert thickness.surface_kind(r) == "estimate" and r.extras["surface_copper_slabs_top"] == 1.0
    assert abs(term(r, p) - term(f, p)) < 0.3 * max(term(f, p), 1e-4) + 5e-5


def test_a_thick_bottom_layer_with_the_part_on_the_bottom_face_mirrors_the_top_face():
    # Several copper slabs on the BOTTOM outer layer: the last slab of the last layer and its neighbour above; the mirror board must give the same term to the round-off of the solver
    top = plates.problem(plates.PLATES[7])
    mirror = copy.deepcopy(top)
    mirror.board.copper_thickness = list(top.board.copper_thickness)[::-1]
    mirror.board.h_top, mirror.board.h_bottom = top.board.h_bottom, top.board.h_top
    mirror.vias.clear()
    top.vias.clear()
    mirror.heaters[0].layer = 1
    a, b = run(top, "solid3d"), run(mirror, "solid3d")
    assert b.extras["surface_copper_slabs_bottom"] >= 2.0
    d_top = float(np.nanmax(a.arrays["T_surface"][0] - a.T[0]))
    d_bot = float(np.nanmax(b.arrays["T_surface"][1] - b.T[1]))
    assert d_bot == pytest.approx(d_top, rel=1e-6) and d_top > 0.1


# ---------------------------------------------------------------- the Lumped: a text, never a temperature

def test_the_lumped_has_no_surface_array_only_the_bound_on_the_term_in_words():
    p = plates.problem(plates.PLATES[0])
    sim = simulate(p, SolverOptions(models=("lumped",), cell_mm=2.0))
    assert "T_surface" not in sim.results["lumped"].arrays
    row = sim.heater_rows()[0]
    q = 25.0 / (10e-3) ** 2
    assert row["surface_bound_k"] == pytest.approx(q * 10e-3 / (2.0 * 150.0), rel=1e-9) and "t_max_surface" not in row
    text = thickness.lumped_surface_note(row["surface_bound_k"], 1)
    for word in ("no surface temperature", "not a guarantee", "hotter neighbouring part", "absent copper", "thick plates", "own error"):
        assert word in text, word
    assert text in sim.report()
    # a part on an inner layer has no outer face: no bound
    q2 = example_board()
    q2.heaters[0].layer = 1
    assert "surface_bound_k" not in simulate(q2, SolverOptions(models=("lumped",), cell_mm=2.0)).heater_rows()[0]


# ---------------------------------------------------------------- the part over a copper window in the Analytic

def test_the_analytic_says_a_part_over_absent_copper_has_no_bare_laminate_term():
    p = Problem.new(60.0, 40.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=None)
    for rect in ((0, 0, 25, 40), (35, 0, 60, 40), (25, 0, 35, 15), (25, 25, 35, 40)):
        p.add_zone(1, rect=rect, fill=1.0)
    p.add_zone(2, rect=(0, 0, 60, 40), fill=1.0)
    p.add_heater(1, 2.0, rect=(27, 17, 33, 23), name="U")
    a, f = run(p, "analytic"), run(p, "fvm")
    assert a.extras.get("surface_part_over_bare_laminate") == 1.0 and "surface_part_over_bare_laminate" not in run(plates.problem(plates.PLATES[0]), "analytic").extras
    assert "no bare-laminate term" in thickness.surface_how(a)
    # the finite-volume column holds the face term (287 degC measured on the branch), the Analytic does not (110 degC): the surface of the Analytic is the sheet's, never better than its column
    assert f.t_max > 250.0 and a.t_max < 120.0
    assert 0 < float(np.nanmax(a.arrays["T_surface"][0] - a.T[0])) < 0.01


# ---------------------------------------------------------------- a view: no column read-out moves

@pytest.mark.parametrize("board", ["example", "plate", "two_layer_via"])
def test_no_column_number_moves_with_the_surface_arrays_switched_off(monkeypatch, board):
    p = {"example": example_board, "plate": lambda: plates.problem(plates.PLATES[0]), "two_layer_via": lambda: plates.problem(plates.PLATES[7])}[board]()
    models = ("lumped", "analytic", "solid3d")
    on = simulate(copy.deepcopy(p), SolverOptions(models=models, cell_mm=2.0))
    monkeypatch.setattr(thickness, "attach_field", lambda *a, **k: None)
    monkeypatch.setattr(thickness, "attach_solid", lambda *a, **k: None)
    off = simulate(copy.deepcopy(p), SolverOptions(models=models, cell_mm=2.0))
    for m in models:
        assert on.results[m].t_max == off.results[m].t_max and np.array_equal(on.results[m].T, off.results[m].T), m
        assert on.results[m].power_out == off.results[m].power_out and on.power_used.get(m) == off.power_used.get(m)
    assert "T_surface" in on.results["analytic"].arrays and "T_surface" not in off.results["analytic"].arrays
    for a, b in zip(on.heater_rows(), off.heater_rows()):
        assert {k: v for k, v in a.items() if "surface" not in k} == {k: v for k, v in b.items() if "surface" not in k}


def test_the_words_the_summary_and_the_files_carry_the_new_surfaces(tmp_path):
    p = plates.problem(plates.PLATES[0])
    sim = simulate(p, SolverOptions(models=("fvm", "analytic", "solid3d", "lumped"), cell_mm=2.0))
    rows = {r["model"]: r for r in sim.table()}
    assert rows["lumped"]["t_max_surface_c"] is None and all(rows[m]["t_max_surface_c"] is not None for m in ("fvm", "analytic", "solid3d"))
    assert "computed from the copper slabs" in thickness.surface_how(sim.results["solid3d"])
    assert "own field and its uniform conductances" in thickness.surface_how(sim.results["analytic"])
    sim.save(str(tmp_path), plots=False, surface_files=True)
    assert (tmp_path / "surface_analytic.csv").exists() and (tmp_path / "surface_solid3d.csv").exists() and not (tmp_path / "surface_lumped.csv").exists()
