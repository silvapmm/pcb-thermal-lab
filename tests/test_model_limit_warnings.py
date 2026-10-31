#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_model_limit_warnings.py
@brief Warnings about the documented limits of the models (Analytic copper spread, bare laminate, vias): they appear where the research measured the
       error, stay silent on the example boards, and never change a result.
"""

import glob
import os

import numpy as np

from pcbthermal import Problem, SolverOptions, project, simulate
from pcbthermal.checks import check_model_limits

EXAMPLES = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "examples", "*.pcbt.json")))


def pad_board(pad_mm=10.0, dielectric_mm=0.1):
    """!
    @brief A 60 x 60 mm two-layer board of the given thickness: top copper only on a pad under the part, no copper on the bottom layer
           (the `gap0.1-empty` kind of row of research/gap-subdivision, where the program's own spread was silent: 0.004 against 0.28).
    @param pad_mm Side of the top copper pad in mm.
    @param dielectric_mm Total board thickness in mm (the gap between the two copper layers is of this order).
    @return Problem.
    """
    p = Problem.new(60, 60, 2, thickness_mm=dielectric_mm)
    p.add_zone(1, rect=(30 - pad_mm / 2, 30 - pad_mm / 2, 30 + pad_mm / 2, 30 + pad_mm / 2))
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def test_analytic_spread_warning_on_thin_gap_pad():
    """!
    @brief The new trigger fires on a pad over a thin gap with a bare second layer (the case the program's own spread missed).
    @return None.
    """
    res = simulate(pad_board(), SolverOptions(models=("analytic",), cell_mm=0.5)).results["analytic"]
    assert any("copper coverage varies around the heaters" in w for w in res.warnings)


def test_analytic_spread_silent_on_uniform_and_examples():
    """!
    @brief No spread warning on a uniform board or on the example boards.
    @return None.
    """
    p = Problem.new(40, 40, 2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(15, 15, 25, 25))
    res = simulate(p, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"]
    assert not any("copper coverage varies" in w for w in res.warnings)
    for f in EXAMPLES:
        r = simulate(project.load_project(f).problem, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"]
        assert not any("copper coverage varies" in w for w in r.warnings), f


def window_board(window_mm, layers=2, part_mm=6.0):
    """!
    @brief The board of research/bare-spot-under-source: 30 mm, full copper on every layer except a centred square window in the top
           layer, a centred square part on top.
    @param window_mm Side of the window in mm (0: full copper).
    @param layers Copper layers.
    @param part_mm Side of the part in mm.
    @return Problem.
    """
    p = Problem.new(30, 30, layers)
    a, b = 15 - window_mm / 2, 15 + window_mm / 2
    for layer in range(1, layers + 1):
        if layer == 1 and window_mm > 0:
            # Four rectangles around the window, edges on the same lines
            for r in ((0, 0, 30, a), (0, b, 30, 30), (0, a, a, b), (b, a, 30, b)):
                p.add_zone(1, rect=r)
        else:
            p.add_zone(layer, rect=(0, 0, 30, 30))
    p.add_heater(1, 1.0, rect=(15 - part_mm / 2, 15 - part_mm / 2, 15 + part_mm / 2, 15 + part_mm / 2), name="U")
    return p


def test_bare_laminate_warning_on_the_windows_of_the_study():
    """!
    @brief Every window of the bare-spot study (2 to 20 mm under a 6 mm part, 2 and 4 layers, cells of 0.5 to 2 mm) warns the layered
           models and only them. Regression: a trigger on the mean fill of the footprint was silent on all of them (mean fill 0.89 and
           0.56 for the 2 and 4 mm windows, 0 for the others).
    @return None.
    """
    for layers in (2, 4):
        for window in (2, 4, 6, 8, 12, 20):
            for cell in (0.5, 1.0, 2.0):
                w = check_model_limits(window_board(window, layers), ("fvm", "solid3d"), cell)
                assert len(w) == 1 and "bare laminate" in w[0] and w[0].kind == "heater" and w[0].index == 0, (layers, window, cell)
                assert "(fvm)" in w[0]
    assert check_model_limits(window_board(6), ("solid3d",), 1.0) == []


def test_bare_laminate_warning_on_a_small_pad_off_the_centre():
    """!
    @brief A part whose centre is off its small pad (4 mm2 of copper in a corner of a 36 mm2 footprint) warns.
    @return None.
    """
    p = Problem.new(60, 60, 2)
    p.add_zone(1, rect=(28, 28, 30, 30))
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    assert any("bare laminate" in w for w in check_model_limits(p, ("fvm",), 1.0))


def test_bare_laminate_silent_on_copper_under_the_part():
    """!
    @brief Full copper, a pad that covers the part, a pad a little smaller than the part (the centre on copper) and a board with no
           copper at all (it has its own warnings) do not trigger it.
    @return None.
    """
    for cell in (0.5, 1.0, 2.0):
        assert check_model_limits(window_board(0, 2), ("fvm", "lumped"), cell) == []
        assert check_model_limits(window_board(0, 4), ("fvm", "lumped"), cell) == []
        assert check_model_limits(pad_board(10.0, 1.6), ("fvm", "lumped"), cell) == []
        assert check_model_limits(pad_board(5.0, 1.6), ("fvm", "lumped"), cell) == []
    none = Problem.new(60, 60, 2)
    none.add_heater(1, 1.0, rect=(27, 27, 33, 33))
    assert check_model_limits(none, ("fvm", "lumped"), 1.0) == []


def test_via_warnings():
    """!
    @brief Lumped: a part with vias under it warns once (tagged with the part); the vias outside every footprint give one warning together
           (tagged with the first), and a via off the board none; the FVM alone gives no via warning at any cell.
    @return None.
    """
    p = Problem.new(60, 60, 2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    p.add_via(29, 29)
    p.add_via(31, 31)
    p.add_via(10, 10)
    p.add_via(50, 10)
    w = check_model_limits(p, ("lumped",), 1.0)
    assert len(w) == 2
    assert w[0].kind == "heater" and w[0].index == 0 and "2 vias under the footprint" in w[0]
    assert w[1].kind == "via" and w[1].index == 2 and "and 1 more vias" in w[1] and "outside the footprint" in w[1]
    for cell in (0.5, 1.0, 2.0, 4.0):
        assert check_model_limits(p, ("fvm", "fdm"), cell) == []
    q = Problem.new(60, 60, 2)
    q.add_full_copper()
    q.add_heater(1, 1.0, rect=(27, 27, 33, 33))
    q.add_via(30, 30)
    w = check_model_limits(q, ("lumped",), 1.0)
    assert len(w) == 1 and "1 via under the footprint" in w[0]


def test_warnings_do_not_change_results_and_reach_the_simulation(monkeypatch):
    """!
    @brief The warnings reach Simulation.problem_warnings, and the fields of every model are bit-identical with the check switched off.
    @param monkeypatch pytest fixture used to switch the check off.
    @return None.
    """
    from pcbthermal import api
    p = window_board(6)
    p.add_via(15, 15)
    opts = SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=1.0)
    sim = simulate(p, opts)
    assert any("bare laminate" in w for w in sim.problem_warnings)
    assert any("via under the footprint" in w for w in sim.problem_warnings)
    assert not any("bare laminate" in w for w in simulate(pad_board(10.0, 1.6), opts).problem_warnings)
    monkeypatch.setattr(api, "check_model_limits", lambda *a, **k: [])
    quiet = simulate(p, opts)
    assert not any("bare laminate" in w for w in quiet.problem_warnings)
    for m in opts.models:
        assert np.array_equal(sim.results[m].T, quiet.results[m].T), m
